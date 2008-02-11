#! /usr/bin/env python

import sys
from time import strftime
from optparse import OptionParser

from grammar import Grammar
from lr1 import LR1
from text import write_block
from wifile import read_rules

wisent_version ="0.1"

parser_types = {
    "ll1": ("LL(1)",),
    "lr0": ("LR(0)",),
    "slr": ("SLR",),
    "lr1": ("LR(1)",),
}

######################################################################
# command line options

parser = OptionParser("usage: %prog [options] grammar")
parser.remove_option("-h")
parser.add_option("-h", "--help", action="store_true", dest="help_flag",
                  help="show this message")
parser.add_option("-t", "--type", action="store", type="string",
                  dest="type", default="lr1",
                  help="choose parse type (%s)"%", ".join(parser_types.keys()),
                  metavar="T")
parser.add_option("-V","--version",action="store_true",dest="version_flag",
                  help="show version information")
(options,args)=parser.parse_args()

if options.help_flag:
    parser.print_help()
    print ""
    print "Please report bugs to <voss@seehuhn.de>."
    raise SystemExit(0)
if options.version_flag:
    print """wisent %s
Copyright (C) 2007 Jochen Voss <voss@seehuhn.de>
Wisent comes with ABSOLUTELY NO WARRANTY, to the extent
permitted by law.  You may redistribute copies of Jvterm under
the terms of the GNU General Public License.  For more
information about these matters, see the file named COPYING."""%wisent_version
    raise SystemExit(0)

if len(args) < 1:
    parser.error("no grammar file specified")
if len(args) > 1:
    parser.error("too many command line arguments")
source = args[0]

if options.type not in parser_types:
    parser.error("invalid parser type %s"%options.type)
parser_name, = parser_types[options.type]

######################################################################
# output the parser class

def print_parser(fd, g, params):
    write_block(fd, 0, """
    #! /usr/bin/env python
    # %(type)s parser, autogenerated on %(date)s
    # source grammar: %(source)s
    # generator: wisent %(version)s, http://seehuhn.de/pages/wisent
    """%params)
    fd.write('\n')
    g.write_decorations(fd)

    g.write_parser(fd)

######################################################################

g = LR1(read_rules(source))

params = {
    'source': source,
    'type': parser_name,
    'version': wisent_version,
    'date': strftime("%Y-%m-%d %H:%M:%S"),
}

print_parser(sys.stdout, g, params)
