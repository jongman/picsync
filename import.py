#!/usr/bin/python
# -*- coding: utf-8 -*-
from argparse import ArgumentParser
from collections import defaultdict
from os import path, makedirs
from lib.index import Index
from lib.config import should_index
from lib.fs_utils import (unicode_walk, md5, stat, get_date, flat_walk, move, copy)
from lib.image_utils import autorotate
from lib.logging_utils import setup_logging
import logging
import codecs
import re
import locale
import sys

setup_logging('import.log')

# Wrap sys.stdout into a StreamWriter to allow writing unicode.
sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout) 

def get_parser():
    parser = ArgumentParser()
    parser.add_argument('from_dir', help='Directory to import from.')
    parser.add_argument('to_dir', help='Import to. Should have pictures.db.')
    parser.add_argument('--dry-run', help="Don't do anything",
                        default=False, action='store_true')
    parser.add_argument('--move', help='Move, do not copy',
                        default=False, action='store_true')
    parser.add_argument('--directory-for-date',
                        help='Use directory name instead of detecting dates.',
                        default=False, action='store_true')
    parser.add_argument('--allow-duplicate-digits',
                        default=False, action='store_true')

    return parser

date_re = re.compile('^\d{4}-\d{2}-\d{2}$')

def detect_dates(args, paths):

    if args.directory_for_date:
        ret = {}
        for pth in paths:
            date_cand = path.basename(path.dirname(pth)).split()[0]
            assert date_re.match(date_cand)
            ret[pth] = date_cand
        return ret
        
    good = True

    ret = {}
    for processed, file in enumerate(paths):
        if processed % 100 == 99:
            logging.info('processing #%d/%d ..' % (processed+1, len(paths)))
        dt = get_date(file)
        if not dt:
            logging.error('Unable to detect date for file %s' % file)
            good = False
        else:
            ret[file] = dt

    if not good: 
        logging.error('Aborting because of above errors.')
        sys.exit(0)
    return ret

def filter_duplicates(to_import, index):
    duplicates, by_md5, new = {}, {}, []
    for f in to_import:
        hash = md5(f)
        existing = index.get(md5=hash)
        if existing:
            duplicates[f] = existing[0]['path']
        elif hash in by_md5:
            duplicates[f] = by_md5[hash]
        else:
            by_md5[hash] = f
            new.append(f)
    return new, duplicates

def import_file(from_path, date, home, index, dry_run, mv):
    ym = date[:7]
    dir = path.join(home, ym, date)
    to_path = path.join(dir, path.basename(from_path))
    rel_path = path.relpath(to_path, home)

    logging.info('importing %s to %s (date %s)' % (from_path, rel_path, date))
    if dry_run: return

    if not path.exists(dir):
        makedirs(dir)
    if mv:
        move(from_path, dir)
    else:
        copy(from_path, dir)

    if autorotate(to_path):
        logging.info('auto rotated %s' % to_path)
    
    mtime, size = stat(to_path)
    index.add(from_path, rel_path, md5(to_path), mtime, size, date)

def main():
    args = get_parser().parse_args()

    logging.info('searching for files to import ..')
    to_import = filter(should_index, flat_walk(args.from_dir))
    logging.info('found %d files.' % len(to_import))
    logging.info('detecting dates ..')
    dates = detect_dates(args, to_import)

    home = args.to_dir
    with Index(path.join(home, 'pictures.db'), autocommit=not args.dry_run) as index:
        to_import, duplicates = filter_duplicates(to_import, index)

        logging.info('%d duplicates, %d to be imported' % (len(duplicates),
                                                           len(to_import)))

        for imp in to_import:
            import_file(imp, dates[imp], home, index, args.dry_run, args.move)

if __name__ == '__main__':
    main()

