import random

import pygame
import sys
import os

SCREEN_SIZE = (896, 768)  # 224, 168 если делить на 4 (все увеличено в 4 раза)
FPS = 60


def load_image(name):
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
        self.rect.x = (SCREEN_SIZE[0] - self.rect[2]) // 2
        self.rect.y = SCREEN_SIZE[1] - self.rect[3] - 32
        self.bullet = pygame.sprite.GroupSingle()

    def update(self):
        keys = pygame.key.get_pressed()

        if keys[pygame.K_RIGHT]:
            self.rect.x += 6
        if keys[pygame.K_LEFT]:
            self.rect.x -= 6
        if keys[pygame.K_SPACE] and not len(self.bullet.sprites()):
            self.bullet.add(Bullet(x=self.rect.x, y=self.rect.y, direction=1))

        if self.rect.x < 0:
            self.rect.x = 0
        if self.rect.x > SCREEN_SIZE[0] - 52:
            self.rect.x = SCREEN_SIZE[0] - 52

        self.bullet.update()


class Bullet(pygame.sprite.Sprite):
    image = load_image('bullet.png')
    image = pygame.transform.scale(image, (4, 16))

    def __init__(self, *groups, x, y, direction):
        super().__init__(*groups)
        self.rect = self.image.get_rect()
        self.rect.x = x + 24
        self.rect.y = y - 16
        self.direction = direction

    def update(self):
        self.rect.y -= 10 * self.direction
        if self.rect.y < 0:
            self.kill()


class Enemy(pygame.sprite.Sprite):
    def __init__(self, *groups, image, x, y):
        super().__init__(*groups)
        self.frames = []
        sheet = load_image(image)
        self.cut_sheet(sheet, int(image[-7]), int(image[-5]))
        self.cur_frame = random.randint(0, 2 % len(self.frames))
        self.frame_count = 0

        self.move_frame_count = 0
        self.move_count = 8
        self.move_freq = 28
        self.direction = 1

        self.image = pygame.transform.scale(self.frames[self.cur_frame],
                                            (self.frames[self.cur_frame].get_rect()[2] * 4,
                                             self.frames[self.cur_frame].get_rect()[3] * 4))
        self.rect = self.image.get_rect()
        self.rect.x = x * 4
        self.rect.y = y * 4

    def cut_sheet(self, sheet, columns, rows):
        self.rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                sheet.get_height() // rows)
        for j in range(rows):
            for i in range(columns):
                frame_location = (self.rect.w * i, self.rect.h * j)
                self.frames.append(sheet.subsurface(pygame.Rect(
                    frame_location, self.rect.size)))

    def update(self):
        self.frame_count += 1
        self.move_frame_count += 1

        if self.move_frame_count == self.move_freq:
            if self.move_count > 0:
                self.rect.x += 12 * self.direction
                self.move_count -= 1
            else:
                self.rect.y += 16
                self.move_count = 17
                self.direction = 0 - self.direction
                self.move_freq = int(self.move_freq * 0.95)
            self.move_frame_count = 0

        if self.frame_count == 5:
            self.cur_frame = (self.cur_frame + 1) % len(self.frames)
            self.frame_count = 0
            self.image = pygame.transform.scale(self.frames[self.cur_frame],
                                                (self.frames[self.cur_frame].get_rect()[2] * 4,
                                                 self.frames[self.cur_frame].get_rect()[3] * 4))
            self.rect = self.image.get_rect().move(self.rect.x, self.rect.y)


def title_screen():
    screen.fill((0, 0, 0))

    font_title = pygame.font.Font('assets/Retro_Gaming.ttf', 48)
    space_text = font_title.render('SPACE', True, (255, 255, 255))
    invaders_text = font_title.render('INVADERS', True, (30, 254, 30))
    space_text_rect = space_text.get_rect()
    invaders_text_rect = invaders_text.get_rect()
    space_text_rect.center = (SCREEN_SIZE[0] // 2 - 160, SCREEN_SIZE[1] // 4)
    invaders_text_rect.center = (SCREEN_SIZE[0] // 2 + 100, SCREEN_SIZE[1] // 4)
    screen.blit(space_text, space_text_rect)
    screen.blit(invaders_text, invaders_text_rect)
    font_text = pygame.font.Font('assets/Retro_Gaming.ttf', 22)
    score_text = font_title.render('SPACE INVADERS', True, (255, 255, 255))

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                return
        pygame.display.flip()
        clock.tick(FPS)


class Game:
    def __init__(self):
        self.player = Player()
        self.player_group = pygame.sprite.GroupSingle(self.player)
        self.enemies = pygame.sprite.Group()
        self.score = 0
        for i in range(11):
            self.enemies.add(Enemy(image='squid_2x4.png', x=28 + 16 * i, y=20))
            self.enemies.add(Enemy(image='enemy_2x4.png', x=27 + 16 * i, y=20 + 16))
            self.enemies.add(Enemy(image='enemy_2x4.png', x=27 + 16 * i, y=20 + 16 * 2))
            self.enemies.add(Enemy(image='brute_2x5.png', x=26 + 16 * i, y=20 + 16 * 3))
            self.enemies.add(Enemy(image='brute_2x5.png', x=26 + 16 * i, y=20 + 16 * 4))
        self.all_game_groups = [self.player_group, self.enemies]

    def detect_collision(self):
        if self.player.bullet.sprite:
            for enemy in self.enemies:
                if self.player.bullet.sprite.rect.colliderect(enemy.rect):
                    self.player.bullet.sprite.kill()
                    self.score += 100
                    enemy.kill()
                    break

    def update(self):
        self.player.update()
        self.enemies.update()
        self.detect_collision()
        for group in self.all_game_groups:
            group.draw(screen)
        self.player.bullet.draw(screen)


if __name__ == '__main__':
    pygame.init()
    pygame.display.set_caption('Космические захватчики')
    screen = pygame.display.set_mode(SCREEN_SIZE)
    clock = pygame.time.Clock()

    title_screen()

    game = Game()

    ENEMYSHOOT = pygame.USEREVENT + 1
    pygame.time.set_timer(ENEMYSHOOT, 800)
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        screen.fill((0, 0, 0))
        game.update()

        pygame.display.flip()
        clock.tick(FPS)
