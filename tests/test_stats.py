from __future__ import absolute_import

import unittest
import socket
import os.path
import os
import re

os.environ['CLAY_CONFIG'] = 'config.json'

from clay import config, stats
log = config.get_logger('clay.tests.stats')


class MockTCPListener(object):
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.listen(2)
        self.accepted = None
        self.buf = ''

    def readline(self):
        if not self.accepted:
            self.accepted, addr = self.sock.accept()
        while self.buf.find('\n') == -1:
            chunk = self.accepted.recv(1024)
            self.buf += chunk
        line, self.buf = self.buf.split('\n', 1)
        log.debug('mockserver.readline: %r' % line)
        return line

    def close(self):
        if self.buf:
            log.warning('Data still in mock server buffer at teardown: %r' % self.buf)
        self.sock.close()


socket.setdefaulttimeout(1.0)
mockserver = MockTCPListener(config.get('statsd.host'), config.get('statsd.port', 8125))

class TestStats(unittest.TestCase):
    def test_send(self):
        self.assertEqual(config.get('statsd.protocol'), 'tcp')
        stats.send('foo:1|c')
        line = mockserver.readline()
        self.assertEqual(line, 'foo:1|c')

    def test_timer_context(self):
        with stats.Timer('foo'):
            pass
        line = mockserver.readline()
        self.assertNotEqual(re.match('^foo:[0-9\.]+|ms$', line), None)

    def test_count(self):
        stats.count('foo', 1)
        line = mockserver.readline()
        self.assertEqual(line, 'foo:1|c')

    def test_count_sample(self):
        stats.count('foo', 1, 0.5)
        line = mockserver.readline()
        self.assertEqual(line, 'foo:1|c|@0.500000')

    def test_timing(self):
        stats.timing('foo', 10.5)
        line = mockserver.readline()
        self.assertEqual(line, 'foo:10.500000|ms')

    def test_gauge(self):
        stats.gauge('foo', 1)
        line = mockserver.readline()
        self.assertEqual(line, 'foo:1.000000|g')

    def test_unique_set(self):
        stats.unique_set('foo', 'bar')
        line = mockserver.readline()
        self.assertEqual(line, 'foo:bar|s')

    def test_wrapper(self):
        @stats.wrapper('foo')
        def foofunc(arg):
            self.assertTrue(arg)
            return arg

        foofunc(True)
        lines = [mockserver.readline() for i in range(2)]
        self.assertIn('foo.calls:1|c', lines)
        self.assertNotIn('foo.exceptions:1|c', lines)
        self.assertEqual(len([x for x in lines if re.match('^foo.duration:[0-9\.]+|ms$', x)]), 1)
