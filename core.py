class LarkException(Exception): pass
class SyntaxError(LarkException): pass
class LarkReturn(LarkException): pass
class LarkBreak(LarkException): pass
class LarkContinue(LarkException): pass

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
        if self.type == 'string':
            if isinstance(a, Val):
                a = a.data
            if isinstance(a, int):
                try:
                    return Val('string', self.data[a])
                except IndexError:
                    raise LarkException("Dot-access index for string is out of range: {0}".format(a))
            else:
                raise LarkException("Cannot dot-access string with value {0}".format(repr(a)))
        raise LarkException("No dot-access for value of type '{0}'".format(self.type))

    def setmember(self, a, x):
        if self.type == 'string':
            raise LarkException("Strings are immutable.")
        raise LarkException("No dot-access for value of type '{0}'".format(self.type))

    def cleanup(self):
        pass

    # primitives should not copy
    def copy(self):
        return self

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
        self.as_str = "pval[{0}]".format(','.join(
            p if isinstance(p, basestring) else '^{0}'.format(p[1]) for p in params
        ))
        self.refs = refs
        for r in self.refs:
            self.cl.incref(r)
        self.params = params

    def __call__(self, *args):
        if len(args) != len(self.params):
            raise LarkException("Wrong number of parameters: expected {0}, got {1}".format(len(self.params), len(args)))
        ex = Env(parent=self.cl)
        refs = []
        for k,v in zip(self.params, args):
            # should refs be allowed as v for non-ref k?
            if isinstance(k, basestring):
                ex.new_assign(k, v.copy())
            else:
                if k[0] == 'ref' and not isinstance(v, Ref):
                    raise LarkException("Expected parameter '{0}' to be a reference.".format(k[1]))
                ex.incref(v)
                ex.vars[k[1]] = v
        ret = self.data(ex)
        ex.cleanup()
        return ret

    def cleanup(self):
        for r in self.refs:
            self.cl.decref(r)

    # needs copy? should closures copy? unclear

class PyVal(Val):
    def __init__(self, obj):
        self.type = 'py'
        self.data = obj

    def getmember(self, a):
        if isinstance(a, Val):
            a = a.data
        if isinstance(a, int):
            try:
                return as_lark(self.data[a])
            except IndexError:
                raise LarkException("Dot-access index for tuple is out of range: {0}".format(a)) # TODO
        elif isinstance(a, basestring):
            try:
                return as_lark(getattr(self.data, a))
            except KeyError:
                try:
                    return as_lark(self.data[a])
                except KeyError:
                    raise LarkException("Dot-access member '{0}' not in tuple".format(a)) # TODO
        else:
            raise LarkException("Cannot dot-access tuple with member {0}".format(repr(a))) # TODO

    def length(self):
        return len(self.data)

    def labels(self):
        return Tuple([Val('string', x) for x in dir(self.data)])

    def setmember(self, a, x):
        if isinstance(a, Val):
            a = a.data
        if isinstance(a, int):
            try:
                self.data[a] = as_py(x)
            except IndexError:
                raise LarkException("Dot-access index for tuple is out of range: {0}".format(a))
        elif isinstance(a, basestring):
            # check for hasattr first?
            setattr(self.named, a, as_py(x))
        else:
            raise LarkException("Cannot dot-access tuple with non-int member {0}".format(repr(a)))
        return x

    def __call__(self, *args):
        if hasattr(self.data, '__call__'):
            return as_lark(self.data.__call__(*map(as_py, args)))
        return self

    def __str__(self):
        return str(self.data)

    def __repr__(self):
        return 'py({0})'.format(repr(self.data))

    def __eq__(self, other):
        return self.data == other.data


def as_lark(obj):
    if obj is None:
        return nil
    elif isinstance(obj, bool):
        return true if obj else false
    elif isinstance(obj, basestring):
        return Val('string', obj)
    elif isinstance(obj, int):
        return Val('int', obj)
    elif isinstance(obj, float):
        return Val('float', obj)
    elif isinstance(obj, tuple):
        return Tuple([as_lark(o) for o in obj])
    elif isinstance(obj, list):
        return Tuple([as_lark(o) for o in obj])
    elif isinstance(obj, dict):
        return Tuple(named={k:as_lark(v) for k,v in obj.items()})
    else:
        return PyVal(obj)

def as_py(val):
    if isinstance(val, Tuple):
        if val.named:
            return {k:as_py(v) for k,v in val.named.items()}
        else:
            return [as_py(x) for x in val.data]
    return val.data

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
                raise LarkException("Dot-access index for tuple is out of range: {0}".format(a))
        elif isinstance(a, basestring):
            try:
                return self.named[a]
            except KeyError:
                raise LarkException("Dot-access member '{0}' not in tuple".format(a))
        else:
            raise LarkException("Cannot dot-access tuple with member {0}".format(repr(a)))

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
            except IndexError:
                raise LarkException("Dot-access index for tuple is out of range: {0}".format(a))
        elif isinstance(a, basestring):
            self.named[a] = x
        else:
            raise LarkException("Cannot dot-access tuple with non-int member {0}".format(repr(a)))
        return x

    def copy(self):
        d = [x.copy() for x in self.data]
        n = {k:v.copy() for k,v in self.named.items()}
        return Tuple(d, named=n)

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
        self.namespaces = {}
        if memory is None:
            if parent is not None:
                self.memory = parent.memory
            else:
                raise LarkException("Must specify memory or parent when constructing Env.")
        self.vars = {}
        # maybe put params in env property -- env.param(0), etc
        # set when building pval, replace in parser with ('param', 0)

    def getref(self, name):
        if '::' in name:
            n, rest = name.split('::', 1)
            ns = self.get_ns(n)
            return ns.getref(rest)
        r = self.vars.get(name, None)
        if r is None:
            if self.parent is not None:
                return self.parent.getref(name)
            else:
                raise LarkException("Could not find variable '{0}'.".format(name))
        return r

    def makeref(self, name):
        if name in self.vars:
            raise LarkException("Variable '{0}' already defined in this scope.".format(name))
        r = Ref(name, self.memory.next_addr())
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

    def get_ns(self, ns):
        if ns in self.namespaces:
            return self.namespaces[ns]
        elif self.parent is not None:
            return self.parent.get_ns(ns)
        raise LarkException("Unknown namespace '{0}'.".format(ns))

    def get_or_create_ns(self, ns):
        if ns in self.namespaces:
            return self.namespaces[ns]
        else:
            return self.set_ns(ns, Env(parent=self))

    def set_ns(self, ns, env):
        self.namespaces[ns] = env
        return env

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
            raise LarkException
        self.memory[ref.addr].val = val
        return val

    def retrieve_val(self, ref):
        if ref.addr not in self.memory:
            raise LarkException
        return self.memory[ref.addr].val

    def cleanup(self):
        for n,r in self.vars.items():
            self.decref(r)

class Mem(object):
    def __init__(self):
        self.last = 0
        self.slots = {}

    def next_addr(self):
        a = self.last
        self.last += 1
        return a

    def __getitem__(self, key):
        return self.slots[key]

    def __setitem__(self, key, val):
        self.slots[key] = val

    def __delitem__(self, key):
        self.slots.__delitem__(key)

    def __contains__(self, item):
        return self.slots.__contains__(item)

