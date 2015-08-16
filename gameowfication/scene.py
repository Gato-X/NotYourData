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
from glcompat import *
from gltools import getViewportSize
import numpy as N
from mathtools import *

class Scene:

    def __init__(self):
        pass

    def init(self):
        self.resetModelview()
        self._normal_m = N.array([(1,0,0),(0,1,0),(0,0,1)],dtype="f")
        self._light_m = T.identity_matrix()


        self._perspective_m = frustumProjMtx(60, 0.5, 500.0)
        vpw, vph = getViewportSize()
        self._ortho_m = T.clip_matrix(0, vpw, vph, 0, -1, 1)#  0.,0.,.,1.,-1.,1.,False)
        self._modelview_m_stack = []

        self.setPerspectiveMode()

        print self._modelview_m
        print self._projection_m

        self.pushTransform()


    def setPerspectiveMode(self):
        self._projection_m = self._perspective_m


    def setOrthoMode(self):
        self._projection_m = self._ortho_m


    def advance(self, screen, time, inp):
        raise RuntimeError("Call a subclass method")


    def freezeLight(self):
        self._light_m = N.linalg.inv(self._modelview_m[0:3,0:3])


    def uploadMatrices(self, shader):
        glUniformMatrix4fv(shader.uni_modelview_m,1,GL_TRUE, self._modelview_m.ravel())
        glUniformMatrix3fv(shader.uni_normal_m,1,GL_TRUE, self._normal_m.ravel())
        glUniformMatrix3fv(shader.uni_light_m,1,GL_TRUE, N.dot(self._light_m, self._modelview_m[0:3,0:3]).ravel())
        glUniformMatrix4fv(shader.uni_projection_m,1,GL_TRUE,self._projection_m.ravel())


    def updateNormalMatrix(self):
        m = self._modelview_m[0:3,0:3]
        try:
            self._normal_m = N.transpose(N.linalg.inv(m))
        except:
            self._normal_m = m


    def replaceLastTransform(self, transform):
        self._modelview_m = N.dot(self._modelview_m_stack[-1], transform)
        self.updateNormalMatrix()


    def pushTransform(self, add_transform=None):
        self._modelview_m_stack.append(self._modelview_m)
        if add_transform is not None:
            self._modelview_m = N.dot(self._modelview_m, add_transform)
            self.updateNormalMatrix()


    def popTransform(self):
        self._modelview_m = self._modelview_m_stack.pop()
        self.updateNormalMatrix()


    def resetModelview(self):
        self._modelview_m = T.identity_matrix()


    def destroy(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args, **kargs):
        print "With exited"
        self.destroy()


