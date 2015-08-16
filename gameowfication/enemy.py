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


from entities import Entity
from particles import ParticleGenerator
import libs.transformations as T
from mathtools import *
import resources as R
import routing as routing
import random


class Enemy(Entity):

    TARGET_REACHED = 1
    DESTROYED = 2

    def __init__(self, scene, pos, dest, router):
        Entity.__init__(self)
        self._destroyed = False
        self._closing = False
        self._target_reached = False

        self._scene = scene
        self._map = scene.getMap()

        self._path = None

        self._dying_t = 0
        self._spin = 0

        self.moveTo(pos)

        self._scale = 1.0
        self._graphics = R.loadObject("enemy.obj","diffuse")
        self._orient_m= T.identity_matrix()

        self._xform_m = N.dot(T.rotation_matrix(math.pi/2,(0,0,1)),T.scale_matrix(self._scale))

        bounds = self._graphics.getObj().getBounds()

        router.requestJob(pos, dest, Enemy.OnRouteObtained, self)

        Entity.setBounds(self,bounds * self._scale)
        self._destroyed = False
        self._old_time = 0

        self._old_pos = None # At t-1
        self._old_pos2 = None # At t-2

        self._hc = HeadingController()


    def closing(self):
        return self._closing


    def close(self, mode=TARGET_REACHED):
        self._closing = mode


    def OnRouteObtained(self, wp):
        self._path = routing.Traveller(wp, self._map, 0.003, cruise_z_offset=1)


    def destroy(self):
        self._destroyed = True
        Entity.destroy(self)

    def explode(self):

        def emitter(t):
            while True:
                dx = 2.*random.random()-1.
                dy = 2.*random.random()-1.
                dz = 2.*random.random()-1.

                r = dx*dx+dy*dy+dz*dz

                if r < 1.0 and r>0.5:

                    d = (dx,dy,dz)

                    return self._pos - (dx*3,dy*3,dz*3), d



        p = ParticleGenerator("billboard","particle4.png")
        p.setEmitter(emitter)
        p.setEvolveTime(1)
        p.setAcceleration(0)
        p.setSpawnSpeed(100)
        p.setEasing(0.5,0.8,0,0.5,0.5)
        p.setMode("ONCE")
        self._scene.getParticleManager().manageGenerator(p)
        self.close(self.DESTROYED)


    def targetReached(self):
        return self._target_reached



    def update(self, time):
        if self._destroyed:
            return False


        if self._closing:
            self._scale -= 0.01
            self._scale = max(self._scale, 0)
            self._scale_m = T.scale_matrix(self._scale)
            if self._scale == 0:
                self._destroyed = True

            if self._closing == self.TARGET_REACHED:
                self._spin += 0.1
                self.moveTo(self._pos + (0,0,0.1))

            self._xform_m = N.dot(T.rotation_matrix(math.pi/2+self._spin,(0,0,1)),T.scale_matrix(self._scale))

        elif not self._target_reached:

            if self._old_time == 0:
                self._old_time = time
                return True

            dt = time - self._old_time
            self._old_time = time

            if self._path:
                new_pos = self._path.advance(dt)
                if new_pos is None:
                    self._target_reached = True
                else:

                    self._orient_m= self._hc(new_pos)

                    self.moveTo(new_pos + (0,0,2))

        return True



    def draw(self, scene):
        self._graphics.draw(scene,mmult(self._pos_m, self._orient_m, self._xform_m))
