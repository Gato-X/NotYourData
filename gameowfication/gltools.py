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


from OpenGL.arrays import vbo
import pygame
#from OpenGL.GL import *
from glcompat import *
import resources as R

fsize = ctypes.sizeof(ctypes.c_float)

def isColorLike(col1, col2):
    dr = abs(col1[0] - col2[0])
    if dr > 5: return False
    dg = abs(col1[1] - col2[1])
    if dg > 5: return False
    db = abs(col1[2] - col2[2])
    if db > 5: return False
    return True


def isGray(col):
    if (max(col[0],col[1],col[2]) - min(col[0],col[1],col[2]) ) >= 5:
       return False

    return (float(col[0])+float(col[1])+float(col[2])) / 3.0


def getViewportSize():
    vp = glGetIntegerv(GL_VIEWPORT)
    return vp[2], vp[3]


class ShaderProgram:
    defaultUniforms = ["light_m","normal_m","modelview_m","projection_m"]
    defaultAttribs = ["position","normal","color","tc"]

    def __init__(self, name, shaders , uniforms="default", attribs="default"):
        self._name = name
        self._program = glCreateProgram()
        self._loc_attribs = {}
        self._loc_uni = {}

        for s in shaders:
            glAttachShader(self._program, s)

        glLinkProgram(self._program)

        if glGetProgramiv(self._program, GL_LINK_STATUS) != GL_TRUE:
            raise RuntimeError(glGetProgramInfoLog(self._program))

        glUseProgram(self._program)

        if uniforms:
            if uniforms == "default":
                uniforms = ShaderProgram.defaultUniforms

            for uniform in uniforms:
                self.getUniformPos(uniform, True)

        if attribs:
            if attribs == "default":
                attribs = ShaderProgram.defaultAttribs

            for attrib in attribs:
                self.getAttribPos(attrib, True)

        glUseProgram(0)


    def getUniformPos(self, uniform, register = False):
        try:
            return self._loc_uni[uniform]
        except:
            loc = glGetUniformLocation(self._program, uniform)
            if loc == -1:
                print "Not such uniform in shader: %s"%uniform
            self._loc_uni[uniform] = loc
            if register:
                setattr(self, "uni_"+uniform, loc)
            return loc


    def getAttribPos(self, attrib, register = False):
        try:
            return self._loc_attribs[attrib]
        except:
            loc = glGetAttribLocation(self._program, attrib)
            if loc == -1:
                print "Not such attribute in shader: %s"%attrib
            self._loc_attribs[attrib] = loc
            if register:
                setattr(self, "attr_"+attrib, loc)
            return loc


    def getName(self):
        return self._name

    def begin(self):
        glUseProgram(self._program)


    def end(self):
        glUseProgram(0)




def compileShader(source, shdr_type):
    if shdr_type == "VERTEX":
        shdr_type = GL_VERTEX_SHADER
    elif shdr_type == "FRAGMENT":
        shdr_type = GL_FRAGMENT_SHADER
    else:
        raise ValueError("Unknown shader type: %s"%shdr_type)

    shader = glCreateShader(shdr_type)
    glShaderSource(shader, source)
    glCompileShader(shader)

    if glGetShaderiv(shader, GL_COMPILE_STATUS) != GL_TRUE:
        raise RuntimeError(glGetShaderInfoLog(shader))

    return shader


class Texture:

    _null_texture = None

    @classmethod
    def getNullTexture(cls):
        if cls._null_texture == None:
            cls._null_texture = Texture("#white")
        return cls._null_texture


    def __init__(self, filename=None, smoothing=True):
        self._smoothing = smoothing
        self._id = 0
        if filename:
            self.load(filename)


    def load(self, filename):
        surf = R.loadSurface(filename, False)
        self.setFromSurface(surf)


    def setFromSurface(self, surf):
        data = pygame.image.tostring(surf, "RGBA", 1)

        self._width = w = surf.get_width()
        self._height = h = surf.get_height()

        if not self._id:
            id = self._id = glGenTextures(1)
        else:
            id = self._id

        glBindTexture(GL_TEXTURE_2D,id)
        if self._smoothing:
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        else:
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glBindTexture(GL_TEXTURE_2D,0)


    def update(self, surf):
        glBindTexture(GL_TEXTURE_2D,self._id)
        data = pygame.image.tostring(surf, "RGBA", 1)
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0,0, self._width, self._height, GL_RGBA, GL_UNSIGNED_BYTE, data )
        glBindTexture(GL_TEXTURE_2D,0)


    def width(self):
        return self._width


    def height(self):
        return self._height


    def id(self):
        return self._id


    def bind(self, sampler_num, uniform_location):
        glUniform1i(uniform_location, sampler_num) # assign the sampler to the texture
        glActiveTexture(GL_TEXTURE0 + sampler_num) # make sure the sampler is enabled
        glBindTexture(GL_TEXTURE_2D, self._id) # select the current texture


    def __del__(self):
        glDeleteTextures(self._id)

    def getBinder(self, sampler_num, uniform_location):
        if uniform_location == -1:
            def binder(sampler_num = 0, uniform_location = 0):
                    pass
            return binder
        else:
            def binder(sampler_num=sampler_num, uniform_location=uniform_location):
                self.bind(sampler_num, uniform_location)
            return binder
