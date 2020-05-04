from .db import fetch_all
from .graph import load_all, reset


def sync():
    print('')
    print('Fetching data from MariaDB...')
    data = fetch_all()

    if not data:
        return 1
    
    # print('')
    # print('Resetting Dgraph...')
    # if not reset():
    #     return 1
    
    print('')
    print('Loading data into Dgraph...')
    if not load_all(data):
        return 1
    
    return 0


if __name__ == '__main__':
    exit(sync())
