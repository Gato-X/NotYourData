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
from profiler import profile


class TargetPoint(Entity):

    def __init__(self, scene, pos):
        Entity.__init__(self)
        self._destroyed = False
        self._closing = False

        self._scene = scene

        self.moveTo(pos)

        self._graphics = R.loadObject("targetpt.obj","diffuse")
        self._beacon = R.loadObject("beacon.obj","glow")

        self._anim_m = T.identity_matrix()
        self._rot= T.quaternion_about_axis(0, (0,0,1))
        self._rot_speed = T.quaternion_about_axis(0.01, (0,0,1))

        self._scale = 0.15

        self.moveTo(self.getPosition() + (0,0,-0.3))

        self._scale_m = T.scale_matrix(self._scale)

        bounds = self._graphics.getObj().getBounds() * self._scale

        Entity.setBounds(self,bounds)


    def closing(self):
        return self._closing


    def close(self):
        pg = ParticleGenerator("billboard","particle2.png")
        pg.setMode("ONCE")
        pg.setPosition(self._pos)
        self._scene.getParticleManager().manageGenerator(pg)
        self._closing = True


    def update(self, time):
        if self._destroyed:
            return False

        if self._closing:
            self._scale -= 0.01
            self._scale = max(self._scale, 0)
            self._scale_m = T.scale_matrix(self._scale)
            if self._scale == 0:
                self._destroyed = True


        self._rot = T.quaternion_multiply(self._rot_speed, self._rot)
        self._anim_m = T.quaternion_matrix(self._rot)

        self._beacon_xform = self._pos_m

        self._geom_xform = mmult(self._pos_m, self._anim_m, self._scale_m)

        return True

    @profile
    def draw(self, scene):
        self._graphics.draw(scene, self._geom_xform)


    def drawBeacon(self, scene):
        self._beacon.draw(scene, self._beacon_xform)
