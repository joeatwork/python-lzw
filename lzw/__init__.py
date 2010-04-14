

import struct
import itertools

# Copyright (c) 2010, Joseph Bowers
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met: 
#
# * Redistributions of source code must retain the above
# copyright notice, this list of conditions and the following
# disclaimer.  
#
# * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following
# disclaimer in the documentation and/or other materials provided with
# the distribution.  
#
# * Neither the name of the author nor the
# names of its contributors may be used to endorse or promote products
# derived from this software without specific prior written
# permission.  
#
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# This software is an implementation of the LZW compression algorithm.
# LZW compression has been Patented in the United States and other
# countries. While it is my belief that the patents relevant to LZW
# compression have expired, I cannot give ANY legal advice or
# assurances to users of this software, particularly with regards to
# the legal status of the LZW algorithm.
# 


"""
After the TIFF implementation of LZW, as described here
http://www.fileformat.info/format/tiff/corion-lzw.htm

In an even-nuttier-shell:

   Starting with codes 0-255 that code to themselves, and two control
   codes, we work our way through a stream of codes. When we encounter
   a pair of codes c1,c2 we add another entry to our code table with
   the lowest available code and the value value(c1) + value(c2)[0]

Of course, there are details :)

Our control codes are:

  Clear is code point 256
      when this code is encountered, we flush the codebook and start over.

  EndOfInformation is code point 257
      when this code is encountered, we treat 

When dealing with bytes, codes are emitted as variable
length bit strings packed into the stream of bytes.

  codepoints are written with varying length
    initially 9 bits
    at 512 entries 10 bits
    at 1025 entries at 11 bits
    at 2048 entries 12 bits
    with max of 4095 entries in a table (including Clear and EOI)

  code points are stored with their MSB in the most significant bit
  available in the output character.

"""

CLEAR_CODE = 256
END_OF_INFO_CODE = 257

DEFAULT_MIN_BITS = 9
DEFAULT_MAX_BITS = 12



def inttobits(anint, width=None):
    """
    Produces an array of booleans representing the given argument as
    an unsigned integer, MSB first. If width is given, will pad the
    MSBs to the given width (but will NOT truncate overflowing
    results)

    >>> import lzw
    >>> lzw.inttobits(304, width=16)
    [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0]

    """
    remains = anint
    retreverse = []
    while remains:
        retreverse.append(remains & 1)
        remains = remains >> 1

    retreverse.reverse()

    ret = retreverse
    if None != width:
        ret_head = [ 0 ] * (width - len(ret))
        ret = ret_head + ret

    return ret


def intfrombits(bits):
    """
    Given a list of boolean values, interprets them as a binary
    encoded, MSB-first unsigned integer (with True == 1 and False
    == 0) and returns the result.
    
    >>> import lzw
    >>> lzw.intfrombits([ 1, 0, 0, 1, 1, 0, 0, 0, 0 ])
    304
    """
    ret = 0
    lsb_first = [ b for b in bits ]
    lsb_first.reverse()
    
    for bit_index in range(len(lsb_first)):
        if lsb_first[ bit_index ]:
            ret = ret | (1 << bit_index)

    return ret


def bytestobits(bytes):
    """
    Breaks a given iterable of bytes into an iterable of boolean
    values representing those bytes as unsigned integers.
    
    >>> import lzw
    >>> [ x for x in lzw.bytestobits(b"\x01\x30") ]
    [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0]
    """
    for b in bytes:
        (value,) = struct.unpack("B", b)
        for bitplusone in range(8, 0, -1):
            bitindex = bitplusone - 1
            nextbit = 1 & (value >> bitindex)
            yield nextbit


def bitstobytes(bits):
    """
    Interprets an indexable list of booleans as bits, MSB first, to be
    packed into a list of integers from 0 to 256, MSB first, with LSBs
    zero-padded. Note this padding behavior means that round-trips of
    bytestobits(bitstobytes(x, width=W)) may not yield what you expect
    them to if W % 8 != 0

    Does *NOT* pack the returned values into a bytearray or the like.

    >>> import lzw
    >>> bitstobytes([0, 0, 0, 0, 0, 0, 0, 0, "Yes, I'm True"]) == [ 0x00, 0x80 ]
    True
    >>> bitstobytes([0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0]) == [ 0x01, 0x30 ]
    True
    """
    ret = []
    nextbyte = 0
    nextbit = 7
    for bit in bits:
        if bit:
            nextbyte = nextbyte | (1 << nextbit)

        if nextbit:
            nextbit = nextbit - 1
        else:
            ret.append(nextbyte)
            nextbit = 7
            nextbyte = 0

    if nextbit < 7: ret.append(nextbyte)
    return ret
        



class BitPacker(object):
    """
    Backs a stream of integers into a variable width stream of bytes,
    widening according to the storage convention above (the next byte
    after the largest possible value for our current width is packed
    with width+1)

    Knows how to recognized CLEAR_CODE, and reset the width to
    minimum.
    """
    def __init__(self, min_width=DEFAULT_MIN_BITS):
        self._min_width = min_width

    def pack(self, codepoints):
        """
        Given an iterator of integer codepoints, returns an iterator
        over bytes containing the codepoints packed into varying
        lengths, beginning with min_width bits and growing by no
        more than one bit after the maximum value for the current
        width is observed and output.

        (If this seems unclear, then treat this method as requiring
        any integer value over a certain low threshold to appear ONLY
        after the preceeding integer has appeared in the input stream
        at least once.

        That is, pack will raise an exception if it sees 512 before it
        has seen 511 at least once in its input iterator.)

        Widths will be reset when the LZW CLEAR_CODE or
        END_OF_INFORMATION code appears in the input.

        >>> import lzw
        >>> pkr = lzw.BitPacker(9)
        >>> [ b for b in pkr.pack([ 1, 257]) ] == [ chr(0), chr(0xC0), chr(0x40) ]
        True
        """
        tailbits = []
        nextwidth = self._min_width

        for pt in codepoints:

            newbits = inttobits(pt, nextwidth)
            tailbits = tailbits + newbits

            if (pt + 1) > (2 ** nextwidth):
                msg = "Can't adapt bit width fast enough to accomodate codepoint {0}".format(pt)
                raise ValueError(msg)
            elif pt == CLEAR_CODE:
                nextwidth = self._min_width
            elif (pt + 1) == (2 ** nextwidth):
                nextwidth = nextwidth + 1
            else:
                pass # leave width alone


            while len(tailbits) > 8:
                nextbits = tailbits[:8]
                nextbytes = bitstobytes(nextbits)
                for bt in nextbytes:
                    yield struct.pack("B", bt)

                tailbits = tailbits[8:]

                       
        if tailbits:
            tail = bitstobytes(tailbits)
            for bt in tail:
                yield struct.pack("B", bt)

                


class BitUnpacker(object):
    """
    Adaptive bit unpacker for LZW codepoints. Knows how to handle
    our variable width coding scheme, and CLEAR codes.
    """
    def __init__(self, min_width=DEFAULT_MIN_BITS):
        self._pointwidth = min_width
        self._min_width = min_width



    def _adjustwidth(self, lastpoint):
        """
        >>> import lzw
        >>> upk = lzw.BitUnpacker(9)
        >>> upk._adjustwidth((2 ** 9) - 1)
        10
        """
        ret = self._pointwidth
        if lastpoint in [ CLEAR_CODE, END_OF_INFO_CODE ]:
            ret = self._min_width
        else:
            while (lastpoint + 1) >= (1 << ret):
                ret = ret + 1

        return ret



    def unpack(self, bytes):
        """
        Given an iterator of bytes, returns an iterator of integer
        code points. Auto-magically adjusts point width when it sees
        an almost-overflow in the input stream, or an LZW CLEAR_CODE
        or END_OF_INFO_CODE

        Trailing bits at the end of the given iterator, after the last
        codepoint, will be dropped on the floor.

        At the end of the iteration, or when an END_OF_INFO_CODE seen
        the unpacker will ignore the bits after the code until it
        reaches the next aligned byte. END_OF_INFO_CODE will *not*
        stop the generator, just reset the alignment and the width


        >>> import lzw
        >>> unpk = lzw.BitUnpacker(9)
        >>> [ i for i in unpk.unpack([ chr(0), chr(0xC0), chr(0x40) ]) ]
        [1, 257]
        """
        bits = []
        offset = 0
        ignore = 0
        for nextbit in bytestobits(bytes):

            offset = (offset + 1) % 8
            if ignore > 0:
                ignore = ignore - 1
                continue

            bits.append(nextbit)

            if len(bits) == self._pointwidth:
                ret = intfrombits(bits)
                bits = []

                yield ret
                self._pointwidth = self._adjustwidth(ret)

                if ret == END_OF_INFO_CODE:
                    ignore = (8 - offset) % 8


        # aforementioned floor dropping:
        # if bits:
        #     yield intfrombits(bits)



class Decoder(object):
    """
    Turns CODE POINTS, that is, integers, into string bytes. 
    Packing and unpacking the codes into binary data should 
    be handled elsewhere.
    """
    def __init__(self):
        self._clear_codes()
        self.remainder = []


    def code_size(self):
        return len(self._codepoints)

    def decode(self, codepoints):
        """
        Given an iterable codepoints, yields the corresponding
        characters. Retails the state of the codebook from call to
        call, so if you have another stream, you'll likely need
        another decoder!

        >>> import lzw
        >>> dec = lzw.Decoder()
        >>> ''.join(dec.decode([103, 97, 98, 98, 97, 32, 258, 260, 262, 121, 111, 263, 259, 261, 256]))
        'gabba gabba yo gabba'

        """
        codepoints = [ cp for cp in codepoints ]

        for cp in codepoints:
            decoded = self.decode_codepoint(cp)
            for character in decoded:
                yield character


    def decode_codepoint(self, codepoint):
        """
        Maps a code point to an output string, AND interprets control
        codes.  May return the empty string for some codepoints.

        Will raise a ValueError if given an END_OF_INFORMATION
        code. EOI codes should be handled by callers if they're
        present in our source stream.

        >>> import lzw
        >>> dec = lzw.Decoder()
        >>> beforesize = dec.code_size()
        >>> dec.decode_codepoint(0x80)
        '\\x80'
        >>> dec.decode_codepoint(0x81)
        '\\x81'
        >>> beforesize + 1 == dec.code_size()
        True
        >>> dec.decode_codepoint(256)
        ''
        >>> beforesize == dec.code_size()
        True
        """

        ret = ""

        if codepoint == CLEAR_CODE:
            self._clear_codes()
        elif codepoint == END_OF_INFO_CODE:
            raise ValueError("End of information code not supported directly by this Decoder")
        else:
            if codepoint in self._codepoints:
                ret = self._codepoints[ codepoint ]
                if None != self._prefix:
                    self._codepoints[ len(self._codepoints) ] = self._prefix + ret[0]

            else:
                ret = self._prefix + self._prefix[0]
                self._codepoints[ len(self._codepoints) ] = ret

            self._prefix = ret

        return ret


    def _clear_codes(self):
        self._codepoints = dict( (pt, struct.pack("B", pt)) for pt in range(256) )
        self._codepoints[CLEAR_CODE] = CLEAR_CODE
        self._codepoints[END_OF_INFO_CODE] = END_OF_INFO_CODE
        self._prefix = None


class Encoder(object):
    """
    Given an iterator of bytes, returns an iterator of integer codepoints.
    """
    def __init__(self, max_code_size=(2**DEFAULT_MAX_BITS)):
        """
        If given a max code size, the encoder will
        """

        self.closed = False

        self._max_code_size = max_code_size
        self._buffer = ''
        self._clear_codes()            

        if max_code_size < self.code_size():
            raise ValueError("Max code size too small, (must be at least {0})".format(self.code_size()))


    def code_size(self):
        """
        Returns a count of the known codes, including
        codes that are implicit in the data but have not
        yet been written to the sink
        """
        return len(self._prefixes)

    def flush(self):
        """
        forces a write of any buffered symbols, ALWAYS followed by a
        clear code.
        """

        flushed = []

        if self._buffer:
            flushed = [ self._prefixes[ self._buffer ] ]
            self._buffer = ''
        
        self._clear_codes()
        flushed.append(CLEAR_CODE)
        return flushed
            


    def encode(self, bytes):
        """
        Given an iterator over bytes, yields the
        corresponding stream of codepoints.
        Will clear the codes at the end of the stream.

        >>> import lzw
        >>> enc = lzw.Encoder()
        >>> [ cp for cp in enc.encode("gabba gabba yo gabba") ]
        [103, 97, 98, 98, 97, 32, 258, 260, 262, 121, 111, 263, 259, 261, 256]

        """
        for b in bytes:
            for point in self.encode_byte(b):
                yield point
        
        for point in self.flush():
            yield point

    def encode_byte(self, byte):
        """
        Casual callers are *strongly* encouraged to investigate
        encode() before messing with this method.

        Returns a list of codepoints as it is given bytes. May not
        output enough information to actually decode the given
        byte unless followed by flush(). Will add at most one
        new point to the code book, and will possibly flush
        and clear the codebook on overflow.
        """

        ret = []
        new_prefix = self._buffer
        
        if new_prefix + byte in self._prefixes:
            new_prefix = new_prefix + byte
        elif new_prefix:
            ret = [  self._prefixes[ new_prefix ] ]
            self._add_code(new_prefix + byte)
            new_prefix = byte
        
        self._buffer = new_prefix

        if self.code_size() >= self._max_code_size:
            # Relies on a cute property of adding a new code-
            # we know if we've added a new code that we're only
            # due to flush a single byte (the tail of the new code)
            # so we won't output our overflow codepoint.
            ret = ret + self.flush()

        return ret


    def _clear_codes(self):

        # Teensy hack, CLEAR_CODE and END_OF_INFO_CODE aren't
        # equal to any possible string.

        self._prefixes = dict( (struct.pack("B", codept), codept) for codept in range(256) )
        self._prefixes[ CLEAR_CODE ] = CLEAR_CODE
        self._prefixes[ END_OF_INFO_CODE ] = END_OF_INFO_CODE


    def _add_code(self, newstring):
        self._prefixes[ newstring ] = len(self._prefixes)



class ByteEncoder(object):
    """
    Combines our Encoder with bit-packing behavior.
    Knows how to read and clear the code table.
    """

    def __init__(self, min_width=DEFAULT_MIN_BITS, max_width=DEFAULT_MAX_BITS):
        self._encoder = Encoder(max_code_size=2**max_width)
        self._packer = BitPacker(min_width=min_width)


    def encodetobytes(self, bytes):
        """
        Returns an iterator of bytes, adjusting our packed width
        between minwidth and maxwidth when it detects an overflow is
        about to occur.

        >>> import lzw
        >>> enc = lzw.ByteEncoder(9,12)
        >>> bigstr = "gabba gabba yo gabba gabba gabba yo gabba gabba gabba yo gabba gabba gabba yo"
        >>> encoding = enc.encodetobytes(bigstr)
        >>> "".join( b for b in encoding )
        '3\\x98LF#\\x08\\x82\\x05\\x04\\x83\\x1eM\\xf0x\\x1c\\x16\\x1b\\t\\x88C\\xe1q(4"\\x1f\\x17\\x85C#1X\\xec.\\x00'

        """
        codepoints = self._encoder.encode(bytes)
        codebytes = self._packer.pack(codepoints)

        return codebytes


class ByteDecoder(object):
    """
    Decodes, combines bit-unpacking and interpreting a codepoint
    stream. Does not understand or handle END_OF_INFORMATION codes.
    """
    def __init__(self, min_width=DEFAULT_MIN_BITS):
        self._decoder = Decoder()
        self._unpacker = BitUnpacker(min_width=min_width)
        self.remaining = []

    def decodefrombytes(self, bytes):
        """
        Returns an iterator over the decoded bytes. Dual of ByteEncoder.encodetobytes

        >>> import lzw
        >>> dec = lzw.ByteDecoder(9)
        >>> coded = '3\\x98LF#\\x08\\x82\\x05\\x04\\x83\\x1eM\\xf0x\\x1c\\x16\\x1b\\t\\x88C\\xe1q(4"\\x1f\\x17\\x85C#1X\\xec.\\x00'
        >>> ''.join( b for b in dec.decodefrombytes(coded) )
        'gabba gabba yo gabba gabba gabba yo gabba gabba gabba yo gabba gabba gabba yo'


        """        
        codepoints = self._unpacker.unpack(bytes)
        clearbytes = self._decoder.decode(codepoints)

        return clearbytes


class PagingEncoder(object):
    """
    Handles encoding of multiple chunks or streams of encodable data,
    separated with control codes. Dual of PagingDecoder.
    """
    def __init__(self, min_width=DEFAULT_MIN_BITS, max_width=DEFAULT_MAX_BITS):
        self._min_width = min_width
        self._max_width = max_width


    def encodepages(self, pages):
        """
        Given an iterator of iterators of bytes, produces a single
        iterator containing a delimited sequence of independantly
        compressed LZW sequences, all beginning on a byte-aligned
        spot, all beginning with a CLEAR code and all terminated with
        an END_OF_INFORMATION code (and zero to seven trailing junk
        bits.)

        The dual of PagingDecoder.decodepages

        >>> import lzw
        >>> enc = lzw.PagingEncoder(9,12)
        >>> coded = enc.encodepages([ "say hammer yo hammer mc hammer go hammer", 
        ...                           "and the rest can go and play",
        ...                           "can't touch this" ])
        ...
        >>> "".join(coded)
        '\\x80\\x1c\\xcc\\'\\x91\\x01\\xa0\\xc2m6\\x99NB\\x03\\xc9\\xbe\\x0b\\x07\\x84\\xc2\\xcd\\xa68|"\\x14 3\\xc3\\xa0\\xd1c\\x94\\x02\\x02\\x80\\x18M\\xc6A\\x01\\xd0\\xd0e\\x10\\x1c\\x8c\\xa73\\xa0\\x80\\xc7\\x02\\x10\\x19\\xcd\\xe2\\x08\\x14\\x10\\xe0l0\\x9e`\\x10\\x10\\x80\\x18\\xcc&\\xe19\\xd0@t7\\x9dLf\\x889\\xa0\\xd2s\\x80@@'

        """

        for page in pages:

            encoder = Encoder(max_code_size=(2**self._max_width))
            codepoints = encoder.encode(page)
            codes_and_eoi = itertools.chain([ CLEAR_CODE ], codepoints, [ END_OF_INFO_CODE ])

            packer = BitPacker(min_width=self._min_width)
            packed = packer.pack(codes_and_eoi)

            for byte in packed: 
                yield byte


            

class PagingDecoder(object):
    def __init__(self, min_width=DEFAULT_MIN_BITS):
        self._min_width = min_width
        self._remains = []

    def next_page(self, codepoints):
        """
        Iterator over the next page of codepoints.
        """
        self._remains = []

        try:
            while 1:
                cp = codepoints.next()
                if cp != END_OF_INFO_CODE:
                    yield cp
                else:
                    self._remains = codepoints
                    break

        except StopIteration:
            pass
        

    def decodepages(self, bytes):
        """
        Takes an iterator of bytes, returns an iterator of iterators
        of uncompressed data. Expects input to conform to the output
        conventions of PagingEncoder(), in particular that "pages" are
        separated with an END_OF_INFO_CODE and padding up to the next
        byte boundary.

        BUG: Dangling trailing page on decompression.

        >>> import lzw
        >>> pgdec = lzw.PagingDecoder()
        >>> pgdecoded = pgdec.decodepages(
        ...     ''.join([ '\\x80\\x1c\\xcc\\'\\x91\\x01\\xa0\\xc2m6',
        ...               '\\x99NB\\x03\\xc9\\xbe\\x0b\\x07\\x84\\xc2',
        ...               '\\xcd\\xa68|"\\x14 3\\xc3\\xa0\\xd1c\\x94',
        ...               '\\x02\\x02\\x80\\x18M\\xc6A\\x01\\xd0\\xd0e',
        ...               '\\x10\\x1c\\x8c\\xa73\\xa0\\x80\\xc7\\x02\\x10',
        ...               '\\x19\\xcd\\xe2\\x08\\x14\\x10\\xe0l0\\x9e`\\x10',
        ...               '\\x10\\x80\\x18\\xcc&\\xe19\\xd0@t7\\x9dLf\\x889',
        ...               '\\xa0\\xd2s\\x80@@' ])
        ... )
        >>> [ "".join(pg) for pg in pgdecoded ]
        ['say hammer yo hammer mc hammer go hammer', 'and the rest can go and play', "can't touch this", '']

        """

        # No good. Doesn't deal with alignments
        unpacker = BitUnpacker(min_width=self._min_width)
        codepoints = unpacker.unpack(bytes)

        self._remains = codepoints
        while self._remains:
            nextpoints = self.next_page(self._remains)
            nextpoints = [ nx for nx in nextpoints ]

            decoder = Decoder()
            decoded = decoder.decode(nextpoints)
            decoded = [ dec for dec in decoded ]

            yield decoded


if __name__ == '__main__':
    # Functional or otherwise screwy test issues
    
    packable = [ CLEAR_CODE, 33, CLEAR_CODE, END_OF_INFORMATION ]
    
