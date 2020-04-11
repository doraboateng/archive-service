import json
import pydgraph


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


def upsert(client, node, selector):
    transaction = client.txn()
    response = None

    try:
        query = '{ u as node(func: ' + selector + ') }'
        nquad = []

        for key in node:
            if key == 'uid':
                continue
            
            nquad.append(f'uid(u) <{key}> "{node[key]}" .')
        
        mutation = transaction.create_mutation(set_nquads="\n".join(nquad))
        request = transaction.create_request(query=query, mutations=[mutation], commit_now=True)
        response = transaction.do_request(request)
    finally:
        transaction.discard()
    
    return response


def load_alphabets(client, alphabets):
    print(f'Importing {len(alphabets)} alphabets...')

    for alphabet in alphabets:
        transaction = client.txn()
        code = alphabet.get('code')
        node = {
            'uid': f'_:{code}',
            'dgraph.type': 'Alphabet',
            'Alphabet.code': code
        }

        for name in alphabet.get('names'):
            if name and name.get('lang_code'):
                node[f'Alphabet.name@{name["lang_code"]}'] = name['value']

        try:
            selector = 'eq(Alphabet.code, "' + code + '")'
            upsert(client, node, selector)
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


def load_languages(client, languages):
    print(f'Importing {len(languages)} languages...')


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
