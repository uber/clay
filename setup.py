#!/usr/bin/env python
from setuptools import setup

setup(
    name='clay-flask',
    version='1.0',
    author='Jeremy Grosser',
    author_email='jeremy@uber.com',
    packages=['clay'],
    description='Clay is a framework for building RESTful backend services using best practices.',
    install_requires=[
        'flask',
    ],
    entry_points={
        'console_scripts': [
            'clay-devserver = clay.server:devserver',
            'clay-celery = clay.celery:main',
        ],
    },
)
