from clay import config
import threading
import random

log = config.get_logger('clay.database')


class DatabaseContext(object):
    def __init__(self, servers, dbapi_name):
        '''
        Servers is a list of config dicts for connecting to postgres
        '''
        self.servers = servers

        self.tlocal = threading.local()
        self.tlocal.dbconn = None

        if not dbapi_name in ('psycopg2', 'MySQLdb', 'sqlite3'):
            raise NotImplementedError('Unsupported database module: %s' % dbapi_name)
        self.dbapi_name = dbapi_name
        self.dbapi = __import__(dbapi_name)

    def __enter__(self):
        server = random.choice(self.servers)
        conn = self.dbapi.connect(**server)
        self.tlocal.dbconn = conn
        return conn

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.tlocal.dbconn.close()
        self.tlocal.dbconn = None

        if exc_type is not None:
            raise
    
    def __str__(self):
        if self.dbconn is not None:
            return 'DatabaseContext %s %r (connected)' % (self.dbapi_name, self.servers)
        else:
            return 'DatabaseContext %s %r (not connected)' % (self.dbapi_name, self.servers)


read = DatabaseContext(config.get('database.read'), config.get('database.module'))
write = DatabaseContext(config.get('database.write'), config.get('database.module'))
