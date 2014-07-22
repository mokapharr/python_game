from twisted.internet.protocol import DatagramProtocol
import protocol_pb2 as proto
from maps.map import Map
from player.player import Player
from datetime import datetime
from gameplay.weapons import ProjectileManager
from gameplay.gamestate import GamestateManager
from itertools import chain
from reliable import AckManager


class GameServer(DatagramProtocol):
    """docstring for GameServer"""
    def __init__(self):
        # super(GameServer, self).__init__()
        self.players = {}
        self.players_pack = {}
        self.spectators = {}
        self.map = Map('test2', server=True)
        self.ackman = AckManager()
        self.gamestate = GamestateManager(self.allgen, self.ackman)
        self.projectiles = ProjectileManager(self.players, self.map,
                                             self.gamestate.damage_player)
        self.mxdt = .03

    def datagramReceived(self, datagram, address):
        data = proto.Message()
        data.ParseFromString(datagram)
        if data.type == proto.newPlayer:
            pl_id = self.get_id()
            self.init_player(data.input, address, pl_id)
        elif data.type == proto.playerUpdate and data.input.id == self.find_id(address):
            self.players[data.input.id].timer = 0
            self.get_input(data.input)
            dt = data.input.time - self.players[data.input.id].time
            if dt > 0:
                dt = (dt / 10000.)
                dt = dt if dt < self.mxdt else self.mxdt
                # update movement
                self.players[data.input.id].update(dt,
                                                   self.rectgen(data.input.id))
                self.players[data.input.id].time = data.input.time
                self.player_to_pack(data.input.id)
        elif (data.type == proto.disconnect and
              data.input.id == self.find_id(address)):
            print ' '.join((str(datetime.now()),
                           self.players[data.input.id].name, 'disconnected'))
            self.disc_player(data.input.id)
        elif data.type == proto.ackResponse:
            self.ackman.receive_ack(data)

    def update(self, dt):
        keys = []
        for key, player in self.players.iteritems():
            player.timer += dt
            if player.timer > 10:
                keys.append(key)
        for key in keys:
            print ' '.join((str(datetime.now()),
                           self.players[key].name, 'timed out'))
            self.disc_player(key)
        self.projectiles.update(dt)
        self.send_all()
        self.ackman.update(dt)

    def send_all(self):
        for idx, player_ in self.players.iteritems():
            for idx_, pack in self.players_pack.iteritems():
                msg = proto.Message()
                msg.type = proto.playerUpdate
                msg.player.CopyFrom(pack)
                self.transport.write(msg.SerializeToString(), player_.address)

    #find next available id
    def get_id(self):
        idx = 1
        while idx in self.players:
            idx += 1
        return idx

    #find id of adress
    def find_id(self, address):
        for idx in self.players:
            if address == self.players[idx].address:
                return idx
        for idx in self.spectators:
            if address == self.spectators[idx].address:
                self.spectators[idx].timer = 0
        return -1

    def player_to_pack(self, idx):
        self.players_pack[idx].posx = self.players[idx].state.pos.x
        self.players_pack[idx].posy = self.players[idx].state.pos.y
        self.players_pack[idx].velx = self.players[idx].state.vel.x
        self.players_pack[idx].vely = self.players[idx].state.vel.y
        self.players_pack[idx].hp = self.players[idx].state.hp
        self.players_pack[idx].armor = self.players[idx].state.armor
        self.players_pack[idx].time = self.players[idx].time
        self.players_pack[idx].mState.CopyFrom(self.players[idx].state.conds)

    def get_input(self, data):
        self.players[data.id].input = data

    def collide(self, idx):
        colled = False

        for rect in self.rectgen(idx):
            coll = self.players[idx].rect.collides(rect)
            if coll:
                colled = True
                ovr, axis = coll
                self.players[idx].resolve_collision(ovr, axis, 0)
        if not colled:
            self.players[idx].determine_state()

    def init_player(self, data, address, pl_id):
        #check if name already exists
        name = data.name
        i = 1
        while name in [p.name for p in self.players.itervalues()]:
            name = data.name + '_' + str(i)
            i += 1
        self.players[pl_id] = Player(True, self.projectiles.add_projectile,
                                     pl_id)
        self.players[pl_id].timer = 0
        self.players[pl_id].address = address
        self.players[pl_id].name = name
        print ' '.join((str(datetime.now()),
                        self.players[pl_id].name, str(pl_id),
                        'joined the server', str(address)))
        self.players[pl_id].time = 0
        self.players[pl_id].spawn(600, 930)
        self.players_pack[pl_id] = proto.Player()
        self.players_pack[pl_id].id = pl_id
        self.player_to_pack(pl_id)
        #send info do newly connected player
        own = proto.Message()
        player = proto.Player()
        own.type = proto.mapUpdate
        player.id = pl_id
        player.chat = self.map.name
        own.player.CopyFrom(player)
        self.ackman.send_rel(own, address)
        #self.transport.write(own.SerializeToString(), address)
        #send other players to player
        for idx, p in self.players.iteritems():
            if idx != pl_id:
                other = proto.Message()
                player = self.players_pack[idx]
                other.type = proto.newPlayer
                other.player.CopyFrom(player)
                #self.transport.write(other.SerializeToString(), address)
                self.ackman.send_rel(other, address)
                #other.type = proto.playerUpdate
                new = proto.Message()
                new.type = proto.newPlayer
                player = self.players_pack[pl_id]
                new.player.CopyFrom(player)
                #self.transport.write(new.SerializeToString(), p.address)
                self.ackman.send_rel(new, p.address)

    def disc_player(self, id):
        del self.players[id], self.players_pack[id]
        disc = proto.Message()
        disc.type = proto.disconnect
        player = proto.Player()
        player.id = id
        disc.player.CopyFrom(player)
        for idx, p in self.players.iteritems():
            #self.transport.write(disc.SerializeToString(), p.address)
            self.ackman.send_rel(disc, p.address)

    def rectgen(self, idx=-1):
        playergen = (player.rect for key, player in self.players.iteritems()
                     if key != idx)
        mapgen = (rect for rect in self.map.quad_tree.retrieve([],
                  self.players[idx].rect))
        return chain(playergen, mapgen)

    def allgen(self):
        playergen = (player for player in self.players.itervalues())
        specgen = (spec for spec in self.spectators.itervalues())
        return chain(playergen, specgen)
