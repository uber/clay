#!/usr/bin/env python
from __future__ import absolute_import
import sys

from flask import Flask
import werkzeug.serving

from clay import config

log = config.get_logger('clay.server')


def load_middleware(app, name, mwconfig):
    log.info('Loading WSGI middleware %s' % name)
    try:
        modulename, wsgi = name.rsplit('.', 1)
        mw = __import__(modulename)
        mw = sys.modules[modulename]
        mw = getattr(mw, wsgi, None)
        if mw is None or not callable(mw):
            log.error('No callable named %s in %s (%r)' % (wsgi, modulename, mw))
        else:
            app = mw(app, **mwconfig)
    except Exception, e:
        log.exception('Unable to load WSGI middleware %s' % name)
    return app

flask_init = config.get('flask.init', {
    'import_name': 'clayapp',
})

app = Flask(**flask_init)
app.debug = config.get('debug.enabled', False)
app.config.update(config.get('flask.config', {}))
application = app
for name, mwconfig in config.get('middleware', {}).iteritems():
    application = load_middleware(application, name, mwconfig)


def devserver():
    if not config.get('debug.enabled', False):
        sys.stderr.write('This server must be run in development mode, set debug.enabled in your config and try again\n')
        return -1

    for modulename in config.get('views'):
        log.debug('Loading views from %s' % modulename)
        module = __import__(modulename)

    conf = config.get('debug.server')
    log.warning('DEVELOPMENT MODE')
    log.info('Listening on %s:%i' % (conf['host'], conf['port']))

    kwargs = {
        'use_reloader': True,
        'use_debugger': True,
        'use_evalex': True,
        'threaded': False,
        'processes': 1,
    }
    kwargs.update(config.get('debug.werkzeug', {}))
    werkzeug.serving.run_simple(conf['host'], conf['port'], application, **kwargs)


if __name__ == '__main__':
    sys.exit(devserver())
