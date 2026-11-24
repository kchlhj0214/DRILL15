import random

from pico2d import *

import game_framework
import game_world
from ball import Ball
from boy import Boy
from grass import Grass
from zombie import Zombie

boy = None


def handle_events():
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit()
            return
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            game_framework.quit()
        else:
            boy.handle_event(event)


def init():
    global boy
    boy = Boy()
    grass = Grass()
    balls = [Ball(random.randint(100, 1700), 60, 0) for _ in range(30)]
    zombies = [Zombie()]
    zombies.extend(Zombie() for _ in range(3))

    game_world.add_oject(boy)
    game_world.add_oject(grass, 0)
    game_world.add_objects(balls, 1)
    game_world.add_objects(zombies, 1)

    game_world.add_collision_pair('boy:zombie', boy, None)
    for zombie in zombies:
        game_world.add_collision_pair('boy:zombie', None, zombie)
        game_world.add_collision_pair('ball:zombie', None, zombie)

    game_world.add_collision_pair('boy:ball', boy, None)
    for ball in balls:
        game_world.add_collision_pair('boy:ball', None, ball)


def pause():
    boy.pause()


def resume():
    pass


def finish():
    global boy
    game_world.clear()
    boy = None


def update():
    game_world.update()
    game_world.handle_collision(lambda: not game_framework.running)


def render():
    clear_canvas()
    game_world.render()
    update_canvas()