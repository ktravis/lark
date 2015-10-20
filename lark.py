#!/usr/bin/env python
import os
import sys

from larkparse import parse
from core import *

root = Env(memory=Mem())
extern_globals = {}
extern_locals = {}

def larkfunction(fn):
    name = fn.func_name.lstrip('_')
    params = fn.__code__.co_varnames[:fn.__code__.co_argcount]
    def wrapper(env):
        return fn(*[env.retrieve_val(env.getref(p)) for p in params])
    root.new_assign(name, ParamVal(wrapper, params=params, cl=root))
    return wrapper

@larkfunction
def _print(x):
    print x
    return nil

@larkfunction
def _len(v):
    assert (v.type in ['string', 'tuple'])
    return Val('int', len(v.data))

@larkfunction
def _size(v):
    assert (v.type == 'tuple')
    return Val('int', len(v.data)+len(v.named))

@larkfunction
def _push(t, x):
    assert isinstance(t, Tuple)
    t.data.append(x)
    return t

@larkfunction
def _keys(t):
    assert hasattr(t, 'labels')
    return t.labels()

@larkfunction
def _pairs(t):
    assert isinstance(t, Tuple)
    p = [Tuple([Val('int', i), v]) for i, v in enumerate(t.data)]
    p += [Tuple([Val('string', k), v]) for k, v in t.named.items()]
    return Tuple(p)

@larkfunction
def _type(v):
    return Val('string', v.type)

def fn_dump(env):
    names = {}
    curr = env
    for k,v in curr.vars.items():
        names[v.addr] = k
    while curr.parent is not None:
        curr = env.parent
        for k,v in curr.vars.items():
            names[v.addr] = k

    print '{{\n{0}\n}}'.format('\n'.join(
        '\t{0:10s} => {1}'.format(names.get(k, str(k)), v) for k,v in env.memory.slots.items()
    ))
    return nil
root.new_assign("dump", ParamVal(fn_dump, cl=root))

def parse_import_path(name):
    parts = name.split('::')
    path = None
    while len(parts) > 0:
        curr = parts[0]
        parts = parts[1:]
        last = path
        if path is None:
            path = curr
        else:
            path = '{0}/{1}'.format(path, curr)
        if not os.path.isdir(path):
            break
    ns_name = curr
    extensions = ['', '.lk', '.lrk', '.lark']
    for ext in extensions:
        if os.path.isfile('{0}{1}'.format(path, ext)):
            return '{0}{1}'.format(path, ext), ns_name, parts
    raise LarkException("Cannot import file at path '{0}'".format(path))

def import_file(name, env):
    path, ns_name, parts = parse_import_path(name)
    try:
        with open(path, 'rb') as f:
            content = f.read()
    except IOError as error:
        raise LarkException(error.message)
    ns = env.get_or_create_ns(ns_name)
    last = run_program(parse(content), ns)
    for n in parts:
        ns = ns.get_ns(n)
        ns_name = n
    env.set_ns(ns_name, ns)
    return last

def run_program(prog, env):
    last = nil
    for expr in prog:
        if expr:
            last = evaluate(expr, env)
    return last

def binary_num_ops(op, l, r):
    assert r.type in ['int', 'float']
    if l.type == 'float' or r.type == 'float':
        out_type = 'float'
    else:
        out_type = 'int'
    if op == "+":
        v = l.data + r.data
    elif op == "-":
        v = l.data - r.data
    elif op == "*":
        v = l.data * r.data
    elif op == "/":
        v = l.data / r.data
    elif op == "<":
        return true if l.data < r.data else false
    elif op == ">":
        return true if l.data > r.data else false
    elif op == "<=":
        return true if l.data <= r.data else false
    elif op == ">=":
        return true if l.data >= r.data else false
    return Val(out_type, v)

def binary_string_ops(op, l, r):
    if op == "+":
        assert r.type == 'string'
        v = l.data + r.data
    elif op == "-":
        raise LarkException("Operator '-' is not defined for types {0} and {1}.".format(l.type, r.type))
    elif op == "*":
        raise LarkException("Operator '*' is not defined for types {0} and {1}.".format(l.type, r.type))
    elif op == "/":
        return Tuple(l.data.split(r.data))
    elif op == "<":
        return true if l.data < r.data else false
    elif op == ">":
        return true if l.data > r.data else false
    elif op == "<=":
        return true if l.data <= r.data else false
    elif op == ">=":
        return true if l.data >= r.data else false
    return Val('string', v)

def binary_tuple_ops(op, l, r):
    try:
        fn = l.getmember(op) 
        return fn(l, r)
    except LarkException:
        pass
    if op == "+":
        assert r.type == 'tuple'
        return Tuple(l.data + r.data, named=dict(l.named, **r.named))
    elif op == "<":
        return true if len(l.data) < len(r.data) else false
    elif op == ">":
        return true if len(l.data) > len(r.data) else false
    elif op == "<=":
        return true if len(l.data) <= len(r.data) else false
    elif op == ">=":
        return true if len(l.data) >= len(r.data) else false
    else:
        raise LarkException("Operator '{0}' is not defined for types {1} and {2}.".format(op, l.type, r.type))

def binary_expr(op, lhs, rhs, env):
    l = evaluate(lhs, env)
    r = evaluate(rhs, env)
    if op == "==":
        return true if l.data == r.data else false
    elif op == "!=":
        return true if not (l.data == r.data) else false

    if l.type in ['int', 'float']:
        return binary_num_ops(op, l, r)
    elif l.type == 'string':
        return binary_string_ops(op, l, r)
    elif l.type == 'tuple':
        return binary_tuple_ops(op, l, r)
    else:
        raise LarkException("Operator '{0}' is not defined for types {1} and {2}.".format(op, l.type, r.type))

def unary_expr(op, v, env):
    v = evaluate(v, env)
    if op == '-':
        assert v.type in ['int', 'float']
        return Val(v.type, -v.data)
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
            if isinstance(x, Val):
                members.append(x)
            elif x[0] == 'named-member':
                mt, a = x[1]
                if mt != 'member-label-literal':
                    a = evaluate(a, env)
                    if not (a.type == 'string' or a.type == 'int'):
                        raise LarkException("Cannot label member in tuple with value of type '{0}'".format(a.type))
                    a = a.data
                if a in named:
                    raise LarkException("Member '{0}' redefined in tuple literal".format(a))
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
            raise LarkException("Cannot set upval from root scope!")
        ref = env.parent.getref(expr[1])
        return env.assign(ref, evaluate(expr[2], env))
    elif t == 'member-assign':
        d = expr[1]
        v = evaluate(d[1], env)
        a = d[2]
        if d[0] == 'indirect-dot':
            a = evaluate(a, env)
        return v.setmember(a, evaluate(expr[2], env)) # ref check?
    elif t == 'op-assign':
        op = expr[1]
        rhs = evaluate(expr[3], env)
        if expr[2] in ['dot', 'indirect-dot']:
            d = expr[2]
            v = evaluate(d[1], env)
            a = d[2]
            if d[0] == 'indirect-dot':
                a = evaluate(a, env)
            lhs = v.getmember(a)
            newval = binary_expr(op, lhs, rhs, env)
            return v.setmember(a, newval) # ref check?
        else:
            lhs_ref = env.getref(expr[2])
            lhs = env.retrieve_val(lhs_ref)
            newval = binary_expr(op, lhs, rhs, env)
            return env.assign(lhs_ref, newval)
    elif t == 'assign':
        if '::' in expr[1]:
            ref= env.getref(expr[1])
        else:
            ref = env.getlocal_ormakeref(expr[1])
        return env.assign(ref, evaluate(expr[2], env))
    elif t == 'namespace':
        ns = env.get_or_create_ns(expr[1])
        return run_program(expr[2], ns)
    elif t == 'extern':
        exec expr[1] in extern_globals, extern_locals
        return as_lark(extern_locals)
    elif t == 'extern-expr':
        return as_lark(eval(expr[1], extern_globals, extern_locals))
    elif t == 'return':
        ret = LarkReturn("Return outside of pval.")
        ret.value = expr[1]
        raise ret
    elif t == 'break':
        raise LarkBreak("Break outside of loop body!")
    elif t == 'continue':
        raise LarkContinue("Continue outside of loop body!")
    elif t == 'loop':
        cond_expr = expr[1]
        body = expr[2]
        last = nil
        while evaluate(cond_expr, env) != false:
            try:
                last = run_program(body, env)
            except LarkContinue:
                continue
            except LarkBreak: # should set last to nil maybe?
                break
        return last
    elif t == 'import':
        return import_file(expr[1], env)
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
        param_names = [p if isinstance(p, basestring) else p[1] for p in params]
        refs = [env.getref(e) for e in expr[-1] if e not in param_names]
        inner = lambda e: run_program(prog, e)
        return ParamVal(v=inner, params=params, cl=env, refs=refs)
    elif t == 'ref':
        return env.getref(expr[1])
    elif t == 'evaluation':
        ref = env.getref(expr[1])
        v = env.retrieve_val(ref)
        try:
            ret = v()
        except LarkReturn as e:
            ret = e.value
        return ret
    elif t == 'param-eval':
        p = expr[1]
        if p[0] == 'evaluation':
            v = env.retrieve_val(env.getref(p[1]))
        else:
            v = evaluate(p, env)
        args = [evaluate(a, env) for a in expr[2]]
        try:
            ret = v(*args)
        except LarkReturn as e:
            ret = e.value
        return ret
    return nil

pairs = {
    '(': ')',
    '[': ']',
    '{': '}',
    'if|loop': 'end',
}
even = [
    '"""',
    "'''",
]

if __name__ == '__main__':
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'rb') as f:
            prog = parse(f.read())
        run_program(prog, root)
    else:
        import readline
        import traceback

        lines = ""
        partial = False
        while True:
            l = raw_input(".... " if partial else "lrk> ")
            lines += l + '\n'
            partial = False
            for start,end in pairs.items():
                if sum(lines.count(s) for s in start.split('|')) != lines.count(end):
                    partial = True
                    break
            for mark in even:
                if (lines.count(mark) % 2) != 0:
                    partial = True
                    break
            if not partial:
                try:
                    prog = parse(lines)
                    if prog:
                        res = run_program(prog, root)
                        if res != nil:
                            print str(res)
                except LarkException:
                    traceback.print_exc()
                lines = ""
