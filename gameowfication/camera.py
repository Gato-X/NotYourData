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


import libs.transformations as T
import math
from mathtools import *
from gltools import *
from verlet import Verlet
from profiler import profile


class Camera:
    def __init__(self, track, map):

        self._track_obj = track


        position = self._track_obj.getPosition()
        self._target = Verlet(position)
        self._pos = Verlet(position + (1,0,0))
        self._map = map

        self._pos.setGravity(0)
        self._target.setGravity(0)

        self._pos.setDamping((0.3,0.3,0.99))
        self._target.setDamping(0.3)

        self._up = N.array((0,0,1),dtype="f")
        self._look_at = position

    @profile
    def update(self,time):
        self._pos.update()
        self._target.update()

        look_at = self._track_obj.getPosition()+(0,0,0.6)
        cam_pos = look_at -self._track_obj.getFrontVector() * 2.0  + N.array((0,0,0.0))

        self._pos.impulseTowards(cam_pos)
        self._target.impulseTowards(look_at)

        # see if the camera doesn't intersect geometry. If it does, push it up

        cam_pos =self._pos.getPosition()
        look_at = self._target._position
        dv = cam_pos - look_at


        dist = T.vector_norm(dv[0:2]) # distance across floor

        n = math.ceil(dist / 0.2)

        z0 = look_at[2]
        dray = dv / n
        m = self._map

        hit = False

        # ray-march
        #z_list = []
        ray_pos = look_at + dray # advance once
        for i in xrange(1,int(n)+3): # start at i=1 to avoid division by zero
            z = m(ray_pos[0], ray_pos[1], False)+0.4 # is an offset so the camera can see
            #z_list.append(int(z*10))
            if z > ray_pos[2]:
                slope = (z-z0) / float(i)
                #if slope > 0.1:
                #   ray_pos -= dray # go back one step
                #   break
                dray[2] = slope
                ray_pos[2] = z
                hit = True

            ray_pos += dray

        ray_pos -= dray*3

        #print z_list
        #print "%s -> %s   %s" % (self._pos.getPosition(), ray_pos, "HIT" if hit else "")

        if hit:
            self._pos.moveTo(ray_pos)







    def getMatrix(self):
        return lookAtMtx(self._pos._position, self._target._position, self._up)

