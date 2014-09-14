from jpegtran import JPEGImage
from shutil import copyfile

def autorotate(path):
    if path.split('.')[-1].lower() not in ('jpg', 'jpeg'):
        return False

    img = JPEGImage(path)
    if img.exif_orientation == 1: return False

    copyfile(path, path + '.original')
    img.exif_autotransform().save(path)
    return True
