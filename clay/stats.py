from __future__ import absolute_import

from clay import config
from functools import wraps
import time
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def send(stat):
    conf = config.get('statsd')
    if not conf:
        return
    sock.sendto(stat + '\n', 0, (conf['host'], conf['port']))


def send_counter(bucket, count):
    send('%s:%s|c' % (bucket, count))


def send_counter_sample(bucket, count, sample):
    send('%s:%s|c|@%s' % (bucket, count, sample))


def send_timing(bucket, timing):
    send('%s:%s|ms' % (bucket, timing))


def send_gauge(bucket, guage_value):
    send('%s:%s|g' % (bucket, guage_value))


def send_set(bucket, set_value):
    send('%s:%s|s' % (bucket, set_value))

def timer(statsd_name=None):
    """Wraps a function with statsd timer instrumentation

    This logs the amount of time it takes to execute a function
    """
    def wrap(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            status_statsd_name = statsd_name or func.__name__
            start_time = time.time()
            try:
                rtrn = func(*args, **kwargs)
            except:
                send_counter("%s.exceptions" % status_statsd_name, 1)
                raise
            else:
                end_time = time.time()
                ms = (end_time - start_time) * 1000
                send_timing("%s.response_time" % status_statsd_name, ms)
            return rtrn
        return wrapper
    return wrap


def instrumented_func(statsd_name=None, prefix=None):
    """Wraps a function with statsd instrumentation.

    Must be called as a function to ensure kwargs passed in
    """

    def wrap(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            status_statsd_name = statsd_name or func.__name__
            if prefix:
                status_statsd_name = "%s.%s" % (prefix, status_statsd_name)
            send_counter("%s.started" % status_statsd_name, 1)

            start_time = time.time()
            try:
                rtrn = func(*args, **kwargs)
            except:
                send_counter("%s.exceptions" % status_statsd_name, 1)
                raise
            else:
                send_counter("%s.successes" % status_statsd_name, 1)

                end_time = time.time()
                ms = (end_time - start_time) * 1000
                send_timing("%s.duration" % status_statsd_name, ms)
                return rtrn
        return wrapper
    return wrap
