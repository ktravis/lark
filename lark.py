#!/usr/bin/env python
import sys

class Val(object):
    def __init__(self, t, v=None):
        self.type = t
        self.data = v

    def __call__(self, *args):
        return self

    def __str__(self):
        return str(self.data)

    def __repr__(self):
        return "val({0}, {1})".format(self.type, repr(self.data))

    def cleanup(self):
        pass

nil = Val('niltype', None)
true = Val('bool', True)
false = Val('bool', False)

class ParamVal(Val):
    def __init__(self, v=None, params=[], cl=None, refs=[]):
        self.type = 'pval'
        self.data = v
        self.cl = cl
        for r in refs:
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
        pass

# class RefVal(Val):

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

def fn_print(env, x):
    print env.retrieve_val(x)
    return nil

def fn_add(env, a, b):
    return Val('num', env.retrieve_val(a).data + env.retrieve_val(b).data)

def fn_adder(env, a):
    r = env.new_assign('n', env.retrieve_val(a))
    def _fn(env, x):
        return Val('num', env.retrieve_val(x).data + env.retrieve_val(r).data)
    return ParamVal(_fn, params=['x'], cl=env, refs=[r])

root = Env(memory=memory)
# root.new_assign("x", Val('string', "hi"))

# pprint = ParamVal(fn_print, params=['x'], cl=root)
# pprint(Val('string', "hello world"))
# pprint(root.retrieve_val(root.getref('x')))

# padd = ParamVal(fn_add, params=['a', 'b'], cl=root)
# pprint(padd(Val('num', 1), Val('num', 2)))

# padder = ParamVal(fn_adder, params=['a'], cl=root)

# padd_two = padder(Val('num', 2))
# pprint(padd_two(Val('num', 5)))
# pprint(padd_two(Val('num', 123)))

# padd_three = padder(Val('num', 3))
# pprint(padd_three(Val('num', 1)))
# pprint(padd_two(Val('num', 123)))

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
    elif t == 'assign':
        ref = env.getlocal_ormakeref(expr[1])
        return env.assign(ref, evaluate(expr[2], env))
    elif t == 'primitive':
        return expr[1]
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
    from larkparse import parse
    with open(sys.argv[1], 'rb') as f:
        prog = parse(f.read())
    print run_program(prog, root)
