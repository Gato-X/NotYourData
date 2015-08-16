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


import numpy as N
from mathtools import *

class Verlet(object):
    def __init__(self, position):
        self._gravity= N.array((0,0,-0.0005),dtype="f")
        self.setDamping(0.001)
        self.reset(position = position)


    def setDamping(self, d):
        try:
            self._inv_damping = 1.0 - d
        except:
            self._inv_damping = 1.0 - N.array(d,dtype="float")

    def setGravity(self, g):
        self._gravity[:] = g

    def getPosition(self):
        return self._position.copy()

    def reset(self, position=None):
        self._impulse = N.array((0,0,0), dtype="f")

        if position is not None:
            self._position = N.array(position+(0,0,1),dtype="f")
            self._last_position = N.array(position+(0,0,1),dtype="f")


    def update(self):
        pos = self._position

        new_position = pos + (pos - self._last_position) * self._inv_damping + self._impulse * 100.0

        self._impulse[:] = self._gravity

        self._last_position[:] = pos
        self._position[:] = new_position


        return True

    # rel_vec is in the player coord sys
    def impulse(self, rel_vec):
        self._impulse += rel_vec


    def impulseTowards(self, target, flattening=0.0, strength=0.001):
        v = target - self._position
        d = T.vector_norm(v)

        if d>0:
            v *= 1.0/d

        d = (strength * d) / (flattening * d+1)

        self.impulse(v * d)


    def moveTo(self, pos):
        self._last_position += pos - self._position
        self._position = pos

    def displace(self, dpos):
        self._last_position += dpos
        self._position += dpos
