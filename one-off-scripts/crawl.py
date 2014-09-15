from lib import smugmug
import json
from ConfigParser import ConfigParser

cp = ConfigParser()
cp.readfp(open('config.ini'))

api = smugmug.API(cp.get('Smugmug', 'APIKEY'),
                  cp.get('Smugmug', 'USERID'),
                  cp.get('Smugmug', 'PASSWORD'))
api.login()
albums = api.get_albums()
print len(albums), 'albums found'
images = []
for idx, album in enumerate(albums):
    print '#%d: %s ..' % (idx+1, album['Title'].encode('utf-8'))
    images += api.get_images(album['id'], album['Key'], {'Heavy': True})

open('images_crawled.json', 'w').write(json.dumps(images, indent=4))
