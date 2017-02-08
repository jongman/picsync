from os.path import split
ACCEPTED_EXTENSIONS = ['avi', 'bmp', 'gif', 'jpg', 'jpeg', 'mov', 'mpg', 'wmv', 'mp4',
                       'mts', 'png']

def should_index(fn):
    return (fn.split('.')[-1].lower() in ACCEPTED_EXTENSIONS 
            and split(fn)[1][0] != '.')
