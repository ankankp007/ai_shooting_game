import pygame
import random
import math
import os  
import requests
HIGHSCORE_FILE = "highscore.txt"  
LEADERBOARD_FILE = "leaderboard.txt"
# ------------------ INIT ------------------
pygame.init()

pygame.mixer.init()
pygame.mouse.set_visible(True)
pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)


WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Bullet Hell Shooter Pro")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 36)


game_state = "menu"
#game_state="leaderboard"
paused = False
difficulty = "normal"

difficulty_settings = {
    "easy": {
        "enemy_hp": 0.8,
        "enemy_speed": 0.8,
        "spawn_rate": 0.8
    },
    "normal": {
        "enemy_hp": 1.0,
        "enemy_speed": 1.0,
        "spawn_rate": 1.0
    },
    "hard": {
        "enemy_hp": 1.4,
        "enemy_speed": 1.3,
        "spawn_rate": 1.3
    }
}



# ------------------ LOAD SOUND ------------------
shoot_sound = pygame.mixer.Sound("sounds/sounds.wav")
shoot_sound.set_volume(0.4)

# ------------------ BACKGROUND ------------------
class Star:
    def __init__(self, speed_range, size_range, layer):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        self.size = random.randint(*size_range)
        self.speed = random.uniform(*speed_range)
        self.layer = layer   # NEW

    def move(self):
        self.y += self.speed
        if self.y > HEIGHT:
            self.y = 0
            self.x = random.randint(0, WIDTH)

    def draw(self, surface):

        # DEBUG COLORS
        if self.layer == "far":
            color = (120,120,255)

        elif self.layer == "mid":
            color = (255,255,255)

        else:  # near
            color = (255,200,200)

        pygame.draw.circle(
            surface,
            color,
            (int(self.x), int(self.y)),
            self.size
        )

far_stars  = [Star((0.05,0.15), (1,1), "far")  for _ in range(100)]
mid_stars  = [Star((0.4,0.8),  (2,2), "mid")  for _ in range(60)]
near_stars = [Star((1.5,3.5),  (3,4), "near") for _ in range(35)]


# ------------------ BULLET ------------------
class Bullet:
    def __init__(self, x, y, dx, dy, color, homing=False):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.radius = 5
        self.color = color
        self.homing = homing

    def move(self, target=None):
        if self.homing and target:
            dx = target.x - self.x
            dy = target.y - self.y
            angle = math.atan2(dy, dx)
            speed = math.hypot(self.dx, self.dy)
            self.dx += math.cos(angle) * 0.2
            self.dy += math.sin(angle) * 0.2
            norm = math.hypot(self.dx, self.dy)
            if norm != 0:
                self.dx = self.dx / norm * speed
                self.dy = self.dy / norm * speed

        self.x += self.dx
        self.y += self.dy

    @property
    def rect(self):
        return pygame.Rect(
            self.x - self.radius,
            self.y - self.radius,
            self.radius * 2,
            self.radius * 2
        )

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)

# ------------------ EXPLOSION ------------------
class Explosion:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.rings = [5, 10, 15]
        self.max_radius = 25

    def update(self):
        self.rings = [r + 2 for r in self.rings]

    def draw(self, surface):
        for r in self.rings:
            pygame.draw.circle(surface, (255, 165, 0), (int(self.x), int(self.y)), int(r), 2)

    def done(self):
        return all(r >= self.max_radius for r in self.rings)
# ------------------ HEALTH PACK ------------------
class HealthPack:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 10
        self.speed = 2

    @property
    def rect(self):
        return pygame.Rect(self.x - 10, self.y - 10, 20, 20)

    def move(self):
        self.y += self.speed

    def draw(self, surface):
        pygame.draw.circle(surface, (0, 255, 255), (int(self.x), int(self.y)), self.radius)
#-------------------POWER UP -----------------
class PowerUp:
    def __init__(self, x, y, type):
        self.x = x
        self.y = y
        self.type = type
        self.radius = 12
        self.speed = 2

        self.color = {
            "rapid": (255, 255, 0),
            "double": (0, 255, 255),
            "shield": (0, 200, 255),
            "nuke": (255, 0, 255),
            "weapon": (255, 120, 0),
            "boss_weapon": (255, 50, 50)  

        }[type]

    @property
    def rect(self):
        return pygame.Rect(self.x-12, self.y-12, 24, 24)

    def move(self):
        self.y += self.speed

    def draw(self, surface):
        pygame.draw.circle(surface, self.color,
                           (int(self.x), int(self.y)), self.radius)

# ------------------ PLAYER ------------------
class Player:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT - 60
        self.radius = 20
        self.color = (0, 255, 0)
        self.health = 100
        self.bullets = []
        self.shoot_cooldown = 0
        self.powerup = None
        self.powerup_timer = 0
        self.weapon = "pistol"
        self.weapon_timer = 0


    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        self.x = max(self.radius, min(WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(HEIGHT - self.radius, self.y))

    def shoot(self):

        if self.shoot_cooldown > 0:
            return

        # ---------------- PISTOL ----------------
        if self.weapon == "pistol":
            self.bullets.append(
                Bullet(self.x, self.y - self.radius, 0, -8, (255,255,0))
            )
            self.shoot_cooldown = 15

        # ---------------- DOUBLE ----------------
        elif self.weapon == "double":
            self.bullets.append(
                Bullet(self.x - 10, self.y - self.radius, 0, -8, (0,255,255))
            )
            self.bullets.append(
                Bullet(self.x + 10, self.y - self.radius, 0, -8, (0,255,255))
            )
            self.shoot_cooldown = 12

        # ---------------- SHOTGUN ----------------
        elif self.weapon == "shotgun":
            for angle in [-0.4, -0.2, 0, 0.2, 0.4]:
                dx = math.sin(angle) * 6
                dy = -6
                self.bullets.append(
                    Bullet(self.x, self.y - self.radius, dx, dy, (255,150,0))
                )
            self.shoot_cooldown = 25

        # ---------------- LASER ----------------
        elif self.weapon == "laser":
            self.bullets.append(
                Bullet(self.x, self.y - self.radius, 0, -14, (255,0,255))
            )
            self.shoot_cooldown = 8

        # ---------------- MISSILE ----------------
        elif self.weapon == "missile":
            self.bullets.append(
                Bullet(self.x, self.y - self.radius, 0, -5, (255,0,0), homing=True)
            )
            self.shoot_cooldown = 35

        shoot_sound.play()


    def draw(self, surface):

        #  Plane Nose 
        nose = (self.x, self.y - self.radius)
        left_wing = (self.x - self.radius, self.y + self.radius)
        right_wing = (self.x + self.radius, self.y + self.radius)

        pygame.draw.polygon(surface, (0, 255, 0), [nose, left_wing, right_wing])

        # -------- Wings --------
        pygame.draw.rect(
            surface,
            (0, 200, 0),
            (self.x - self.radius, self.y, self.radius * 2, 8)
        )

        # -------- Tail --------
        pygame.draw.polygon(
            surface,
            (0, 180, 0),
            [
                (self.x, self.y + self.radius),
                (self.x - 8, self.y + self.radius + 15),
            (self.x + 8, self.y + self.radius + 15),
        ]
    )

        # -------- Health Bar (same as before) --------
        pygame.draw.rect(
            surface,
            (255, 0, 0),
            (self.x - self.radius, self.y - self.radius - 10, self.radius * 2, 5)
        )

        pygame.draw.rect(
            surface,
            (0, 255, 0),
            (
                self.x - self.radius,
                self.y - self.radius - 10,
                self.radius * 2 * self.health / 100,
                5
            )
        )

        # -------- Bullets --------
        for b in self.bullets:
            b.draw(surface) 
    

# ------------------ ENEMY ------------------
class Enemy:
    def __init__(self, x, y, type="basic", wave=1):
        self.x = x
        self.y = y
        self.type = type
        if self.type == "kamikaze":
            self.radius = 25   # Bigger skull
        elif self.type == "boss":
            self.radius = 40   # Boss bigger
        else:
            self.radius = 20   # Default enemies
        self.color = {
            "basic": (255, 0, 0),
            "shooter": (0, 0, 255),
            "homing": (0, 255, 0),
            "boss": (255, 0, 255),
            "kamikaze": (255, 140, 0),
            "sniper": (200, 0, 200),
            "splitter": (0, 200, 200)
        }[type]
        # -------- Base Health --------
        base_health = {
            "basic": 20,
            "shooter": 40,
            "homing": 30,
            "boss": 200,
            "kamikaze": 15,
            "sniper": 35,
            "splitter": 25
        }[type]
        mult = difficulty_settings[difficulty]["enemy_hp"]
        # -------- FINal health--------------
        self.health = int((base_health + wave * 5) * mult)

        self.bullets = []
        self.direction = 1
        self.shoot_cooldown = random.randint(50, 150)
        self.speed = 1.5 + wave * 0.2

    def move(self, wave):

        # -------- BOSS --------
        if self.type == "boss":
            self.x += math.sin(pygame.time.get_ticks() / 500) * 2

        # -------- HOMING --------
        elif self.type == "homing":
            if self.x < player.x:
                self.x += self.speed
            if self.x > player.x:
                self.x -= self.speed
            if self.y < player.y - 200:
                self.y += self.speed

        # -------- KAMIKAZE --------
        elif self.type == "kamikaze":
            dx = player.x - self.x
            dy = player.y - self.y
            dist = math.hypot(dx, dy)
            if dist != 0:
                self.x += (dx / dist) * (self.speed + 2)
                self.y += (dy / dist) * (self.speed + 2)

        # -------- SNIPER --------
        elif self.type == "sniper":
            self.y += 0.3   # slow drift down

        # -------- SPLITTER --------
        elif self.type == "splitter":
            self.x += self.direction * self.speed * 0.8
            if self.x < self.radius or self.x > WIDTH - self.radius:
                self.direction *= -1
                self.y += 25

        # -------- DEFAULT --------
        else:
            self.x += self.direction * self.speed
            if self.x < self.radius or self.x > WIDTH - self.radius:
                self.direction *= -1
                self.y += 20

       

    def shoot(self):
        if self.type == "basic":
            return

        if self.shoot_cooldown <= 0:
            if self.type == "shooter":
                for angle in [-0.3, 0, 0.3]:
                    self.bullets.append(
                        Bullet(self.x, self.y + self.radius, math.sin(angle) * 5, 5, self.color)
                    )
            elif self.type == "homing":
                self.bullets.append(
                    Bullet(self.x, self.y + self.radius, 0, 5, self.color, homing=True)
                )
            elif self.type == "boss":
                for i in range(0, 360, 30):
                    rad = math.radians(i + pygame.time.get_ticks() / 5 % 360)
                    self.bullets.append(
                        Bullet(self.x, self.y, math.cos(rad) * 3, math.sin(rad) * 3, self.color)
                    )
            elif self.type == "sniper":
                dx = player.x - self.x
                dy = player.y - self.y
                dist = math.hypot(dx, dy)
                if dist != 0:
                    self.bullets.append(
                        Bullet(
                            self.x,
                            self.y + self.radius,
                            (dx / dist) * 7,
                            (dy / dist) * 7,
                            self.color
                        )
                    )

            shoot_sound.play()  
            self.shoot_cooldown = random.randint(30, 100)
        else:
            self.shoot_cooldown -= 1

    def draw(self, surface):

        
        if self.type == "kamikaze":

            # Skull head
            pygame.draw.circle(
                surface,
                (255, 255, 255),
                (int(self.x), int(self.y)),
                self.radius
            )

            pygame.draw.circle(surface, (0, 0, 0),
                            (int(self.x - 8), int(self.y - 5)), 5)
            pygame.draw.circle(surface, (0, 0, 0),
                            (int(self.x + 8), int(self.y - 5)), 5)

            # Nose
            pygame.draw.polygon(
                surface,
                (0, 0, 0),
                [
                    (self.x, self.y),
                    (self.x - 4, self.y + 6),
                    (self.x + 4, self.y + 6)
                ]
            )

            # Teeth
            pygame.draw.rect(
                surface,
                (0, 0, 0),
                (self.x - 8, self.y + 8, 16, 6)
            )

        # -------- OTHER ENEMIES --------
        else:
            pygame.draw.circle(
                surface,
                self.color,
                (int(self.x), int(self.y)),
                self.radius
            )

        # -------- DRAW BULLETS --------
        for b in self.bullets:
            b.draw(surface)

# ------------------ GAME SETUP ------------------
player = Player()
wave = 1
score = 0
score_saved=False
if os.path.exists(HIGHSCORE_FILE):
    with open(HIGHSCORE_FILE, "r") as f:
        high_score = int(f.read())
else:
    high_score = 0
enemies = []
explosions = []
health_packs = []
powerups = []
frame_count = 0

def spawn_wave(wave):

    result = []

    # -------- BOSS WAVE --------
    if wave % 5 == 0:
        result.append(
            Enemy(WIDTH // 2, 100, type="boss", wave=wave)
        )

    else:
        # -------- DIFFICULTY SPAWN SCALE--------
        spawn_mult = difficulty_settings[difficulty]["spawn_rate"]
        enemy_count = int((wave + 2) * spawn_mult)
        for _ in range(enemy_count):
            t = random.choices(
                ["basic", "shooter", "homing", "kamikaze", "sniper", "splitter"],
                [0.30, 0.20, 0.15, 0.15, 0.10, 0.10]
            )[0]
            result.append(
                Enemy(
                    random.randint(50, WIDTH - 50),
                    random.randint(50, 150),
                    t,
                    wave
                )
            )

    return result


enemies = spawn_wave(wave)
#---------------NMAE INPUT FUNC------------------
def get_player_name():

    name = ""
    entering = True

    while entering:
        screen.fill((0, 0, 0))

        text = font.render("ENTER YOUR NAME:", True, (255, 255, 255))
        name_text = font.render(name, True, (0, 255, 0))

        screen.blit(text, (WIDTH // 2 - 150, HEIGHT // 2 - 50))
        screen.blit(name_text, (WIDTH // 2 - 100, HEIGHT // 2))

        pygame.display.update()

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            if event.type == pygame.KEYDOWN:

                if event.key == pygame.K_RETURN:
                    entering = False

                elif event.key == pygame.K_BACKSPACE:
                    name = name[:-1]

                else:
                    if len(name) < 10:
                        name += event.unicode

    return name if name else "Player"
#----------------------------
def save_to_leaderboard(name, score):

    with open(LEADERBOARD_FILE, "a") as f:
        f.write(f"{name} - {score}\n")

#----------------------RESET BUTTON--------------
def reset_game():
    global player, enemies, explosions, health_packs
    global score, wave, frame_count

    player = Player()
    enemies = spawn_wave(1)
    explosions = []
    health_packs = []
    score = 0
    wave = 1
    frame_count = 0
    score_saved=False
#-------------------MENU------------------------
def draw_menu():

    global difficulty

    screen.fill((0, 0, 0))

    # -------- TITLE --------
    title = font.render("BULLET HELL SHOOTER", True, (255, 0, 0))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 120))

    # -------- START --------
    start_btn = draw_button(
        "START",
        WIDTH//2 - 100, 220, 200, 50,
        (0, 255, 0), (0, 200, 0)
    )

    # -------- DIFFICULTY LABEL --------
    diff_text = font.render(f"DIFFICULTY: {difficulty.upper()}", True, (255, 255, 255))
    screen.blit(diff_text, (WIDTH//2 - diff_text.get_width()//2, 290))

    # -------- DIFFICULTY BUTTONS --------
    easy_btn = draw_button(
        "EASY",
        WIDTH//2 - 220, 340, 120, 40,
        (100, 255, 100), (50, 200, 50)
    )

    normal_btn = draw_button(
        "NORMAL",
        WIDTH//2 - 60, 340, 120, 40,
        (255, 255, 100), (200, 200, 50)
    )

    hard_btn = draw_button(
        "HARD",
        WIDTH//2 + 100, 340, 120, 40,
        (255, 100, 100), (200, 50, 50)
    )

    # -------- EXIT --------
    quit_btn = draw_button(
        "EXIT",
        WIDTH//2 - 100, 410, 200, 50,
        (255, 100, 100), (200, 50, 50)
    )

    pygame.display.update()

    return start_btn, quit_btn, easy_btn, normal_btn, hard_btn

#-----------leaderboard---------------------------
def draw_leaderboard():

    global leader_anim_x, leader_anim_done
    screen.fill((0, 0, 0))
    title = font.render("LEADERBOARD", True, (255, 215, 0))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
    scores = []
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, "r") as f:
            scores = f.readlines()
    scores = [s.strip() for s in scores if "-" in s]
    scores.sort(key=lambda x: int(x.split("-")[1]), reverse=True)
    # -------- ANIMATION MOVE --------
    if leader_anim_x < WIDTH//2 - 150:
        leader_anim_x += 10   # Speed
    else:
        leader_anim_done = True

    # -------- DRAW SCORES --------
    y = 120
    for i, line in enumerate(scores[:10]):

        text = font.render(f"{i+1}. {line}", True, (255, 255, 255))

        screen.blit(text, (leader_anim_x, y))
        y += 40

    
    return_btn = draw_button(
    "RETURN",
    WIDTH//2 - 100,
    HEIGHT - 60,
    200,
    40,
    (255, 200, 0),
    (200, 150, 0)
    )


    pygame.display.update()
    return return_btn   # 👈 ADD THIS LINE

#--------------------button
def draw_button(text, x, y, w, h, color, hover_color):

    mouse = pygame.mouse.get_pos()
    rect = pygame.Rect(x, y, w, h)

    if rect.collidepoint(mouse):
        pygame.draw.rect(screen, hover_color, rect)
    else:
        pygame.draw.rect(screen, color, rect)


    label = font.render(text, True, (0, 0, 0))
    screen.blit(label, (x + w//2 - label.get_width()//2,
                        y + h//2 - label.get_height()//2))

    return rect

leader_anim_x = -400   
leader_anim_done = False


# ------------------ MAIN LOOP ------------------
#player_name = get_player_name()

running = True
while running:
    if game_state == "leaderboard":
        return_btn = draw_leaderboard()
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            # Keyboard return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_state = "menu"

            # Mouse return
            if event.type == pygame.MOUSEBUTTONDOWN:
                if return_btn.collidepoint(event.pos):
                    game_state = "menu"

        continue

    if game_state == "menu":
        #----get menu----
        mouse = pygame.mouse.get_pos()
        hovering = False
    # Draw buttons
        start_btn, quit_btn, easy_btn, normal_btn, hard_btn = draw_menu()
    #--------------cursor control-----
        if (
            start_btn.collidepoint(mouse) or
            quit_btn.collidepoint(mouse) or
            easy_btn.collidepoint(mouse) or
            normal_btn.collidepoint(mouse) or
            hard_btn.collidepoint(mouse)
        ):
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
        else:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
    #---------------EVENTS--------------
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            # -------- MOUSE CLICK --------
            if event.type == pygame.MOUSEBUTTONDOWN:

                if start_btn.collidepoint(event.pos):
                    player_name = get_player_name()
                    reset_game()
                    game_state = "playing"

                if quit_btn.collidepoint(event.pos):
                    pygame.quit()
                    exit()
#----------------DIFFICULTY----------------
                if easy_btn.collidepoint(event.pos):
                    difficulty = "easy"

                if normal_btn.collidepoint(event.pos):
                    difficulty = "normal"

                if hard_btn.collidepoint(event.pos):
                    difficulty = "hard"
        continue

    screen.fill((10, 10, 20))
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                paused = not paused

    if paused:
    # Dark overlay
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(150)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # Pause text
        pause_text = font.render("PAUSED", True, (255, 255, 0))
        info_text = font.render("Press P to Resume", True, (200, 200, 200))

        screen.blit(
            pause_text,
            (WIDTH//2 - pause_text.get_width()//2, HEIGHT//2 - 40)
        )

        screen.blit(
            info_text,
            (WIDTH//2 - info_text.get_width()//2, HEIGHT//2 + 10)
        )

        pygame.display.update()
        clock.tick(60)
        continue
    frame_count += 1
    #-----------HEALTH PACK SPAWN----------------
    if random.randint(1, 800) == 1:
       health_packs.append(
           HealthPack(random.randint(20, WIDTH - 20), 0)
    )
#-----------------POERUP SPAWN-------------------
    if random.randint(1, 120) == 1:
        powerups.append(
            PowerUp(
                random.randint(40, WIDTH - 40),
                0,
                random.choice(["rapid", "double", "shield", "nuke", "weapon"])
            )
        )
    screen.fill((5, 5, 20))  # dark space background

    for star in far_stars:
        star.move()
        star.draw(screen)

    for star in mid_stars:
        star.move()
        star.draw(screen)

    for star in near_stars:
        star.move()
        star.draw(screen)


    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
           if event.key == pygame.K_p:
              paused = not paused

    keys = pygame.key.get_pressed()
    dx = dy = 0
    if keys[pygame.K_LEFT]: dx = -5
    if keys[pygame.K_RIGHT]: dx = 5
    if keys[pygame.K_UP]: dy = -5
    if keys[pygame.K_DOWN]: dy = 5
    player.move(dx, dy)
  #-----------------POWERUP SETUP--------------
    if player.powerup:
        player.powerup_timer -= 1
        if player.powerup_timer <= 0:
            player.powerup = None
  #-----------------WEAPON TIMER---------------
    if player.weapon != "pistol":
        player.weapon_timer -= 1
        if player.weapon_timer <= 0:
            player.weapon = "pistol"
   #------------------         
    if keys[pygame.K_SPACE]:
        player.shoot()

    if player.shoot_cooldown > 0:
        player.shoot_cooldown -= 1

    for b in player.bullets[:]:
        b.move()
        bullet_removed = False
        for e in enemies:
            if e.health > 0 and b.rect.colliderect(
                pygame.Rect(e.x - e.radius, e.y - e.radius, e.radius * 2, e.radius * 2)
            ):
                e.health -= 10
                shoot_sound.play()
                if b in player.bullets:
                    player.bullets.remove(b)
                bullet_removed = True

                if e.health <= 0:
                    score += 10
                    explosions.append(Explosion(e.x, e.y))
                    if e.type == "boss":
                       powerups.append(PowerUp(e.x, e.y, "boss_weapon"))
                    if e.type == "splitter":
                        enemies.append(Enemy(e.x - 15, e.y, "basic", wave))
                        enemies.append(Enemy(e.x + 15, e.y, "basic", wave))
                break
        if not bullet_removed and b.y < 0:
          if b in player.bullets:
            player.bullets.remove(b)

    for e in enemies:
        if e.health > 0:
            e.move(wave)
            e.shoot()
            if e.type == "kamikaze":

                enemy_rect = pygame.Rect(
                    e.x - e.radius,
                    e.y - e.radius,
                    e.radius * 2,
                    e.radius * 2
                )

                player_rect = pygame.Rect(
                    player.x - player.radius,
                    player.y - player.radius,
                    player.radius * 2,
                    player.radius * 2
                )

                if enemy_rect.colliderect(player_rect):
                    player.health -= 20
                    explosions.append(Explosion(e.x, e.y))
                    e.health = 0
        for b in e.bullets[:]:
            b.move(player)
            if b.rect.colliderect(
                pygame.Rect(player.x - player.radius, player.y - player.radius,
                            player.radius * 2, player.radius * 2)
            ):
                if player.powerup != "shield":
                   player.health -= 5
                shoot_sound.play()
                e.bullets.remove(b)
            elif b.y > HEIGHT:
                e.bullets.remove(b)
        # ------------------ HEALTH PACK LOGIC ------------------
    for hp in health_packs[:]:
        hp.move()

        if hp.rect.colliderect(
            pygame.Rect(
                player.x - player.radius,
                player.y - player.radius,
                player.radius * 2,
                player.radius * 2
            )
        ):
            player.health = min(100, player.health + 30)
            health_packs.remove(hp)
     
        elif hp.y > HEIGHT:
            health_packs.remove(hp)
#-----------------powerup logic-------------------
    for p in powerups[:]:
        p.move()

        if p.rect.colliderect(
            pygame.Rect(
                player.x - player.radius,
                player.y - player.radius,
                player.radius*2,
                player.radius*2
            )
        ):
            # Apply powerup
            if p.type == "nuke":
                for e in enemies:
                    explosions.append(Explosion(e.x, e.y))
                    e.health = 0
            elif p.type == "weapon":

                player.weapon = random.choice([
                    "double",
                    "shotgun",
                    "laser",
                    "missile"
                ])
                player.weapon_timer = 600
            elif p.type == "boss_weapon":

                player.weapon = random.choice([
                    "shotgun",
                    "laser",
                    "missile"
                ])

                player.weapon_timer = 1200   

                for e in enemies:
                    explosions.append(Explosion(e.x, e.y))
 
            else:
                player.powerup = p.type
                player.powerup_timer = 600   

            powerups.remove(p)

        elif p.y > HEIGHT:
            powerups.remove(p)

#-------------
    for ex in explosions[:]:
        ex.update()
        if ex.done():
            explosions.remove(ex)

    player.draw(screen)
    for e in enemies:
        if e.health > 0:
            e.draw(screen)
    for ex in explosions:
        ex.draw(screen)
    for hp in health_packs:     
        hp.draw(screen)
    for p in powerups:
        p.draw(screen)

    if all(e.health <= 0 for e in enemies):
        wave += 1
        enemies = spawn_wave(wave)

    score_text = font.render(f"Score: {score}  Wave: {wave}", True, (255, 255, 255))
    screen.blit(score_text, (10, 10))
    #-------POWERUP UI-----------
    if player.powerup:
        p_text = font.render(
            f"POWER: {player.powerup.upper()}", True, (255, 255, 0)
        )
        screen.blit(p_text, (10, 40))
    #---------weapon ui---------------
    weapon_text = font.render(
        f"WEAPON: {player.weapon.upper()}",
        True,
        (255,150,0)
    )
    screen.blit(weapon_text, (10, 70))

    if player.health <= 0 and not score_saved:
        #player_name = get_player_name()
        if score > high_score:
            high_score = score
            with open(HIGHSCORE_FILE, "w") as f:
                f.write(str(high_score))
        
        with open(LEADERBOARD_FILE, "a") as f:
            f.write(f"{player_name} - {score}\n")
        game_state="leaderbaord"
    
        shoot_sound.play()
        screen.fill((0, 0, 0))

        over_text = font.render("GAME OVER", True, (255, 0, 0))
        name_text = font.render(f"PLAYER: {player_name}", True, (0, 255, 255))
        score_text2 = font.render(f"SCORE: {score}", True, (255, 255, 255))
        high_text = font.render(f"HIGH SCORE: {high_score}", True, (255, 255, 0))

        retry_btn = draw_button(
            "RETRY",
            WIDTH//2 - 100, HEIGHT//2 + 80,
            200, 40,
            (0, 255, 0), (0, 200, 0)
        )

        exit_btn = draw_button(
            "EXIT",
            WIDTH//2 - 100, HEIGHT//2 + 130,
            200, 40,
            (255, 100, 100), (200, 50, 50)
        )

        leader_btn = draw_button(
            "LEADERBOARD",
            WIDTH//2 - 100, HEIGHT//2 + 180,
            200, 40,
            (0, 200, 255), (0, 150, 200)
        )


        screen.blit(over_text, (WIDTH//2 - over_text.get_width()//2, HEIGHT//2 - 120))
        screen.blit(name_text, (WIDTH//2 - name_text.get_width()//2, HEIGHT//2 - 60))
        screen.blit(score_text2, (WIDTH//2 - score_text2.get_width()//2, HEIGHT//2 - 20))
        screen.blit(high_text, (WIDTH//2 - high_text.get_width()//2, HEIGHT//2 + 20))

    

        pygame.display.update()
        waiting = True
        while waiting:
         if event.type == pygame.MOUSEBUTTONDOWN:

            if retry_btn.collidepoint(event.pos):
                reset_game()
                waiting = False
                game_state = "playing"

            if exit_btn.collidepoint(event.pos):
                pygame.quit()
                exit()

            if leader_btn.collidepoint(event.pos):
                game_state = "leaderboard"
                waiting = False

         for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            if event.type == pygame.KEYDOWN:
                  if event.key == pygame.K_r:   # Retry
                    reset_game()
                    waiting = False
                    game_state="playing"

                  if event.key == pygame.K_ESCAPE:  # Exit
                    pygame.quit()
                    exit()
                  if event.key == pygame.K_l:   # Leaderboard
                    game_state = "leaderboard"
                    waiting = False

 

    pygame.display.update()
    clock.tick(60)
pygame.quit()
