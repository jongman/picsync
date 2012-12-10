#!/usr/bin/python
# -*- coding: utf-8 -*-
from argparse import ArgumentParser
from os import path
from lib.index import Index
from lib.config import should_index
from lib.fs_utils import flat_walk, md5, stat

def get_parser():
    parser = ArgumentParser()
    parser.add_argument('archive_dir', help='Home directory.')
    parser.add_argument('--dry-run', help='Do not change the index.',
                        default=False, action='store_true')
    parser.add_argument('--allow-duplicate', help='Add duplicates to the index too.',
                        default=False, action='store_true')
    return parser

def classify_files(archive_dir, by_path):
    unchanged, changed, new, seen = set(), set(), set(), set()

    all_files = filter(should_index, flat_walk(archive_dir)) 
    for file in all_files:
        relpath = path.relpath(file, archive_dir)
        seen.add(relpath)
        if relpath not in by_path:
            new.add(relpath)
        else:
            mtime, size = stat(file)
            if (by_path[relpath]['mtime'] == mtime and
                by_path[relpath]['filesize'] == size):
                unchanged.add(relpath)
            else:
                changed.add(relpath)

    missing = set()
    for pth in by_path:
        if pth not in seen:
            missing.add(pth)

    return unchanged, changed, new, missing

def detect_moved_files(args, new, missing, by_path):
    missing_md5 = {by_path[missing_path]['md5']: missing_path
                   for missing_path in missing}
    matched_new = set()
    moved = {}
    for new_path in new:
        hash = md5(path.join(args.archive_dir, new_path))
        if hash in missing_md5:
            from_path = missing_md5[hash]
            to_path = new_path
            moved[from_path] = to_path

            matched_new.add(to_path)

            del missing_md5[hash]

    new = {pth for pth in new if pth not in matched_new}
    missing = {pth for pth in missing if pth not in moved}

    return new, missing, moved

def update_changed_files(args, changed, by_path, index):
    for pth in changed:
        print 'changed', pth

        full_path = path.join(args.archive_dir, pth)
        hash = md5(full_path)
        mtime, size = stat(full_path)

        rowid = by_path[pth]['rowid']

        index.set(rowid, md5=hash, mtime=mtime, filesize=size)

def update_moved_files(args, moved, by_path, index):
    for from_path, to_path in moved.items():
        print 'moved', from_path, '=>', to_path

        full_path = path.join(args.archive_dir, to_path)
        mtime, size = stat(full_path)

        rowid = by_path[from_path]['rowid']
        index.set(rowid, path=to_path, mtime=mtime)

def add_new_files(args, new, index):
    for new_path in new:

        full_path = path.join(args.archive_dir, new_path)
        hash = md5(full_path)
        mtime, size = stat(full_path)

        already = index.get(md5=hash)
        if already:
            if args.allow_duplicate:
                print 'duplicate-new', new_path, 'with', already[0]['path']
            else:
                print 'duplicate-ignore', new_path
                continue
        else:
            print 'new', new_path

        index.add(origin=full_path, path=new_path, md5=hash, mtime=mtime,
                  filesize=size)

def remove_missing_files(missing, by_path, index):
    for missing_path in missing:
        print 'delete', missing_path

        rowid = by_path[missing_path]['rowid']
        index.erase(rowid)

def update_index(args, index):
    # use cases:
    # 1. updated file, in place (update md5 and size, mtime)
    # 2. moved file (update index)
    # 3. new file (add to index)
    # 4. deleted file (delete from index)

    indexed_files = index.get()
    by_path = {file['path']: file for file in indexed_files}

    # A. identify new/changed/unchanged/missing paths
    unchanged, changed, new, missing = classify_files(args.archive_dir, by_path)

    # B. detect moved files
    new, missing, moved = detect_moved_files(args, new, missing, by_path)

    # C. update index 
    update_changed_files(args, changed, by_path, index)
    update_moved_files(args, moved, by_path, index)
    add_new_files(args, new, index)
    remove_missing_files(missing, by_path, index)

def main():
    args = get_parser().parse_args()
    home = args.archive_dir

    with Index(path.join(home, 'pictures.db'), autocommit=not args.dry_run) as index:
        update_index(args, index)

if __name__ == '__main__':
    main()

