from collision.caabb import cAABB as Rectangle, Line
from player.cvec2 import cvec2 as vec2
from network_utils import protocol_pb2 as proto
import math

phext = vec2(16, 54)


def spread(dx, dy, angle, num):
    vec_angle = math.atan2(dy, dx)
    div_angle = float(angle) / num
    a = num // 2
    dys = [dx * math.tan(vec_angle - a * div_angle + i * div_angle)
           for i in range(num)]
    return dys

weaponcolors = {'w0': [255, 255, 255], 'w3': [149, 17, 70],
                'w2': [255, 152, 0], 'w1': [126, 138, 162],
                'w4': [34, 83, 120]}

#values for ammo_boxes. (max_ammo, ammoval)
ammo_values = {'w1': (50, 25), 'w2': (100, 50), 'w3': (25, 10), 'w4': (25, 10)}


class Weapon(Rectangle):
    """BaseWeapon class for other to inherit from"""
    def __init__(self, dmg=1, knockback=0, reload_t=0,
                 ammo=0, max_ammo=100, ammoval=5, respawn=10, ind=None, *args,
                 **kwargs):
        super(Weapon, self).__init__(*args, **kwargs)
        #dmg per hit
        self.dmg = dmg
        self.knockback = knockback
        #time the weapon is active when firing
        self.reload_t = reload_t
        self.ammo = ammo
        self.max_ammo = max_ammo
        self.ammoval = ammoval
        #for reloading
        self.active = False
        self.keystr = ''
        self.respawn = respawn
        #for spawning
        self.inactive = False
        self.ind = ind

    def __eq__(self, other):
        if isinstance(other, Weapon):
            return self.keystr == other.keystr

    def __ne__(self, other):
        if isinstance(other, Weapon):
            return self.keystr != other.keystr

    def on_fire(self, pos, aim_pos):
        pass

    def fire(self, pos, aim_pos):
        if not self.active and self.ammo > 0:
            self.active = self.reload_t
            try:
                self.on_fire(pos, aim_pos)
                self.ammo -= 1
            except TypeError:
                pass
        elif not self.ammo:
            raise NoAmmoError

    def reload(self):
        pass

    def update(self, dt):
        dt = dt * 10**3
        if self.active:
            self.active = self.active - dt
            if self.active < 0:
                self.active = 0

    #pickup weapon
    def apply(self, player):
        if self.keystr not in player.weapons.weapons:
            player.weapons.pickup(self.keystr)
            self.inactive = self.respawn
            return True
        elif player.weapons.weapons[self.keystr].ammo < self.max_ammo:
            player.weapons.weapons[self.keystr].ammo += self.ammoval
            if player.weapons.weapons[self.keystr].ammo > self.max_ammo:
                player.weapons.weapons[self.keystr].ammo = self.max_ammo
            self.inactive = self.respawn
            return True
        return False


class Melee(Weapon):
    """docstring for Melee"""
    def __init__(self, dispatch_proj, id):
        super(Melee, self).__init__()
        self.dmg = 40
        self.knockback = 300
        self.reload_t = 400
        self.dispatch_proj = dispatch_proj
        self.id = id
        self.ammo = 1
        self.vel_ = 0
        self.selfhit = False
        self.proj_lifetime = 1. / 12
        self.reach = 40
        self.keystr = 'w0'

    def on_fire(self, pos, aim_pos):
        self.ammo += 1
        rectoffset = phext
        temp = aim_pos - pos - rectoffset
        direc = temp / temp.mag()
        if temp.mag() <= self.reach:
            offset = direc * temp.mag()
        else:
            offset = direc * self.reach
        npos = pos + rectoffset + offset
        proj = MeleeProjectile(self.dmg, self.knockback, self.id, npos.x,
                               npos.y, width=70, height=70, vel=self.vel_,
                               selfhit=self.selfhit, direc=direc,
                               lifetime=self.proj_lifetime,
                               offset=offset, ppos=pos)
        self.dispatch_proj(proj)


class Blaster(Weapon):
    """docstring for Blaster"""
    def __init__(self, dispatch_proj, id, *args, **kwargs):
        super(Blaster, self).__init__(*args, **kwargs)
        self.dispatch_proj = dispatch_proj
        self.id = id
        self.reload_t = 800
        self.ammo = 10
        self.max_ammo = 15
        self.ammoval = 5
        self.vel_ = 1600
        self.selfhit = True
        self.proj_lifetime = 10
        self.keystr = 'w3'
        self.knockback = 500

    def on_fire(self, pos, aim_pos):
        rectoffset = phext
        temp = aim_pos - pos - rectoffset
        direc = temp / temp.mag()
        proj = BlasterProjectile(x=pos.x+phext.x, y=pos.y+phext.y,
                                 width=10, height=10, vel=self.vel_,
                                 direc=direc, lifetime=self.proj_lifetime,
                                 dmg=110, id=self.id, knockback=self.knockback)
        proj.dispatch_proj = self.dispatch_proj
        self.dispatch_proj(proj)


class LightningGun(Weapon):
    """docstring for LightningGun"""
    def __init__(self, dispatch_proj, id, *args, **kwargs):
        super(LightningGun, self).__init__(*args, **kwargs)
        self.dispatch_proj = dispatch_proj
        self.id = id
        self.reload_t = 50
        self.ammo = 50
        self.max_ammo = 50
        self.ammoval = 25
        self.length = 800
        self.dmg = 8
        self.knockback = 70
        self.keystr = 'w2'

    def on_fire(self, pos, aim_pos):
        dr = aim_pos - pos
        line = HitScanLine(pos.x + phext.x, pos.y + phext.y, dr.x, dr.y,
                           self.length, self.dmg, self.knockback, self.id,
                           proto.lg)
        self.dispatch_proj(line)


class ShotGun(Weapon):
    """docstring for ShotGun"""
    def __init__(self, dispatch_proj, id, *args, **kwargs):
        super(ShotGun, self).__init__(*args, **kwargs)
        self.dispatch_proj = dispatch_proj
        self.id = id
        self.reload_t = 500
        self.ammo = 25
        self.max_ammo = 50
        self.ammoval = 25
        self.pellets = 6
        self.pelletdmg = 4
        self.pelletknockback = 30
        self.pelletlength = 3000
        self.keystr = 'w1'

    def on_fire(self, pos, aim_pos):
        dr = aim_pos - pos - phext
        pellets = ShotGunPellets(pos.x + phext.x, pos.y + phext.y, dr.x, dr.y,
                                 self.pelletdmg, self.pellets,
                                 self.pelletknockback, self.pelletlength,
                                 self.id, proto.sg)
        self.dispatch_proj(pellets)


class GrenadeLauncher(Weapon):
    """docstring for GrenadeLauncher"""
    def __init__(self, dispatch_proj, id, *args, **kwargs):
        super(GrenadeLauncher, self).__init__(*args, **kwargs)
        self.dispatch_proj = dispatch_proj
        self.id = id
        self.reload_t = 600
        self.ammo = 10
        self.max_ammo = 15
        self.ammoval = 5
        self.vel_ = 900
        self.knockback = 700
        self.proj_lifetime = 2.5
        self.keystr = 'w4'

    def on_fire(self, pos, aim_pos):
        pos += phext
        dr = aim_pos - pos
        drunit = dr / dr.mag() + vec2(0, 0.3)
        #drunit = drunit / drunit.mag()
        proj = NadeProjectile(x=pos.x, y=pos.y, width=15, height=10,
                              vel=self.vel_, direc=drunit,
                              lifetime=self.proj_lifetime, dmg=120, id=self.id,
                              knockback=self.knockback)
        #proj.vel.y += 500
        proj.dispatch_proj = self.dispatch_proj
        self.dispatch_proj(proj)


class NoAmmoError(Exception):
    def __init__(self):
        pass


class ProjContainer(list):
    """docstring for ProjContainer"""
    def __init__(self, time, ind):
        super(ProjContainer, self).__init__()
        self.time = time
        self.ind = ind


class Projectile(Rectangle):
    """docstring for Projectile"""
    #x and y are center positions for convenience
    def __init__(self, dmg=10, knockback=10, id=0, x=0, y=0, width=100,
                 height=100, vel=10, selfhit=False, direc=vec2(10, 0),
                 lifetime=0.1, offset=None, ppos=None):
        super(Projectile, self).__init__(x - width / 2, y - height / 2,
                                         width, height)
        self.dmg = dmg
        self.knockback = knockback
        #playerid for collision
        self.id = id
        #vel is float
        self.direc = direc
        self.vel = direc * vel
        self.selfhit = selfhit
        self.lifetime = lifetime
        self.type = None
        self.offset = offset
        self.ppos = ppos
        self.canthurt = 0.5

    def on_hit(self, player=None, norm=0):
        pass

    def on_runout(self):
        return True

    def updateproj(self, dt, mapgen, playergen):
        self.lifetime -= dt
        if self.canthurt:
            self.canthurt -= dt
            if self.canthurt <= 0:
                self.canthurt = False
        return self.collide(dt, mapgen, playergen)

    def collide(self, dt, mapgen, playergen):
        norm = False
        all_collisions = ((self.sweep(obj.rect, dt), obj.id)
                          for obj in playergen)
        collisions = [coldata for coldata in all_collisions if coldata[0]]
        id = False
        try:
            xt = min(col[0][1] for col in collisions if col[0][0].x != 0)
            norm, id = [(col[0][0], col[1]) for col in collisions if
                        col[0][1] == xt and col[0][0].x != 0][0]
        except (TypeError, ValueError):
            xt = dt
        try:
            yt = min(col[0][1] for col in collisions if col[0][0].y != 0)
            if yt < xt:
                norm, id = [(col[0][0], col[1]) for col in collisions if
                            col[0][1] == yt and col[0][0].y != 0][0]
        except (TypeError, ValueError):
            yt = dt
        dt_ = vec2(xt, yt)
        if not id:
            #mapcollisions
            all_collisions = (self.sweep(obj, dt) for obj in mapgen)
            collisions = [coldata for coldata in all_collisions if coldata]
            try:
                xt = min(col[1] for col in collisions if col[0].x != 0)
                norm = [col[0] for col in collisions
                        if col[1] == xt and col[0].x != 0][0]
            except (TypeError, ValueError):
                xt = dt
            try:
                yt = min(col[1] for col in collisions if col[0].y != 0)
                norm = [col[0] for col in collisions
                        if col[1] == yt and col[0].y != 0][0]
            except (TypeError, ValueError):
                yt = dt
            dt_ = vec2(xt, yt)
            if (dt_.x < dt or dt_.y < dt):
                id = -1
        return self.resolve_sweep(dt_, id, norm)

    def resolve_sweep(self, dt, id, norm):
        pos = self.pos + self.vel * dt
        self.update(*pos)
        if not id:
            return False
        elif id == self.id and self.canthurt:
            return False
        else:
            return id, norm

    def pass_pos(self, pos, vel):
        self.vel, self.pos = vel, pos


class MeleeProjectile(Projectile):
    """docstring for MeleeProjectile"""
    def __init__(self, *args, **kwargs):
        super(MeleeProjectile, self).__init__(*args, **kwargs)
        self.type = proto.melee
        self.rectoffset = vec2(phext.x-self.width / 2, phext.y-self.height / 2)
        self.vel = vec2(0, 0)
        self.ids = [self.id]

    def on_hit(self, players=None, norm=0):
        for player in players:
            if player.id not in self.ids:
                self.damage_player(player, self)
                player.state.vel += self.direc * self.knockback
                self.ids.append(player.id)
        return False

    def collide(self, dt, mapgen, playergen):
        return [plr for plr in playergen if self.overlaps(plr.rect)], 0

    def updateproj(self, dt, mapgen, playergen):
        self.update(*(vec2(*self.ppos) + self.offset + self.rectoffset))
        self.lifetime -= dt
        return self.collide(dt, mapgen, playergen)

    def resolve_sweep(self, dt, id):
        if not id:
            return False
        else:
            return id


class BlasterProjectile(Projectile):
    """docstring for BlasterProjectile"""
    def __init__(self, *args, **kwargs):
        super(BlasterProjectile, self).__init__(*args, **kwargs)
        self.type = proto.blaster

    def on_hit(self, player=None, norm=0):
        posx = self.center.x
        posy = self.center.y
        hwidth = 125
        proj = BlasterExplosion(dmg=100, knockback=400, id=self.id,
                                x=posx, y=posy,
                                width=hwidth*2,
                                height=hwidth*2, vel=0, direc=vec2(0, 0),
                                lifetime=0.05)
        if player:
            #direc should already be normalized for blasterproj
            player.state.vel += self.direc * self.knockback
            self.damage_player(player, self)
            proj.players.append(player)
        self.dispatch_proj(proj)
        #direct dmg
        return True


class NadeProjectile(Projectile):
    """docstring for NadeProjectile"""
    def __init__(self, *args, **kwargs):
        super(NadeProjectile, self).__init__(*args, **kwargs)
        self.type = proto.gl
        self.canthurt = 0.25

    def on_hit(self, player, norm):
        if player:
            posx = self.center.x
            posy = self.center.y
            hwidth = 125
            proj = BlasterExplosion(dmg=110, knockback=700, id=self.id, x=posx,
                                    y=posy, width=hwidth*2, height=hwidth*2,
                                    vel=0, direc=vec2(0, 0), lifetime=0.05)
            proj.type = proto.explNade
            player.state.vel += self.direc * self.knockback
            self.damage_player(player, self)
            proj.players.append(player)
            self.dispatch_proj(proj)
            return True
        else:
            if norm.x:
                self.vel.x *= -0.6
            else:
                self.vel.x *= 0.9
                self.vel.y *= -0.6
            return False

    def on_runout(self):
        posx = self.center.x
        posy = self.center.y
        hwidth = 125
        proj = BlasterExplosion(dmg=110, knockback=700, id=self.id, x=posx,
                                y=posy, width=hwidth*2, height=hwidth*2, vel=0,
                                direc=vec2(0, 0), lifetime=0.05)
        proj.type = proto.explNade
        self.dispatch_proj(proj)
        return True

    def resolve_sweep(self, dt, id, norm):
        if not id == -1:
            self.vel -= vec2(0, 1500) * dt
        pos = self.pos + self.vel * dt
        self.update(*pos)
        if not id:
            return False
        elif id == self.id and self.canthurt:
            return False
        else:
            return id, norm


class Explosion(Projectile):
    """docstring for Explosion"""
    def __init__(self, *args, **kwargs):
        super(Explosion, self).__init__(*args, **kwargs)
        self.players = []
        self.orig_dmg = self.dmg

    def collide(self, dt, mapgen, playergen):
        return [plr for plr in playergen if self.overlaps(plr.rect)], 0

    def on_hit(self, players, norm=0):
        for player in players:
            if player not in self.players:
                direc = self.center - player.rect.center
                mag = direc.mag()
                hw = self.width * 0.5
                dmg = int((hw - mag) / hw * self.dmg)
                if dmg < 10:
                    dmg = 10
                self.dmg = dmg
                player.state.vel -= direc / mag * self.knockback
                self.damage_player(player, self)
                self.dmg = self.orig_dmg
            self.players.append(player)
        return False


class BlasterExplosion(Explosion):
    """docstring for BlasterExplosion"""
    def __init__(self, *args, **kwargs):
        super(BlasterExplosion, self).__init__(*args, **kwargs)
        self.type = proto.explBlaster


class HitScanLine(Line):
    """docstring for HitScanLine"""
    def __init__(self, x, y, dx, dy, length, dmg, knockback, id, typ):
        super(HitScanLine, self).__init__(x, y, dx - phext.x, dy - phext.y,
                                          length)
        self.dmg = dmg
        self.knockback = knockback
        self.id = id
        self.type = typ

    def on_hit(self, dmg_func, player):
        dmg_func(player, self)
        player.state.vel += self.unit * self.knockback


class ShotGunPellets(object):
    """docstring for ShotGunPellets"""
    def __init__(self, x, y, dx, dy, pdmg, pnum, pkb, plength, id, typ):
        super(ShotGunPellets, self).__init__()
        self.pdmg = pdmg
        self.pnum = pnum
        self.pkb = pkb
        self.plength = plength
        self.id = id
        self.type = typ
        spread_dy = spread(dx, dy, angle=0.1, num=pnum)
        self.pellets = [HitScanLine(x, y, dx, spread_dy[i], plength, pdmg, pkb,
                        id, 0) for i in range(pnum)]
        self.dir = vec2(dx, dy)
        self.unit = self.dir.normalize()

    def collide(self, quadtree, playergen, id):
        colls = [line.collide(quadtree, playergen(), id)
                 for line in self.pellets]
        colls = [coll for coll in colls if coll is not False]
        playerids = [coll[1] for coll in colls if coll[1] is not False]
        if len(playerids) == 0:
            return False
        dct = {}
        for id in set(playerids):
            count = 0
            for ind in playerids:
                if ind == id:
                    count += 1
            dct[id] = count
        return dct

    def on_hit(self, dmg_func, players):
        for player in players:
            self.dmg = self.pdmg * player.hitcount
            dmg_func(player, self)
            player.state.vel += self.unit * self.pkb * player.hitcount


class ProjectileManager(object):
    """docstring for ProjectileManager"""
    def __init__(self, players, _map, dmg_func, allgen):
        super(ProjectileManager, self).__init__()
        self.projs = []
        self.todelete = []
        self.send_ = None
        self.proj_num = 0
        self.message = proto.Message()
        self.message.type = proto.projectile
        #for collisions
        self.players = players
        self.map = _map
        self.allgen = allgen
        self.damage_player = dmg_func

    def __iter__(self):
        return iter(self.projs)

    def __getitem__(self, key):
        return self.projs[key]

    def __len__(self):
        return len(self.projs)

    def update(self, dt):
        for proj in self.projs:
            mapgen = (rect for rect in self.map.quad_tree.retrieve([], proj))
            playergen = (player for player in self.players.itervalues())
            coll = proj.updateproj(dt, mapgen, playergen)
            if coll:
                coll, norm = coll
                try:
                    player = self.players[coll]
                except KeyError:
                    player = False
                except TypeError:
                    #in case of explosions coll: list of players in expl radius
                    player = coll
                self.resolve_collision(proj, player, norm)
            if proj.lifetime < 0:
                if proj.on_runout():
                    self.todelete.append(proj)
        #loop over copy of list to make deletion possible
        self.del_projectiles()
        self.send_all()

    def resolve_collision(self, proj, player, norm):
        #self.todelete.append(proj)
        if proj.on_hit(player, norm):
            self.todelete.append(proj)

    def del_projectiles(self):
        for proj in set(self.todelete):
            self.projs.remove(proj)
            self.send(proj, toDelete=True)
            while proj in self.todelete:
                self.todelete.remove(proj)

    def add_projectile(self, proj):
        self.proj_num += 1
        proj.projId = self.proj_num
        if isinstance(proj, Projectile):
            proj.damage_player = self.damage_player
            proj.playerId = proj.id
            self.projs.append(proj)
        elif isinstance(proj, HitScanLine):
            self.process_hitscan(proj)
        elif isinstance(proj, ShotGunPellets):
            self.process_hitscan_mul(proj)
            #knockback
            cond = self.players[proj.id].state.conds
            if cond.ascending or cond.descending:
                self.players[proj.id].state.vel -= proj.unit * vec2(150, 300)

    def send(self, proj, toDelete=False):
        projectile = proto.Projectile()
        projectile.projId = proj.projId
        projectile.playerId = proj.id
        projectile.type = proj.type
        projectile.posx, projectile.posy = proj.pos.x, proj.pos.y
        projectile.velx, projectile.vely = proj.vel.x, proj.vel.y
        projectile.toDelete = toDelete
        self.message.projectile.CopyFrom(projectile)
        for player in self.allgen():
            self.send_(self.message.SerializeToString(), player.address)

    def send_all(self):
        for proj in self.projs:
            self.send(proj)

    def receive_send(self, func):
        self.send_ = func

    def process_hitscan(self, line):
        playergen = (player for player in self.players.itervalues())
        coll = line.collide(self.map.quad_tree, playergen, line.id)
        if not coll:
            length, pl = line.length, False
        else:
            length, pl = coll
        #TODO: hitting players
        if pl:
            line.on_hit(self.damage_player, self.players[pl])
        proj = proto.Projectile()
        proj.type = line.type
        proj.playerId = line.id
        proj.projId = line.projId
        #posx: length, posy: isplayerhit
        proj.posx = length
        proj.posy = pl
        self.message.projectile.CopyFrom(proj)
        for player in self.allgen():
            self.send_(self.message.SerializeToString(), player.address)

    def process_hitscan_mul(self, pellets):
        def pgen():
            return (player for player in self.players.itervalues())
        coldict = pellets.collide(self.map.quad_tree, pgen, pellets.id)
        if not coldict:
            pl = False
        else:
            players = []
            pl = True
            for id, count in coldict.iteritems():
                self.players[id].hitcount = count
                players.append(self.players[id])
            pellets.on_hit(self.damage_player, players)
        proj = proto.Projectile()
        proj.type = pellets.type
        proj.playerId = pellets.id
        proj.projId = pellets.projId
        proj.posy = pl
        self.message.projectile.CopyFrom(proj)
        for player in self.allgen():
            self.send_(self.message.SerializeToString(), player.address)


class WeaponsManager(object):
    """docstring for WeaponsManager"""
    def __init__(self, dispatch_proj, id):
        super(WeaponsManager, self).__init__()
        self.dispatch_proj = dispatch_proj
        self.id = id
        #start only with melee
        self.starting_weapons = ('w0', 'w1')
        self.weapons = {}
        for k in self.starting_weapons:
            self.weapons[k] = allweapons[k](self.dispatch_proj, self.id)
        self.current_w = self.weapons['w1']
        self.current_s = allstrings['w1']
        self.wli = 0
        self.hudhook = None
        self.switch_time = 0.5

    def fire(self, pos, aim_pos):
        try:
            self.current_w.fire(pos, aim_pos)
        except NoAmmoError:
            if self.hudhook:
                self.hudhook(text='no ammo')

    def update(self, dt, state, input):
        if state.isDead or state.frozen:
            return 0
        if input.att:
            self.fire(state.pos, vec2(input.mx, input.my))
        if input.switch != proto.no_switch:
            self.switch_to('w' + str(input.switch-1))
        self.current_w.update(dt)

    def switch_to(self, key):
        try:
            if self.current_w != self.weapons[key]:
                active = self.current_w.active + self.switch_time
                self.current_w = self.weapons[key]
                self.current_w.active = active
                self.current_s = allstrings[key]
                if self.hudhook:
                    self.hudhook(weapon=self.current_s,
                                 ammo=(str(self.current_w.ammo), self.weapons))
        except KeyError:
            pass

    def hook_hud(self, hudhook):
        self.hudhook = hudhook
        self.hudhook(ammo=(str(self.current_w.ammo), self.weapons),
                     weapon=self.current_s)

    def unhook(self):
        if self.hudhook:
            self.hudhook = None

    def reset(self):
        self.weapons = {}
        for k in self.starting_weapons:
            self.weapons[k] = allweapons[k](self.dispatch_proj, self.id)
        self.current_w = self.weapons['w1']
        self.current_s = allstrings['w1']
        self.current_w.active = 300
        if self.hudhook:
                self.hudhook(weapon=self.current_s)

    def pickup(self, keystr):
        if keystr in allweapons:
            self.weapons[keystr] = allweapons[keystr](self.dispatch_proj,
                                                      self.id)

    def apply(self, keystr, player):
        self.weapons[keystr].apply(player)
        if self.weapons[keystr] == self.current_w:
            self.hudhook(ammo=(str(self.current_w.ammo), self.weapons))

    def pack_ammo_weapon(self):
        key = self.current_w.keystr
        return self.current_w.ammo, int(key[-1]) + 1

    def from_server(self, weapinfo):
        ammo, weap = weapinfo
        key = 'w' + str(weap - 1)
        try:
            if self.current_w.keystr == key:
                self.current_w.ammo = ammo
                self.hudhook(ammo=(str(self.current_w.ammo), self.weapons))
        except KeyError:
            pass

    def predict_ammo(self, keystr):
        maxammo, ammoval = ammo_values[keystr]
        self.weapons[keystr].ammo += ammoval
        if self.weapons[keystr].ammo > maxammo:
            self.weapons[keystr].ammo = maxammo

allweapons = {'w0': Melee, 'w3': Blaster, 'w2': LightningGun,
              'w1': ShotGun, 'w4': GrenadeLauncher}

allstrings = {'w0': 'melee', 'w3': 'blaster',
              'w2': 'lightning gun', 'w1': 'shotgun', 'w4': 'grenades'}
