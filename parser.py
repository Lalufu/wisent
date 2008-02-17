#! /usr/bin/env python
# LR(1) parser, autogenerated on 2008-02-17 01:14:25
# source grammar: grammar.wi
# generator: wisent 0.1, http://seehuhn.de/pages/wisent

# terminal symbols:
#   '*' '+' ':' ';' 'string' 'token' '|'

# non-terminal symbols:
#   '_item' '_item*' '_rhs' '_tos' 'grammar' 'list' 'rule' 'rule*'

# production rules:
#   'grammar' -> 'rule*'
#   'rule*' -> 
#   'rule*' -> 'rule*' 'rule'
#   'rule' -> 'token' ':' '_rhs' ';'
#   '_rhs' -> 'list'
#   '_rhs' -> '_rhs' '|' 'list'
#   'list' -> '_item*'
#   '_item*' -> 
#   '_item*' -> '_item*' '_item'
#   '_item' -> '_tos'
#   '_item' -> '_tos' '+'
#   '_item' -> '_tos' '*'
#   '_tos' -> 'token'
#   '_tos' -> 'string'

from itertools import chain

class Parser(object):

    class ParseErrors(Exception):
    
        def __init__(self, errors, tree, EOF):
            self.errors = errors
            self.tree = tree
            self.EOF = EOF

    terminal = [ '*', '+', ':', ';', 'string', 'token', '|' ]
    EOF = object()
    _transparent = [ '_rhs', 'rule*', '_item*', '_tos', '_item' ]
    _start = object()
    _halting_state = 5

    _reduce = {
        (17,'token'): ('_item',2), (17,'string'): ('_item',2),
        (12,';'): ('_item',1), (10,'token'): ('rule',4), (15,'*'): ('_tos',1),
        (3,'token'): ('rule*',2), (0,EOF): ('rule*',0), (8,'|'): ('list',1),
        (13,'|'): ('_tos',1), (18,'|'): ('_item',2), (18,'token'): ('_item',2),
        (11,'token'): ('_item*',0), (6,'string'): ('_item*',0),
        (9,';'): ('_rhs',1), (17,'|'): ('_item',2), (1,EOF): ('grammar',1),
        (13,';'): ('_tos',1), (13,'string'): ('_tos',1), (15,'+'): ('_tos',1),
        (12,'token'): ('_item',1), (15,'|'): ('_tos',1), (16,';'): ('_rhs',3),
        (3,EOF): ('rule*',2), (6,';'): ('_item*',0), (6,'|'): ('_item*',0),
        (14,'token'): ('_item*',2), (16,'|'): ('_rhs',3),
        (11,'|'): ('_item*',0), (12,'string'): ('_item',1),
        (12,'|'): ('_item',1), (13,'token'): ('_tos',1),
        (15,'token'): ('_tos',1), (17,';'): ('_item',2),
        (15,'string'): ('_tos',1), (13,'*'): ('_tos',1),
        (6,'token'): ('_item*',0), (14,'string'): ('_item*',2),
        (5,EOF): (_start,2), (11,'string'): ('_item*',0), (10,EOF): ('rule',4),
        (18,'string'): ('_item',2), (0,'token'): ('rule*',0),
        (18,';'): ('_item',2), (9,'|'): ('_rhs',1), (11,';'): ('_item*',0),
        (14,';'): ('_item*',2), (15,';'): ('_tos',1), (13,'+'): ('_tos',1),
        (8,';'): ('list',1), (14,'|'): ('_item*',2)
    }

    _shift = {
        (2,EOF): 5, (7,';'): 10, (4,':'): 6, (1,'token'): 4, (8,'token'): 13,
        (12,'*'): 17, (12,'+'): 18, (7,'|'): 11, (8,'string'): 15
    }

    _goto = {
        (8,'_tos'): 12, (1,'rule'): 3, (8,'_item'): 14, (0,'rule*'): 1,
        (6,'_item*'): 8, (6,'_rhs'): 7, (0,'grammar'): 2, (6,'list'): 9,
        (11,'list'): 16, (11,'_item*'): 8
    }

    def __init__(self, max_err=None, errcorr_pre=4, errcorr_post=4):
        self.max_err = max_err
        self.m = errcorr_pre
        self.n = errcorr_post

    @staticmethod
    def leaves(tree):
        if tree[0]:
            yield tree[1:]
        else:
            for x in tree[2:]:
                for t in Parser.leaves(x):
                    yield t

    def _parse_tree(self, input, stack, state):
        """Internal function to construct a parse tree.
    
        'Input' is the input token stream, 'stack' is the inital stack
        and 'state' is the inital state of the automaton.
    
        Returns a 4-tuple (done, count, state, error).  'done' is a
        boolean indicationg whether parsing is completed, 'count' is
        number of successfully shifted tokens, and 'error' is None on
        success or else the first token which could not be parsed.
        """
        read_next = True
        count = 0
        while state != self._halting_state:
            if read_next:
                try:
                    readahead = input.next()
                except StopIteration:
                    return (False,count,state,None)
                read_next = False
            token = readahead[0]
    
            if (state,token) in self._reduce:
                X,n = self._reduce[(state,token)]
                if n > 0:
                    state = stack[-n][0]
                    tree = [ False, X ]
                    for s in stack[-n:]:
                        if s[1][1] in self._transparent:
                            tree.extend(s[1][2:])
                        else:
                            tree.append(s[1])
                    tree = tuple(tree)
                    del stack[-n:]
                else:
                    tree = (False, X)
                stack.append((state,tree))
                state = self._goto[(state,X)]
            elif (state,token) in self._shift:
                stack.append((state,(True,)+readahead))
                state = self._shift[(state,token)]
                read_next = True
                count += 1
            else:
                return (False,count,state,readahead)
        return (True,count,state,None)

    def _try_parse(self, input, stack, state):
        count = 0
        while state != self._halting_state and count < len(input):
            token = input[count][0]
    
            if (state,token) in self._reduce:
                X,n = self._reduce[(state,token)]
                if n > 0:
                    state = stack[-n]
                    del stack[-n:]
                stack.append(state)
                state = self._goto[(state,X)]
            elif (state,token) in self._shift:
                stack.append(state)
                state = self._shift[(state,token)]
                count += 1
            else:
                break
        return count

    def parse_tree(self, input):
        errors = []
        input = chain(input, [(self.EOF,)])
        stack = []
        state = 0
        while True:
            done,_,state,readahead = self._parse_tree(input, stack, state)
            if done:
                break
    
            expect = [ t for s,t in self._reduce.keys()+self._shift.keys()
                       if s == state ]
            errors.append(([ s[1] for s in stack ], readahead, expect))
            if self.max_err is not None and len(errors) >= self.max_err:
                raise self.ParseErrors(errors, None, self.EOF)
    
            queue = []
            def split_input(m, stack, readahead, input, queue):
                for s in stack:
                    for t in self.leaves(s[1]):
                        queue.append(t)
                        if len(queue) > m:
                            yield queue.pop(0)
                queue.append(readahead)
            in2 = split_input(self.m, stack, readahead, input, queue)
            stack = []
            done,_,state,readahead = self._parse_tree(in2, stack, 0)
            m = len(queue)
            for i in range(0, self.n):
                try:
                    queue.append(input.next())
                except StopIteration:
                    break
    
            def vary_queue(queue, m):
                for i in range(m-1, -1, -1):
                    for t in self.terminal:
                        yield queue[:i]+[(t,)]+queue[i:]
                    if queue[i][0] == self.EOF:
                        continue
                    for t in self.terminal:
                        if t == queue[i]:
                            continue
                        yield queue[:i]+[(t,)]+queue[i+1:]
                    yield queue[:i]+queue[i+1:]
            best_val = len(queue)-m+1
            best_queue = queue
            for q2 in vary_queue(queue, m):
                pos = self._try_parse(q2, [ s[0] for s in stack ], state)
                val = len(q2) - pos
                if val < best_val:
                    best_val = val
                    best_queue = q2
                    if val == len(q2):
                        break
            if best_val >= len(queue)-m+1:
                raise self.ParseErrors(errors, None, self.EOF)
            input = chain(best_queue, input)
    
        tree = stack[0][1]
        if errors:
            raise self.ParseErrors(errors, tree, self.EOF)
        return tree
