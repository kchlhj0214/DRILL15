import runpy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import game_world


class CollisionTest(unittest.TestCase):
    def test_overlap_and_separation(self):
        boy = Mock(get_bb=Mock(return_value=(350, 40, 450, 140)))
        for bounds, expected in (
            ((390, 50, 410, 70), True),
            ((450, 50, 470, 70), True),
            ((451, 50, 471, 70), False),
            ((320, 50, 340, 70), False),
            ((390, 141, 410, 161), False),
            ((390, 10, 410, 30), False),
        ):
            with self.subTest(bounds=bounds):
                ball = Mock(get_bb=Mock(return_value=bounds))
                self.assertIs(game_world.collide(boy, ball), expected)

    def test_pickup_removes_ball_from_world_and_counts_it_once(self):
        root = Path(__file__).parent
        with patch.dict(sys.modules,
                        pico2d=SimpleNamespace(load_image=Mock(), draw_rectangle=Mock(),
                                               get_canvas_width=Mock(return_value=1600)),
                        sdl2=SimpleNamespace(SDL_KEYDOWN=1, SDL_KEYUP=2,
                                             SDLK_LEFT=3, SDLK_RIGHT=4, SDLK_SPACE=5),
                        transitions=SimpleNamespace(Machine=Mock()),
                        game_framework=Mock()):
            ball_class = runpy.run_path(str(root / 'ball.py'))['Ball']
            with patch.dict(sys.modules, ball=SimpleNamespace(Ball=ball_class)):
                boy_class = runpy.run_path(str(root / 'boy.py'))['Boy']
        boy = boy_class.__new__(boy_class)
        boy.x, boy.y, boy.ball_count = 400, 90, 10
        boy.update = Mock()
        with patch.dict(sys.modules, pico2d=SimpleNamespace(),
                        game_framework=Mock(),
                        boy=SimpleNamespace(Boy=Mock(return_value=boy)),
                        ball=SimpleNamespace(Ball=ball_class),
                        grass=SimpleNamespace(Grass=Mock()),
                        zombie=SimpleNamespace(Zombie=Mock())):
            play = runpy.run_path(str(Path(__file__).with_name('play_mode.py')))
        with patch.object(game_world, 'world', [[], [], []]), \
                patch.object(game_world, 'collision_pairs', {}):
            play['init']()
            self.assertEqual(len(game_world.world[1]), 31)
            for ball in game_world.world[1][1:]:
                ball.x, ball.y = 400, 60
            play['update']()
            self.assertEqual(game_world.world[1], [boy])
            self.assertEqual(boy.ball_count, 40)
            play['update']()
            self.assertEqual(boy.ball_count, 40)
            self.assertEqual(game_world.collision_pairs['boy:ball'][1], [])
            play['finish']()
            self.assertEqual(game_world.collision_pairs, {})


if __name__ == '__main__':
    unittest.main()
