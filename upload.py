#!/usr/bin/python
# -*- coding: utf-8 -*-
from argparse import ArgumentParser
from lib.index import Index
from lib.smugmug import API, SmugmugException
from lib.logging_utils import setup_logging
from lib.decorators import memoize
from lib.fs_utils import read_exif
from ConfigParser import ConfigParser
from os import path
import logging
import codecs
import locale
import sys
import re

setup_logging('upload.log')

# Wrap sys.stdout into a StreamWriter to allow writing unicode.
sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout) 

def get_parser():
    parser = ArgumentParser()
    parser.add_argument('archive_dir', help='Home directory.')
    parser.add_argument('--config', help='Path to config file.', default='config.ini')
    parser.add_argument('--move', default=False, action='store_true',
                        help='Check already-uploaded files and move to correct '
                        'album if required.')
    return parser

ALBUM_NAME_REGEXP = re.compile(r'\d{4}-\d{2}-\d{2}')

def get_subcategory_album_name(path):
    chunks = path.split('/')
    year_month = chunks[0]
    album_name = chunks[1][:10]
    if not ALBUM_NAME_REGEXP.match(album_name):
        album_name = 'Uncategorized'
    return year_month, album_name

def get_required_albums(index):
    'Returns a list of ("subcategory name", "album name")'
    albums = set()
    for date in index.get_distinct('date'):
        if date is None:
            albums.add(('Uncategorized', 'Uncategorized'))
        else:
            albums.add((date[:7], date))
    return sorted(albums)

def create_required_albums(api, category, required_albums):
    categories = api.get_categories()
    if category not in categories:
        raise Exception('Cannot find category %s', category)
    cid = categories[category]
    subcategories = api.get_subcategories(cid)

    existing_albums = {(album['Category']['id'], 
                        album['SubCategory']['id'],
                        album['Title']): {'id': album['id'],
                                          'Key': album['Key']}
                       for album in api.get_albums()
                       if 'SubCategory' in album}

    for subcategory, album in required_albums:
        if subcategory not in subcategories:
            logging.info('Creating subcategory %s ..', subcategory)
            sid = api.create_subcategory(cid, subcategory)
            subcategories[subcategory] = sid
        else:
            sid = subcategories[subcategory]

        if (cid, sid, album) not in existing_albums:
            logging.info('Creating album %s/%s/%s ..' % (category,
                                                         subcategory,
                                                         album))
            key, id = api.create_album(album.encode('utf-8'), cid, 
                                       {'Public': False,
                                        'SmugSearchable': False,
                                        'SubCategoryID': sid})
            existing_albums[(cid, sid, album)] = {'Key': key,
                                                  'id': id}

    subcategory_reverse_map = {v: k for k, v in subcategories.items()}
    return {(subcategory_reverse_map[sid], album): val
            for (cat_id, sid, album), val in existing_albums.items()
            if cid == cat_id}


def retry(job, times):
    for i in xrange(times):
        try:
            return job()
        except KeyboardInterrupt:
            raise
        except Exception as e:
            pass
    raise e


def has_non_standard_colorspace(path):
    """ Returns if colorspace is not sRGB:
        
        Smugmug converts all uploaded photos to sRGB. Therefore these photos should not 
        be checked using MD5 checksum."""
    if not path.lower().endswith('.jpg'): return False
    exif = read_exif(path)
    return 'sRGB' not in exif.get('Profile Description', 'sRGB')


def upload_file(api, path, filesize, md5, album_id):
    ret = api.upload(path, album_id, filesize, md5, hidden=True)
    if ret['stat'] != 'ok':
        logging.info('FAILED to upload %s: result JSON %s',
                     path, str(ret))
        return False

    info = api.get_image_info(ret['Image']['id'], ret['Image']['Key'])
    if info['Image']['MD5Sum'] != md5:
        logging.info('Uploaded file is corrupt! Expected md5: %s Got md5: %s', 
                     md5, info['Image']['MD5Sum'])
        logging.info('Path: %s', path)
        if not has_non_standard_colorspace(path):
            api.delete_image(ret['Image']['id'])
            return False
        logging.info('However, original picture has non-sRGB colorspace; carrying on.')

    return ret['Image']



def upload_file_retry(api, path, filesize, md5, album_id, tries=3):
    logging.info('Uploading file %s to album %d..', path, album_id)
    exception = None
    ret = None
    while tries > 0:
        tries -= 1
        try:
            ret = upload_file(api, path, filesize, md5, album_id)
            if ret: return ret
        except Exception as e:
            exception = e

    if exception: raise exception
    return False

    
def upload(home, index, api, to_upload, albums):
    total_size = sum(img['filesize'] for img in to_upload)
    logging.info('%d files will be uploaded.' % len(to_upload))

    for idx, img in enumerate(to_upload):
        subcategory, album = get_subcategory_album_name(img['path'])
        album_info = albums[(subcategory, album)]
        logging.info('Uploading %s (%dkb).. (#%d/%d)', img['path'],
                     img['filesize'] / 1024, 
                     idx+1,
                     len(to_upload))
        image_info = upload_file_retry(api, path.join(home, img['path']), 
                                       img['filesize'], img['md5'], album_info['id'])
        if image_info:
            logging.info('Uploaded %s to image id: %d image key: %s',
                         img['path'], image_info['id'], image_info['Key'])
            index.set(img['rowid'], 
                      smugmug_id=image_info['id'],
                      smugmug_key=image_info['Key'],
                      smugmug_album_id=album_info['id'],
                      smugmug_album_key=album_info['Key'])
        else:
            logging.info('failed to upload image %s after repeated tries.',
                         img['path'])
            index.set(img['rowid'], smugmug_error='Failed to upload')


def main():
    args = get_parser().parse_args()

    cp = ConfigParser()
    cp.readfp(open(args.config))
    home = args.archive_dir

    default_category = cp.get('Smugmug', 'DEFAULT_CATEGORY')
    api = API(cp.get('Smugmug', 'APIKEY'), cp.get('Smugmug', 'USERID'), cp.get('Smugmug', 'PASSWORD'))
    logging.info('Logging in..')
    api.login()

    try:
        with Index(path.join(home, 'pictures.db')) as index:
            logging.info('Creating required albums ..')
            required_albums = get_required_albums(index)
            albums = create_required_albums(api, default_category, required_albums)
            images = index.get(smugmug_id=None)
            images.sort(key=lambda img: img['date'])
            images.reverse()
            images = [img for img in images
                      if img['smugmug_error'] is None]
            upload(home, index, api, images, albums)


    except SmugmugException as e:
        logging.critical('SmugmugException: %s', str(e.response))
        

if __name__ == '__main__':
    main()

