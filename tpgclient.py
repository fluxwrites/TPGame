#!/usr/bin/env python3
import pygame
import pygame.locals
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.spread import pb
import locals
import settings


class ClientState(pb.Referenceable):
    state = locals.GAME_READY
    background_color = locals.COLOR_READY

    def __init__(self, factory):
        pb.Referenceable.__init__(self)
        self.factory = factory
        self.update_server()

    def update_server(self):
        def give_client_state(obj, client_state):
            obj.callRemote('takeClientState', client_state)

        d = self.factory.getRootObject()
        d.addCallback(give_client_state, self)

    def remote_setClientState(self, state):
        self.state = state
        if self.state == locals.GAME_READY:
            self.background_color = locals.COLOR_READY
        elif self.state == locals.GAME_PLAY:
            self.background_color = locals.COLOR_PLAY
        elif self.state == locals.GAME_WIN:
            self.background_color = locals.COLOR_WIN
        #self.update_server()


class Engine:
    screen_width = settings.screen_width
    screen_height = settings.screen_height
    screen_size = (screen_width, screen_height)
    keydown_handlers = {}
    keyup_handlers = {}

    def __init__(self, game_state):
        self.game_state = game_state

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
            pygame.display.flip()

        LoopingCall(draw_screen).start(1.0 / 60.0)
        LoopingCall(handle_events).start(1.0 / 120.0)


class Game:
    def start(self, address, port):
        print("Client.")
        pygame.init()
        factory = pb.PBClientFactory()
        engine = Engine(ClientState(factory))

        def send_press_up(obj):
            obj.callRemote('setUpArrow', True)

        @engine.handle_keydown(pygame.locals.K_UP)
        def press_up():
            d = factory.getRootObject()
            d.addCallback(send_press_up)

        def send_release_up(obj):
            obj.callRemote('setUpArrow', False)

        @engine.handle_keyup(pygame.locals.K_UP)
        def release_up():
            d = factory.getRootObject()
            d.addCallback(send_release_up)

        def send_press_down(obj):
            obj.callRemote('setDownArrow', True)

        @engine.handle_keydown(pygame.locals.K_DOWN)
        def press_down():
            d = factory.getRootObject()
            d.addCallback(send_press_down)

        def send_release_down(obj):
            obj.callRemote('setDownArrow', False)

        @engine.handle_keyup(pygame.locals.K_DOWN)
        def release_down():
            d = factory.getRootObject()
            d.addCallback(send_release_down)

        def send_press_left(obj):
            obj.callRemote('setLeftArrow', True)

        @engine.handle_keydown(pygame.locals.K_LEFT)
        def press_left():
            d = factory.getRootObject()
            d.addCallback(send_press_left)

        def send_release_left(obj):
            obj.callRemote('setLeftArrow', False)

        @engine.handle_keyup(pygame.locals.K_LEFT)
        def release_left():
            d = factory.getRootObject()
            d.addCallback(send_release_left)

        def send_press_right(obj):
            obj.callRemote('setRightArrow', True)

        @engine.handle_keydown(pygame.locals.K_RIGHT)
        def press_right():
            d = factory.getRootObject()
            d.addCallback(send_press_right)

        def send_release_right(obj):
            obj.callRemote('setRightArrow', False)

        @engine.handle_keyup(pygame.locals.K_RIGHT)
        def release_right():
            d = factory.getRootObject()
            d.addCallback(send_release_right)

        @engine.handle_keyup(pygame.locals.K_q)
        def stop():
            reactor.stop()

        pygame.display.set_caption('TPG Client')
        engine.start()
        reactor.connectTCP(address, port, factory)
        reactor.run()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("address")
    parser.add_argument("port", type=int)
    args = parser.parse_args()
    game = Game()
    game.start(args.address, args.port)
