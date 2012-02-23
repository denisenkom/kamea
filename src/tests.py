'''
Created on Feb 22, 2012

@author: misha
'''
import os
import unittest
from StringIO import StringIO
from kamea import *

class Test(unittest.TestCase):
    def test_real_parse(self):
        parse(open(os.path.join(os.path.dirname(__file__), 'circle.kam'), 'r'))

    def test_empty_file(self):
        self.assertEqual(parse(StringIO('\x00\x00\x00\x00')), ([], []))

    def test_simple_instr(self):
        instrs, points = parse(StringIO('\x01\x00\x00\x084,2,1,3\x00' + '\x00' * 22 + '\x00\x00'))
        self.assertEqual(instrs, [Instruction(PP_LINE,
                                              start_point=4,
                                              end_point=2,
                                              dz=1,
                                              spd=3,
                                              updown=True)])
        self.assertEqual(points, [])

    def test_points_load(self):
        instr, points = parse(StringIO('\x00\x00\x02\x00\x55\x00\x01\x00\x44\x00\x21\x00'))
        self.assertEqual(points, [(0x55/10.0, 0.1), (0x44/10.0, 0x21/10.0)])
        
    def test_invalid_file1(self):
        self.assertRaises(ParseError, parse, StringIO())

    def test_invalid_file2(self):
        self.assertRaises(ParseError, parse, StringIO('\x01\x00'))

    def test_invalid_file3(self):
        self.assertRaises(ParseError, parse, StringIO('\x00\x00'))

    def test_invalid_file4(self):
        self.assertRaises(ParseError, parse, StringIO('\x01\x00\xab' + '\x00' * 31 + '\x00\x00'))
        #'Invalid command 171 in instruction at offset 0x2'

    def test_invalid_file5(self):
        self.assertRaises(ParseError, parse, StringIO('\x01\x00\x00\x55' + '\x00' * 30 + '\x00\x00'))
        #'Invalid command length 85 in instruction at offset 0x2'

    def test_invalid_file6(self):
        self.assertRaises(ParseError, parse, StringIO('\x01\x00\x00\x00' + '\x00' * 30 + '\x00\x00'))
        #'Invalid parameters string in instruction at offset 0x2'

    def test_invalid_file7(self):
        self.assertRaises(ParseError, parse, StringIO('\x01\x00\x00\x021\x01' + '\x00' * 28 + '\x00\x00'))
        #'Missing required parameters in instruction at offset 0x2'

    def test_invalid_file8(self):
        self.assertRaises(ParseError, parse, StringIO('\x01\x00\x00\x060,0,a\x01' + '\x00' * 24 + '\x00\x00'))
        #'could not convert string to float: a in instruction at offset 0x2'

    def test_invalid_file9(self):
        self.assertRaises(ParseError, parse, StringIO('\x01\x00\x00\x080,0,1,a\x01' + '\x00' * 22 + '\x00\x00'))
        #"invalid literal for int() with base 10: 'a' in instruction at offset 0x2"

    def test_invalid_file10(self):
        self.assertRaises(ParseError, parse, StringIO('\x01\x00\x00\x080,0,1,0\x01' + '\x00' * 22 + '\x00\x00'))
        #"Invalid speed value 0 in instruction at offset 0x2"

    def test_invalid_file11(self):
        self.assertRaises(ParseError, parse, StringIO('\x00\x00\x01\x00'))
        #"Unexpected end of file when loading points"

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
