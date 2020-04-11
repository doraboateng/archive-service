import mysql.connector
from mysql.connector import Error

definition_types = {
    0: 'word',
    5: 'name',
    10: 'expression',
    30: 'story',
}

parts_of_speech = {
    'adj': 'adjective',
    'adv': 'adverb',
    'n': 'noun',
    'v': 'verb',
}


def utf_encode(data):
    return data
    # return data.encode('utf-8') if data else data


def close_db_connection(conn, cursor):
    if conn and conn.is_connected():
        if cursor:
            cursor.close()
        
        conn.close()


def open_db_connection():
    connection = None
    cursor = None

    try:
        connection = mysql.connector.connect(
            host='dora-temp-maria',
            database='temp',
            user='root',
            password='temp',
        )

        cursor = connection.cursor()

        return connection, cursor

    except Error as err:
        print('Could not connect to MariaDB:', err)

    close_db_connection(connection, cursor)
    
    return None, None


def get_transliteration(value = None, lang = None, script = None):
    if not value:
        return None
    
    return {
        'value': utf_encode(value),
        'lang_code': lang.lower() if lang and len(lang) > 0 else None,
        'script_code': script.lower() if script and len(script) > 0 else None,
    }


def fetch_alphabet_records(cursor):
    alphabets = []
    cursor.execute('SELECT id, code, script_code, letters FROM alphabets')
    alphabet_records = cursor.fetchall()
    print(f'Total alphabets in MariaDB: {cursor.rowcount:,}')

    for alphabet_id, alphabet_code, script_code, letters in alphabet_records:
        alphabet = {
            'code': alphabet_code.lower(),
            'script_code': script_code.lower() if script_code else None,
            'names': [],
            'letters': utf_encode(letters),
        }

        # Pull transliterations
        cursor.execute(
            f'SELECT z.language, z.transliteration FROM alphabets AS a '
            f'LEFT JOIN transliterations AS z ON z.parent_id = a.id '
            f'WHERE z.parent_id = {alphabet_id} '
            f"AND z.parent_type = 'App\\\\Models\\\\Alphabet'"
        )

        transliteration_records = cursor.fetchall()

        for lang, transliteration in transliteration_records:
            tr = get_transliteration(transliteration, lang)

            if tr is not None:
                alphabet['names'].append(tr)

        alphabets.append(alphabet)
    
    return alphabets


def fetch_expression_records(cursor):
    expressions = []

    cursor.execute('SELECT id, type, sub_type, main_language_code FROM definitions')
    definition_records = cursor.fetchall()
    print(f'Total expressions in MariaDB: {cursor.rowcount:,}')

    for def_id, def_type, def_sub_type, def_lang in definition_records:
        expression = {
            'type': definition_types.get(def_type, def_type),
            'titles': [],
            'languages': [],
            'part_of_speech': parts_of_speech.get(def_sub_type, None),
            'noun_type': None,
            'lexeme': None,
            'literal_translation': [],
            'practical_translation': [],
            'meaning': [],
            'tags': [],
            'related': [],
            'references': [],
        }

        expressions.append(expression)

        # Pull titles for definition.
        cursor.execute(
            f'SELECT t.id, t.title, a.script_code FROM definition_titles AS t '
            f'LEFT JOIN alphabets AS a ON a.id = t.alphabet_id '
            f'WHERE t.definition_id = {def_id}'
        )

        title_records = cursor.fetchall()

        for title_id, title, script_code in title_records:
            tr = get_transliteration(title, None, script_code)

            if tr is not None:
                expression['titles'].append(tr)

            # Pull transliterations
            cursor.execute(
                f'SELECT z.language, z.transliteration FROM definition_titles AS d '
                f'LEFT JOIN transliterations AS z ON z.parent_id = d.id '
                f'WHERE z.parent_id = {title_id} '
                f"AND z.parent_type = 'App\\\\Models\\\\DefinitionTitle'"
            )

            transliteration_records = cursor.fetchall()

            for lang, transliteration in transliteration_records:
                tr = get_transliteration(transliteration, lang)

                if tr is not None:
                    expression['titles'].append(tr)

        # Pull languages for definition.
        cursor.execute(
            f'SELECT l.code FROM definition_language AS p '
            f'LEFT JOIN languages AS l ON l.id = p.language_id '
            f'WHERE p.definition_id = {def_id}'
        )

        language_records = cursor.fetchall()
        expression['languages'] += [lang[0] for lang in language_records]

        # TODO: tags

        # Pull translations for definition.
        cursor.execute(
            f'SELECT language, practical, literal, meaning '
            f'FROM translations '
            f'WHERE definition_id = {def_id}'
        )

        translation_records = cursor.fetchall()

        for tr_lang, tr_practical, tr_literal, tr_meaning in translation_records:
            tr = get_transliteration(tr_literal, tr_lang)
            if tr is not None:
                expression['literal_translation'].append(tr)
            
            tr = get_transliteration(tr_practical, tr_lang)
            if tr is not None:
                expression['practical_translation'].append(tr)
            
            tr = get_transliteration(tr_meaning, tr_lang)
            if tr is not None:
                expression['meaning'].append(tr)
    
    return expressions


def fetch_language_records(cursor):
    languages = []
    cursor.execute('SELECT code, parent_code, name, alt_names FROM languages')
    language_records = cursor.fetchall()
    print(f'Total languages in MariaDB: {cursor.rowcount:,}')

    for lang_code, parent_code, name, alt_names  in language_records:
        language = {
            'code': lang_code,
            'parent_code': parent_code or None,
            'names': [],
        }

        names = [name] + (alt_names or '').split(',')

        for name in names:
            name = utf_encode(name).strip()

            if len(name) > 0:
                language['names'].append({
                    'value': name,
                    'lang_code': None,
                    'script_code': None,
                })

        languages.append(language)
    
    return languages


def fetch_all():
    connection, cursor = open_db_connection()

    if not connection:
        return None
    
    result = None
    
    try:
        result = {
            'alphabets': fetch_alphabet_records(cursor),
            'expressions': fetch_expression_records(cursor),
            'languages': fetch_language_records(cursor),
            'stories': [],
        }
    except Exception as error:
        print('Error while fetching data from MariaDB:', error)
    
    close_db_connection(connection, cursor)

    return result
