#!/usr/bin/python
# -*- coding: utf-8 -*-
from os import path
from fs_utils import flat_walk, md5, stat
from sys import argv
from index import Index

home = argv[1]
should_index = lambda fn: fn.split('.')[-1].lower in ('jpg', 'mov', 'avi')

with Index(path.join(home, 'pictures.db')) as index:

    for file in filter(should_index, flat_walk(home)):
        hash = md5(file)
        stat_result = stat(file)
        mtime = int(stat_result.st_mtime)
        size = stat_result.st_size
        pth = path.relpath(file, home)

        print 'indexing', pth, mtime, size

        index.add(path=pth, mtime=mtime, filesize=size, md5=md5)

    


