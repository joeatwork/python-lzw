
import lzw

import unittest
import itertools
import random
import struct
import os


# These tests are less interesting than the doctests inside of the lzw
# module itself, they're generally not really unit tests at all;
# rather, they're functional tests written for "dual" subsystems in
# lzw, or else particularly tricky bits and otherwise detected bugs I
# want to be sure don't regress against code changes.

TEST_ROOT = os.path.dirname(__file__)
ENGLISH_FILE = os.path.join(TEST_ROOT, "data", "the_happy_prince.txt")

class TestEncoder(unittest.TestCase):
    
    def setUp(self):
        self.english = None

        with open(ENGLISH_FILE, "rb") as inf:
            self.english = inf.read()

        self.gibberish = b"".join(struct.pack("B", random.randrange(256))
                                  for b in self.english)
            

    def test_readbytes(self):

        realbytes = None

        with open(ENGLISH_FILE, "rb") as inf:
            realbytes = inf.read()

        testbytes = b"".join(lzw.readbytes(ENGLISH_FILE))

        for (old,new) in itertools.izip_longest(realbytes, testbytes):
            self.assertEqual(old, new)


    def test_encoder_packing_assumption(self):
        """
        Our bitpacking scheme relies on assumptions about the size of
        the codebook in relation to the number of codes produced. In
        particular:
        
        - each non-control code emitted by the encoder is FOLLOWED by
          a single addition to the encoder's codebook, or is followed
          by a control code in the output.
         
        - each control code emitted by the encoder is FOLLOWED by a
          reversion of the codebook to it's initial state.

        """
        encoder = lzw.Encoder()
        initial_codesize = encoder.code_size()
        codesize = initial_codesize
        codes_seen = 0

        probablyfailed = False

        for pt in encoder.encode(self.english):
            codesize = encoder.code_size()

            if pt == lzw.CLEAR_CODE:
                codes_seen = 0
                probablyfailed = False
            elif probablyfailed:
                self.fail(probablyfailed)
            else:
                codes_seen = codes_seen + 1
                if initial_codesize + codes_seen != codesize:
                    probablyfailed = "Expected code size {0} but found {1}, Not followed by a control signal"


    def test_encodedecode(self):

        encoder = lzw.Encoder()
        decoder = lzw.Decoder()

        codepoints = encoder.encode(self.english)
        decoded = decoder.decode(codepoints)
        newbytes = b"".join(decoded)

        self.assertEqual(self.english, newbytes)

        encoder = lzw.Encoder()
        decoder = lzw.Decoder()

        codepoints = encoder.encode(self.gibberish)
        decoded = decoder.decode(codepoints)
        newbytes = b"".join(decoded)

        self.assertEqual(self.gibberish, newbytes)

    
    def test_compressdecompress(self):
        english = self.english
        gibberish = self.gibberish

        compressed = lzw.compress(english)
        compressed = [ b for b in compressed ]

        decompressed = b"".join(lzw.decompress(compressed))

        self.assertEqual(english, decompressed)

        compressed = lzw.compress(gibberish)
        compressed = [ b for b in compressed ]

        decompressed = b"".join(lzw.decompress(compressed))
        
        self.assertEqual(gibberish, decompressed)

