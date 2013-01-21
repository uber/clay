from __future__ import absolute_import

import logging
import random
import signal
import json
import time
import os.path
import os
import sys

from clay import logger


class Configuration(object):
    '''
    Manages global configuration from JSON files
    '''
    def __init__(self):
        self.paths = []
        self.config = {}
        self.last_updated = None
        self.remote_log = None
        self.init_logging()

    def debug(self):
        '''
        Returns True if this server should use debug configuration and logging
        '''
        if os.environ.get('CLAY_ENVIRONMENT', None) == 'development':
            return True
        else:
            return False

    def load(self, signum=None, frame=None):
        '''
        Iterate through expected config file paths, loading the ones that
        exist and can be parsed.
        '''

        cwd = os.getcwd()
        if not cwd in sys.path:
            sys.path.insert(0, cwd)

        self.config = {}
        paths = list(self.paths)
        if 'CLAY_CONFIG' in os.environ:
            paths += os.environ['CLAY_CONFIG'].split(':')

        for path in paths:
            path = os.path.expandvars(path)
            path = os.path.abspath(path)
            config = self.load_from_file(path)
            self.config.update(config)

        self.init_remote_logging()
        self.last_updated = time.time()

    def load_from_file(self, filename):
        '''
        Attempt to load configuration from the given filename. Returns an empty
        dict upon failure.
        '''

        try:
            config = json.load(file(filename, 'r'))
            sys.stderr.write('Loaded configuration from %s\n' % filename)
            return config
        except ValueError, e:
            sys.stderr.write('Error loading config from %s: %s\n' %
                (filename, str(e)))
            sys.exit(1)
            return {}

    def get(self, key, default=None):
        '''
        Get the configuration for a specific variable, using dots as
        delimiters for nested objects. Example: config.get('api.host') returns
        the value of self.config['api']['host'] or None if any of those keys
        does not exist. The default return value can be overridden.
        '''
        value = self.config
        for k in key.split('.'):
            try:
                value = value[k]
            except KeyError:
                return default
        #sys.stderr.write('config: %s=%r\n' % (key, value))
        return value

    def init_logging(self):
        '''
        Configure the root logger to output to stderr, with verbosity if
        self.debug() return True
        '''

        fmt = logging.Formatter('%(name)s %(levelname)s %(message)s')
        stderr = logging.StreamHandler()
        stderr.setFormatter(fmt)
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        root.addHandler(stderr)

        if self.debug():
            stderr.setLevel(logging.DEBUG)
        else:
            stderr.setLevel(logging.WARNING)

    def init_remote_logging(self):
        '''
        Configure logging to a remote server only if this is *not* a debug
        instance.
        '''

        if self.debug():
            return

        root = logging.getLogger()
        if self.remote_log:
            root.removeHandler(self.remote_log)

        loghost = self.get('logging.host', None)
        if loghost:
            host, port = loghost.split(':', 1)
            port = int(port)

            udplog = logger.UDPHandler(host, port)
            udplog.setLevel(logging.INFO)
            self.remote_log = udplog
            root.addHandler(udplog)

    def get_logger(self, name):
        '''
        Returns a Logger instance that may be used to emit messages with the
        given log name, respecting debug behavior.
        '''

        log = logging.getLogger(name)
        if self.debug():
            log.setLevel(logging.DEBUG)
        else:
            log.setLevel(logging.INFO)
        return log

    def feature_flag(self, name):
        '''
        Returns a boolean value for the given feature, which may be
        probabalistic.
        '''
        feature = self.get('features.%s' % name)
        if not feature:
            return False
        if not 'enabled' in feature:
            return False
        if 'percent' in feature:
            percent = float(feature['percent']) / 100.0
            return (random.random() < percent)
        return True


CONFIG = Configuration()
CONFIG.load()

# Upon receiving a SIGHUP, configuration will be reloaded
signal.signal(signal.SIGHUP, CONFIG.load)

# Expose some functions at the top level for convenience
get = CONFIG.get
get_logger = CONFIG.get_logger
feature_flag = CONFIG.feature_flag
debug = CONFIG.debug
