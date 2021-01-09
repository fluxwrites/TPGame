#!/usr/bin/env python3
import math
import random
import time
import pygame
import pygame.locals
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.spread import pb
import locals
import settings


class Piece:
    def __init__(self, color, r):
        self.color = color
        self.r = r
        self.x = 0
        self.y = 0
        self.dx = 0
        self.dy = 0
        self.min_x = 0 + self.r
        self.min_y = 0 + self.r
        self.max_x = settings.screen_width - self.r
        self.max_y = settings.screen_height - self.r

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (self.x, self.y), self.r)


class Player(Piece):
    def __init__(self):
        Piece.__init__(self, settings.player_color, settings.player_radius)
        self.x, self.y = self.get_initial_position()

    def get_initial_position(self):
        x = random.randint(self.r, settings.screen_width - self.r)
        y = random.randint(self.r, settings.screen_height - self.r)
        return x, y

    def is_touching(self, piece):
        distance_squ = (self.x - piece.x)**2 + (self.y - piece.y)**2
        touching_squ = (self.r + piece.r)**2
        if distance_squ < touching_squ:
            return True
        else:
            return False

    def move(self, frame_count):
        self.x += frame_count * self.dx
        self.y += frame_count * self.dy
        if self.x > self.max_x:
            self.x = max(
                self.min_x, (self.x - (self.x - self.max_x))
            )
        if self.x < self.min_x:
            self.x = min(self.max_x, (self.min_x + (self.min_x - self.x)))
        if self.y > self.max_y:
            self.y = max(
                self.min_y, (self.y - (self.y - self.max_y))
            )
        if self.y < self.min_y:
            self.y = min(self.max_y, (self.min_y + (self.min_y - self.y)))


class Goal(Piece):
    def __init__(self, player):
        Piece.__init__(self, settings.goal_color, settings.goal_radius)
        self.x, self.y = self.get_initial_position(player)

    def get_initial_position(self, player):
        distance = random.uniform(settings.distance_min, settings.distance_max)
        total_distance = distance + player.r + self.r
        angle = random.uniform(0, 2.0 * math.pi)
        print("distance = ", distance)
        print("angle = ", angle)
        x_distance = int(total_distance * math.cos(angle))
        y_distance = int(total_distance * math.sin(angle))
        x = x_distance + player.x
        y = y_distance + player.y
        print("Initial (x, y):", (x, y))
        print("player x, player y:", (player.x, player.y))
        print("x distance, y distance:", (x_distance, y_distance))
        # Keep the goal piece on the screen.
        if x + self.r > settings.screen_width:
            x = player.x + (x_distance * -1)
        elif x - self.r < 0:
            x = player.x + (x_distance * -1)
        if y + self.r > settings.screen_height:
            y = player.y + (y_distance * -1)
        elif y - self.r < 0:
            y = player.y + (y_distance * -1)
        print("(x, y) = ", (x, y))
        print("new x distance, y distance:", (x - player.x, y - player.y))
        assert abs(x_distance) == abs(x - player.x)
        assert abs(y_distance) == abs(y - player.y)
        return x, y


class Controller(pb.Root):
    def __init__(self, engine):
        self.engine = engine
        self.player = engine.player
        self.up_arrow = False
        self.down_arrow = False
        self.left_arrow = False
        self.right_arrow = False

    def remote_setUpArrow(self, keydown):
        if self.engine.game_state.state == locals.GAME_READY:
            self.engine.game_state.state = locals.GAME_PLAY
        self.up_arrow = keydown
        if self.up_arrow:
            self.player.dy = -1
        elif self.down_arrow:
            self.player.dy = 1
        else:
            self.player.dy = 0
        return self

    def remote_setDownArrow(self, keydown):
        if self.engine.game_state.state == locals.GAME_READY:
            self.engine.game_state.state = locals.GAME_PLAY
        self.down_arrow = keydown
        if self.down_arrow:
            self.player.dy = 1
        elif self.up_arrow:
            self.player.dy = -1
        else:
            self.player.dy = 0
        return self

    def remote_setLeftArrow(self, keydown):
        if self.engine.game_state.state == locals.GAME_READY:
            self.engine.game_state.state = locals.GAME_PLAY
        self.left_arrow = keydown
        if self.left_arrow:
            self.player.dx = -1
        elif self.right_arrow:
            self.player.dx = 1
        else:
            self.player.dx = 0
        return self

    def remote_setRightArrow(self, keydown):
        if self.engine.game_state.state == locals.GAME_READY:
            self.engine.game_state.state = locals.GAME_PLAY
        self.right_arrow = keydown
        if self.right_arrow:
            self.player.dx = 1
        elif self.left_arrow:
            self.player.dx = -1
        else:
            self.player.dx = 0
        return self

    def remote_takeClientState(self, client_state_obj):
        self.engine.game_state.client_state_obj = client_state_obj
        print("ClientState is taken.")


class GameState:
    __state = locals.GAME_READY
    background_color = locals.COLOR_READY
    client_state_obj = None
    time_start = 0.0
    time_end = 0.0

    @property
    def state(self):
        return self.__state

    @state.setter
    def state(self, state):
        self.__state = state
        if state == locals.GAME_READY:
            self.background_color = locals.COLOR_READY
        elif state == locals.GAME_PLAY:
            self.time_start = time.time()
            self.background_color = locals.COLOR_PLAY
        elif state == locals.GAME_WIN:
            self.time_end = time.time()
            print(self.time_end - self.time_start)
            self.background_color = locals.COLOR_WIN
        self.client_state_obj.callRemote('setClientState', state)


class Engine:
    screen_width = settings.screen_width
    screen_height = settings.screen_height
    screen_size = (screen_width, screen_height)
    background_color = locals.COLOR_BLACK
    keydown_handlers = {}
    keyup_handlers = {}
    drawables = []
    client_state_d = None

    def __init__(self):
        self.game_state = GameState()
        self.player = Player()
        self.goal = Goal(self.player)
        self.drawables.append(self.goal)
        self.drawables.append(self.player)

    def handle_keydown(self, key):
        def decorator(decorated):
            self.keydown_handlers[key] = decorated
            return decorated
        return decorator

    def handle_keyup(self, key):
        def decorator(decorated):
            self.keyup_handlers[key] = decorated
            return decorated
        return decorator

    def start(self):
        screen = pygame.display.set_mode(self.screen_size, vsync=1)

        def handle_events():
            if self.game_state.state == locals.GAME_PLAY:
                if self.player.is_touching(self.goal):
                    print("Touching!")
                    self.game_state.state = locals.GAME_WIN
            for event in pygame.event.get():
                if event.type == pygame.locals.KEYDOWN:
                    handler = self.keydown_handlers.get(event.key)
                    if handler:
                        handler()
                elif event.type == pygame.locals.KEYUP:
                    handler = self.keyup_handlers.get(event.key)
                    if handler:
                        handler()

        def draw_screen():
            screen.fill(self.game_state.background_color)
            for drawable in self.drawables:
                drawable.draw(screen)
            pygame.display.flip()

        player_mover = LoopingCall.withCount(self.player.move)
        player_mover.start(1 / 60.0)
        LoopingCall(draw_screen).start(1.0 / 60.0)
        LoopingCall(handle_events).start(1.0 / 120.0)


class Game:
    def start(self, port):
        print("Server.")
        random.seed()
        pygame.init()
        engine = Engine()

        @engine.handle_keyup(pygame.locals.K_q)
        def stop():
            reactor.stop()

        pygame.display.set_caption('TPG Server')
        engine.start()
        reactor.listenTCP(port, pb.PBServerFactory(Controller(engine)))
        reactor.run()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("port", type=int)
    args = parser.parse_args()
    game = Game()
    game.start(args.port)
