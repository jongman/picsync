from lib.index import Index
from collections import Counter
from os import path

STRIP = [
    '//media/jongman/f47c2fa1-64ff-4f26-8f1a-3b11633fe147/pictures/',
    '/home/jongman/portable/pictures-backup/',
    '/media/data/pictures/'
]

with Index('/Volumes/Passport/pictures-backup/pictures.db', autocommit=True) as index:
    all = index.get()
    for a in all:
        if a['path'].startswith('/'):
            for s in STRIP:
                if a['path'].startswith(s):
                    change_to = a['path'][len(s):]
                    print a['path'].encode('utf-8'), '=>', change_to.encode('utf-8')
                    index.set(a['rowid'], path=change_to)
                    break
