import json
import pydgraph

_NODE_CACHE = {}


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
        print(f'TODO: handle error type "{type(error)}".')
        print(error)
    finally:
        close_graph_connection(stub, client)

    return result


def upsert(client, node_type, key_name, key_value, node = None):
    transaction = client.txn()
    response = None
    node = node or {}
    node[key_name] = f'"{key_value}"'
    node['uid'] = f'"_:{key_value}"'
    node['dgraph.type'] = f'"{node_type}"'

    try:
        selector = f'eq({node_type}.{key_name}, "{key_value}")'
        query = '{ u as node(func: ' + selector + ') { uid } }'
        nquad = []

        for key in node:
            if key == 'uid':
                continue
        
            if type(node[key]) == list:
                for list_value in node[key]:
                    nquad.append(f'uid(u) <{node_type}.{key}> {list_value} .')
            else:
                nquad_key = key if key == 'dgraph.type' else f'{node_type}.{key}'
                nquad.append(f'uid(u) <{nquad_key}> {node[key]} .')
        
        mutation = transaction.create_mutation(set_nquads="\n".join(nquad))
        request = transaction.create_request(query=query, mutations=[mutation], commit_now=True)
        response = transaction.do_request(request)
    finally:
        transaction.discard()
    
    return response


def get_uid_from_response(response):
    if not response:
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
    
    _NODE_CACHE[node_type][code] = None
    response = upsert(client, 'Script', 'code', code)

    _NODE_CACHE[node_type][code] = get_uid_from_response(response)
    
    return _NODE_CACHE[node_type][code]


def get_transliteration_uids(client, transliterations):
    uids = []

    for tr in transliterations:
        uid = create_node(tr)

        if uid:
            uids.append(uid)
    
    return uids


def load_alphabets(client, alphabets):
    print(f'Importing {len(alphabets)} alphabets...')

    for alphabet in alphabets:
        transaction = client.txn()
        code = alphabet.get('code')
        script_uid = get_node_uid(client, 'Script', alphabet.get('script_code'))
        node = {
            'characters': f'"{alphabet.get("letters", "")}"',
            'script': f'<{script_uid}>' if script_uid else None,
        }

        for name in alphabet.get('names'):
            if name and name.get('lang_code'):
                node[f'name@{name["lang_code"]}'] = f'"{name["value"]}"'

        try:
            upsert(client, 'Alphabet', 'code', code, node)
        finally:
            transaction.discard()
    
    # Check
    query = """{
        alphabets(func: type(Alphabet)) {
            Alphabet.code
            Alphabet.name@.
        }
    }"""
    response = client.txn(read_only=True).query(query)
    json_response = json.loads(response.json.decode('utf-8'))
    print(f'Total alphabets in graph: {len(json_response["alphabets"]):,}')

    for alphabet in json_response['alphabets']:
        print(f' - {alphabet.get("Alphabet.code")}: {u"".join([alphabet.get("Alphabet.name@.")])}')


def load_expressions(client, expressions):
    print(f'Importing {len(expressions)} expressions...')

    for expression in expressions:
        transaction = client.txn()
        expression_id = expression.get('id')
        node = {
            'type': f'"{expression.get("type")}"',
            # 'titles': get_transliteration_uids(expression.get('titles')),
            # 'languages': [],
            'partOfSpeech': None,
            'nounType': None,
            'lexeme': None,
        }

        for tr in expression.get('literal_translation'):
            node[f'literalTranslation@{tr["lang_code"]}'] = f'"{tr["value"]}"'
        
        for tr in expression.get('practical_translation'):
            node[f'practicalTranslation@{tr["lang_code"]}'] = f'"{tr["value"]}"'
        
        for tr in expression.get('meaning'):
            node[f'meaning@{tr["lang_code"]}'] = f'"{tr["value"]}"'
        
        # TODO: tags

        try:
            pass
            # upsert(client, 'Expression', 'id', expression_id, node)
        finally:
            transaction.discard()


def load_languages(client, languages):
    print(f'Importing {len(languages)} languages...')

    for language in languages:
        transaction = client.txn()
        code = language.get('code')
        node = {
            'alphabets': [],
            'names': get_transliteration_uids(client, language.get('names')),
            # 'isFamily': '"false"',
        }

        parent_uid = get_node_uid(client, 'Language', language.get('parent_code'))
        
        if parent_uid:
            node['parent'] = f'<{parent_uid}>'

        try:
            upsert(client, 'Language', 'code', code, node)
        finally:
            transaction.discard()
    
    # Check
    query = """{
        languages(func: type(Language)) {
            Language.code
            Language.names {
                value
            }
        }
    }"""
    response = client.txn(read_only=True).query(query)
    json_response = json.loads(response.json.decode('utf-8'))
    print(f'Total languages in graph: {len(json_response["languages"]):,}')

    for lang in json_response['languages']:
        print(f' - {lang.get("Language.code")}')


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
