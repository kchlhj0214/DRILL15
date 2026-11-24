# LEC17 공으로 좀비 맞히기

현재 `Labs/LEC17_Collision`의 코드에서 이어서 작업하는 10개 커밋입니다. 각 단계에 나온 파일의 **전체 내용**을 해당 파일에 붙여넣고, 단계 제목의 문구를 커밋 메시지로 사용하세요. 한 단계에 파일이 여러 개면 모두 교체한 뒤 한 번에 커밋하고, 다음 단계는 앞선 변경을 적용한 상태에서 진행하세요.

최종 동작은 다음과 같습니다.

- 시작할 때 좀비 한 마리가 등장합니다. `play_mode.py`의 `zombies.extend(...)` 예시 주석을 풀면 좀비가 두 마리 더 등장합니다.
- 방향키로 이동하고 스페이스바로 바라보는 방향에 공을 던집니다. 소년이 잠들어 있으면 스페이스바를 한 번 눌러 깨운 뒤 발사합니다.
- 발사한 공이 좀비에 닿으면 공이 사라집니다. 첫 타격에는 좀비가 절반 크기로 줄어들고, 두 번째 타격에는 좀비가 사라집니다.
- 바닥 공은 소년이 닿으면 주울 수 있습니다. 소년이 좀비에 닿으면 게임이 종료되며, 같은 프레임에 발사한 공도 좀비에 닿았다면 소년과 좀비의 접촉이 우선입니다.

## 01. 충돌 중 제거된 물체를 건너뛰고 종료 시 충돌 목록 비우기

두 바닥 공에 동시에 닿으면 각각 한 번씩 주울 수 있게 합니다. 충돌 목록의 복사본을 순회하면서 실제 목록에서 제거된 물체는 건너뜁니다. 충돌한 한 쌍에는 양쪽 콜백을 모두 호출하므로, 발사한 공이 먼저 사라진 뒤에도 좀비에 같은 충돌을 전달할 수 있습니다. 게임 종료 시에는 월드와 충돌 목록을 함께 비웁니다.

### `game_world.py`

```python
world = [[], [], []]  # 0: 배경, 1: 오브젝트, 2: UI

def add_oject(o, depth=1):
    world[depth].append(o)

def add_objects(ol, depth=1):
    world[depth] += ol

def remove_object(o):
    for layer in world:
        if o in layer:
            layer.remove(o)
            remove_collision_object(o)
            return


def collide(a, b):
    left_a, bottom_a, right_a, top_a = a.get_bb()
    left_b, bottom_b, right_b, top_b = b.get_bb()

    if left_a > right_b: return False
    if right_a < left_b: return False
    if top_a < bottom_b: return False
    if bottom_a > top_b: return False

    return True

collision_pairs = {}

def add_collision_pair(group, a, b):
    if group not in collision_pairs:
        collision_pairs[group] = [[], []]
    if a:
        collision_pairs[group][0].append(a)
    if b:
        collision_pairs[group][1].append(b)

def update():
    for layer in world:
        for o in layer[:]:
            o.update()

def render():
    for layer in world:
        for o in layer[:]:
            o.draw()

def clear():
    for layer in world:
        layer.clear()
    collision_pairs.clear()

# 충돌 목록의 복사본을 순회하고, 제거된 물체는 실제 목록에서 확인한다.
def handle_collision():
    for group, pairs in collision_pairs.items():
        for a in pairs[0][:]:
            for b in pairs[1][:]:
                if a not in pairs[0]:
                    break
                if b not in pairs[1] or not collide(a, b):
                    continue
                a.handle_collision(group, b)
                b.handle_collision(group, a)

def remove_collision_object(o):
    for pairs in collision_pairs.values():
        if o in pairs[0]:
            pairs[0].remove(o)
        if o in pairs[1]:
            pairs[1].remove(o)
```

## 02. 플레이 화면에 좀비 한 마리를 배치하고 추가 생성 예시 남기기

좀비를 오브젝트 레이어에 등록해 기존 이동과 애니메이션을 화면에 표시합니다. 기본값은 한 마리입니다. 바닥 공 테스트는 충돌 그룹에서 바닥 공 30개를 찾고, 모두 주운 뒤에도 좀비가 월드에 있는지 확인합니다.

### `play_mode.py`

```python
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
    # zombies.extend(Zombie() for _ in range(2))  # 좀비 2마리 추가

    game_world.add_oject(boy)
    game_world.add_oject(grass, 0)
    game_world.add_objects(balls, 1)
    game_world.add_objects(zombies, 1)

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
    game_world.handle_collision()


def render():
    clear_canvas()
    game_world.render()
    update_canvas()
```

### `test_collision.py`

```python
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
        zombie = Mock(get_bb=Mock(return_value=(900, 50, 1100, 250)))
        with patch.dict(sys.modules, pico2d=SimpleNamespace(),
                        game_framework=Mock(),
                        boy=SimpleNamespace(Boy=Mock(return_value=boy)),
                        ball=SimpleNamespace(Ball=ball_class),
                        grass=SimpleNamespace(Grass=Mock()),
                        zombie=SimpleNamespace(Zombie=Mock(return_value=zombie))):
            play = runpy.run_path(str(Path(__file__).with_name('play_mode.py')))
        with patch.object(game_world, 'world', [[], [], []]), \
                patch.object(game_world, 'collision_pairs', {}):
            play['init']()
            ground_balls = game_world.collision_pairs['boy:ball'][1][:]
            self.assertEqual(len(ground_balls), 30)
            self.assertEqual(game_world.world[1], [boy, *ground_balls, zombie])
            for ball in ground_balls:
                ball.x, ball.y = 400, 60
            play['update']()
            self.assertEqual(game_world.world[1], [boy, zombie])
            self.assertEqual(boy.ball_count, 40)
            play['update']()
            self.assertEqual(boy.ball_count, 40)
            self.assertEqual(game_world.collision_pairs['boy:ball'][1], [])
            play['finish']()
            self.assertEqual(game_world.collision_pairs, {})


if __name__ == '__main__':
    unittest.main()
```

## 03. 작은 공과 큰 공의 충돌 상자를 각 반지름에 맞추기

공의 충돌 상자가 작은 공의 21픽셀 이미지와 큰 공의 41픽셀 이미지 크기를 각각 반영하도록 기존 반지름 값을 사용합니다.

### `ball.py`

```python
from pico2d import draw_rectangle, get_canvas_width, load_image

import game_world
import game_framework

# 단위: 픽셀, 초
LAUNCH_SPEED_X = 300.0
LAUNCH_SPEED_Y = 300.0
GRAVITY = 9.8 * (10.0 / 0.3)  # 9.8 m/s²를 픽셀/s²로 변환
GROUND_Y = 40


class Ball:
    images = {}

    def __init__(self, x, y, direction, ball_type=1):
        if ball_type not in Ball.images:
            Ball.images[ball_type] = load_image(
                'ball21x21.png' if ball_type == 1 else 'ball41x41.png')
        self.image = Ball.images[ball_type]
        self.x, self.y = x, y
        self.velocity_x = direction * LAUNCH_SPEED_X
        self.velocity_y = LAUNCH_SPEED_Y
        self.radius = 10.5 if ball_type == 1 else 20.5
        self.stopped = (direction == 0)  # direction 이 0이면 바닥에 놓인 공

    def update(self):
        if self.stopped:
            return
        dt = game_framework.frame_time
        self.x += self.velocity_x * dt
        self.y += self.velocity_y * dt - 0.5 * GRAVITY * dt ** 2
        self.velocity_y -= GRAVITY * dt
        if (self.x < -self.radius or self.x > get_canvas_width() + self.radius
                or self.y - self.radius <= GROUND_Y):
            game_world.remove_object(self)

    def draw(self):
        self.image.draw(self.x, self.y)
        draw_rectangle(*self.get_bb())

    def get_bb(self):
        return (self.x - self.radius, self.y - self.radius,
                self.x + self.radius, self.y + self.radius)

    def handle_collision(self, group, other):
            #충돌 그룹 이름이 "boy:ball"이면, 소년이 공과 충돌한 경우이다.
            if group == "boy:ball":
                #소년이 공과 충돌했을때의 처리
                game_world.remove_object(self)
```

## 04. 좀비의 그림과 충돌 상자를 같은 크기로 계산하고 바닥 높이 고정

좀비의 표시 크기와 충돌 상자가 같은 값을 사용하게 합니다. 충돌 상자의 밑변은 기존 높이인 y=50에 고정하고, 크기가 바뀌면 그림의 중심도 함께 옮겨 밑변이 들리지 않게 합니다.

### `zombie.py`

```python
import random

from pico2d import load_image, draw_rectangle, clamp

import game_framework
import game_world

# 좀비 달리기 속력: km/h -> 픽셀/초
PIXEL_PER_METER = (10.0 / 0.3)  # 10 pixel 30 cm
RUN_SPEED_KMPH = 10.0  # Km / Hour
RUN_SPEED_MPM = (RUN_SPEED_KMPH * 1000.0 / 60.0)
RUN_SPEED_MPS = (RUN_SPEED_MPM / 60.0)
RUN_SPEED_PPS = (RUN_SPEED_MPS * PIXEL_PER_METER)

# 좀비 애니메이션 속도: 0.5초에 10프레임
TIME_PER_ACTION = 0.5
ACTION_PER_TIME = 1.0 / TIME_PER_ACTION
FRAMES_PER_ACTION = 10

MIN_X, MAX_X = 800, 1600  # 좀비가 오가는 구간
START_SIZE = 200
FEET_Y = 50


class Zombie:
    images = None

    def load_images(self):
        if Zombie.images is None:
            Zombie.images = {
                'Walk': [load_image(f'./zombie/Walk ({i}).png') for i in range(1, 11)]
            }

    def __init__(self):
        self.load_images()
        self.x = random.randint(MIN_X, MAX_X)
        self.size = START_SIZE
        self.frame = random.randint(0, 9)
        self.dir = random.choice([-1, 1])

    def update(self):
        dt = game_framework.frame_time
        self.frame = (self.frame + FRAMES_PER_ACTION * ACTION_PER_TIME * dt) % FRAMES_PER_ACTION
        self.x += self.dir * RUN_SPEED_PPS * dt
        if self.x > MAX_X:
            self.dir = -1
        elif self.x < MIN_X:
            self.dir = 1
        self.x = clamp(MIN_X, self.x, MAX_X)

    @property
    def y(self):
        return FEET_Y + self.size / 2

    def draw(self):
        image = Zombie.images['Walk'][int(self.frame)]
        if self.dir < 0:
            image.composite_draw(0, 'h', self.x, self.y, self.size, self.size)
        else:
            image.draw(self.x, self.y, self.size, self.size)
        draw_rectangle(*self.get_bb())

    def get_bb(self):
        half_size = self.size / 2
        return self.x - half_size, FEET_Y, self.x + half_size, FEET_Y + self.size
```

## 05. 발사한 공과 좀비를 연결해 첫 타격에 공을 없애고 좀비를 줄이기

소년이 발사한 공만 `ball:zombie`에 등록합니다. 공이 좀비에 닿으면 공은 월드에서 제거되고, 좀비의 그림과 충돌 상자는 200×200에서 100×100으로 줄어듭니다.

### `boy.py`

```python
from math import pi

from pico2d import *

from sdl2 import (SDL_KEYDOWN, SDL_KEYUP, SDLK_LEFT, SDLK_RIGHT,
                  SDLK_SPACE)
from transitions import Machine

import game_world
from ball import Ball

import game_framework

# 달리기 속력을 시속 km에서 초속 m, 다시 초당 픽셀로 변환한다.
PIXEL_PER_METER = (10.0 / 0.3)  # 10 pixel 30 cm
RUN_SPEED_KMPH = 20.0  # Km / Hour
RUN_SPEED_MPM = (RUN_SPEED_KMPH * 1000.0 / 60.0)
RUN_SPEED_MPS = (RUN_SPEED_MPM / 60.0)
RUN_SPEED_PPS = (RUN_SPEED_MPS * PIXEL_PER_METER)

# 한 보폭은 0.8m이고, 달리기 애니메이션 5프레임이 한 보폭에 해당한다.
# 7km/h = 7000 / 3600 = 약 1.944m/s
# 한 보폭에 걸리는 시간 = 0.8 / 1.944 = 약 0.411초
# 한 프레임의 지속시간 = 0.411 / 5 = 약 0.082초
# 초당 프레임 수 = (초속 / 보폭) * 보폭당 프레임 수 = 약 12.15
STRIDE_LENGTH_M = 1.5  # 보폭 길이
RUN_FRAMES_PER_STRIDE = 5 # 1개 보폭에 대한 애니메이션 프레임 수
RUN_FRAMES_PER_SECOND = RUN_SPEED_MPS / STRIDE_LENGTH_M * RUN_FRAMES_PER_STRIDE # 프레임 증가 속도, 즉 1초당 몇개 프레임을 증가시켜야 하는가?





class Idle:
    def enter(self, boy):
        boy.idle_started_at = get_time()
        boy.frame = 0

    def do(self, boy):
        if get_time() - boy.idle_started_at >= 5.0:
            boy.fall_asleep()
        else:
            boy.frame = (boy.frame + 1) % 8

    def draw(self, boy):
        row = 300 if boy.face_dir == 1 else 200
        boy.image.clip_draw(boy.frame * 100, row, 100, 100, boy.x, boy.y)

    def space(self, boy):
        boy.fire_ball()

    def move(self, boy):
        boy.start_run()


class Sleep:
    def enter(self, boy):
        boy.frame = 0

    def do(self, boy):
        pass

    def draw(self, boy):
        angle = pi / 2 if boy.face_dir == 1 else -pi / 2
        flip = '' if boy.face_dir == 1 else 'h'
        boy.image.clip_composite_draw(
            boy.frame * 100, 300, 100, 100,
            angle, flip, boy.x, boy.y - 30, 100, 100
        )

    def space(self, boy):
        boy.wake_up()

    def move(self, boy):
        boy.start_run()


class Run:
    def enter(self, boy):
        boy.frame = 0

    def do(self, boy):
        boy.frame = (boy.frame + RUN_FRAMES_PER_SECOND * game_framework.frame_time) % 8
        boy.x += boy.dir * RUN_SPEED_PPS * game_framework.frame_time
        boy.x = max(25, min(get_canvas_width() - 25, boy.x))

    def draw(self, boy):
        row = 100 if boy.face_dir == 1 else 0
        # 그림을 선택할 때만 소수 부분을 버린다.
        boy.image.clip_draw(int(boy.frame) * 100, row, 100, 100, boy.x, boy.y)

    def space(self, boy):
        boy.fire_ball()

    def move(self, boy):
        pass


class Boy:
    def __init__(self):
        self.font = load_font('ENCR10B.TTF', 16)
        self.x, self.y = 400, 90
        self.frame = 0
        self.image = load_image('animation_sheet.png')
        self.idle_started_at = get_time()
        self.dir = 0
        self.face_dir = 1
        self.pressed_keys = set()
        self.item = 'Ball'
        self.ball_count = 10  # 가지고 있는 공의 개수

        self.states = {'IDLE': Idle(), 'SLEEP': Sleep(), 'RUN': Run()}

        self.machine = Machine(
            model=self,
            states=['IDLE', 'SLEEP', 'RUN'],
            transitions=[
                {'trigger': 'fall_asleep',
                 'source': 'IDLE', 'dest': 'SLEEP'},
                {'trigger': 'wake_up',
                 'source': 'SLEEP', 'dest': 'IDLE'},
                {'trigger': 'start_run',
                 'source': ['IDLE', 'SLEEP'], 'dest': 'RUN'},
                {'trigger': 'stop_run',
                 'source': 'RUN', 'dest': 'IDLE'},
            ],
            initial='IDLE',
            auto_transitions=False,
        )

    def on_enter_IDLE(self):
        self.states['IDLE'].enter(self)

    def on_enter_SLEEP(self):
        self.states['SLEEP'].enter(self)

    def on_enter_RUN(self):
        self.states['RUN'].enter(self)

    def fire_ball(self):
        if self.item is None or self.ball_count <= 0:
            return
        self.ball_count -= 1
        ball = Ball(self.x + self.face_dir * 40, self.y + 60, self.face_dir,
                    1 if self.item == 'Ball' else 2)
        game_world.add_oject(ball)
        game_world.add_collision_pair('ball:zombie', ball, None)

    def pause(self):
        self.pressed_keys.clear()
        if self.state == 'RUN':
            self.dir = 0
            self.stop_run()

    def handle_event(self, event):
        if event.type == SDL_KEYDOWN and event.key == SDLK_SPACE:
            self.states[self.state].space(self)
            return

        if (event.type not in (SDL_KEYDOWN, SDL_KEYUP) or
                event.key not in (SDLK_LEFT, SDLK_RIGHT)):
            return

        if event.type == SDL_KEYDOWN:
            self.pressed_keys.add(event.key)
        else:
            self.pressed_keys.discard(event.key)

        direction = (int(SDLK_RIGHT in self.pressed_keys) -
                     int(SDLK_LEFT in self.pressed_keys))

        if direction != 0:
            self.dir = direction
            self.face_dir = direction
            self.states[self.state].move(self)
        elif self.state == 'RUN':
            self.dir = 0
            self.stop_run()

    def update(self):
        self.states[self.state].do(self)

    def draw(self):
        self.states[self.state].draw(self)
        self.font.draw(self.x - 10, self.y + 50, f'{self.ball_count:02d}', (255, 255, 0))
        draw_rectangle(*self.get_bb())

#소년의 충돌 영역을 계산하여 Bounding Box 리턴.
    def get_bb(self):
        return self.x - 20, self.y - 50, self.x + 20, self.y + 50

    def handle_collision(self, group, other):
        #충돌 그룹 이름이 "boy:ball"이면, 소년이 공과 충돌한 경우이다.
        if group == "boy:ball":
            #소년이 공과 충돌했을때의 처리
            self.ball_count += 1
```

### `play_mode.py`

```python
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
    # zombies.extend(Zombie() for _ in range(2))  # 좀비 2마리 추가

    game_world.add_oject(boy)
    game_world.add_oject(grass, 0)
    game_world.add_objects(balls, 1)
    game_world.add_objects(zombies, 1)

    for zombie in zombies:
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
    game_world.handle_collision()


def render():
    clear_canvas()
    game_world.render()
    update_canvas()
```

### `ball.py`

```python
from pico2d import draw_rectangle, get_canvas_width, load_image

import game_world
import game_framework

# 단위: 픽셀, 초
LAUNCH_SPEED_X = 300.0
LAUNCH_SPEED_Y = 300.0
GRAVITY = 9.8 * (10.0 / 0.3)  # 9.8 m/s²를 픽셀/s²로 변환
GROUND_Y = 40


class Ball:
    images = {}

    def __init__(self, x, y, direction, ball_type=1):
        if ball_type not in Ball.images:
            Ball.images[ball_type] = load_image(
                'ball21x21.png' if ball_type == 1 else 'ball41x41.png')
        self.image = Ball.images[ball_type]
        self.x, self.y = x, y
        self.velocity_x = direction * LAUNCH_SPEED_X
        self.velocity_y = LAUNCH_SPEED_Y
        self.radius = 10.5 if ball_type == 1 else 20.5
        self.stopped = (direction == 0)  # direction 이 0이면 바닥에 놓인 공

    def update(self):
        if self.stopped:
            return
        dt = game_framework.frame_time
        self.x += self.velocity_x * dt
        self.y += self.velocity_y * dt - 0.5 * GRAVITY * dt ** 2
        self.velocity_y -= GRAVITY * dt
        if (self.x < -self.radius or self.x > get_canvas_width() + self.radius
                or self.y - self.radius <= GROUND_Y):
            game_world.remove_object(self)

    def draw(self):
        self.image.draw(self.x, self.y)
        draw_rectangle(*self.get_bb())

    def get_bb(self):
        return (self.x - self.radius, self.y - self.radius,
                self.x + self.radius, self.y + self.radius)

    def handle_collision(self, group, other):
        if group in ('boy:ball', 'ball:zombie'):
            game_world.remove_object(self)
```

### `zombie.py`

```python
import random

from pico2d import load_image, draw_rectangle, clamp

import game_framework
import game_world

# 좀비 달리기 속력: km/h -> 픽셀/초
PIXEL_PER_METER = (10.0 / 0.3)  # 10 pixel 30 cm
RUN_SPEED_KMPH = 10.0  # Km / Hour
RUN_SPEED_MPM = (RUN_SPEED_KMPH * 1000.0 / 60.0)
RUN_SPEED_MPS = (RUN_SPEED_MPM / 60.0)
RUN_SPEED_PPS = (RUN_SPEED_MPS * PIXEL_PER_METER)

# 좀비 애니메이션 속도: 0.5초에 10프레임
TIME_PER_ACTION = 0.5
ACTION_PER_TIME = 1.0 / TIME_PER_ACTION
FRAMES_PER_ACTION = 10

MIN_X, MAX_X = 800, 1600  # 좀비가 오가는 구간
START_SIZE = 200
HIT_SIZE = 100
FEET_Y = 50


class Zombie:
    images = None

    def load_images(self):
        if Zombie.images is None:
            Zombie.images = {
                'Walk': [load_image(f'./zombie/Walk ({i}).png') for i in range(1, 11)]
            }

    def __init__(self):
        self.load_images()
        self.x = random.randint(MIN_X, MAX_X)
        self.size = START_SIZE
        self.frame = random.randint(0, 9)
        self.dir = random.choice([-1, 1])

    def update(self):
        dt = game_framework.frame_time
        self.frame = (self.frame + FRAMES_PER_ACTION * ACTION_PER_TIME * dt) % FRAMES_PER_ACTION
        self.x += self.dir * RUN_SPEED_PPS * dt
        if self.x > MAX_X:
            self.dir = -1
        elif self.x < MIN_X:
            self.dir = 1
        self.x = clamp(MIN_X, self.x, MAX_X)

    @property
    def y(self):
        return FEET_Y + self.size / 2

    def draw(self):
        image = Zombie.images['Walk'][int(self.frame)]
        if self.dir < 0:
            image.composite_draw(0, 'h', self.x, self.y, self.size, self.size)
        else:
            image.draw(self.x, self.y, self.size, self.size)
        draw_rectangle(*self.get_bb())

    def get_bb(self):
        half_size = self.size / 2
        return self.x - half_size, FEET_Y, self.x + half_size, FEET_Y + self.size

    def handle_collision(self, group, other):
        if group == 'ball:zombie':
            self.size = HIT_SIZE
```

## 06. 좀비별 피격 횟수를 세어 두 번째 타격에 제거

좀비마다 맞은 횟수를 기록합니다. 두 번째 공이 닿으면 그 공과 좀비가 월드 및 충돌 등록에서 빠집니다. 좀비를 여러 마리 배치해도 피격 횟수는 개별적으로 계산됩니다.

### `zombie.py`

```python
import random

from pico2d import load_image, draw_rectangle, clamp

import game_framework
import game_world

# 좀비 달리기 속력: km/h -> 픽셀/초
PIXEL_PER_METER = (10.0 / 0.3)  # 10 pixel 30 cm
RUN_SPEED_KMPH = 10.0  # Km / Hour
RUN_SPEED_MPM = (RUN_SPEED_KMPH * 1000.0 / 60.0)
RUN_SPEED_MPS = (RUN_SPEED_MPM / 60.0)
RUN_SPEED_PPS = (RUN_SPEED_MPS * PIXEL_PER_METER)

# 좀비 애니메이션 속도: 0.5초에 10프레임
TIME_PER_ACTION = 0.5
ACTION_PER_TIME = 1.0 / TIME_PER_ACTION
FRAMES_PER_ACTION = 10

MIN_X, MAX_X = 800, 1600  # 좀비가 오가는 구간
START_SIZE = 200
HIT_SIZE = 100
FEET_Y = 50


class Zombie:
    images = None

    def load_images(self):
        if Zombie.images is None:
            Zombie.images = {
                'Walk': [load_image(f'./zombie/Walk ({i}).png') for i in range(1, 11)]
            }

    def __init__(self):
        self.load_images()
        self.x = random.randint(MIN_X, MAX_X)
        self.size = START_SIZE
        self.hits = 0
        self.frame = random.randint(0, 9)
        self.dir = random.choice([-1, 1])

    def update(self):
        dt = game_framework.frame_time
        self.frame = (self.frame + FRAMES_PER_ACTION * ACTION_PER_TIME * dt) % FRAMES_PER_ACTION
        self.x += self.dir * RUN_SPEED_PPS * dt
        if self.x > MAX_X:
            self.dir = -1
        elif self.x < MIN_X:
            self.dir = 1
        self.x = clamp(MIN_X, self.x, MAX_X)

    @property
    def y(self):
        return FEET_Y + self.size / 2

    def draw(self):
        image = Zombie.images['Walk'][int(self.frame)]
        if self.dir < 0:
            image.composite_draw(0, 'h', self.x, self.y, self.size, self.size)
        else:
            image.draw(self.x, self.y, self.size, self.size)
        draw_rectangle(*self.get_bb())

    def get_bb(self):
        half_size = self.size / 2
        return self.x - half_size, FEET_Y, self.x + half_size, FEET_Y + self.size

    def handle_collision(self, group, other):
        if group != 'ball:zombie':
            return
        self.hits += 1
        if self.hits == 1:
            self.size = HIT_SIZE
        else:
            game_world.remove_object(self)
```

## 07. 소년이 좀비에 닿으면 게임 종료 요청

`boy:zombie` 그룹을 추가하고 소년이 좀비와 충돌하면 기존의 `game_framework.quit()`을 호출합니다. 같은 프레임에 소년과 발사한 공이 모두 좀비에 닿을 경우에는 소년과 좀비의 접촉을 먼저 검사합니다.

### `boy.py`

```python
from math import pi

from pico2d import *

from sdl2 import (SDL_KEYDOWN, SDL_KEYUP, SDLK_LEFT, SDLK_RIGHT,
                  SDLK_SPACE)
from transitions import Machine

import game_world
from ball import Ball

import game_framework

# 달리기 속력을 시속 km에서 초속 m, 다시 초당 픽셀로 변환한다.
PIXEL_PER_METER = (10.0 / 0.3)  # 10 pixel 30 cm
RUN_SPEED_KMPH = 20.0  # Km / Hour
RUN_SPEED_MPM = (RUN_SPEED_KMPH * 1000.0 / 60.0)
RUN_SPEED_MPS = (RUN_SPEED_MPM / 60.0)
RUN_SPEED_PPS = (RUN_SPEED_MPS * PIXEL_PER_METER)

# 한 보폭은 0.8m이고, 달리기 애니메이션 5프레임이 한 보폭에 해당한다.
# 7km/h = 7000 / 3600 = 약 1.944m/s
# 한 보폭에 걸리는 시간 = 0.8 / 1.944 = 약 0.411초
# 한 프레임의 지속시간 = 0.411 / 5 = 약 0.082초
# 초당 프레임 수 = (초속 / 보폭) * 보폭당 프레임 수 = 약 12.15
STRIDE_LENGTH_M = 1.5  # 보폭 길이
RUN_FRAMES_PER_STRIDE = 5 # 1개 보폭에 대한 애니메이션 프레임 수
RUN_FRAMES_PER_SECOND = RUN_SPEED_MPS / STRIDE_LENGTH_M * RUN_FRAMES_PER_STRIDE # 프레임 증가 속도, 즉 1초당 몇개 프레임을 증가시켜야 하는가?





class Idle:
    def enter(self, boy):
        boy.idle_started_at = get_time()
        boy.frame = 0

    def do(self, boy):
        if get_time() - boy.idle_started_at >= 5.0:
            boy.fall_asleep()
        else:
            boy.frame = (boy.frame + 1) % 8

    def draw(self, boy):
        row = 300 if boy.face_dir == 1 else 200
        boy.image.clip_draw(boy.frame * 100, row, 100, 100, boy.x, boy.y)

    def space(self, boy):
        boy.fire_ball()

    def move(self, boy):
        boy.start_run()


class Sleep:
    def enter(self, boy):
        boy.frame = 0

    def do(self, boy):
        pass

    def draw(self, boy):
        angle = pi / 2 if boy.face_dir == 1 else -pi / 2
        flip = '' if boy.face_dir == 1 else 'h'
        boy.image.clip_composite_draw(
            boy.frame * 100, 300, 100, 100,
            angle, flip, boy.x, boy.y - 30, 100, 100
        )

    def space(self, boy):
        boy.wake_up()

    def move(self, boy):
        boy.start_run()


class Run:
    def enter(self, boy):
        boy.frame = 0

    def do(self, boy):
        boy.frame = (boy.frame + RUN_FRAMES_PER_SECOND * game_framework.frame_time) % 8
        boy.x += boy.dir * RUN_SPEED_PPS * game_framework.frame_time
        boy.x = max(25, min(get_canvas_width() - 25, boy.x))

    def draw(self, boy):
        row = 100 if boy.face_dir == 1 else 0
        # 그림을 선택할 때만 소수 부분을 버린다.
        boy.image.clip_draw(int(boy.frame) * 100, row, 100, 100, boy.x, boy.y)

    def space(self, boy):
        boy.fire_ball()

    def move(self, boy):
        pass


class Boy:
    def __init__(self):
        self.font = load_font('ENCR10B.TTF', 16)
        self.x, self.y = 400, 90
        self.frame = 0
        self.image = load_image('animation_sheet.png')
        self.idle_started_at = get_time()
        self.dir = 0
        self.face_dir = 1
        self.pressed_keys = set()
        self.item = 'Ball'
        self.ball_count = 10  # 가지고 있는 공의 개수

        self.states = {'IDLE': Idle(), 'SLEEP': Sleep(), 'RUN': Run()}

        self.machine = Machine(
            model=self,
            states=['IDLE', 'SLEEP', 'RUN'],
            transitions=[
                {'trigger': 'fall_asleep',
                 'source': 'IDLE', 'dest': 'SLEEP'},
                {'trigger': 'wake_up',
                 'source': 'SLEEP', 'dest': 'IDLE'},
                {'trigger': 'start_run',
                 'source': ['IDLE', 'SLEEP'], 'dest': 'RUN'},
                {'trigger': 'stop_run',
                 'source': 'RUN', 'dest': 'IDLE'},
            ],
            initial='IDLE',
            auto_transitions=False,
        )

    def on_enter_IDLE(self):
        self.states['IDLE'].enter(self)

    def on_enter_SLEEP(self):
        self.states['SLEEP'].enter(self)

    def on_enter_RUN(self):
        self.states['RUN'].enter(self)

    def fire_ball(self):
        if self.item is None or self.ball_count <= 0:
            return
        self.ball_count -= 1
        ball = Ball(self.x + self.face_dir * 40, self.y + 60, self.face_dir,
                    1 if self.item == 'Ball' else 2)
        game_world.add_oject(ball)
        game_world.add_collision_pair('ball:zombie', ball, None)

    def pause(self):
        self.pressed_keys.clear()
        if self.state == 'RUN':
            self.dir = 0
            self.stop_run()

    def handle_event(self, event):
        if event.type == SDL_KEYDOWN and event.key == SDLK_SPACE:
            self.states[self.state].space(self)
            return

        if (event.type not in (SDL_KEYDOWN, SDL_KEYUP) or
                event.key not in (SDLK_LEFT, SDLK_RIGHT)):
            return

        if event.type == SDL_KEYDOWN:
            self.pressed_keys.add(event.key)
        else:
            self.pressed_keys.discard(event.key)

        direction = (int(SDLK_RIGHT in self.pressed_keys) -
                     int(SDLK_LEFT in self.pressed_keys))

        if direction != 0:
            self.dir = direction
            self.face_dir = direction
            self.states[self.state].move(self)
        elif self.state == 'RUN':
            self.dir = 0
            self.stop_run()

    def update(self):
        self.states[self.state].do(self)

    def draw(self):
        self.states[self.state].draw(self)
        self.font.draw(self.x - 10, self.y + 50, f'{self.ball_count:02d}', (255, 255, 0))
        draw_rectangle(*self.get_bb())

#소년의 충돌 영역을 계산하여 Bounding Box 리턴.
    def get_bb(self):
        return self.x - 20, self.y - 50, self.x + 20, self.y + 50

    def handle_collision(self, group, other):
        if group == 'boy:ball':
            self.ball_count += 1
        elif group == 'boy:zombie':
            game_framework.quit()
```

### `play_mode.py`

```python
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
    # zombies.extend(Zombie() for _ in range(2))  # 좀비 2마리 추가

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
    game_world.handle_collision()


def render():
    clear_canvas()
    game_world.render()
    update_canvas()
```

## 08. 게임 종료가 요청된 프레임의 남은 업데이트와 그리기 건너뛰기

입력이나 충돌 처리에서 종료를 요청하면 즉시 게임 루프를 빠져나갑니다. 기존 정리 코드가 월드를 비우고 `main.py`가 캔버스를 닫습니다.

### `game_framework.py`

```python
import time
running = False
stack = []


def change_mode(mode):
    if stack:
        stack.pop().finish()
    stack.append(mode)
    mode.init()


def push_mode(mode):
    if stack:
        stack[-1].pause()
    stack.append(mode)
    mode.init()


def pop_mode():
    if stack:
        stack.pop().finish()
    if stack:
        stack[-1].resume()
    else:
        quit()


def quit():
    global running
    running = False


frame_time = 0.0

def run(start_mode):
    global running, stack
    running = True
    stack = [start_mode]
    try:
        start_mode.init()
        global frame_time
        frame_time = 0.0
        current_time = time.time()
        while running:
            stack[-1].handle_events()
            if not running:
                break
            stack[-1].update()
            if not running:
                break
            stack[-1].render()
            frame_time = time.time() - current_time
            frame_rate = 1.0 / frame_time
            current_time += frame_time

    finally:
        while stack:
            stack.pop().finish()
        running = False
```

## 09. 소년이 좀비에 닿은 뒤 같은 프레임의 나머지 충돌 검사 중단

소년과 좀비의 접촉으로 종료가 결정되면 같은 프레임의 남은 공 타격과 공 줍기도 중단합니다. 월드는 플레이 모드에서 전달받은 종료 조건으로 다음 충돌을 검사할지 결정합니다.

### `game_world.py`

```python
world = [[], [], []]  # 0: 배경, 1: 오브젝트, 2: UI

def add_oject(o, depth=1):
    world[depth].append(o)

def add_objects(ol, depth=1):
    world[depth] += ol

def remove_object(o):
    for layer in world:
        if o in layer:
            layer.remove(o)
            remove_collision_object(o)
            return


def collide(a, b):
    left_a, bottom_a, right_a, top_a = a.get_bb()
    left_b, bottom_b, right_b, top_b = b.get_bb()

    if left_a > right_b: return False
    if right_a < left_b: return False
    if top_a < bottom_b: return False
    if bottom_a > top_b: return False

    return True

collision_pairs = {}

def add_collision_pair(group, a, b):
    if group not in collision_pairs:
        collision_pairs[group] = [[], []]
    if a:
        collision_pairs[group][0].append(a)
    if b:
        collision_pairs[group][1].append(b)

def update():
    for layer in world:
        for o in layer[:]:
            o.update()

def render():
    for layer in world:
        for o in layer[:]:
            o.draw()

def clear():
    for layer in world:
        layer.clear()
    collision_pairs.clear()

# 충돌 목록의 복사본을 순회하고, 제거된 물체는 실제 목록에서 확인한다.
def handle_collision(should_stop=None):
    for group, pairs in collision_pairs.items():
        for a in pairs[0][:]:
            for b in pairs[1][:]:
                if a not in pairs[0]:
                    break
                if b not in pairs[1] or not collide(a, b):
                    continue
                a.handle_collision(group, b)
                b.handle_collision(group, a)
                if should_stop is not None and should_stop():
                    return

def remove_collision_object(o):
    for pairs in collision_pairs.values():
        if o in pairs[0]:
            pairs[0].remove(o)
        if o in pairs[1]:
            pairs[1].remove(o)
```

### `play_mode.py`

```python
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
    # zombies.extend(Zombie() for _ in range(2))  # 좀비 2마리 추가

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
```

## 10. 바닥 공 줍기와 좀비 두 번 타격, 접촉 종료를 테스트로 검증

화면 라이브러리를 대체해 바닥 공과 발사한 공의 구분, 연속 피격과 같은 프레임의 두 번 피격, 공 한 개당 한 마리만 피격되는지, 접촉 이후 프레임 종료를 자동으로 확인합니다.

### `test_collision.py`

```python
import importlib
import runpy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import game_framework
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
        zombie = Mock(get_bb=Mock(return_value=(900, 50, 1100, 250)))
        with patch.dict(sys.modules, pico2d=SimpleNamespace(),
                        game_framework=Mock(),
                        boy=SimpleNamespace(Boy=Mock(return_value=boy)),
                        ball=SimpleNamespace(Ball=ball_class),
                        grass=SimpleNamespace(Grass=Mock()),
                        zombie=SimpleNamespace(Zombie=Mock(return_value=zombie))):
            play = runpy.run_path(str(Path(__file__).with_name('play_mode.py')))
        with patch.object(game_world, 'world', [[], [], []]), \
                patch.object(game_world, 'collision_pairs', {}):
            play['init']()
            ground_balls = game_world.collision_pairs['boy:ball'][1][:]
            self.assertEqual(len(ground_balls), 30)
            self.assertEqual(game_world.world[1], [boy, *ground_balls, zombie])
            for ball in ground_balls:
                ball.x, ball.y = 400, 60
            play['update']()
            self.assertEqual(game_world.world[1], [boy, zombie])
            self.assertEqual(boy.ball_count, 40)
            play['update']()
            self.assertEqual(boy.ball_count, 40)
            self.assertEqual(game_world.collision_pairs['boy:ball'][1], [])
            play['finish']()
            self.assertEqual(game_world.collision_pairs, {})


class ZombieCollisionTest(unittest.TestCase):
    def setUp(self):
        pico2d = SimpleNamespace(
            clamp=lambda low, value, high: max(low, min(value, high)),
            draw_rectangle=Mock(),
            get_canvas_width=Mock(return_value=1600),
            get_time=Mock(return_value=0.0),
            load_font=Mock(),
            load_image=Mock(),
        )
        sdl2 = SimpleNamespace(
            SDL_KEYDOWN=1, SDL_KEYUP=2, SDLK_LEFT=3, SDLK_RIGHT=4, SDLK_SPACE=5,
        )
        with patch.dict(sys.modules, pico2d=pico2d, sdl2=sdl2,
                        transitions=SimpleNamespace(Machine=Mock())):
            self.play = importlib.import_module('play_mode')

        patches = (
            patch.object(game_world, 'world', [[], [], []]),
            patch.object(game_world, 'collision_pairs', {}),
            patch.object(game_framework, 'running', True),
            patch.object(game_framework, 'frame_time', 0.0),
        )
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

        self.play.init()
        self.addCleanup(self.play.finish)
        self.play.boy.state = 'IDLE'
        self.ground_balls = game_world.collision_pairs['boy:ball'][1]
        for ball in self.ground_balls:
            ball.x = 100
        self.zombies = game_world.collision_pairs['ball:zombie'][1]
        self.assertEqual(len(self.zombies), 1)
        self.zombie = self.zombies[0]
        self.zombie.x = 1000

    def fire_at_zombie(self):
        self.play.boy.fire_ball()
        ball = game_world.collision_pairs['ball:zombie'][0][-1]
        ball.x, ball.y = self.zombie.x, 110
        return ball

    def test_ground_ball_does_not_damage_zombie(self):
        ball = self.ground_balls[0]
        ball.x = self.zombie.x
        self.play.update()
        self.assertEqual(self.zombie.hits, 0)
        self.assertIn(ball, game_world.world[1])

    def test_first_shot_shrinks_zombie_and_second_shot_removes_it(self):
        initial_box = self.zombie.get_bb()
        first_ball = self.fire_at_zombie()
        self.play.update()
        self.assertNotIn(first_ball, game_world.world[1])
        self.assertEqual(game_world.collision_pairs['ball:zombie'][0], [])
        self.assertIn(self.zombie, game_world.world[1])
        self.assertEqual(self.zombie.hits, 1)
        left, bottom, right, top = self.zombie.get_bb()
        self.assertEqual((right - left, top - bottom), (100, 100))
        self.assertEqual(bottom, initial_box[1])

        second_ball = self.fire_at_zombie()
        self.play.update()
        self.assertNotIn(second_ball, game_world.world[1])
        self.assertNotIn(self.zombie, game_world.world[1])
        self.assertEqual(self.zombie.hits, 2)
        self.assertEqual(game_world.collision_pairs['ball:zombie'], [[], []])
        self.assertEqual(game_world.collision_pairs['boy:zombie'][1], [])
        self.assertTrue(game_framework.running)

    def test_two_projectiles_hit_in_one_frame(self):
        balls = [self.fire_at_zombie(), self.fire_at_zombie()]
        self.play.update()
        for ball in balls:
            self.assertNotIn(ball, game_world.world[1])
        self.assertEqual(self.zombie.hits, 2)
        self.assertNotIn(self.zombie, game_world.world[1])

    def test_one_projectile_cannot_hit_two_zombies(self):
        other_zombie = self.play.Zombie()
        other_zombie.x = self.zombie.x
        game_world.add_oject(other_zombie)
        game_world.add_collision_pair('ball:zombie', None, other_zombie)

        self.fire_at_zombie()
        self.play.update()
        self.assertEqual(self.zombie.hits, 1)
        self.assertEqual(other_zombie.hits, 0)

    def test_boy_contact_stops_remaining_collisions(self):
        self.fire_at_zombie()
        self.play.boy.x = self.zombie.x
        self.ground_balls[0].x = self.zombie.x
        ball_count = self.play.boy.ball_count

        self.play.update()
        self.assertFalse(game_framework.running)
        self.assertEqual(self.zombie.hits, 0)
        self.assertEqual(self.play.boy.ball_count, ball_count)


class GameFrameworkTest(unittest.TestCase):
    def test_quit_during_update_skips_render_and_finishes_mode(self):
        mode = Mock()
        mode.update.side_effect = game_framework.quit
        game_framework.run(mode)
        mode.update.assert_called_once()
        mode.render.assert_not_called()
        mode.finish.assert_called_once()
        self.assertFalse(game_framework.running)


if __name__ == '__main__':
    unittest.main()
```

## 적용 확인

LEC17 폴더에서 아래 명령을 실행하세요.

```powershell
python -m unittest -v test_collision
python main.py
```

게임을 켠 뒤 공을 던져 공이 사라지고 좀비가 작아지는지 확인하세요. 작아진 좀비에 두 번째 공을 맞혀 좀비가 사라지는지 확인하세요. 다시 실행한 뒤 이번에는 좀비에게 다가가 게임 창이 닫히는지 확인하세요.
