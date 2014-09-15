#!/usr/bin/python
# -*- coding: utf-8 -*-
from argparse import ArgumentParser
from lib.index import Index
from lib.smugmug import API, SmugmugException
from lib.logging_utils import setup_logging
from lib.decorators import memoize
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

def get_required_albums(images):
    'Returns a list of ("subcategory name", "album name")'
    albums = set()
    for img in images:
        assert img['path'][0] != '/'
        albums.add(get_subcategory_album_name(img['path']))
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
            logging.info('Listing images..')
            images = index.get()

            logging.info('Creating required albums ..')
            required_albums = get_required_albums(images)
            albums = create_required_albums(api, default_category, required_albums)
            # if args.move:
            #     check_existing(
            # upload(index, api)
    except SmugmugException as e:
        logging.critical('SmugmugException: %s', str(e.response))
        

if __name__ == '__main__':
    main()

