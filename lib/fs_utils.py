from os import path
from os import walk as _walk
from os import stat as _stat
from decorators import memoize
from minimal_exif_reader import MinimalExifReader
from hachoir_parser import createParser
from hachoir_metadata import extractMetadata
from subprocess import check_output
import sys
import hashlib
import shutil
import unicodedata

FS_ENC = sys.getfilesystemencoding()

def decode_path(str): 
    return str.decode(FS_ENC)

def encode_path(str): 
    if sys.platform != 'darwin': str = unicodedata.normalize('NFC', str)
    return str.encode(FS_ENC)

def copy(src, dst):
    if path.isdir(encode_path(dst)):
        dst = path.join(dst, path.basename(src))
    shutil.copyfile(encode_path(src), encode_path(dst))

def move(src, dst): 
    shutil.move(encode_path(src), encode_path(dst))

def unicode_walk(root):
    for dirname, dirnames, files in _walk(encode_path(root)):
        yield (decode_path(dirname), 
               map(decode_path, dirnames),
               map(decode_path, files))

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
    fp = open(encode_path(file_path), "rb")
    while True:
        chunk = fp.read(CHUNK)
        if not chunk: break
        m.update(chunk)
    return m.hexdigest()

def stat(file_path):
    stat_result = _stat(encode_path(file_path))
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


def read_exif(file_path):
    exif = {}
    lines = check_output(['ExifTool', file_path]).splitlines()
    for line in lines:
        toks = line.split()
        if ':' in toks:
            colon = toks.index(':')
            key = ' '.join(toks[:colon])
            exif[key] = ' '.join(toks[colon+1:])
    return exif


def get_exif_date(file_path):
    exif = read_exif(file_path)
    ACCEPTABLE_KEYS = ['Date/Time Original', 
                       'Creation Date', 
                       'File Modification Date/Time']

    for KEY in ACCEPTABLE_KEYS:
        if KEY in exif:
            return exif[KEY].split()[0].replace(':', '-')

    return None

def get_jpg_date(file_path):
    try:
        dt = MinimalExifReader(encode_path(file_path)).dateTimeOriginal()
        assert dt
        ret = "-".join(dt.split()[0].split(":"))
        if (len(ret) != 10 or 
            ret == '0000-00-00' or 
            int(ret.split('-')[0] < 2000)): return None
        return ret
    except:
        return None

def get_date(file_path):
    try:
        if file_path.lower().endswith('.jpg'):
            dt = get_jpg_date(file_path)
            if dt: return dt
        return get_exif_date(file_path)
    except KeyboardInterrupt:
        raise
    except:
        pass

    return None
