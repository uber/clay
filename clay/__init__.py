from __future__ import absolute_import
__version__ = '2.1.0'

from clay.server import app
from clay import config, stats, logger

__all__ = ['app', 'config', 'stats', 'logger']
