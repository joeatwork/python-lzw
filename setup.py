
from distutils.core import setup, Command
import unittest
import doctest
from unittest import defaultTestLoader, TextTestRunner

import sys

# BUG. At least we should support 3.0, which means getting
# rid of a bunch of stupid byte-as-string stuff, which is kind
# of awesome.
(major_version, minor_version) = sys.version_info[:2]
if (major_version != 2) or (minor_version < 6):
    raise Exception("LZW currently requires python 2.6")
else:
    import lzw


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
        doctest.testmod(lzw)

        utests = defaultTestLoader.loadTestsFromName(TEST_MODULE_NAME)
        urunner = TextTestRunner(verbosity=2)
        urunner.run(utests)

        if self.runslow:
            utests = defaultTestLoader.loadTestsFromName(SLOW_TEST_MODULE_NAME)
            urunner = TextTestRunner(verbosity=2)
            urunner.run(utests)


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
      version=lzw.__version__,
      author=lzw.__author__,
      author_email=lzw.__email__,
      url=lzw.__url__,
      license=lzw.__license__,
      platforms='Python 2.6',
      download_url='http://pypi.python.org/packages/source/l/lzw/lzw-0.01.tar.gz',

      classifiers = [
        "Development Status :: 2 - Pre-Alpha",
        "Programming Language :: Python",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
        "Topic :: System :: Archiving",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        ],

      long_description = """
A pure python module for compressing and decompressing streams of
data, built around iterators. Requires python 2.6
""",

      cmdclass = { 
        'test' : RunTestsCommand,
        'doc' : DocCommand,
        },
      )
