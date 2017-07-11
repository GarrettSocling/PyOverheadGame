
import arcade
import re
import numpy
from typing import Set, List, Dict
from .data import DATA_DIR, GFX_DIR


GAME_DATA_DIR = DATA_DIR + "/game"

PICTURE_SIZE = 30
BACKGROUND_PIC = 'hinter'
PLAYER_PIC = "figur"
PLAYER_PICS = ['figur', 'konig'] + ['robot%i' % i for i in range(1, 10)]
ERROR_PIC = 'error'  # used for error-displaying

# room count
WORLD_WIDTH = 5
WORLD_HEIGHT = 4
# entity/place count in a room
ROOM_WIDTH = 20
ROOM_HEIGHT = 20
# entity/item/place count in the knapsack
KNAPSACK_WIDTH = 10
KNAPSACK_HEIGHT = 5
KNAPSACK_MAX = 27  # compatibility with Robot1 (9*3)

COMPUTER_CONTROL_INTERVAL = 750  # timer-interval for computer player control


class Game:
    def __init__(self):
        self.world = World()
        self.cur_room_idx = 0
        self.human_player = None  # type: Entity

    @property
    def cur_room(self):
        return self.world.rooms[self.cur_room_idx]

    def load(self, filename):
        """
        :param str filename:
        """
        self.world.load(filename)
        self.human_player = self.world.find_human_player()

    def draw(self):
        self.cur_room.draw()

    def on_screen_resize(self):
        for room in self.world.rooms:
            room.on_screen_resize()

    def on_key_arrow(self, relative):
        """
        :param (int,int) relative: (x,y)
        """
        relative = numpy.array(relative)
        self.human_player.move(relative)

    def update(self, delta_time):
        """
        Movement and game logic. This is called for every frame.

        :param float delta_time: how much time passed
        """


class World:
    def __init__(self):
        self.rooms = [Room(world=self, idx=i) for i in range(WORLD_WIDTH * WORLD_HEIGHT)]

    @staticmethod
    def valid_coord(coord):
        """
        :param (int,int)|numpy.ndarray coord:
        :rtype: bool
        """
        x, y = coord
        return 0 <= x < WORLD_WIDTH and 0 <= y < WORLD_HEIGHT

    @staticmethod
    def coord_to_idx(coord):
        """
        :param (int,int)|numpy.ndarray coord:
        :rtype: int
        """
        assert World.valid_coord(coord)
        x, y = coord
        return y * WORLD_WIDTH + x

    @staticmethod
    def idx_to_coord(idx):
        """
        :param int idx:
        :return: (x,y) coord
        :rtype: numpy.ndarray
        """
        x = idx % WORLD_WIDTH
        y = idx // WORLD_WIDTH
        return numpy.array([x, y])

    def find_human_player(self):
        """
        :rtype: Entity
        """
        for room in self.rooms:
            for player in room.players:
                if player.name == PLAYER_PIC:
                    return player

    def load(self, filename):
        """
        :param str filename:
        """
        loaded_rooms_idxs = set()  # type: Set[int]
        cur_room_idx = None
        cur_place_idx = 0
        for l in open("%s/%s" % (GAME_DATA_DIR, filename)).read().splitlines():
            if cur_room_idx is None:
                m = re.match(r":RAUM([0-9]+)", l)
                assert m, "did not expect %r" % l
                cur_room_idx = int(m.groups()[0]) - 1
                assert 0 <= cur_room_idx < WORLD_WIDTH * WORLD_HEIGHT
                assert cur_room_idx not in loaded_rooms_idxs
                del self.rooms[cur_room_idx].players[:]
                loaded_rooms_idxs.add(cur_room_idx)
                continue
            name = Place.normalize_name(l)
            if name != BACKGROUND_PIC:
                entity = Entity(
                    world=self,
                    world_coord=World.idx_to_coord(cur_room_idx),
                    room_coord=Room.idx_to_coord(cur_place_idx),
                    name=name)
            else:
                entity = None
            if name in PLAYER_PICS:
                if name == PLAYER_PIC:
                    entity.lives = 3
                self.rooms[cur_room_idx].players.append(entity)
            self.rooms[cur_room_idx].places[cur_place_idx].set_entity(entity)
            cur_place_idx += 1
            if cur_place_idx == ROOM_WIDTH * ROOM_HEIGHT:
                cur_room_idx = None
                cur_place_idx = 0
        assert cur_room_idx is None, "last room incomplete"
        assert len(loaded_rooms_idxs) == WORLD_WIDTH * WORLD_HEIGHT, "some room is missing"


class Room:
    def __init__(self, world, idx):
        """
        :param World world:
        :param int idx:
        """
        self.world = world
        self.idx = idx
        self.places = [Place(room=self, idx=i) for i in range(ROOM_WIDTH * ROOM_HEIGHT)]
        self.players = []  # type: List[Entity]
        self.entities_sprite_list = arcade.SpriteList()

    @staticmethod
    def valid_coord(coord):
        """
        :param (int,int)|numpy.ndarray coord:
        :rtype: bool
        """
        x, y = coord
        return 0 <= x < ROOM_WIDTH and 0 <= y < ROOM_HEIGHT

    @staticmethod
    def coord_to_idx(coord):
        """
        :param (int,int)|numpy.ndarray coord:
        :rtype: int
        """
        assert Room.valid_coord(coord)
        x, y = coord
        return y * ROOM_WIDTH + x

    @staticmethod
    def idx_to_coord(idx):
        """
        :param int idx:
        :return: (x,y) coord
        :rtype: numpy.ndarray
        """
        x = idx % ROOM_WIDTH
        y = idx // ROOM_WIDTH
        return numpy.array([x, y])

    def get_place(self, coord):
        """
        :param (int,int)|numpy.ndarray coord:
        """
        return self.places[self.coord_to_idx(coord)]

    def reset_place(self, coord):
        """
        :param (int,int)|numpy.ndarray coord:
        """
        self.places[self.coord_to_idx(coord)].reset_entities()

    def draw(self):
        self.entities_sprite_list.draw()

    def on_screen_resize(self):
        del self.entities_sprite_list[:]
        for place in self.places:
            for entity in place.entities:
                entity.reset_sprite()
            if place.entities:
                self.entities_sprite_list.append(place.entities[-1].sprite)


class Place:
    def __init__(self, room, idx):
        """
        :param Room room:
        :param int idx:
        """
        self.room = room
        self.idx = idx
        self.entities = []  # type: List[Entity]

    @property
    def x(self):
        return self.idx % ROOM_WIDTH

    @property
    def y(self):
        return self.idx // ROOM_WIDTH

    @property
    def coord(self):
        return numpy.array([self.x, self.y])

    @property
    def top_entity_name(self):
        if self.entities:
            return self.entities[-1].name
        return BACKGROUND_PIC

    @staticmethod
    def normalize_name(name):
        """
        :param str name: e.g. "wand1.bmp" or "wand1.png" or "wand1"
        :return: e.g. "wand1"
        :rtype: str
        """
        if name.endswith(".bmp") or name.endswith(".png"):
            name = name[:-4]
        return name

    def _remove_top_entity_sprite(self):
        if self.entities and self.entities[-1].sprite in self.room.entities_sprite_list:
            self.room.entities_sprite_list.remove(self.entities[-1].sprite)

    def _add_top_entity_sprite(self):
        if self.entities:
            self.room.entities_sprite_list.append(self.entities[-1].sprite)

    def reset_entities(self):
        self._remove_top_entity_sprite()
        del self.entities[:]

    def set_entity(self, entity):
        """
        :param Entity entity:
        """
        self._remove_top_entity_sprite()
        del self.entities[:]
        if entity:
            self.add_entity(entity)

    def add_entity(self, entity):
        """
        :param Entity entity:
        """
        self._remove_top_entity_sprite()
        self.entities.append(entity)
        self._add_top_entity_sprite()
        self.on_add_entity()

    def remove_entity(self, entity):
        """
        :param Entity entity:
        """
        self._remove_top_entity_sprite()
        self.entities.remove(entity)
        self._add_top_entity_sprite()

    def is_free(self):
        return not self.entities

    def is_allowed_to_add_entity(self, entity):
        """
        :param Entity entity:
        :rtype: bool
        """
        return is_allowed_together(self.entities + [entity])

    def on_add_entity(self):
        on_joined_together(world=self.room.world, entities=self.entities)


class Entity:
    def __init__(self, world, world_coord, room_coord, name):
        """
        :param World world:
        :param numpy.ndarray world_coord:
        :param numpy.ndarray room_coord:
        :param str name: e.g. "figur"
        """
        self.world = world
        self.cur_world_coord = world_coord
        self.cur_room_coord = room_coord
        self.name = name
        self.door_keys = set()  # type: Set[int]
        self.scores = 0
        self.lives = 0
        self.is_alive = True
        self.sprite = None  # type: arcade.Sprite
        self.reset_sprite()

    def __repr__(self):
        return "<Entity %r in room %r in place %r>" % (
            self.name, tuple(self.cur_world_coord), tuple(self.cur_room_coord))

    def update_sprite_pos(self):
        from .app import app
        screen_width, screen_height = app.window.get_size()
        self.sprite.left = self.sprite.width * self.cur_room_coord[0]
        self.sprite.top = screen_height - self.sprite.height * self.cur_room_coord[1]

    def reset_sprite(self):
        from .app import app
        screen_width, screen_height = app.window.get_size()
        sprite_width = screen_width // ROOM_WIDTH
        sprite_height = screen_height // ROOM_HEIGHT
        texture = arcade.load_texture(file_name="%s/%s.png" % (GFX_DIR, self.name))
        scale = min(sprite_width / texture.width, sprite_height / texture.height)
        self.sprite = arcade.Sprite(scale=scale)
        self.sprite.append_texture(texture)
        self.sprite.set_texture(0)
        self.update_sprite_pos()

    @property
    def cur_room(self):
        return self.world.rooms[World.coord_to_idx(self.cur_world_coord)]

    @property
    def cur_place(self):
        return self.cur_room.get_place(self.cur_room_coord)

    def move(self, relative):
        """
        :param numpy.ndarray relative: (x,y)
        """
        if not self.is_alive:
            return
        new_coord = self.cur_room_coord + relative
        if not Room.valid_coord(new_coord):
            return
        cur_room = self.cur_room
        if not cur_room.get_place(new_coord).is_allowed_to_add_entity(self):
            return
        self.cur_place.remove_entity(self)
        self.cur_room_coord = new_coord
        self.cur_room.get_place(new_coord).add_entity(self)
        self.update_sprite_pos()

    def kill(self):
        if self.lives > 0:
            self.lives -= 1
            return
        self.cur_place.remove_entity(self)
        self.is_alive = False


def is_allowed_together(entities):
    """
    :param list[Entity] entities:
    :rtype: bool
    """
    if len(entities) <= 1:
        return True
    entity_names_map = {}  # type: Dict[str,List[Entity]]
    for entity in entities:
        entity_names_map.setdefault(entity.name, [])
        entity_names_map[entity.name].append(entity)
    if any(["wand%i" % i in entity_names_map for i in range(1, 3)]):
        return False
    if any(["code%i" % i in entity_names_map for i in range(1, 4)]):
        return False
    doors = [i for i in range(1, 10) if "tuer%i" % i in entity_names_map]
    if doors:
        if len(doors) > 1:
            return False
        door_idx = doors[0]
        door = "tuer%i" % door_idx
        for entity in entities:
            if entity.name == door:
                continue
            if door_idx not in entity.door_keys:
                return False
        return True
    robots = [entity for entity in entities if entity.name in PLAYER_PICS and entity.name != PLAYER_PIC]
    if len(robots) > 1:
        return False
    return True


def on_joined_together(world, entities):
    """
    :param World world:
    :param list[Entity] entities:
    """
    if len(entities) <= 1:
        return
    electro_walls = [entity for entity in entities if entity.name == "wand3"]
    players = [entity for entity in entities if entity.name in PLAYER_PICS]
    while players and electro_walls:
        for player in players:
            if not electro_walls:
                break
            electro_wall = electro_walls[0]
            electro_wall.kill()
            player.kill()
            if not electro_wall.is_alive:
                electro_walls.remove(electro_wall)
            if not player.is_alive:
                players.remove(player)
    human_players = [entity for entity in players if entity.name == PLAYER_PIC]
    robots = [entity for entity in players if entity.name != PLAYER_PIC]
    while human_players and robots:
        human = human_players[0]
        robot = robots[0]
        robot.kill()
        human.kill()
        if not robot.is_alive:
            robots.remove(robot)
        if not human.is_alive:
            human_players.remove(human)
    points = [entity for entity in entities if entity.name.startswith("punkt")]
    while human_players and points:
        for human in human_players:
            if not points:
                break
            point = points[0]
            human.scores += 1000
            point.kill()
            if not point.is_alive:
                points.remove(point)
