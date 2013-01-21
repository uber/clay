from traceback import format_exc
from datetime import datetime
from Queue import Queue
import threading
import logging
import socket
import json
import time
import ssl


LOG_QUEUE_SIZE = 5000
BACKOFF_INITIAL = 0.1
BACKOFF_MULTIPLE = 1.2
INTERNAL_LOG = logging.getLogger('clay_internal')


class TCPHandler(logging.Handler):
    '''
    Python logging handler for sending JSON formatted messages over
    TCP, optionally wrapping the connection with TLSv1
    '''
    def __init__(self, host, port, ssl_ca_file=None):
        '''
        Instantiate a TCPHandler with the intent of connecting to the
        given host (string) and port (int) with or without using SSL/TLSv1
        '''
        logging.Handler.__init__(self)
        self.host = host
        self.port = port
        self.ssl_ca_file = ssl_ca_file
        self.sock = None
        self.queue = Queue(LOG_QUEUE_SIZE)
        self.connect_wait = BACKOFF_INITIAL
        self.raiseExceptions = 0

        self.hostname = socket.gethostname()
        if self.hostname.find('.') != -1:
            self.hostname = self.hostname.split('.', 1)[0]

        self.sender = threading.Thread(target=self.run)
        self.sender.setDaemon(True)
        self.sender.start()

    def connect(self):
        '''
        Create a connection with the server, sleeping for some
        period of time if connection errors have occurred recently.
        '''
        self.sock = socket.socket()
        if self.ssl_ca_file:
            self.sock = ssl.wrap_socket(self.sock,
                ssl_version=ssl.PROTOCOL_TLSv1,
                cert_reqs=ssl.CERT_REQUIRED,
                ca_certs=self.ssl_ca_file)

        INTERNAL_LOG.debug('Connecting (backoff: %.03f)' %
            self.connect_wait)
        time.sleep(self.connect_wait)
        self.sock.connect((self.host, self.port))

    def jsonify(self, record):
        '''
        Translate a LogRecord instance into a json_event
        '''
        timestamp = datetime.utcfromtimestamp(record.created)
        timestamp = timestamp.isoformat()

        fields = {
            'level': record.levelname,
            'filename': record.pathname,
            'lineno': record.lineno,
            'method': record.funcName,
        }
        if record.exc_info:
            fields['exception'] = str(record.exc_info)
            fields['traceback'] = format_exc(record.exc_info)

        log = {
            '@source_host': self.hostname,
            '@timestamp': timestamp,
            '@tags': [record.name],
            '@message': record.getMessage(),
            '@fields': fields,
        }
        return json.dumps(log)

    def emit(self, record):
        '''
        Send a LogRecord object formatted as json_event via a
        queue and worker thread.
        '''
        self.queue.put_nowait(record)

    def run(self):
        '''
        Main loop of the logger thread. All network I/O and exception handling
        originates here. Strings are consumed from self.queue and sent to
        self.sock, creating a new connection if necessary.

        If any exceptions are caught, the message is put() back on the queue
        and the exception is allowed to propagate up through
        logging.Handler.handleError(), potentially causing this thread to abort.
        '''
        INTERNAL_LOG.debug('Log I/O thread started')
        while True:
            record = self.queue.get()
            if record is None:
                break

            jsonrecord = self.jsonify(record)
            jsonrecord = '%s\n' % jsonrecord

            try:
                if self.sock is None:
                    self.connect()
                self.send(jsonrecord)
            except Exception:
                # This exception will be silently ignored and the message
                # requeued unless self.raiseExceptions=1
                self.queue.put(record)
                self.handleError(record)
            self.queue.task_done()
        INTERNAL_LOG.debug('Log I/O thread exited cleanly')

    def send(self, data):
        '''
        Keep calling SSLSocket.write until the entire message has been sent
        '''
        while len(data) > 0:
            if self.ssl_ca_file:
                sent = self.sock.write(data)
            else:
                sent = self.sock.send(data)
            data = data[sent:]
        self.connect_wait = BACKOFF_INITIAL

    def handleError(self, record):
        '''
        If an error occurs trying to send the log message, close the connection
        and delegate the exception handling to the superclass' handleError,
        which raises the exception (potentially killing the log thread) unless
        self.raiseExceptions is False.
        http://hg.python.org/cpython/file/e64d4518b23c/Lib/logging/__init__.py#l797
        '''
        INTERNAL_LOG.exception('Unable to send log')
        self.cleanup()
        self.connect_wait *= BACKOFF_MULTIPLE
        logging.Handler.handleError(self, record)

    def cleanup(self):
        '''
        If the socket to the server is still open, close it. Otherwise, do
        nothing.
        '''
        if self.sock:
            INTERNAL_LOG.info('Closing socket')
            self.sock.close()
            self.sock = None

    def close(self):
        '''
        Send a sentinel None object to the worker thread, telling it to exit
        and disconnect from the server.
        '''
        self.queue.put(None)
        self.cleanup()
        #self.sender.join()


class UDPHandler(logging.Handler):
    '''
    Python logging handler for sending JSON formatted messages over UDP
    '''
    def __init__(self, host, port):
        '''
        Instantiate a UDPHandler with the intent of connecting to the
        given host (string) and port (int)
        '''
        logging.Handler.__init__(self)
        self.host = host
        self.port = port
        self.sock = None
        self.raiseExceptions = 0

        self.hostname = socket.gethostname()
        if self.hostname.find('.') != -1:
            self.hostname = self.hostname.split('.', 1)[0]

    def connect(self):
        '''
        Create a connection with the server, sleeping for some
        period of time if connection errors have occurred recently.
        '''
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.connect((self.host, self.port))

    def jsonify(self, record):
        '''
        Translate a LogRecord instance into a json_event
        '''
        timestamp = datetime.utcfromtimestamp(record.created)
        timestamp = timestamp.isoformat()

        fields = {
            'level': record.levelname,
            'filename': record.pathname,
            'lineno': record.lineno,
            'method': record.funcName,
        }
        if record.exc_info:
            fields['exception'] = str(record.exc_info)
            fields['traceback'] = format_exc(record.exc_info)

        log = {
            '@source_host': self.hostname,
            '@timestamp': timestamp,
            '@tags': [record.name],
            '@message': record.getMessage(),
            '@fields': fields,
        }
        return json.dumps(log)

    def emit(self, record):
        '''
        Send a LogRecord object formatted as json_event via a
        queue and worker thread.
        '''
        try:
            if self.sock is None:
                self.connect()
            jsonrecord = self.jsonify(record)
            jsonrecord = '%s\n' % jsonrecord
            self.sock.sendall(jsonrecord)
        except Exception:
            INTERNAL_LOG.exception('Error sending message to log server')
            self.close()

    def close(self):
        if self.sock:
            self.sock.close()
        self.sock = None
