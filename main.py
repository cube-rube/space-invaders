import pygame
import os
import sys

pygame.init()

SCREEN_SIZE = (892, 672)  # 223, 168 если делить на 4 (все увеличено в 4 раза)

FPS = 50


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
        if 0 <= self.rect.x + 6 * state <= SCREEN_SIZE[0] - 52:
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

        for i in enemies.spritedict:
            if self.rect.colliderect(i.rect):
                # i.kill() надо заменить на анимацию
                i.kill()
                self.kill()
                break

        if self.rect.y < 0:
            self.kill()


class Enemy(pygame.sprite.Sprite):
    def __init__(self, *groups, enemy_image, x, y):
        super().__init__(*groups)
        self.image = load_image(enemy_image)
        self.image = pygame.transform.scale(self.image, (self.image.get_rect()[2] * 4, self.image.get_rect()[3] * 4))
        self.rect = self.image.get_rect()
        self.rect.x = x * 4
        self.rect.y = y * 4


def main():

    screen = pygame.display.set_mode(SCREEN_SIZE)

    all_sprites = pygame.sprite.Group()

    enemies = pygame.sprite.Group()

    player = Player(all_sprites)

    bul = None

    # Враг для дебага
    enemy = Enemy(all_sprites, enemies, enemy_image='enemy1.png', x=20, y=28)
    enemy1 = Enemy(all_sprites, enemies, enemy_image='enemy2.png', x=30, y=28)

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
        if keys[pygame.K_SPACE]:
            if not bul or not bul.alive():
                bul = Bullet(all_sprites, x=player.rect.x, y=player.rect.y)
        if bul:
            bul.update()

        screen.fill((0, 0, 0))
        all_sprites.draw(screen)

        clock.tick(FPS)
        pygame.display.flip()

    pygame.quit()


if __name__ == '__main__':
    main()