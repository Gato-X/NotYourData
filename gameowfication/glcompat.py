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



from OpenGL.GL import *
import platform


try:
    def glGenVertexArray():
        return ARB.vertex_array_object.glGenVertexArrays(1)

    glBindVertexArray = ARB.vertex_array_object.glBindVertexArray
    print "ARB version"
except:
    def glGenVertexArray():
        return glGenVertexArrays(1)





if platform.system() == 'Darwin':
    from OpenGL.GL.APPLE import vertex_array_object

    def glGenVertexArray_apple():
        vao_id = GLuint(0)
        vertex_array_object.glGenVertexArraysAPPLE(1, vao_id)
        return vao_id.value

    glGenVertexArray = glGenVertexArray_apple
    glBindVertexArray = vertex_array_object.glBindVertexArrayAPPLE
