# lark

Language running on python -- everything is a value, whatever that means.

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

counter = make_counter[0]
print[counter] # 1
print[counter] # 2
print[counter] # 3
```
