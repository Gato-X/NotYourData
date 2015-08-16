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
import libs.transformations as T
from mathtools import *
import resources as R


class Base(Entity):

    def __init__(self, pos, particles):
        Entity.__init__(self)

        self._particles = particles

        self.moveTo(pos)

        self._graphics = R.loadObject("base.obj","diffuse")
        self._anim_m = T.identity_matrix()

        bounds = self._graphics.getObj().getBounds()

        Entity.setBounds(self,bounds)


    def destroy(self):
        Entity.destroy(self)
        self._particles.destroy()


    def update(self, time):
        pass


    def draw(self, scene):
        self._graphics.draw(scene,mmult(self._anim_m, self._pos_m))




