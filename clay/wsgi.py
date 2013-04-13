from __future__ import absolute_import
from clay.server import application
from clay import config

log = config.get_logger('clay.wsgi')

views = config.get('views', [])
if not views:
    log.warning('No clay view modules configured')

for modulename in views:
    log.debug('Loading views from %s' % modulename)
    module = __import__(modulename)
