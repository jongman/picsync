#!/usr/bin/python
# -*- coding: utf-8 -*-
from os import path
from sys import argv
from lib.fs_utils import flat_walk, md5, stat
from lib.index import Index
from lib.config import should_index

home = argv[1]

with Index(path.join(home, 'pictures.db')) as index:
    all = flat_walk(home)

    for file in filter(should_index, all):
        hash = md5(file)
        mtime, size = stat(file)
        pth = path.relpath(file, home)

        print 'indexing', pth, mtime, size

        index.add(origin=file, path=pth, mtime=mtime, filesize=size, md5=hash)

    


