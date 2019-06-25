#!/usr/bin/env python
from setuptools import setup

# Adding this import avoids an exception caused by nosetests
# http://stackoverflow.com/questions/9352656/python-assertionerror-when-running-nose-tests-with-coverage
from multiprocessing import util
util = util  # make pyflakes/etc happy

def read_long_description(filename="README.md"):
    with open(filename) as f:
        return f.read().strip()


def requirements(filename="requirements.txt"):
    with open(filename) as f:
        return f.readlines()

setup(
    name='clay-flask',
    version='2.1.8',
    author='Jeremy Grosser',
    author_email='jeremy@uber.com',
    packages=['clay'],
    description='Clay is a framework for building RESTful backend services using best practices.',
    install_requires=requirements(),
    tests_require=[
        'pytest',
        'webtest',
        'mock >= 1.0.0',
    ],
    test_suite='nose.collector',
    entry_points={
        'console_scripts': [
            'clay-devserver = clay.server:devserver',
            'clay-celery = clay.celery:main',
        ],
    },
)
