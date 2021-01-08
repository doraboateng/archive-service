import json
import pydgraph
from hashlib import sha256
from typing import List, Union

_NODE_CACHE = {}
skip_expression_titles = {
    'Foo',
    'OpgNWeVydVsOulWTXz',
    'IxRCtWZJwPgQGyTEmbb',
    'WHvZIeuZFVbvts',
    'fjuZRLctwBDroRElyZ',
}


def open_graph_connection():
    stub = pydgraph.DgraphClientStub('localhost:9080')
    client = pydgraph.DgraphClient(stub)

    return stub, client


def close_graph_connection(stub, client):
    stub.close()


def reset():
    result = True
    stub, client = open_graph_connection()

    try:
        client.alter(pydgraph.Operation(drop_all=True))
    except Exception as error:
        result = False
        print(f'Dgraph alter "{type(error)}" error:', error)
    finally:
        close_graph_connection(stub, client)

    return result


def upsert(
    client: pydgraph.DgraphClient,
    node_type: str,
    key_name: str,
    key_value: str,
    po_pairs: List[tuple],
):
    nquads = []
    response = None
    selector = f'eq({node_type}.{key_name}, "{key_value}")'
    query = '{ u as node(func: ' + selector + ') { uid } }'

    po_pairs.append((key_name, f'"{key_value}"'))

    for i, pair in enumerate(po_pairs):
        nquads.append(f'uid(u) <{node_type}.{pair[0]}> {pair[1]} .')

    nquads.append(f'uid(u) <dgraph.type> "{node_type}" .')

    try:
        transaction = client.txn()
        mutation = transaction.create_mutation(set_nquads="\n".join(nquads))
        request = transaction.create_request(query=query, mutations=[mutation], commit_now=True)
        response = transaction.do_request(request)
    finally:
        if transaction:
            transaction.discard()

    return response


def upsert_bak(
    client,
    node_type,
    key_name,
    key_value,
    node = None,
    selector = None,
):
    transaction = client.txn()
    response = None
    node = node or {}
    node[key_name] = f'"{key_value}"'
    node['dgraph.type'] = f'"{node_type}"'

    if 'uid' not in node:
        node['uid'] = f'"_:{key_value}"'
    
    if not selector:
        selector = f'eq({node_type}.{key_name}, "{key_value}")'

    try:
        query = '{ u as node(func: ' + selector + ') { uid } }'
        nquads = []

        for key in node:
            if key == 'uid':
                continue
        
            if type(node[key]) == list:
                for list_value in node[key]:
                    nquads.append(f'uid(u) <{node_type}.{key}> {list_value} .')
            else:
                nquad_key = key if key == 'dgraph.type' else f'{node_type}.{key}'
                nquads.append(f'uid(u) <{nquad_key}> {node[key]} .')

        mutation = transaction.create_mutation(set_nquads="\n".join(nquads))
        request = transaction.create_request(query=query, mutations=[mutation], commit_now=True)
        response = transaction.do_request(request)
    finally:
        transaction.discard()
    
    return response


def get_hash(*args):
    return sha256(bytes('.'.join(args), 'utf-8')).hexdigest()


def get_uid_from_response(response):
    if not response:
        print('Received invalid response in get_uid_from_response()')
        return None
    
    if len(response.uids.keys()) == 1:
        uid_key = next(iter(response.uids))
        return response.uids[uid_key]
    
    if not response.json:
        return None
    
    json_response = json.loads(response.json.decode('utf-8'))

    if 'node' not in json_response \
            or len(json_response['node']) != 1 \
            or 'uid' not in json_response['node'][0] \
            or len(json_response['node'][0]['uid']) < 1:
        return None
    
    return json_response['node'][0]['uid']


def create_node(client, node):
    transaction = client.txn()
    response = None

    try:
        response = transaction.mutate(set_obj=node, commit_now=True)
    except Exception as error:
        print('create_node() error: ', error)
    finally:
        transaction.discard()

    return get_uid_from_response(response)


def get_node_uid(client, node_type, code):
    if not code or len(code) < 1:
        return None

    if node_type not in _NODE_CACHE:
        _NODE_CACHE[node_type] = {}

    if code in _NODE_CACHE[node_type]:
        return _NODE_CACHE[node_type][code]

    _NODE_CACHE[node_type][code] = get_uid_from_response(upsert(
        client,
        node_type,
        'code',
        code,
        [],
    ))

    return _NODE_CACHE[node_type][code]


def get_transliteration_uids(client, node_type, code, transliterations):
    uids = []

    for tr in transliterations:
        value = tr.get('value')
        # uid = create_node(client, tr)

        for k in tr:
            if k == 'value':
                tr[k] = tr.get(k, '').replace('"', '\\"')
            tr[k] = f'"{tr[k]}"'

        uid = get_uid_from_response(upsert_bak(
            client,
            'Transliteration',
            'hash',
            get_hash(node_type, code, value),
            tr,
        ))

        if uid:
            uids.append(f'<{uid}>')

    return uids


def transliteration_to_str(tr: Union[dict, list]) -> str:
    if type(tr) == list:
        return u', '.join([transliteration_to_str(t) for t in tr])

    return f'{tr["Transliteration.value"]} ({tr["Transliteration.hash"][:6]})'


def add_transliteration_po_pair(predicate: str, tr: dict, po_pairs: List[tuple]):
    value = tr.get('value', '').replace('"', '\\"')
    value = f'"{value}"'

    po_pairs.append((predicate, value))


def load_alphabets(client, alphabets):
    print('')
    print(f'Importing {len(alphabets):,} alphabets...')

    for alphabet in alphabets:
        script_uid = get_node_uid(client, 'Script', alphabet.get('script_code'))
        
        po_pairs = [
            ('characters', f'"{alphabet.get("letters", "")}"'),
            ('script', f'<{script_uid}>' if script_uid else '""'),
        ]

        # Get UIDs for each transliteration.
        name_trs = []
        for name in alphabet.get('names'):
            if name and name.get('lang_code'):
                name_trs.append(name)

        name_tr_uids = get_transliteration_uids(
            client,
            'Alphabet',
            alphabet.get('code'),
            name_trs,
        )

        for uid in name_tr_uids:
            po_pairs.append(('names', uid))

        upsert(client, 'Alphabet', 'code', alphabet.get('code'), po_pairs)

    # Verify import
    check_response = client.txn(read_only=True).query(
        """{
            alphabets(func: type(Alphabet)) {
                Alphabet.code
                Alphabet.names {
                    expand(_all_)
                }
            }
        }"""
    )

    check_json = json.loads(check_response.json.decode('utf-8'))
    print(f'Total alphabets in graph: {len(check_json["alphabets"]):,}')

    for alphabet in check_json['alphabets']:
        names = transliteration_to_str(alphabet.get('Alphabet.names', []))
        print(f' - {alphabet.get("Alphabet.code")}: {names}')


def load_expressions(client, expressions):
    print('')
    print(f'Importing {len(expressions):,} expressions...')

    for expression in expressions:
        if bool(skip_expression_titles & set([t.get('value') for t in expression.get('titles')])):
            continue

        uuid = expression.get('uuid')
        titles = get_transliteration_uids(client, 'Expression', uuid, expression.get('titles'))
        po_pairs = [
            ('type', f'"{expression.get("type")}"'),
        ]

        for uid in titles:
            po_pairs.append(('titles', uid))
        
        for lang_code in expression.get('languages', []):
            uid = get_node_uid(client, 'Language', lang_code)
            po_pairs.append(('languages', f'<{uid}>'))

        if expression.get("part_of_speech"):
            po_pairs.append(('partOfSpeech', f'"{expression.get("part_of_speech")}"'))
        
        # Get transliterations for literal/practical translations and meanings.
        for field in ('literal_translation', 'practical_translation', 'meaning'):
            uids = get_transliteration_uids(client, f'Expression.{field}', uuid, expression.get(field))

            for uid in uids:
                po_pairs.append((f'{field.replace("_t", "T")}s', uid))

        # TODO: tags

        upsert(client, 'Expression', 'uuid', uuid, po_pairs)
    
    # Verify import
    check_response = client.txn(read_only=True).query(
        """{
            expressions(func: type(Expression)) {
                Expression.uuid
                Expression.practicalTranslations {
                    expand(_all_)
                }
                Expression.languages {
                    expand(_all_)
                }
                Expression.titles {
                    expand(_all_)
                }
            }
        }"""
    )

    check_json = json.loads(check_response.json.decode('utf-8'))
    print(f'Total Expressions in graph: {len(check_json["expressions"]):,}')

    for ex in check_json['expressions']:
        transliterations = transliteration_to_str(ex.get('Expression.titles', []))
        translations = transliteration_to_str(ex.get('Expression.practicalTranslations', []))
        print(f' - {ex.get("Expression.uuid")[:6]}: {transliterations} == {translations}')


def load_languages(client, languages):
    print('')
    print(f'Importing {len(languages):,} languages...')

    for language in languages:
        po_pairs = []
        transliterations = get_transliteration_uids(
            client,
            'Language',
            language.get('code'),
            language.get('names'),
        )

        for uid in transliterations:
            po_pairs.append(('names', uid))

        parent_uid = get_node_uid(client, 'Language', language.get('parent_code'))
        
        if parent_uid:
            po_pairs.append(('parent', f'<{parent_uid}>'))
        
        upsert(client, 'Language', 'code', language.get('code'), po_pairs)
    
    # Verify import
    check_response = client.txn(read_only=True).query(
        """{
            languages(func: type(Language)) {
                Language.code
                Language.names {
                    expand(_all_)
                }
            }
        }"""
    )

    check_json = json.loads(check_response.json.decode('utf-8'))
    print(f'Total languages in graph: {len(check_json["languages"]):,}')

    for lang in check_json['languages']:
        transliterations = transliteration_to_str(lang.get("Language.names", []))
        print(f' - {lang.get("Language.code")}: {transliterations}')


def load_all(data):
    result = True
    stub, client = open_graph_connection()

    try:
        load_alphabets(client, data.get('alphabets', []))
        load_expressions(client, data.get('expressions', []))
        load_languages(client, data.get('languages', []))
    except Exception as error:
        result = False
        print(f'TODO: handle error type "{type(error)}".')
        print(error)
    finally:
        close_graph_connection(stub, client)

    return result
