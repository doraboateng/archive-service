"""
The 2017 format is a series of SQL scripts, 
"""
import json
import re
from os import DirEntry, scandir
from typing import List, Optional, Union


def list_files(directory: str, extension: str) -> Optional[DirEntry]:
    try:
        entries = scandir(directory)
    except FileNotFoundError as error:
        return print(str(error))

    files = []

    for entry in entries:
        if entry.is_file() and entry.name.endswith(f'.{extension}'):
            files.append(entry)
    
    return files if len(files) else None


def restore_BAK(directory: str) -> bool:
    file_entries = list_files(directory, 'json')

    if not file_entries:
        return False
    
    for entry in file_entries:
        with open(entry.path) as file_pointer:
            data = json.load(file_pointer)

            print(entry.name, node_type_re, node_type_re.group(1))

    return True



def restore(backup_filename: str) -> bool:
    print(f'Restoring "{backup_filename}"...')

    return False


if __name__ == '__main__':
    from sys import argv

    if len(argv) != 2:
        print('Usage: python restore/2017.py <FILENAME>')

        exit(1)
    
    success = restore(argv[1])

    exit(0 if success else 1)
