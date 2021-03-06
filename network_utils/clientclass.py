import protocol_pb2 as proto
from twisted.internet.protocol import DatagramProtocol
from player.state import state
from player.cvec2 import cvec2 as vec2
from reliable import AckManager
from player.options import Options


class Client(DatagramProtocol):
    """docstring for Client"""
    def __init__(self):
        self.time = 0
        self.connected = False
        self.host = ('nils.cc', 8961)
        # self.host = ('127.0.0.1', 59446)
        self.con_timer = 0
        self.message = proto.Message()
        self.input = proto.Input()
        self.id = None
        self.ackman = AckManager()

        self.listeners = {}

    def start_connection(self):
        # self.transport.connect(*self.host)
        opts = Options()
        self.message.Clear()
        self.message.type = proto.newPlayer
        self.message.input.Clear()
        self.message.input.name = opts['color']
        self.message.input.time = 0
        pl = proto.Player()
        pl.chat = opts['name']
        self.message.player.CopyFrom(pl)
        # self.transport.write(self.message.SerializeToString(), self.host)
        self.ackman.send_rel(self.message, self.host)

    def disconnect(self):
        if self.connected:
            self.message.Clear()
            self.input.Clear()
            self.message.type = proto.disconnect
            self.input.id = self.id
            self.input.time = 0
            self.message.input.CopyFrom(self.input)
            #self.transport.write(self.message.SerializeToString(), self.host)
            self.ackman.send_rel(self.message, self.host)
        self.connected = False
        self.id = None
        self.time = 0

    def get_input(self, event, msg):
        #self.input, dt = msg
        if event == 'input' and self.connected:
            self.input, time = msg
            self.time = time
            self.message = proto.Message()
            self.message.type = proto.playerUpdate
            self.input.time = time
            self.input.id = self.id
            self.message.input.CopyFrom(self.input)
            msg_ = self.message.SerializeToString()
            self.transport.write(msg_, self.host)
        elif event == 'other':
            #only need one message for now, check git for other
            inpt = proto.Input()
            inpt.id = self.input.id
            msg.input.CopyFrom(inpt)
            self.ackman.send_rel(msg, self.host)

    def datagramReceived(self, datagram, address):
        self.message.ParseFromString(datagram)
        if self.message.type == proto.connectResponse and not self.id:
            self.connected = True
            self.id = self.message.player.id
            name = self.message.player.chat
            mapname = self.message.input.name
            gs = self.message.gameState
            self.ackman.respond(self.message, address)
            self.send_message('on_connect', (self.id, mapname, name, gs))
        elif self.message.type == proto.playerUpdate and self.connected:
            ind = self.message.player.id
            state = self.server_to_state(self.message.player)
            time = self.message.player.time
            inpt = self.message.input
            weaponinfo = (self.message.player.ammo, self.message.player.weapon)
            self.send_message('serverdata',
                              (proto.playerUpdate, (ind, time, state, inpt,
                               weaponinfo)))
        elif self.message.type == proto.newPlayer and self.connected:
            ind = self.message.player.id
            name = self.message.player.chat
            gs = self.message.gameState
            colstring = self.message.input.name
            self.ackman.respond(self.message, address)
            if gs == proto.goesSpec:
                self.send_message('serverdata',
                                  (proto.newPlayer, (gs,
                                   (ind, name, colstring))))
            elif gs == proto.wantsJoin:
                state = self.server_to_state(self.message.player)
                time = self.message.player.time
                self.send_message('serverdata',
                                  (proto.newPlayer, (gs, (ind,
                                   name, state, time, colstring))))
        elif self.message.type == proto.disconnect and self.connected:
            ind = self.message.player.id
            self.ackman.respond(self.message, address)
            self.send_message('serverdata', (proto.disconnect, ind))
        elif self.message.type == proto.projectile and self.connected:
            self.send_message('serverdata',
                              (proto.projectile, self.message.projectile))
        elif self.message.type == proto.ackResponse:
            self.ackman.receive_ack(self.message)
        elif self.message.type == proto.stateUpdate:
            ind = self.message.player.id
            stat = self.message.gameState
            gt = self.message.gameTime
            if stat == proto.isDead:
                killer = self.message.projectile.playerId
                weapon = self.message.projectile.type
                ind = (ind, killer, weapon)
            elif stat == proto.spawns:
                pos = vec2(self.message.player.posx, self.message.player.posy)
                ind = (ind, pos)
            elif stat == proto.isReady:
                name = self.message.player.chat
                ind = (ind, name)
            self.ackman.respond(self.message, address)
            self.send_message('serverdata', (proto.stateUpdate,
                              (gt, (stat, ind))))
        elif self.message.type == proto.mapUpdate:
            ind = self.message.player.id
            itemid = self.message.input.id
            gt = self.message.gameTime
            spawn = self.message.input.right
            self.ackman.respond(self.message, address)
            self.send_message('serverdata', (proto.mapUpdate,
                              (ind, itemid, gt, spawn)))
        elif self.message.type == proto.chat:
            self.ackman.respond(self.message, address)
            ind = self.message.player.id
            chat = self.message.player.chat
            self.send_message('serverdata', (proto.chat, (ind, chat)))

    def register(self, listener, events=None):
        self.listeners[listener] = events

    def send_message(self, event, msg=None):
        for listener, events in self.listeners.items():
          #  try:
            listener(event, msg)
        #    except (Exception, ):
         #       self.unregister(listener, msg)

    def unregister(self, listener, msg):
        print '%s deleted, %s' % (listener, msg)
        del self.listeners[listener]

    def server_to_state(self, data):
        pos = vec2(data.posx, data.posy)
        vel = vec2(data.velx, data. vely)
        hp = data.hp
        armor = data.armor
        conds = proto.MState()
        conds.CopyFrom(data.mState)
        return state(pos, vel, hp, armor, conds=conds)

    def register_ack(self):
        self.ackman.receive_send(self.transport.write)

    def update(self, dt):
        self.ackman.update(dt)

    def get_ip(self, d):
        self.host = (d, 8961)


class move(object):
    """docstring for move"""
    def __init__(self, time, input, state):
        super(move, self).__init__()
        self.time = time
        self.input = input
        self.state = state


class moves(list):
    """docstring for moves"""
    def __init__(self, maximum):
        super(moves, self).__init__()
        self.maximum = maximum

    def advance(self, index):
        index[0] += 1
        if index[0] >= self.maximum:
            index[0] -= self.maximum


def correct_client(update_physics, s_move, moves, head, tail, update_state):
    """update_physics is a function which updates physics and has dt, state
    and input as an argument. state is the state sent from server as in
    player.state.state"""
    threshold = 5

    try:
        while s_move.time > moves[head[0]].time and head[0] != tail:
            moves.advance(head)
    except IndexError:
        pass

    if head[0] != tail and s_move.time == moves[head[0]].time:
        if (moves[head[0]].state.pos - s_move.state.pos).mag() > threshold:
            c_time = s_move.time
            c_state = s_move.state.copy()
            c_input = s_move.input

            moves.advance(head)
            index = [head[0]]
            if index[0] == tail:
                update_physics(0, c_state, c_input)
            while index[0] != tail:
                dt = (moves[index[0]].time - c_time) / 1000000.
                c_state = update_physics(dt, c_state, c_input)

                c_time = moves[index[0]].time
                c_input.CopyFrom(moves[index[0]].input)
                moves[index[0]].state = c_state
                moves.advance(index)
        elif moves[head[0]].state.chksm != s_move.state.chksm:
            update_state(s_move.state)
