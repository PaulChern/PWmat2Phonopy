#!/usr/bin/env python
from distutils.core import setup

setup(
    name = 'PWmat2Phonopy',
    author = 'Paul Chern',
    author_email = 'peng.chen.iphy@gmail.com',
    version = '0.2.1',
    url = 'peng',
    packages = ['pwmat2phonopy',],
    scripts=['bin/PWmat2Phonopy','bin/PWmatRunPhonopy.py','bin/pos2pwmat.py','bin/pwmat2pos.py'],
    license = 'Creative Commons Attribution-Noncommercial-Share Alike license',
    long_description = open('README.txt').read(),
    install_requires=[
        "phonopy == 1.12.0",
        "numpy >= ",
        "matplotlib >= "
    ],
)
