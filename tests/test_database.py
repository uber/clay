from __future__ import absolute_import
import webtest.lint
import webtest
import threading
import os

os.environ['CLAY_CONFIG'] = 'config.json'

from clay import config, database
log = config.get_logger('clay.tests.database')


def test_database_cursor():
    with database.read as dbread:
        cur = dbread.cursor()
        cur.close()


def test_database_create_schema():
    with database.write as dbwrite:
        cur = dbwrite.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY NOT NULL,
                email TEXT NOT NULL
            )''')
        cur.execute('INSERT INTO users(email) VALUES("test@uber.com")')
        cur.close()
        dbwrite.commit()

    with database.read as dbread:
        cur = dbread.cursor()
        cur.execute('SELECT * FROM users WHERE id=1')
        assert cur.fetchone() == (1, 'test@uber.com')
        cur.close()


def test_database_threads():
    test_database_create_schema()

    def dbthread(num):
        with database.write as dbwrite:
            cur = dbwrite.cursor()
            cur.execute('INSERT INTO users(email) VALUES(?)', (str(num),))
            cur.close()
            dbwrite.commit()

        with database.read as dbread:
            cur = dbread.cursor()
            cur.execute('SELECT COUNT(*) FROM users')
            assert cur.fetchone()[0] > 1
            cur.close()

    threads = []
    for i in xrange(64):
        t = threading.Thread(target=dbthread, args=(i,))
        t.setDaemon(True)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()
