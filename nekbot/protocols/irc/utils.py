

def add_sharp(name):
    if not name.startswith('#'):
        return '#' + name
    return name


def remove_sharp(name):
    if name.startswith('#'):
        name = name[1:]
    return name