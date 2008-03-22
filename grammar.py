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

import sys
from os.path import basename
from random import choice, uniform
from inspect import getsource

from text import split_it, write_block
from scanner import tokens
from parser import Parser
import template


def _print_error(msg, lineno=None, offset=None, fname=None):
    """Emit error messages to stderr."""
    parts = []
    if fname is not None:
        parts.append("%s:"%fname)
        if lineno is not None:
            parts.append("%d:"%lineno)
            if offset is not None:
                parts.append("%d:"%offset)
        prefix = "".join(parts)
    else:
        prefix = "error:"
    if prefix:
        prefix = prefix+" "
    print >>sys.stderr, prefix+str(msg)

class RulesError(Exception):

    """Error conditions in the set of production rules."""

    def __init__(self, msg):
        """Create an exception describing an error in a rule set.

        `msg` should be a human-readable description of the problem
        for use in an error message.
        """
        super(RulesError, self).__init__(msg)

class Conflicts(Exception):

    """Lists of conflicts in LR(1) grammars.

    In order to allow Wisent to report all discovered conflicts in one
    run, this exception represents lists of grammar conflicts.
    """

    def __init__(self):
        """Create a new Conflicts exception.

        At creation time, the exception object contains no information
        about conflicts.  All errors should be added using the `add`
        method before the exception is raised.

        Iterating over the exception object returns the recorded
        conflicts one by one.
        """
        self.list = {}

    def __len__(self):
        """The number of conflicts recorded in the exception."""
        return len(self.list)

    def __iter__(self):
        return self.list.iteritems()

    def add(self, data, text):
        """Add another conflict to the list.

        `data` is a list of tuples describing the conflict, each tuple
        encoding information about one of the conflicting actions.
        For shift actions the first element of the tuple is the string
        'S', the second element is the index of the corresponding
        production rule and the third element is the position of the
        shifted element within the rule.  For reduce actions the first
        element of the tuple is the string 'R' and the second element
        is the index of the production rule involved.

        `text` is a string of terminal symbols which illustrates the
        conflict: after the tokens from `text[:-1]` are read and with
        lookahead symbol `text[-1]`, each of the actions described by
        `data` can be applied.
        """
        if data in self.list:
            if len("".join(text)) >= len("".join(self.list[data])):
                return
        self.list[data] = text

    def print_conflicts(self, rules, rule_locations={}, fname=None):
        """Print a human-readable description of the errors to stderr.

        `rules` must be a dictionary mapping rule indices to
        production rules.  The optional argument `rule_locations`, if
        present, must be a dictionary such that `rule_locations[k][n]`
        is a tuple giving the line and column of the `n`th token of
        the `k`th grammar rule in the source file.  `fname`, if given,
        should be the input file name.
        """
        ee = []
        def rule_error(k, n):
            r = [ repr(X) for X in rules[k] ]
            if n < len(r):
                tail = " ".join(r[1:n])+"."+" ".join(r[n:])
            else:
                tail = " ".join(r[1:])
            ee.append("    "+r[0]+": "+tail+";")
            try:
                loc = rule_locations[k][n]
            except KeyError:
                loc = (None,None)
            while ee:
                msg = ee.pop(0)
                _print_error(msg, loc[0], loc[1], fname=fname)

        for res, text in self:
            shift = []
            red = []
            for m in res:
                if m[0] == 'S':
                    shift.append(m[1:])
                else:
                    red.append(m[1])

            if len(red)>1:
                conflict = "reduce-reduce"
            else:
                conflict = "shift-reduce"
            ee.append("%s conflict: the input"%conflict)
            head = " ".join(x for x in text[:-1] if x)
            ee.append("    "+head+"."+text[-1]+" ...")

            if shift:
                msg = "  can be shifted using "
                if len(shift)>1:
                    msg += "one of the production rules"
                else:
                    msg += "the production rule"
                ee.append(msg)
                for k, n in shift:
                    rule_error(k, n)
                cont = "or "
            else:
                cont = ""

            for k in red:
                rule = rules[k]
                n = len(rule)
                ee.append("  %scan be reduced to"%cont)
                head = "".join(x+" " for x in text[:-n] if x)
                repl = head+repr(rule[0])+"."+text[-1]
                ee.append("    "+repl+" ...")
                ee.append("  using the production rule")
                rule_error(k, n)
                cont = "or "

class Unique(object):

    """Unique objects for use as markers.

    These objects are internally used to represent the start symbol
    and the end-of-input marker of the grammar.
    """

    def __init__(self, label):
        """Create a new unique object.

        `label` is a string which is used as a textual representation
        of the object.
        """
        self.label = label

    def __repr__(self):
        """Return the `label` given at object construction."""
        return self.label

class Grammar(object):

    """Represent a context free grammar."""

    def __init__(self, rules, cleanup=True, **kwargs):
        """Create a new grammar instance.

        The argument 'rules' must be an iterable, listing all
        production rules.  Each production rule must be a list or
        tuple with a non-terminal as the first element, and the
        replacement of the non-terminal in the remaining elements.

        The optional keyword argument 'start' denotes the start symbol
        of the grammar.  If it is not given, the head of the first
        rule is used as the start symbol.
        """
        self.rules = {}
        self.symbols = set()
        self.terminals = set()
        self.nonterminals = set()

        rules = dict(enumerate(rules))
        if not rules:
            raise RulesError("empty grammar")
        first = True
        for key, r in rules.iteritems():
            self.rules[key] = r
            self.nonterminals.add(r[0])
            if first:
                self.start = r[0]
                first = False
            for s in r[1:]:
                self.symbols.add(s)

        if "start" in kwargs:
            self.start = kwargs["start"]
            if self.start not in self.nonterminals:
                msg = "start symbol %s is not a nonterminal"%repr(self.start)
                raise RulesError(msg)

        self.terminals = self.symbols - self.nonterminals
        if cleanup:
            self._cleanup()
        self.nonterminals = frozenset(self.nonterminals)
        self.terminals = frozenset(self.terminals)
        self.symbols = frozenset(self.symbols)

        self.rule_from_head = {}
        for X in self.symbols:
            self.rule_from_head[X] = []
        for k, rule in self.rules.iteritems():
            self.rule_from_head[rule[0]].append((k,len(rule)))

        # precompute the set of all nullable symbols
        self.nullable = frozenset(self._compute_nbtab())

        # precompute the table of all possible first symbols in expansions
        fitab = self._compute_fitab()
        self.fitab = {}
        for s in self.nonterminals|self.terminals:
            self.fitab[s] = frozenset(fitab[s])

        # precompute the table of all possible follow-up symbols
        fotab = self._compute_fotab()
        self.fotab = {}
        for s in self.nonterminals|self.terminals:
            self.fotab[s] = frozenset(fotab[s])

    def _cleanup(self):
        """Remove unnecessary rules and symbols."""
        # remove nonterminal symbols which do generate terminals
        N = set([r[0] for r in self.rules.values() if len(r) == 1])
        T = self.terminals
        R = self.rules.keys()
        done = False
        while not done:
            done = True
            for key in R:
                r = self.rules[key]
                if r[0] in N:
                    continue
                if set(r[1:])&(N|T):
                    N.add(r[0])
                    done = False
        if self.start not in N:
            tmpl = "start symbol %s doesn't generate terminals"
            raise RulesError(tmpl%repr(self.start))
        for key in R:
            if not set(self.rules[key]) <= (N|T):
                del self.rules[key]

        # remove unreachable symbols
        gamma = set([self.start])
        done = False
        while not done:
            done = True
            for key in R:
                r = self.rules[key]
                if r[0] not in gamma:
                    continue
                for w in r[1:]:
                    if w not in gamma:
                        gamma.add(w)
                        done = False
        N &= gamma
        T &= gamma
        for key in R:
            if not set(self.rules[key]) <= (N|T):
                del self.rules[key]

        # generate a terminator symbol
        s = Unique('EOF')
        T.add(s)
        self.EOF = s

        # generate a private start symbol
        s = Unique('S')
        N.add(s)
        self.rules[-1] = (s, self.start, self.EOF)
        self.start = s

        self.nonterminals = N
        self.terminals = T
        self.symbols = N|T

    def _compute_nbtab(self):
        """Compute the set of nullable symbols."""
        nbtab = set()
        done = False
        while not done:
            done = True
            for key, r in self.rules.iteritems():
                if r[0] in nbtab:
                    continue
                for s in r[1:]:
                    if s not in nbtab:
                        break
                else:
                    nbtab.add(r[0])
                    done = False
        return nbtab

    def _compute_fitab(self):
        """Compute the table of all possible first symbols in expansions."""
        fitab = {}
        for s in self.nonterminals:
            fitab[s] = set()
        for s in self.terminals:
            fitab[s] = set([s])
        done = False
        while not done:
            done = True
            for key, r in self.rules.iteritems():
                fi = set()
                for s in r[1:]:
                    fi |= fitab[s]
                    if s not in self.nullable:
                        break
                if not(fi <= fitab[r[0]]):
                    fitab[r[0]] |= fi
                    done = False
        return fitab

    def _compute_fotab(self):
        fotab = {}
        for s in self.nonterminals|self.terminals:
            fotab[s] = set()
        done = False
        while not done:
            done = True
            for key, r in self.rules.iteritems():
                for i in range(1,len(r)):
                    fo = set()
                    for s in r[i+1:]:
                        fo |= self.fitab[s]
                        if s not in self.nullable:
                            break
                    else:
                        fo |= fotab[r[0]]
                    if not (fo <= fotab[r[i]]):
                        fotab[r[i]] |= fo
                        done = False
        return fotab

    def is_nullable(self, word):
        """Check whether 'word' can derive the empty word.

        'word' must be a list of symbols.  The return value is True,
        if every symbol in 'word' is nullable.  Otherwise the return
        value is false.
        """
        for x in word:
            if x not in self.nullable:
                return False
        return True

    def first_tokens(self, word):
        """Get all possible first terminals in derivations of 'word'.

        'word' must be a list of symbols.  The return value is the set
        of all possible terminal symbols which can be the start of a
        derivation from 'word'.
        """
        fi = set()
        for s in word:
            fi |= self.fitab[s]
            if s not in self.nullable:
                break
        return fi

    def follow_tokens(self, x):
        """Get all possible follow-up tokens after 'x'.

        'x' must be a symbol.  The return value is the set of all
        terminals which can directly follow 'x' in a derivation.
        """
        return self.fotab[x]

    def shortcuts(self):
        """Return a dictionary containing short expansions for every symbol.

        Nullable symbols are expanded to empty sequences, terminal
        symbols are mapped to one-element sequences containing
        themselves.
        """
        res = {}
        for X in self.terminals:
            res[X] = (X,)
        todo = set()
        for X in self.nonterminals:
            if X in self.nullable:
                res[X] = ()
            else:
                todo.add(X)

        rtab = {}
        for X in todo:
            rtab[X] = []
        for r in self.rules.itervalues():
            if r[0] in todo:
                rtab[r[0]].append(r[1:])

        while todo:
            still_todo = set()
            for X in todo:
                good_rules = []
                for r in rtab[X]:
                    for Y in r:
                        if Y not in res:
                            break
                    else:
                        good_rules.append(r)
                if good_rules:
                    word = reduce(lambda x,y: x+y,
                                  (res[Y] for Y in good_rules[0]),
                                  ())
                    for r in good_rules[1:]:
                        w2 = reduce(lambda x,y: x+y,
                                    (res[Y] for Y in r),
                                    ())
                        if len(w2) < len(word):
                            word = w2
                    res[X] = word
                else:
                    still_todo.add(X)
            todo = still_todo
        return res

    def write_terminals(self, fd=sys.stdout, prefix=""):
        fd.write(prefix+"terminal symbols:\n")
        tt = map(repr, sorted(self.terminals-set([self.EOF])))
        for l in split_it(tt, padding=prefix+"  "):
            fd.write(l+"\n")

    def write_nonterminals(self, fd=sys.stdout, prefix=""):
        fd.write(prefix+"nonterminal symbols:\n")
        tt = map(repr, sorted(self.nonterminals-set([self.start])))
        for l in split_it(tt, padding=prefix+"  "):
            fd.write(l+"\n")

    def write_productions(self, fd=sys.stdout, prefix=""):
        fd.write(prefix+"production rules:\n")
        keys = sorted(self.rules.keys())
        for key in keys:
            r = self.rules[key]
            if r[0] == self.start:
                continue
            head = repr(r[0])
            tail = " ".join(map(repr, r[1:]))
            fd.write(prefix+"  %s -> %s\n"%(head, tail))

    def write_example(self, fd=sys.stdout, params={}):
        word = [ self.rules[-1][1] ]
        todo = set(self.rules.keys())

        nt = self.nonterminals
        def count_nt(k):
            return len([X for X in self.rules[k][1:] if X in nt])

        while todo:
            actions = []
            for i,X in enumerate(word):
                if X not in nt:
                    continue
                rules = set(k for k,l in self.rule_from_head[X])&todo
                for k in rules:
                    actions.append((i,k))
            good_actions = [ a for a in actions if count_nt(a[1])>1 ]
            if good_actions:
                actions = good_actions
            try:
                i,k = choice(actions)
            except IndexError:
                break
            word[i:i+1] = self.rules[k][1:]
            if uniform(0,1)<0.1*len(word):
                todo.discard(k)
        short = self.shortcuts()
        res = []
        for X in word:
            res.extend(repr((Y,)) for Y in short[X])

        parser = params.get("parser_name", "")
        if parser.endswith(".py"):
            parser = basename(parser)[:-3]
        else:
            parser = "..."

        write_block(fd, 0, """
        #! /usr/bin/env python
        # %(example_name)s - illustrate the use of a Wisent-generated parser
        # example code autogenerated on %(date)s
        # generator: wisent %(version)s, http://seehuhn.de/pages/wisent
        """%params, first=True)
        if 'fname' in params:
            fd.write("# source: %(fname)s\n"%params)

        fd.write('\n')
        fd.write('from %s import Parser\n'%parser)

        write_block(fd, 0, getsource(template.print_tree))

        fd.write('\n')
        for l in split_it(res, start1="input = [ ", end2=" ]"):
            fd.write(l+'\n')
        write_block(fd, 0, """
        p = Parser()
        try:
            tree = p.parse(input)
        except p.ParseErrors, e:
            for token,expected in e.errors:
                if token[0] == p.EOF:
                    print >>stderr, "unexpected end of file"
                    continue

                found = repr(token[0])
                if len(expected) == 1:
                    msg = "missing %s (found %s)"%(repr(expected[0]), found)
                else:
                    msg1 = "parse error before %s, "%found
                    l = sorted([ repr(s) for s in expected ])
                    msg2 = "expected one of "+", ".join(l)
                    msg = msg1+msg2
                print >>stderr, msg
            raise SystemExit(1)
        """)
        fd.write('\n')
        fd.write('print_tree(tree, p.terminals)\n')

######################################################################
# read grammar files

def _parse_grammar_file(fd, params={}):
    """Read a grammar file and return the resulting parse tree.

    The return value of this function is a tuple, consisting of the
    parse tree (or None in case of an unrecoverable error) and a
    boolean indicating whether errors (recoverable or unrecoverable)
    were found.

    If the grammar file contains errors, error messages are printed to
    stderr.
    """
    max_err = 100
    p = Parser(max_err=max_err)
    try:
        tree = p.parse(tokens(fd))
        has_errors = False
    except SyntaxError, e:
        _print_error(e.msg, e.lineno, e.offset,
                     fname=params.get("fname", None))
        tree = None
        has_errors = True
    except p.ParseErrors, e:
        for token,expected in e.errors:
            if token[0] == p.EOF:
                _print_error("unexpected end of file",
                             fname=params.get("fname", None))
                continue

            def quote(x):
                s = str(x)
                if not s.isalpha():
                    s = "'"+s+"'"
                return s
            tp = quote(token[0])
            val = quote(token[1])
            if val and tp != val:
                found = "%s %s"%(tp, repr(token[1]))
            else:
                found = tp

            if p.EOF in expected:
                expected.remove(p.EOF)
                expect_eol = True
            else:
                expect_eol = False
            if len(expected) == 1:
                missing = quote(expected[0])
                _print_error("missing %s (found %s)"%(missing, found),
                             token[2], token[3],
                             fname=params.get("fname", None))
                continue

            msg1 = "parse error before %s"%found
            l = sorted([ quote(s) for s in expected ])
            if expect_eol:
                l.append("end of line")
            msg2 = "expected "+", ".join(l[:-1])+" or "+l[-1]
            _print_error(msg1+", "+msg2, token[2], token[3],
                         fname=params.get("fname", None))
        tree = e.tree
        has_errors = True
        if len(e.errors) == max_err and tree is None:
            _print_error("too many errors, giving up ...",
                         fname=params.get("fname", None))
    return tree, has_errors

def _extract_rules(tree, aux={}):
    """Extract the grammar rules from the parse tree.

    This generator yields the grammar rules one by one.  The special
    "*" and "+" suffix tokens are expanded here.

    As a side-effect, all transparent symbols are added to the set
    'aux'.
    """
    for rule in tree[1:]:
        # rule[0] == 'rule'
        head = rule[1]
        # rule[2] == (':', ...)
        # repaired trees have no payload
        if len(head)<2:
            head = ('token', '')+rule[2][2:]

        if head[0] == "token" and head[1].startswith("_"):
            aux.add(head[1])
        for r in rule[3:]:
            if r[0] == "list":
                tail = list(r[1:])
                for i,x in enumerate(tail):
                    if not x:
                        # repaired trees have no payload
                        tail[i] = ('', )+rule[2][2:]
            else:
                # at a '|' or ';'
                res = [ head ]+tail+[ (';',';')+r[2:] ]

                todo = []
                for i in range(len(res)-2, 1, -1):
                    y = res[i]
                    if y[0] in [ '+', '*' ]:
                        x = res[i-1]
                        new = x[1]+y[0]
                        if new not in aux:
                            aux.add(new)
                            todo.append((new,)+x[1:])
                        res[i-1:i+1] = [ ('token',new)+x[2:] ]

                force = []
                i = 0
                while i < len(res):
                    x = res[i]
                    if x[0] == "!":
                        force.append(i)
                        del(res[i])
                    else:
                        i += 1

                yield [ x[1:] for x in res ], force
                for x in todo:
                    h = x[0]
                    a = (h,)+x[2:]
                    b = x[1:]
                    c = (';',)+x[2:]
                    if h[-1] == '+':
                        yield [ a, b, c ], []
                        yield [ a, a, b, c ], []
                    elif h[-1] == '*':
                        yield [ a, c ], []
                        yield [ a, a, b, c ], []

def read_grammar(fd, params={}, checkfunc=None):
    """Convert a grammar file into a `Grammar` object.

    This function reads the textual description of a grammar from a
    file.  If the contents of this file are valid, a `Grammar` object
    is returned.  Otherwise a list of errors is printed to `stderr`
    and the program is terminated.
    """
    fname = params.get("fname", None)
    tree, has_errors = _parse_grammar_file(fd)
    if tree is None:
        raise SystemExit(1)

    def postprocess(rr, rule_locations, overrides):
        """Postprocess the output of `rules`

        This removes trailing semi-colons and extracts the line number
        information and the conflict override information.
        """
        for k,r_f in enumerate(rr):
            r,force = r_f
            rule_locations[k] = tuple(x[1:] for x in r)
            overrides[k] = frozenset(force)
            yield tuple(x[0] for x in r[:-1])

    aux = set()
    rule_locations = {}
    overrides = {}
    rr = postprocess(_extract_rules(tree, aux), rule_locations, overrides)
    params['transparent_tokens'] = aux
    params['overrides'] = overrides

    try:
        g = Grammar(rr)
    except RulesError, e:
        _print_error(e, fname=fname)
        raise SystemExit(1)

    if checkfunc is not None:
        try:
            res = checkfunc(g, params)
        except Conflicts, e:
            e.print_conflicts(g.rules, rule_locations, fname)
            n = len(e)
            if n == 1:
                msg = "1 conflict"
            else:
                msg = "%d conflicts"%n
            _print_error("%s, aborting ..."%msg, fname=fname)
            has_errors = True
    else:
        res = g

    if has_errors:
        raise SystemExit(1)

    return res
