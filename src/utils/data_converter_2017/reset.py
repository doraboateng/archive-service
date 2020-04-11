from graph import reset as reset_graph


def reset():
    if not reset_graph():
        return 1
    
    return 0


if __name__ == '__main__':
    exit(reset())
