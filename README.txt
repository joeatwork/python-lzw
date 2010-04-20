This is the README file for lzw, small, low level, pure python module
for simple, stream-friendly data compression, built around iterators.
Please see the accompanying LICENSE.txt file for license terms.

lzw currently requires python 2.6 to run, this will likely change to
support python 3.0 in (near) future releases.

Before going on, potential users are advised to take a look at the
gzip, zlib, bz2, zipfile, and tarfile modules available in the python
standard library, which are dynamite-fast, mature, well supported, and
generally awesome.

Seriously, check them out! You've already got them!

----

This software is in Pre-Alpha release, any bug reports (or even
stories about ways you use the software, or wish you could use the
software) are appreciated! Mail joerbowers@joe-bowers.com with your
info.

---

INSTALLING

you should be able to install this package with

   python setup.py install

----

Ok, moving on.

The easiest way to use lzw is probably something like this

>>> import lzw
>>>
>>> infile = lzw.readbytes("My Uncompressed File.txt")
>>> compressed = lzw.compress(infile)
>>> lzw.writebytes("My Compressed File.lzw", compressed)
>>>
>>> # Then later (or elsewhere)
>>> infile = lzw.readbytes("My Compressed File.lzw", compressed)
>>> uncompressed = lzw.decompress(infile)
>>> for bt in uncompressed:
>>> 	do_something_awesome_with_this_byte(bt)
>>>

See the module documentation for more details.

---

The underlying compression algorithm for this module is as expressed
in section 13 of the TIFF 6.0 specification, pages 58 to 62, available
at the time of this writing on-line at

    http://partners.adobe.com/public/developer/en/tiff/TIFF6.pdf

Wherever possible, I've tried to adhere to the algorithm and
conventions that are described (in exhaustive and yet very readable
detail!) in that document, even when it gets a bit Tiff
specific. Where there are differences, they are likely bugs in this
code.

---

Current dev priorities:

- Support python 3.0, which likely means treating our byte streams as
  lists of ints until the last possible moment, which also seems like
  it'll make everything a bit more simple and sane.

- Hunt down some potential user applications, see why they're
  potential rather than actual, and then get on that bus.


For now

- Keep things as simple and intelligible as possible
- Adhere as closely to the TIFF spec as is reasonable
- Keep memory use low for good use of the iterators
- Stay in pure python
- Faster would be nicer, though...


