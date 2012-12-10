from os import path
from os import walk as _walk
from os import stat as _stat
from decorators import memoize
from minimal_exif_reader import MinimalExifReader
from hachoir_parser import createParser
from hachoir_metadata import extractMetadata
import sys
import hashlib

FS_ENC = sys.getfilesystemencoding()

def _decode(str): return str.decode(FS_ENC)
def _encode(str): return str.encode(FS_ENC)

def unicode_walk(root):
    for dirname, dirnames, files in _walk(_encode(root)):
        yield (_decode(dirname), 
               map(_decode, dirnames),
               map(_decode, files))

def flat_walk(root):
    ret = []
    for dirname, __, files in unicode_walk(root):
        for f in files:
            ret.append(path.join(dirname, f))
    return ret

@memoize
def md5(file_path):
    m = hashlib.md5()
    CHUNK = 1024 * 1024 * 4
    fp = open(_encode(file_path), "rb")
    while True:
        chunk = fp.read(CHUNK)
        if not chunk: break
        m.update(chunk)
    return m.hexdigest()

def stat(file_path):
    stat_result = _stat(_encode(file_path))
    mtime = int(stat_result.st_mtime)
    size = stat_result.st_size
    return mtime, size

def get_creation_date(file_path):
    try:
        parser = createParser(file_path)
        metadata = extractMetadata(parser, 0.5)
        return metadata['creation_date'].strftime('%Y-%m-%d')
    except:
        return None

def get_jpg_date(file_path):
    try:
        dt = MinimalExifReader(_encode(file_path)).dateTimeOriginal()
        assert dt
        ret = "-".join(dt.split()[0].split(":"))
        if (len(ret) != 10 or 
            ret == '0000-00-00' or 
            int(ret.split('-')[0] < 2000)): return None
        return ret
    except:
        return None
