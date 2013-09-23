from __future__ import absolute_import

import logging.config
import logging
import random
import signal
import json
import time
import os.path
import os
import sys

from clay import logger


SERIALIZERS = {'json': json}

try:
    import yaml
    SERIALIZERS['yaml'] = yaml
except ImportError:
    pass


class Configuration(object):
    '''
    Manages global configuration from JSON files
    '''
    def __init__(self):
        self.paths = []
        self.config = {}
        self.last_updated = None
        self.init_logging()

    def load(self, signum=None, frame=None):
        '''
        Called when the configuration should be loaded. May be called multiple
        times during the execution of a program to change or update the
        configuration. This method should be overridden by a subclass.
        '''
        return

    def debug(self):
        '''
        Returns True if this server should use debug configuration and logging.
        This method is deprecated and 
        '''
        log = self.get_logger('clay.config')
        log.warning('Configuration.debug() is deprecated and may be removed in a future release of clay-flask. Please use config.get("debug.enabled", False) instead')
        return self.get('debug.enabled', False)

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
        Configure the default root logger to output WARNING to stderr
        '''
        logging.basicConfig(
            format='%(asctime)s %(name)s %(levelname)s %(message)s',
            level=logging.WARNING)

    def reset_logging(self):
        '''
        Reset the root logger configuration to no handlers
        '''
        root = logging.getLogger()
        if root.handlers:
            for handler in list(root.handlers):
                root.removeHandler(handler)

    def configure_logging(self, log_config):
        '''
        Remove all existing logging configuration and use the given
        configuration instead. The format of the log_config dict is specified at
        http://docs.python.org/2/library/logging.config.html#logging-config-dictschema
        '''
        logging.config.dictConfig(log_config)

    def get_logger(self, name):
        '''
        Returns a Logger instance that may be used to emit messages with the
        given log name, respecting debug behavior.
        '''

        log = logging.getLogger(name)
        if self.get('debug.logging', False):
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
        if 'percent' in feature:
            percent = float(feature['percent']) / 100.0
            return (random.random() < percent)
        return feature.get('enabled', False)


class FileConfiguration(Configuration):
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

        self.last_updated = time.time()

        self.init_logging()
        log_config = self.get('logging')
        if log_config:
            self.configure_logging(log_config)

    def load_from_file(self, filename):
        '''
        Attempt to load configuration from the given filename. Returns an empty
        dict upon failure.
        '''
        log = self.get_logger('clay.config')

        try:
            filetype = os.path.splitext(filename)[-1].lstrip('.').lower()
            if not filetype in SERIALIZERS:
                log.warning('Unknown config format %s, parsing as JSON' % filetype)
                filetype = 'json'

            # Try getting a safe_load function. If absent, use 'load'.
            load = getattr(SERIALIZERS[filetype], "safe_load",
                           getattr(SERIALIZERS[filetype], "load"))

            config = load(file(filename, 'r'))
            if not config:
                raise ValueError('Empty config')
            log.info('Loaded configuration from %s' % filename)
            return config
        except ValueError, e:
            log.critical('Error loading config from %s: %s' %
                (filename, str(e)))
            sys.exit(1)
            return {}


CONFIG = FileConfiguration()
CONFIG.load()

# Upon receiving a SIGHUP, configuration will be reloaded
signal.signal(signal.SIGHUP, CONFIG.load)

# Expose some functions at the top level for convenience
get = CONFIG.get
get_logger = CONFIG.get_logger
feature_flag = CONFIG.feature_flag
debug = CONFIG.debug
