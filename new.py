import typing
import time

import pygame
import pygame_ecs

import sys
from pathlib import Path
from enum import Enum
import json
from random import randint

from pygame_ecs import Entity
from pygame_ecs.components.base_component import BaseComponent
from pygame_ecs.managers.component_manager import ComponentInstanceType, ComponentManager
from pygame_ecs.managers.entity_manager import EntityManager
from pygame_ecs.managers.system_manager import SystemManager
from pygame_ecs.systems.base_system import BaseSystem

SCALE = 4
SCREEN_SIZE = (224, 192)
FPS = 60
VOLUME = 0.2
DRAW_BOUNDING_BOXES = False
PLAYER_SPEED = 2 * SCALE


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


def load_image(path: str) -> tuple[pygame.surface.Surface]:
    abs_path = Path(__file__).parent / path
    if not abs_path.is_file():
        raise FileNotFoundError(f"Tried loading {abs_path} as image")
    return pygame.transform.scale_by(pygame.image.load(abs_path), SCALE),


def increment_delay(cur_delay, state: dict) -> int:
    delay: int = state['delay']
    looping: bool = state['looping']
    if delay is None:
        return -1
    if looping:
        return (cur_delay + 1) % delay
    return cur_delay + 1


class Image(BaseComponent):
    def __init__(self, image: pygame.Surface):
        super().__init__()
        self.image: pygame.Surface = image


class Player(BaseComponent):
    pass


class AnimatedSprite(BaseComponent):
    def __init__(self, frames: list[pygame.Surface], states: Enum, cur_frame=0):
        super().__init__()
        self.frames = frames
        self.cur_frame = cur_frame
        self.states = states
        self.state: dict = self.states.IDLE.value
        self.cur_delay = 0


class BoundingBox(BaseComponent):
    def __init__(self, rect: pygame.Rect):
        super().__init__()
        self.rect = rect


class Health(BaseComponent):
    def __init__(self, health: int):
        super().__init__()
        self.health = health


class Velocity(BaseComponent):
    def __init__(self):
        super().__init__()
        self.vector = pygame.Vector2(0, 0)


class ImageDraw(BaseSystem):
    def __init__(self, screen: pygame.Surface):
        super().__init__(required_component_types=[AnimatedSprite, BoundingBox])
        self.screen = screen

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

        if sprite.cur_delay == 0:
            sprite.cur_frame = (sprite.cur_frame + 1) % len(sprite.state['frames'])

        sprite.cur_delay = increment_delay(sprite.cur_delay, sprite.state)


class ApplyVelocity(BaseSystem):
    def __init__(self):
        super().__init__(required_component_types=[BoundingBox, Velocity])

    def update_entity(
            self,
            entity: Entity,
            entity_components: dict[typing.Type[BaseComponent], ComponentInstanceType],
    ):
        bounding_box: BoundingBox = entity_components[BoundingBox]
        velocity: Velocity = entity_components[Velocity]
        bounding_box.rect = bounding_box.rect.move(velocity.vector)
        if bounding_box.rect.x < 0:
            bounding_box.rect.x = 0
        if bounding_box.rect.x > (SCREEN_SIZE[0]) * SCALE - bounding_box.rect.w:
            bounding_box.rect.x = (SCREEN_SIZE[0]) * SCALE - bounding_box.rect.w
        if bounding_box.rect.y < 0:
            bounding_box.rect.y = 0
        if bounding_box.rect.y > (SCREEN_SIZE[1]) * SCALE - bounding_box.rect.h:
            bounding_box.rect.y = (SCREEN_SIZE[1]) * SCALE - bounding_box.rect.h


class PlayerMovement(BaseSystem):
    def __init__(self):
        super().__init__(required_component_types=[Player, BoundingBox, AnimatedSprite, Velocity])
        self.direction = [0]

    def update_entity(
            self,
            entity: Entity,
            entity_components: dict[typing.Type[BaseComponent], ComponentInstanceType],
    ):
        velocity: Velocity = entity_components[Velocity]

        keys = pygame.event.get(pygame.KEYDOWN)
        for key in keys:
            if key.key == pygame.K_RIGHT:
                self.direction.append(1)
            if key.key == pygame.K_LEFT:
                self.direction.append(-1)

        keys = pygame.event.get(pygame.KEYUP)
        for key in keys:
            if key.key == pygame.K_RIGHT:
                self.direction.remove(1)
            if key.key == pygame.K_LEFT:
                self.direction.remove(-1)

        if self.direction[-1] == 0:
            velocity.vector = pygame.Vector2(0, 0)

        if self.direction[-1] == 1:
            velocity.vector = pygame.Vector2(PLAYER_SPEED, 0)

        if self.direction[-1] == -1:
            velocity.vector = pygame.Vector2(-PLAYER_SPEED, 0)


class StartDeathAnim(BaseSystem):
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


def init_player(entity_manager: EntityManager,
                component_manager: ComponentManager) -> Entity:
    player: Entity = entity_manager.add_entity()
    rect, frames, states = load_image_sheet("assets/sprites/player")
    rect.centerx = SCREEN_SIZE[0] * SCALE // 2
    rect.centery = SCREEN_SIZE[1] * SCALE - 16 * SCALE
    component_manager.add_component(player, AnimatedSprite(frames, states))
    component_manager.add_component(player, BoundingBox(rect))
    component_manager.add_component(player, Player())
    component_manager.add_component(player, Velocity())
    component_manager.add_component(player, Health(3))
    return player


def load_enemy(path: str, row: int, column: int,
               entity_manager: EntityManager,
               component_manager: ComponentManager) -> Entity:
    enemy = entity_manager.add_entity()
    rect, frames, states = load_image_sheet(path)
    rect.x = (28 - int(row >= 2) - int(row >= 3) + 16 * column) * SCALE
    rect.y = (30 + 16 * row) * SCALE
    component_manager.add_component(enemy, AnimatedSprite(frames, states, randint(0, len(frames) - 1)))
    component_manager.add_component(enemy, BoundingBox(rect))
    component_manager.add_component(enemy, Health(1))
    return enemy


def init_enemies(entity_manager: EntityManager,
                 component_manager: ComponentManager) -> list[Entity]:
    enemies = []
    for i in range(11):
        enemies.append(load_enemy("assets/sprites/squid", 1, i, entity_manager, component_manager))
        enemies.append(load_enemy("assets/sprites/enemy", 2, i, entity_manager, component_manager))
        enemies.append(load_enemy("assets/sprites/enemy", 3, i, entity_manager, component_manager))
        enemies.append(load_enemy("assets/sprites/brute", 4, i, entity_manager, component_manager))
        enemies.append(load_enemy("assets/sprites/brute", 5, i, entity_manager, component_manager))

    return enemies


def main():
    screen = pygame.display.set_mode(tuple(map(lambda x: x * SCALE, SCREEN_SIZE)))
    clock = pygame.time.Clock()

    component_manager = ComponentManager()
    entity_manager = EntityManager(component_manager)
    system_manager = SystemManager(entity_manager, component_manager)

    system_manager.add_system(ImageDraw(screen))
    system_manager.add_system(ApplyVelocity())
    system_manager.add_system(StartDeathAnim())
    system_manager.add_system(PlayerMovement())
    component_manager.init_components()

    init_player(entity_manager, component_manager)
    init_enemies(entity_manager, component_manager)

    while True:
        pygame.event.pump()

        if pygame.event.peek(pygame.QUIT):
            pygame.quit()
            sys.exit(0)

        screen.fill((0, 0, 0))

        system_manager.update_entities()
        pygame.display.update()
        clock.tick(FPS)


if __name__ == '__main__':
    main()
