from lib import index
from json import load

crawled = load(open('images_crawled.json'))
by_md5 = {img['MD5Sum']: img for img in crawled}

match = 0
with index.Index('/Volumes/Passport/pictures-backup/pictures.db') as index:
    images = index.get()
    for img in images:
        if img['md5'] in by_md5:
            in_smug = by_md5[img['md5']]
            print img['md5'], img['path'].encode('utf-8')
            keyval = {'smugmug_id': in_smug['id']}
            if 'Album' in in_smug:
                keyval['smugmug_album_id'] = in_smug['Album']['id']
                keyval['smugmug_album_key'] = in_smug['Album']['Key']
            index.set(img['rowid'], **keyval)
            match += 1

print match, 'matches out of', len(images)

