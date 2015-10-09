#!/usr/bin/env python
import sys

from larkparse import parse
from core import *

root = Env(memory=Mem())

def larkfunction(fn):
    name = fn.func_name.lstrip('_')
    params = fn.__code__.co_varnames
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
def _push(t, x):
    assert isinstance(t, Tuple)
    t.data.append(x)
    return t

def run_program(prog, env):
    last = nil
    for expr in prog:
        if expr:
            last = evaluate(expr, env)
    return last

def binary_expr(op, lhs, rhs, env):
    l = evaluate(lhs, env)
    r = evaluate(rhs, env)
    # all of this is wrong
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
            if isinstance(x, Val):
                members.append(x)
            elif x[0] == 'named-member':
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
    elif t == 'op-assign':
        op = expr[1]
        rhs = evaluate(expr[3], env)
        if isinstance(expr[2], basestring):
            lhs_ref = env.getref(expr[2])
            lhs = env.retrieve_val(lhs_ref)
            newval = binary_expr(op, lhs, rhs, env)
            return env.assign(lhs_ref, newval)
        else:
            d = expr[2]
            v = evaluate(d[1], env)
            a = d[2]
            if d[0] == 'indirect-dot':
                a = evaluate(a, env)
            lhs = v.getmember(a)
            newval = binary_expr(op, lhs, rhs, env)
            return v.setmember(a, newval) # ref check?
    elif t == 'assign':
        ref = env.getlocal_ormakeref(expr[1])
        return env.assign(ref, evaluate(expr[2], env))
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

pairs = {
    '(': ')',
    '[': ']',
    '{': '}',
    'if|loop': 'end',
}

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
            if not partial:
                try:
                    prog = parse(lines)
                    if prog:
                        res = run_program(prog, root)
                        if res != nil:
                            print str(res)
                except Exception:
                    traceback.print_exc()
                lines = ""
