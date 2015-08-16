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

class Input:
    def __init__(self):
        self._rot = 0
        self._fwd = 0
        self._back = 0
        self._left = 0
        self._right = 0
        self._jump = 0
        self._shoot = 0

        self._actions ={
            pygame.K_LEFT:self._updateLeft,
            pygame.K_a:self._updateLeft,
            pygame.K_RIGHT:self._updateRight,
            pygame.K_d:self._updateRight,
            pygame.K_UP:self._updateFwd,
            pygame.K_w:self._updateFwd,
            pygame.K_DOWN:self._updateBack,
            pygame.K_s:self._updateBack,
            pygame.K_SPACE:self._updateJump,
            pygame.K_RETURN:self._updateShoot,
            pygame.K_KP_ENTER:self._updateShoot
        }

        self._should_quit = False


    def shouldQuit(self):
        return self._should_quit

    def wantJump(self):
        return self._jump

    def wantShoot(self):
        return self._shoot

    def fwdMotion(self):
        return self._fwd - self._back

    def rotMotion(self):
        return self._left - self._right

    def process(self):
        self._jump=0
        self._shoot=0
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.KEYDOWN:
                try:
                    act = self._actions[event.key]
                    act(1)
                except:
                    pass
            elif event.type == pygame.KEYUP:
                try:
                    act = self._actions[event.key]
                    act(0)
                except:
                    pass

            elif event.type == pygame.QUIT:
                self._should_quit = True

    #---------

    def _updateFwd(self, press):
        self._fwd = 1 if press else 0

    def _updateBack(self, press):
        self._back = 1 if press else 0

    def _updateLeft(self, press):
        self._left = 1 if press else 0

    def _updateRight(self, press):
        self._right = 1 if press else 0

    def _updateJump(self, press):
        if press == 1:
            self._jump = 1

    def _updateShoot(self, press):
        if press == 1:
            self._shoot = 1
