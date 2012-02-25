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
        fname = os.path.join(os.path.dirname(__file__), r'..\test\circle.kam')
        with open(fname, 'rb') as f:
            res = parse(f)
        self.assertEqual(res, eval(repr(res)))
        
    def test_rect_parse(self):
        fname = os.path.join(os.path.dirname(__file__), r'..\test\rect.kam')
        with open(fname, 'rb') as f:
            res = parse(f)
        self.assertEqual(res, eval(repr(res)))

    def test_empty_file(self):
        self.assertEqual(parse(StringIO('\x00\x00\x00\x00')), ([], []))

    def test_simple_instr(self):
        instrs, points = parse(StringIO('\x01\x00\x00\x080,1,2,3\x00' + '\x00' * 22 + '\x02\x00\x00\x00\x01\x00\x00\x00\x05\x00'))
        self.assertEqual(instrs, [{'type': 'PP_LINE',
                                   'start_point': PointRef(0),
                                   'end_point': PointRef(1),
                                   'dz': 2,
                                   'spd': 3,
                                   'updown': True}])
        self.assertEqual(points, [(0, 0.1), (0, 0.5)])
        self.assertEqual([instrs[0]['start_point'].get(), instrs[0]['end_point'].get()], [(0, 0.1), (0, 0.5)])

    def test_simple_instr2(self):
        b = '\x01\x00' + \
            '\x04\x0910,20,2,4' + '\x00' * 21 + \
            '\x00\x00'
        instrs, points = parse(StringIO(b))
        self.assertEqual((instrs, points), ([{'type': 'LINE',
                                              'dx': 10,
                                              'dy': 20,
                                              'dz': 2,
                                              'spd': 4} ],
                                            []))

    def test_points_load(self):
        instr, points = parse(StringIO('\x00\x00\x02\x00\x55\x00\x01\x00\x44\x00\x21\x00'))
        self.assertEqual((instr, points), ([], [(0x55/10.0, 0.1), (0x44/10.0, 0x21/10.0)]))
        
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

    def test_invalid_file12(self):
        self.assertRaises(ParseError, parse, StringIO('\x01\x00\x00\x080,-1,1,1\x01' + '\x00' * 22 + '\x00\x00'))
        #"Invalid point reference: -1 in instruction at offset 0x2"

    def test_invalid_point_reference(self):
        self.assertRaises(ParseError, parse, StringIO('\x01\x00\x00\x080,1,2,3\x00' + '\x00' * 22 + '\x01\x00\x00\x00\x01\x00'))
    
    def test_sub_redefined(self):
        self.assertRaises(ParseError, parse, StringIO('\x02\x00\x1f\x03abc' + '\x00' * 27 + '\x1f\x03abc' + '\x00' * 27 + '\x00\x00'))
        
    def test_valid_proc_reference(self):
        parse(StringIO('\x03\x00' +
                       '\x1f\x03abc' + '\x00' * 27 +\
                       '\x15\x00' + '\x00' * 30 +\
                       '\x14\x03abc' + '\x00' * 27 +\
                       '\x00\x00'))
    
    def test_invalid_proc_reference(self):
        self.assertRaises(ParseError, parse, StringIO('\x03\x00' +
                                                      '\x1f\x03abc' + '\x00' * 27 +
                                                      '\x15\x00' + '\x00' * 30 +
                                                      '\x14\x03abd' + '\x00' * 27 +
                                                      '\x00\x00'))
    
    def test_label_redefined(self):
        b = '\x02\x00' + \
            '\x13\x03abc' + '\x00' * 27 + \
            '\x13\x03abc' + '\x00' * 27 + \
            '\x00\x00'
        self.assertRaises(ParseError, parse, StringIO(b))
        
    def test_valid_label_reference(self):
        b = '\x02\x00' + \
            '\x16\x03abc' + '\x00' * 27 + \
            '\x13\x03abc' + '\x00' * 27 + \
            '\x00\x00'
        parse(StringIO(b))
    
    def test_invalid_label_reference(self):
        b = '\x02\x00' + \
            '\x16\x03abc' + '\x00' * 27 + \
            '\x13\x03abd' + '\x00' * 27 + \
            '\x00\x00'
        self.assertRaises(ParseError, parse, StringIO(b))
        
    def test_simple_save(self):
        stm = StringIO()
        instrs = [dict(type='LINE', dx=10, dy=20, dz=2, spd=4),
                  dict(type='COMMENT', text='test comment')]
        write(instrs, stm)
        b = '\x02\x00' + \
            '\x04\x0f10.0,20.0,2.0,4' + '\x00' * 15 + \
            '\x1b\x0ctest comment' + '\x00' * 18 + \
            '\x00\x00'
        self.assertEqual(stm.getvalue(), b)
        stm.pos = 0
        read_result = parse(stm)
        self.assertEqual((instrs, []), read_result)
        
    def test_too_many_instructions(self):
        self.assertRaises(WriteError, write, [dict(type='LINE', dx=10, dy=20, dz=2, spd=4)]*65536, StringIO())
        
    def test_most_instructions(self):
        class NullStream():
            def write(self, buf):
                pass
        write([dict(type='LINE', dx=10, dy=20, dz=2, spd=4)]*65535, NullStream())
        
    def test_too_long_instruction_params(self):
        self.assertRaises(WriteError, write, [dict(type='COMMENT', text='x'*31)], StringIO())

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
