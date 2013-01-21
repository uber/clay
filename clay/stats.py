from __future__ import absolute_import

from clay import config
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def send(stat):
    conf = config.get('statsd')
    if not conf:
        return
    sock.sendto(stat + '\n', 0, (conf['host'], conf['port']))
