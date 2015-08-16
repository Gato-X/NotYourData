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
import resources as R
from particles import ParticleGenerator
from entities import Entity
from mathtools import *
import random



class Missile(Entity):

    _gravity = N.array((0,0,-0.008))

    def __init__(self, scene, pos, direction, missile_type, follow):
        Entity.__init__(self)

        self._t0 = None
        self._follow = follow

        self._scene = scene

        self._map = scene.getMap()

        self.moveTo(pos)

        self._thrust = 0.01
        self._speed = 0.1

        self._destroyed = False

        self._graphics = R.loadObject(missile_type+".obj","diffuse")
        self._pos_m = T.translation_matrix(pos)


        axis = T.random_vector(3)

        self._d_rotation = T.quaternion_about_axis(0.01, axis)
        self._rotation = T.random_quaternion()

        self._dir = direction

        scale = 0.05

        self._scaling_m = T.scale_matrix(scale)

        bounds = self._graphics.getObj().getBounds() * scale

        Entity.setBounds(self,bounds)

        self._trail= ParticleGenerator("billboard","puff.jpg")
        self._trail.setEvolveTime(0.5)
        self._trail.setAcceleration(0)
        self._trail.setEasing(0.5, 0.5, 0.0, 0.05, 0.2)
        self._trail.setBrightness(0.5)

        pg = scene.getParticleManager()

        def em(t):
            while True:
                dx = 2.*random.random()-1.
                dy = 2.*random.random()-1.
                dz = 2.*random.random()-1.

                r = dx*dx+dy*dy+dz*dz

                if r < 1.0:
                    break

            return self._pos,(dx*0.2,dy*0.2,dz*0.2)

        self._trail.setEmitter(em)
        self._trail.setMode("DYNAMIC")

        pg.manageGenerator(self._trail)

        self._last_z = 0




    def destroy(self):
        self._destroyed = True
        Entity.destroy(self)
        if self._trail:
            self._trail.destroy()
            self._trail = None


    def explode(self):
        self.destroy()
        p = ParticleGenerator("billboard","particle3.png")
        p.setPosition(self._pos)
        p.setEvolveTime(0.5)
        p.setAcceleration(0)
        p.setSpawnSpeed(100)
        p.setMode("ONCE")

        self._scene.getParticleManager().manageGenerator(p)


    def checkColliders(self, colliders):
        hits = []
        for c in colliders:
            if self.collidesWith(c):
                hits.append(c)
        return hits


    def update(self, time):
        if self._destroyed:
            return False

        if self._t0 is None:
           self._t0 = time

        if self._follow is not None and not self._follow.closing() :

            d = self._follow._pos - self._pos

            T.unit_vector(d,d)

            self._dir = self._dir * (1-self._thrust) + d * self._thrust

            if time - self._t0 > 3000 or self._follow._destroyed:
                print "Not following anymore"

                self._follow = None

            Entity.moveTo(self, self._pos + self._dir * self._speed) # also updates _pos
        else:
            # too simple to use Verlet
            Entity.moveTo(self, self._pos + self._dir * self._speed) # also updates _pos
            self._dir += self._gravity

        self._xform = mmult(self._pos_m,self._scaling_m, T.quaternion_matrix(self._rotation))
        self._rotation = T.quaternion_multiply(self._d_rotation, self._rotation)

        # hit the floor
        if self._map(self._pos[0], self._pos[1], False) > self._pos[2]:
            self.explode()
            return False # tell the scene the missile is toast

        return True


    def draw(self, scene):
        self._graphics.draw(scene, self._xform)




