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
import math
import libs.transformations as T


ZeroVec3 = N.array((0,0,0), dtype="f")

def cartesianProduct(arrays):
    broadcastable = N.ix_(*arrays)
    broadcasted = N.broadcast_arrays(*broadcastable)
    rows, cols = reduce(N.multiply, broadcasted[0].shape), len(broadcasted)
    out = N.empty(rows * cols, dtype="f")
    start, end = 0, rows
    for a in broadcasted:
        out[start:end] = a.reshape(-1)
        start, end = end, end + rows
    return out.reshape(cols, rows).T


def swapColumns(mat, col1, col2):
    mat[:,[col1,col2]] = mat[:,[col2, col1]]

def mmult(*matrices):
    return reduce(lambda a,b:N.dot(a,b), matrices)


def lookAtMtx(eye, target, up):
    fwd = target - eye
    fwd = T.unit_vector(fwd)
    side = N.cross(fwd, up)
    side = T.unit_vector(side)
    up = N.cross(side, fwd)
    M = N.identity(4,dtype="f")
    M[0,0:3] = side
    M[1,0:3] = up
    M[2,0:3] = -fwd
    M[0:3,3] = N.dot(M[0:3,0:3],-eye)
    return M


class HeadingController:
    def __init__(self, banking = 1.0, easing = 0.95, max_bank=1.0):
        self._banking = banking
        self._accel = None
        self._last_pos = None
        self._easing = easing
        self._pos = None
        self._last_fwd = (0,0,0)
        self._last_banking_angle = 0
        self._max_bank = max_bank


    def __call__(self, pos):

        try:
            self._accel = pos - 2.0 * self._last_pos + self._pos
        except:
            b = T.identity_matrix()
        else:
            fwd = pos - self._pos

            fwd = (-fwd + self._last_fwd)*self._easing + fwd

            self._last_fwd = fwd


            fwd = T.unit_vector(fwd)
            side = N.cross(fwd, (0.,0.,1.))
            side = T.unit_vector(side)
            up = N.cross(side, fwd)#(fwd[1], -fwd[0], 0) # #same thing
            M = N.identity(4,dtype="f")
            M[0,0:3] = fwd
            M[1,0:3] = side
            M[2,0:3] = up
            #M[0:3,3] = N.dot(M[0:3,0:3],pos)

            a = self._accel

            bank_angle = (a[0] * fwd[1] - a[1] * fwd[0]) * self._banking

            bank_angle = max(min(bank_angle, self._max_bank), -self._max_bank)

            bank_angle = (bank_angle - self._last_banking_angle)*self._easing + self._last_banking_angle

            self._last_banking_angle = bank_angle

            c = math.cos(bank_angle)
            s = math.sin(bank_angle)

            B = N.identity(4,dtype="f")
            B[1,1] = B[2,2] = c
            B[2,1] = s
            B[1,2] = -s

            #print side, N.linalg.det(M)
            b = N.dot(M,B)



        self._last_pos = self._pos
        self._pos = pos

        return b




def frustumProjMtx(fovy, near, far, aspect=0):
    if aspect == 0:
        from gltools import getViewportSize
        w,h = getViewportSize()
        aspect = float(w) / float(h)
    h = math.tan(fovy / 360.0 * math.pi) * near
    w = h * aspect
    return T.clip_matrix(-w, w, -h, h, near, far, perspective=True)

# seg1,2 are tuples/lists/arrays like so: (x0,y0,x1,y1)
# returns None if no intersection occurs or if it occurs but lies outside
# the segment and only_in_segment is true
# or ((x,y),(t0,t1),within_segment)
# first the point where lines intersects
# then the t of each segment
# then whether the intersection occurs within the segments

def getSegmentIntersection(seg1, seg2, only_in_segment=True):
    s1_x = seg1[2] - seg1[0];     s1_y = seg1[3] - seg1[1]
    s2_x = seg2[2] - seg2[0];     s2_y = seg2[3] - seg2[1]

    d = (-s2_x * s1_y + s1_x * s2_y)

    if d>-0.00001 and d < 0.00001:
        return None

    t = (-s1_y * (seg1[0] - seg2[0]) + s1_x * (seg1[1] - seg2[1])) / d
    s = ( s2_x * (seg1[1] - seg2[1]) - s2_y * (seg1[0] - seg2[0])) / d

    within_segment = s>=0 and s<=1 and t>=0 and t<=1

    if only_in_segment and not within_segment:
        return None

    px = seg1[0] + (s * s1_x)
    py = seg1[1] + (s * s1_y)

    return (px,py),(s,t),within_segment



def saveMap(map, filename):
    try:
        import Image
    except:
        from PIL import Image

    shape = map.shape

    mv = max(map.flatten())


    scaling = 1.0 if mv > 1.0 else 255.0

    im = Image.fromarray(N.uint8(map*scaling))

    im.save(filename)
