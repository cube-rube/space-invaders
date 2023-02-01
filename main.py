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
        self.rect.x = 384
        self.rect.y = 600
        self.state = 0

    def move(self, state):
        if 0 <= self.rect.x + 6 * state <= screen_size[0] - 52:
            self.rect.x += 6 * state


class Bullet(pygame.sprite.Sprite):
    image = load_image('bullet.png')
    image = pygame.transform.scale(image, (4, 16))

    def __init__(self, *groups, x, y):
        super().__init__(*groups)
        self.rect = self.image.get_rect()
        self.rect.x = x + 24
        self.rect.y = y - 16

    def update(self):
        self.rect.y -= 10
        if self.rect.y < 0:
            self.kill()


class Enemy(pygame.sprite.Sprite):
    def __init__(self, *groups, enemy_image, x, y):
        super().__init__(*groups)
        self.image = load_image(enemy_image)
        self.image = pygame.transform.scale(self.image, (self.image.get_rect()[2] * 4, self.image.get_rect()[3] * 4))
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y


screen_size = (893, 672)
screen = pygame.display.set_mode(screen_size)

FPS = 50

all_sprites = pygame.sprite.Group()
player = Player(all_sprites)
bul = Bullet(all_sprites, x=player.rect.x, y=player.rect.y)
bul.kill()
running = True
clock = pygame.time.Clock()


while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if not bul or not bul.alive():
                bul = Bullet(all_sprites, x=player.rect.x, y=player.rect.y)

    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:
        player.move(-1)
    if keys[pygame.K_RIGHT]:
        player.move(1)
    if bul:
        bul.update()

    screen.fill((0, 0, 0))
    all_sprites.draw(screen)

    clock.tick(FPS)
    pygame.display.flip()

pygame.quit()

