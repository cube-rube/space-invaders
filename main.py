import sys
import time
import typing
from pathlib import Path
from enum import Enum
import json
import random
from random import randint
import functools
import os

import pygame
from pygame_ecs import Entity
from pygame_ecs.components.base_component import BaseComponent
from pygame_ecs.managers.component_manager import ComponentInstanceType, ComponentManager
from pygame_ecs.managers.entity_manager import EntityManager
from pygame_ecs.managers.system_manager import SystemManager
from pygame_ecs.systems.base_system import BaseSystem

SCALE = 4
SCREEN_SIZE = (224, 192)
FPS = 0
VOLUME = 0.05
DRAW_BOUNDING_BOXES = False
PLAYER_SPEED = 1 * SCALE
SCORE = 0


class GameScene(Enum):
    MENU = 0
    GAME = 1
    GAME_OVER = 2
    DEATH = 3


GAME_SCENE = GameScene.MENU


def cut_sheet(image: pygame.Surface, rows: int, columns: int) -> tuple[pygame.Rect, list[pygame.Surface]]:
    rect = pygame.Rect(0, 0, image.get_width() // columns, image.get_height() // rows)
    frames = []
    for j in range(rows):
        for i in range(columns):
            frame_location = (rect.w * i, rect.h * j)
            frames.append(image.subsurface(pygame.Rect(frame_location, rect.size)))

    return frames[0].get_bounding_rect(), frames


def load_image_sheet(path: str) -> tuple[pygame.Rect, list[pygame.Surface], Enum]:
    with (open(Path(__file__).parent / (path + "/data.json"), encoding="utf-8") as json_file,
          open(Path(__file__).parent / (path + "/image.png"), encoding="utf-8") as image_file):
        data = json.load(json_file)
        image = pygame.transform.scale_by(pygame.image.load(image_file), SCALE)
        rect, frames = cut_sheet(image, data['rows'], data['columns'])
        states = Enum("AnimationState", data['states'])
        return rect, frames, states


def load_file(path: str) -> Path:
    abs_path = Path(__file__).parent / path
    if not abs_path.is_file():
        raise FileNotFoundError()
    return abs_path


def load_image(path: str) -> tuple[pygame.surface.Surface]:
    return pygame.transform.scale_by(pygame.image.load(load_file(path)), SCALE),


def cls():
    os.system('cls' if os.name == 'nt' else 'clear')


# ------------------------------------------------------------
# COMPONENTS
# ------------------------------------------------------------


class Image(BaseComponent):
    def __init__(self, image: pygame.Surface):
        super().__init__()
        self.image: pygame.Surface = image


class PlayerControlled(BaseComponent):
    pass


class Direction(Enum):
    NORTH = 1
    EAST = 2
    SOUTH = 3
    WEST = 4


class ShootOnEvent(BaseComponent):
    def __init__(self, event: tuple, direction: Direction,
                 sprites: tuple[str, ...], cooldown: int = 50, projectile_speed: float = (7 / 4)):
        super().__init__()
        self.event = event
        self.direction = direction
        self.sprites = sprites
        self.cooldown_timer = 0
        self.cooldown = cooldown
        self.projectile_speed = projectile_speed


class AnimatedSprite(BaseComponent):
    def __init__(self, frames: list[pygame.Surface], states: Enum, cur_frame=0):
        super().__init__()
        self.frames = frames
        self.cur_frame = cur_frame
        self.states = states
        self.state: dict = self.states.IDLE.value
        self.cur_delay: float = 0


class BoundingBox(BaseComponent):
    def __init__(self, rect: pygame.Rect):
        super().__init__()
        self.rect = rect
        self.x: float = rect.x
        self.y: float = rect.y


class Health(BaseComponent):
    def __init__(self, health: int):
        super().__init__()
        self.health = health


class Velocity(BaseComponent):
    def __init__(self, vector: tuple[float, float] = (0.0, 0.0)):
        super().__init__()
        self.vector = pygame.Vector2(vector)


class DamageOnContact(BaseComponent):
    def __init__(self, parent: str, damage: int = 1):
        super().__init__()
        self.parent = parent
        self.damage = damage


class StepMovement(BaseComponent):
    def __init__(self):
        super().__init__()
        self.freq = 55
        self.delay = self.freq
        self.step_count = 8
        self.direction = 1


class GameOverOnDeath(BaseComponent):
    def __init__(self):
        super().__init__()
        self.delay = 80


EVENT_LIST: list[pygame.event.Event] = []
ENTITY_LIST: list[Entity] = []
ENEMY_RECT_LIST: list[tuple[pygame.rect.Rect, Entity]] = []
PLAYER_RECT_HEALTH: tuple[pygame.rect.Rect, Health] | None = None
ENTITY_SPAWN_QUEUE: list[list[BaseComponent]] = []
ENTITY_KILL_QUEUE: list[Entity] = []
SYSTEM_PERF: dict[str: float] = dict()

ENEMY_SHOOT = pygame.USEREVENT + 1


# ------------------------------------------------------------
# SYSTEMS
# ------------------------------------------------------------


def system_performance(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        d = time.perf_counter()

        result = func(*args, **kwargs)

        performance = time.perf_counter() - d
        class_name = type(args[0]).__name__
        if class_name not in SYSTEM_PERF:
            SYSTEM_PERF[class_name] = 0
        SYSTEM_PERF[class_name] += performance

        return result

    return wrapper


def increment_delay(cur_delay: float, state: dict, clock: pygame.time.Clock) -> float | None:
    delay: int = state['delay']
    looping: bool = state['looping']

    if delay is None:
        return -1
    if not looping and cur_delay < 0:
        return -1
    cur_delay -= 1 / 12 * clock.get_time()
    return cur_delay


class SpriteDraw(BaseSystem):
    def __init__(self, screen: pygame.Surface, clock: pygame.time.Clock):
        super().__init__(required_component_types=[AnimatedSprite, BoundingBox])
        self.screen = screen
        self.clock = clock

    def update_entity(
            self,
            entity: Entity,
            entity_components: dict[typing.Type[BaseComponent], ComponentInstanceType],
    ):
        sprite: AnimatedSprite = entity_components[AnimatedSprite]
        bounding_box: BoundingBox = entity_components[BoundingBox]

        frame_index = sprite.state['frames'][sprite.cur_frame]
        frame = sprite.frames[frame_index]

        rect = frame.get_rect()
        rect.centerx = bounding_box.rect.centerx
        rect.centery = bounding_box.rect.centery

        if DRAW_BOUNDING_BOXES:
            pygame.draw.rect(self.screen, 'blue', bounding_box.rect, 2)
        self.screen.blit(frame, rect)
        if DRAW_BOUNDING_BOXES:
            pygame.draw.rect(self.screen, 'red', rect, 2)

        if sprite.cur_delay <= 0:
            sprite.cur_frame = (sprite.cur_frame + 1) % len(sprite.state['frames'])
            sprite.cur_delay = sprite.state['delay']
        sprite.cur_delay = increment_delay(sprite.cur_delay, sprite.state, self.clock)


class PositionCalculation(BaseSystem):
    def __init__(self, clock: pygame.time.Clock):
        super().__init__(required_component_types=[BoundingBox, Velocity])
        self.clock = clock

    def update_entity(
            self,
            entity: Entity,
            entity_components: dict[typing.Type[BaseComponent], ComponentInstanceType],
    ):
        bounding_box: BoundingBox = entity_components[BoundingBox]
        velocity: Velocity = entity_components[Velocity]

        if not (velocity.vector.x == 0 and velocity.vector.y == 0):
            bounding_box.x += velocity.vector.x / 12 * self.clock.get_time()
            bounding_box.y += velocity.vector.y / 12 * self.clock.get_time()

            if bounding_box.x < 0:
                bounding_box.x = 0
            if bounding_box.x > (SCREEN_SIZE[0]) * SCALE - bounding_box.rect.w:
                bounding_box.x = (SCREEN_SIZE[0]) * SCALE - bounding_box.rect.w
            if bounding_box.y < 0 - bounding_box.rect.h:
                ENTITY_KILL_QUEUE.append(entity)
            if bounding_box.y > (SCREEN_SIZE[1]) * SCALE - bounding_box.rect.h:
                ENTITY_KILL_QUEUE.append(entity)

            bounding_box.rect.x = bounding_box.x
            bounding_box.rect.y = bounding_box.y


class PlayerMovement(BaseSystem):
    def __init__(self):
        super().__init__(required_component_types=[PlayerControlled, Velocity])
        self.direction = [0]

    def update_entity(
            self,
            entity: Entity,
            entity_components: dict[typing.Type[BaseComponent], ComponentInstanceType],
    ):
        velocity: Velocity = entity_components[Velocity]

        for event in EVENT_LIST:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT:
                    self.direction.append(1)
                if event.key == pygame.K_LEFT:
                    self.direction.append(-1)

        for event in EVENT_LIST:
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_RIGHT:
                    self.direction.remove(1)
                if event.key == pygame.K_LEFT:
                    self.direction.remove(-1)

        if self.direction[-1] == 0:
            velocity.vector = pygame.Vector2(0, 0)

        if self.direction[-1] == 1:
            velocity.vector = pygame.Vector2(PLAYER_SPEED, 0)

        if self.direction[-1] == -1:
            velocity.vector = pygame.Vector2(-PLAYER_SPEED, 0)


class EnemyMovement(BaseSystem):
    def __init__(self, clock: pygame.time.Clock):
        super().__init__(required_component_types=[BoundingBox, StepMovement])
        self.clock = clock

    def update_entity(
            self,
            entity: Entity,
            entity_components: dict[typing.Type[BaseComponent], ComponentInstanceType],
    ):
        stepping: StepMovement = entity_components[StepMovement]
        bounding_box: BoundingBox = entity_components[BoundingBox]

        stepping.delay -= 1 / 12 * self.clock.get_time()

        if stepping.delay < 0:
            if stepping.step_count > 0:
                bounding_box.rect.x += 12 * stepping.direction
                stepping.step_count -= 1
            else:
                bounding_box.rect.y += 16
                stepping.step_count = 16
                stepping.direction = -stepping.direction
                stepping.freq = stepping.freq * 0.91
            stepping.delay = stepping.freq


class Shoot(BaseSystem):
    def __init__(self, clock: pygame.time.Clock):
        super().__init__(required_component_types=[ShootOnEvent, BoundingBox])
        self.clock = clock

    def update_entity(
            self,
            entity: Entity,
            entity_components: dict[typing.Type[BaseComponent], ComponentInstanceType],
    ):
        global EVENT_LIST
        shooting: ShootOnEvent = entity_components[ShootOnEvent]
        bounding_box = entity_components[BoundingBox]

        if shooting.cooldown_timer > 0:
            shooting.cooldown_timer -= 1 * 1 / 12 * self.clock.get_time()
            return None

        for event in EVENT_LIST:
            if event.type == pygame.KEYDOWN == shooting.event[0]:
                if event.key == shooting.event[1]:
                    components = []
                    rect, frames, states = load_image_sheet(random.choice(shooting.sprites))
                    components.append(AnimatedSprite(frames, states))
                    match shooting.direction:
                        case Direction.NORTH:
                            rect.centerx = bounding_box.rect.centerx
                            rect.centery = bounding_box.rect.y - rect.h // 2 - 1 * SCALE
                            components.append(Velocity((0, -shooting.projectile_speed * SCALE)))
                            sound = pygame.mixer.Sound(load_file('assets/sounds'
                                                                 '/270344__littlerobotsoundfactory__shoot_00.wav'))
                            sound.set_volume(VOLUME)
                            sound.play()
                        case Direction.SOUTH:
                            rect.centerx = bounding_box.rect.centerx
                            rect.centery = bounding_box.rect.centery
                            components.append(Velocity((0, shooting.projectile_speed * SCALE)))
                        case Direction.EAST:
                            rect.centerx = bounding_box.rect.centerx
                            rect.centery = bounding_box.rect.centery
                            components.append(Velocity((-shooting.projectile_speed * SCALE, 0)))
                        case Direction.WEST:
                            rect.centerx = bounding_box.rect.centerx
                            rect.centery = bounding_box.rect.centery
                            components.append(Velocity((shooting.projectile_speed * SCALE, 0)))
                            sound = pygame.mixer.Sound(load_file('assets/sounds'
                                                                 '/270343__littlerobotsoundfactory__shoot_01.wav'))
                            sound.set_volume(VOLUME)
                            sound.play()
                    components.append(BoundingBox(rect))
                    components.append(DamageOnContact("player"))
                    ENTITY_SPAWN_QUEUE.append(components)
                    shooting.cooldown_timer = shooting.cooldown
            elif event.type == shooting.event[0]:
                components = []
                rect, frames, states = load_image_sheet(random.choice(shooting.sprites))
                components.append(AnimatedSprite(frames, states))
                match shooting.direction:
                    case Direction.NORTH:
                        rect.centerx = bounding_box.rect.centerx
                        rect.centery = bounding_box.rect.y - rect.h // 2 - 1 * SCALE
                        components.append(Velocity((0, -shooting.projectile_speed * SCALE)))
                    case Direction.SOUTH:
                        rect.centerx = bounding_box.rect.centerx
                        rect.centery = bounding_box.rect.centery
                        components.append(Velocity((0, shooting.projectile_speed * SCALE)))
                    case Direction.EAST:
                        rect.centerx = bounding_box.rect.centerx
                        rect.centery = bounding_box.rect.centery
                        components.append(Velocity((-shooting.projectile_speed * SCALE, 0)))
                    case Direction.WEST:
                        rect.centerx = bounding_box.rect.centerx
                        rect.centery = bounding_box.rect.centery
                        components.append(Velocity((shooting.projectile_speed * SCALE, 0)))
                components.append(BoundingBox(rect))
                components.append(DamageOnContact("enemy"))
                ENTITY_SPAWN_QUEUE.append(components)
                shooting.cooldown_timer = shooting.cooldown


class DamageEntities(BaseSystem):
    def __init__(self):
        super().__init__(required_component_types=[BoundingBox, DamageOnContact])

    def update_entity(
            self,
            entity: Entity,
            entity_components: dict[typing.Type[BaseComponent], ComponentInstanceType],
    ):
        global SCORE
        bounding_box: BoundingBox = entity_components[BoundingBox]
        damaging: DamageOnContact = entity_components[DamageOnContact]
        if damaging.parent == "player":
            indices = bounding_box.rect.collidelistall(list(map(lambda x: x[0], ENEMY_RECT_LIST)))
            if len(indices) == 0:
                return None
            for index in indices:
                ENTITY_KILL_QUEUE.append(ENEMY_RECT_LIST[index][1])
                ENEMY_RECT_LIST.pop(index)
                SCORE += 100
            ENTITY_KILL_QUEUE.append(entity)
        else:
            if not bounding_box.rect.colliderect(PLAYER_RECT_HEALTH[0]):
                return None
            PLAYER_RECT_HEALTH[1].health -= 1
            ENTITY_KILL_QUEUE.append(entity)


class KillEntities(BaseSystem):
    def __init__(self):
        super().__init__(required_component_types=[Health])

    def update_entity(
            self,
            entity: Entity,
            entity_components: dict[typing.Type[BaseComponent], ComponentInstanceType],
    ):
        if entity_components[Health].health == 0:
            ENTITY_KILL_QUEUE.append(entity)


class StartDeathAnimation(BaseSystem):
    def __init__(self):
        super().__init__(required_component_types=[AnimatedSprite, Health])

    def update_entity(
            self,
            entity: Entity,
            entity_components: dict[typing.Type[BaseComponent], ComponentInstanceType],
    ):
        health: Health = entity_components[Health]
        sprite: AnimatedSprite = entity_components[AnimatedSprite]
        if health.health == 0:
            sprite.state = sprite.states.DEATH.value
            sprite.cur_delay = 0
            sprite.cur_frame = 0
            health.health = -1


class StartGameOverAnimation(BaseSystem):
    def __init__(self, clock: pygame.time.Clock):
        super().__init__(required_component_types=[Health, GameOverOnDeath])
        self.clock = clock

    def update_entity(
            self,
            entity: Entity,
            entity_components: dict[typing.Type[BaseComponent], ComponentInstanceType],
    ):
        global GAME_SCENE
        health: Health = entity_components[Health]
        game_over: GameOverOnDeath = entity_components[GameOverOnDeath]
        if health.health <= 0:
            GAME_SCENE = GameScene.DEATH
            if game_over.delay <= 0:
                GAME_SCENE = GameScene.GAME_OVER
            game_over.delay -= 1 * 1 / 12 * self.clock.get_time()


def init_player(entity_manager: EntityManager,
                component_manager: ComponentManager) -> Entity:
    global PLAYER_RECT_HEALTH
    player: Entity = entity_manager.add_entity()
    rect, frames, states = load_image_sheet("assets/sprites/player")
    rect.centerx = SCREEN_SIZE[0] * SCALE // 2
    rect.centery = SCREEN_SIZE[1] * SCALE - 16 * SCALE
    component_manager.add_component(player, AnimatedSprite(frames, states))
    component_manager.add_component(player, BoundingBox(rect))
    component_manager.add_component(player, PlayerControlled())
    component_manager.add_component(player, ShootOnEvent((pygame.KEYDOWN, pygame.K_SPACE),
                                                         Direction.NORTH,
                                                         ("assets/sprites/bullet",)))
    component_manager.add_component(player, Velocity())
    health = Health(3)
    component_manager.add_component(player, health)
    component_manager.add_component(player, GameOverOnDeath())
    PLAYER_RECT_HEALTH = (rect, health)
    return player


def load_enemy(path: str, row: int, column: int,
               entity_manager: EntityManager,
               component_manager: ComponentManager, can_shoot: int = -1) -> Entity:
    enemy = entity_manager.add_entity()
    rect, frames, states = load_image_sheet(path)
    rect.x = (28 - int(row >= 1) - int(row >= 2) + 16 * column) * SCALE
    rect.y = (30 + 16 * row) * SCALE
    component_manager.add_component(enemy, AnimatedSprite(frames, states, randint(0, len(frames) - 1)))
    component_manager.add_component(enemy, BoundingBox(rect))
    component_manager.add_component(enemy, StepMovement())
    if can_shoot != -1:
        component_manager.add_component(enemy, ShootOnEvent((can_shoot, None),
                                                            Direction.SOUTH,
                                                            ("assets/sprites/bullet1", "assets/sprites/bullet2"),
                                                            0))
    ENEMY_RECT_LIST.append((rect, enemy))
    return enemy


def init_enemies(entity_manager: EntityManager,
                 component_manager: ComponentManager) -> list[Entity]:
    enemies = []
    event_int = pygame.USEREVENT + 2
    for i in range(11):
        enemies.append(load_enemy("assets/sprites/squid", 0, i, entity_manager, component_manager, can_shoot=event_int))
        enemies.append(load_enemy("assets/sprites/enemy", 1, i, entity_manager, component_manager))
        enemies.append(load_enemy("assets/sprites/enemy", 2, i, entity_manager, component_manager))
        enemies.append(load_enemy("assets/sprites/brute", 3, i, entity_manager, component_manager))
        enemies.append(load_enemy("assets/sprites/brute", 4, i, entity_manager, component_manager))
        event_int += 1

    return enemies


def add_entity_from_queue(components: list[BaseComponent],
                          entity_manager: EntityManager,
                          component_manager: ComponentManager) -> Entity:
    entity = entity_manager.add_entity()
    for component in components:
        component_manager.add_component(entity, component)
    return entity


def main():
    global EVENT_LIST, ENTITY_LIST, GAME_SCENE, SCORE
    pygame.init()
    pygame.mixer.init()
    pygame.display.set_caption('Space Invaders')
    screen = pygame.display.set_mode(tuple(map(lambda x: x * SCALE, SCREEN_SIZE)))
    clock = pygame.time.Clock()

    component_manager = ComponentManager()
    entity_manager = EntityManager(component_manager)

    component_manager.init_components()

    while True:
        match GAME_SCENE:
            case GameScene.MENU:
                state = 0
                while True:
                    screen.fill((0, 0, 0))

                    font_title = pygame.font.Font(load_file('assets/fonts/Retro_Gaming.ttf'), 48)
                    space_text = font_title.render('SPACE', True, (255, 255, 255))
                    invaders_text = font_title.render('INVADERS', True, (30, 254, 30))
                    space_text_rect = space_text.get_rect()
                    invaders_text_rect = invaders_text.get_rect()
                    space_text_rect.center = (SCREEN_SIZE[0] * SCALE // 2 - 160, SCREEN_SIZE[1] * SCALE // 4)
                    invaders_text_rect.center = (SCREEN_SIZE[0] * SCALE // 2 + 100, SCREEN_SIZE[1] * SCALE // 4)
                    screen.blit(space_text, space_text_rect)
                    screen.blit(invaders_text, invaders_text_rect)

                    font = pygame.font.Font(load_file('assets/fonts/Retro_Gaming.ttf'), 33)
                    score_text = font.render('HI-SCORE', True, (255, 255, 255))
                    score_text_rect = score_text.get_rect()
                    score_text_rect.x += 10
                    score_text_rect.y += 5
                    screen.blit(score_text, score_text_rect)

                    with open(load_file('data/score.txt'), encoding='utf8') as file:
                        data = file.readline()
                        SCORE = data
                    score_num_text = font.render(str(SCORE).zfill(6), True, (255, 255, 255))
                    score_num_rect = score_num_text.get_rect()
                    score_num_rect.x += 15
                    score_num_rect.y += 38
                    screen.blit(score_num_text, score_num_rect)

                    start_font = pygame.font.Font(load_file('assets/fonts/Retro_Gaming.ttf'), 36)
                    start_text = start_font.render('START', True, (255, 255, 255))
                    start_text_select = start_font.render('START', True, (30, 254, 30))
                    start_text_rect = start_text.get_rect()
                    start_text_rect.center = (SCREEN_SIZE[0] * SCALE // 2, SCREEN_SIZE[1] * SCALE // 6 * 4)

                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            sys.exit()
                        if event.type == pygame.MOUSEBUTTONUP:
                            pos = pygame.mouse.get_pos()
                            if start_text_rect.collidepoint(*pos):
                                GAME_SCENE = GameScene.GAME
                                break

                    pos = pygame.mouse.get_pos()
                    if start_text_rect.collidepoint(*pos):
                        if state == 0:
                            sound = pygame.mixer.Sound(
                                load_file('assets/sounds/270315__littlerobotsoundfactory__menu_navigate_03.wav'))
                            sound.set_volume(VOLUME)
                            sound.play()
                        screen.blit(start_text_select, start_text_rect)
                        state = 1
                    else:
                        state = 0
                        screen.blit(start_text, start_text_rect)

                    pygame.display.flip()
                    clock.tick(FPS)
                    if GAME_SCENE != GameScene.MENU:
                        break
            case GameScene.GAME:
                entity_manager = EntityManager(component_manager)
                system_manager = SystemManager(entity_manager, component_manager)

                systems = [PositionCalculation(clock),
                           PlayerMovement(),
                           EnemyMovement(clock),
                           Shoot(clock),
                           DamageEntities()]

                for system in systems:
                    system_manager.add_system(system)

                system_manager.add_system(SpriteDraw(screen, clock))
                system_manager.add_system(StartDeathAnimation())
                system_manager.add_system(StartGameOverAnimation(clock))

                ENTITY_LIST.append(init_player(entity_manager, component_manager))
                ENTITY_LIST += init_enemies(entity_manager, component_manager)

                pygame.time.set_timer(ENEMY_SHOOT, random.randint(1, 1600))

                SCORE = 0

                while True:
                    EVENT_LIST = pygame.event.get()

                    for event in EVENT_LIST:
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            sys.exit(0)
                        elif event.type == ENEMY_SHOOT:
                            pygame.time.set_timer(ENEMY_SHOOT, random.randint(1, 1600))
                            new_event = pygame.event.Event(random.randint(pygame.USEREVENT + 2, pygame.USEREVENT + 12))
                            pygame.event.post(new_event)

                    screen.fill((0, 0, 0))

                    system_manager.update_entities()

                    while len(ENTITY_SPAWN_QUEUE) > 0:
                        ENTITY_LIST.append(
                            add_entity_from_queue(ENTITY_SPAWN_QUEUE.pop(), entity_manager, component_manager))

                    while len(ENTITY_KILL_QUEUE) > 0:
                        entity = ENTITY_KILL_QUEUE.pop()
                        ENTITY_LIST.remove(entity)
                        entity_manager.kill_entity(entity)

                    if len(ENEMY_RECT_LIST) == 0:
                        ENTITY_LIST += init_enemies(entity_manager, component_manager)

                    font = pygame.font.Font(load_file('assets/fonts/Retro_Gaming.ttf'), 33)
                    score_text = font.render('SCORE', True, (255, 255, 255))
                    score_text_rect = score_text.get_rect()
                    score_text_rect.x += 10
                    score_text_rect.y += 5
                    screen.blit(score_text, score_text_rect)

                    score_num_text = font.render(str(SCORE).zfill(6), True, (255, 255, 255))
                    score_num_rect = score_num_text.get_rect()
                    score_num_rect.x += 15
                    score_num_rect.y += 38
                    screen.blit(score_num_text, score_num_rect)

                    lives_text = font.render('LIVES', True, (255, 255, 255))
                    lives_rect = lives_text.get_rect()
                    lives_rect.x += 500
                    lives_rect.y += 5
                    screen.blit(lives_text, lives_rect)

                    for i in range(1, PLAYER_RECT_HEALTH[1].health + 1):
                        image = load_image('assets/sprites/lives/image.png')[0]
                        image = pygame.transform.scale_by(image, 0.5)
                        rect = image.get_rect()
                        rect.x += 600 + 56 * i
                        rect.y += 10
                        screen.blit(image, rect)

                    pygame.display.update()
                    clock.tick(FPS)

                    if GAME_SCENE != GameScene.GAME:
                        print("HAH")
                        if GAME_SCENE != GameScene.DEATH:
                            break
                        else:
                            for system in systems:
                                system_manager.remove_system(system)
                            systems = []

                    for system, performance in sorted(SYSTEM_PERF.items(), key=lambda x: x[0]):
                        print(system, performance, sep="\t")
            case GameScene.GAME_OVER:
                with open(load_file('data/score.txt'), encoding='utf8') as file:
                    data = file.readline()
                    score = int(data)
                with open(load_file('data/score.txt'), mode='w', encoding='utf8') as file:
                    file.write(str(max(SCORE, score)))
                state = 0
                while True:
                    screen.fill((0, 0, 0))

                    font_title = pygame.font.Font(load_file('assets/fonts/Retro_Gaming.ttf'), 55)
                    game_over_text = font_title.render('GAME OVER', True, (255, 255, 255))

                    game_over_rect = game_over_text.get_rect()
                    game_over_rect.center = (SCREEN_SIZE[0] * 4 // 2, SCREEN_SIZE[1] * 4 // 4)
                    screen.blit(game_over_text, game_over_rect)

                    font = pygame.font.Font(load_file('assets/fonts/Retro_Gaming.ttf'), 33)
                    score_text = font.render('HI-SCORE', True, (255, 255, 255))
                    score_text_rect = score_text.get_rect()
                    score_text_rect.x += 10
                    score_text_rect.y += 5
                    screen.blit(score_text, score_text_rect)

                    with open(load_file('data/score.txt'), encoding='utf8') as file:
                        data = file.readline()
                        SCORE = int(data)
                    score_num_text = font.render(str(SCORE).zfill(6), True, (255, 255, 255))
                    score_num_rect = score_num_text.get_rect()
                    score_num_rect.x += 15
                    score_num_rect.y += 38
                    screen.blit(score_num_text, score_num_rect)

                    start_font = pygame.font.Font(load_file('assets/fonts/Retro_Gaming.ttf'), 36)
                    start_text = start_font.render('START', True, (255, 255, 255))
                    start_text_select = start_font.render('START', True, (30, 254, 30))
                    start_text_rect = start_text.get_rect()
                    start_text_rect.center = (SCREEN_SIZE[0] * 4 // 2, SCREEN_SIZE[1] * 4 // 6 * 4)

                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            sys.exit()
                        if event.type == pygame.MOUSEBUTTONUP:
                            pos = pygame.mouse.get_pos()
                            if start_text_rect.collidepoint(*pos):
                                GAME_SCENE = GameScene.GAME
                                break

                    pos = pygame.mouse.get_pos()
                    if start_text_rect.collidepoint(*pos):
                        if state == 0:
                            sound = pygame.mixer.Sound(
                                load_file('assets/sounds/'
                                          '270315__littlerobotsoundfactory__menu_navigate_03.wav')
                            )
                            sound.set_volume(VOLUME)
                            sound.play()
                        screen.blit(start_text_select, start_text_rect)
                        state = 1
                    else:
                        screen.blit(start_text, start_text_rect)
                        state = 0

                    pygame.display.flip()
                    clock.tick(FPS)

                    if GAME_SCENE != GameScene.GAME_OVER:
                        break


if __name__ == '__main__':
    main()
