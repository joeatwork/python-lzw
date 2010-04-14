
from distutils.core import setup

setup(name="lzw",
      version="0.01",
      py_modules=['lzw'],
      description="Low Level, pure python lzw compression/decompression library",
      author="Joe Bowers",
      author_email="joerbowers@gmail.com",
      url="http://www.joe-bowers.com/lzw",

      classifiers = [
        "Development Status :: 2 - Pre-Alpha",
        "Programming Language :: Python",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: BSD License",
        "Topic :: System :: Archiving",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],

      long_description = """
A pure python module for compressing and decompressing streams of data.
"""
      )
