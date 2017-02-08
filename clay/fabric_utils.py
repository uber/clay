from __future__ import absolute_import
import os

from fabric.api import local
from fabric.context_managers import prefix
from fabric.utils import abort

ROOT_PATH = None
DEFAULT_ENVIRONMENT = "local"
DEFAULT_CONFIG_FILENAME = "config/{environment}.yaml"
ENV_VAR_PREFIX = "export CLAY_CONFIG={root_path}/{config_filename}"


def setfabfile(fabfile):
    """Set the path to the fabfile"""
    global ROOT_PATH
    ROOT_PATH = os.path.abspath(os.path.dirname(fabfile))


def localenv(*args, **kwargs):
    """Execute cmd in local environment."""
    if not ROOT_PATH:
        abort(
            "call clay.fabric_utils.setfabfile(__file__) in your project's " +
            "fabfile"
        )

    # Remove empty keys
    kwargs = {k: v for k, v in kwargs.items() if v}

    template_vars = {
        "root_path": ROOT_PATH,
        "environment": kwargs.pop("environment", DEFAULT_ENVIRONMENT),
        "config_filename": kwargs.pop("config_filename",
                                      DEFAULT_CONFIG_FILENAME)
    }

    # By default, the config filename includes the role name,
    # that's why we need to format it.
    template_vars["config_filename"] = kwargs.pop(
        "config_filename",
        DEFAULT_CONFIG_FILENAME).format(**template_vars)
    env_prefix = ENV_VAR_PREFIX.format(**template_vars)

    with prefix(env_prefix):
        return local(*args, **kwargs)
