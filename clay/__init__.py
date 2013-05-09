from __future__ import absolute_import
__version__ = '2.0.2'

from clay.server import app
from clay import config, stats, logger, mail

__all__ = ['app', 'config', 'stats', 'logger', 'mail']
