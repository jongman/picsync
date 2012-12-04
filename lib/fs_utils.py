from os import path
from os import walk as _walk
from os import stat as _stat
from decorators import memoize
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

