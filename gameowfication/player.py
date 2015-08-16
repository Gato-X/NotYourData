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
from mathtools import *
import math
import numpy as N
from missile import Missile
from verlet import Verlet
from entities import Entity
from profiler import profile

class Player(Entity):
    def __init__(self, map, position):

        print "New player"

        Entity.__init__(self)
        self._lock = None
        self._phys = Verlet(position)
        self._phys.setDamping((0.02,0.02,0.0002))
        self._phys.setGravity((0,0,-0.00006))

        self._on_floor = False
        self._speed = 0

        self._map = map
        self._heading = 0
        self.reset()

        r = self._radius = 0.1

        self.setBounds(((-r,-r,-r),(r,r,r))) # entity stuff
        Entity.moveTo(self, position) # keep the entity updated

        self._scaling = T.scale_matrix(self._radius)

        self._last_pos = N.array((0,0,0),dtype="f")

        self._graphics = R.loadObject("sphere.obj","diffuse")


    def getMissile(self, scene):

        if self._lock is not None:
            follow = self._lock[0]
        else:
            follow = None

        m_dir = 50*(self._speed+0.02) * self._front_vec*1.5 + self._normal
        T.unit_vector(m_dir, out=m_dir)

        return Missile(scene, self._pos, m_dir, "projectile", follow)

    def reset(self, position=None):
        self._rotation = T.quaternion_about_axis(0,(1,0,0))
        self.setHeading(0)
        if position is not None:
            self.moveTo(position)


    def checkLock(self, enemy):
        best_d = 100000 if self._lock is None else self._lock[1]
        if enemy._closing:
            return
        v =  enemy._pos - self._pos
        d = N.dot(v,v)
        if d < 1000: # max enemy distance
            if self._lock is None or best_d > d:
                self._lock = (enemy, d, enemy._pos)


    def getLockPosition(self):
        try:
            return self._lock[2] # enemy position when locked
        except:
            return None



    # for physics simulation
    @profile
    def update(self, time):
        self._lock = None

        # ----- here be dragons

        ph = self._phys

        ph._impuse = ph._gravity

        ph.update()


        # test for collision with map
        z,normal = self._map(ph._position[0],ph._position[1])

        h = (z+self._radius) - ph._position[2]

        T.unit_vector(normal, out=normal)


        self._on_floor = h>0



        if self._on_floor and ph._position[2] < ph._last_position[2]: # collision
            ph._impulse += h * normal * 0.00001# * normal[2]
            ph._position[2] += h
            ph._last_position[2] += h

        new_pos = ph._position

        # -----

        self._dir = new_pos - self._pos

        self._speed = T.vector_norm(self._dir)

        self._last_pos[:] = new_pos

        Entity.moveTo(self, new_pos) # updates self._pos too

        self._normal = normal

        self._axis = N.cross(self._dir, normal)

        self.roll( self._axis )


    def moveTo(self, pos):
        dp = pos - self._pos
        Entity.moveTo(pos)
        self._phys.displace(dp)


    def roll(self, axis):
        len = T.vector_norm(axis)*5.0
        rot = T.quaternion_about_axis(-len, axis)
        self._rotation = T.quaternion_multiply(rot, self._rotation)


    def getHeading(self):
        return self._heading

    def setHeading(self, new_angle):
        self._heading = new_angle
        self._front_vec = N.array((math.cos(new_angle), math.sin(new_angle), 0),dtype="f")

    def alterHeading(self, delta_angle):
        if delta_angle!= 0:
            self.setHeading(self._heading + delta_angle)


    def advance(self, amount):
        if amount == 0:
            return

        r =  N.cross(self._normal, self._front_vec)
        T.unit_vector(r,out = r)

        # vector facing front, parallel to the floor
        front = N.cross(r, self._normal)

        self._phys.impulse(front * amount)


    def getFrontVector(self):
        return self._front_vec


    def draw(self, scene):
        self._graphics.draw(scene,mmult(self._pos_m,T.quaternion_matrix(self._rotation),self._scaling))


    def jump(self):
        if self._on_floor:
            self._phys._last_position = self._phys._position - self._normal * 0.1

