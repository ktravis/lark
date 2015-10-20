# lark

Language running on python -- everything is a value, whatever that means.


## Features

- python interoperability
- reference counting (not complete yet, but close)
- namespaces
- closures
- dynamic variables
- flexible tuple data type (named members and positional slots)
- explicit and unambiguous "references"


## Getting Started

```bash
pip install ply
./lark.py
```


## Examples

```
# comments
x = 3
y = { x } # boxed val
z = [a]{ a * x } # parametrized value
z[2] # 6

str = 'hello wendl' #string

make_counter = [n]{
    a = n
    { ^a = a + 1 } # last expression is returned
}
if true
    print['sane universe']
elif false
    print['uh oh']
else
    print['who even knows']
end

thing = if x > 2
    'x is bigger than two'
else
    'x is 2 or smaller'
end

noref = [x] { x += 1 }
y = 0
noref[y] # 1
y # 1

yesref = [^x] { x += 1 }
# yesref[y] # error
yesref[^y] # 1
y # 1
yesref[^y] # 2

counter = make_counter[0]
print[counter] # 1
print[counter] # 2
print[counter] # 3

t = (1,) # tuple
t2 = (1, "hello world") # more tuple
print[t.0] # 1
i = 1
print[t2.(i)] # hello world

i = 0
loop true
    i += 1
    print[i]
    if i > 5
        break
    end
end

namespace hello {
    namespace world {
        yes = true
    }
}
print[hello::world::yes] # true

import test # imports a file named test (optional extensions)
import test::nested # imports namespace "nested" from file test,
                   # or file "nested[.lk]" from folder 'test'

nested::my_value = i

extern """import sys"""
input = extern "sys.stdin.readline().strip()"
```
