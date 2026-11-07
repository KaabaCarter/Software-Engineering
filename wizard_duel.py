"""
Wizard Duel - a simple 2D local 2-player fighting game (Pygame prototype).

Run:  pip install pygame
      python wizard_duel.py

Wizard artwork lives in wizard_art.py; the arena, spells and UI pieces in
scene_art.py (both drawn from the Claude Design canvas).
"""
import sys
import pygame
from pygame import gfxdraw
from wizard_art import draw_wizard, LOOKS
import scene_art as art
from scene_art import THEME

pygame.init()

# ---------------- Settings ----------------
WIDTH, HEIGHT = 960, 540
FPS = 60
GROUND_Y = HEIGHT - 80
GRAVITY = 0.8
JUMP_SPEED = -16
ROUNDS_TO_WIN = 2          # best 2 out of 3 (FR8)
MAX_HEALTH = 100          # default; a wizard can override it with "health"
MELEE_DAMAGE = 6
MELEE_COOLDOWN = 30
BLOCK_REDUCTION = 0.25     # blocked hits do 25% damage

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Wizard Duel")
# Each frame is drawn on this solid (no alpha channel) canvas, then copied to the
# window. On some Macs the window itself has an alpha channel, which makes
# translucent effects replace the colors under them instead of blending.
canvas = pygame.Surface((WIDTH, HEIGHT), 0, 24)
clock = pygame.time.Clock()

TITLE_FONT = art.load_font("display", 76)
HEAD_FONT = art.load_font("display", 40)
NAME_FONT = art.load_font("display", 22)
BODY_FONT = art.load_font("body", 22)
SMALL_FONT = art.load_font("body", 16)
KEY_FONT = art.load_font("body", 15)

BACKGROUND = art.build_background(WIDTH, HEIGHT, GROUND_Y)
TITLE_GLOW = pygame.transform.smoothscale(art.radial_glow(100, THEME["gold"], 90), (560, 170))
PIP_GLOW = art.radial_glow(12, THEME["gold_bright"], 150)

# Playable wizards (FR3)
# "look" picks the artwork in wizard_art.LOOKS. "power" multiplies spell damage.
WIZARDS = [
    {"name": "Ember", "look": "ember", "speed": 6, "power": 1.0, "health": 100},
    {"name": "Sage", "look": "sage", "speed": 5, "power": 1.25, "health": 100},
    {"name": "Quill", "look": "quill", "speed": 5.5, "power": 1.1, "health": 100},
    {"name": "Bramble", "look": "bramble", "speed": 4.5, "power": 1.1, "health": 120},
]

# Two spells per character (FR5). Cooldowns are in frames (60 = 1 second).
SPELLS = {
    "spell1": {"name": "Stun Bolt", "kind": "stun", "damage": 8, "speed": 12, "radius": 8,
               "cooldown": 45, "color": THEME["stun"]},
    "spell2": {"name": "Fire Blast", "kind": "fire", "damage": 15, "speed": 8, "radius": 14,
               "cooldown": 150, "color": THEME["fire"]},
}

# Key bindings for each player (FR1).
# These are PHYSICAL key positions (scancodes), named after a US QWERTY keyboard,
# so the controls sit in the same place on any layout. On a French AZERTY
# keyboard, for example, Player 1 uses Z Q S D and Player 2 uses ; : = (Mac)
# or ; : ! (Windows). The on-screen labels show the user's own layout.
CONTROLS = [
    {"left": pygame.KSCAN_A, "right": pygame.KSCAN_D, "jump": pygame.KSCAN_W,
     "block": pygame.KSCAN_S, "attack": pygame.KSCAN_F,
     "spell1": pygame.KSCAN_G, "spell2": pygame.KSCAN_H},
    {"left": pygame.KSCAN_LEFT, "right": pygame.KSCAN_RIGHT, "jump": pygame.KSCAN_UP,
     "block": pygame.KSCAN_DOWN, "attack": pygame.KSCAN_COMMA,
     "spell1": pygame.KSCAN_PERIOD, "spell2": pygame.KSCAN_SLASH},
]

# What each control does: (keys, short label for the in-game bar, long label for the Controls screen)
ACTIONS = [
    (("left", "right"), "Move", "Move"),
    (("jump",), "Jump", "Jump"),
    (("block",), "Block", "Block (shield)"),
    (("attack",), "Strike", "Wand strike"),
    (("spell1",), "Stun", "Stun Bolt"),
    (("spell2",), "Fire", "Fire Blast"),
]


ARROW_LABELS = {pygame.KSCAN_LEFT: "LEFT", pygame.KSCAN_RIGHT: "RIGHT",
                pygame.KSCAN_UP: "UP", pygame.KSCAN_DOWN: "DOWN"}
QWERTY_LABELS = {pygame.KSCAN_COMMA: ",", pygame.KSCAN_PERIOD: ".", pygame.KSCAN_SLASH: "/"}


def layout_labels():
    """Which character the user's keyboard layout puts on each physical key.

    pygame looks up held keys by turning a key code into a scancode for the
    current layout; feeding it the numbers 0..511 lets us read that mapping.
    """
    labels = {}
    try:
        lookup = pygame.key.ScancodeWrapper(range(512))
        for code in range(33, 127):                 # printable characters
            scancode = lookup[code]
            if scancode and scancode not in labels:
                labels[scancode] = chr(code).upper()
    except Exception:                               # fall back to QWERTY names
        pass
    return labels


LAYOUT_LABELS = layout_labels()


def key_label(scancode):
    """Physical key -> keycap label on this keyboard ('Z', ';', or 'LEFT' for an arrow)."""
    if scancode in ARROW_LABELS:
        return ARROW_LABELS[scancode]
    if scancode in LAYOUT_LABELS:
        return LAYOUT_LABELS[scancode]
    if scancode in QWERTY_LABELS:
        return QWERTY_LABELS[scancode]
    return chr(ord("A") + scancode - pygame.KSCAN_A)  # letter keys


class HeldKeys:
    """Which physical keys are held down, looked up by scancode."""

    def __init__(self, pressed):
        self.pressed = pressed

    def __getitem__(self, scancode):
        return tuple.__getitem__(self.pressed, scancode)


def house_color(wizard):
    return LOOKS[wizard["look"]]["house"]


def name_color(wizard):
    return art.mix(house_color(wizard), (255, 255, 255), 0.45)


# ---------------- Spell projectile ----------------
class Projectile:
    def __init__(self, owner, spell, x, y, direction, power):
        self.owner = owner
        self.x, self.y = x, y
        self.dir = direction
        self.kind = spell["kind"]
        self.speed = spell["speed"]
        self.radius = spell["radius"]
        self.color = spell["color"]
        self.damage = spell["damage"] * power
        self.alive = True
        self.tick = 0

    def rect(self):
        r = self.radius
        return pygame.Rect(self.x - r, self.y - r, r * 2, r * 2)

    def update(self, target):
        self.x += self.speed * self.dir
        self.tick += 1
        if self.kind == "fire" and self.tick % 2 == 0:
            art.spawn_embers(self.owner.fx, self.x, self.y, self.dir)
        if self.x < -50 or self.x > WIDTH + 50:
            self.alive = False
        elif self.rect().colliderect(target.rect):
            target.take_hit(self.damage, (self.x, self.y), self.color)
            self.alive = False

    def draw(self, surf):
        if self.kind == "fire":
            art.draw_fire_blast(surf, self.x, self.y, self.dir, self.tick)
        else:
            art.draw_stun_bolt(surf, self.x, self.y, self.dir, self.tick)


# ---------------- Fighter ----------------
class Fighter:
    WIDTH, HEIGHT = 50, 100

    def __init__(self, x, wizard, controls, facing):
        self.start_x = x
        self.start_facing = facing
        self.wizard = wizard
        self.controls = controls
        self.fx = []            # shared particle list, set by Game
        self.reset()

    def reset(self):
        self.rect = pygame.Rect(self.start_x, GROUND_Y - self.HEIGHT,
                                self.WIDTH, self.HEIGHT)
        self.x = float(self.start_x)   # float position so fractional speeds work
        self.vy = 0
        self.max_health = self.wizard.get("health", MAX_HEALTH)
        self.health = self.max_health
        self.lag_health = self.max_health   # amber "just lost" strip on the health bar
        self.facing = self.start_facing
        self.blocking = False
        self.attack_timer = 0
        self.hit_flash = 0
        self.cast_timer = 0
        self.moving = False
        self.anim = 0
        self.cooldowns = {"attack": 0, "spell1": 0, "spell2": 0}

    def on_ground(self):
        return self.rect.bottom >= GROUND_Y

    def attack_box(self):
        w = 45
        x = self.rect.right if self.facing == 1 else self.rect.left - w
        return pygame.Rect(x, self.rect.y + 30, w, 30)

    def take_hit(self, damage, at=None, color=None):
        if self.blocking:
            damage *= BLOCK_REDUCTION
        self.health = max(0, self.health - damage)   # FR6
        self.hit_flash = 8
        x, y = at or (self.rect.centerx, self.rect.y + 45)
        art.burst(self.fx, x, y, (159, 211, 255) if self.blocking else (color or THEME["gold_bright"]))

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
        if self.cast_timer > 0:
            self.cast_timer -= 1
        self.anim += 1

        # Movement, jump, block (FR4). Can't move while blocking.
        self.blocking = keys[c["block"]] and self.on_ground()
        self.moving = False
        if not self.blocking:
            if keys[c["left"]]:
                self.x -= self.wizard["speed"]
                self.moving = True
            if keys[c["right"]]:
                self.x += self.wizard["speed"]
                self.moving = not self.moving   # both keys held = standing still
            if keys[c["jump"]] and self.on_ground():
                self.vy = JUMP_SPEED
        self.x = max(0, min(WIDTH - self.rect.width, self.x))
        self.rect.x = round(self.x)

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
            self.cooldowns["attack"] = MELEE_COOLDOWN
            box = self.attack_box()
            if box.colliderect(other.rect):
                other.take_hit(MELEE_DAMAGE, box.clip(other.rect).center)

        # Spells (FR5)
        for slot in ("spell1", "spell2"):
            if keys[c[slot]] and self.cooldowns[slot] == 0:
                spell = SPELLS[slot]
                x = self.rect.centerx + self.facing * 50
                projectiles.append(Projectile(self, spell, x, self.rect.y + 45,
                                              self.facing, self.wizard["power"]))
                self.cooldowns[slot] = spell["cooldown"]
                self.cast_timer = 12

    def charge(self, slot):
        """0..1, how recharged an attack or spell is (1 = ready)."""
        full = MELEE_COOLDOWN if slot == "attack" else SPELLS[slot]["cooldown"]
        return 1 - self.cooldowns[slot] / full

    def pose(self):
        if self.health <= 0:
            return "ko"
        if self.hit_flash > 0:
            return "hit"
        if self.blocking:
            return "block"
        if self.attack_timer > 0:
            return "melee"
        if self.cast_timer > 0:
            return "cast"
        if not self.on_ground():
            return "jump"
        if self.moving:
            return "walk" if (self.anim // 8) % 2 == 0 else "idle"
        return "idle"

    def draw(self, surf):
        draw_wizard(surf, self.wizard["look"], self.pose(), self.rect.x, self.rect.y,
                    facing=self.facing, white=self.hit_flash > 5, tick=self.anim,
                    ground=GROUND_Y - self.rect.y)


# ---------------- Game (menus, rounds, drawing) ----------------
class Game:
    def __init__(self):
        self.running = True
        self.state = "menu"   # menu, controls, select, fight, round_over, match_over
        self.choice = [0, 1]
        self.ready = [False, False]
        self.paused = False
        self.show_keys = True  # the key bar at the bottom of the fight screen
        self.p1 = self.p2 = None
        self.projectiles = []
        self.fx = []
        self.ambient = art.Ambient(WIDTH, HEIGHT)
        self.keys = None
        self.wins = [0, 0]
        self.round_num = 0
        self.round_winner = None
        self.timer = 0
        self.tick = 0
        self.message = ""

    def start_match(self):
        self.p1 = Fighter(200, WIZARDS[self.choice[0]], CONTROLS[0], 1)
        self.p2 = Fighter(WIDTH - 250, WIZARDS[self.choice[1]], CONTROLS[1], -1)
        self.p1.fx = self.p2.fx = self.fx
        self.wins = [0, 0]
        self.round_num = 0
        self.start_round()

    def start_round(self):
        self.p1.reset()
        self.p2.reset()
        self.projectiles = []
        self.fx.clear()
        self.paused = False
        self.round_num += 1
        self.state = "fight"

    # ----- Input -----
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        if event.type != pygame.KEYDOWN:
            return
        k = event.key            # menu keys: by letter (Enter, C, Esc, Tab, Q, M)
        sc = event.scancode      # player keys: by physical position

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
                if sc == c["left"]:
                    self.choice[i] = (self.choice[i] - 1) % len(WIZARDS)
                elif sc == c["right"]:
                    self.choice[i] = (self.choice[i] + 1) % len(WIZARDS)
                elif sc == c["attack"]:
                    self.ready[i] = True
            if all(self.ready):
                self.start_match()

        elif self.state == "fight":                            # pause (FR11)
            if k == pygame.K_ESCAPE:
                self.paused = not self.paused
            elif k == pygame.K_TAB:
                self.show_keys = not self.show_keys
            elif self.paused and k == pygame.K_q:
                self.state = "menu"

        elif self.state == "match_over":                       # winner screen (FR10)
            if k == pygame.K_RETURN:
                self.start_match()
            elif k == pygame.K_m:
                self.state = "menu"

    # ----- Logic -----
    def update(self, keys):
        self.keys = keys
        self.tick += 1
        self.ambient.update()
        art.update_particles(self.fx)
        if self.state in ("fight", "round_over", "match_over") and not self.paused:
            for f in (self.p1, self.p2):         # amber "just lost" strip catches up
                f.lag_health = max(f.health, f.lag_health - 0.5)

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
                    self.round_winner = None
                elif self.p2.health <= 0:
                    self.wins[0] += 1
                    self.round_winner = self.p1
                    self.message = f"{self.p1.wizard['name']} wins the round!"
                else:
                    self.wins[1] += 1
                    self.round_winner = self.p2
                    self.message = f"{self.p2.wizard['name']} wins the round!"
                self.state = "round_over"
                self.timer = 2 * FPS

        elif self.state == "round_over":
            self.timer -= 1
            if self.timer <= 0:
                if max(self.wins) >= ROUNDS_TO_WIN:            # FR8
                    winner = self.p1 if self.wins[0] > self.wins[1] else self.p2
                    num = 1 if winner is self.p1 else 2
                    self.round_winner = winner
                    self.message = f"Player {num} ({winner.wizard['name']}) wins!"
                    self.state = "match_over"
                else:
                    self.start_round()

    # ----- Drawing: screens -----
    def draw(self, surf):
        surf.blit(BACKGROUND, (0, 0))
        self.ambient.draw(surf)
        if self.state == "menu":
            self.draw_menu(surf)
        elif self.state == "controls":
            self.draw_controls(surf)
        elif self.state == "select":
            self.draw_select(surf)
        else:  # fight, round_over, match_over
            self.draw_fight(surf)

    def draw_menu(self, surf):
        art.dim(surf, 90)
        draw_wizard(surf, "ember", "cast", 90, 250, facing=1, scale=2, tick=self.tick)
        draw_wizard(surf, "sage", "cast", WIDTH - 190, 250, facing=-1, scale=2, tick=self.tick)
        surf.blit(TITLE_GLOW, TITLE_GLOW.get_rect(center=(WIDTH // 2, 112)))
        art.text(surf, "Wizard Duel", TITLE_FONT, THEME["gold_bright"], (WIDTH // 2, 108))
        art.ornament(surf, WIDTH // 2, 168, THEME["gold"])
        art.text(surf, "TWO WIZARDS  ·  ONE KEYBOARD  ·  BEST OF THREE", SMALL_FONT,
                 THEME["parchment"], (WIDTH // 2, 196))
        for i, (label, key) in enumerate((("Play", "Enter"), ("Controls", "C"), ("Quit", "Esc"))):
            art.button(surf, (350, 250 + i * 64, 260, 52), label, key, BODY_FONT, KEY_FONT, selected=i == 0)

    def draw_controls(self, surf):
        art.dim(surf, 150)
        art.panel(surf, (90, 34, 780, 412))
        art.text(surf, "Controls", HEAD_FONT, THEME["gold_bright"], (WIDTH // 2, 76))
        for p in (0, 1):
            x0 = 130 if p == 0 else 510
            art.text(surf, f"PLAYER {p + 1}", SMALL_FONT, THEME["gold"], (x0, 120), "midleft", False)
            pygame.draw.line(surf, THEME["panel_edge"], (x0, 136), (x0 + 320, 136), 2)
            for r, (names, _, long_label) in enumerate(ACTIONS):
                y = 150 + r * 42
                art.text(surf, long_label, BODY_FONT, THEME["parchment"], (x0, y + 13), "midleft", False)
                kx = x0 + 320
                for name in reversed(names):
                    label = key_label(CONTROLS[p][name])
                    kx -= art.keycap_width(label, KEY_FONT, 28)
                    art.keycap(surf, label, kx, y, KEY_FONT, h=28)
                    kx -= 6
        art.text(surf, "Esc pauses the duel   ·   Tab shows or hides the key bar during a fight",
                 SMALL_FONT, THEME["muted"], (WIDTH // 2, 420), shadow=False)
        art.button(surf, (380, 466, 200, 50), "Back", "Esc", BODY_FONT, KEY_FONT)

    def draw_select(self, surf):
        art.dim(surf, 110)
        art.text(surf, "Choose your wizard", HEAD_FONT, THEME["gold_bright"], (WIDTH // 2, 54))
        maxes = {s: max(w.get(s, MAX_HEALTH) for w in WIZARDS) for s in ("speed", "power", "health")}
        for i in (0, 1):
            wiz = WIZARDS[self.choice[i]]
            look = LOOKS[wiz["look"]]
            box = pygame.Rect(40 if i == 0 else 500, 92, 420, 420)
            ready = self.ready[i]
            art.panel(surf, box, edge=THEME["gold_bright"] if ready else THEME["panel_edge"])
            pygame.draw.rect(surf, look["house"], (box.x + 2, box.y + 2, box.w - 4, 6),
                             border_top_left_radius=10, border_top_right_radius=10)
            art.text(surf, f"PLAYER {i + 1}", SMALL_FONT, THEME["gold"], (box.x + 20, box.y + 26),
                     "midleft", False)

            # Wizard preview with browse arrows
            cx = box.centerx
            pygame.draw.ellipse(surf, (8, 6, 16), (cx - 90, 312, 180, 22))
            draw_wizard(surf, wiz["look"], "cast" if ready else "idle", cx - 50, 122,
                        facing=1 if i == 0 else -1, scale=1.9, tick=self.tick)
            if not ready:
                for side in (-1, 1):
                    ax = cx + side * 160
                    pts = [(ax + side * 10, 220), (ax - side * 6, 208), (ax - side * 6, 232)]
                    pygame.draw.polygon(surf, THEME["muted"], pts)

            art.text(surf, wiz["name"], HEAD_FONT, name_color(wiz), (cx, 352))
            art.text(surf, look["label"], SMALL_FONT, THEME["muted"], (cx, 380), shadow=False)

            # Stat bars
            for r, (stat, label) in enumerate((("speed", "SPEED"), ("power", "POWER"), ("health", "HEALTH"))):
                y = 402 + r * 20
                value = wiz.get(stat, MAX_HEALTH)
                art.text(surf, label, KEY_FONT, THEME["parchment"], (box.x + 70, y), "midleft", False)
                bar = pygame.Rect(box.x + 150, y - 5, 190, 10)
                pygame.draw.rect(surf, THEME["bar_back"], bar, border_radius=5)
                pygame.draw.rect(surf, THEME["gold"], (bar.x, bar.y, round(bar.w * value / maxes[stat]), bar.h),
                                 border_radius=5)
                shown = f"x{value}" if stat == "power" else str(value)
                art.text(surf, shown, KEY_FONT, THEME["parchment"], (bar.right + 10, y), "midleft", False)

            # How to choose
            if ready:
                art.text(surf, "READY!", NAME_FONT, THEME["gold_bright"], (cx, 482))
            else:
                c = CONTROLS[i]
                parts = [([key_label(c["left"]), key_label(c["right"])], "change"),
                         ([key_label(c["attack"])], "confirm")]
                self.draw_key_hints(surf, parts, cx, 470, centered=True)

    def draw_fight(self, surf):
        self.p1.draw(surf)
        self.p2.draw(surf)
        for p in self.projectiles:
            p.draw(surf)
        for p in self.fx:
            p.draw(surf)
        self.draw_hud(surf)

        if self.state == "fight":
            if self.show_keys:
                self.draw_key_bar(surf)
            else:
                art.text(surf, "Tab  show keys", SMALL_FONT, THEME["muted"], (WIDTH // 2, 512), shadow=False)
            if self.paused:
                self.draw_pause(surf)
        elif self.state == "round_over":
            self.draw_round_over(surf)
        elif self.state == "match_over":
            self.draw_match_over(surf)

    def draw_pause(self, surf):
        art.dim(surf, 150)
        art.panel(surf, (300, 120, 360, 300))
        art.text(surf, "Paused", HEAD_FONT, THEME["gold_bright"], (WIDTH // 2, 168))
        art.button(surf, (330, 212, 300, 50), "Resume", "Esc", BODY_FONT, KEY_FONT, selected=True)
        art.button(surf, (330, 276, 300, 50), "Hide keys" if self.show_keys else "Show keys",
                   "Tab", BODY_FONT, KEY_FONT)
        art.button(surf, (330, 340, 300, 50), "Quit to menu", "Q", BODY_FONT, KEY_FONT)

    def draw_round_over(self, surf):
        art.dim(surf, 70)
        accent = house_color(self.round_winner.wizard) if self.round_winner else THEME["parchment"]
        band = pygame.Surface((WIDTH, 130), pygame.SRCALPHA)
        band.fill((12, 10, 26, 220))
        surf.blit(band, (0, 180))
        pygame.draw.line(surf, accent, (0, 180), (WIDTH, 180), 3)
        pygame.draw.line(surf, accent, (0, 309), (WIDTH, 309), 3)
        art.text(surf, f"ROUND {self.round_num}", SMALL_FONT, THEME["gold"], (WIDTH // 2, 206), shadow=False)
        color = THEME["gold_bright"] if self.round_winner else THEME["parchment"]
        art.text(surf, self.message, HEAD_FONT, color, (WIDTH // 2, 246))
        sub = "No point awarded" if self.round_winner is None else (
            "The duel is decided..." if max(self.wins) >= ROUNDS_TO_WIN else "Next round begins...")
        art.text(surf, sub, BODY_FONT, THEME["parchment"], (WIDTH // 2, 284), shadow=False)

    def draw_match_over(self, surf):
        art.dim(surf, 150)
        winner = self.round_winner
        box = pygame.Rect(210, 100, 540, 320)
        pygame.draw.rect(surf, house_color(winner.wizard), box.inflate(10, 10), 3, border_radius=16)
        art.panel(surf, box, edge=THEME["gold_bright"])
        art.text(surf, "MATCH OVER", SMALL_FONT, THEME["gold"], (WIDTH // 2, 136), shadow=False)
        art.text(surf, self.message, HEAD_FONT, THEME["gold_bright"], (WIDTH // 2, 186))
        # Score with round pips
        for i, f in enumerate((self.p1, self.p2)):
            side = -1 if i == 0 else 1
            anchor = "midright" if i == 0 else "midleft"
            art.text(surf, f.wizard["name"], NAME_FONT, name_color(f.wizard),
                     (WIDTH // 2 + side * 120, 250), anchor)
            for r in range(ROUNDS_TO_WIN):
                self.draw_pip(surf, WIDTH // 2 + side * (60 + r * 22), 250, r < self.wins[i])
        art.text(surf, f"{self.wins[0]} – {self.wins[1]}", NAME_FONT, THEME["parchment"], (WIDTH // 2, 250))
        art.button(surf, (250, 330, 220, 50), "Rematch", "Enter", BODY_FONT, KEY_FONT, selected=True)
        art.button(surf, (490, 330, 220, 50), "Menu", "M", BODY_FONT, KEY_FONT)

    # ----- Drawing: HUD -----
    def draw_pip(self, surf, x, y, won):
        if won:
            surf.blit(PIP_GLOW, (x - 12, y - 12))
            gfxdraw.filled_circle(surf, x, y, 7, THEME["gold_bright"])
        else:
            gfxdraw.filled_circle(surf, x, y, 7, THEME["bar_back"])
        gfxdraw.aacircle(surf, x, y, 7, THEME["gold"])

    def draw_hud(self, surf):
        bar_w, bar_h, y = 380, 18, 24
        for i, f in enumerate((self.p1, self.p2)):
            x = 30 if i == 0 else WIDTH - 30 - bar_w
            house = house_color(f.wizard)

            def span(amount):
                w = round(bar_w * amount / f.max_health)
                return pygame.Rect(x if i == 0 else x + bar_w - w, y, w, bar_h)

            pygame.draw.rect(surf, THEME["bar_back"], (x - 3, y - 3, bar_w + 6, bar_h + 6), border_radius=6)
            pygame.draw.rect(surf, THEME["window"], span(f.lag_health), border_radius=4)
            hp = span(f.health)
            pygame.draw.rect(surf, house, hp, border_radius=4)
            pygame.draw.rect(surf, art.mix(house, (255, 255, 255), 0.35), (hp.x, hp.y, hp.w, 5), border_radius=3)
            low = f.health < f.max_health * 0.25 and (self.tick // 15) % 2 == 0
            pygame.draw.rect(surf, THEME["danger"] if low else THEME["gold"],
                             (x - 3, y - 3, bar_w + 6, bar_h + 6), 2, border_radius=6)

            # P1/P2 chip, name and round pips under the bar
            chip = SMALL_FONT.render(f"P{i + 1}", True, (255, 255, 255))
            name = NAME_FONT.render(f.wizard["name"], True, THEME["parchment"])
            cw = chip.get_width() + 12
            row_y = y + bar_h + 18
            if i == 0:
                chip_x, name_x = x, x + cw + 8
                pip_x = [name_x + name.get_width() + 18 + r * 22 for r in range(ROUNDS_TO_WIN)]
            else:
                chip_x = x + bar_w - cw
                name_x = chip_x - 8 - name.get_width()
                pip_x = [name_x - 18 - r * 22 for r in range(ROUNDS_TO_WIN)]
            pygame.draw.rect(surf, house, (chip_x, row_y - 10, cw, 20), border_radius=4)
            surf.blit(chip, chip.get_rect(center=(chip_x + cw // 2, row_y)))
            surf.blit(name, name.get_rect(midleft=(name_x, row_y)))
            for r, px in enumerate(pip_x):
                self.draw_pip(surf, px, row_y, r < self.wins[i])

        # Round plaque
        plaque = art.panel(surf, (WIDTH // 2 - 44, 12, 88, 54), radius=8)
        art.text(surf, "ROUND", KEY_FONT, THEME["gold"], (plaque.centerx, 26), shadow=False)
        art.text(surf, str(self.round_num), NAME_FONT, THEME["gold_bright"], (plaque.centerx, 49))

    def hint_width(self, parts, h, gap, font=SMALL_FONT):
        total = 0
        for labels, word, *_ in parts:
            total += sum(art.keycap_width(lb, KEY_FONT, h) + 4 for lb in labels) + 2 + font.size(word)[0]
        return total + gap * (len(parts) - 1)

    def draw_key_hints(self, surf, parts, x, y, centered=False):
        """Draw '[A][D] change  [F] confirm' style hints. parts: [([labels], word), ...]"""
        h, gap = 26, 14
        if centered:
            x -= self.hint_width(parts, h, gap) // 2
        self.draw_hint_row(surf, parts, x, y, h, gap)

    def draw_hint_row(self, surf, parts, x, y, h, gap, fighter=None, font=SMALL_FONT):
        """parts: (labels, word) or (labels, word, (slot, control names, glow color))
        for live keys that light up while held and show their recharge."""
        for labels, word, *live in parts:
            for k, lb in enumerate(labels):
                pressed, charge, glow = False, None, None
                if live:
                    slot, names, color = live[0]
                    pressed = bool(self.keys and self.keys[CONTROLS[fighter][names[k]]])
                    if slot:
                        f = self.p1 if fighter == 0 else self.p2
                        charge, glow = f.charge(slot), color
                x += art.keycap(surf, lb, x, y, KEY_FONT, h=h, pressed=pressed, charge=charge, glow=glow) + 4
            x += 2
            img = font.render(word, True, THEME["parchment"])
            surf.blit(img, img.get_rect(midleft=(x, y + h // 2 - 1)))
            x += img.get_width() + gap

    def draw_key_bar(self, surf):
        """Always-visible reminder of each player's keys. Keys light up while held;
        Strike/Stun/Fire fill up as they recharge and glow when ready."""
        glows = {"attack": THEME["gold_bright"], "spell1": THEME["stun"], "spell2": THEME["fire"]}
        h, gap, y = 24, 9, HEIGHT - 40
        for p in (0, 1):
            parts = []
            for names, short, _ in ACTIONS:
                slot = names[0] if names[0] in glows else None
                parts.append(([key_label(CONTROLS[p][n]) for n in names], short,
                              (slot, names, glows.get(slot))))
            total = self.hint_width(parts, h, gap, KEY_FONT)
            x = 18 if p == 0 else WIDTH - 18 - total
            strip = pygame.Surface((total + 20, h + 14), pygame.SRCALPHA)
            strip.fill((5, 4, 12, 150))
            surf.blit(strip, (x - 10, y - 7))
            self.draw_hint_row(surf, parts, x, y, h, gap, fighter=p, font=KEY_FONT)
        art.text(surf, "Esc  pause     Tab  hide keys", KEY_FONT, THEME["muted"],
                 (WIDTH // 2, GROUND_Y + 16), shadow=False)


def main():
    game = Game()
    while game.running:
        for event in pygame.event.get():
            game.handle_event(event)
        game.update(HeldKeys(pygame.key.get_pressed()))
        game.draw(canvas)
        screen.blit(canvas, (0, 0))
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
