"""
Ani Washington

Wizard Duel - a simple 2D local 2-player fighting game (Pygame prototype).

Run:  pip install pygame-ce
      python wizard_duel.py

We can update the characters later but for now I put them as shapes
"""
import sys
import pygame

pygame.init()

# ---------------- Settings ----------------
WIDTH, HEIGHT = 960, 540
FPS = 60
GROUND_Y = HEIGHT - 80
GRAVITY = 0.8
JUMP_SPEED = -16
ROUNDS_TO_WIN = 2          # best 2 out of 3 (FR8)
MAX_HEALTH = 100
MELEE_DAMAGE = 6
BLOCK_REDUCTION = 0.25     # blocked hits do 25% damage

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GOLD = (230, 190, 60)
GRAY = (150, 150, 160)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Wizard Duel")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont(None, 32)
SMALL_FONT = pygame.font.SysFont(None, 24)
BIG_FONT = pygame.font.SysFont(None, 72)

# Playable wizards (FR3)
WIZARDS = [
    {"name": "Ember", "color": (200, 60, 50), "speed": 6, "power": 1.0},
    {"name": "Sage", "color": (60, 160, 90), "speed": 5, "power": 1.25},
]

# Two spells per character (FR5). Cooldowns are in frames (60 = 1 second).
SPELLS = {
    "spell1": {"name": "Stun Bolt", "damage": 8, "speed": 12, "radius": 8,
               "cooldown": 45, "color": (120, 180, 255)},
    "spell2": {"name": "Fire Blast", "damage": 15, "speed": 8, "radius": 14,
               "cooldown": 150, "color": (255, 140, 40)},
}

# Key bindings for each player (FR1)
CONTROLS = [
    {"left": pygame.K_a, "right": pygame.K_d, "jump": pygame.K_w,
     "block": pygame.K_s, "attack": pygame.K_f,
     "spell1": pygame.K_g, "spell2": pygame.K_h},
    {"left": pygame.K_LEFT, "right": pygame.K_RIGHT, "jump": pygame.K_UP,
     "block": pygame.K_DOWN, "attack": pygame.K_COMMA,
     "spell1": pygame.K_PERIOD, "spell2": pygame.K_SLASH},
]
CONTROL_TEXT = [
    "Player 1:  A/D move   W jump   S block   F attack   G Stun Bolt   H Fire Blast",
    "Player 2:  Arrows move/jump   Down block   , attack   . Stun Bolt   / Fire Blast",
    "ESC pauses the match.",
]


def draw_text(surf, text, font, color, center):
    img = font.render(text, True, color)
    surf.blit(img, img.get_rect(center=center))


# ---------------- Spell projectile ----------------
class Projectile:
    def __init__(self, owner, spell, x, y, direction, power):
        self.owner = owner
        self.x, self.y = x, y
        self.dir = direction
        self.speed = spell["speed"]
        self.radius = spell["radius"]
        self.color = spell["color"]
        self.damage = spell["damage"] * power
        self.alive = True

    def rect(self):
        r = self.radius
        return pygame.Rect(self.x - r, self.y - r, r * 2, r * 2)

    def update(self, target):
        self.x += self.speed * self.dir
        if self.x < -50 or self.x > WIDTH + 50:
            self.alive = False
        elif self.rect().colliderect(target.rect):
            target.take_hit(self.damage)
            self.alive = False

    def draw(self, surf):
        pos = (int(self.x), int(self.y))
        pygame.draw.circle(surf, self.color, pos, self.radius)
        pygame.draw.circle(surf, WHITE, pos, self.radius // 2)


# ---------------- Fighter ----------------
class Fighter:
    WIDTH, HEIGHT = 50, 100

    def __init__(self, x, wizard, controls, facing):
        self.start_x = x
        self.start_facing = facing
        self.wizard = wizard
        self.controls = controls
        self.reset()

    def reset(self):
        self.rect = pygame.Rect(self.start_x, GROUND_Y - self.HEIGHT,
                                self.WIDTH, self.HEIGHT)
        self.vy = 0
        self.health = MAX_HEALTH
        self.facing = self.start_facing
        self.blocking = False
        self.attack_timer = 0
        self.hit_flash = 0
        self.cooldowns = {"attack": 0, "spell1": 0, "spell2": 0}

    def on_ground(self):
        return self.rect.bottom >= GROUND_Y

    def attack_box(self):
        w = 45
        x = self.rect.right if self.facing == 1 else self.rect.left - w
        return pygame.Rect(x, self.rect.y + 30, w, 30)

    def take_hit(self, damage):
        if self.blocking:
            damage *= BLOCK_REDUCTION
        self.health = max(0, self.health - damage)   # FR6
        self.hit_flash = 8

    def update(self, keys, other, projectiles):
        c = self.controls

        # Timers count down every frame
        for k in self.cooldowns:
            if self.cooldowns[k] > 0:
                self.cooldowns[k] -= 1
        if self.attack_timer > 0:
            self.attack_timer -= 1
        if self.hit_flash > 0:
            self.hit_flash -= 1

        # Movement, jump, block (FR4). Can't move while blocking.
        self.blocking = keys[c["block"]] and self.on_ground()
        if not self.blocking:
            if keys[c["left"]]:
                self.rect.x -= self.wizard["speed"]
            if keys[c["right"]]:
                self.rect.x += self.wizard["speed"]
            if keys[c["jump"]] and self.on_ground():
                self.vy = JUMP_SPEED
        self.rect.x = max(0, min(WIDTH - self.rect.width, self.rect.x))

        # Gravity
        self.vy += GRAVITY
        self.rect.y += int(self.vy)
        if self.rect.bottom >= GROUND_Y:
            self.rect.bottom = GROUND_Y
            self.vy = 0

        # Always face the opponent
        self.facing = 1 if other.rect.centerx > self.rect.centerx else -1

        if self.blocking:
            return

        # Basic attack (FR5)
        if keys[c["attack"]] and self.cooldowns["attack"] == 0:
            self.attack_timer = 8
            self.cooldowns["attack"] = 30
            if self.attack_box().colliderect(other.rect):
                other.take_hit(MELEE_DAMAGE)

        # Spells (FR5)
        for slot in ("spell1", "spell2"):
            if keys[c[slot]] and self.cooldowns[slot] == 0:
                spell = SPELLS[slot]
                x = self.rect.centerx + self.facing * 50
                projectiles.append(Projectile(self, spell, x, self.rect.y + 45,
                                              self.facing, self.wizard["power"]))
                self.cooldowns[slot] = spell["cooldown"]

    def draw(self, surf):
        cx, y = self.rect.centerx, self.rect.y
        robe = WHITE if self.hit_flash > 0 else self.wizard["color"]
        body = pygame.Rect(self.rect.x, y + 25, self.rect.width, self.rect.height - 25)
        pygame.draw.rect(surf, robe, body, border_radius=8)
        pygame.draw.circle(surf, (240, 210, 180), (cx, y + 15), 15)          # head
        pygame.draw.polygon(surf, (40, 40, 70),
                            [(cx - 20, y + 6), (cx + 20, y + 6), (cx, y - 30)])  # hat
        wx, wy = cx + self.facing * 22, y + 50
        pygame.draw.line(surf, (110, 70, 30), (wx, wy),
                         (wx + self.facing * 28, wy - 10), 4)                 # wand
        if self.blocking:
            pygame.draw.circle(surf, (150, 200, 255), self.rect.center, 62, 3)
        if self.attack_timer > 0:
            pygame.draw.rect(surf, GOLD, self.attack_box(), 3)


# ---------------- Game (menus, rounds, drawing) ----------------
class Game:
    def __init__(self):
        self.running = True
        self.state = "menu"   # menu, controls, select, fight, round_over, match_over
        self.choice = [0, 1]
        self.ready = [False, False]
        self.paused = False
        self.p1 = self.p2 = None
        self.projectiles = []
        self.wins = [0, 0]
        self.timer = 0
        self.message = ""

    def start_match(self):
        self.p1 = Fighter(200, WIZARDS[self.choice[0]], CONTROLS[0], 1)
        self.p2 = Fighter(WIDTH - 250, WIZARDS[self.choice[1]], CONTROLS[1], -1)
        self.wins = [0, 0]
        self.start_round()

    def start_round(self):
        self.p1.reset()
        self.p2.reset()
        self.projectiles = []
        self.paused = False
        self.state = "fight"

    # ----- Input -----
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        if event.type != pygame.KEYDOWN:
            return
        k = event.key

        if self.state == "menu":                               # start menu
            if k == pygame.K_RETURN:
                self.ready = [False, False]
                self.state = "select"
            elif k == pygame.K_c:
                self.state = "controls"
            elif k == pygame.K_ESCAPE:
                self.running = False

        elif self.state == "controls":
            if k in (pygame.K_ESCAPE, pygame.K_RETURN):
                self.state = "menu"

        elif self.state == "select":                           # character select
            if k == pygame.K_ESCAPE:
                self.state = "menu"
                return
            for i in (0, 1):
                c = CONTROLS[i]
                if self.ready[i]:
                    continue
                if k in (c["left"], c["right"]):
                    self.choice[i] = (self.choice[i] + 1) % len(WIZARDS)
                elif k == c["attack"]:
                    self.ready[i] = True
            if all(self.ready):
                self.start_match()

        elif self.state == "fight":                            # pause (FR11)
            if k == pygame.K_ESCAPE:
                self.paused = not self.paused
            elif self.paused and k == pygame.K_q:
                self.state = "menu"

        elif self.state == "match_over":                       # winner screen (FR10)
            if k == pygame.K_RETURN:
                self.start_match()
            elif k == pygame.K_m:
                self.state = "menu"

    # ----- Logic -----
    def update(self, keys):
        if self.state == "fight" and not self.paused:
            self.p1.update(keys, self.p2, self.projectiles)
            self.p2.update(keys, self.p1, self.projectiles)
            for p in self.projectiles:
                p.update(self.p2 if p.owner is self.p1 else self.p1)
            self.projectiles = [p for p in self.projectiles if p.alive]

            # Round ends when someone hits 0 health (FR7)
            if self.p1.health <= 0 or self.p2.health <= 0:
                if self.p1.health <= 0 and self.p2.health <= 0:
                    self.message = "Double KO!"
                elif self.p2.health <= 0:
                    self.wins[0] += 1
                    self.message = f"{self.p1.wizard['name']} wins the round!"
                else:
                    self.wins[1] += 1
                    self.message = f"{self.p2.wizard['name']} wins the round!"
                self.state = "round_over"
                self.timer = 2 * FPS

        elif self.state == "round_over":
            self.timer -= 1
            if self.timer <= 0:
                if max(self.wins) >= ROUNDS_TO_WIN:            # FR8
                    winner = self.p1 if self.wins[0] > self.wins[1] else self.p2
                    num = 1 if winner is self.p1 else 2
                    self.message = f"Player {num} ({winner.wizard['name']}) wins!"
                    self.state = "match_over"
                else:
                    self.start_round()

    # ----- Drawing -----
    def draw_arena(self, surf):                                # FR9
        surf.fill((25, 25, 50))
        for i in range(4):                                     # castle windows
            x = 110 + i * 230
            pygame.draw.rect(surf, (60, 60, 100), (x, 120, 60, 120), border_radius=30)
            pygame.draw.rect(surf, (230, 200, 120), (x + 8, 130, 44, 100), border_radius=22)
        pygame.draw.rect(surf, (70, 65, 75), (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
        for x in range(0, WIDTH, 80):
            pygame.draw.line(surf, (50, 45, 55), (x, GROUND_Y), (x, HEIGHT), 2)

    def draw_hud(self, surf):
        bar_w, bar_h = 380, 24
        for i, f in enumerate((self.p1, self.p2)):
            x = 30 if i == 0 else WIDTH - 30 - bar_w
            pygame.draw.rect(surf, (70, 0, 0), (x, 20, bar_w, bar_h))
            fill = int(bar_w * f.health / MAX_HEALTH)
            fx = x if i == 0 else x + bar_w - fill
            pygame.draw.rect(surf, (220, 40, 40), (fx, 20, fill, bar_h))
            pygame.draw.rect(surf, WHITE, (x, 20, bar_w, bar_h), 2)
            name = SMALL_FONT.render(f"P{i + 1} {f.wizard['name']}", True, WHITE)
            name_x = x if i == 0 else x + bar_w - name.get_width()
            surf.blit(name, (name_x, 50))
            # Round wins
            for r in range(ROUNDS_TO_WIN):
                dot_x = x + bar_w - 15 - r * 25 if i == 0 else x + 15 + r * 25
                color = GOLD if r < self.wins[i] else GRAY
                pygame.draw.circle(surf, color, (dot_x, 60), 8)
            # Spell cooldown bars
            for j, slot in enumerate(("spell1", "spell2")):
                spell = SPELLS[slot]
                ready = 1 - f.cooldowns[slot] / spell["cooldown"]
                bx, by = x + j * 130, 80
                pygame.draw.rect(surf, (40, 40, 40), (bx, by, 120, 8))
                pygame.draw.rect(surf, spell["color"], (bx, by, int(120 * ready), 8))

    def draw(self, surf):
        if self.state == "menu":
            surf.fill((20, 20, 40))
            draw_text(surf, "WIZARD DUEL", BIG_FONT, GOLD, (WIDTH // 2, 160))
            draw_text(surf, "ENTER - Play", FONT, WHITE, (WIDTH // 2, 280))
            draw_text(surf, "C - Controls", FONT, WHITE, (WIDTH // 2, 320))
            draw_text(surf, "ESC - Quit", FONT, WHITE, (WIDTH // 2, 360))

        elif self.state == "controls":
            surf.fill((20, 20, 40))
            draw_text(surf, "CONTROLS", BIG_FONT, GOLD, (WIDTH // 2, 120))
            for i, line in enumerate(CONTROL_TEXT):
                draw_text(surf, line, SMALL_FONT, WHITE, (WIDTH // 2, 230 + i * 40))
            draw_text(surf, "ENTER or ESC - Back", FONT, GRAY, (WIDTH // 2, 450))

        elif self.state == "select":
            surf.fill((20, 20, 40))
            draw_text(surf, "CHOOSE YOUR WIZARD", BIG_FONT, GOLD, (WIDTH // 2, 80))
            for i in (0, 1):
                cx = WIDTH // 4 if i == 0 else 3 * WIDTH // 4
                wiz = WIZARDS[self.choice[i]]
                pygame.draw.rect(surf, wiz["color"], (cx - 40, 180, 80, 140), border_radius=10)
                draw_text(surf, f"Player {i + 1}: {wiz['name']}", FONT, WHITE, (cx, 360))
                draw_text(surf, f"Speed {wiz['speed']}  Power x{wiz['power']}",
                          SMALL_FONT, GRAY, (cx, 395))
                status = "READY!" if self.ready[i] else (
                    "A/D change, F confirm" if i == 0 else "Left/Right change, , confirm")
                draw_text(surf, status, SMALL_FONT, GOLD if self.ready[i] else WHITE, (cx, 440))

        else:  # fight, round_over, match_over
            self.draw_arena(surf)
            self.p1.draw(surf)
            self.p2.draw(surf)
            for p in self.projectiles:
                p.draw(surf)
            self.draw_hud(surf)

            if self.state == "fight" and self.paused:
                draw_text(surf, "PAUSED", BIG_FONT, WHITE, (WIDTH // 2, HEIGHT // 2 - 30))
                draw_text(surf, "ESC resume   Q quit to menu", FONT, WHITE,
                          (WIDTH // 2, HEIGHT // 2 + 30))
            elif self.state == "round_over":
                draw_text(surf, self.message, BIG_FONT, GOLD, (WIDTH // 2, HEIGHT // 2))
            elif self.state == "match_over":
                draw_text(surf, self.message, BIG_FONT, GOLD, (WIDTH // 2, HEIGHT // 2 - 30))
                draw_text(surf, "ENTER rematch   M menu", FONT, WHITE,
                          (WIDTH // 2, HEIGHT // 2 + 30))


def main():
    game = Game()
    while game.running:
        for event in pygame.event.get():
            game.handle_event(event)
        game.update(pygame.key.get_pressed())
        game.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
