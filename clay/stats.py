from __future__ import absolute_import

import time
import socket
from functools import wraps

from clay import config

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def send(stat):
    """Send a stat to statsd"""
    conf = config.get('statsd')
    if not conf:
        return
    sock.sendto(stat + '\n', 0, (conf['host'], conf['port']))


def send_counter(bucket, count):
    """Send a counter stat to statsd

    :param bucket: The bucket to increment by the count
    :type bucket: string
    :param count: The count to increment by
    :type count: integer
    """
    send('%s:%s|c' % (bucket, count))


def send_counter_sampled(bucket, count, sample):
    """Send a sampled counter stat to statsd

    :param bucket: The bucket to increment by the count
    :type bucket: string
    :param count: The count to increment by
    :type count: integer
    :param sample: The sample rate for the counter. Must be between 0 and 1
    :type sample: float
    """
    send('%s:%s|c|@%s' % (bucket, count, sample))


def send_timing(bucket, timing):
    """Send a timing stat to statsd

    :param bucket: The bucket to put the timing data into
    :type bucket: string
    :param timing: Timing (usually in ms)
    :type timing: integer
    """
    send('%s:%s|ms' % (bucket, timing))


def send_gauge(bucket, guage_value):
    """Send a guage stat to statsd

    :param bucket: The bucket to put the guage into
    :type bucket: string
    :param guage_value: Guage value or change, in the form "+N" or "-N"
    :type guage_value: float or string
    """
    send('%s:%s|g' % (bucket, guage_value))


def send_set(bucket, set_value):
    """Send a set stat to statsd

    :param bucket: The bucket to put the set into
    :type bucket: string
    :param guage_value: Set value
    :type guage_value: float
    """
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
