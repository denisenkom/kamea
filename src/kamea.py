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

class ValidationError(Exception):
    pass
    
class _Integer(object):
    @classmethod
    def parse(cls, val): return int(val)
    @classmethod
    def write(cls, val): return '%d' % val
    
class _Floating(object):
    @classmethod
    def parse(cls, val): return float(val)
    @classmethod
    def write(cls, val): return '%.1f' % val
    
class _String(object):
    @classmethod
    def parse(cls, val): return str(val)
    @classmethod
    def write(cls, val): return val
    
class _Boolean:
    @classmethod
    def parse(cls, val): return bool(val)
    @classmethod
    def write(cls, val): return '1' if val else '0'
    
class _PointRef(_Integer): pass
class _NameRef(_String): pass
    
_command_metadata = {'PP_LINE': {'params': (('start_point', _PointRef),
                                            ('end_point', _PointRef),
                                            ('dz', _Floating)),
                                 'has_speed': True},
                     'PP_ARC': {'params': (('start_point', _PointRef),
                                           ('mid_point', _PointRef),
                                           ('end_point', _PointRef)),
                                'has_speed': True},
                     'PR_ARC': {'params': (('start_point', _PointRef),
                                           ('end_point', _PointRef),
                                           ('radius', _Floating)),
                                'has_speed': True,},
                     'PZ_ARC': {'params': (('start_point', _PointRef),
                                           ('mid_point', _PointRef),
                                           ('dz', _Floating)),
                                'has_speed': True,},
                     'PRZ_ARC': {'params': (('start_point', _PointRef),
                                            ('end_point', _PointRef),
                                            ('radius', _Floating),
                                            ('dz', _Floating)),
                                 'has_speed': True,},
                     'LINE': {'params': (('dx', _Floating),
                                         ('dy', _Floating),
                                         ('dz', _Floating)),
                              'has_speed': True,},
                     'ARC': {'params': (('radius', _Floating),
                                        ('al', _Floating),
                                        ('fi', _Floating)),
                             'has_speed': True,},
                     'REL_ARC': {'params': (('dx', _Floating),
                                            ('dy', _Floating),
                                            ('radius', _Floating)),
                                 'has_speed': True,},
                     'ON': {'params': (('device', _Integer),)},
                     'OFF': {'params': (('device', _Integer),)},
                     'SCALE_X': {'params': (('old_scale', _Integer),
                                            ('new_scale', _Integer))},
                     'SCALE_Y': {'params': (('old_scale', _Integer),
                                            ('new_scale', _Integer))},
                     'SCALE_Z': {'params': (('old_scale', _Integer),
                                            ('new_scale', _Integer))},
                     'TURN': {'params': (('mirror_x', _Boolean),
                                         ('mirror_y', _Boolean),
                                         ('angle', _Floating))},
                     'SPEED': {'params': (('speed', _Integer),)},
                     'SET_PARK': {},
                     'GO_PARK': {},
                     'SET_ZERO': {},
                     'GO_ZERO': {'x': ()},
                     'CALL': {'params': (('proc_name', _NameRef),),},
                     'RET': {},
                     'LABEL': {'params': (('name', _String),),},
                     'GOTO': {'params': (('label_name', _NameRef),),},
                     'SUB': {'params': (('name', _String),),},
                     'LOOP': {'params': (('n', _Integer),)},
                     'ENDLOOP': {},
                     'STOP': {},
                     'FINISH': {},
                     'PAUSE': {'params': (('delay', _Floating),)},
                     'COMMENT': {'params': (('text', _String),),},
                     'SPLINE': {'params': (('p1', _PointRef),
                                           ('p2', _PointRef),
                                           ('p3', _PointRef),
                                           ('p4', _PointRef))},
                     }

MAX_CMD_LEN = 30

def _instr_error(msg, instr_offset):
    raise ParseError('%s in instruction at offset 0x%x' % (msg, instr_offset))

def parse(stream):
    instructions = []
    instr_num_buf = stream.read(2)
    if len(instr_num_buf) < 2:
        raise ParseError('Bad file format')
    instr_num, = struct.unpack('<H', instr_num_buf)
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
        instr = {'type': instr_type}
        if instr_type == 'PP_LINE':
            if not params_str:
                _instr_error('Invalid parameters string', instr_offset)
            instr['updown'] = (ord(params_str[-1]) == 0)
            params_str = params_str[0:-1]
        req = metadata.get('params', ())
        params_str = filter(lambda c: 32 <= ord(c) <= 126, params_str)
        params = params_str.split(',')
        if len(params) < len(req):
            _instr_error('Missing required parameters', instr_offset)
        for i, (name, conv) in enumerate(req):
            try:
                val = conv.parse(params[i])
            except ValueError, e:
                _instr_error(e, instr_offset)
            instr[name] = val
        params = params[len(req):]
        if metadata.get('has_speed', False) and params:
            try:
                instr['spd'] = int(params.pop())
            except ValueError, e:
                _instr_error(e, instr_offset)
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
        
    _validate(instructions, points)

    return instructions, points

MAX_INSTRUCTIONS = 2**16 - 1

def _validate(instructions, points):
    if len(instructions) > MAX_INSTRUCTIONS:
        msg = "Too many instructions %d, maximum allowed is %d" 
        raise ValidationError(msg % (len(instructions), MAX_INSTRUCTIONS))
    errors = []
    points_refs = []
    sub_refs = []
    subs = set()
    label_refs = []
    labels = set()
    for instr_idx, instr in enumerate(instructions):
        metadata = _command_metadata[instr['type']]
        for name, conv in metadata.get('params', ()):
            if name not in instr:
                msg = 'Missing required parameter %s' % name
                errors.append((msg, instr, instr_idx))
                continue
            try:
                val = conv.parse(instr[name])
            except ValueError, e:
                msg = "Invalid value '%s' for parameter %s: %s"
                errors.append((msg % (instr[name], name, e), instr, instr_idx))
                continue
            if issubclass(conv, _PointRef):
                points_refs.append((instr, instr_idx, val, name))
        if metadata.get('has_speed', False) and 'spd' in instr:
            if not (MIN_SPD <= instr['spd'] <= MAX_SPD):
                msg = "Invalid speed value %s" % instr['spd']
                errors.append((msg, instr, instr_idx))
        if instr['type'] == 'SUB':
            if instr['name'] in subs:
                msg = "Procedure redefined: '%s'" % instr['name']
                errors.append((msg, instr, instr_idx))
            else:
                subs.add(instr['name'])
        elif instr['type'] == 'CALL':
            sub_refs.append((instr, instr_idx))
        elif instr['type'] == 'LABEL':
            if instr['name'] in labels:
                msg = "Label redefined: '%s'" % instr['name']
                errors.append((msg, instr, instr_idx))
            else:
                labels.add(instr['name'])
        elif instr['type'] == 'GOTO':
            label_refs.append((instr, instr_idx))

    # validating/fixing points refs
    for instr, instr_idx, ref, name in points_refs:
        if ref >= len(points):
            msg = "Referenced point doesn't exist, point # %d" % ref
            errors.append((msg, instr, instr_idx))

    # validating proc refs
    for instr, instr_idx in sub_refs:
        if instr['proc_name'] not in subs:
            msg = "Unresolved reference: '%s'" % instr['proc_name']
            errors.append((msg, instr, instr_idx))
            
    # validating label refs
    for instr, instr_idx in label_refs:
        if instr['label_name'] not in labels:
            msg = "Unresolved reference to label: '%s'" % instr['label_name']
            errors.append((msg, instr, instr_idx))
            
    if errors:
        raise ValidationError(errors)

def write(instructions, stream):
    _validate(instructions, [])
    num_buf = struct.pack('<H', len(instructions))
    stream.write(num_buf)
    for instr in instructions:
        code_buf = struct.pack('B', _str_to_code[instr['type']])
        stream.write(code_buf)
        metadata = _command_metadata[instr['type']]
        params = []
        for name, conv in metadata.get('params', ()):
            params.append(conv.write(instr[name]))
        if metadata.get('has_speed', False):
            if instr['spd'] != SPDDEF:
                params.append(str(instr['spd']))
        params_str = ','.join(params)
        if instr['type'] == 'PP_LINE':
            params_str += '\x00' if instr['updown'] else '\x01'
        if len(params_str) > 30:
            msg = "Bad instruction, parameters are too long: '%s'" % params_str
            raise WriteError(msg)
        stream.write(struct.pack('B', len(params_str)))
        stream.write(params_str + '\x00'* (30 - len(params_str)))
    stream.write('\x00\x00')
