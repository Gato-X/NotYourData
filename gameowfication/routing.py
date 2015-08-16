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


import Queue
import threading
import weakref

import numpy as N
import math
try:
    import Image, ImageDraw
except:
    from PIL import Image, ImageDraw

from mathtools import *
from libs.sortedcontainers.sorteddict import SortedList
from collections import namedtuple

class Traveller:
    def __init__(self, route_waypoints, map, speed=0.1, intro_fn=None, outro_fn=None, cruise_z_offset = 0):
        self.cruise_z_offset = (0,0,cruise_z_offset) if cruise_z_offset else 0.0
        self._route = iter(route_waypoints)
        self._map = map
        self._intro_fn = intro_fn # takes two parameters. Should return the last one as the last element
        self._outro_fn = outro_fn # takes two parameters. Should return the first one as the first element
        self._speed = speed
        self._waypoint_generator = self._getWaypoints()
        self._pos = self._next_pos = self._waypoint_generator.next()
        self._done = False

        # doesn't affect the intro/outro, but affects the parameters passed to those functions


    def _getNextRoutePoint(self):
        p = self._route.next()
        return N.array((p[0],p[1],self._map(p[0], p[1], False)), dtype="f") + self.cruise_z_offset

    def _getWaypoints(self):

        if self._intro_fn:
            p0 = self._getNextRoutePoint()
            p1 = self._getNextRoutePoint()
            for pt in self._intro_fn(p0,p1):
                p0 = pt
                yield pt
        else:
            p0 = self._getNextRoutePoint()
            yield p0

        p1 = self._getNextRoutePoint()
        while True:
            try:
                p2 = self._getNextRoutePoint()
            except StopIteration:
                if self._outro_fn:
                    for pt in self._outro_fn(p0,p1):
                        yield pt
                else:
                    yield p1
                raise StopIteration
            yield p1
            p0 = p1
            p1 = p2



    def advance(self, dt):
        if self._done: return None
        to_travel = dt * self._speed

        while True:
            v = self._next_pos - self._pos
            d = math.sqrt(N.dot(v,v))

            if to_travel > d:
                self._pos = self._next_pos
                try:
                    self._next_pos = self._waypoint_generator.next()
                except StopIteration:
                    self._done = True
                    return self._pos
                to_travel -= d
            else:
                self._pos = self._pos + v * to_travel / d
                self._pos[2] = max(self._pos[2], self._map(self._pos[0], self._pos[1],False))
                return self._pos





class Area:
    def __init__(self, x1,y1,x2,y2,extra=None):
        self.x1 = x1
        self.x2 = x2
        self.y1 = y1
        self.y2 = y2
        self.extra = extra
        self._adj = None

    def isFreeArea(self):
        try:
            int(self.extra)
            return True
        except:
            return False

    def rect(self): # returns the area in range 0..1
        return (self.x1,self.y1,self.x2,self.y2)


    def setFreeAreaId(self, id):
        self.extra = id


    def getFreeAreaId(self):
        return int(self.extra)


    def setChildren(self, ch):
        self.extra = ch


    def getChildren(self):
        assert not self.isFreeArea()
        return self.extra


    def __str__(self):
        if self.extra is None:
            return "A[%s]"%(self.rect(),)
        if self.isFreeArea():
            return "A[%s ID:%s]"%(self.rect(),self.extra)
        else:
            return "A[%s #C:%s]"%(self.rect(),len(self.extra))


    def distanceTo(self, other):
        dx = (other.x1+other.x2) - (self.x1+self.x2)
        dy = (other.y1+other.y2) - (self.y1+self.y2)

        return math.sqrt(dx*dx+dy*dy)*0.5


    def hasPoint(self, point):
        return (point[0]>=self.x1 and point[0]<=self.x2 and
                point[1]>=self.y1 and point[1]<=self.y2)


    def setAdjacencies(self, adj):
        self._adj = adj


    def getAdjacencies(self):
        return self._adj


    def getCenter(self):
        return (self.x1+self.x2)*0.5, (self.y1+self.y2)*0.5




class Router:
    def __init__(self, map, walkable_position, max_angle=45, smoothing=3, levels=6):
        self._map = map
        self._raster = self.getBlockingMap(max_angle, smoothing)
        self._free_areas = []
        self._root_area = None
        self.processAll(walkable_position, levels)


    def getBlockingMap(self, max_angle=30.0, threshold=3):
        normals = self._map.getNormals()
        assert(normals is not None)

        min_z = math.cos(max_angle / 180.0 * math.pi)

        n = normals[:,:,2]

        n = N.piecewise(n, [n<min_z,n>=min_z], [1,0])

        n1 = N.roll(n, 1,0)
        n2 = N.roll(n, -1,0)
        n3 = N.roll(n, 1,1)
        n4 = N.roll(n, 1,1)
        n5 = N.roll(n1,  1,1)
        n6 = N.roll(n1, -1,1)
        n7 = N.roll(n2,  1,1)
        n8 = N.roll(n2, -1,1)

        n = n+n1+n2+n3+n4+n5+n6+n7+n8

        return N.piecewise(n, [n<threshold,n>=threshold], [0,1])


    def processAll(self, walkable_position=None, levels=6):

        #saveMap(self._raster,"blocking.png")
        if walkable_position is not None:
            self.filterUnreachable(walkable_position)
        self.computeAreas(levels)
        self.buildGraph()
        #self.saveAreasImage("areas.png")

        self._raster = None # free the map


    def getContainingArea(self, map_pos):
       return self._getContainingArea(map_pos, self._root_area)



    def getAdjacencies(self, area_id):
        return self._free_areas[area_id].getAdjacencies()


    def printTouchingAreas(self, free_area_id):
        print "For region: ",self._free_areas[free_area_id]
        ta = self.getTouchingAreas(self._root_area, self._free_areas[free_area_id])
        for t in ta:
            print "    %s through %s"%(self._free_areas[t[0]], t[1])


    def saveAreasImage(self, filename, hilights=None, waypoints=None):

        img = Image.new("RGB", (self._map_w, self._map_h))
        draw = ImageDraw.Draw(img)

        for r in self._free_areas:
            draw.rectangle(r.rect(),outline=(64,0,0))

        if hilights:
            points=[]
            for hl,portal in hilights:
                r = self.getArea(hl)
                points.append(r.getCenter())

                draw.rectangle(r.rect(),fill=(0,0,128),outline=(128,0,0))

            draw.line(points, fill=(255,255,0))

            for hl,portal in hilights:
                if portal:
                    x0,y0,x1,y1 =  map(int,portal)

                    draw.line(((x0,y0),(x1,y1)),fill=(0,255,0))

        if waypoints:
            waypoints =[(w[0],w[1]) for w in waypoints]
            draw.point(waypoints,fill=(255,0,255))

            x,y = waypoints[0]
            draw.ellipse((x-1,y-1,x+1,y+1), fill=(128,128,128))

        img.save(filename)


    def printTree(self, area, indent=0):
        print " "*indent, area
        try:
            children = area.getChildren()
        except:
            return
        for c in children:
            self.printTree(c, indent+2)


    def getArea(self, area_id):
        return self._free_areas[area_id]

    #-- helper methods

    def filterUnreachable(self, reachable):
        # we'll use the flood fill in Image
        img = Image.fromarray(N.uint8(self._raster) * 64).copy()
        ImageDraw.floodfill(img,map(int,reachable[:2]), 128)
        n = N.array(img.getdata()).reshape(img.size[0], img.size[1])

        self._raster =  N.piecewise(n, [n==128,n!=128], [0,1])

        #img.save("filled.png")

        #saveMap(self._raster, "reachable.png")


    def computeAreas(self, depth=8):
        self._free_areas = []

        m = 2**depth

        h,w = self._raster.shape

        self._map_w = w
        self._map_h = h

        self._root_area = Area(0.0,0.0,w,h)

        self._split(self._root_area, depth)



    def buildGraph(self):
        self._adj = {}

        for area in self._free_areas:
            ta = self.getTouchingAreas(self._root_area, area) # this is rather expensive. So we cache it
            area.setAdjacencies(ta)



    # returns a list of (free_area_id, portal)
    def getTouchingAreas(self, node, area):
        if self.intersects(area, node):
            if node.isFreeArea():
                portal = self.getPortal(area, node)
                if portal is not None:
                    return [(node.getFreeAreaId(), portal)]
            else:
                touching = []
                for child in node.getChildren():
                    touching += self.getTouchingAreas(child, area)
                return touching

        return []


    def intersects(self, a1, a2):
        if a1.x1 > a2.x2: return False
        if a2.x1 > a1.x2: return False
        if a1.y1 > a2.y2: return False
        if a2.y1 > a1.y2: return False

        return True


    def touches(self, a1, a2):
        code = 0
        if a1.x1 == a2.x2: code |= 1
        if a2.x1 == a1.x2: code |= 1+4
        if a1.y1 == a2.y2: code |= 2+8
        if a2.y1 == a1.y2: code |= 2+16

        if (code & 3) == 3: return False # diagonal adjacent

        return code >> 2


    # areas must be touching. Otherwise it's undefined
    def getPortal(self, a1, a2):
        # vertical portal
        x0=x1=y0=y1=0
        if a1.x1 == a2.x2:
            x0 = x1 = a1.x1
            y0 = max(a1.y1,a2.y1)
            y1 = min(a1.y2,a2.y2)
        elif a2.x1 == a1.x2:
            x0 = x1 = a2.x1
            y0 = max(a1.y1,a2.y1)
            y1 = min(a1.y2,a2.y2)
        # horizontal portal
        elif a1.y1 == a2.y2:
            y0 = y1 = a1.y1
            x0 = max(a1.x1,a2.x1)
            x1 = min(a1.x2,a2.x2)
        elif a2.y1 == a1.y2:
            y0 = y1 = a2.y1
            x0 = max(a1.x1,a2.x1)
            x1 = min(a1.x2,a2.x2)

        if x0==x1 and y0==y1: return None
        return x0,y0,x1,y1

    #-- internal methods


    def _getContainingArea(self, pos, root_node):
        if root_node.hasPoint(pos):
            try:
                root_node.getFreeAreaId()
                return root_node
            except:
                for c in root_node.getChildren():
                    r = self._getContainingArea(pos, c)
                    if r is not None:
                        return r
        return None



    def _split(self, area, levels_to_go):

        obs = self._obstructed(area)

        if obs == 0: # not obstructed
            area.setFreeAreaId(len(self._free_areas)) # number of leaf
            self._free_areas.append(area)
            return True

        if levels_to_go==0 or obs == 2: # no more levels or fully obstructed
            return False

        x0,y0,x1,y1 = area.rect()
        xm = (x0+x1)/2
        ym = (y0+y1)/2

        levels_to_go -= 1

        sub_areas = [
            Area(x0,y0,xm,ym),
            Area(xm,y0,x1,ym),
            Area(x0,ym,xm,y1),
            Area(xm,ym,x1,y1)
        ]

        children = None

        for a in sub_areas:
            h = self._split(a, levels_to_go)
            if h:
                try:
                    children.append(a)
                except:
                    children = [a]

        area.setChildren(children)

        return bool(children)



    def _obstructed(self, area):
        x0,y0,x1,y1 = area.rect()
        x0 = int(x0)
        x1 = int(x1)
        y0 = int(y0)
        y1 = int(y1)
        o = N.any(self._raster[y0:y1,x0:x1])

        if o:
            if N.all(self._raster[y0:y1,x0:x1]):
                return 2
            return 1
        return 0



    def computeDistances(self, src, dest_list): # uses Dijkstra

        pm = self

        origin_area= self.getContainingArea(src)

        target_areas = [self.getContainingArea(dest) for dest in dest_list]
        target_area_ids = set([a.getFreeAreaId() if a is not None else -1 for a in target_areas ])

        if origin_area is None or not any(target_areas):
            return [None]*len(dest_list)

        search_front_queue = SortedList()

        search_front_queue.add((0,origin_area.getFreeAreaId()))
        search_front_p = {}
        target_distances = {}
        frozen = set()

        loops = 0

        while search_front_queue:
            loops += 1
            d,a = search_front_queue.pop(0)
            if a in frozen: # ignore duplicates
                continue

            # target found
            if a == target_area_ids:
                target_distances[a] = d
                target_area_ids.remove(a)
                if len(target_area_ids) == 0:
                    break

            frozen.add(a)

            area = pm.getArea(a)

            for adj, portal in area.getAdjacencies():
                if adj in frozen: # don't try to even check nodes that have been already frozen
                    continue

                new_d = d + area.distanceTo(pm.getArea(adj))

                # route to adj through a is longer than what we already had. Dismiss
                if adj in search_front_p and new_d > search_front_p[adj]:
                    continue

                search_front_p[adj] = new_d
                # this might add duplicate adj items (ideally we would delete any previous insertion)
                # because we can't easily erase from the queue.
                search_front_queue.add((new_d, adj))

        distances = []
        for t in target_area_ids:
            try:
                distances.append(target_distances[t])
            except:
                distances.append(None)

        return distances



    def computeRoute(self, src, dest): # uses A*
        pm = self

        origin_area= self.getContainingArea(src)
        target_area = self.getContainingArea(dest)

        if origin_area is None or target_area is None:
            return None

        origin_area_id = origin_area.getFreeAreaId()
        target_area_id = target_area.getFreeAreaId()

        search_front_queue = SortedList()
        h = 0#origin_area.distanceTo(target_area) # A* heuristic distance value

        search_front_queue.add((h,h,origin_area_id))
        search_front_p = {}
        frozen = set()

        loops = 0

        while search_front_queue:
            loops += 1
            d,old_h,a = search_front_queue.pop(0)
            if a in frozen: # ignore duplicates
                continue


            # target found
            if a == target_area_id:
                break

            frozen.add(a)

            area = pm.getArea(a)

            for adj, portal in area.getAdjacencies():
                if adj in frozen: # don't try to even check nodes that have been already frozen
                    continue

                dg = area.distanceTo(pm.getArea(adj))

                new_h = area.distanceTo(target_area)

                new_d = d+dg-old_h+new_h

                # route to adj through a is longer than what we already had. Dismiss
                if adj in search_front_p and new_d > search_front_p[adj][0]:
                    continue

                search_front_p[adj] = (new_d, a, portal)
                # this might add duplicate adj items (ideally we would delete any previous insertion)
                # because we can't easily erase from the queue.
                search_front_queue.add((new_d, h, adj))

        p = target_area_id
        route = [(p,None)] # stores tuples: area_number, exit portal
        while p in search_front_p:
            _,prev,portal = search_front_p[p]
            route.append((prev, portal))
            p = prev

        route.reverse()

        return route


    def getWaypointCalculator(self, source, dest, randomize = True):
        route = self.computeRoute(source, dest)
        return self._routeWaypointCalculator(source, dest, route, randomize)


    # smooth out the path
    def _routeWaypointCalculator(self, src, dest, route, randomize=True):
        yield src
        pos = src[0:2]

        next_area = next_portal = next_area_center = None

        for i in xrange(0, len(route)):

            portal = next_portal
            area_center = next_area_center

            next_a_num,next_portal = route[i]
            next_area = self.getArea(next_a_num)
            next_area_center = next_area.getCenter()

            if i == 0: continue

            x,y = pos

            line = (x,y,next_area_center[0], next_area_center[1])
            pt, st, within = getSegmentIntersection(portal, line, only_in_segment=False)

            # see if we can go from where we are to the center of the next area
            # in a straight line


            if within:# we advanced to the next area in a straight line towards its center
                pos = pt
                yield pt
            else:# we advance towards the exit portal, with a little curve
                s = st[0]
                if s<0.1: s = 0.1
                elif s>0.9: s = 0.9
                pos = new_x,new_y = (portal[2]-portal[0])*s + portal[0], (portal[3]-portal[1])*s + portal[1]

                # midpoint between portal exits
                mx,my= (new_x+x)*0.5, (new_y+y)*0.5

                #push it a little bit towards the area center

                yield (area_center[0]-mx)*0.1+mx, (area_center[1]-my)*0.1+my

                yield pos

        if len(route)<2:
            # so we have at least three waypoints
            yield (src[0]+dest[0])*0.5, (src[1]+dest[1])*0.5


        yield dest


class RouterBatchProcessor:
    def __init__(self, router):
        self._router = router
        self._to_do = Queue.Queue()
        self._done = Queue.Queue()

        self._do_end = False

        self._thread = threading.Thread(target = self._worker)
        self._thread.start()


    def requestJob(self, src, dest, method, obj=None):
        self._to_do.put((src, dest, (method, weakref.ref(obj) if obj else None)))


    def dispatch(self): # dispatch only one (will call this every frame)
        try:
            cb, result = self._done.get(False)
            method, object = cb
            if object:
                o = object()
                if o is not None:
                    method(o,result)
            else:
                method(result)
        except Queue.Empty:
            pass


    def finish(self):
        self._do_end = True
        self._thread.join()


    def _worker(self):
        while not self._do_end:
            try:
                src, dest, cb = self._to_do.get(True,0.5)
                wp = self._router.getWaypointCalculator(src, dest)
                self._done.put((cb, wp))

            except Queue.Empty:
                pass

