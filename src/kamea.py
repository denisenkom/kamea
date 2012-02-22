'''
Created on Feb 21, 2012

@author: misha
'''
import os
import re
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
    def __init__(self, msg, stm):
        super(self, ParseError).__init__('%s at offset 0x%x' % (msg, stm.tell()))
        
def _split(stm, cmd, req):
    res = cmd.split(',')
    if len(res) < req:
        raise ParseError('Missing required parameters', stm)
    return res[0:req], res[req:]

def _parse_command(stm, cmd, req, opt):
    res = cmd.split(',')
    if len(res) < len(req):
        raise ParseError('Missing required parameters', stm)
    req_res = res[0:len(req)]
    for i, t in enumerate(req):
        # TODO: catch conversion error
        req_res[i] = t(req_res[i])
    opt_res = res[len(req):]
    for i, t in enumerate(opt):
        # TODO: catch conversion error
        opt_res[i] = t(opt_res[i])
    return req_res, opt_res

def _check_spd(stm, spd):
    if spd > MAX_SPD or spd < MIN_SPD:
        raise ParseError("Invalid speed value %s" % spd, stm)
    
def _get_spd(stm, opt):
    if opt:
        _check_spd(stm, opt[0])
        return opt[0]
    else:
        return SPDDEF
    
def _pp_line_handler(cmd, cmdbuf, param_l):
    cmd.updown = (cmdbuf[param_l-1] == 0)
    
    
_command_metadata = {PP_LINE: {'req_pars': (('start_point', int), ('end_point', int), ('dz', float)),
                               'has_speed': True,
                               'handler': _pp_line_handler,
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
                     OFF: {'req_pars': (('device', int),)},
                     SPEED: {'req_pars': (('speed', int),)},
                     SET_PARK: {'req_pars': ()},
                     GO_ZERO: {'req_pars': ()},
                     CALL: {'req_pars': (('proc_name', str)),},
                    }

MAX_CMD_LEN = 30

class Command(object):
    pass

def parse(stream):
    commands = []
    cmds_num, = struct.unpack('<H', stream.read(2))
    for i in range(cmds_num):
        cmd_id, = struct.unpack('B', stream.read(1))
        if cmd_id > 0x1f:
            raise ParseError('Invalid command %d' % cmd_id, stream)

        param_l, = struct.unpack('B', stream.read(1))
        if param_l > MAX_CMD_LEN:
            raise ParseError("Invalid command length %d" % param_l, stream)

        cmdbuf = stream.read(param_l)
        stream.seek(MAX_CMD_LEN - param_l, os.SEEK_CUR)
        cmd = Command()
        cmd.cmd_type = cmd_id
        metadata = _command_metadata[cmd_id]
        req = [t for _, t in metadata['req_pars']]
        opt = ()
        if metadata.get('has_speed', False):
            opt = (int,)
        req, opt = _parse_command(stream, cmdbuf, req, opt)
        for i, (name, _) in enumerate(metadata['req_pars']):
            setattr(cmd, name, req[i])
        if metadata.get('has_speed', False):
            cmd.spd = _get_spd(opt)
        handler = metadata.get('handler')
        if handler:
            handler(cmd, cmdbuf, param_l)
        commands.append(cmd)
            
#        case LINE:
#            res = sscanf(cmdbuf, "%f,%f,%f,%u", &dx, &dy, &dz, &spd);    
#            if (res < 3)
#                throw EInvalidCommandFormat("", i, cmdId);
#            if (spd > SPD8 || spd < SPDDEF)
#                throw EInvalidSpeedValue("", i, cmdId, spd);
#            program.addCommand(auto_ptr<Command>(new CLINE(dx, dy, dz, static_cast<ESpeed>(spd))));
#            break;
#
#        case ARC:
#            res = sscanf(cmdbuf, "%f,%f,%f,%u", &radius, &al, &fi, &spd);    
#            if (res < 3)
#                throw EInvalidCommandFormat("", i, cmdId);
#            if (spd > SPD8 || spd < SPDDEF)
#                throw EInvalidSpeedValue("", i, cmdId, spd);
#            program.addCommand(auto_ptr<Command>(new CARC(radius, al, fi, static_cast<ESpeed>(spd))));
#            break;
#
#        case REL_ARC:
#            res = sscanf(cmdbuf, "%f,%f,%f,%u", &dx, &dy, &radius, &spd);    
#            if (res < 3)
#                throw EInvalidCommandFormat("", i, cmdId);
#            if (spd > SPD8 || spd < SPDDEF)
#                throw EInvalidSpeedValue("", i, cmdId, spd);
#            program.addCommand(auto_ptr<Command>(new CREL_ARC(dx, dy, radius, static_cast<ESpeed>(spd))));
#            break;
#
#        case GO_PARK: program.addCommand(auto_ptr<Command>(new CGO_PARK)); break;
#        case SET_ZERO: program.addCommand(auto_ptr<Command>(new CSET_ZERO)); break;
#
#        case ON:
#            res = sscanf(cmdbuf, "%u", &device);
#            if (res < 1)
#                throw EInvalidCommandFormat("", i, cmdId);
#            if (device != SPINDEL)
#                throw EInvalidDevice("", i, cmdId, device);
#            program.addCommand(auto_ptr<Command>(new CON(static_cast<EDevice>(device))));
#            break;
#
#
#
#        case SCALE_X:
#            relative = (cmdbuf[param_l-1] == 1);
#            for (char *ptr = cmdbuf; ptr != cmdbuf+param_l; ptr++)
#                if (*ptr < ' ') *ptr = ' ';
#            res = sscanf(cmdbuf, "%u,%u", &old_scale, &new_scale);
#            if (res < 2)
#                throw EInvalidCommandFormat("", i, cmdId);
#            program.addCommand(auto_ptr<Command>(new CSCALEX(old_scale, new_scale, relative)));
#            break;
#
#        case SCALE_Y:
#            relative = (cmdbuf[param_l-1] == 1);
#            for (char *ptr = cmdbuf; ptr != cmdbuf+param_l; ptr++)
#                if (*ptr < ' ') *ptr = ' ';
#            res = sscanf(cmdbuf, "%u,%u", &old_scale, &new_scale);
#            if (res < 2)
#                throw EInvalidCommandFormat("", i, cmdId);
#            program.addCommand(auto_ptr<Command>(new CSCALEY(old_scale, new_scale, relative)));
#            break;
#
#        case SCALE_Z:
#            relative = (cmdbuf[param_l-1] == 1);
#            for (char *ptr = cmdbuf; ptr != cmdbuf+param_l; ptr++)
#                if (*ptr < ' ') *ptr = ' ';
#            res = sscanf(cmdbuf, "%u,%u", &old_scale, &new_scale);
#            if (res < 2)
#                throw EInvalidCommandFormat("", i, cmdId);
#            program.addCommand(auto_ptr<Command>(new CSCALEZ(old_scale, new_scale, relative)));
#            break;
#
#        case TURN:
#            res = sscanf(cmdbuf, "%u,%u,%f", &mirrorX, &mirrorY, &angle);
#            if (res < 3)
#                throw EInvalidCommandFormat("", i, cmdId);
#            program.addCommand(auto_ptr<Command>(new CTURN(mirrorX > 0 ? true : false, mirrorY > 0 ? true : false, angle)));
#            break;
#
#        case SUB: program.addCommand(auto_ptr<Command>(new CSUB(cmdbuf))); break;
#        case CALL: program.addCommand(auto_ptr<Command>(new CCALL(cmdbuf))); break;
#        case RET: program.addCommand(auto_ptr<Command>(new CRET)); break;
#        case LABEL: program.addCommand(auto_ptr<Command>(new CLABEL(cmdbuf))); break;
#        case GOTO: program.addCommand(auto_ptr<Command>(new CGOTO(cmdbuf))); break;
#
#        case LOOP:
#            res = sscanf(cmdbuf, "%u", &n);
#            if (res < 1)
#                throw EInvalidCommandFormat("", i, cmdId);
#            program.addCommand(auto_ptr<Command>(new CLOOP(n)));
#            break;
#
#        case ENDLOOP: program.addCommand(auto_ptr<Command>(new CENDLOOP)); break;
#        case STOP: program.addCommand(auto_ptr<Command>(new CSTOP)); break;
#        case FINISH: program.addCommand(auto_ptr<Command>(new CFINISH)); break;
#
#        case PAUSE:
#            res = sscanf(cmdbuf, "%f", &delay);
#            if (res < 1)
#                throw EInvalidCommandFormat("", i, cmdId);
#            program.addCommand(auto_ptr<Command>(new CPAUSE(delay)));
#            break;
#
#        case COMMENT: program.addCommand(auto_ptr<Command>(new CCOMMENT(cmdbuf))); break;
#
#        case SPLINE:
#            res = sscanf(cmdbuf, "%i%i%i%i", &p1, &p2, &p3, &p4);
#            if (res < 4)
#                throw EInvalidCommandFormat("", i, cmdId);
#            program.addCommand(auto_ptr<Command>(new CSPLINE(p1, p2, p3, p4)));
#            break;
#        }
#    }

    points_num = struct.unpack('<H', stream.read(2))
    points = []
    for _ in range(points_num):
        points.append(struct.unpack('<HH', stream.read(4)))

    return commands, points

if __name__ == '__main__':
    print parse(open(r'C:\Users\misha\documents\workspace\dxf2kam\test\circle.kam', 'r'))
