"""
The MIT License (MIT)

Copyright (c) 2015 Guillermo Romero Franco (AKA Gato)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


import time

_registered_ids = {}
_registered_funcs = []

def _tally(fn_id, time):
    global _registered_funcs
    m = _registered_funcs[fn_id]
    m[1] += time
    m[2] += 1


def _register(func):
    global _registered_ids
    global _registered_funcs

    name = "%s@%s"%(func.__name__, func.__module__)
    try:
        return _registered_ids[name]
    except:
        _registered_ids[name] = len(_registered_funcs)
        _registered_funcs.append([name,0.0,0])
        return _registered_ids[name]

def printTotals(loops):
    t_tot = 0
    for d in _registered_funcs:
        name, time, calls = d
        if calls > 0:
            t_tot += time
            print "%s (%s calls) %3fms"%(name, calls/loops, 1000.0*time/calls)
            d[1] = 0.0
            d[2] = 0
    print "Total: %3fms"%(1000.0*t_tot/loops)

def reset():
    for d in _registered_funcs:
        d[1] = 0.0
        d[2] = 0


#this is a decorator
def profile(func):
    id = _register(func)

    def fn(*args, **kwargs):
        t1 = time.clock()
        result = func(*args, **kwargs)
        t2 = time.clock()
        _tally(id, t2-t1)
    return fn
