#!/usr/bin/env python3
'''
AraoSL - AraoSecret
'''

import os
from setuptools import setup


setup(
    name='AraoSecret',
    version='0.1',
    author='Estevo Paz',
    author_email='estevo@araosl.com',
    description='Credentials management system',
    packages=['arao_secret'],
    # scripts=['bin/' + script for script in os.listdir('bin')],
    keywords='python3 www crypt',
    license='GPL',
    classifiers=['Development Status :: 5 - Production/Stable',
                 'Natural Language :: English',
                 'Operating System :: OS Independent',
                 'Programming Language :: Python :: 3',
                 'License :: OSI Approved ::'
                 ' GNU Library or Lesser General Public License (LGPL)',
                 'License :: OSI Approved ::'
                 ' GNU Affero General Public License v3',
                 'Topic :: Internet',
                 'Topic :: Internet :: WWW/HTTP']
)
