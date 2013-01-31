#!/usr/bin/python
# -*- coding: utf-8 -*-
from argparse import ArgumentParser
from collections import defaultdict
from os import path, makedirs
from lib.index import Index
from lib.config import should_index
from lib.fs_utils import unicode_walk, md5, stat, get_jpg_date, flat_walk, move

import codecs
import re
import locale
import sys

# Wrap sys.stdout into a StreamWriter to allow writing unicode.
sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout) 

def get_parser():
    parser = ArgumentParser()
    parser.add_argument('from_dir', help='Directory to import from.')
    parser.add_argument('to_dir', help='Import to. Should have pictures.db.')
    parser.add_argument('--dry-run', help="Don't do anything",
                        default=False, action='store_true')
    parser.add_argument('--directory-for-date',
                        help='Use directory name instead of detecting dates.',
                        default=False, action='store_true')
    parser.add_argument('--allow-duplicate-digits',
                        default=False, action='store_true')

    return parser

def get_digits(s):
    d = ''.join(ch for ch in s if ch.isdigit())
    if not d: return 0
    return int(d)

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
    by_dir = defaultdict(list)
    for file in paths:
        dir, base = path.split(file)
        by_dir[dir].append(base)

    for dir, files in by_dir.items():

        files.sort(key=get_digits)

        for a, b in zip(files, files[1:]):
            if get_digits(a) == get_digits(b) and not args.allow_duplicate_digits:
                print ('fail to import directory %s: duplicate digits with '
                       'file %s and %s.' % (dir, a, b))
                good = False

        recognized = [None for i in files]
        for i, f in enumerate(files):
            if f.lower().endswith('.jpg'):
                recognized[i] = get_jpg_date(path.join(dir, f))

        last_date = None
        for i in range(len(files)) + range(len(files)-1, -1, -1):
            if recognized[i] is None:
                recognized[i] = last_date
            else:
                last_date = recognized[i]

        if recognized.count(None) > 0:
            print ('fail to import directory %s: cannot recognize dates.' %
                   dir)

            # for rec, f in zip(recognized, files):
            #     if not rec:
            #         print path.join(dir, f)
            good = False

        for rec, f in zip(recognized, files):
            ret[path.join(dir, f)] = rec

    if not good: sys.exit(0)
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

def import_file(from_path, date, home, index):
    ym = date[:7]
    dir = path.join(home, ym, date)
    if not path.exists(dir):
        makedirs(dir)
    move(from_path, dir)
    to_path = path.join(dir, path.basename(from_path))
    mtime, size = stat(to_path)
    index.add(from_path, to_path, md5(to_path), mtime, size)

def main():
    args = get_parser().parse_args()

    to_import = filter(should_index, flat_walk(args.from_dir))
    dates = detect_dates(args, to_import)

    home = args.to_dir
    with Index(path.join(home, 'pictures.db'), autocommit=not args.dry_run) as index:
        to_import, duplicates = filter_duplicates(to_import, index)

        for duplicate, existing in sorted(duplicates.items()):
            print 'duplicate', duplicate, 'with', existing

        for imp in to_import:
            print 'import %s date %s' % (imp, dates[imp])
            import_file(imp, dates[imp], home, index)



if __name__ == '__main__':
    main()

