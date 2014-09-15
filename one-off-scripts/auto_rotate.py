from lib.index import Index
from lib.image_utils import autorotate
from lib.fs_utils import stat, md5

with open('errors.txt', 'w') as errors:
    with Index('/Volumes/Passport/pictures-backup/pictures.db', autocommit=True) as index:
        all = index.get()

        for i, a in enumerate(sorted(all, key=lambda p: p['path'])):
            if i % 100 == 99: print i, '/', len(all), '..', a['path']
            pth = '/Volumes/Passport/pictures-backup/' + a['path']
            try:
                if autorotate(pth):
                    mtime, size = stat(pth)
                    hash = md5(pth)
                    index.set(a['rowid'], mtime=mtime, filesize=size, md5=hash)
                    print 'updated', pth
            except:
                errors.write('%s\n' % pth.encode('utf-8'))




