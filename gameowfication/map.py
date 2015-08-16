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


import pygame
from profiler import profile
try:
    import Image
except:
    from PIL import Image

import ConfigParser
import math
import numpy as N
import resources as R
from gltools import *
from mathtools import *
#from OpenGL.arrays import vbo
#from OpenGL.GL import *


class Map:
    def __init__(self, mapfile, no_gl=False): #height_map = None, textures = None, shader = None):
        self._dimensions = (0,0)

        self._map_locations = {}

        self._marker_colors = {}
        self._no_gl = no_gl

        self._player_initial_position = (0,0)
        self._bases_positions = []
        self._drop_point_positions = []
        self._target_point_positions = []
        self._enemy_start_positions = []
        self._map = None
        self._normals = None

        self._indices_vbo = None
        self._map_positions_vbo = None
        self._patch_index_offsets = []
        self._total_patches = 0
        self._vao = 0

        self.loadConfig(mapfile)

        self._shader = None

        if not no_gl:
            if self._shader_name:
                self._shader = R.getShaderProgram(self._shader_name)
                self._map_world_scale_loc = self._shader.getUniformPos("world_scale")
            else:
                self._map_world_scale_loc = -1

        if self._height_map is not None:
            self.loadMap()



    def loadConfig(self,mapfile):

        cfg = ConfigParser.ConfigParser()
        cfg.readfp(R.openResource(mapfile + ".map"))

        def get(option, default=None, section="Main"):
            try:
                return cfg.get(section, option)
            except:
                return default

        def getColor(option, default=(0,0,0), section="MapMarkerColors"):
            try:
                col = cfg.get(section, option).strip()
            except:
                return default

            if ',' in col:
                col = col.replace("(","").replace(")","")
                col = map(int,col.split(','))
            else:
                col = pygame.Color(col)
                col = col.r, col.g, col.b

            return col

        self._shader_name = get("shader")
        self._height_map = get("height_map")
        self._texture_map = get("texture_map")
        self._detail_map = get("detail_map")

        self._textures = [self._texture_map, self._detail_map]

        for name, color in cfg.items("MapMarkerColors"):
            self._marker_colors[name] = getColor(name)

        print "Markers:"
        print self._marker_colors




    def getResourcePositions(self, resource):
        try:
            return self._map_locations[resource]
        except:
            return []


    def getPlayerInitialPosition(self):
        return self._map_locations["player"][0]


    def loadTextures(self):
        texture_binders = []
        for i,t in enumerate(self._textures):
            if t is not None:
                binder = R.loadTexture(t).getBinder(i,self._shader.getUniformPos("texture%s"%i))
                texture_binders.append(binder)

        # replace the texture name with the binder
        self._textures = texture_binders

    def loadMap(self):
        print "Loading map..."
        if not self._no_gl:
            self.loadTextures()

        img = R.loadImage(self._height_map)
        img = img.convert("RGB")
        #img = img.transpose(Image.ROTATE_270)
        w,h = img.size

        self._dimensions = w,h

        m = N.array(img.getdata()).reshape(h,w,3)

        r = m[:,:,0]
        g = m[:,:,1]
        b = m[:,:,2]

        low = N.where(r<g, r,g)
        low = N.where(low<b, low, b)

        high = N.where(r>g, r,g)
        high = N.where(high>b, high, b)

        marks = N.where((high-low) > 5)
        marks = N.transpose(marks)
        marks = N.roll(marks, 1,1) # swap x's and y's

        # extract the colors so we can identify the marker type.
        # the m array won't be available for long
        mark_colors = []
        for mk in marks:
            mark_colors.append(m[mk[1], mk[0], :])

        # square the map height so we can have better detail at low heights
        # and high peaks
        m = N.array((r+g+b) * 0.006,dtype="f")
        self._map = m*m

        self.processLocations(marks, mark_colors)

        self.computeNormals()

        if self._shader: #otherwise we assume it won't be displayed
            self.prepareTiles()

        print "Loaded"


    def processLocations(self, marks, colors):
        print "Fixing gaps..."

        for xy,marker_color in zip(marks,colors):
            x,y=xy
            self._map[y,x] = N.median(self._map[y-1:y+1,x-1:x+1].flatten())

            for loc_name, loc_type_color in self._marker_colors.iteritems():
                found = False
                if isColorLike(loc_type_color, marker_color):
                    z = self(x,y,False)
                    pos = N.array((x,y,z),dtype="f")
                    try:
                        self._map_locations[loc_name].append(pos)
                    except:
                        self._map_locations[loc_name]=[pos]
                    print "%s : %s,%s "%(loc_name, x,y)
                    found = True
                    break
                if not found:
                    print "Unknown marker with color: %s"%marker_color



    def computeNormals(self):
        print "Computing normals..."
        w,h = self._dimensions

        self._normals = N.zeros((h,w,3), dtype="f")

        grad = N.gradient(self._map)

        mag = 1.0/N.sqrt(grad[0]*grad[0] + grad[1]*grad[1] + 1.0)

        self._normals = N.array([-grad[1]*mag, -grad[0]*mag, mag])
        self._normals = self._normals.transpose(1,2,0)



    def getNormals(self):
        return self._normals


    def getTotalPatchVertices(self, x0, y0, x1, y1):
        dx = x1-x0
        dy = y1-y0
        n = (dx * (2*dy-2) + (dy-2)*2)
        return n

        # x1 and y1 are NOT included
    def calcPatchTriStripsIndices(self, x0, y0, x1, y1):
        w = self._dimensions[0]
        dx = x1-x0
        dy = y1-y0

        idx = N.zeros( self.getTotalPatchVertices(x0,y0,x1,y1))

        y_2 = y1-2
        w_1 = w-1
        dx_1 = dx-1
        j = 0
        p = w * y0 + x0
        y = y0

        while (True):
            for x in xrange(dx):
                idx[j] = p
                j += 1
                p+= w # move down
                idx[j] = p
                j += 1
                p-= w_1 # move up-right
            if y == y_2: break
            p += w_1 # move down-left
            idx[j] = p # degenerate vertex
            j += 1
            p -= dx_1 # move all the way left
            idx[j] = p # degenerate vertex
            j += 1
            y += 1

        return idx

    # get the rects (extensions) of all patches (x0,y0,x1,y1)
    def computePatchRects(self, patch_w = 200, patch_h = 200):
        w,h = self._dimensions
        x = y = 0

        rects = []

        while True: # on y
            ny = min(y + patch_h+1, h)
            while True: # on x
                nx = min(x + patch_w+1, w)
                rects.append((x,y,nx,ny))
                x = nx-1
                if nx == w: break
            x,y = 0,ny-1
            if ny == h: break

        return rects

    # TODO: create VBO and VAO in constructor
    def prepareTiles(self):

        self._vao = glGenVertexArray()
        glBindVertexArray(self._vao)

        w,h = self._map.shape

        print "Creating VBO...", w,h

        # the first array changes the slowest
        vertices = cartesianProduct([N.linspace(0,h-1,h), N.linspace(0,w-1,w), [0]])

        # we want to traverse along x first
        swapColumns(vertices,0,1)

        vertices[:,2] = self._map.ravel()

        self._map_positions_vbo = vbo.VBO(vertices,usage=GL_STATIC_DRAW)
        self._map_positions_vbo.bind()
        self._map_positions_vbo.copy_data()

        glEnableVertexAttribArray(self._shader.attr_position)
        glVertexAttribPointer(self._shader.attr_position, 3, GL_FLOAT, False, 0, None)

        patches = self.computePatchRects()

        self._total_patches  = len(patches)

        print "total patches: ",self._total_patches

        total_indices = sum(map(lambda p:self.getTotalPatchVertices(*p), patches))

        print "total indices: ",total_indices

        indices = N.zeros(total_indices, dtype = N.int32) # make a large enough array

        self._patch_bounds = N.zeros((self._total_patches, 2, 3), dtype = "f")
        self._patch_indices = N.zeros((self._total_patches, 2), dtype=N.int32)

        i_pos = 0
        i = 0
        for x0,y0,x1,y1 in patches:
            # append the indices of the patch to the list of indices
            p_idx = self.calcPatchTriStripsIndices(x0,y0,x1,y1)
            p_size = p_idx.shape[0]
            indices[i_pos:i_pos+p_size]=p_idx
            # compute the bounding box of the patch
            pvals = self._map[y0:y1, x0:x1].ravel()

            z0 = min(pvals)
            z1 = max(pvals)
            self._patch_bounds[i] = ((x0,y0,z0),(x1-1, y1-1,z1))
            self._patch_indices[i] = (p_size, i_pos)  # (total indices, first index) of patch
            # update the index offset
            i_pos += p_size
            i += 1

        #Create the index buffer object
        self._indices_vbo = vbo.VBO(indices, target=GL_ELEMENT_ARRAY_BUFFER)


        self._indices_vbo.bind()
        self._indices_vbo.copy_data()

        for i in xrange(self._total_patches):
            ofs = int(self._patch_indices[i][1]) * ctypes.sizeof(ctypes.c_int32)
            self._patch_index_offsets.append(ctypes.c_void_p(ofs))

        glBindVertexArray(0)

    # evaluate the map at a given coordinate
    def __call__(self, x, y, with_normal=True):
        m = self._map
        n = self._normals

        xf,xi = math.modf(x)
        yf,yi = math.modf(y)

        try:
            if (xf > (1-yf)): # triangle of points [x,y+1], [x+1,y], [x+1,y+1]
                xf = 1-xf
                yf = 1-yf
                pos = (1-xf-yf) * m[yi+1,xi+1] + yf * m[yi,xi+1] + xf * m[yi+1,xi]
                if not with_normal:
                    return pos

                norm = (1-xf-yf) * n[yi+1,xi+1] + yf * n[yi,xi+1] + xf * n[yi+1,xi]
                #nx = -(m[yi+1,xi+1] - m[yi+1,xi])
                #ny = -(m[yi+1,xi+1] - m[yi,xi+1])
                #d = 1.0/math.sqrt(1.0 + nx*nx + ny*ny)

                return pos, norm #N.array((nx*d, ny*d, d), dtype="f")

            else: # triangle of points [x,y], [x,y+1], [x+1,y]
                pos = (1-xf-yf) * m[yi,xi] + xf * m[yi,xi+1] + yf * m[yi+1,xi]
                if not with_normal:
                    return pos

                norm = (1-xf-yf) * n[yi,xi] + xf * n[yi,xi+1] + yf * n[yi+1,xi]
                #nx = (m[xi,yi] - m[yi,xi+1])
                #ny = (m[xi,yi] - m[yi+1,xi])
                #d = 1.0/math.sqrt(1.0 + nx*nx + ny*ny)

                return pos, norm #N.array((nx*d, ny*d, d), dtype="f")
        except:
            if not with_normal:
                return 0.0
            return 0.0, N.array((0,0,1),dtype="float")


    @profile
    def draw(self, scene):

        glBindVertexArray(self._vao)
        self._shader.begin()

        glUniform2f(self._map_world_scale_loc, self._dimensions[0], self._dimensions[1] )

        for t in self._textures: t()

        scene.uploadMatrices(self._shader)

        self._indices_vbo.bind()

        for i in xrange(self._total_patches):
            cnt = int(self._patch_indices[i][0])
            glDrawElements(GL_TRIANGLE_STRIP,cnt,
                            GL_UNSIGNED_INT, self._patch_index_offsets[i])
        self._shader.end()

        glBindVertexArray(0)












