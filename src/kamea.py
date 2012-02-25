'''
Created on Feb 21, 2012

@author: misha
'''
import struct

_CODES = (('PP_LINE', 0), ('PP_ARC', 1), ('PR_ARC', 2), ('PZ_ARC', 3),
          ('PRZ_ARC', 30), ('LINE', 4), ('ARC', 6), ('REL_ARC', 7), ('SET_PARK', 8),
          ('GO_PARK', 9), ('SET_ZERO', 10), ('GO_ZERO', 11), ('ON', 12), ('OFF', 13),
          ('SPEED', 14), ('SCALE_X', 15), ('SCALE_Y', 16), ('SCALE_Z', 17), ('TURN', 18),
          ('LABEL', 19), ('CALL', 20), ('RET', 21), ('GOTO', 22), ('LOOP', 23),
          ('ENDLOOP', 24), ('STOP', 25), ('FINISH', 26), ('COMMENT', 27), ('PAUSE', 28),
          ('SUB', 31), ('SPLINE', 40))

_str_to_code = dict(_CODES)
_code_to_str = dict([(b, a) for a, b in _CODES])

MAX_SPD = 8
MIN_SPD = 1
SPDDEF = 0

class ParseError(Exception):
    pass

class WriteError(Exception):
    pass
    
class PointRef(object):
    def __init__(self, val):
        if isinstance(val, PointRef):
            self._val = val._val
        else:
            val = int(val)
            if val < 0:
                raise ValueError('Invalid point reference: %d' % val)
            self._val = val
    
    def __eq__(self, other):
        return self._val == other._val
    
    def __ne__(self, other):
        return self._val != other._val
    
    def __repr__(self):
        return repr(self._val)
    
    def get(self):
        return self._pt
    
class NameRef(object):
    def __init__(self, val):
        if isinstance(val, NameRef):
            self._val = val._val
        else:
            self._val = val

    def __eq__(self, other):
        return self._val == other._val
    
    def __ne__(self, other):
        return self._val != other._val
    
    def __repr__(self):
        return self._val
    
class Floating(object):
    def __init__(self, val):
        if isinstance(val, Floating):
            self._val = val._val
        else:
            self._val = float(val)

    def __eq__(self, other):
        if isinstance(other, Floating):
            return self._val == other._val
        else:
            return self._val == other
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __repr__(self):
        return '%.1f' % self._val
    
_command_metadata = {'PP_LINE': {'req_pars': (('start_point', PointRef), ('end_point', PointRef), ('dz', Floating)),
                                 'has_speed': True},
                     'PP_ARC': {'req_pars': (('start_point', int), ('mid_point', int), ('end_point', int)),
                                'has_speed': True},
                     'PR_ARC': {'req_pars': (('start_point', int), ('end_point', int), ('radius', Floating)),
                                'has_speed': True,},
                     'PZ_ARC': {'req_pars': (('start_point', int), ('mid_point', int), ('dz', Floating)),
                                'has_speed': True,},
                     'PRZ_ARC': {'req_pars': (('start_point', int), ('end_point', int), ('radius', Floating), ('dz', Floating)),
                                 'has_speed': True,},
                     'LINE': {'req_pars': (('dx', Floating), ('dy', Floating), ('dz', Floating)),
                              'has_speed': True,},
                     'ARC': {'req_pars': (('radius', Floating), ('al', Floating), ('fi', Floating)),
                             'has_speed': True,},
                     'REL_ARC': {'req_pars': (('dx', Floating), ('dy', Floating), ('radius', Floating)),
                                 'has_speed': True,},
                     'ON': {'req_pars': (('device', int),)},
                     'OFF': {'req_pars': (('device', int),)},
                     'SCALE_X': {'req_pars': (('old_scale', int), ('new_scale', int))},
                     'SCALE_Y': {'req_pars': (('old_scale', int), ('new_scale', int))},
                     'SCALE_Z': {'req_pars': (('old_scale', int), ('new_scale', int))},
                     'TURN': {'req_pars': (('mirror_x', bool), ('mirror_y', bool), ('angle', Floating))},
                     'SPEED': {'req_pars': (('speed', int),)},
                     'SET_PARK': {},
                     'GO_PARK': {},
                     'SET_ZERO': {},
                     'GO_ZERO': {'x': ()},
                     'CALL': {'req_pars': (('proc_name', NameRef),),},
                     'RET': {},
                     'LABEL': {'req_pars': (('name', str),),},
                     'GOTO': {'req_pars': (('label_name', NameRef),),},
                     'SUB': {'req_pars': (('name', str),),},
                     'LOOP': {'req_pars': (('n', int),)},
                     'ENDLOOP': {},
                     'STOP': {},
                     'FINISH': {},
                     'PAUSE': {'req_pars': (('delay', Floating),)},
                     'COMMENT': {'req_pars': (('text', str),),},
                     'SPLINE': {'req_pars': (('p1', int), ('p2', int), ('p3', int), ('p4', int))},
                     }

MAX_CMD_LEN = 30

def Instruction(instr_type, **kwargs):
    instr = _Instruction(instr_type)
    instr._metadata = _command_metadata[instr_type]
    req_pars = instr._metadata.get('req_pars', ())
    for name, conv in req_pars:
        setattr(instr, name, conv(kwargs[name]))
    if instr._metadata.get('has_speed'):
        instr.spd = kwargs.get('spd', SPDDEF)
    if instr_type == 'PP_LINE' and 'updown' in kwargs:
        instr.updown = kwargs['updown']
    return instr

class _Instruction(object):
    def __init__(self, instr_type):
        self.instr_type = instr_type

    def __eq__(self, other):
        for key in self.__dict__:
            if key[0] != '_':
                if self.__dict__[key] != other.__dict__[key]:
                    return False
        return True
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __repr__(self):
        params = []
        for key in self.__dict__:
            if key[0] != '_' and key != 'instr_type':
                params.append('%s=%s' % (key, repr(getattr(self, key))))
        params_str = ','.join(params)
        return 'Instruction(%s%s)' % (repr(self.instr_type), ',' + params_str if params_str else '')

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
        instr_code, = struct.unpack('B', instr_buf[0])
        instr_type = _code_to_str.get(instr_code)
        if instr_type is None:
            _instr_error('Invalid command %s' % instr_type, instr_offset)
        metadata = _command_metadata[instr_type]
        params_len, = struct.unpack('B', instr_buf[1])
        if params_len > MAX_CMD_LEN:
            _instr_error('Invalid command length %d' % params_len, instr_offset)

        params_str = instr_buf[2:2 + params_len]
        instr = _Instruction(instr_type)
        instr._offset = instr_offset
        if instr_type == 'PP_LINE':
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

        if instr_type == 'SUB':
            if instr.name in subs:
                _instr_error("Procedure redefined: '%s'" % instr.name, instr_offset)
            subs.add(instr.name)
        elif instr_type == 'CALL':
            sub_refs.append(instr)
        elif instr_type == 'LABEL':
            if instr.name in labels:
                _instr_error("Label redefined: '%s'" % instr.name, instr_offset)
            labels.add(instr.name)
        elif instr_type == 'GOTO':
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
        code_buf = struct.pack('B', _str_to_code[instr.instr_type])
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
