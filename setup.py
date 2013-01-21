#!/usr/bin/env python
from setuptools import setup

setup(
    name='clay',
    packages=['clay'],
    description='Uber backend service framework',
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
