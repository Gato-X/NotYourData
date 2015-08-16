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


#from OpenGL.arrays import vbo
from profiler import profile
from glcompat import *
from gltools import *
import resources as R
import numpy as N
import math
import random
import time

_attrlist = [ # attribute name, floats used
             ("angle",1),
             ("rand",1),
             ("age",1),
             ("center",3),
             ("speed",3)
           ]

_fields_per_vertex = sum (a[1] for a in _attrlist)

ONCE_MODE = 2
DYNAMIC_MODE = 0
LOOP_MODE = 1

# must be obtained with ParticleController.getGenerator
class ParticleGenerator:

        _uniforms = ("acceleration","growth","rotation","easing","params1")

        def __init__(self, shader_name, texture_name):
            self._shader_name = shader_name
            self._texture_name = texture_name

            self._shader = R.getShaderProgram(shader_name)

            self._tbinder = None
            self._texture = None

            if texture_name:
                self._texture = R.loadTexture(texture_name) if texture_name else None
                if self._texture:
                    tloc = self._shader.getUniformPos("texture0")
                    self._tbinder = self._texture.getBinder(0, tloc) if tloc>-1 else None

            self._tot_vert_gl = 0
            self._ofs_gl = None

            for uni in self._uniforms:
                setattr(self, "_"+uni+"_uni", self._shader.getUniformPos(uni))

            self.reset()


        def reset(self):
            self.setSpawnSpeed()
            self.setAcceleration()
            self.setEasing()
            self.setRotationRange()
            self.setEvolveTime()
            self.setMode()
            self.setPosition()
            self.setBrightness()
            self._active_particles_range = (0,0)

        #----

        def getSlotId(self):
            return self._slot


        def getShader(self):
            return self._shader


        def getTextureName(self):
            return self._texture_name


        def getTextureBinder(self):
            return self._tbinder


        def bindTexture(self):
            if self._tbinder: self._tbinder()


        def setSpawnSpeed(self, tot=50): # particles per second
            self._spawn_speed = tot


        def setAcceleration(self, accel=(0,0,5)): #usually a vector
            if accel == 0:
                self._accel = N.array((0.0,0.0,0.0),dtype="f")
            else:
                self._accel = N.array(accel,dtype="f")


        def setEasing(self, ease_in=0.2, ease_out=0.8, initial_size=0.0, mid_size=0.1, decay_size=0.2):
            self._growth = N.array((initial_size, mid_size, decay_size),dtype="f")
            self._easing = N.array((ease_in, 1.0 - ease_out),dtype="f")


        def setRotationRange(self, min_speed=-3.0, max_speed=3.0):
            self._rot = N.array((min_speed, max_speed), dtype="f")


        def setEvolveTime(self, time = 2): # particles last by default 2 seconds
            self._evolve_speed = 1.0 / time


        # can be a callable, in which case it's called repetitively (with "time" as parameter) to get
        # a position for new particles
        def setPosition(self, position = (0.,0.,0.), speed=None):
            position = N.array(position,dtype="f")
            if speed is None:
                def emitter(t):
                    while True:
                        dx = 2.*random.random()-1.
                        dy = 2.*random.random()-1.
                        dz = 2.*random.random()-1.

                        r = dx*dx+dy*dy+dz*dz

                        if r < 1.0:
                            return position, (dx,dy,dz)

                self._emitter = emitter
            else:
                speed = N.array(speed,dtype="f")
                def emitter(t):
                    return position, speed

                self._emitter = emitter

        def setBrightness(self, b = 1.0):
            self._brightness = b

        # emitter must be a callable that:
        # pos, speed = emitter(time)
        def setEmitter(self, emitter):
            self._emitter = emitter


        # DYNAMIC particles are constantly being renewed
        # LOOP particles are computed once and displayed over and over
        # ONCE particles are computed once and displayed once

        # max_particles is ignored for DYNAMIC particles
        def setMode(self, mode = "DYNAMIC", max_particles=100):
            self._mode = {"DYNAMIC":DYNAMIC_MODE, "LOOP":LOOP_MODE, "ONCE":ONCE_MODE}[mode]
            self._max_particles = max_particles

        #---- The following methods should only be called by the ParticleController

        # called by the controller when the Generator is attached to it.
        def beginManaged(self,controller,slot_number, data_view):
            self._controller = controller
            self._particles_per_generator = controller.getParticlesPerGenerator()
            self._slot = slot_number
            self._data = data_view
            self._last_t = 0
            self._buffer_tail = self._buffer_head = 0
            self._to_spawn = 0
            self._max_particles = min(self._max_particles, self._particles_per_generator)
            self._wants2die = False
            self._is_managed = True
            self._update_fn = self.dynamicUpdate if self._mode==DYNAMIC_MODE else self.nonDynamicUpdate
            self._max_time = None
            self._time = None


        def destroy(self):
            # once mode stops automatically
            if self._mode != ONCE_MODE:
                self._spawn_speed = 0
                self._update_fn = self.updateDying


        def endManaged(self):
            self._is_managed = False
            self._controller = None # to avoid circular references
            pass


        def update(self, time):
            time *= 0.001*self._evolve_speed
            self._time = time

            if self._last_t == 0:
                r = True
            else:
                r = self._update_fn()

            self._last_t = self._time

            return r


        def nonDynamicUpdate(self):
            def dummy() : return True

            if self._mode == ONCE_MODE:
                self._update_fn = self.updateDying
            else:
                self._update_fn = dummy # already initialized, no need for calling it again

            if self._mode == ONCE_MODE: # once:
                cycles = 1
            else:
                cycles = int(self._particles_per_generator / self._max_particles)

            t0,t1 = 0, cycles * self._max_particles

            self.spawn(t0,t1 , self._time, 1.0 / self._max_particles)

            self._buffer_tail, self._buffer_head = t0,t1

            self.updateActiveParticleRange(t0,t1)

            return t0,t1




        def dynamicUpdate(self):
            # returns:
            # True: no change
            # False: particle no longer needs to be managed
            # (t0,t1) the range of particles that changed

            time = self._time

            max_s = self._particles_per_generator

            dt = float(time - self._last_t) # time in "particle lives"

            t0, t1 = self._buffer_tail, self._buffer_head

            tail_moved = added_particles = False

            # see if there are particles that died now
            while self._data[t0*4,2]+self._time > 1.0: # field2 = age

                tail_moved = True
                t0 += 1
                if t0 == max_s:
                    t0 = 0
                if t0 == t1:  # empty buffer
                    break
            self._buffer_tail = t0

            tot_p = t1-t0 # total particles

            if tot_p < 0:
                tot_p += max_s

            # see if we need to spawn more particles
            self._to_spawn += dt * self._spawn_speed


            to_spawn = math.floor(self._to_spawn)

            if to_spawn>0:
                self._to_spawn -= to_spawn

                to_spawn = int(min(to_spawn, max_s-1))

                s0 = t1
                s1 = s0 + to_spawn

                p_dt = dt / to_spawn

                t = self._time-dt

                if s1 > max_s:
                    self.spawn(s0, max_s, t, p_dt) # buffer wraps around
                    s1 -= max_s
                    self.spawn(0, s1, t+p_dt*(max_s - s0), p_dt)
                    n0,n1 = 0, max_s # range of fields to update in the VBO
                else:
                    self.spawn(s0, s1, t, p_dt)
                    n0,n1 = s0,s1

                t1 = s1 if s1 < max_s else 0 #new head

                # see if we stepped on previous particles
                if tot_p + to_spawn >= max_s:
                    t0 = t1+1
                    if t0 == max_s:
                        t0 = 0

                added_particles = n0,n1

            if added_particles or tail_moved:
                self._buffer_tail, self._buffer_head = t0,t1
                # compute range in buffer used by particles (may be split in two:
                # at the end and at the beginning. If so, then use the whole range
                if t0 > t1:
                    t0,t1 = 0, max_s

                self.updateActiveParticleRange(t0,t1)

                if added_particles:
                    return added_particles

            return True


        def updateDying(self):
            if self._max_time is None:
                self._max_time = self._time + 2.1
            elif self._time > self._max_time:
                # the Generator can be disposed
                return False
            # there are still particles
            return True



        def spawn(self, s0, s1, t, dt):
            max_s = self._particles_per_generator
            e = self._emitter

            while s0 != s1:
                if s0 == max_s:
                    s0 = 0

                pos,speed = e(t)

                # four vertices per particle
                s = s0*4
                i = 0
                while i<4:
                    self._data[s+i,3:6] = pos
                    self._data[s+i,6:9] = speed
                    self._data[s+i,2] = -t
                    i+=1

                s0 += 1
                t += dt


        def updateActiveParticleRange(self, t0, t1):
            old_t0, old_t1 = self._active_particles_range
            if t0 < old_t0 or t1 > old_t1 or (t0 - old_t0)>50 or (old_t1 - t1)>50:
                self._active_particles_range = t0, t1
                self.recomputeGlData()



        def recomputeGlData(self):
            t0,t1 = self._active_particles_range
            first_part = self._particles_per_generator * self._slot + t0
            first_vert = first_part * 6

            self._tot_vert_gl = (t1-t0) * 6
            self._ofs_gl = ctypes.c_void_p(ctypes.sizeof(ctypes.c_uint16) * first_vert)


        def draw(self):
            if not self._time:
                return
            # load uniforms (fields created dynamically in constructor)
            glUniform3f(self._acceleration_uni, self._accel[0], self._accel[1], self._accel[2])
            glUniform3f(self._growth_uni, self._growth[0], self._growth[1], self._growth[2])
            glUniform2f(self._rotation_uni, self._rot[0], self._rot[1])
            glUniform2f(self._easing_uni, self._easing[0], self._easing[1])
            glUniform3f(self._params1_uni, self._time, 1.0 if self._mode==LOOP_MODE else 0.0, self._brightness)
            #glUniform3f(self._params1_uni, self._time, 0.0, 1.0)
            # draw the quads
            glDrawElements(GL_TRIANGLES, self._tot_vert_gl, GL_UNSIGNED_SHORT, self._ofs_gl)



class ParticleController:
    def __init__(self, max_particles=10000): # max: 10900
        self._max_particles_per_generator = 100
        self._max_particles = max_particles
        max_generators = max_particles / self._max_particles_per_generator
        self._free_slots = set(range(max_generators))
        self._lru_slots = []
        self._generators = [None] * max_generators
        self._vao = {} # all used VAO indexed by shader

        self._data = N.zeros((self._max_particles*4, _fields_per_vertex),dtype="f")
        self._batches = []
        # uniforms: accel x,y,z, time

        self.initBuffers()

    def getParticlesPerGenerator(self):
        return self._max_particles_per_generator

    def initBuffers(self):

        tot_indices = self._max_particles*6

        indices = N.zeros(tot_indices, dtype=N.uint16)

        # set up the indices (we won't need to change these anymore)
        i = 0
        j = 0
        while i < tot_indices:
            indices[i] = j
            indices[i+1] = j+1
            indices[i+2] = j+2
            indices[i+3] = j+0
            indices[i+4] = j+2
            indices[i+5] = j+3
            j+=4; i+=6
        # set up the corner angles in the self._data
        j = 0
        angle = [i*math.pi/2. + math.pi/4. for i in range(4)]
        for i in xrange(self._max_particles):
            # corners
            self._data[j][0] = angle[0]
            self._data[j+1][0] = angle[1]
            self._data[j+2][0] = angle[2]
            self._data[j+3][0] = angle[3]
            # random/particle ido
            r = (i % self._max_particles_per_generator) + random.random()
            self._data[j][1] = r
            self._data[j+1][1] = r
            self._data[j+2][1] = r
            self._data[j+3][1] = r
            j+= 4

        self._data_vbo = vbo.VBO(self._data.flatten(), GL_STREAM_DRAW)
        self._data_vbo.bind()
        self._indices_vbo = vbo.VBO(indices.flatten(), GL_DYNAMIC_DRAW, target=GL_ELEMENT_ARRAY_BUFFER)
        self._indices_vbo.bind()



    # upload changed data to the VBO
    def loadGeneratorData(self, g, n0, n1):
        # n0,n1 are in the range [0..0..self._max_particles_per_generator]
        # indicate the range of particles that the generator updated

        snum = g.getSlotId()

        s0 = self._max_particles_per_generator * snum

        n0p = (s0+n0) * _fields_per_vertex
        n1p = (s0+n1) * _fields_per_vertex


        #self._data_vbo.bind() already bound when calling this

        #


        ptr = self._data[(s0+n0)*4:(s0+n1)*4].ravel().ctypes.data_as(ctypes.c_void_p)

        glBufferSubData(
            GL_ARRAY_BUFFER,
            n0p*4*ctypes.sizeof(ctypes.c_float), # because there are 4 vertices per particle
            (n1-n0)*4*_fields_per_vertex*ctypes.sizeof(ctypes.c_float),
            ptr
        )

        # this shit doesn't work everywhere
        # self._data_vbo[n0p*4:n1p*4] = self._data[(s0+n0)*4:(s0+n1)*4].flatten()




    def manageGenerator(self, g):
        if len(self._free_slots)==0:
            snum = self._lru_slots.pop(0)
            g = self._generators[snum]
            g.endManaged()
        else:
            snum = self._free_slots.pop()

        s0 = self._max_particles_per_generator * snum
        s1 = s0 + self._max_particles_per_generator


        g.beginManaged(self, snum, self._data[s0*4:s1*4])

        self._generators[snum] = g

        self._lru_slots.append(snum) # we use a list because we want temporal ordering

        self.refreshBatches()


    def refreshBatches(self):
        self._batches = []
        glist = filter(None, self._generators[:])

        if not glist:
            return

        glist.sort() # sorts by 1)shader, 2)texture

        shader_name = glist[0].getShader().getName()
        new_shader_name = shader_name
        last_texture = None
        shader = None
        used_vaos = set()

        groups = []
        for g in glist:

            shader = g.getShader()

            new_shader_name = shader.getName()

            used_vaos.add(new_shader_name)

            if new_shader_name!= shader_name:
                vao = self.getVAO(shader)
                self._batches.append((shader, groups, vao))
                shader_name = new_shader_name
                groups = []
                last_texture = None

            texture = g.getTextureName()

            do_load_texture = bool(texture != last_texture and texture)

            groups.append( (g, do_load_texture) )

            if texture:
                last_texture = texture

        if groups:
            vao = self.getVAO(shader)
            self._batches.append((shader, groups, vao))




    # get an already existent VAO or create one if there's
    # none assigned to that shader
    def getVAO(self, shader):
        try:
            return self._vao[shader.getName()]
        except:
            vao = self.newVAO(shader)
            self._vao[shader.getName()] = vao
            return vao


    def newVAO(self, shader):
        vao = glGenVertexArray()
        shader.begin()

        glBindVertexArray(vao)

        self._data_vbo.bind()

        stride = _fields_per_vertex*ctypes.sizeof(ctypes.c_float)
        ofs = 0

        for attrname, floats in _attrlist:
            loc = shader.getAttribPos(attrname)

            if loc == -1: continue

            glEnableVertexAttribArray(loc)
            glVertexAttribPointer(loc, floats,  GL_FLOAT, False, stride, ctypes.c_void_p(ofs))

            ofs += ctypes.sizeof(ctypes.c_float) * floats

        self._indices_vbo.bind()

        glBindVertexArray(0)
        shader.end()

        return vao



    @profile
    def update(self, time):
        to_remove = []
        added = False

        self._data_vbo.bind()

        for snum in self._lru_slots:
            g = self._generators[snum]
            keep = g.update(time)

            if keep is False: # the generator is done. Remove it
                g.endManaged()
                self._generators[snum] = None
                to_remove.append(snum)
            elif keep is True: # nothing changed
                pass
            else: # particles added
                self.loadGeneratorData(g, keep[0], keep[1])
                added = True

        if added:
            self._data_vbo.copy_data()

        if to_remove:
            self._lru_slots = [s for s in self._lru_slots if s not in to_remove]
            self._free_slots.update(to_remove)
            self.refreshBatches()



    # delete all VAOs
    def __del__(self):
        try:
            for v in self._vao.values():
                glDeleteVertexArrays(v)
        except:
            pass


    @profile
    def draw(self, scene):

        shader = None
        for shader, groups, vao in self._batches:
            shader.begin()

            scene.uploadMatrices(shader)
            glBindVertexArray(vao)
            #self._indices_vbo.bind()
            for g, bind_texture in groups:
                if bind_texture: g.bindTexture()
                g.draw()

        glBindVertexArray(0)
        if shader: shader.end()
