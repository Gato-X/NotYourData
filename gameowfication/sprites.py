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


from glcompat import *
from profiler import profile
import numpy as N
import math
import libs.transformations as T
from gltools import *
#from OpenGL.arrays import vbo
from libs.sortedcontainers.sortedlist import SortedList


_floats_per_vertex = 6

class SpriteTexture:
    def __init__(self, surface_size):
        self._surface = pygame.Surface((surface_size,surface_size), flags=pygame.SRCALPHA)
        self._texture = Texture(smoothing=True)
        self._texture.setFromSurface(self._surface)
        self._vbo_change_low = 1000000
        self._vbo_change_high = 0
        self.reset()


    def getSurface(self):
        return self._surface

    # note vbo_index is the GLOBAL TILE NUMBER
    # that is, not numbered within the texture
    def setTainted(self, img = False, vbo_index=None):
        if img:
            self._img_tainted = True
        if vbo_index is not None:
            self._vbo_change_low = min(self._vbo_change_low, vbo_index)
            self._vbo_change_high = max(self._vbo_change_high, vbo_index+1)


    def reset(self):
        self._img_tainted = False

        self._vbo_change_low = 1000000
        self._vbo_change_high = 0


    def isImageTainted(self):
        return self._img_tainted


    def isVboTainted(self):
        t = self._vbo_change_high > self._vbo_change_low
        return t


    def updateGlTexture(self):
        if self._img_tainted:
            self._texture.update(self._surface)
            self._img_tainted = False


    def bind(self, loc):
        return self._texture.bind(0,loc)



class SpriteManager:
    def __init__(self, tile_size=64):
        self._tile_size = tile_size
        self._texture_size = 1024
        self._max_textures = 5
        self._tile_rows_in_texture = self._texture_size / tile_size
        self._free_tiles = SortedList()
        self._textures = []
        self._total_tiles = 0
        self._sprites = {}
        self._top_sprite_id = 0
        self._total_tiles_per_texture = int(self._tile_rows_in_texture**2)
        self._vbo_index_bytes_per_texture = self._total_tiles_per_texture * 6 * _floats_per_vertex * ctypes.sizeof(ctypes.c_uint16)

        self._max_tiles = self._total_tiles_per_texture *self._max_textures

        self.initBuffers()



    def initBuffers(self):
        self._vao = glGenVertexArray()
        glBindVertexArray(self._vao)

        self._shader = R.getShaderProgram("sprites")

        self._texture_loc = self._shader.getUniformPos("texture0")

        # 1 vectors of 3 for vertex coords
        # 1 vector of 2 for texture coords
        # 1 float for alpha
        # = 6 floats = _floats_per_vertex
        # x 4 points per quad
        self._data = N.zeros((self._max_tiles * 4, _floats_per_vertex),dtype="f")

        # 6 indices (2 tris) per quad
        indices = N.empty((self._max_tiles,6), dtype=N.uint16)

        j = 0
        for i in xrange(self._max_tiles):
            ind = indices[i,:]
            ind[0] = j+0
            ind[1] = j+1
            ind[2] = j+2
            ind[3] = j+0
            ind[4] = j+2
            ind[5] = j+3
            j+=4;

        self._vertices_vbo = vbo.VBO(self._data.ravel(),usage=GL_DYNAMIC_DRAW)
        self._vertices_vbo.bind()

        stride = fsize * _floats_per_vertex

        glEnableVertexAttribArray(self._shader.attr_position)
        glVertexAttribPointer(self._shader.attr_position, 3, GL_FLOAT, False, stride, None)

        glEnableVertexAttribArray(self._shader.attr_tc)
        glVertexAttribPointer(self._shader.attr_tc, 2, GL_FLOAT, False, stride, ctypes.c_void_p(3 * fsize))

        self._shader.getAttribPos("alpha",True)

        glEnableVertexAttribArray(self._shader.attr_alpha)
        glVertexAttribPointer(self._shader.attr_alpha, 1, GL_FLOAT, False, stride, ctypes.c_void_p(5*fsize))

        self._indices_vbo = vbo.VBO(indices.ravel(), target=GL_ELEMENT_ARRAY_BUFFER,usage=GL_STATIC_DRAW)
        self._indices_vbo.bind()

        glBindVertexArray(0)


    # creates a new texture and pushes all new tiles
    # into the _free_tiles list

    def newTexture(self):
        texture_surface_id = len(self._textures)

        texture = SpriteTexture(self._texture_size)

        self._textures.append(texture) #[texture_surf, texture,False,0,0])

        ty = 0
        for y in xrange(self._tile_rows_in_texture):
            tx = 0
            for x in xrange(self._tile_rows_in_texture): #  #cols = #rows
                self._free_tiles.add((texture_surface_id, (ty,tx), self._total_tiles))
                tx += self._tile_size
                self._total_tiles += 1
            ty += self._tile_size


    def getFreeTile(self):
        try:
            tile = self._free_tiles.pop(0)
        except:
            self.newTexture() # create more tiles
            tile = self._free_tiles.pop(0)

        return tile



    def setTileAlpha(self, tile, alpha):
        texture_surf_id, tile_pos, tile_num = tile

        d = self._data[4*tile_num:4*tile_num+4]
        d[0:4,5] = alpha

        self._textures[texture_surf_id].setTainted(vbo_index=tile_num)


    def setTileGraphics(self, tile, src_tile_coord, surf, alpha):
        texture_surf_id, (ty,tx), tile_num = tile

        src_x = src_tile_coord[0] * self._tile_size
        src_y = src_tile_coord[1] * self._tile_size
        ts = self._tile_size

        # blit texture onto it

        tex = self._textures[texture_surf_id]
        texture_surf = tex.getSurface()# texture surface

        texture_surf.fill((0,0,0,0), rect=(tx,ty,ts,ts) )
        texture_surf.blit(surf, (tx,ty), area=(src_x,src_y,ts,ts))


        # setup the vbo data
        u0 = float(tx) / self._texture_size
        u1 = float(tx+ts) / self._texture_size
        v0 = 1.0-float(ty) / self._texture_size
        v1 = 1.0-float(ty+ts) / self._texture_size


        d = self._data[4*tile_num:4*tile_num+4]
        d[0][3:6] = (u0,v0, alpha)
        d[1][3:6] = (u0,v1, alpha)
        d[2][3:6] = (u1,v1, alpha)
        d[3][3:6] = (u1,v0, alpha)

        tex.setTainted(img=True, vbo_index=tile_num)


    def setTileTransform(self, tile, src_tile_coord, transform_info):
        texture_surf_id, tile_pos, tile_num = tile

        dx,dy,p0,px,py = transform_info

        x0 = dx * src_tile_coord[0]
        y0 = dy * src_tile_coord[1]

        d = self._data[4*tile_num:4*tile_num+4]
        vx = px - p0
        vy = py - p0

        p0 = p0 + vx*x0 + vy*y0

        d[0][0:3] = p0
        d[1][0:3] = p0 + vy * dy
        d[2][0:3] = p0 + vx * dx + vy * dy
        d[3][0:3] = p0 + vx * dx

        self._textures[texture_surf_id].setTainted(vbo_index=tile_num)


    def getTransformInfo(self, surf_w, surf_h, xform,centered):

        ts = self._tile_size
        tiles_w = int(math.ceil(float(surf_w)/ts))
        tiles_h = int(math.ceil(float(surf_h)/ts))

        p0 = N.array((0,0,0),dtype="f")
        px = N.array((surf_w,0,0),dtype="f")
        py = N.array((0,surf_h,0),dtype="f")

        if centered is not None:
            dp = N.array((surf_w*0.5,surf_h*0.5,0),dtype="f")
            p0 -= dp
            px -= dp
            py -= dp

        if xform is not None:
            xr = xform[0:3,0:3]
            xt = xform[0:3,3]
            p0 = N.dot(xr,p0)+xt
            px = N.dot(xr,px)+xt
            py = N.dot(xr,py)+xt


        dx = 1.0/tiles_w
        dy = 1.0/tiles_h


        return dx,dy,p0,px,py

    def _newSpriteHlp(self, surface, alpha, xform=None, centered=None):
        try:
            surface.get_width()
        except:
            surface = R.loadSurface(surface)

        ts = self._tile_size
        w,h = surface.get_width(), surface.get_height()
        tiles_x = int(math.ceil(float(w)/ts))
        tiles_y = int(math.ceil(float(h)/ts))

        transform_info = self.getTransformInfo(w,h,xform,centered)
        sprite_tiles = []


        for y in xrange(tiles_y):
            for x in xrange(tiles_x):
                tile = self.getFreeTile()
                self.setTileGraphics(tile, (x,y), surface, alpha )
                self.setTileTransform(tile, (x,y), transform_info )
                sprite_tiles.append(tile)

        return (sprite_tiles,(w,h),alpha,xform,centered)


    def newSprite(self, surface, alpha=1.0, xform=None, centered=None):
        try:
            surface.get_width()
        except:
            surface = R.loadSurface(surface,False)

        s = self._newSpriteHlp(surface, alpha, xform, centered)

        id = self._top_sprite_id
        self._sprites[id] = s
        self._top_sprite_id+=1

        return id


    def destroySprite(self, sid):
        try:
            s = self._sprites[sid]
        except:
            return

        for tile in s[0]: # iterate over the tiles in the sprite
            self.setTileAlpha(tile, 0) # this disables the rendering of the sprite
            self._free_tiles.add(tile)

        del self._sprites[sid]


    def setSpriteAlpha(self, sid, alpha):
        try:
            s = self._sprites[sid]
        except:
            return

        if s[2] == alpha:
            return

        for tile in s[0]: # iterate over the tiles in the sprite
            self.setTileAlpha(tile, alpha)


    def setSpriteTransform(self, sid, xform, centered=None):
        try:
            s = self._sprites[sid]
        except:
            return

        tiles,(w,h),alpha,old_xform,old_centered = s

        if centered is None:
            centered = old_centered

        transform_info = self.getTransformInfo(w,h,xform,centered)

        ts = self._tile_size
        tiles_x = int(math.ceil(float(w)/ts))
        tiles_y = int(math.ceil(float(h)/ts))

        i = 0
        for y in xrange(tiles_y):
            for x in xrange(tiles_x):
                self.setTileTransform(tiles[i], (x,y), transform_info )
                i+=1


    def setSpriteGraphics(self, sid, surface):
        try:
            s = self._sprites[sid]
        except:
            return

        sprite_tiles,(w,h),alpha,xform,centered  = s

        for tile in sprite_tiles: # iterate over the tiles in the sprite
            self._free_tiles.add(tile)
            self.setTileAlpha(tile, 0) # this disables the rendering of the sprite


        s = self._newSpriteHlp(surface, alpha, xform, centered)

        self._sprites[sid] = s


    @profile
    def draw(self, scene):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_DEPTH_TEST)
        self._shader.begin()

        scene.uploadMatrices(self._shader)

        glBindVertexArray(self._vao)
        ofs = 0
        self._indices_vbo.bind()
        for t in self._textures:
            t.updateGlTexture()

            if t.isVboTainted():
                fac = _floats_per_vertex * 4 * fsize # bytes/quad
                self._vertices_vbo.bind()
                glBufferSubData(
                    GL_ARRAY_BUFFER,
                    fac * t._vbo_change_low,
                    fac * (t._vbo_change_high - t._vbo_change_low),
                    self._data[t._vbo_change_low*4:].ravel().ctypes.data_as(ctypes.c_void_p)
                )
                self._indices_vbo.bind()

            t.bind(self._texture_loc)

            glDrawElements(GL_TRIANGLES,self._total_tiles_per_texture*6, GL_UNSIGNED_SHORT, ctypes.c_void_p(ofs))

            ofs += self._vbo_index_bytes_per_texture

            t.reset()

        glBindVertexArray(0)
        self._shader.end()
        glEnable(GL_DEPTH_TEST)
        glDisable(GL_BLEND)



