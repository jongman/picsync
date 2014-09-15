from jpegtran import JPEGImage
from fs_utils import encode_path, copy
from subprocess import check_output, STDOUT

def autorotate(path):
    if path.split('.')[-1].lower() not in ('jpg', 'jpeg'):
        return False

    output = check_output(['jhead', encode_path(path)], stderr=STDOUT).splitlines()
    rotated = False
    for line in output:
        if line.startswith('Orientation'):
            rotated = True
            break

    if not rotated: return False

    copy(path, path + '.original')
    print check_output(['jhead', '-autorot', encode_path(path)])

    return True
