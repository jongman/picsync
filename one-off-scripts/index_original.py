from lib.index import Index
from lib.image_utils import autorotate
from lib.fs_utils import stat, md5
from os import path

with Index('/home/jongman/data/pictures-backup/pictures.db', autocommit=True) as index:
    all = index.get()

    for i, a in enumerate(sorted(all, key=lambda p: p['path'])):
        if i % 100 == 99: print i, '/', len(all), '..', a['path']
        pth = '/home/jongman/data/pictures-backup/' + a['path'] + '.original'
        if path.exists(pth) and a['md5_original'] is None:
            original_md5 = md5(pth)
            index.set(a['rowid'], md5_original=original_md5)
            print 'updated', pth




