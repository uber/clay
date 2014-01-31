from __future__ import absolute_import

import functools
import socket
import time

from clay import config

log = config.get_logger('clay.stats')


class StatsConnection(object):
    '''
    Handles the lifecycle of stats sockets and connections.
    '''
    def __init__(self):
        self.sock = None
        self.proto = None
        self.host = None
        self.port = None
        self.next_retry = None
        self.backoff = 0.5
        self.max_backoff = 10.0

    def __str__(self):
        if self.sock is not None:
            return 'StatsConnection %s %s:%i (connected)' % (
                   self.proto, self.host, self.port)
        else:
            return 'StatsConnection %s %s:%i (not connected)' % (
                   self.proto, self.host, self.port)

    def get_socket(self):
        '''
        Creates and connects a new socket, or returns an existing one if this
        method was called previously. Returns a (protocol, socket) tuple, where
        protocol is either 'tcp' or 'udp'. If the returned socket is None, the
        operation failed and details were logged.
        '''
        if self.sock is not None:
            return (self.proto, self.sock)

        proto = config.get('statsd.protocol', 'udp')
        self.proto = proto
        self.host = config.get('statsd.host', None)
        self.port = config.get('statsd.port', 8125)

        if self.host is None or self.port is None:
            return (self.proto, None)

        if (self.next_retry is not None) and (self.next_retry > time.time()):
            return

        if proto == 'udp':
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            log.debug('Created udp statsd socket')
            return (proto, self.sock)

        if proto == 'tcp':
            if self.host is None or not isinstance(self.port, int):
                log.error('Invalid TCP statsd config: host=%r port=%r',
                          self.host, self.port)
                self.sock = None
            else:
                try:
                    self.sock = socket.create_connection(address=(self.host, self.port), timeout=4.0)
                    log.debug('Connected tcp statsd socket to %s:%i',
                              self.host, self.port)
                    # Succesful connection resets retry backoff to 1 second
                    self.next_retry = None
                    self.backoff = 0.5
                except socket.error:
                    log.exception('Cannot open tcp stats socket %s:%i',
                                  self.host, self.port)
                    self.sock = None

                    # Every time a connection fails, we add 25% of the backoff value
                    # We cap this at max_backoff so that we guarantee retries after
                    # some period of time
                    if self.backoff > self.max_backoff:
                        self.backoff = self.max_backoff
                    log.warning('Unable to connect to statsd, not trying again for %.03f seconds', self.backoff)
                    self.next_retry = (time.time() + self.backoff)
                    self.backoff *= 1.25
            return (proto, self.sock)

        log.warning('Unknown protocol configured for statsd socket: %s', proto)
        return (proto, None)

    def reset(self):
        '''
        Close and remove references to the socket.
        '''
        if self.sock is None:
            return
        try:
            self.sock.close()
        except socket.error:
            pass
        self.sock = None
        log.debug('Reset statsd socket')

    def send(self, stat):
        '''
        Send a raw stat line to statsd. A new socket will be opened and
        connected if necessary. Returns True if the stat was sent successfully.

        :param stat: The stat to be sent to statsd, with no trailing newline
        :type stat: string
        :rtype: boolean
        '''
        proto, sock = self.get_socket()
        if sock is None:
            return False

        if not stat.endswith('\n'):
            stat += '\n'

        try:
            if proto == 'udp':
                sock.sendto(stat, 0, (self.host, self.port))
                return True

            if proto == 'tcp':
                sock.sendall(stat)
                return True
        except socket.error:
            log.exception('Unable to send to statsd, resetting socket')
            self.reset()
        return False

connection = StatsConnection()
send = connection.send  # backwards compatibility


class Timer(object):
    '''
    Context manager for recording wall-clock timing stats.

    with clay.stats.Timer("myapp.example"):
        # do some work
    '''
    def __init__(self, key):
        self.key = key
        self.start = None

    def __enter__(self):
        self.start = time.time()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        now = time.time()
        elapsed_ms = ((now - self.start) * 1000.0)
        timing(self.key, elapsed_ms)


def count(key, n, sample=1.0):
    '''
    Increment a counter by n, or decrement if n is negative.

    :param key: The key to increment by the count
    :type key: string
    :param n: The number to increment by
    :type n: integer
    :param sample: Optional sample rate to scale the counter by. Must be a
                   float between 0.0 and 1.0. Defaults to 1.0
    :type sample: float
    '''
    if sample == 1.0:
        return connection.send('%s:%i|c' % (key, n))
    else:
        return connection.send('%s:%i|c|@%f' % (key, n, sample))


def timing(key, ms):
    '''
    Send a timing stat to statsd

    :param key: A key identifying this stat
    :type key: string
    :param ms: A floating point number of milliseconds
    :type ms: float
    '''
    if not isinstance(ms, float):
        ms = float(ms)
    return connection.send('%s:%f|ms' % (key, ms))


def gauge(key, value):
    '''
    Send an instantaneous gauge value to statsd

    :param key: Name of this gauge
    :type key: string
    :param value: Gauge value or delta
    :type value: float
    '''
    if not isinstance(value, float):
        value = float(value)
    return connection.send('%s:%f|g' % (key, value))


def unique_set(key, value):
    '''
    Send a set stat to statsd, counting the approximate number of unique
    key/value pairs.

    :param key: Name of this set
    :type key: string
    :param value: Set value
    :type value: string
    '''
    return connection.send('%s:%s|s' % (key, value))


def wrapper(prefix):
    '''
    Decorator that logs timing, call count, and exception count statistics to
    statsd. Given a prefix of "example", the following keys would be created:

    stats.counts.example.calls
    stats.counts.example.exceptions
    stats.timers.example.duration

    :param: prefix
    :type key: Prefix for stats keys to be created under
    '''

    def clay_stats_wrapper(func):
        @functools.wraps(func)
        def wrap(*args, **kwargs):
            count('%s.calls' % prefix, 1)
            try:
                with Timer('%s.duration' % prefix):
                    return func(*args, **kwargs)
            except Exception:
                count('%s.exceptions' % prefix, 1)
                raise
        return wrap
    return clay_stats_wrapper
