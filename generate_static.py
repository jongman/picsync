#!/usr/bin/python
# -*- coding: utf-8 -*-
from argparse import ArgumentParser
from lib.smugmug import API, SmugmugException
from lib.logging_utils import setup_logging
from lib.decorators import memoize
from ConfigParser import ConfigParser
from os import path, makedirs
from jinja2 import Template
import codecs
import locale
import logging
import shutil
import sys

setup_logging('generate_static.log')

# Wrap sys.stdout into a StreamWriter to allow writing unicode.
sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout) 

def album_matches(album_spec, album_info):
    chunks = album_spec.split('/')
    key = None
    if len(chunks) == 1: 
        key = [album_info['Title']]
    elif len(chunks) == 2: 
        key = [album_info['Category']['Name'], album_info['Title']] 
    elif len(chunks) == 3: 
        key = [album_info['Category']['Name'],
               album_info.get('SubCategory', {'Name': ''})['Name'],
               album_info['Title']] 
    return key == chunks


def generate_single(api, args):
    albums = [album for album in api.get_albums()
              if album_matches(args.album, album)]
    if len(albums) == 0:
        logging.error('No album matches pattern %s', args.album)
        return
    if len(albums) > 1:
        logging.error('More than one album matches pattern %s', args.album)
        for a in albums:
            logging.error('  Category %s SubCategory %s Title %s id %d Key %s',
                          a['Category']['Name'],
                          album_info.get('SubCategory', {'Name': ''})['Name'],
                          a['Title'],
                          a['id'],
                          a['Key'])
        return

    generate_album(api, albums[0]['id'], albums[0]['Key'], args.output_dir,
                   args.image_size, args.template_dir)

def generate_subcategory(api, args):
    albums = [album for album in api.get_albums()
              if album.get('SubCategory', {'Name': ''})['Name'] == args.subcategory]

    for album in albums:
        generate_album(api, album['id'], album['Key'], 
                       path.join(args.output_dir, album['Title']),
                       args.image_size, args.template_dir)


def generate_album(api, album_id, album_key, output_dir, image_size, template_dir):
    logging.info('Mirroring album %d/%s to %s ..', album_id, album_key,
                 output_dir)
    if not path.exists(output_dir):
        shutil.copytree(template_dir, output_dir)
    images = api.get_images(album_id, album_key, {'Heavy': True})
    images.sort(key=lambda img: img['FileName'])
    info = []

    for idx, img in enumerate(images[:20]):
        print img
        assert img['Format'] in ('JPG', 'PNG', 'MP4', 'MOV')
        filename = img[image_size + 'URL'].split('/')[-1]
        info.append({'Format': img['Format'],
                     'FileName': img['FileName'],
                     'Thumbnail': 'Thumbnail' + filename,
                     'Image': filename,
                     'Link': img['URL']})

        logging.info('Downloading image %s (#%d/%d)..', img['FileName'], idx+1,
                     len(images))

        if not path.exists(path.join(output_dir, filename)):
            api.download(img[image_size + 'URL'], path.join(output_dir, filename))
        if not path.exists(path.join(output_dir, 'Thumbnail' + filename)):
            api.download(img['ThumbURL'], path.join(output_dir, 'Thumbnail' + filename))
    
    logging.info('Finishing %s ..', output_dir)
    tmpl = Template(open(path.join(output_dir, 'template.html')).read())
    open(path.join(output_dir, 'index.html'), 'w').write(tmpl.render(images=info))


def get_parser():
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()

    parser.add_argument('--template-dir', default='static_gallery_template')
    parser.add_argument('--config', default='config.ini')
    parser.add_argument('--image-size', default='X2Large')

    parser_single = subparsers.add_parser('single')
    parser_single.add_argument('album')
    parser_single.add_argument('output_dir')
    parser_single.set_defaults(func=generate_single)
    
    parser_single = subparsers.add_parser('subcategory')
    parser_single.add_argument('subcategory')
    parser_single.add_argument('output_dir')
    parser_single.set_defaults(func=generate_subcategory)
    
    return parser

def main():
    args = get_parser().parse_args()

    cp = ConfigParser()
    cp.readfp(open(args.config))

    api = API(cp.get('Smugmug', 'APIKEY'), cp.get('Smugmug', 'USERID'), cp.get('Smugmug', 'PASSWORD'))
    logging.info('Logging in..')
    api.login()

    args.func(api, args)


if __name__ == '__main__':
    main()

