import typing

import pygame
import pygame_ecs
from pathlib import Path
from enum import Enum
import json
import sys

from pygame_ecs import Entity
from pygame_ecs.components.base_component import BaseComponent
from pygame_ecs.managers.component_manager import ComponentInstanceType

SCALE = 4
SCREEN_SIZE = (224, 192)
FPS = 60
VOLUME = 0.2
DRAW_BOUNDING_BOXES = True


def cut_sheet(image: pygame.Surface, rows: int, columns: int) -> tuple[pygame.Rect, list[pygame.Surface]]:
    rect = pygame.Rect(0, 0, image.get_width() // columns, image.get_height() // rows)
    frames = []
    for j in range(rows):
        for i in range(columns):
            frame_location = (rect.w * i, rect.h * j)
            frames.append(image.subsurface(pygame.Rect(frame_location, rect.size)))

    return frames[0].get_bounding_rect(), frames


def load_image_sheet(path: str) -> tuple[pygame.Rect, list[pygame.Surface], Enum]:
    with (open(Path(__file__).parent / (path + ".json"), encoding="utf-8") as json_file,
          open(Path(__file__).parent / (path + ".png"), encoding="utf-8") as image_file):
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


def increment_delay(cur_delay, state: dict):
    delay: int = state['delay']
    looping: bool = state['looping']
    if delay is None:
        return -1
    if looping:
        return (cur_delay + 1) % delay
    return cur_delay + 1


class Image(pygame_ecs.BaseComponent):
    def __init__(self, image: pygame.Surface):
        super().__init__()
        self.image: pygame.Surface = image


class Player(pygame_ecs.BaseComponent):
    pass


class AnimatedSprite(pygame_ecs.BaseComponent):
    def __init__(self, frames: list[pygame.Surface], states: Enum):
        super().__init__()
        self.frames = frames
        self.cur_frame = 0
        self.states = states
        self.state: dict = self.states.IDLE.value
        self.cur_delay = 0


class BoundingBox(pygame_ecs.BaseComponent):
    def __init__(self, rect: pygame.Rect):
        super().__init__()
        self.rect = rect


class Health(pygame_ecs.BaseComponent):
    def __init__(self, health: int):
        super().__init__()
        self.health = health


class Velocity(pygame_ecs.BaseComponent):
    def __init__(self):
        super().__init__()
        self.vector = pygame.Vector2(0, 0)


class ImageDraw(pygame_ecs.BaseSystem):
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

        rect = frame.get_rect().move(bounding_box.rect.centerx - (frame.get_rect().w // 2),
                                     bounding_box.rect.centery - (frame.get_rect().h // 2) + 2)  # + 2 ???

        if DRAW_BOUNDING_BOXES:
            pygame.draw.rect(self.screen, 'red', rect, 2)
            pygame.draw.rect(self.screen, 'blue', bounding_box.rect, 2)
        self.screen.blit(frame, rect)

        if sprite.cur_delay == 0:
            sprite.cur_frame = (sprite.cur_frame + 1) % len(sprite.state['frames'])

        sprite.cur_delay = increment_delay(sprite.cur_delay, sprite.state)


class PlayerMovement(pygame_ecs.BaseSystem):
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
            velocity.vector = pygame.Vector2(6, 0)

        if self.direction[-1] == -1:
            velocity.vector = pygame.Vector2(-6, 0)


class ApplyVelocity(pygame_ecs.BaseSystem):
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


class StartDeathAnim(pygame_ecs.BaseSystem):
    def __init__(self):
        super().__init__(required_component_types=[AnimatedSprite, Health])

    def update_entity(
            self,
            entity: Entity,
            entity_components: dict[typing.Type[BaseComponent], ComponentInstanceType],
    ):
        health: int = entity_components[Health].health
        sprite: AnimatedSprite = entity_components[AnimatedSprite]
        if health == 0:
            sprite.state = sprite.states.DEATH.value
            sprite.cur_delay = 0
            sprite.cur_frame = 0


def init_player(entity_manager: pygame_ecs.EntityManager, component_manager: pygame_ecs.ComponentManager) -> None:
    player: pygame_ecs.Entity = entity_manager.add_entity()
    rect, frames, states = load_image_sheet("assets/player_2x3")
    component_manager.add_component(player, AnimatedSprite(frames, states))
    component_manager.add_component(player, BoundingBox(rect.move(((SCREEN_SIZE[0] * SCALE) - rect[2]) // 2,
                                                                  (SCREEN_SIZE[1] * SCALE) - rect[3] - 32)))
    component_manager.add_component(player, Player())
    component_manager.add_component(player, Velocity())


def main():
    screen = pygame.display.set_mode(tuple(map(lambda x: x * SCALE, SCREEN_SIZE)))
    clock = pygame.time.Clock()

    component_manager = pygame_ecs.ComponentManager()
    entity_manager = pygame_ecs.EntityManager(component_manager)
    system_manager = pygame_ecs.SystemManager(entity_manager, component_manager)

    system_manager.add_system(ImageDraw(screen))
    system_manager.add_system(ApplyVelocity())
    system_manager.add_system(StartDeathAnim())
    system_manager.add_system(PlayerMovement())
    component_manager.init_components()

    init_player(entity_manager, component_manager)

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
