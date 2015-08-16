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
import libs.transformations as T
from gltools import *
import pygame
import resources as R
from sprites import SpriteManager

from collections import OrderedDict

class Writer:
    def __init__(self, sprite_manager):
        self._sprite_manager = sprite_manager
        self._text_cache = OrderedDict
        self.setAntialias(True)
        self.setFont(10)
        self.setColor(255,255,255)
        self._texts = {}


    def setFont(self, size, face=None):
        w,h = getViewportSize()

        size *= min(w,h)*0.01

        self._current_font = R.getFont(int(size), face)


    def setColor(self, *color):
        self._color=pygame.Color(*color)


    def setAntialias(self, enable=True):
        self._aa = enable


    def changeText(self, txt_id, new_text, pos=None, color=None):
        try:
            txt = self._texts[txt_id]
        except:
            return

        old_text, f, aa, old_color = txt

        surf = f.render(new_text, aa, color or old_color)

        self._sprite_manager.setSpriteGraphics(txt_id, surf)

        if pos is not None:
            self.moveText(txt_id, pos)

        txt[0] = new_text


    def addText(self, pos, text):
        f =  self._current_font
        t = (text,f,self._color,self._aa)

        surf = f.render(text, self._aa, self._color)

        txt_id = self._sprite_manager.newSprite(surf, 1.0, T.translation_matrix((pos[0],pos[1],0)))

        self._texts[txt_id] = [text, f, self._aa, self._color]

        return txt_id


    def moveText(self, txt_id, pos):
        self._sprite_manager.setSpriteTransform(txt_id, T.translation_matrix((pos[0],pos[1],0)))


    def setTextAlpha(self, txt_id, alpha):
        self._sprite_manager.setSpriteAlpha(txt_id, alpha)


    def removeText(self, txt_id):
        try:
            txt = self._texts[txt_id]
        except:
            return


        txt_id = self._sprite_manager.destroySprite(txt_id)

        del self._texts[txt_id]


