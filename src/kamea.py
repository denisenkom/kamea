'''
Created on Feb 21, 2012

@author: misha
'''
import struct

PP_LINE = 0x00
PP_ARC = 0x01
PR_ARC = 0x02
PZ_ARC = 0x03
PRZ_ARC = 0x1e
LINE = 0x04
ARC = 0x06
REL_ARC = 0x07
SET_PARK = 0x08 
GO_PARK = 0x09
SET_ZERO = 0x0a
GO_ZERO = 0x0b
ON = 0x0c
OFF = 0x0d
SPEED = 0x0e
SCALE_X = 0x0f
SCALE_Y = 0x10
SCALE_Z = 0x11
TURN = 0x12
LABEL = 0x13
CALL = 0x14
RET = 0x15
GOTO = 0x16
LOOP = 0x17
ENDLOOP = 0x18
STOP = 0x19
FINISH = 0x1a
COMMENT = 0x1b
PAUSE = 0x1c
SUB = 0x1f
SPLINE = 0x28

MAX_SPD = 8
MIN_SPD = 1
SPDDEF = 0

class ParseError(Exception):
    pass

class WriteError(Exception):
    pass
    
class PointRef(object):
    def __init__(self, val):
        if isinstance(val, str):
            val = int(val)
        if val < 0:
            raise ValueError('Invalid point reference: %d' % val)
        self._val = val
    
    def __eq__(self, other):
        return self._val == other._val
    
    def __ne__(self, other):
        return self._val != other._val
    
    def get(self):
        return self._pt
    
class NameRef(object):
    def __init__(self, val):
        self._val = val

    def __eq__(self, other):
        return self._val == other._val
    
    def __ne__(self, other):
        return self._val != other._val
    
_command_metadata = {PP_LINE: {'req_pars': (('start_point', PointRef), ('end_point', PointRef), ('dz', float)),
                               'has_speed': True,
                               },
                     PP_ARC: {'req_pars': (('start_point', int), ('mid_point', int), ('end_point', int)),
                              'has_speed': True,
                              },
                     PR_ARC: {'req_pars': (('start_point', int), ('end_point', int), ('radius', float)),
                              'has_speed': True,},
                     PZ_ARC: {'req_pars': (('start_point', int), ('mid_point', int), ('dz', float)),
                              'has_speed': True,},
                     PRZ_ARC: {'req_pars': (('start_point', int), ('end_point', int), ('radius', float), ('dz', float)),
                               'has_speed': True,},
                     LINE: {'req_pars': (('dx', float), ('dy', float), ('dz', float)),
                            'has_speed': True,},
                     ARC: {'req_pars': (('radius', float), ('al', float), ('fi', float)),
                            'has_speed': True,},
                     REL_ARC: {'req_pars': (('dx', float), ('dy', float), ('radius', float)),
                               'has_speed': True,},
                     ON: {'req_pars': (('device', int),)},
                     OFF: {'req_pars': (('device', int),)},
                     SCALE_X: {'req_pars': (('old_scale', int), ('new_scale', int))},
                     SCALE_Y: {'req_pars': (('old_scale', int), ('new_scale', int))},
                     SCALE_Z: {'req_pars': (('old_scale', int), ('new_scale', int))},
                     TURN: {'req_pars': (('mirror_x', bool), ('mirror_y', bool), ('angle', float))},
                     SPEED: {'req_pars': (('speed', int),)},
                     SET_PARK: {},
                     GO_PARK: {},
                     SET_ZERO: {},
                     GO_ZERO: {'x': ()},
                     CALL: {'req_pars': (('proc_name', NameRef),),},
                     RET: {},
                     LABEL: {'req_pars': (('name', str),),},
                     GOTO: {'req_pars': (('label_name', NameRef),),},
                     SUB: {'req_pars': (('name', str),),},
                     LOOP: {'req_pars': (('n', int),)},
                     ENDLOOP: {},
                     STOP: {},
                     FINISH: {},
                     PAUSE: {'req_pars': (('delay', float),)},
                     COMMENT: {'req_pars': (('text', str),),},
                     SPLINE: {'req_pars': (('p1', int), ('p2', int), ('p3', int), ('p4', int))},
                     }

MAX_CMD_LEN = 30

class Instruction(object):
    def __init__(self, instr_type, **kwargs):
        self.instr_type = instr_type
        self.__dict__.update(kwargs)
    def __eq__(self, other):
        for key in self.__dict__:
            if key[0] != '_':
                if self.__dict__[key] != other.__dict__[key]:
                    return False
        return True
    def __ne__(self, other):
        return not self.__eq__(other)

def _instr_error(msg, instr_offset):
    raise ParseError('%s in instruction at offset 0x%x' % (msg, instr_offset))

def parse(stream):
    instructions = []
    instr_num_buf = stream.read(2)
    if len(instr_num_buf) < 2:
        raise ParseError('Bad file format')
    instr_num, = struct.unpack('<H', instr_num_buf)
    points_refs = []
    sub_refs = []
    subs = set()
    label_refs = []
    labels = set()
    for _ in range(instr_num):
        instr_offset = stream.tell()
        instr_buf = stream.read(32)
        if len(instr_buf) < 32:
            _instr_error('Unexpected end of file', instr_offset)
        instr_type, = struct.unpack('B', instr_buf[0])
        metadata = _command_metadata.get(instr_type)
        if metadata is None:
            _instr_error('Invalid command %d' % instr_type, instr_offset)

        params_len, = struct.unpack('B', instr_buf[1])
        if params_len > MAX_CMD_LEN:
            _instr_error('Invalid command length %d' % params_len, instr_offset)

        params_str = instr_buf[2:2 + params_len]
        instr = Instruction(instr_type)
        instr._offset = instr_offset
        if instr_type == PP_LINE:
            if not params_str:
                _instr_error('Invalid parameters string', instr_offset)
            instr.updown = (ord(params_str[-1]) == 0)
            params_str = params_str[0:-1]
        req = metadata.get('req_pars', ())
        opt = ()
        if metadata.get('has_speed', False):
            opt = (int,)
        params_str = filter(lambda c: 32 <= ord(c) <= 126, params_str)
        params = params_str.split(',')
        if len(params) < len(req):
            _instr_error('Missing required parameters', instr_offset)
        for i, (name, conv) in enumerate(req):
            try:
                val = conv(params[i])
            except ValueError, e:
                _instr_error(e, instr_offset)
            setattr(instr, name, val)
            if isinstance(val, PointRef):
                points_refs.append((instr, val, name))
        opt_res = params[len(req):]
        for i in range(min(len(opt), len(params) - len(req))):
            try:
                val = opt[i](opt_res[i])
            except ValueError, e:
                _instr_error(e, instr_offset)
            opt_res[i] = opt[i](opt_res[i])
        if metadata.get('has_speed', False):
            if opt_res:
                spd = opt_res[0]
                if MIN_SPD <= spd <= MAX_SPD:
                    instr.spd = spd
                else:
                    _instr_error("Invalid speed value %s" % spd, instr_offset)
            else:
                instr.spd = SPDDEF
        if instr_type == SUB:
            if instr.name in subs:
                _instr_error("Procedure redefined: '%s'" % instr.name, instr_offset)
            subs.add(instr.name)
        elif instr_type == CALL:
            sub_refs.append(instr)
        elif instr_type == LABEL:
            if instr.name in labels:
                _instr_error("Label redefined: '%s'" % instr.name, instr_offset)
            labels.add(instr.name)
        elif instr_type == GOTO:
            label_refs.append(instr)
            
        instructions.append(instr)

    points_num_buf = stream.read(2)
    if len(points_num_buf) < 2:
        raise ParseError('Bad file format')
    points_num, = struct.unpack('<H', points_num_buf)
    points = []
    for _ in range(points_num):
        point_buf = stream.read(4)
        if len(point_buf) < 4:
            raise ParseError('Unexpected end of file when loading points')
        x, y = struct.unpack('<HH', point_buf)
        points.append((x/10.0, y/10.0))

    # validating/fixing points refs
    for instr, ref, name in points_refs:
        if ref._val >= len(points):
            _instr_error("Referenced point doesn't exist, point # %d" % ref._val, instr._offset)
        ref._pt = points[ref._val]
        
    # validating proc refs
    for instr in sub_refs:
        if instr.proc_name._val not in subs:
            _instr_error("Unresolved reference to procedure: '%s'" % instr.proc_name._val, instr._offset)
            
    # validating label refs
    for instr in label_refs:
        if instr.label_name._val not in labels:
            _instr_error("Unresolved reference to label: '%s'" % instr.label_name._val, instr._offset)

    return instructions, points

MAX_INSTRUCTIONS = 2**16 - 1

def write(instructions, stream):
    if len(instructions) > MAX_INSTRUCTIONS:
        raise WriteError("Too many instructions %d, maximum allowed is %d", (len(instructions), MAX_INSTRUCTIONS))
        
    num_buf = struct.pack('<H', len(instructions))
    stream.write(num_buf)
    for instr in instructions:
        code_buf = struct.pack('B', instr.instr_type)
        stream.write(code_buf)
        metadata = _command_metadata[instr.instr_type]
        params = [repr(getattr(instr, name)) for name, _ in metadata.get('req_pars', ())]
        if metadata.get('has_speed', False):
            if instr.spd != SPDDEF:
                params.append(repr(instr.spd))
        params_str = ','.join(params)
        if len(params_str) > 30:
            raise WriteError("Bad instruction, parameters are too long: '%s'" % params_str)
        stream.write(struct.pack('B', len(params_str)))
        stream.write(params_str + '\x00'* (30 - len(params_str)))
    stream.write('\x00\x00')
