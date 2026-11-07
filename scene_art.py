"""
Wizard Duel - arena, spells, particles and UI pieces.

Everything here is drawn with pygame shapes. Colors live in THEME so the
whole palette can be changed in one place.
"""
import math
import os
import random
import pygame
from pygame import gfxdraw
from wizard_art import hx, star_points

# ---------------- Themes: Night and Day ----------------
# Night: dark, rich hall; only what players must read is bright.
# Day: the same hall in daylight, with light panels and dark text.
# Colors are "#hex" strings; other values are settings.
THEMES = {
    "night": {
        "sky_top": "#07060F", "sky_bottom": "#1A1430",
        "pillar": "#120E20", "pillar_edge": "#1B1530",
        "window_frame": "#2A2140", "window": "#E9A24A", "window_core": "#F7D58A",
        "window_glow": "#E9A24A", "sunbeams": False,
        "floor": "#1C1726", "floor_edge": "#4B3F5C", "floor_line": "#14101C",
        "candle": "#EFE3C8", "flame": "#FFD27A", "dust": "#F7D58A",
        "vignette": "#000000", "overlay": "#05040C", "shadow": "#000000",
        "gold": "#D9A73E", "gold_bright": "#F2C14E", "heading": "#F2C14E",
        "text": "#EFE3C8", "text_muted": "#A89DBB", "name_tint": "#FFFFFF",
        "panel": "#15112A", "panel_edge": "#3A3150", "bar_back": "#0B0914",
        "button_hi": "#EFE3C8", "button_hi_text": "#2B2420", "floor_shadow": "#080610",
        "key": "#2B2420", "key_edge": "#5A4E44", "key_lip": "#0F0C0A", "key_text": "#EFE3C8",
        "stun": "#5FD0FF", "fire": "#FF8A1F", "fire_core": "#FFC23D", "fire_hot": "#FFF3C4",
        "vine": "#5BD67A", "arcane": "#B48CFF", "quake": "#E0B04A",
        "spell_outline": False, "danger": "#FFB347", "lag": "#E9A24A", "pip_empty": "#0B0914",
    },
    "day": {
        "sky_top": "#BFB2A0", "sky_bottom": "#E6DAC6",
        "pillar": "#A89A87", "pillar_edge": "#95877A",
        "window_frame": "#5A4636", "window": "#9CCDEB", "window_core": "#E4F4FF",
        "window_glow": "#FFF6DA", "sunbeams": True,
        "floor": "#8E8070", "floor_edge": "#5E5246", "floor_line": "#7C6F61",
        "candle": "#F7EFDD", "flame": "#FFC75A", "dust": "#FFF8E8",
        "vignette": "#3C2814", "overlay": "#F6EFE2", "shadow": None,
        "gold": "#A87A1C", "gold_bright": "#C9952A", "heading": "#7A3E0B",
        "text": "#2B2420", "text_muted": "#6B5E52", "name_tint": "#000000",
        "panel": "#F5ECDA", "panel_edge": "#C9B79A", "bar_back": "#3A302A",
        "button_hi": "#2B2420", "button_hi_text": "#F5ECDA", "floor_shadow": "#6E6253",
        "key": "#2B2420", "key_edge": "#5A4E44", "key_lip": "#0F0C0A", "key_text": "#EFE3C8",
        "stun": "#1E9FD8", "fire": "#F06A0A", "fire_core": "#FFB21F", "fire_hot": "#FFF0B8",
        "vine": "#2E8B45", "arcane": "#7A4FD6", "quake": "#9A6B12",
        "spell_outline": True, "danger": "#D9480F", "lag": "#E9A24A", "pip_empty": "#F5ECDA",
    },
}
THEME = {}          # the active theme; filled by set_theme()
MODE = "night"


def set_theme(name):
    """Switch Night/Day. THEME is updated in place so every module sees it."""
    global MODE
    MODE = name
    THEME.clear()
    for k, v in THEMES[name].items():
        THEME[k] = hx(v) if isinstance(v, str) else v


set_theme("night")
WHITE = (255, 255, 255)

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")


def load_font(kind, size):
    """kind: 'display' (storybook serif) or 'body' (narrow sans).

    Uses the design's fonts if they are in assets/fonts, else system fonts
    that ship with both macOS and Windows.
    """
    files = {"display": "Cinzel-Bold.ttf", "body": "BarlowSemiCondensed-SemiBold.ttf"}
    path = os.path.join(FONT_DIR, files[kind])
    if os.path.exists(path):
        return pygame.font.Font(path, size)
    if kind == "display":
        return pygame.font.SysFont("georgia,palatino,timesnewroman", size, bold=True)
    return pygame.font.SysFont("arialnarrow,arial", size, bold=True)


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def rgba(rgb, alpha):
    return rgb[0], rgb[1], rgb[2], max(0, min(255, int(alpha)))


def text(surf, s, font, color, pos, anchor="center", shadow=True):
    img = font.render(s, True, color)
    rect = img.get_rect(**{anchor: pos})
    if shadow and THEME["shadow"]:
        sh = font.render(s, True, THEME["shadow"])
        sh.set_alpha(170)
        surf.blit(sh, rect.move(0, 2))
    surf.blit(img, rect)
    return rect


def radial_glow(radius, color, strength=120):
    """Smooth round glow: a small gradient scaled up, so there are no rings."""
    n = 48
    small = pygame.Surface((n, n), pygame.SRCALPHA)
    c = n / 2
    for y in range(n):
        for x in range(n):
            d = math.hypot(x + 0.5 - c, y + 0.5 - c) / c
            if d < 1:
                small.set_at((x, y), rgba(color, strength * (1 - d) ** 2))
    return pygame.transform.smoothscale(small, (radius * 2, radius * 2))


# ---------------- Arena ----------------
WINDOW_XS = [95, 335, 575, 815]


def build_background(width, height, ground_y):
    """The static castle hall, drawn once and reused every frame."""
    s = pygame.Surface((width, height), 0, 24)          # solid, so glows blend
    for y in range(height):
        pygame.draw.line(s, mix(THEME["sky_top"], THEME["sky_bottom"], y / height), (0, y), (width, y))
    for i in range(5):                                    # stone pillars
        x = i * 240 - 30
        pygame.draw.rect(s, THEME["pillar"], (x, 0, 60, ground_y))
        pygame.draw.line(s, THEME["pillar_edge"], (x + 59, 0), (x + 59, ground_y), 2)
        for y in range(30, ground_y, 46):
            pygame.draw.line(s, THEME["sky_top"], (x, y), (x + 60, y), 1)
    glow = radial_glow(150, THEME["window_glow"], 70)
    for x in WINDOW_XS:                                   # arched windows and their light
        s.blit(glow, (x + 45 - 150, 190 - 150))
    for x in WINDOW_XS:
        pygame.draw.rect(s, THEME["window_frame"], (x - 6, 104, 102, 176),
                         border_top_left_radius=51, border_top_right_radius=51)
        pygame.draw.rect(s, THEME["window"], (x, 112, 90, 162),
                         border_top_left_radius=45, border_top_right_radius=45)
        pygame.draw.rect(s, THEME["window_core"], (x + 18, 130, 54, 126),
                         border_top_left_radius=27, border_top_right_radius=27)
        pygame.draw.line(s, THEME["window_frame"], (x + 45, 112), (x + 45, 274), 4)
        pygame.draw.line(s, THEME["window_frame"], (x, 200), (x + 90, 200), 4)
    pygame.draw.rect(s, THEME["floor"], (0, ground_y, width, height - ground_y))
    pygame.draw.line(s, THEME["floor_edge"], (0, ground_y), (width, ground_y), 3)
    for x in range(0, width + 96, 96):
        pygame.draw.line(s, THEME["floor_line"], (x, ground_y + 3), (x - 30, height), 2)
    if THEME["sunbeams"]:                                 # light falling from each window
        beams = pygame.Surface((width, height), pygame.SRCALPHA)
        for x in WINDOW_XS:
            pygame.draw.polygon(beams, rgba(THEME["window_glow"], 46),
                                [(x + 4, 200), (x + 86, 200), (x + 190, height), (x + 40, height)])
        s.blit(beams, (0, 0))
    vignette = pygame.Surface((width, height), pygame.SRCALPHA)
    strength = 6 if MODE == "night" else 3
    for k in range(36):
        pygame.draw.rect(vignette, rgba(THEME["vignette"], strength),
                         (k * 3, k * 2, width - k * 6, height - k * 4), 6)
    s.blit(vignette, (0, 0))
    return s


class Ambient:
    """Floating candles and dust motes drifting up through the light."""

    # Between the windows and below the HUD
    CANDLES = [(42, 118), (262, 100), (488, 92), (728, 104), (936, 122), (212, 168), (690, 176)]

    def __init__(self, width, height):
        self.w, self.h = width, height
        self.tick = 0
        self.halo = radial_glow(16, THEME["flame"], 110)
        self.dust = [[random.uniform(0, width), random.uniform(0, height), random.uniform(0.15, 0.45)]
                     for _ in range(40)]

    def update(self):
        self.tick += 1
        for d in self.dust:
            d[1] -= d[2]
            d[0] += 0.15 * math.sin((self.tick + d[1]) * 0.02)
            if d[1] < 0:
                d[0], d[1] = random.uniform(0, self.w), self.h

    def draw(self, surf):
        for i, (cx, cy) in enumerate(self.CANDLES):
            y = cy + 4 * math.sin(self.tick * 0.03 + i)
            surf.blit(self.halo, (cx - 16, y - 22))
            pygame.draw.rect(surf, THEME["candle"], (cx - 3, y, 6, 18))
            flick = 3 + (self.tick // 6 + i) % 2
            gfxdraw.filled_circle(surf, cx, int(y) - 4, flick, THEME["flame"])
        for x, y, _ in self.dust:
            gfxdraw.pixel(surf, int(x), int(y), rgba(THEME["dust"], 140))


# ---------------- Particles ----------------
class Particle:
    def __init__(self, x, y, vx, vy, color, life, size, gravity=0.0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.color, self.life, self.max_life, self.size, self.gravity = color, life, life, size, gravity

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.life -= 1

    def draw(self, surf):
        t = self.life / self.max_life
        r = max(1, round(self.size * (0.4 + 0.6 * t)))
        gfxdraw.filled_circle(surf, int(self.x), int(self.y), r, rgba(self.color, 255 * t))


def burst(fx, x, y, color, count=14, speed=3.5):
    for _ in range(count):
        a = random.uniform(0, 2 * math.pi)
        v = random.uniform(0.4, 1) * speed
        fx.append(Particle(x, y, math.cos(a) * v, math.sin(a) * v,
                           random.choice((color, WHITE)), random.randint(12, 24), 3, 0.08))


def update_particles(fx):
    for p in fx:
        p.update()
    fx[:] = [p for p in fx if p.life > 0]


# ---------------- Spells ----------------
def draw_stun_bolt(surf, x, y, direction, tick):
    """Quick jet of electric-blue light: tapering streak, glow, white-hot core."""
    c = THEME["stun"]
    tail = [(x, y - 7), (x - direction * 46, y - 1), (x - direction * 46, y + 1), (x, y + 7)]
    gfxdraw.filled_polygon(surf, [(round(px), round(py)) for px, py in tail], rgba(c, 120))
    gfxdraw.filled_circle(surf, int(x), int(y), 16, rgba(c, 55))
    gfxdraw.filled_circle(surf, int(x), int(y), 10, rgba(c, 140))
    gfxdraw.filled_circle(surf, int(x), int(y), 6, c)
    gfxdraw.filled_circle(surf, int(x), int(y), 3, WHITE)
    if THEME["spell_outline"]:
        gfxdraw.aacircle(surf, int(x), int(y), 10, mix(c, (0, 0, 0), 0.5))
    if tick % 4 < 2:
        pygame.draw.polygon(surf, WHITE, star_points(x + direction * 6, y - 9, 4))


def draw_fire_blast(surf, x, y, direction, tick):
    """Slow, heavy fireball: layered orange, gold and cream with a flame tail."""
    wob = 2 * math.sin(tick * 0.5)
    tail = [(x, y - 13), (x - direction * (40 + wob), y - 3), (x - direction * 30, y),
            (x - direction * (40 - wob), y + 4), (x, y + 13)]
    gfxdraw.filled_polygon(surf, [(round(px), round(py)) for px, py in tail], rgba(THEME["fire"], 150))
    gfxdraw.filled_circle(surf, int(x), int(y), 26, rgba(THEME["fire"], 50))
    gfxdraw.filled_circle(surf, int(x), int(y), 15, THEME["fire"])
    gfxdraw.filled_circle(surf, int(x + direction * 2), int(y), 10, THEME["fire_core"])
    gfxdraw.filled_circle(surf, int(x + direction * 4), int(y - 1), 5, THEME["fire_hot"])
    if THEME["spell_outline"]:
        gfxdraw.aacircle(surf, int(x), int(y), 15, mix(THEME["fire"], (0, 0, 0), 0.5))


def draw_vine_snare(surf, x, y, direction, tick):
    """A thorny seed pod trailing curling vines."""
    c = THEME["vine"]
    dark = mix(c, (0, 0, 0), 0.45)
    for k in range(3):                                   # three wavy tendrils behind it
        pts = []
        for s in range(9):
            px = x - direction * s * 5
            py = y + (k - 1) * 6 + 4 * math.sin(tick * 0.4 + s * 0.9 + k)
            pts.append((px, py))
        pygame.draw.lines(surf, dark if k == 1 else c, False, pts, 2)
    gfxdraw.filled_circle(surf, int(x), int(y), 15, rgba(c, 50))
    gfxdraw.filled_circle(surf, int(x), int(y), 9, dark)
    gfxdraw.filled_circle(surf, int(x), int(y), 6, c)
    for a in range(0, 360, 60):                          # thorns
        r = math.radians(a + tick * 6)
        pygame.draw.line(surf, dark, (x + 8 * math.cos(r), y + 8 * math.sin(r)),
                         (x + 13 * math.cos(r), y + 13 * math.sin(r)), 2)
    if THEME["spell_outline"]:
        gfxdraw.aacircle(surf, int(x), int(y), 10, dark)


def draw_arcane_bolt(surf, x, y, direction, tick):
    """Small violet shard with a short glowing tail."""
    c = THEME["arcane"]
    tail = [(x, y - 4), (x - direction * 26, y), (x, y + 4)]
    gfxdraw.filled_polygon(surf, [(round(px), round(py)) for px, py in tail], rgba(c, 130))
    gfxdraw.filled_circle(surf, int(x), int(y), 10, rgba(c, 60))
    shard = [(x + direction * 8, y), (x, y - 5), (x - direction * 6, y), (x, y + 5)]
    pygame.draw.polygon(surf, c, shard)
    gfxdraw.filled_circle(surf, int(x), int(y), 2, WHITE)
    if THEME["spell_outline"]:
        pygame.draw.polygon(surf, mix(c, (0, 0, 0), 0.5), shard, 1)


def draw_shockwave(surf, x, ground_y, direction, tick):
    """Rock spikes bursting out of the floor as the wave rolls forward."""
    c = THEME["quake"]
    dark = mix(c, (0, 0, 0), 0.5)
    gfxdraw.filled_ellipse(surf, int(x), int(ground_y - 4), 34, 12, rgba(c, 45))
    for k in range(4):
        px = x - direction * k * 11
        h = max(6, 26 - k * 6 + 3 * math.sin(tick * 0.8 + k))
        spike = [(px - 7, ground_y), (px + direction * 2, ground_y - h), (px + 7, ground_y)]
        pygame.draw.polygon(surf, c if k % 2 == 0 else dark, spike)
        pygame.draw.polygon(surf, dark, spike, 1)


def draw_snare(surf, cx, ground_y, tick):
    """Vines wrapped around a slowed wizard's feet."""
    c = THEME["vine"]
    dark = mix(c, (0, 0, 0), 0.45)
    for k in range(3):
        y = ground_y - 6 - k * 9
        pygame.draw.ellipse(surf, dark if k % 2 else c, (cx - 22, y - 4, 44, 9), 2)
    for k in range(4):
        a = math.radians(tick * 4 + k * 90)
        lx, ly = cx + 20 * math.cos(a), ground_y - 14 + 4 * math.sin(a)
        gfxdraw.filled_ellipse(surf, int(lx), int(ly), 4, 2, c)


def spawn_dust(fx, x, ground_y, color):
    fx.append(Particle(x + random.uniform(-10, 10), ground_y - random.uniform(0, 6),
                       random.uniform(-0.6, 0.6), random.uniform(-1.4, -0.4),
                       color, random.randint(12, 22), 3, 0.06))


def spawn_embers(fx, x, y, direction):
    fx.append(Particle(x - direction * random.uniform(8, 20), y + random.uniform(-8, 8),
                       -direction * random.uniform(0.2, 0.8), random.uniform(-0.3, 0.6),
                       random.choice((THEME["fire"], THEME["fire_core"])), random.randint(14, 26), 2, 0.05))


# ---------------- UI pieces ----------------
ARROWS = {"LEFT": 180, "RIGHT": 0, "UP": -90, "DOWN": 90}


def keycap_width(label, font, h=26):
    return h if label in ARROWS else max(h, font.size(label)[0] + 14)


def keycap(surf, label, x, y, font, h=26, pressed=False, charge=None, glow=None):
    """Dark-wood keycap with a bottom lip. label 'LEFT'/'RIGHT'/'UP'/'DOWN' draws an arrow.

    charge: 0..1 recharge fill for spells; glow: color of the fill / ready glow.
    Returns the keycap's width.
    """
    img = None if label in ARROWS else font.render(label, True, THEME["key_text"])
    w = keycap_width(label, font, h)
    lip = 1 if pressed else 3
    top = y + (2 if pressed else 0)
    body = pygame.Rect(x, top, w, h - lip)
    if charge is not None and charge >= 1 and glow:
        pygame.draw.rect(surf, glow, body.inflate(4, 4), 2, border_radius=6)
    pygame.draw.rect(surf, THEME["key_lip"], (x, top + 2, w, h - 2), border_radius=5)
    pygame.draw.rect(surf, THEME["key"], body, border_radius=5)
    if charge is not None and glow and charge < 1:
        fill_h = round((h - lip) * charge)
        if fill_h > 0:
            pygame.draw.rect(surf, mix(THEME["key"], glow, 0.45),
                             (x, top + h - lip - fill_h, w, fill_h), border_radius=5)
    edge = THEME["gold_bright"] if pressed else (glow if charge is not None and charge >= 1 and glow
                                                  else THEME["key_edge"])
    pygame.draw.rect(surf, edge, body, 1, border_radius=5)
    if img:
        surf.blit(img, img.get_rect(center=body.center))
    else:
        a = math.radians(ARROWS[label])
        cx, cy, r = body.centerx, body.centery, h * 0.22
        pts = [(cx + r * math.cos(a), cy + r * math.sin(a)),
               (cx + r * math.cos(a + 2.4), cy + r * math.sin(a + 2.4)),
               (cx + r * math.cos(a - 2.4), cy + r * math.sin(a - 2.4))]
        gfxdraw.aapolygon(surf, [(round(px), round(py)) for px, py in pts], THEME["key_text"])
        gfxdraw.filled_polygon(surf, [(round(px), round(py)) for px, py in pts], THEME["key_text"])
    return w


def panel(surf, rect, edge=None, fill=None, radius=12):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surf, fill or THEME["panel"], rect, border_radius=radius)
    pygame.draw.rect(surf, edge or THEME["gold"], rect, 2, border_radius=radius)
    return rect


def dim(surf, alpha):
    shade = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    shade.fill(rgba(THEME["overlay"], alpha))
    surf.blit(shade, (0, 0))


def button(surf, rect, label, key, font, key_font, selected=False):
    """Menu button: text on the left, its keycap on the right."""
    rect = pygame.Rect(rect)
    if selected:
        pygame.draw.rect(surf, rgba(THEME["gold"], 60), rect.inflate(10, 10), border_radius=12)
        pygame.draw.rect(surf, THEME["button_hi"], rect, border_radius=9)
        pygame.draw.rect(surf, THEME["gold_bright"], rect, 2, border_radius=9)
        color = THEME["button_hi_text"]
    else:
        pygame.draw.rect(surf, THEME["panel"], rect, border_radius=9)
        pygame.draw.rect(surf, THEME["panel_edge"], rect, 2, border_radius=9)
        color = THEME["text"]
    img = font.render(label, True, color)
    surf.blit(img, img.get_rect(midleft=(rect.x + 20, rect.centery)))
    w = keycap_width(key, key_font, 28)
    keycap(surf, key, rect.right - 12 - w, rect.centery - 14, key_font, h=28)


def ornament(surf, cx, y, color):
    pygame.draw.line(surf, color, (cx - 140, y), (cx - 22, y), 2)
    pygame.draw.line(surf, color, (cx + 22, y), (cx + 140, y), 2)
    gfxdraw.filled_circle(surf, cx - 16, y, 2, color)
    gfxdraw.filled_circle(surf, cx + 16, y, 2, color)
    pygame.draw.polygon(surf, THEME["gold_bright"], star_points(cx, y, 9))
