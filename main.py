import pygame
import os
import sys


pygame.init()


def load_image(name, colorkey=None):
    fullname = os.path.join('assets', name)
    if not os.path.isfile(fullname):
        print(f"Файл с изображением '{fullname}' не найден")
        sys.exit()
    image = pygame.image.load(fullname)
    return image


class Player(pygame.sprite.Sprite):
    image = load_image('player_small.png')
    image = pygame.transform.scale(image, (52, 32))

    def __init__(self, *groups):
        super().__init__(*groups)
        self.rect = self.image.get_rect()
        print(self.rect)
        self.rect.x = 384
        self.rect.y = 600
        self.state = 0

    def move(self, state):
        if 0 <= self.rect.x + 6 * state <= screen_size[0] - 52:
            self.rect.x += 6 * state


screen_size = (893, 672)
screen = pygame.display.set_mode(screen_size)

FPS = 50

all_sprites = pygame.sprite.Group()
player = Player(all_sprites)
running = True
clock = pygame.time.Clock()


while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:
        player.move(-1)
    if keys[pygame.K_RIGHT]:
        player.move(1)

    screen.fill((0, 0, 0))
    all_sprites.draw(screen)

    clock.tick(FPS)
    pygame.display.flip()

pygame.quit()

