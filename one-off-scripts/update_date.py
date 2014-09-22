from os import path
from lib import index
import sys
import re


DATE_RE = re.compile(r'\d{4}-\d{2}-\d{2}')

match = 0
with index.Index(sys.argv[1]) as index:
    images = index.get(date=None)
    for img in images:
        date = img['path'].split('/')[1].split()[0][:10]
        if not DATE_RE.match(date):
            continue
        index.set(img['rowid'], date=date)
        print img['path'].encode('utf-8'), date


