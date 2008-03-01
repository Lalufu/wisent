#! /usr/bin/env python
#
# Copyright (C) 2008  Jochen Voss <voss@seehuhn.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from sys import argv, stderr
from grammar import Grammar
from wifile import read_rules
from text import layout_list
from sniplets import emit_class_parseerror, emit_rules

class LR0(Grammar):

    def __init__(self, *args, **kwargs):
        Grammar.__init__(self, *args, **kwargs)

        self.starts = {}
        for X in self.symbols:
            self.starts[X] = []
        for k,s in self.rules.items():
            self.starts[s[0]].append((k,len(s),1))

    def closure(self, U):
        U = set(U)
        current = U
        while current:
            new = set()
            for key,l,n in current:
                if n == l: continue
                r = self.rules[key]
                X = r[n]

                for x in self.starts[X]:
                    if x not in U:
                        new.add(x)
            U |= new
            current = new
        return frozenset(U)

    def goto(self, U, X):
        rules = self.rules
        T = [ (key,l,n+1) for key,l,n in U if n<l and rules[key][n]==X ]
        return self.closure(T)

    def tables(self):
        stateno = 0
        T = {}
        Tinv = {}
        E = {}

        for key in self.rules:
            if self.rules[key][0] == self.start:
                break
        state = self.closure([ (key,len(self.rules[key]),1) ])
        T[stateno] = state
        Tinv[state] = stateno
        stateno += 1

        done = False
        while not done:
            done = True
            for I in T.keys():
                if I not in E: E[I] = {}
                for key,l,n in T[I]:
                    if n == l: continue
                    r = self.rules[key]
                    X = r[n]
                    J = self.goto(T[I], X)
                    if J not in Tinv:
                        T[stateno] = J
                        Tinv[J] = stateno
                        stateno += 1
                        done = False
                    if X not in E[I]: E[I][X] = []
                    if Tinv[J] not in E[I][X]:
                        E[I][X].append(Tinv[J])
                        done = False
        return  T, E

g = LR0(read_rules(argv[1]))
T, E = g.tables()

rtab = {}
for I in T:
    reductions = []
    for key,l,n in T[I]:
        r = g.rules[key]
        if l == n:
            reductions.append((key, r[0], n-1))
    if len(reductions) == 1:
        key,l,n = reductions[0]
        for X in g.follow_tokens(r[0]):
            rtab[(I,X)] = (key, l, n)
    elif len(reductions) > 1:
        print >>stderr, "not a SLR grammar (reduce-reduce conflict)"
        raise SystemExit(1)

stab = {}
gtab = {}
for I in E:
    EI = E[I]
    if not EI:
        continue
    for X in EI:
        if (I,X) in rtab:
            print >>stderr, "not a SLR grammar (shift-reduce conflict)"
            raise SystemExit(1)
        JJ = EI[X]
        if len(JJ)>1:
            # TODO: can this really occur?
            print >>stderr, "not a SLR grammar (shift-shift conflict)"
            raise SystemExit(1)
        J = JJ[0]
        if X in g.terminal:
            stab[(I,X)] = J
            if X == g.terminator:
                final_state = J
        else:
            gtab[(I,X)] = J

print "from itertools import chain"
print
emit_class_parseerror()
print
print "class Parser(object):"
print
print "    _rtab = {"
for l in layout_list("        ", ["%s: %s"%(repr(i),repr(rtab[i])) for i in rtab], ""):
    print l
print "    }"
print
print "    _stab = {"
for l in layout_list("        ", ["(%d,%s): %s"%(i,repr(x),stab[(i,x)]) for i,x in stab], ""):
    print l
print "    }"
print
print "    _gtab = {"
for l in layout_list("        ", ["(%d,%s): %s"%(i,repr(x),gtab[(i,x)]) for i,x in gtab], ""):
    print l
print "    }"
print
print "    def __init__(self):"
print "        pass"
print
print "    def _peek(self):"
print "        if not self.valid:"
print "            next = self.input.next()"
print "            self.t,self.val = next[0], next[1:]"
print "            self.valid = True"
print "        return self.t"
print
print "    def _shift(self):"
print "        t = self._peek()"
print "        self.stack.append((self.state,t,self.val))"
print "        self.state = self._stab[(self.state,t)]"
print "        self.valid = False"
print
print "    def parse(self, input):"
print "        self.input = chain(input,[(%s,)])"%repr(g.terminator)
print "        self.valid = False"
print "        self.state = 0"
print "        self.stack = []"
print "        while self.state != %s:"%final_state
print "            X = self._peek()"
print "            if (self.state,X) in self._rtab:"
print "                key,X,n = self._rtab[(self.state,X)]"
print "                oldstate = self.stack[-n][0]"
print "                self.stack[-n:] = [ (oldstate, X,[(Y,val) for s,Y,val in self.stack[-n:]]) ]"
print "                if X == %s:"%repr(g.start)
print "                    break"
print "                self.state = self._gtab[(oldstate,X)]"
print "            else:"
print "                self._shift()"
print "                "
print "        return (self.stack[0][1], self.stack[0][2])"
