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
    
class SubRef(object):
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
                     CALL: {'req_pars': (('proc_name', SubRef),),},
                     RET: {},
                     LABEL: {'req_pars': (('name', str),),},
                     GOTO: {'req_pars': (('label_name', str),),},
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
        return self.__dict__ == other.__dict__
    def __ne__(self, other):
        return self.__dict__ != other.__dict__

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
        inst = Instruction(instr_type)
        if instr_type == PP_LINE:
            if not params_str:
                _instr_error('Invalid parameters string', instr_offset)
            inst.updown = (ord(params_str[-1]) == 0)
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
            setattr(inst, name, val)
            if isinstance(val, PointRef):
                points_refs.append((instr_offset, val, inst, name))
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
                    inst.spd = spd
                else:
                    _instr_error("Invalid speed value %s" % spd, instr_offset)
            else:
                inst.spd = SPDDEF
        if instr_type == SUB:
            if inst.name in subs:
                _instr_error("Procedure redefined: '%s'" % inst.name, instr_offset)
            subs.add(inst.name)
        elif instr_type == CALL:
            sub_refs.append((instr_offset, inst))
        instructions.append(inst)

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
    for instr_offset, ref, inst, name in points_refs:
        if ref._val >= len(points):
            _instr_error("Referenced point doesn't exist, point # %d" % ref._val, instr_offset)
        ref._pt = points[ref._val]
        
    # validating proc refs
    for instr_offset, inst in sub_refs:
        if inst.proc_name._val not in subs:
            _instr_error("Unresolved reference to procedure: '%s'" % inst.proc_name._val, instr_offset)

    return instructions, points
