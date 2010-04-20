
import lzw
import unittest

import os
import tempfile
import itertools

TEST_ROOT = os.path.dirname(__file__)
BIG_FILE = os.path.join(TEST_ROOT, "data", "library-of-congress-smaller.ppm")
GIANT_FILE = os.path.join(TEST_ROOT, "data", "library-of-congress-photo.ppm")

class TestEncoderSlowly(unittest.TestCase):

    def test_big_file(self):
        self.verify_compressed_file(BIG_FILE)

    def test_giant_file(self):
        self.verify_compressed_file(GIANT_FILE)


    def verify_compressed_file(self, testfile=GIANT_FILE):

        with tempfile.TemporaryFile("w+b") as compressedfile:

            originalsize = 0
            compressedsize = 0
            uncompressedsize = 0

            bigstream = lzw.readbytes(testfile)
            compressed = lzw.compress(bigstream)
            
            for bs in compressed: 
                compressedsize = compressedsize + 1
                compressedfile.write(bs)

            ############################

            compressedfile.flush()
            compressedfile.seek(0)

            checkstream = lzw.readbytes(testfile)
            uncompressed = lzw.decompress(lzw.filebytes(compressedfile))

            for oldbyte, newbyte in itertools.izip_longest(checkstream, uncompressed):
                uncompressedsize = uncompressedsize + 1

                if oldbyte != newbyte:
                    msg = "Corrupted byte at {0}, original {1} != {2}".format(uncompressedsize, oldbyte, newbyte)
                    self.assertEquals(oldbyte, newbyte, msg)

