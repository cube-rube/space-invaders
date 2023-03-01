import random
import csv
import pygame
import sys
import os

SCREEN_SIZE = (896, 768)  # 224, 168 если делить на 4 (все увеличено в 4 раза)
FPS = 60
VOLUME = 0.2


def load_image(name):
    fullname = os.path.join('assets', name)
    if not os.path.isfile(fullname):
        print(f"Файл с изображением '{fullname}' не найден")
        sys.exit()
    image = pygame.image.load(fullname)
    return image


class Player(pygame.sprite.Sprite):
    def __init__(self, *groups):
        super().__init__(*groups)
        self.frames = []
        sheet = load_image('player1.png')
        self.cut_sheet(sheet, 2, 3)
        self.cur_frame = 0
        self.frame_count = 0

        self.image = pygame.transform.scale(self.frames[self.cur_frame],
                                            (self.frames[self.cur_frame].get_rect()[2] * 4,
                                             self.frames[self.cur_frame].get_rect()[3] * 4))

        self.rect = self.image.get_rect()
        self.rect.x = (SCREEN_SIZE[0] - self.rect[2]) // 2
        self.rect.y = SCREEN_SIZE[1] - self.rect[3] - 32
        self.bullet = pygame.sprite.GroupSingle()
        self.lives = 3

    def cut_sheet(self, sheet, columns, rows):
        self.rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                sheet.get_height() // rows)
        for j in range(rows):
            for i in range(columns):
                frame_location = (self.rect.w * i, self.rect.h * j)
                self.frames.append(sheet.subsurface(pygame.Rect(
                    frame_location, self.rect.size)))

    def update(self):
        keys = pygame.key.get_pressed()
        if self.lives == 0:
            pygame.mixer.music.stop()
            if self.cur_frame == 5:
                return 'DEATH'
            if self.frame_count == 5 and self.cur_frame < 5:
                self.cur_frame += 1
                self.frame_count = 0
                self.image = pygame.transform.scale(self.frames[self.cur_frame],
                                                    (self.frames[self.cur_frame].get_rect()[2] * 4,
                                                     self.frames[self.cur_frame].get_rect()[3] * 4))
                self.rect = self.image.get_rect().move(self.rect.x, self.rect.y)
            self.frame_count += 1
            return

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
    def __init__(self, *groups, image='bullet_1x1.png', x, y, direction):
        super().__init__(*groups)
        self.frames = []
        sheet = load_image(image)
        self.cut_sheet(sheet, int(image[-7]), int(image[-5]))
        self.cur_frame = 0
        self.frame_count = 0

        self.image = pygame.transform.scale(self.frames[self.cur_frame],
                                            (self.frames[self.cur_frame].get_rect()[2] * 4,
                                             self.frames[self.cur_frame].get_rect()[3] * 4))

        self.rect = self.image.get_rect()
        if direction == 1:
            self.rect.x = x + 36
        else:
            self.rect.x = x + 24
        self.rect.y = y - (16 * direction)
        self.direction = direction

        if direction == 1:
            sound = pygame.mixer.Sound('assets/sounds/270344__littlerobotsoundfactory__shoot_00.wav')
        else:
            sound = pygame.mixer.Sound('assets/sounds/270343__littlerobotsoundfactory__shoot_01.wav')
        sound.set_volume(VOLUME)
        sound.play()

    def cut_sheet(self, sheet, columns, rows):
        self.rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                sheet.get_height() // rows)
        for j in range(rows):
            for i in range(columns):
                frame_location = (self.rect.w * i, self.rect.h * j)
                self.frames.append(sheet.subsurface(pygame.Rect(
                    frame_location, self.rect.size)))

    def update(self):
        if self.direction == -1:
            self.rect.y += 6
        else:
            self.rect.y -= 10
        if not SCREEN_SIZE[0] >= self.rect.y >= 0:
            self.kill()

        if self.frame_count == 5:
            self.cur_frame = (self.cur_frame + 1) % len(self.frames)
            self.frame_count = 0
            self.image = pygame.transform.scale(self.frames[self.cur_frame],
                                                (self.frames[self.cur_frame].get_rect()[2] * 4,
                                                 self.frames[self.cur_frame].get_rect()[3] * 4))
            self.rect = self.image.get_rect().move(self.rect.x, self.rect.y)
        self.frame_count += 1


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
        self.move_freq = 40
        self.direction = 1

        self.image = pygame.transform.scale(self.frames[self.cur_frame],
                                            (self.frames[self.cur_frame].get_rect()[2] * 4,
                                             self.frames[self.cur_frame].get_rect()[3] * 4))
        self.rect = self.image.get_rect()
        self.rect.x = x * 4
        self.rect.y = y * 4

        self.bullet = pygame.sprite.GroupSingle()

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

        self.bullet.update()

    def shoot(self):
        if not self.bullet.sprite:
            images = ['bullet1_1x5.png', 'bullet2_4x1.png']
            self.bullet.add(Bullet(image=random.choice(images), x=self.rect.x, y=self.rect.bottom, direction=-1))


def title_screen():
    state = 0
    while True:
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

        font = pygame.font.Font('assets/Retro_Gaming.ttf', 33)
        score_text = font.render('HI-SCORE', True, (255, 255, 255))
        score_text_rect = score_text.get_rect()
        score_text_rect.x += 10
        score_text_rect.y += 5
        screen.blit(score_text, score_text_rect)

        with open('data/scores.csv', encoding='utf8') as file:
            data = csv.reader(file)
            score = max(map(lambda x: int(x[0]), data))
        score_num_text = font.render(str(score).zfill(6), True, (255, 255, 255))
        score_num_rect = score_num_text.get_rect()
        score_num_rect.x += 15
        score_num_rect.y += 38
        screen.blit(score_num_text, score_num_rect)

        start_font = pygame.font.Font('assets/Retro_Gaming.ttf', 36)
        start_text = start_font.render('START', True, (255, 255, 255))
        start_text_select = start_font.render('START', True, (30, 254, 30))
        start_text_rect = start_text.get_rect()
        start_text_rect.center = (SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 6 * 4)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONUP:
                pos = pygame.mouse.get_pos()
                if start_text_rect.collidepoint(*pos):
                    return

        pos = pygame.mouse.get_pos()
        if start_text_rect.collidepoint(*pos):
            if state == 0:
                sound = pygame.mixer.Sound('assets/sounds/270315__littlerobotsoundfactory__menu_navigate_03.wav')
                sound.set_volume(VOLUME)
                sound.play()
            screen.blit(start_text_select, start_text_rect)
            state = 1
        else:
            state = 0
            screen.blit(start_text, start_text_rect)

        pygame.display.flip()
        clock.tick(FPS)


def game_over_screen():
    with open('data/scores.csv', mode='a', encoding='utf8') as file:
        file.write(str(game.score)+'\n')
    state = 0
    while True:
        screen.fill((0, 0, 0))

        font_title = pygame.font.Font('assets/Retro_Gaming.ttf', 55)
        game_over_text = font_title.render('GAME OVER', True, (255, 255, 255))

        game_over_rect = game_over_text.get_rect()
        game_over_rect.center = (SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 4)
        screen.blit(game_over_text, game_over_rect)

        font = pygame.font.Font('assets/Retro_Gaming.ttf', 33)
        score_text = font.render('HI-SCORE', True, (255, 255, 255))
        score_text_rect = score_text.get_rect()
        score_text_rect.x += 10
        score_text_rect.y += 5
        screen.blit(score_text, score_text_rect)

        with open('data/scores.csv', encoding='utf8') as file:
            data = csv.reader(file)
            score = max(map(lambda x: int(x[0]), data))
        score_num_text = font.render(str(score).zfill(6), True, (255, 255, 255))
        score_num_rect = score_num_text.get_rect()
        score_num_rect.x += 15
        score_num_rect.y += 38
        screen.blit(score_num_text, score_num_rect)

        start_font = pygame.font.Font('assets/Retro_Gaming.ttf', 36)
        start_text = start_font.render('START', True, (255, 255, 255))
        start_text_select = start_font.render('START', True, (30, 254, 30))
        start_text_rect = start_text.get_rect()
        start_text_rect.center = (SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 6 * 4)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONUP:
                pos = pygame.mouse.get_pos()
                if start_text_rect.collidepoint(*pos):
                    return

        pos = pygame.mouse.get_pos()
        if start_text_rect.collidepoint(*pos):
            if state == 0:
                sound = pygame.mixer.Sound('assets/sounds/270315__littlerobotsoundfactory__menu_navigate_03.wav')
                sound.set_volume(VOLUME)
                sound.play()
            screen.blit(start_text_select, start_text_rect)
            state = 1
        else:
            screen.blit(start_text, start_text_rect)
            state = 0

        pygame.display.flip()
        clock.tick(FPS)


class Game:
    def __init__(self):
        self.player = Player()
        self.player_group = pygame.sprite.GroupSingle(self.player)

        self.score = 0
        self.setup_enemies()

        self.all_game_groups = [self.player_group, self.enemies]
        self.lives_icon = None
        self.state = 1

    def setup_enemies(self):
        self.enemies = pygame.sprite.Group()
        self.shooting = pygame.sprite.Group()

        for i in range(11):
            Enemy(self.enemies, self.shooting, image='squid_2x4.png', x=28 + 16 * i, y=30)
            self.enemies.add(Enemy(image='enemy_2x4.png', x=27 + 16 * i, y=30 + 16))
            self.enemies.add(Enemy(image='enemy_2x4.png', x=27 + 16 * i, y=30 + 16 * 2))
            self.enemies.add(Enemy(image='brute_2x5.png', x=26 + 16 * i, y=30 + 16 * 3))
            self.enemies.add(Enemy(image='brute_2x5.png', x=26 + 16 * i, y=30 + 16 * 4))
        self.all_game_groups = [self.player_group, self.enemies]

    def detect_collision(self):
        if self.player.bullet.sprite:
            for enemy in self.enemies:
                if self.player.bullet.sprite.rect.colliderect(enemy.rect):
                    self.player.bullet.sprite.kill()
                    self.score += 10
                    sound = pygame.mixer.Sound('assets/sounds/270306__littlerobotsoundfactory__explosion_02.wav')
                    sound.set_volume(VOLUME)
                    sound.play()
                    enemy.kill()
                    break
        for sprite in self.shooting.sprites():
            if sprite.bullet.sprite:
                if sprite.bullet.sprite.rect.colliderect(self.player.rect):
                    sprite.bullet.sprite.kill()
                    sound = pygame.mixer.Sound('assets/sounds/270325__littlerobotsoundfactory__hit_02.wav')
                    sound.set_volume(VOLUME + 0.2)
                    sound.play()
                    self.player.lives -= 1

    def shoot(self):
        if self.state and len(self.shooting.sprites()):
            random.choice(self.shooting.sprites()).shoot()

    def update(self):
        if self.player.lives == 0 and self.state == 1:
            sound = pygame.mixer.Sound('assets/sounds/270308__littlerobotsoundfactory__explosion_00.wav')
            sound.set_volume(VOLUME)
            sound.play()
            self.state = 0
            return
        if self.player.update() == 'DEATH':
            return 'GAME OVER'
        if not len(self.enemies.sprites()):
            return 'WIN'
        if self.state:
            self.enemies.update()
            self.detect_collision()

    def draw(self):
        font = pygame.font.Font('assets/Retro_Gaming.ttf', 33)
        score_text = font.render('SCORE', True, (255, 255, 255))
        score_text_rect = score_text.get_rect()
        score_text_rect.x += 10
        score_text_rect.y += 5
        screen.blit(score_text, score_text_rect)

        score_num_text = font.render(str(self.score).zfill(6), True, (255, 255, 255))
        score_num_rect = score_num_text.get_rect()
        score_num_rect.x += 15
        score_num_rect.y += 38
        screen.blit(score_num_text, score_num_rect)

        lives_text = font.render('LIVES', True, (255, 255, 255))
        lives_rect = lives_text.get_rect()
        lives_rect.x += 500
        lives_rect.y += 5
        screen.blit(lives_text, lives_rect)

        self.lives_icon = pygame.sprite.Group()

        for i in range(1, self.player.lives + 1):
            image = load_image('lives.png')
            image = pygame.transform.scale(image,  (image.get_rect().w * 2, image.get_rect().h * 2))
            rect = image.get_rect()
            rect.x += 600 + 56 * i
            rect.y += 10
            screen.blit(image, rect)

        for group in self.all_game_groups:
            group.draw(screen)
        self.player.bullet.draw(screen)
        for sprite in self.shooting.sprites():
            sprite.bullet.draw(screen)


if __name__ == '__main__':
    pygame.init()
    pygame.mixer.init()
    pygame.display.set_caption('Космические захватчики')
    screen = pygame.display.set_mode(SCREEN_SIZE)
    clock = pygame.time.Clock()

    title_screen()

    while True:
        timer = -1
        ENEMYSHOOT = pygame.USEREVENT
        pygame.time.set_timer(ENEMYSHOOT, 800)
        game = Game()
        pygame.mixer.music.load('assets/sounds/583613__evretro__8-bit-brisk-music-loop.wav')
        pygame.mixer.music.play(loops=-1)
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == ENEMYSHOOT:
                    game.shoot()
                    pygame.time.set_timer(ENEMYSHOOT, random.randint(1, 1600))
            screen.fill((0, 0, 0))

            res = game.update()
            if res == 'GAME OVER':

                if timer > 0:
                    timer -= 1
                else:
                    timer = 30
            if res == 'WIN':
                if timer > 0:
                    timer -= 1
                else:
                    timer = 10

            if timer == 0 and res == 'GAME OVER':

                break
            if timer == 0 and res == 'WIN':
                game.setup_enemies()
            game.draw()
            pygame.display.flip()
            clock.tick(FPS)
            timer -= 1
        game_over_screen()
