import sqlite3
from collections import OrderedDict

class Index(object):
    def __init__(self, filename, autocommit=True):
        self.filename = filename
        self.autocommit = autocommit
        self.db = None

    def connect(self):
        self.db = sqlite3.connect(self.filename)
        self.create_table()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        if self.autocommit: self.commit()
        self.db.close()

    def create_table(self):
        c = self.db.cursor()
        c.execute("""
                  CREATE TABLE IF NOT EXISTS pictures (
                    date TEXT,
                    path TEXT,
                    md5 TEXT,
                    md5_original TEXT,
                    mtime INTEGER,
                    filesize INTEGER,
                    origin TEXT,
                    smugmug_id INTEGER,
                    smugmug_key TEXT,
                    smugmug_album_id INTEGER,
                    smugmug_album_key TEXT,
                    smugmug_error TEXT
                 );""")
        c.execute("CREATE INDEX IF NOT EXISTS path_index ON pictures (path);")
        c.execute("CREATE INDEX IF NOT EXISTS md5_index ON pictures (md5);")
        self.commit()

    def add(self, origin, path, md5, mtime, filesize, date, md5_original=None):
        self.assert_context_manager()
        if md5_original is None: md5_original = md5

        c = self.db.cursor()
        c.execute("INSERT INTO pictures (origin, path, md5, md5_original, mtime, filesize, date) "
                  "VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (origin, path, md5, md5_original, mtime, filesize, date))
        if self.autocommit: self.commit()

    def get(self, **kwargs):
        self.assert_context_manager()

        conditions = OrderedDict(kwargs.items())

        if conditions:
            # clauses = ["%s=?" % key for key in conditions]
            clauses = []
            values = []
            for key, val in conditions.items():
                if val is None:
                    clauses.append('%s is null' % key)
                else:
                    clauses.append('%s=?' % key)
                    values.append(val)
            where = 'WHERE ' + ' AND '.join(clauses)
        else:
            where = ''
            values = []

        query = 'SELECT ROWID, * FROM pictures %s;' % where
        return self._get(query, tuple(values))

    def get_distinct(self, column):
        query = "SELECT DISTINCT %s FROM pictures;" % column
        return set(row[column] for row in self._get(query, []))

    def _get(self, query, values):
        self.assert_context_manager()

        c = self.db.cursor()
        c.execute(query, values)
        description = [col[0] for col in c.description]
        return [dict(zip(description, row)) for row in c.fetchall()]

    def set(self, rowid, **kwargs):
        self.assert_context_manager()

        args = OrderedDict(kwargs.items())
        set = ', '.join(['%s=?' % key for key in args])
        query = "UPDATE pictures SET %s WHERE ROWID=%d;" % (set, int(rowid))
        c = self.db.cursor()
        c.execute(query, tuple(args.values()))
        if self.autocommit: self.commit()

    def erase(self, rowid):
        self.assert_context_manager()

        query = "DELETE FROM pictures WHERE rowid=?;"
        self.db.cursor().execute(query, (rowid,))
        if self.autocommit: self.commit()

    def commit(self):
        self.assert_context_manager()

        self.db.commit()

    def assert_context_manager(self):
        if not self.db:
            raise Exception('Index should be used as a context manager.')

