from movement import Movement
from graphics.primitives import Rect
from collision.rectangle import Rectangle
from network_utils import protocol_pb2 as proto
from state import vec2, state
from menu.menu_events import Events
from gameplay.weapons import WeaponsManager


class Player(Events):
    """docstring for player"""
    def __init__(self, server=False, dispatch_proj=None, id=False):
        super(Player, self).__init__()
        self.state = state(vec2(50, 50), vec2(0, 0), 100)
        self.move = Movement(*self.state.pos)
        self.dispatch_proj = dispatch_proj
     # spawning player at 0,0, width 32 = 1280 / 40. and height 72 = 720/10.
        if not server:
            self.Rect = Rect
        else:
            self.Rect = Rectangle
        if id:
            self.id = id
            self.weapons = WeaponsManager(self.dispatch_proj, self.id)
        self.rect = self.Rect(0, 0, 32, 72, (0, .8, 1.))
        #input will be assigned by windowmanager class
        self.input = proto.Input()
        self.listeners = {}

    def update(self, dt, state=False, input=False):
        if not state:
            state = self.state
        if not input:
            input = self.input
        self.state.vel, self.state.pos = self.move.update(dt, state, input)
        self.rect.update(*self.state.pos)
        self.weapons.update(dt, self.state, self.input)
        self.state.update(dt)

    def client_update(self, s_state):
        easing = .8
        snapping_distance = 20

        diff = vec2(s_state.pos.x - self.state.pos[0],
                    s_state.pos.y - self.state.pos[1])
        len_diff = diff.mag()

        if len_diff > snapping_distance:
            self.state.pos = s_state.pos
        elif len_diff > .1:
            self.state.pos += diff * easing
        self.state.vel = s_state.vel
        self.rect.update(*self.state.pos)

    def draw(self):
        self.rect.draw()

    def resolve_collision(self, ovrlap, axis, angle):
        self.state.pos[0] = self.rect.x1 - ovrlap * axis[0]
        self.state.pos[1] = self.rect.y1 - ovrlap * axis[1]
        self.state.vel[0] *= axis[1] > 0
        self.state.vel[1] *= axis[0] > 0
        self.rect.update(*self.state.pos)
        self.move.resolve_coll(self.state.pos, self.state.vel)
        if axis[1] > 0 and ovrlap < 0:
            #self.move.conds['on_ground'] = True
            self.state.set_cond('onGround')
            #self.move.angle = angle
        elif axis[0] > 0:
            if ovrlap > 0:
                self.state.set_cond('onRightWall')
            elif ovrlap < 0:
                self.state.set_cond('onLeftWall')

    def spawn(self, x, y):
        self.state.pos = vec2(x, y)
        self.state.vel = vec2(0, 0)

    def get_id(self, id):
        self.id = id
        self.weapons = WeaponsManager(self.dispatch_proj, self.id)
