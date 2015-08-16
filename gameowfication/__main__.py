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
import time
from input import Input
from mainscene import MainScene
from gltools import *
#from OpenGL.GL import *
import resources as R
from map import Map

import profiler as prof

def main():
    pygame.init()
    pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 16)
    screen = pygame.display.set_mode((800,600), pygame.OPENGL|pygame.DOUBLEBUF)

    inp = Input()


    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LEQUAL)
    glDisable(GL_CULL_FACE)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    glViewport(0,0,800,600)


    print 'Window: Actual color bits r%d g%d b%d a%d'%(
        pygame.display.gl_get_attribute(pygame.GL_RED_SIZE),
        pygame.display.gl_get_attribute(pygame.GL_GREEN_SIZE),
        pygame.display.gl_get_attribute(pygame.GL_BLUE_SIZE),
        pygame.display.gl_get_attribute(pygame.GL_ALPHA_SIZE))
    print 'Window: Actual depth bits: %d'%(
        pygame.display.gl_get_attribute(pygame.GL_DEPTH_SIZE),)
    print 'Window: Actual stencil bits: %d'%(
        pygame.display.gl_get_attribute(pygame.GL_STENCIL_SIZE),)
    print 'Window: Actual multisampling samples: %d'%(
        pygame.display.gl_get_attribute(pygame.GL_MULTISAMPLESAMPLES),)


    print "Running..."
    frame = 0
    old_t = 0

    scene = MainScene()
    try:

        scene.init()

        max_fps = 65.0

        frame_ticks = 1000.0 / max_fps

        while True:
            glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)

            t = pygame.time.get_ticks()

            inp.process()

            if (inp.shouldQuit()): break

            scene.advance(screen, t, inp)

            #t0 = pygame.time.get_ticks()
            pygame.display.flip()
            #t1 = pygame.time.get_ticks()

            dt = pygame.time.get_ticks() - t

            pygame.time.delay(max(0,int(frame_ticks - dt))) # be nice and yield some time
            #------


            if 0:
                frame += 1
                if (t - old_t > 1000.0):
                    dt = t - old_t
                    #load = 1.0 - float(t1-t0) / dt

                    #print "%s FPS, LOAD: %s%%"%(1000.0*(float(frame) / dt), int(load*100) )
                    print "%s FPS"%(1000.0*(float(frame) / dt))
                    prof.printTotals(frame)
                    frame = 0
                    old_t = t
    finally:
        scene.destroy()





