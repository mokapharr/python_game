import math
from state import vec2


class Movement(object):
    """docstring for Movement"""
    def __init__(self, x, y):
        super(Movement, self).__init__()
        self.pos = vec2(x, y)
        self.vel = vec2(0, 0)
        self.gravity = 2500.
        self.normal_accel = 500.
        self.boost_accel = 20.
        self.turn_multplier = 4.
        self.jump_vel = 900.
        self.max_vel = 500
        self.angle = 0

    def update(self, dt, state, input):
        pos, vel, conds = state.pos, state.vel, state.conds
        self.calc_vel(dt, pos, vel, input, conds, state)
        self.step(dt, pos, vel)
        return self.vel, self.pos

    def step(self, dt, pos, vel):
        self.vel[1] = vel[1] - self.gravity * dt
        for i, j in enumerate(self.pos):
            self.pos[i] = pos[i] + self.vel[i] * dt

    def calc_vel(self, dt, pos, vel, input, conds, state):
        avel = abs(vel.x)
        if input.right and not input.left:
            sign = 1
        elif input.left and not input.right:
            sign = -1
        else:
            self.vel.x = 0
            sign = 0
        self.curr_sign = self.sign_of(vel.x)
        if not avel > self.max_vel:
            v = self.normal_accel
        else:
            v = 0
        if conds.onGround and self.curr_sign * sign > 0:
            v *= self.turn_multplier
        if avel + v * dt > self.max_vel or (conds.onGround
                                            and avel > self.max_vel):
            self.vel.x = self.max_vel * self.curr_sign
        self.vel.x = vel.x + v * sign * dt

        if (conds.landing or conds.onGround) and conds.canJump:
            self.vel.y = self.jump_vel
            state.set_cond('ascending')
        if not input.up:
            state.set_cond('canJump')
            if self.vel.y > 0:
                self.vel.y = 0

    def sign_of(self, num):
        if num > 0:
            return 1
        elif num < 0:
            return -1
        else:
            return 0

    def resolve_coll(self, pos, vel):
        self.pos, self.vel = pos, vel
