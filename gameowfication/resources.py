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


try:
    import Image
except:
    from PIL import Image


import os
import pygame
import weakref
import gltools as glt
import objloader

_data_py = os.path.abspath(os.path.dirname(__file__))
_data_dir = None


def setResourcesPath(resources_path):
    global _data_dir;
    _data_dir = os.path.normpath(os.path.join(_data_py, resources_path))


setResourcesPath(os.path.join('..','data'))


_cache = weakref.WeakValueDictionary()

# adapted from the pygame cookbook

def cached(group=None):
    def deco(func):
        def memo(*args, **kwargs):
            global _cache
            try:
                # Create a key, resorting to repr if the key isn't hashable.
                k = (group, args, tuple(kwargs.items()))
                try:
                    hash(k)
                except TypeError:
                    k = "%s:%s"%(group,repr(k))

                return _cache[k]
            except KeyError:
                result = func(*args, **kwargs)
                _cache[k] = result
                return result

        return memo
    return deco




def resourcePath(filename):
    return os.path.join(_data_dir, filename)



def openResource(filename, mode='rb'):
    return open(resourcePath(filename), mode)



@cached("SURFACE")
def loadSurface(filename, convert=True):

    if filename.startswith("#"): # so we can get a texture like so too: #white
        surf = pygame.Surface((64,64))
        surf.fill(pygame.Color(filename[1:]))
    else:
        surf = pygame.image.load(resourcePath(filename))

    if convert:
        surf = surf.convert()

    return surf


@cached("IMAGE")
def loadImage(filename, convert=True):
    img = Image.open(resourcePath(filename))
    return img

@cached("TEXTURE")
def loadTexture(filename):
    return glt.Texture(filename)


def loadShader(filename):
    if "_v." in filename:
        shdr = glt.compileShader(openResource(filename,"rt").read(), "VERTEX")
    elif "_f." in filename:
        shdr = glt.compileShader(openResource(filename,"rt").read(), "FRAGMENT")
    else:
        raise ValueError("Unknown shader type: %s")

    return shdr


@cached("SHADER_P")
def getShaderProgram(name):
    vs = loadShader(name+"_v.shdr")
    fs = loadShader(name+"_f.shdr")
    return glt.ShaderProgram(name, [vs,fs])


@cached("OBJ")
def loadObject(filename, shader_name=None):
    """
    if shader is not specified, returns an ObjFile else returns a ObjRenderer
    """

    obj = objloader.ObjFile(filename)
    if shader_name is None:
        return obj
    else:
        return objloader.ObjRenderer(obj, getShaderProgram(shader_name))


@cached("FONT")
def getFont(size, face=None):
    return pygame.font.Font(face,size)




