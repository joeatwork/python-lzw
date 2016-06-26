
from setuptools import setup, Command, distutils
import unittest
import doctest
from unittest import defaultTestLoader, TextTestRunner

import sys

__author__ = "Joe Bowers"
__license__ = "MIT License"
__version__ = "0.2.11"
__status__ = "Development"
__email__ = "joerbowers@gmail.com"
__url__ = "http://www.joe-bowers.com/static/lzw"

TEST_MODULE_NAME = "tests.tests"
SLOW_TEST_MODULE_NAME = "tests.slow"
DOC_DIR_NAME = "doc"
MODULES = [ "lzw" ]

class RunTestsCommand(Command):
    """Runs package tests"""
    
    user_options = [('runslow', None, 'also runs the (fairly slow) functional tests')]

    def initialize_options(self):
        self.runslow = False

    def finalize_options(self):
        pass # how on earth is this supposed to work?


    def run(self):
        import lzw
        success = doctest.testmod(lzw).failed == 0

        utests = defaultTestLoader.loadTestsFromName(TEST_MODULE_NAME)
        urunner = TextTestRunner(verbosity=2)
        success &= urunner.run(utests).wasSuccessful()

        if self.runslow:
            utests = defaultTestLoader.loadTestsFromName(SLOW_TEST_MODULE_NAME)
            urunner = TextTestRunner(verbosity=2)
            success &= urunner.run(utests).wasSuccessful()

        if not success:
            raise distutils.errors.DistutilsError('Test failure')


class DocCommand(Command):
    """Generates package documentation using epydoc"""

    user_options = []

    def initialize_options(self): pass
    def finalize_options(self): pass

    def run(self):
        # Slightly stupid. Move to sphinx when you can, please.
        import epydoc.cli
        real_argv = sys.argv
        sys.argv = [ "epydoc", "--output", DOC_DIR_NAME, "--no-private" ] + MODULES
        epydoc.cli.cli()
        sys.argv = real_argv


setup(name="lzw",
      description="Low Level, pure python lzw compression/decompression library",

      py_modules=MODULES,
      version=__version__,
      author=__author__,
      author_email=__email__,
      url=__url__,
      license=__license__,

      classifiers = [
        "Development Status :: 2 - Pre-Alpha",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
        "Topic :: System :: Archiving",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        ],

      packages = ['lzw'],

      install_requires=['six'],

      long_description = """
A pure python module for compressing and decompressing streams of
data, built around iterators. Requires python 2.6
""",

      cmdclass = { 
        'test' : RunTestsCommand,
        'doc' : DocCommand,
        },
      )
