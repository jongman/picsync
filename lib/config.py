ACCEPTED_EXTENSIONS = ['avi', 'bmp', 'gif', 'jpg', 'mov', 'mpg', 'wmv']

def should_index(fn):
    return fn.split('.')[-1].lower() in ACCEPTED_EXTENSIONS
