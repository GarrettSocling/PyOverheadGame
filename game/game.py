
import arcade
import os
import re
import numpy
import random
from typing import Set, List, Dict, Optional
from .data import DATA_DIR, GFX_DIR, UserDataDir
from .gui import Menu, WindowStack, ConfirmActionMenu, MessageBox, TextInput


GAME_DATA_DIR = DATA_DIR + "/game"
GameDataDirs = (UserDataDir + "/game", GAME_DATA_DIR)

PICTURE_SIZE = 30
BACKGROUND_PIC = 'hinter'
PLAYER_PIC = "figur"
KING_PIC = "konig"
ROBOT_PICS = [KING_PIC] + ['robot%i' % i for i in range(1, 10)]
PLAYER_PICS = [PLAYER_PIC] + ROBOT_PICS
KEY_PICS = ["schl%i" % i for i in range(1, 10)]
DOOR_PICS = ["tuer%i" % i for i in range(1, 10)]
DIAMOND_PICS = ["diamant%i" % i for i in range(1, 4)]
CODE_PICS = ["code%i" % i for i in range(1, 4)]
SCORES_PICS = ["punkt%i" % i for i in range(1, 6)]
GET_LIVE_PIC = "leben"
BURN_PIC = "aetz"
SAVE_PIC = "speicher"
KILL_PIC = "kill"
SOFT_WALL_PIC = "wand1"
HARD_WALL_PIC = "wand2"
ELECTRIC_WALL_PIC = "wand3"
WALL_PICS = [SOFT_WALL_PIC, HARD_WALL_PIC, ELECTRIC_WALL_PIC]
BURNABLE_PICS = [SOFT_WALL_PIC]
COLLECTABLE_PICS = [SAVE_PIC, BURN_PIC, GET_LIVE_PIC] + KEY_PICS + DIAMOND_PICS
ERROR_PIC = 'error'  # used for error-displaying

# room count
WORLD_WIDTH = 5
WORLD_HEIGHT = 4
# entity/place count in a room
ROOM_WIDTH = 20
ROOM_HEIGHT = 20
# entity/item/place count in the knapsack
KNAPSACK_WIDTH = 3
KNAPSACK_HEIGHT = 9
KNAPSACK_MAX = 27  # compatibility with Robot1 (9*3)

COMPUTER_CONTROL_INTERVAL = 0.75  # timer-interval for computer player control

GameFocusHumanPlayer = 0
GameFocusKnapsack = 1
NumberGameFocus = 2


class Game:
    Compatibility1999 = True

    def __init__(self):
        self.world = World(game=self)
        self.cur_room = self.world.get_room((0, 0))
        self.human_player = None  # type: Entity
        self.dt_computer = 0.0
        self.window_stack = WindowStack()
        self.main_menu = MainMenu(game=self)
        self.main_menu.open()
        self.game_focus = GameFocusHumanPlayer
        self.game_text_gfx_label = None  # type: arcade.pyglet.text.Label
        self.info_text = ""
        self.info_text_gfx_label = None  # type: arcade.pyglet.text.Label
        self.set_info_text("Welcome")
        self.recheck_finished_game = False
        self.game_selected = "robot.sce"

    def init(self):
        self.load(self.game_selected)

    def restart(self):
        self.init()
        self.set_info_text("Game restarted")

    def exit(self):
        print("Good bye!")
        import sys
        sys.exit()

    @property
    def menu_is_visible(self):
        return self.window_stack.is_visible()

    def load(self, filename):
        """
        :param str filename:
        """
        self.world.load(filename)
        self.human_player = self.world.find_human_player()
        self.human_player.knapsack.selected_place = self.human_player.knapsack.get_place((0, 0))
        self.cur_room = self.human_player.room
        self.dt_computer = 0.0

    def save(self, filename):
        self.world.save(filename)

    def get_text_placement(self):
        from .app import app
        y0 = ROOM_HEIGHT * app.window.room_pixel_size
        y1 = (ROOM_HEIGHT + 1) * app.window.room_pixel_size
        x0 = 0
        x1 = ROOM_WIDTH * app.window.room_pixel_size
        return numpy.array((x0, y0)), numpy.array((x1, y1))

    def draw_text(self):
        from .app import app
        p1, p2 = self.get_text_placement()
        center = (p1 + p2) // 2
        arcade.draw_rectangle_filled(color=arcade.color.WHITE, **app.get_screen_pos_args((p1, p2)))
        txt = "Score: %i, lives: %i" % (self.human_player.scores, self.human_player.lives)
        if not self.game_text_gfx_label or self.game_text_gfx_label.text != txt:
            self.game_text_gfx_label = arcade.create_text(txt, color=arcade.color.BLACK, anchor_y="center")
        arcade.render_text(
            self.game_text_gfx_label,
            start_x=p1[0] + 5, start_y=app.window.height - center[1])
        if self.info_text_gfx_label:
            arcade.render_text(
                self.info_text_gfx_label,
                start_x=p1[0] + self.game_text_gfx_label.content_width + 20, start_y=app.window.height - center[1])

    def confirm_action(self, title, action):
        """
        :param str title:
        :param ()->None action:
        """
        ConfirmActionMenu(
            window_stack=self.window_stack,
            title=title, action=action).open()

    def set_info_text(self, info_txt):
        self.info_text = info_txt
        self.info_text_gfx_label = arcade.create_text(
            info_txt, color=arcade.color.BLUE, anchor_y="center")

    def draw(self):
        self.draw_text()
        self.cur_room.draw()
        if not self.menu_is_visible and self.game_focus == GameFocusHumanPlayer:
            self.cur_room.draw_focus()
        self.human_player.knapsack.draw()
        if not self.menu_is_visible and self.game_focus == GameFocusKnapsack:
            self.human_player.knapsack.draw_focus()
        self.human_player.knapsack.draw_selection(
            focused=self.game_focus == GameFocusKnapsack and not self.menu_is_visible)
        self.window_stack.draw()

    def on_screen_resize(self):
        for room in self.world.rooms:
            room.on_screen_resize()

    def on_key_tab(self):
        if self.window_stack.is_visible():
            self.window_stack.switch_focus()
        else:
            self.change_game_focus()

    def on_key_return(self):
        if self.window_stack.is_visible():
            self.window_stack.do_action()
        else:
            self.use_knapsack_selection()

    def on_key_escape(self):
        if not self.window_stack.is_visible():
            self.main_menu.open()
        else:
            self.window_stack.on_key_escape()

    def on_text(self, text):
        if self.window_stack.is_visible():
            self.window_stack.on_text(text)

    def on_text_motion(self, motion):
        if self.window_stack.is_visible():
            self.window_stack.on_text_motion(motion)

    def on_key_arrow(self, relative):
        """
        :param (int,int) relative: (x,y)
        """
        relative = numpy.array(relative)
        if self.window_stack.is_visible():
            self.window_stack.switch_focus(sum(relative))
        else:  # game
            if self.game_focus == GameFocusHumanPlayer:
                self.human_player.move(relative)
                self.cur_room = self.human_player.room
            elif self.game_focus == GameFocusKnapsack:
                self.human_player.knapsack.move_selection(relative)

    def change_game_focus(self):
        self.game_focus += 1
        self.game_focus %= NumberGameFocus

    def use_knapsack_selection(self):
        place = self.human_player.knapsack.selected_place
        if not place.entities:
            return
        item = place.entities[-1]
        do_item_action(player=self.human_player, item=item)
        if not item.place.entities:  # if item was used/killed
            # Select any other such item in the knapsack, if there is one.
            others = self.human_player.knapsack.find_entities([item.name])
            if others:
                self.human_player.knapsack.selected_place = others[0].place
        self.game_focus = GameFocusHumanPlayer

    def do_computer_interval(self):
        for player in self.cur_room.find_robots():
            do_robot_action(robot=player, human=self.human_player)
            if player.name == KING_PIC:
                # The king does two actions at once.
                do_robot_action(robot=player, human=self.human_player)

    def update(self, delta_time):
        """
        Movement and game logic. This is called for every frame.

        :param float delta_time: how much time passed
        """
        if self.menu_is_visible:
            return
        self.dt_computer += delta_time
        if self.dt_computer >= COMPUTER_CONTROL_INTERVAL:
            self.dt_computer -= COMPUTER_CONTROL_INTERVAL
            self.do_computer_interval()
        if self.recheck_finished_game:
            if not self.world.find_king():
                self.world.finish_game()
                MessageBox(
                    title="Congratulations! The king is defeated. You finished the game.",
                    window_stack=self.window_stack).open()
            self.recheck_finished_game = False


class GameMenu(Menu):
    def __init__(self, game, **kwargs):
        """
        :param Game game:
        """
        super(GameMenu, self).__init__(window_stack=game.window_stack, **kwargs)
        self.game = game


class MainMenu(GameMenu):
    def __init__(self, game):
        """
        :param Game game:
        """
        super(MainMenu, self).__init__(game=game, title="PyOverheadGame!", actions=[
            ("Play", self.close),
            ("Restart", lambda: game.confirm_action("Do you really want to restart?", game.restart)),
            ("Switch game", SelectGameMenu(game=game).open),
            ("Load", lambda: LoadGameMenu(game=game).open()),
            ("Save", SaveGameMenu(game=game).open),
            ("Debug", DebugMenu(game=game).open),
            ("Exit", lambda: game.confirm_action("Do you really want to exit?", game.exit))
        ])


class LoadGameMenu(GameMenu):
    def __init__(self, game):
        """
        :param Game game:
        """
        from glob import glob
        import os
        def make_load_action_tuple(f):
            save_name = os.path.splitext(os.path.basename(f))[0]
            return "Load '%s'" % save_name, lambda: self.load_game(f)
        files = []
        for d in GameDataDirs:
            files += glob(d + "/*.spi")
        load_actions = [make_load_action_tuple(f) for f in files]
        super(LoadGameMenu, self).__init__(
            game=game, title="Load game",
            actions=load_actions + [("Close", self.close)])

    def load_game(self, f):
        """
        :param str f:
        """
        print("load saved game %r" % f)
        self.game.load(f)
        self.close()
        MessageBox(
            title="Game %r loaded." % os.path.splitext(os.path.basename(f))[0],
            window_stack=self.window_stack).open()


class SelectGameMenu(GameMenu):
    def __init__(self, game):
        """
        :param Game game:
        """
        from glob import glob
        import os
        def make_load_action_tuple(f):
            save_name = os.path.splitext(os.path.basename(f))[0]
            return "Game '%s'" % save_name, lambda: self.load_game(f)
        files = []
        for d in GameDataDirs:
            files += glob(d + "/*.sce")
        load_actions = [make_load_action_tuple(f) for f in files]
        super(SelectGameMenu, self).__init__(
            game=game, title="Select game",
            actions=load_actions + [("Close", self.close)])

    def load_game(self, f):
        """
        :param str f:
        """
        print("select game %r" % f)
        self.game.game_selected = f
        self.game.load(f)
        self.close()
        MessageBox(
            title="Welcome to the %s game." % os.path.splitext(os.path.basename(f))[0],
            window_stack=self.window_stack).open()


class SaveGameMenu(TextInput):
    def __init__(self, game):
        """
        :param Game game:
        """
        super(SaveGameMenu, self).__init__(
            window_stack=game.window_stack, title="Save game under name:",
            callback=self.save_game)
        self.game = game

    def save_game(self, f):
        """
        :param str|None f:
        """
        if f is None:
            return
        for c in ":\n\t/\\":
            f = f.replace(c, "")
        f = f.strip()
        if not f:
            MessageBox(title="Please enter a valid name.", window_stack=self.window_stack).open()
            return
        f += ".spi"
        f = get_unique_game_file(f)
        print("save %r" % f)
        self.game.save(f)
        MessageBox(title="Game saved as %r." % os.path.splitext(f)[0], window_stack=self.window_stack).open()


class DebugMenu(GameMenu):
    def __init__(self, game):
        """
        :param Game game:
        """
        super(DebugMenu, self).__init__(game=game, title="Debug", actions=[
            ("Close", self.close),
            ("Console print hello", lambda: print("Hello")),
            ("Text input",
                TextInput(
                    title="Text input", window_stack=game.window_stack,
                    callback=self.text_input).open),
            ("Profiler start", self.profile_start),
            ("Profiler stop", self.profile_stop)
        ])

    def profile_start(self):
        import yappi
        yappi.start()

    def profile_stop(self):
        import yappi
        yappi.stop()
        columns = {0: ("name", 36), 1: ("ncall", 7),
                   2: ("tsub", 8), 3: ("ttot", 8), 4: ("tavg", 8)}
        yappi.get_func_stats().print_all(columns=columns)
        yappi.get_thread_stats().print_all()

    def text_input(self, s):
        """
        :param str|None s:
        """
        if s is None:
            MessageBox("Text input was cancelled.", window_stack=self.window_stack).open()
        else:
            MessageBox("Text input: %r" % s, window_stack=self.window_stack).open()


class World:
    def __init__(self, game):
        """
        :param Game game:
        """
        self.game = game
        self.rooms = [Room(world=self, idx=i) for i in range(WORLD_WIDTH * WORLD_HEIGHT)]
        self.diamonds_activated = [False] * len(DIAMOND_PICS)

    def _reset_diamonds(self):
        for i in range(len(DIAMOND_PICS)):
            self.diamonds_activated[i] = False

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

    def get_room(self, coord):
        """
        :param (int,int)|numpy.ndarray coord:
        :rtype: Room
        """
        return self.rooms[self.coord_to_idx(coord)]

    def find_human_player(self):
        """
        :rtype: Entity
        """
        for room in self.rooms:
            for player in room.players:
                if player.name == PLAYER_PIC:
                    return player

    def find_king(self):
        for room in self.rooms:
            for player in room.players:
                if player.name == KING_PIC:
                    return player
        return None

    def set_king_vulnerable(self):
        for room in self.rooms:
            for player in room.players:
                if player.name == KING_PIC:
                    player.lives = 0

    def finish_game(self):
        for room in self.rooms:
            for player in room.players:
                if player.name in ROBOT_PICS:
                    player.lives = 0
                    player.kill()
            for place in room.places:
                removed = False
                for entity in list(place.entities):
                    if entity.name in WALL_PICS + DOOR_PICS:
                        entity.kill()
                        removed = True
                if removed and place.is_free():
                    place.set_entity(Entity(
                        room=room,
                        room_coord=place.coord,
                        name=random.choice(SCORES_PICS)))

    def load(self, filename):
        """
        :param str filename:
        """
        # We only need to reset diamond states.
        # The entities of each room will be reset via set_entity().
        self._reset_diamonds()
        loaded_rooms_idxs = set()  # type: Set[int]
        cur_room_idx = None
        cur_place_idx = 0
        file_ext = filename.rsplit(".", 1)[-1].lower()
        if "/" not in filename:
            filename = find_game_file(filename)
        lines = open(filename).read().splitlines()
        assert file_ext in ("sce", "spi")
        # sce -> just the world rooms
        # spi -> full game state
        """
        file content (for full game state):
        [Room-Nr]
        [Name]
        [Scores]
        [Life]
        [Diamond status 1]
        [Diamond status 2]
        [Diamond status 3]
        [Place under player]
        :RUCK
        bild1.bmp
        ...
        :RAUM1
        bild1.bmp
        bild2.bmp
        ...
        :RAUM2
        ...
        :RAUM20
        ...
        """
        line_start_idx = 0
        if file_ext == "spi":  # full game state:
            assert lines[8] == ":RUCK"
            line_start_idx = 9 + KNAPSACK_MAX + 1
            assert lines[line_start_idx - 1] == "ENDE"
        BackgroundPics = (BACKGROUND_PIC, SAVE_PIC, "")
        for l in lines[line_start_idx:]:
            if cur_room_idx is None:
                if not l:
                    continue
                m = re.match(r":RAUM([0-9]+)", l, flags=re.IGNORECASE)
                assert m, "did not expect %r" % l
                cur_room_idx = int(m.groups()[0]) - 1
                assert 0 <= cur_room_idx < WORLD_WIDTH * WORLD_HEIGHT
                assert cur_room_idx not in loaded_rooms_idxs
                del self.rooms[cur_room_idx].players[:]
                loaded_rooms_idxs.add(cur_room_idx)
                continue
            name = Place.normalize_name(l)
            # We treat background just as nothing.
            # We also ignore the save mechanism and allow to save always via the menu.
            if name not in BackgroundPics:
                entity = Entity(
                    room=self.rooms[cur_room_idx],
                    room_coord=self.rooms[cur_room_idx].idx_to_coord(cur_place_idx),
                    name=name)
            else:
                entity = None
            if name in PLAYER_PICS:
                if name == PLAYER_PIC:
                    entity.knapsack = Room(
                        world=self,
                        width=KNAPSACK_WIDTH, height=KNAPSACK_HEIGHT,
                        screen_offset=(ROOM_WIDTH + 1, 0))
                self.rooms[cur_room_idx].players.append(entity)
            self.rooms[cur_room_idx].places[cur_place_idx].set_entity(entity)
            cur_place_idx += 1
            if cur_place_idx == ROOM_WIDTH * ROOM_HEIGHT:
                cur_room_idx = None
                cur_place_idx = 0
        assert cur_room_idx is None, "last room incomplete"
        assert len(loaded_rooms_idxs) == WORLD_WIDTH * WORLD_HEIGHT, "some room is missing"
        if file_ext == "spi":  # full game state
            # no need for room number, neither the name (line 0 and 1)
            player = self.find_human_player()
            player.scores = int(lines[2])
            player.lives = int(lines[3])
            assert len(DIAMOND_PICS) == len(self.diamonds_activated) == 3
            for i in range(3):
                self.diamonds_activated[i] = bool(int(lines[4 + i]))
            place_under_player = Place.normalize_name(lines[7])
            if place_under_player not in BackgroundPics:
                assert player.place.entities == [player]
                entity = Entity(
                    room=player.room,
                    room_coord=player.room_coord,
                    name=place_under_player)
                player.place.entities.insert(0, entity)
            assert lines[8] == ":RUCK"
            for idx, l in enumerate(lines[9:9 + KNAPSACK_MAX]):
                room_coord = numpy.array([idx % KNAPSACK_WIDTH, idx // KNAPSACK_WIDTH])
                name = Place.normalize_name(l)
                if name not in BackgroundPics:
                    entity = Entity(room=player.knapsack, room_coord=room_coord, name=name)
                    player.knapsack.get_place(room_coord).set_entity(entity)
        if all(self.diamonds_activated):
            self.set_king_vulnerable()

    def save(self, filename):
        """
        :param str filename:
        """
        assert "/" not in filename
        name, file_ext = filename.rsplit(".", 1)
        assert file_ext in ("sce", "spi")
        assert "\n" not in name
        # sce -> just the world rooms
        # spi -> full game state
        filename = GameDataDirs[0] + "/" + filename
        assert not os.path.exists(filename)
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        with open(filename, "w") as f:
            # see self.load()
            if file_ext == "spi":
                player = self.find_human_player()
                f.write("%i\n" % self.game.cur_room.idx)  # room-nr
                f.write("%s\n" % name)  # name
                f.write("%i\n" % player.scores)  # scores
                f.write("%i\n" % player.lives)  # lives
                assert len(DIAMOND_PICS) == len(self.diamonds_activated) == 3
                for i in range(3):
                    f.write("%i\n" % int(self.diamonds_activated[i]))
                if len(player.place.entities) >= 2:
                    assert len(player.place.entities) == 2
                    f.write("%s.bmp\n" % player.place.entities[0].name)  # place under player
                else:
                    assert len(player.place.entities) == 1
                    f.write("\n")  # place under player (nothing)
                f.write(":RUCK\n")
                assert len(player.knapsack.places) == KNAPSACK_MAX
                for place_idx, place in enumerate(player.knapsack.places):
                    if place.entities:
                        assert len(place.entities) == 1
                        f.write("%s.bmp\n" % place.entities[-1].name)
                    else:
                        f.write("\n")
                f.write("ENDE\n")
            assert len(self.rooms) == WORLD_WIDTH * WORLD_HEIGHT
            for room_idx, room in enumerate(self.rooms):
                f.write(":RAUM%i\n" % (room_idx + 1))
                assert len(room.places) == ROOM_WIDTH * ROOM_HEIGHT
                for place_idx, place in enumerate(room.places):
                    if place.entities:
                        f.write("%s.bmp\n" % place.entities[-1].name)
                    else:
                        f.write("%s.bmp\n" % BACKGROUND_PIC)
            f.close()


class Room:
    def __init__(self, world, idx=None, width=ROOM_WIDTH, height=ROOM_HEIGHT, screen_offset=(0, 0)):
        """
        :param World world:
        :param int|None idx: room idx in the world, such that world.rooms[idx] is self
        :param int width: number of places in width
        :param int height: number of places in height
        :param (int,int) screen_offset: place-size screen offset
        """
        self.world = world
        self.idx = idx
        self.screen_offset = numpy.array(screen_offset)
        self.width = width
        self.height = height
        self.places = [Place(room=self, idx=i) for i in range(width * height)]
        self.selected_place = None  # type: Place
        self.players = []  # type: List[Entity]  # king + robots + human
        self.entities_sprite_list = arcade.SpriteList()

    def __repr__(self):
        return "<Room idx=%r>" % (self.idx,)

    @property
    def world_coord(self):
        x = self.idx % WORLD_WIDTH
        y = self.idx // WORLD_WIDTH
        return numpy.array((x, y))

    def valid_coord(self, coord):
        """
        :param (int,int)|numpy.ndarray coord:
        :rtype: bool
        """
        x, y = coord
        return 0 <= x < self.width and 0 <= y < self.height

    def coord_to_idx(self, coord):
        """
        :param (int,int)|numpy.ndarray coord:
        :rtype: int
        """
        assert self.valid_coord(coord)
        x, y = coord
        return y * self.width + x

    def idx_to_coord(self, idx):
        """
        :param int idx:
        :return: (x,y) coord
        :rtype: numpy.ndarray
        """
        x = idx % self.width
        y = idx // self.width
        return numpy.array([x, y])

    def get_place(self, coord):
        """
        :param (int,int)|numpy.ndarray coord:
        """
        coord = numpy.array(coord)
        if not self.valid_coord(coord):
            assert self.idx is not None
            world_size = numpy.array((WORLD_WIDTH, WORLD_HEIGHT))
            room_size = numpy.array((self.width, self.height))
            world_room_coord = self.world_coord * room_size + coord
            world_room_coord %= world_size * room_size
            world_coord = world_room_coord // room_size
            coord = world_room_coord % room_size
            room = self.world.get_room(world_coord)
            assert room.valid_coord(coord)
            return room.get_place(coord)
        return self.places[self.coord_to_idx(coord)]

    def reset_place(self, coord):
        """
        :param (int,int)|numpy.ndarray coord:
        """
        self.places[self.coord_to_idx(coord)].reset_entities()

    def get_screen_placement(self):
        """
        :return: ((x1,y1), (x2,y2))
        :rtype: (numpy.ndarray, numpy.ndarray)
        """
        from .app import app
        size = numpy.array((self.width, self.height))
        screen_size = size * app.window.room_pixel_size
        pos = self.screen_offset * app.window.room_pixel_size
        return pos, pos + screen_size

    def draw(self):
        from .app import app
        arcade.draw_rectangle_filled(
            color=[127, 127, 127], **app.get_screen_pos_args(self.get_screen_placement()))
        self.entities_sprite_list.draw()

    def draw_focus(self):
        from .app import app
        arcade.draw_rectangle_outline(
            color=arcade.color.BLUE, **app.get_screen_pos_args(self.get_screen_placement()))

    def draw_selection(self, focused=False):
        if not self.selected_place:
            return
        from .app import app
        p1 = (self.screen_offset + self.selected_place.coord) * app.window.room_pixel_size
        size = numpy.array((app.window.room_pixel_size, app.window.room_pixel_size))
        p2 = p1 + size
        center = (p1 + p2) // 2
        arcade.draw_rectangle_outline(
            color=arcade.color.BLUE if focused else arcade.color.BLACK,
            center_x=center[0], center_y=app.window.height - center[1],
            width=size[0], height=size[1])

    def move_selection(self, relative):
        """
        :param numpy.ndarray relative:
        """
        coord = self.selected_place.coord + relative
        if not self.valid_coord(coord):
            return
        self.selected_place = self.get_place(coord)

    def on_screen_resize(self):
        del self.entities_sprite_list[:]
        for place in self.places:
            for entity in place.entities:
                entity.reset_sprite()
            if place.entities:
                self.entities_sprite_list.append(place.entities[-1].sprite)

    def count_entities(self):
        """
        :return: total number of entities in this room
        :rtype: int
        """
        c = 0
        for place in self.places:
            c += len(place.entities)
        return c

    def have_entity_name(self, name):
        """
        :param str name:
        :return: whether we have an entity with this name
        :rtype: bool
        """
        for place in self.places:
            for entity in place.entities:
                if entity.name == name:
                    return True
        return False

    def find_free_place(self):
        """
        :return: a place where there is no entity, or None
        :rtype: None|Place
        """
        for place in self.places:
            if not place.entities:
                return place
        return None

    def find_entities(self, entity_names):
        """
        :param list[str] entity_names:
        :return: list of entities
        :rtype: list[Entity]
        """
        entities = []
        for place in self.places:
            for entity in place.entities:
                if entity.name in entity_names:
                    entities.append(entity)
        return entities

    def find_players(self):
        return self.find_entities(PLAYER_PICS)

    def find_robots(self):
        return self.find_entities(ROBOT_PICS)


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
        return self.idx % self.room.width

    @property
    def y(self):
        return self.idx // self.room.width

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
        on_joined_together(self.entities)

    def is_at_room_border(self):
        if self.x in (0, self.room.width - 1):
            return True
        if self.y in (0, self.room.height - 1):
            return True
        return False

    def nearby_places(self, allow_room_borders=False):
        """
        :param bool allow_room_borders:
        :return: list of places in this room
        :rtype: list[Place]
        """
        places = []
        room_borders = [[0, self.room.width - 1], [0, self.room.height - 1]]
        if not allow_room_borders:
            for b in room_borders:
                b[0] += 1
                b[1] -= 1
        for rel in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            coord = self.coord + numpy.array(rel)
            if coord[0] < room_borders[0][0] or coord[0] > room_borders[0][1]:
                continue
            if coord[1] < room_borders[1][0] or coord[1] > room_borders[1][1]:
                continue
            places.append(self.room.get_place(coord))
        return places

    def nearby_entities(self, include_room_borders=False):
        """
        :param bool include_room_borders:
        :return: list of entities
        :rtype: list[Entity]
        """
        entities = []
        for place in self.nearby_places(allow_room_borders=include_room_borders):
            entities.extend(reversed(place.entities))
        return entities


class Entity:
    def __init__(self, room, room_coord, name):
        """
        :param Room room:
        :param numpy.ndarray room_coord:
        :param str name: e.g. "figur"
        """
        self.room = room
        self.room_coord = room_coord
        self.name = name
        self.knapsack = None  # type: Optional[Room]
        self.scores = 0
        if name == PLAYER_PIC:
            self.lives = 3
        elif name == KING_PIC:
            self.lives = float("inf")
        else:
            self.lives = 0
        self.is_alive = True
        self.sprite = None  # type: arcade.Sprite
        self.reset_sprite()

    def __repr__(self):
        return "<Entity %r in room %r in place %r>" % (
            self.name, self.room, tuple(self.room_coord))

    def is_at_room_edge(self):
        if self.room_coord[0] in (0, self.room.width - 1):
            return True
        if self.room_coord[1] in (0, self.room.height -1):
            return True
        return False

    def update_sprite_pos(self):
        from .app import app
        self.sprite.left = self.sprite.width * self.room_coord[0] + \
                           self.room.screen_offset[0] * app.window.room_pixel_size
        self.sprite.top = app.window.height - (
            self.sprite.height * self.room_coord[1] +
            self.room.screen_offset[1] * app.window.room_pixel_size)

    def reset_sprite(self):
        from .app import app
        texture = arcade.load_texture(file_name="%s/%s.png" % (GFX_DIR, self.name))
        scale = app.window.room_pixel_size / texture.width
        self.sprite = arcade.Sprite(scale=scale)
        self.sprite.append_texture(texture)
        self.sprite.set_texture(0)
        self.update_sprite_pos()

    @property
    def place(self):
        return self.room.get_place(self.room_coord)

    def can_move(self, relative):
        """
        :param numpy.ndarray relative: (x,y)
        """
        if not self.is_alive:
            return False
        new_coord = self.room_coord + relative
        if not self.room.valid_coord(new_coord):
            return True  # we will just always switch to a new room in this case
        if not self.room.get_place(new_coord).is_allowed_to_add_entity(self):
            return False
        return True

    def move(self, relative):
        """
        :param numpy.ndarray relative: (x,y)
        """
        if not self.can_move(relative):
            return
        self.move_to_place(self.room.get_place(self.room_coord + relative))

    def move_to_place(self, place):
        """
        :param Place place:
        """
        self.place.remove_entity(self)
        self.room = place.room
        self.room_coord = place.coord
        place.add_entity(self)
        self.update_sprite_pos()

    def kill(self):
        if self.lives > 0:
            self.lives -= 1
            return
        if self is self.room.world.game.human_player:
            self.room.world.game.set_info_text("Very sad, you are dead.")
        if self.name == KING_PIC:
            self.room.world.game.set_info_text("The king is dead!")
            self.room.world.game.recheck_finished_game = True
        if self.name in PLAYER_PICS:
            self.room.players.remove(self)
        self.place.remove_entity(self)
        self.is_alive = False


def is_allowed_together(entities):
    """
    :param list[Entity] entities:
    :rtype: bool
    """
    if len(entities) <= 1:
        return True
    robots = [entity for entity in entities if entity.name in ROBOT_PICS]
    if len(robots) > 1:
        return False
    game = entities[0].room.world.game
    if game.Compatibility1999:
        # This is only for game-state compatibility with older versions,
        # and with the saved games format.
        if robots:
            remaining = [e for e in entities if e.name not in ROBOT_PICS]
            # Now remove all which are allowed together with robots.
            # The only reason they are not allowed is because we couldn't save such a state.
            remaining = [e for e in remaining if e.name != PLAYER_PIC]
            remaining = [e for e in remaining if e.name != ELECTRIC_WALL_PIC]
            if remaining:  # Still any which are not allowed together?
                return False
    entity_names_map = {}  # type: Dict[str,List[Entity]]
    for entity in entities:
        entity_names_map.setdefault(entity.name, [])
        entity_names_map[entity.name].append(entity)
    if any(["wand%i" % i in entity_names_map for i in range(1, 3)]):
        return False
    if any(["code%i" % i in entity_names_map for i in range(1, 4)]):
        return False
    doors = [door for door in DOOR_PICS if door in entity_names_map]
    if doors:
        if len(doors) > 1:
            return False
        door_name = doors[0]
        door = entity_names_map[door_name][0]
        if door.is_at_room_edge() and door.room.find_robots():
            # special rule: nothing can pass any door at an edge if there are robots alive
            return False
        door_idx = DOOR_PICS.index(door_name)
        door_key = KEY_PICS[door_idx]
        for entity in entities:
            if entity.name == door_name:
                continue
            if not entity.knapsack:
                return False
            if not entity.knapsack.have_entity_name(door_key):
                return False
        return True
    return True


def on_joined_together(entities):
    """
    :param list[Entity] entities:
    """
    if len(entities) <= 1:
        return
    electric_walls = [entity for entity in entities if entity.name == ELECTRIC_WALL_PIC]
    players = [entity for entity in entities if entity.name in PLAYER_PICS]
    while players and electric_walls:
        for player in players:
            if not electric_walls:
                break
            electro_wall = electric_walls[0]
            electro_wall.kill()
            player.kill()
            if not electro_wall.is_alive:
                electric_walls.remove(electro_wall)
            if not player.is_alive:
                players.remove(player)
    human_players = [entity for entity in players if entity.name == PLAYER_PIC]
    robots = [entity for entity in players if entity.name != PLAYER_PIC]
    while human_players and robots:
        human = human_players[0]
        robot = robots[0]
        robot.kill()
        human.kill()
        if not robot.is_alive or robot.lives == float("inf"):
            robots.remove(robot)
        if not human.is_alive or human.lives == float("inf"):
            human_players.remove(human)
    points = [entity for entity in entities if entity.name in SCORES_PICS]
    while human_players and points:
        for human in human_players:
            if not points:
                break
            point = points[0]
            human.scores += 1000
            point.kill()
            if not point.is_alive:
                points.remove(point)
    collectable = [entity for entity in entities if entity.name in COLLECTABLE_PICS]
    collecting_humans = list(human_players)
    while collecting_humans and collectable:
        for human in list(collecting_humans):
            if not collectable:
                break
            place = human.knapsack.find_free_place()
            if not place:
                human.room.world.game.set_info_text("No free place in your knapsack.")
                collecting_humans.remove(human)
                continue
            item = collectable.pop(0)
            item.move_to_place(place)
    kill_switches = [entity for entity in entities if entity.name == KILL_PIC]
    if human_players and kill_switches:
        for kill in kill_switches:
            for robot in kill.room.find_entities(ROBOT_PICS):
                robot.kill()
            kill.kill()


def do_robot_action(robot, human):
    """
    :param Entity robot:
    :param Entity human:
    """
    relative = numpy.clip(human.room_coord - robot.room_coord, -1, 1)
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    random.shuffle(dirs)
    dirs = [numpy.array(d) for d in dirs]
    # First try to move in any direction like the human player.
    for d in dirs:
        if not robot.can_move(d):
            continue
        for i in (0, 1):
            if relative[i] and relative[i] == d[i]:
                robot.move(d)
                return
    # Now try to move in any direction.
    for d in dirs:
        if robot.can_move(d):
            robot.move(d)
            return
    # This will fail but show some intention.
    robot.move(dirs[0])


def do_item_action(player, item):
    """
    :param Entity player:
    :param Entity item:
    """
    print("%r do item %r action" % (player, item))
    if item.name == BURN_PIC:
        count = 0
        for entity in player.place.nearby_entities(include_room_borders=False):
            if entity.name in BURNABLE_PICS:
                entity.kill()
                count += 1
        if count > 0:
            item.kill()
        else:
            player.room.world.game.set_info_text("Cannot burn anything here.")
    elif item.name == GET_LIVE_PIC:
        player.lives += 1
        player.room.world.game.set_info_text("You got an extra live.")
        item.kill()
    elif item.name in KEY_PICS:
        player.room.world.game.set_info_text("A key has no action. But you can go through doors.")
    elif item.name in DIAMOND_PICS:
        count = 0
        diamond_idx = DIAMOND_PICS.index(item.name)
        for entity in player.place.nearby_entities(include_room_borders=True):
            if entity.name == CODE_PICS[diamond_idx]:
                count += 1
                entity.kill()
                item.kill()
                player.room.world.diamonds_activated[diamond_idx] = True
                break
        if count:
            rem = len(player.room.world.diamonds_activated) - sum(player.room.world.diamonds_activated)
            if rem > 0:
                player.room.world.game.set_info_text("%i diamonds remaining." % rem)
            else:
                player.room.world.game.set_info_text("You finished it. The king is vulnerable.")
                player.room.world.set_king_vulnerable()
        else:
            player.room.world.game.set_info_text("The diamond can not be used here.")
    else:
        print("no action implemented for item %r" % item.name)


def find_game_file(filename, assert_exists=True):
    """
    :param str filename: e.g. "game.sce"
    :param bool assert_exists:
    :return: full filename, e.g. GAME_DATA_DIR + "/game.sce"
    :rtype: str|None
    """
    for d in GameDataDirs:
        full_fn = "%s/%s" % (d, filename)
        if os.path.exists(full_fn):
            return full_fn
    if assert_exists:
        raise Exception("Did not found game file: %s" % filename)
    return None


def get_unique_game_file(filename):
    """
    :param str filename: eg. "game.spi"
    :return: filename which does not exists in GameDataDirs, e.g. "game.spi" or "game_1.spi" or so
    :rtype: str
    """
    assert "/" not in filename
    base, file_ext = os.path.splitext(filename)
    count = 0
    while True:
        if not count:
            postfix = ""
        else:
            postfix = "_%i" % count
        name = base + postfix + file_ext
        if not find_game_file(name, assert_exists=False):
            return name
        count += 1
