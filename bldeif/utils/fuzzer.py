# Copyright 2012 Rally Software Development Corp. All Rights Reserved.

##########################################################################################
#
# This really basic algorithm obfuscates but does not encrypt strings
#
# Thanks to Erika for the idea about adding some text at the beginning of the encoded target.
# This clues people in that the result of the fuzzing is just fuzz and also makes sure that the 
# defuzzing of the fuzzed target will not fail.
#
##########################################################################################

import base64
import types
import re

##########################################################################################

ENCODED_TEXT_PATTERN = re.compile(r'^encoded(-.*[^-])$')

##########################################################################################

class Fuzzer(object):
    SEPARATOR = "-"
    ENCODED = "encoded" + SEPARATOR

    @staticmethod
    def encode(target):
        if not target:
            return target
        if not type(target) == str:  # could we ever use something like str(target) or something more elegantgType
            return target
        bytes_for_encoding = target.encode('UTF-8', 'ignore')
        b64_encoded_string = base64.b64encode(bytes_for_encoding).decode('UTF-8')
        chars = [char for char in b64_encoded_string if ord(char) != 10]
        return '%s%s' % (Fuzzer.ENCODED, Fuzzer.SEPARATOR.join(chars))
    
    fuzz = encode

    @staticmethod
    def decode(target):
        if not Fuzzer.isEncoded(target):
            return target
        return base64.b64decode(Fuzzer.encoding(target)).decode('UTF-8')

    defuzz = decode
        
    @staticmethod     
    def encoding(target):
        """
            Given a parm that should be the result of an encoding, 
            return back the portion that can be decoded, 
            ie., after the 'encoded-' prefix with alternating '-' 
            chars removed.
        """
        if not target:
            return target
        chopped = target.rstrip('-')  # chop off any trailing '-' char...
        mo = ENCODED_TEXT_PATTERN.match(chopped)
        if not mo:
            return target
        dashed_encoding = mo.group(1)
        raw_encoding = dashed_encoding[1::2] # start at ix 1, and step by 2
        return raw_encoding

    @staticmethod    
    def isEncoded(target):
        """
            return a boolean indication as to whether the target looks like an encoding
            that was produced by a Fuzzer.
        """
        if not target:
            return False

        if not target.startswith(Fuzzer.ENCODED):
            return False
        chopped = target.rstrip('-')  # chop off any trailing '-' char...
        mo = ENCODED_TEXT_PATTERN.match(chopped)
        if not mo:
            return False
        dashed_encoding = mo.group(1)
        num_dashes   = dashed_encoding.count('-')
        just_letters = dashed_encoding.replace('-', '')
        num_letters  = len(just_letters)
        if num_dashes != num_letters:
            #print "unequal number of dashes(%d) and non-dashes(%d)" % (num_dashes, num_letters)
            return False
        encoding = dashed_encoding[1::2]  # start at ix 1, and step by 2
        if len(encoding) != num_dashes:
            return False
        return True

########################################################################################

def test():
    fuzz_target = 'kipster-t@netflix.net'
    print("fuzz target: |%s|" % fuzz_target)
    encoded = Fuzzer.encode(fuzz_target)
    print("     target   encoded: |%s|" % encoded)
    decoded = Fuzzer.decode(encoded)
    print("     encoding decoded: |%s|" % decoded)
    fooled = Fuzzer.isEncoded('encod-e-d-V-2-7-b-G-s-9-M')
    print("  was i fooled? %s" % fooled)

########################################################################################
########################################################################################

if __name__ == '__main__':
    test()
