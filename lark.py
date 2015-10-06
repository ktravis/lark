#!/usr/bin/env python
import sys

from larkparse import parse

class Val(object):
    def __init__(self, t, v=None):
        self.type = t
        self.data = v
        self.as_str = str(v)

    def __call__(self, *args):
        return self

    def __str__(self):
        return self.as_str

    def __repr__(self):
        return "val({0}, {1})".format(self.type, repr(self.data))

    def __eq__(self, other):
        return self.type == other.type and self.data == other.data

    def getmember(self, a):
        raise Exception("No dot-access for value of type '{0}'".format(self.type))

    def setmember(self, a):
        raise Exception("No dot-access for value of type '{0}'".format(self.type))

    def cleanup(self):
        pass

nil = Val('niltype', None)
nil.as_str = 'nil'
true = Val('bool', True)
true.as_str = 'true'
false = Val('bool', False)
false.as_str = 'false'

class ParamVal(Val):
    def __init__(self, v=None, params=[], cl=None, refs=[]):
        self.type = 'pval'
        self.data = v
        self.cl = cl
        self.as_str = "pval[{0}]".format(','.join(params))
        self.refs = refs
        for r in self.refs:
            self.cl.incref(r)
        self.params = params

    def __call__(self, *args):
        if len(args) != len(self.params):
            raise Exception("Not enough parameters")
        ex = Env(parent=self.cl)
        refs = []
        for k,v in zip(self.params, args):
            ex.new_assign(k, v)
        #return self.data(*refs)
        ret = self.data(ex)
        ex.cleanup()
        return ret

    def cleanup(self):
        for r in self.refs:
            self.cl.decref(r)

class Tuple(Val):
    def __init__(self, v=[], named={}):
        self.type = 'tuple'
        self.data = v
        self.named = {str(k): v for k,v in named.items()}

    def __str__(self):
        return '({0})'.format(
                ','.join([str(d) for d in self.data] + ['{0}:{1}'.format(k, str(v)) for k,v in self.named.items()])
        )

    def getmember(self, a):
        if isinstance(a, Val):
            a = a.data
        if isinstance(a, int):
            try:
                return self.data[a]
            except IndexError:
                raise Exception("Dot-access index for tuple is out of range: {0}".format(a))
        elif isinstance(a, basestring):
            try:
                return self.named[a]
            except KeyError:
                raise Exception("Dot-access member '{0}' not in tuple".format(a))
        else:
            raise Exception("Cannot dot-access tuple with member {0}".format(repr(a)))

    def length(self):
        return len(self.data)

    def labels(self):
        return Tuple([Val('string', x) for x in self.named.keys()])

    def setmember(self, a, x):
        if isinstance(a, Val):
            a = a.data
        if isinstance(a, int):
            try:
                self.data[a] = x
                return x
            except IndexError:
                raise Exception("Dot-access index for tuple is out of range: {0}".format(a))
        elif isinstance(a, basestring):
            self.named[a] = x
        else:
            raise Exception("Cannot dot-access tuple with non-int member {0}".format(repr(a)))

class Var(object):
    def __init__(self, val=nil):
        self.val = val
        self.refs = 1

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return "var({0}, {1} refs)".format(repr(self.val), self.refs)

class Ref(object):
    def __init__(self, name, addr):
        self.name = name
        self.addr = addr

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return "ref({0}, {1})".format(self.name, self.addr)

class Env(object):
    def __init__(self, memory=None, parent=None):
        self.memory = memory
        self.parent = parent
        if memory is None:
            if parent is not None:
                self.memory = parent.memory
            else:
                raise Exception("Must specify memory or parent when constructing Env.")
        self.vars = {}
        # maybe put params in env property -- env.param(0), etc
        # set when building pval, replace in parser with ('param', 0)

    def getref(self, name):
        r = self.vars.get(name, None)
        if r is None:
            if self.parent is not None:
                return self.parent.getref(name)
            else:
                raise Exception("Could not find variable '{0}'.".format(name))
        return r

    def makeref(self, name):
        if name in self.vars:
            raise Exception("Variable '{0}' already defined in this scope.".format(name))
        r = Ref(name, next_addr())
        self.vars[name] = r
        self.memory[r.addr] = Var(nil)
        return r

    def getlocal_ormakeref(self, name):
        if name in self.vars:
            r = self.getref(name)
        else:
            r = self.makeref(name)
        return r

    def incref(self, ref):
        self.memory[ref.addr].refs += 1

    def decref(self, ref):
        n = self.memory[ref.addr].refs
        n -= 1
        if n > 0:
            self.memory[ref.addr].refs = n
        else:
            del self.memory[ref.addr]

    def new_assign(self, name, val):
        ref = self.makeref(name)
        self.memory[ref.addr].val = val
        return ref

    def assign(self, ref, val):
        if ref.addr not in self.memory:
            raise Exception
        self.memory[ref.addr].val = val
        return val

    def retrieve_val(self, ref):
        if ref.addr not in self.memory:
            raise Exception
        return self.memory[ref.addr].val

    def cleanup(self):
        for n,r in self.vars.items():
            self.decref(r)

memory = { }
lastAddress = 0

def next_addr():
    global lastAddress
    a = lastAddress
    lastAddress += 1
    return a

def fn_print(env):
    print env.retrieve_val(env.getref("x"))
    return nil

root = Env(memory=memory)
root.new_assign("print", ParamVal(fn_print, params=['x'], cl=root))

def run_program(prog, env):
    last = None
    for expr in prog:
        if expr:
            last = evaluate(expr, env)
    return last

def binary_expr(op, lhs, rhs, env):
    l = evaluate(lhs, env)
    r = evaluate(rhs, env)
    if op == "+":
        return Val('num', l.data + r.data)
    elif op == "-":
        return Val('num', l.data - r.data)
    elif op == "*":
        return Val('num', l.data * r.data)
    elif op == "/":
        return Val('num', l.data / r.data)
    elif op == "<":
        return true if l.data < r.data else false
    elif op == ">":
        return true if l.data > r.data else false
    elif op == "<=":
        return true if l.data <= r.data else false
    elif op == ">=":
        return true if l.data >= r.data else false
    elif op == "==":
        return true if l.data == r.data else false
    elif op == "!=":
        return true if not (l.data == r.data) else false

def unary_expr(op, v, env):
    v = evaluate(v, env)
    if op == '-':
        assert v.type == 'num'
        return Val('num', -v.data)
    elif op == '!':
        if v == false or v == nil or not v.data:
            return true
        else:
            return false

def evaluate(expr, env):
    if isinstance(expr, Val):
        return expr
    t = expr[0]

    if t == 'binary':
        x = binary_expr(expr[1], expr[2], expr[3], env)
        return x
    elif t == 'unary':
        return unary_expr(expr[1], expr[2], env)
    elif t == 'tuple':
        members = []
        named = {}
        for x in expr[1]:
            if x[0] == 'named-member':
                mt, a = x[1]
                if mt != 'member-label-literal':
                    a = evaluate(a, env)
                    if not (a.type == 'string' or a.type == 'num'):
                        raise Exception("Cannot label member in tuple with value of type '{0}'".format(a.type))
                    a = a.data
                if a in named:
                    raise Exception("Member '{0}' redefined in tuple literal".format(a))
                named[a] = evaluate(x[2], env) 
            else:
                members.append(evaluate(x, env))
        return Tuple(members, named=named)
    elif t == 'dot':
        v = evaluate(expr[1], env)
        return v.getmember(expr[2])
    elif t == 'indirect-dot':
        v = evaluate(expr[1], env)
        return v.getmember(evaluate(expr[2], env))
    elif t == 'upval-assign':
        if env.parent is None:
            raise Exception("Cannot set upval from root scope!")
        ref = env.parent.getref(expr[1])
        return env.assign(ref, evaluate(expr[2], env))
    elif t == 'member-assign':
        d = expr[1]
        v = evaluate(d[1], env)
        a = d[2]
        if d[0] == 'indirect-dot':
            a = evaluate(a, env)
        return v.setmember(a, evaluate(expr[2], env)) # ref check?
    elif t == 'assign':
        ref = env.getlocal_ormakeref(expr[1])
        return env.assign(ref, evaluate(expr[2], env))
    elif t == 'primitive':
        return Val(expr[1][0], expr[1][1])
    elif t == 'group': # should this have its own scope?
        return run_program(expr[1], env)
    elif t == 'cond-else':
        if evaluate(expr[1], env) == true: # or should this be != false, != nil
            return evaluate(expr[2], env)
        elif len(expr) > 4:
            for cond, body in expr[3]:
                if evaluate(cond, env) == true:
                    return evaluate(body, env)
        return evaluate(expr[-1], env)
    elif t == 'cond':
        if evaluate(expr[1], env) == true: # or should this be != false, != nil
            return evaluate(expr[2], env)
        elif len(expr) > 3:
            for cond, body in expr[3]:
                if evaluate(cond, env) == true:
                    return evaluate(body, env)
        return nil
    elif t == 'pval':
        params = []
        if len(expr) == 3:
            prog = expr[1]
        else:
            params = expr[1]
            prog = expr[2]
        refs = [env.getref(e) for e in expr[-1]]
        inner = lambda e: run_program(prog, e)
        return ParamVal(v=inner, params=params, cl=env, refs=refs)
    elif t == 'evaluation':
        v = env.retrieve_val(env.getref(expr[1]))
        return v()
    elif t == 'param-eval':
        p = expr[1]
        if p[0] == 'evaluation':
            v = env.retrieve_val(env.getref(p[1]))
        else:
            v = evaluate(p, env)
        args = [evaluate(a, env) for a in expr[2]]
        return v(*args)


if __name__ == '__main__':
    with open(sys.argv[1], 'rb') as f:
        prog = parse(f.read())
    run_program(prog, root)
