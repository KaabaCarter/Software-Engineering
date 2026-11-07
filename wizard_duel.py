"""
Wizard Duel - a simple 2D local 2-player fighting game (Pygame prototype).

Run:  pip install pygame
      python wizard_duel.py

Wizard artwork lives in wizard_art.py; the arena, spells and UI pieces in
scene_art.py (both drawn from the Claude Design canvas).
"""
import asyncio
import json
import os
import sys
import pygame
from pygame import gfxdraw
import wizard_art
from wizard_art import draw_wizard, LOOKS
import scene_art as art
import sound
from scene_art import THEME

sound.init_mixer()
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
TINY_FONT = art.load_font("body", 13)   # key bar fallback when a font is wide (e.g. in a browser)

# ---------------- Night / Day mode ----------------
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
BACKGROUND = TITLE_GLOW = PIP_GLOW = None


def load_settings():
    try:
        with open(SETTINGS_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f)
    except OSError:
        pass                      # not being able to save the mode is harmless


def apply_mode(mode):
    """Switch colors and rebuild the pre-drawn pieces that use them."""
    global BACKGROUND, TITLE_GLOW, PIP_GLOW
    art.set_theme(mode)
    wizard_art.SHIELD_EDGE = (40, 95, 140) if mode == "day" else None
    BACKGROUND = art.build_background(WIDTH, HEIGHT, GROUND_Y)
    TITLE_GLOW = pygame.transform.smoothscale(art.radial_glow(100, THEME["gold"], 90), (560, 170))
    PIP_GLOW = art.radial_glow(12, THEME["gold_bright"], 150)


apply_mode(load_settings().get("mode", "night"))
sound.enabled = load_settings().get("sound", True)
sound.load()

# Playable wizards (FR3)
# "look" picks the artwork in wizard_art.LOOKS. "power" multiplies spell damage.
# "signature" picks the wizard's own second spell from SIGNATURE_SPELLS.
WIZARDS = [
    {"name": "Ember", "look": "ember", "speed": 6, "power": 1.0, "health": 100, "signature": "fire"},
    {"name": "Sage", "look": "sage", "speed": 5, "power": 1.25, "health": 100, "signature": "vines"},
    {"name": "Quill", "look": "quill", "speed": 5.5, "power": 1.1, "health": 100, "signature": "volley"},
    {"name": "Bramble", "look": "bramble", "speed": 4.5, "power": 1.1, "health": 120, "signature": "quake"},
]

# Two spells per character (FR5): Stun Bolt for everyone, plus a signature spell.
# Cooldowns and "slow" are in frames (60 = 1 second). "color" names a THEME color.
STUN_BOLT = {"name": "Stun Bolt", "short": "Stun", "kind": "stun", "damage": 8, "speed": 12,
             "radius": 8, "cooldown": 45, "color": "stun"}
SIGNATURE_SPELLS = {
    "fire":   {"name": "Fire Blast", "short": "Fire", "about": "big, slow fireball",
               "kind": "fire", "damage": 16, "speed": 8, "radius": 14, "cooldown": 120, "color": "fire"},
    "vines":  {"name": "Vine Snare", "short": "Vines", "about": "slows the foe",
               "kind": "vines", "damage": 11, "speed": 7, "radius": 12, "cooldown": 150, "color": "vine",
               "slow": 90},
    "volley": {"name": "Arcane Volley", "short": "Volley", "about": "three quick bolts",
               "kind": "volley", "damage": 5, "speed": 13, "radius": 6, "cooldown": 120, "color": "arcane",
               "count": 3},
    "quake":  {"name": "Shockwave", "short": "Quake", "about": "rolls along the floor; jump it",
               "kind": "quake", "damage": 13, "speed": 7, "radius": 14, "cooldown": 150, "color": "quake"},
}
SLOW_FACTOR = 0.5          # Vine Snare halves movement speed while it lasts

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
    (("spell2",), "Spell", "Signature spell"),
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
    """House color, lightened at night or darkened by day so names stay readable."""
    return art.mix(house_color(wizard), THEME["name_tint"], 0.45 if art.MODE == "night" else 0.25)


# ---------------- Spell projectile ----------------
class Projectile:
    DRAW = {"stun": art.draw_stun_bolt, "fire": art.draw_fire_blast,
            "vines": art.draw_vine_snare, "volley": art.draw_arcane_bolt, "quake": art.draw_shockwave}

    def __init__(self, owner, spell, x, y, direction, power, vy=0.0):
        self.owner = owner
        self.spell = spell
        self.x, self.y = x, y
        self.vy = vy
        self.dir = direction
        self.kind = spell["kind"]
        self.speed = spell["speed"]
        self.radius = spell["radius"]
        self.damage = spell["damage"] * power
        self.alive = True
        self.tick = 0

    def rect(self):
        if self.kind == "quake":               # hugs the floor, so jumping dodges it
            return pygame.Rect(self.x - 16, GROUND_Y - 22, 32, 22)
        r = self.radius
        return pygame.Rect(self.x - r, self.y - r, r * 2, r * 2)

    def update(self, target):
        self.x += self.speed * self.dir
        self.y += self.vy
        self.tick += 1
        color = THEME[self.spell["color"]]
        if self.kind == "fire" and self.tick % 2 == 0:
            art.spawn_embers(self.owner.fx, self.x, self.y, self.dir)
        elif self.kind == "quake" and self.tick % 3 == 0:
            art.spawn_dust(self.owner.fx, self.x, GROUND_Y, color)
        if self.x < -50 or self.x > WIDTH + 50:
            self.alive = False
        elif self.rect().colliderect(target.rect):
            if self.spell.get("slow") and not target.blocking:
                target.slow_timer = self.spell["slow"]
            target.take_hit(self.damage, self.rect().center, color)
            self.alive = False

    def draw(self, surf):
        self.DRAW[self.kind](surf, self.x, self.y, self.dir, self.tick)


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
        self.slow_timer = 0          # Vine Snare
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
        sound.play("block" if self.blocking else "hit")
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
        if self.slow_timer > 0:
            self.slow_timer -= 1
        self.anim += 1
        speed = self.wizard["speed"] * (SLOW_FACTOR if self.slow_timer > 0 else 1)

        # Movement, jump, block (FR4). Can't move while blocking.
        self.blocking = keys[c["block"]] and self.on_ground()
        self.moving = False
        if not self.blocking:
            if keys[c["left"]]:
                self.x -= speed
                self.moving = True
            if keys[c["right"]]:
                self.x += speed
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
            sound.play("swing")
            box = self.attack_box()
            if box.colliderect(other.rect):
                other.take_hit(MELEE_DAMAGE, box.clip(other.rect).center)

        # Spells (FR5)
        for slot in ("spell1", "spell2"):
            if keys[c[slot]] and self.cooldowns[slot] == 0:
                spell = self.spell(slot)
                self.cast(spell, projectiles)
                sound.play(spell["kind"])
                self.cooldowns[slot] = spell["cooldown"]
                self.cast_timer = 12

    def spell(self, slot):
        return STUN_BOLT if slot == "spell1" else SIGNATURE_SPELLS[self.wizard["signature"]]

    def cast(self, spell, projectiles):
        x, y, power = self.rect.centerx + self.facing * 50, self.rect.y + 45, self.wizard["power"]
        if spell["kind"] == "volley":            # a fan of small bolts
            count = spell.get("count", 3)
            for k in range(count):
                vy = (k - (count - 1) / 2) * 0.9
                projectiles.append(Projectile(self, spell, x, y, self.facing, power, vy))
        elif spell["kind"] == "quake":           # starts at the wizard's feet
            projectiles.append(Projectile(self, spell, self.rect.centerx + self.facing * 40,
                                          GROUND_Y, self.facing, power))
        else:
            projectiles.append(Projectile(self, spell, x, y, self.facing, power))

    def charge(self, slot):
        """0..1, how recharged an attack or spell is (1 = ready)."""
        full = MELEE_COOLDOWN if slot == "attack" else self.spell(slot)["cooldown"]
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
        if self.slow_timer > 0 and self.health > 0:
            art.draw_snare(surf, self.rect.centerx, self.rect.bottom, self.anim)


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

    def toggle_mode(self):
        mode = "day" if art.MODE == "night" else "night"
        apply_mode(mode)
        save_settings({**load_settings(), "mode": mode})
        sound.play("click")

    def toggle_sound(self):
        sound.set_enabled(not sound.enabled)
        save_settings({**load_settings(), "sound": sound.enabled})
        sound.play("confirm")

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
                sound.play("confirm")
            elif k == pygame.K_c:
                self.state = "controls"
                sound.play("click")
            elif k == pygame.K_l:
                self.toggle_mode()
            elif k == pygame.K_v:
                self.toggle_sound()
            elif k == pygame.K_ESCAPE:
                self.running = False

        elif self.state == "controls":
            if k in (pygame.K_ESCAPE, pygame.K_RETURN):
                self.state = "menu"
                sound.play("click")

        elif self.state == "select":                           # character select
            if k == pygame.K_ESCAPE:
                self.state = "menu"
                sound.play("click")
                return
            for i in (0, 1):
                c = CONTROLS[i]
                if self.ready[i]:
                    continue
                if sc == c["left"]:
                    self.choice[i] = (self.choice[i] - 1) % len(WIZARDS)
                    sound.play("click")
                elif sc == c["right"]:
                    self.choice[i] = (self.choice[i] + 1) % len(WIZARDS)
                    sound.play("click")
                elif sc == c["attack"]:
                    self.ready[i] = True
                    sound.play("confirm")
            if all(self.ready):
                self.start_match()

        elif self.state == "fight":                            # pause (FR11)
            if k == pygame.K_ESCAPE:
                self.paused = not self.paused
                sound.play("pause")
            elif k == pygame.K_TAB:
                self.show_keys = not self.show_keys
                sound.play("click")
            elif self.paused and k == pygame.K_l:
                self.toggle_mode()
            elif self.paused and k == pygame.K_v:
                self.toggle_sound()
            elif self.paused and k == pygame.K_q:
                self.state = "menu"
                sound.play("click")

        elif self.state == "match_over":                       # winner screen (FR10)
            if k == pygame.K_RETURN:
                self.start_match()
                sound.play("confirm")
            elif k == pygame.K_m:
                self.state = "menu"
                sound.play("click")

    # ----- Logic -----
    def update(self, keys):
        self.keys = keys
        self.tick += 1
        sound.poll()
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
                sound.play("ko")

        elif self.state == "round_over":
            self.timer -= 1
            if self.timer == FPS and self.round_winner and max(self.wins) < ROUNDS_TO_WIN:
                sound.play("round_win")
            if self.timer <= 0:
                if max(self.wins) >= ROUNDS_TO_WIN:            # FR8
                    winner = self.p1 if self.wins[0] > self.wins[1] else self.p2
                    num = 1 if winner is self.p1 else 2
                    self.round_winner = winner
                    self.message = f"Player {num} ({winner.wizard['name']}) wins!"
                    self.state = "match_over"
                    sound.play("victory")
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
        art.text(surf, "Wizard Duel", TITLE_FONT, THEME["heading"], (WIDTH // 2, 108))
        art.ornament(surf, WIDTH // 2, 168, THEME["gold"])
        art.text(surf, "TWO WIZARDS  ·  ONE KEYBOARD  ·  BEST OF THREE", SMALL_FONT,
                 THEME["text"], (WIDTH // 2, 196))
        other_mode = "Day mode" if art.MODE == "night" else "Night mode"
        items = (("Play", "Enter"), ("Controls", "C"), (other_mode, "L"),
                 ("Sound: on" if sound.enabled else "Sound: off", "V"), ("Quit", "Esc"))
        for i, (label, key) in enumerate(items):
            art.button(surf, (350, 222 + i * 50, 260, 42), label, key, BODY_FONT, KEY_FONT, selected=i == 0)

    def draw_controls(self, surf):
        art.dim(surf, 150)
        art.panel(surf, (90, 34, 780, 412))
        art.text(surf, "Controls", HEAD_FONT, THEME["heading"], (WIDTH // 2, 76))
        for p in (0, 1):
            x0 = 130 if p == 0 else 510
            art.text(surf, f"PLAYER {p + 1}", SMALL_FONT, THEME["gold"], (x0, 120), "midleft", False)
            pygame.draw.line(surf, THEME["panel_edge"], (x0, 136), (x0 + 320, 136), 2)
            for r, (names, _, long_label) in enumerate(ACTIONS):
                y = 150 + r * 42
                art.text(surf, long_label, BODY_FONT, THEME["text"], (x0, y + 13), "midleft", False)
                kx = x0 + 320
                for name in reversed(names):
                    label = key_label(CONTROLS[p][name])
                    kx -= art.keycap_width(label, KEY_FONT, 28)
                    art.keycap(surf, label, kx, y, KEY_FONT, h=28)
                    kx -= 6
        art.text(surf, "Esc pauses the duel   ·   Tab shows or hides the key bar during a fight",
                 SMALL_FONT, THEME["text_muted"], (WIDTH // 2, 420), shadow=False)
        art.button(surf, (380, 466, 200, 50), "Back", "Esc", BODY_FONT, KEY_FONT)

    def draw_select(self, surf):
        art.dim(surf, 110)
        art.text(surf, "Choose your wizard", HEAD_FONT, THEME["heading"], (WIDTH // 2, 54))
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
            pygame.draw.ellipse(surf, THEME["floor_shadow"], (cx - 82, 300, 164, 20))
            draw_wizard(surf, wiz["look"], "cast" if ready else "idle", cx - 42, 140,
                        facing=1 if i == 0 else -1, scale=1.65, tick=self.tick)   # tallest hat fits
            if not ready:
                for side in (-1, 1):
                    ax = cx + side * 160
                    pts = [(ax + side * 10, 212), (ax - side * 6, 200), (ax - side * 6, 224)]
                    pygame.draw.polygon(surf, THEME["text_muted"], pts)

            art.text(surf, wiz["name"], HEAD_FONT, name_color(wiz), (cx, 340))
            art.text(surf, look["label"], SMALL_FONT, THEME["text_muted"], (cx, 374), shadow=False)
            sig = SIGNATURE_SPELLS[wiz["signature"]]
            art.text(surf, f"Signature: {sig['name']} ({sig['about']})", SMALL_FONT,
                     art.mix(THEME[sig["color"]], THEME["text"], 0.25), (cx, 395), shadow=False)

            # Stat bars
            for r, (stat, label) in enumerate((("speed", "SPEED"), ("power", "POWER"), ("health", "HEALTH"))):
                y = 418 + r * 18
                value = wiz.get(stat, MAX_HEALTH)
                art.text(surf, label, KEY_FONT, THEME["text"], (box.x + 70, y), "midleft", False)
                bar = pygame.Rect(box.x + 150, y - 5, 190, 10)
                pygame.draw.rect(surf, THEME["bar_back"], bar, border_radius=5)
                pygame.draw.rect(surf, THEME["gold"], (bar.x, bar.y, round(bar.w * value / maxes[stat]), bar.h),
                                 border_radius=5)
                shown = f"x{value}" if stat == "power" else str(value)
                art.text(surf, shown, KEY_FONT, THEME["text"], (bar.right + 10, y), "midleft", False)

            # How to choose
            if ready:
                art.text(surf, "READY!", NAME_FONT, THEME["heading"], (cx, 486))
            else:
                c = CONTROLS[i]
                parts = [([key_label(c["left"]), key_label(c["right"])], "change"),
                         ([key_label(c["attack"])], "confirm")]
                self.draw_key_hints(surf, parts, cx, 474, centered=True)

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
                art.text(surf, "Tab  show keys", SMALL_FONT, THEME["text_muted"], (WIDTH // 2, 512), shadow=False)
            if self.paused:
                self.draw_pause(surf)
        elif self.state == "round_over":
            self.draw_round_over(surf)
        elif self.state == "match_over":
            self.draw_match_over(surf)

    def draw_pause(self, surf):
        art.dim(surf, 150)
        art.panel(surf, (300, 70, 360, 380))
        art.text(surf, "Paused", HEAD_FONT, THEME["heading"], (WIDTH // 2, 112))
        items = (("Resume", "Esc"), ("Hide keys" if self.show_keys else "Show keys", "Tab"),
                 ("Day mode" if art.MODE == "night" else "Night mode", "L"),
                 ("Sound: on" if sound.enabled else "Sound: off", "V"), ("Quit to menu", "Q"))
        for i, (label, key) in enumerate(items):
            art.button(surf, (330, 150 + i * 58, 300, 48), label, key, BODY_FONT, KEY_FONT, selected=i == 0)

    def draw_round_over(self, surf):
        art.dim(surf, 70)
        accent = house_color(self.round_winner.wizard) if self.round_winner else THEME["text"]
        band = pygame.Surface((WIDTH, 130), pygame.SRCALPHA)
        band.fill(art.rgba(THEME["panel"], 225))
        surf.blit(band, (0, 180))
        pygame.draw.line(surf, accent, (0, 180), (WIDTH, 180), 3)
        pygame.draw.line(surf, accent, (0, 309), (WIDTH, 309), 3)
        art.text(surf, f"ROUND {self.round_num}", SMALL_FONT, THEME["gold"], (WIDTH // 2, 206), shadow=False)
        color = THEME["heading"] if self.round_winner else THEME["text"]
        art.text(surf, self.message, HEAD_FONT, color, (WIDTH // 2, 246))
        sub = "No point awarded" if self.round_winner is None else (
            "The duel is decided..." if max(self.wins) >= ROUNDS_TO_WIN else "Next round begins...")
        art.text(surf, sub, BODY_FONT, THEME["text"], (WIDTH // 2, 284), shadow=False)

    def draw_match_over(self, surf):
        art.dim(surf, 150)
        winner = self.round_winner
        box = pygame.Rect(210, 100, 540, 320)
        pygame.draw.rect(surf, house_color(winner.wizard), box.inflate(10, 10), 3, border_radius=16)
        art.panel(surf, box, edge=THEME["gold_bright"])
        art.text(surf, "MATCH OVER", SMALL_FONT, THEME["gold"], (WIDTH // 2, 136), shadow=False)
        art.text(surf, self.message, HEAD_FONT, THEME["heading"], (WIDTH // 2, 186))
        # Score with round pips
        for i, f in enumerate((self.p1, self.p2)):
            side = -1 if i == 0 else 1
            anchor = "midright" if i == 0 else "midleft"
            art.text(surf, f.wizard["name"], NAME_FONT, name_color(f.wizard),
                     (WIDTH // 2 + side * 120, 250), anchor)
            for r in range(ROUNDS_TO_WIN):
                self.draw_pip(surf, WIDTH // 2 + side * (60 + r * 22), 250, r < self.wins[i])
        art.text(surf, f"{self.wins[0]} – {self.wins[1]}", NAME_FONT, THEME["text"], (WIDTH // 2, 250))
        art.button(surf, (250, 330, 220, 50), "Rematch", "Enter", BODY_FONT, KEY_FONT, selected=True)
        art.button(surf, (490, 330, 220, 50), "Menu", "M", BODY_FONT, KEY_FONT)

    # ----- Drawing: HUD -----
    def draw_pip(self, surf, x, y, won):
        if won:
            surf.blit(PIP_GLOW, (x - 12, y - 12))
            gfxdraw.filled_circle(surf, x, y, 7, THEME["gold_bright"])
        else:
            gfxdraw.filled_circle(surf, x, y, 7, THEME["pip_empty"])
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
            pygame.draw.rect(surf, THEME["lag"], span(f.lag_health), border_radius=4)
            hp = span(f.health)
            pygame.draw.rect(surf, house, hp, border_radius=4)
            pygame.draw.rect(surf, art.mix(house, (255, 255, 255), 0.35), (hp.x, hp.y, hp.w, 5), border_radius=3)
            low = f.health < f.max_health * 0.25 and (self.tick // 15) % 2 == 0
            pygame.draw.rect(surf, THEME["danger"] if low else THEME["gold"],
                             (x - 3, y - 3, bar_w + 6, bar_h + 6), 2, border_radius=6)

            # P1/P2 chip, name and round pips under the bar
            chip = SMALL_FONT.render(f"P{i + 1}", True, (255, 255, 255))
            name = NAME_FONT.render(f.wizard["name"], True, THEME["text"])
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
        art.text(surf, str(self.round_num), NAME_FONT, THEME["heading"], (plaque.centerx, 49))

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
            img = font.render(word, True, THEME["text"])
            surf.blit(img, img.get_rect(midleft=(x, y + h // 2 - 1)))
            x += img.get_width() + gap

    def draw_key_bar(self, surf):
        """Always-visible reminder of each player's keys. Keys light up while held;
        Strike/Stun/Fire fill up as they recharge and glow when ready."""
        h, gap, y = 24, 7, HEIGHT - 40
        for p in (0, 1):
            f = self.p1 if p == 0 else self.p2
            sig = f.spell("spell2")
            glows = {"attack": THEME["gold_bright"], "spell1": THEME["stun"], "spell2": THEME[sig["color"]]}
            parts = []
            for names, short, _ in ACTIONS:
                if names[0] == "spell2":
                    short = sig["short"]
                slot = names[0] if names[0] in glows else None
                parts.append(([key_label(CONTROLS[p][n]) for n in names], short,
                              (slot, names, glows.get(slot))))
            # Fit each player's bar in its half of the screen, whatever font is available
            room = WIDTH // 2 - 30
            for gap, font in ((7, KEY_FONT), (4, KEY_FONT), (4, TINY_FONT), (2, TINY_FONT)):
                total = self.hint_width(parts, h, gap, font)
                if total <= room:
                    break
            x = 18 if p == 0 else WIDTH - 18 - total
            strip = pygame.Surface((total + 20, h + 14), pygame.SRCALPHA)
            strip.fill(art.rgba(THEME["panel"], 170))
            surf.blit(strip, (x - 10, y - 7))
            self.draw_hint_row(surf, parts, x, y, h, gap, fighter=p, font=font)
        art.text(surf, "Esc  pause     Tab  hide keys", KEY_FONT, THEME["text_muted"],
                 (WIDTH // 2, GROUND_Y + 16), shadow=False)


async def main():
    """The game loop. It is async so the same code also runs in a web browser
    (pygbag), where each frame must hand control back to the page."""
    game = Game()
    while game.running:
        for event in pygame.event.get():
            game.handle_event(event)
        game.update(HeldKeys(pygame.key.get_pressed()))
        game.draw(canvas)
        screen.blit(canvas, (0, 0))
        pygame.display.flip()
        clock.tick(FPS)
        await asyncio.sleep(0)
    pygame.quit()
    if sys.platform != "emscripten":      # in a browser, just stop
        sys.exit()


if __name__ == "__main__":
    asyncio.run(main())
