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


import numpy as N
import libs.transformations as T
import math

class Entity:
    _grid = {}

    def __init__(self):
        self._pos = N.array((0,0,0),dtype="f")
        self._pos_m = T.identity_matrix()
        self._grid_cell = 0
        self._bounds= N.array(((0,0,0),(0,0,0)),dtype="f")
        self._grid_x = 0
        self._grid_y = 0
        self._closing = False

    # removes the entity from the grid
    def destroy(self):
        try:
            self._grid[self._grid_cell].remove(self)
        except:
            pass


    def setBounds(self, bounds):
        self._bounds[0][:] = bounds[0]
        self._bounds[1][:] = bounds[1]


    def getPosition(self):
        return self._pos


    def moveTo(self, pos):
        gx = int(pos[0]/16)
        gy = int(pos[1]/16)

        if gx != self._grid_x or gy != self._grid_y:
            self._grid_x = gx
            self._grid_y = gy

            try:
                self._grid[self._grid_cell].remove(self)
            except:
                pass

            self._grid_cell = gc = (gx,gy)

            try:
                self._grid[gc].add(self)
            except:
                self._grid[gc]={self}

        self._pos[:] = pos
        self._pos_m = T.translation_matrix(pos)


    def getCloseEntities(self):
        gclist = [self._grid_cell]

        fx = math.modf(self._pos[0])
        fy = math.modf(self._pos[1])

        # a bit repetitive, but optimized
        if fx < 0.5:
            gclist.append((self._grid_x-1, self._grid_y))
            if fy < 0.5:
                gclist.append((self._grid_x, self._grid_y-1))
                gclist.append((self._grid_x-1, self._grid_y-1))
            else:
                gclist.append((self._grid_x, self._grid_y+1))
                gclist.append((self._grid_x-1, self._grid_y+1))

        elif fx > 0.5:
            gclist.append((self._grid_x+1, self._grid_y))
            if fy < 0.5:
                gclist.append((self._grid_x, self._grid_y-1))
                gclist.append((self._grid_x+1, self._grid_y-1))
            else:
                gclist.append((self._grid_x, self._grid_y+1))
                gclist.append((self._grid_x+1, self._grid_y+1))
        else:
            if fy < 0.5:
                gclist.append((self._grid_x, self._grid_y-1))
            else:
                gclist.append((self._grid_x, self._grid_y+1))

        nearby = []
        for gc in gclist:
            try:
                nearby += filter(lambda e:e!=self, self._grid[gc])
            except:
                continue

        return nearby

    def getCollisions(self):
        collisions = []
        for g in self.getCloseEntities():
            if self.collidesWith(g):
                collisions.append(g)

        return collisions



    def collidesWith(self, other_entity):
        if other_entity._closing:
            return False

        pmin = self._pos + self._bounds[0]
        omax = other_entity._pos + other_entity._bounds[1]

        if pmin[0] > omax[0]: return False
        if pmin[1] > omax[1]: return False
        if pmin[2] > omax[2]: return False

        omin = other_entity._pos + other_entity._bounds[0]
        pmax = self._pos + self._bounds[1]

        if omin[0] > pmax[0]: return False
        if omin[1] > pmax[1]: return False
        if omin[2] > pmax[2]: return False

        return True
