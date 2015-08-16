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


from scene import Scene
from map import Map
from player import Player
from camera import Camera
from particles import *
from base import Base
from targetpoint import TargetPoint
from routing import *
from enemy import Enemy
from text import Writer
from sprites import SpriteManager


class MainScene(Scene):

    def __init__(self):
        Scene.__init__(self)


    def init(self):
        Scene.init(self)
        self._game_over = False
        self._router = None
        self._total_tp = 0
        self._total_tp_reached = 0
        self._data_collected = 0
        self._data_leaked = 0
        self._total_kills = 0
        self._score = 0
        self._show_once = set()
        self._time = 0

        self._alerts = SortedList()

        self._current_alert = 1

        self._bases = []
        self._target_points= set()
        self._projectiles = set()
        self._enemies = set()

        self._vpw, self._vph = getViewportSize()

        self._sprites = SpriteManager()
        self._text_writer = Writer(self._sprites)


        self._map = Map("map2")

        pos = self._map.getPlayerInitialPosition()

        self._player = Player(self._map, pos + (0,0,1))

        self._camera = Camera(self._player, self._map)

        self._particles = ParticleController()

        self._router = RouterBatchProcessor(Router(self._map, pos, 65))

        self.placeInitialLocations()

        self._time_z = 0

        self._new_spawn  = float("Inf")

        self._lock_sprite = self._sprites.newSprite("lock.png",alpha=1.0,centered=True)
        self._sprites.setSpriteAlpha(self._lock_sprite,0)


        self._texts = {
            "collected":[-1,(20,20),lambda:"Data collected: %s%%"%int(100*self._data_collected)],
            "leaked":[-1,(20,50),lambda:"Data leaked: %s%%"%int(100*(self._data_leaked / self._data_collected) if self._total_tp_reached else 0)],
            "kills":[-1,(500,50),lambda:"Kills: %s"%self._total_kills],
            "score":[-1,(500,20),lambda:"SCORE %s"%self._score]
        }

        for i in xrange(10):
            # expiry time, location, writer_id
            self._alerts.append((float("Inf"),0,0))

        self.updateText(*self._texts.keys())


        #pygame.image.save(self._sprites._textures[0]._surface,"tiles.png")




        self.addAlert(self._time+8000, "*Use the arrow keys to move around\n<ENTER> for shooting and <SPACE> for jumping", color=(0,255,0), once="keys")


    def updateText(self, *which):
        for w in which:
            v = self._texts[w]
            id,pos,fn = v
            if id == -1:
                self._text_writer.setFont(10)
                self._text_writer.setColor(255,255,255,200)
                id = self._text_writer.addText(pos,fn())
                v[0] = id
            else:
                self._text_writer.changeText(id, fn())


    def getAlertPos(self, i):
        return (20, i*17+90)


    def addAlert(self, keep_until, text, color=(255,255,255), once=None):

        if once is not None:
            if once in self._show_once:
                return

            self._show_once.add(once)

        if "\n" in text:
            for line in text.split("\n"):
                self.addAlert(keep_until, line, color)
            return

        if self._alerts[0][0]>0: # take an empty slot
            p = self._alerts.pop(-1)
        else: # or an alert which is closest to disappear
            p = self._alerts.pop(0)

        id = p[2]
        if id == 0:
            self._text_writer.setFont(6)
            self._text_writer.setColor(*color)
            id = self._text_writer.addText((0,0),text)
        else:
            self._text_writer.changeText(id,text,pos=(0,0), color=color)

        self._alerts.add((keep_until,self._current_alert,id)) # insert the text
        self._current_alert += 1

        self.reorderAlerts()


    def reorderAlerts(self):
        # now, reorganize the list, sorted by alert number
        i = 0
        for l in sorted(self._alerts, key=lambda a:a[1]): # sort by location
            expiry, slot, writer = l
            if expiry == 0 or writer==0: # not active
                continue
            self._text_writer.moveText(writer, self.getAlertPos(i))
            i+=1


    def updateAlerts(self, time):
        changed = False
        while True:
            expiry, slot, writer = self._alerts[0]
            if expiry == 0 or expiry > time:
                break
            p = self._alerts.pop(0)
            self._text_writer.setTextAlpha(p[2],0.0)
            self._alerts.add((float("Inf"),1000,p[2]))
            changed = True

        if changed:
            self.reorderAlerts()



    def gameOver(self):
        self._game_over = True
        c = T.translation_matrix((self._vpw/2, self._vph/2,-0.1))
        self._game_over_sprite = self._sprites.newSprite("gameover.png",centered=True, xform=c)

    def gameWin(self):
        self._game_over = True
        c = T.translation_matrix((self._vpw/2, self._vph/2,-0.1))
        self._game_over_sprite = self._sprites.newSprite("finished.png",centered=True, xform=c)


    def getMap(self):
        return self._map


    def getParticleManager(self):
        return self._particles


    def placeInitialLocations(self):
        self._total_tp = 0

        for pos in self._map.getResourcePositions("base"):
            self.placeBase(pos)

        for pos in self._map.getResourcePositions("target_point"):
            self.placeTargetPoints(pos)

        for pos in self._map.getResourcePositions("enemy_base"):
            self.placeEnemyBase(pos)


    def placeTargetPoints(self, pos):
        self._total_tp += 1
        self._total_tp_reached = 0
        self._target_points.add(TargetPoint(self, pos+(0,0,1)))




    def placeBase(self, pos):


        pg = ParticleGenerator("billboard","particle5.png")
        pg.setEasing(0.2,0.2,0.0,0.5,2.0)
        pg.setBrightness(0.5)
        pg.setMode("LOOP")
        pg.setPosition(pos + (0,0,3))
        self._particles.manageGenerator(pg)


        #pg = ParticleGenerator("billboard","particle2.png")
        #pg.setMode("LOOP")
        #pg.setPosition(pos)
        #self._particles.manageGenerator(pg)

        self._bases.append(Base(pos, pg))




    def placeEnemyBase(self, pos):
        pass



    def newEnemy(self):
        pos = random.choice(self._map.getResourcePositions("enemy_source"))
        tgt = random.choice(self._bases).getPosition()
        m = Enemy(self, pos, tgt, self._router)
        self._enemies.add(m)


    def enemyReachedBase(self, e):
        if e.closing():
            return
        e.close()
        self._data_leaked += (self._data_collected-self._data_leaked) *random.random()*0.2
        self.updateText("leaked")


        self.addAlert(self._time+3000, "*Enemies are stealing your data!", color=(255,128,0))
        self.addAlert(self._time+8000, "*If 50% of your collected data gets leeched, you lose", color=(0,255,0), once="lose")
        if self._data_leaked >0  and (self._data_leaked > self._data_collected * 0.5):
            if not self._game_over:
                self.gameOver()


        #pygame.image.save(self._sprites._textures[0]._surface,"tiles.png")


    def reachedTargetPoint(self, tp):
        if tp.closing():
            return
        tp.close()
        self._total_tp_reached += 1
        self._data_collected = float(self._total_tp_reached)/self._total_tp
        self._score += 500
        self.updateText("collected","score","leaked")
        self.addAlert(self._time+8000, "*Follow all the beacons to collect the data", color=(0,255,0), once="beacons")
        #pygame.image.save(self._sprites._textures[0]._surface,"tiles.png")

        if self._total_tp_reached == self._total_tp:
            self.gameWin()

        # first leecher is spawned after data is collected
        if self._total_tp_reached == 1:
            self._new_spawn = self._time + 5000


    def updateEntities(self, time, *entity_list):
        for el in entity_list:
            p = []
            for e in el:
                r = e.update(time)
                if not r:
                    p.append(e)
            el.difference_update(p)



    def advance(self, screen, time, inp):
        if self._time_z == 0:
            self._time_z = time
            return

        time -= self._time_z  # relative time to the beginning of the game

        self._time = time

        self._modelview_m = self._camera.getMatrix()

        self.freezeLight()

        #self._modelview_m = lookAtMtx(N.array((300,300,300),dtype="f"),N.array(self._player.getPosition(),dtype="f"), (0,0,1))

        # pre-render update -------

        self._player.update(time)

        self._camera.update(time)

        self._particles.update(time)

        for e in self._bases: e.update(time)

        self.updateEntities(time,
                self._target_points,
                self._projectiles,
                self._enemies
            )

        # check collisions -------

        #for e in self._projectiles:
        #    collisions = e.getCollisions()
        #    for c in collisions:
        #        if c in self._enemies:
        #            c.destroy()
        #            e.explode()



        for e in self._enemies:
            if e.targetReached():
                self.enemyReachedBase(e)
            else:
                self._player.checkLock(e)
                for p in self._projectiles:
                    if p.collidesWith(e):
                        self._total_kills += 1
                        p.explode()
                        e.explode()
                        self._score += 100
                        self.updateText("kills", "score")



        if not self._game_over:
            p = self._player
            nearby = p.getCloseEntities()
            for n in nearby:
                if isinstance(n,TargetPoint):
                    if p.collidesWith(n):
                        self.reachedTargetPoint(n)

        #  draw -------

        self._map.draw(self)
        self._player.draw(self)

        for e in self._bases: e.draw(self)
        for e in self._target_points: e.draw(self)
        for e in self._projectiles: e.draw(self)
        for e in self._enemies: e.draw(self)


        glDepthMask(False)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glEnable(GL_BLEND)

        self._particles.draw(self) # very last thing to draw
        for e in self._target_points: e.drawBeacon(self)

        glDisable(GL_BLEND)
        glDepthMask(True)

        # UI ------
        self.updateAlerts(time)

        locking = False
        if not self._game_over:
            lock_pos = self._player.getLockPosition()
            if lock_pos is not None:
                proj = mmult(self._perspective_m, self._modelview_m, N.array((lock_pos[0], lock_pos[1], lock_pos[2], 1), dtype = "f"))

                if proj[3] > 0:
                    px = ((proj[0] / proj[3]) +1.0)* self._vpw*0.5
                    py = (1.0 - (proj[1] / proj[3]))* self._vph*0.5
                    if px > 0 and px < self._vpw and py >0 and py < self._vph:
                        self._sprites.setSpriteTransform(self._lock_sprite, T.translation_matrix((px,py,0)))
                        self._sprites.setSpriteAlpha(self._lock_sprite, 0.5)
                        locking = True
        if not locking:
            self._sprites.setSpriteAlpha(self._lock_sprite, 0.0)

        self.resetModelview()
        self.setOrthoMode()

        self._sprites.draw(self)

        self.setPerspectiveMode()
        # process input ------

        if not self._game_over:

            if (inp.wantJump()):
                self._player.jump()

            if (inp.wantShoot()):
                m = self._player.getMissile(self)
                self._projectiles.add(m)

            self._player.advance(inp.fwdMotion()*0.00001)
            self._player.alterHeading(inp.rotMotion()*0.01)

        # misc world advance ------

        self._router.dispatch()

        if time > self._new_spawn:
            self.newEnemy()
            self.addAlert(time+3000,"*New leecher approaching",(200,200,0))

            self._new_spawn = time+ random.randint(20000,50000)


    def destroy(self):
        if self._router:
            self._router.finish()
        self._router = None


    def __del__(self):
        try:
            # in case "destroy" wasn't called.
            # do this at least
            if self._router:
                self._router.finish()
            self._router = None
        except:
            pass
