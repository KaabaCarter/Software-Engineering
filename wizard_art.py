"""
Wizard Duel - wizard artwork.

Draws the wizards from the Claude Design canvas ("Wizard Duel - Visual
Direction", see design/Wizard.dc.html) using plain pygame shapes, so no
image files are needed.

All shapes use the design's local coordinates: the 50 x 100 hitbox spans
x 0..50, y 0..100, and draw_wizard() maps that box onto the screen.
"""
import math
import re
import pygame
from pygame import gfxdraw


def hx(color):
    """'#C8102E' -> (200, 16, 46)"""
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def with_alpha(rgb, alpha):
    return rgb[0], rgb[1], rgb[2], int(alpha * 255)


# ---------------- Looks (one per wizard) ----------------
LOOKS = {
    "ember": {
        "pal": {"robe": "#C8102E", "dark": "#7A0A1C", "trim": "#F5C542", "hat": "#8E0B20",
                "band": "#F5C542", "skin": "#F2C29E", "hair": "#C2531F", "glow": "#FFD36B"},
        "hat": "M12 22 L38 22 L24 -1 Q20 -9 10 -13 Q17 -6 17 2 Z",
        "hair": "M15 23 L7 26 L13 30 L6 35 L14 37 L10 43 L19 39 L22 26 Z",
        "beard": None,
    },
    "sage": {
        "pal": {"robe": "#2E9E5B", "dark": "#1A472A", "trim": "#D9DEE3", "hat": "#1A472A",
                "band": "#D9DEE3", "skin": "#C9966F", "hair": "#3A2A22", "glow": "#9CFFC9"},
        "hat": "M13 22 L37 22 L28 -6 L25 -24 L22 -6 Z",
        "hair": "M14 24 Q10 36 13 47 L21 45 Q18 34 20 26 Z",
        "beard": "M26 39 Q31 50 35 38 Q31 41.5 26 39 Z",
    },
    "quill": {
        "pal": {"robe": "#2F5BD3", "dark": "#0E1A40", "trim": "#CD8B3E", "hat": "#0E1A40",
                "band": "#CD8B3E", "skin": "#8A5A3C", "hair": "#1E1B2E", "glow": "#9CC2FF"},
        "hat": "M12 22 L38 22 L30 2 Q34 -6 42 -9 Q31 -11 25 -3 Z",
        "hair": "M14 25 Q5 30 8 41 Q13 45 19 38 Q17 30 19 26 Z",
        "beard": None,
    },
    "bramble": {
        "pal": {"robe": "#3A302A", "dark": "#1E1916", "trim": "#FFD23F", "hat": "#FFD23F",
                "band": "#2B2420", "skin": "#F1C9A5", "hair": "#D9A441", "glow": "#FFE680"},
        "hat": "M11 22 L39 22 L31 6 Q25 -3 13 -1 Q21 3 19 9 Z",
        "hair": "M14 24 Q8 26 10 32 Q6 36 12 39 Q14 42 19 38 L21 27 Z",
        "beard": None,
    },
}
for _look in LOOKS.values():
    _look["pal"] = {k: hx(v) for k, v in _look["pal"].items()}

# Palette used for the white "just got hit" flash
WHITE_PAL = {k: hx(v) for k, v in {
    "robe": "#FFFFFF", "dark": "#DCE5FF", "trim": "#FFFFFF", "hat": "#F2F5FF",
    "band": "#DCE5FF", "skin": "#FFFFFF", "hair": "#EEF2FF", "glow": "#FFFFFF"}.items()}

ROBES = {
    "idle": ("M15 46 Q25 42 35 46 L49 96 Q25 101 1 96 Z", "M3 90 Q25 94 47 90 L49 96 Q25 101 1 96 Z"),
    "walk": ("M15 46 Q25 42 35 46 L46 96 Q22 101 -3 95 Z", "M-1 89 Q22 94 44.5 90 L46 96 Q22 101 -3 95 Z"),
    "jump": ("M15 46 Q25 42 35 46 L52 90 Q25 97 -2 90 Z", "M0 84 Q25 90 50 84 L52 90 Q25 97 -2 90 Z"),
}

# body: transforms in SVG order (outermost first). ("t", dx, dy) or ("r", deg, cx, cy)
# arm: rotation of the wand arm around the shoulder (31, 50)
# The design's jump pose also lifts the body 34px; in game the hitbox itself rises.
POSES = {
    "idle":  {"body": [], "arm": 52, "robe": "idle", "boots": (17, 33, 98), "shadow": 22},
    "walk":  {"body": [("r", 5, 25, 98)], "arm": 38, "robe": "walk", "boots": (7, 40, 98), "shadow": 22},
    "jump":  {"body": [], "arm": 18, "robe": "jump", "boots": (19, 31, 93), "shadow": 13},
    "block": {"body": [("t", -2, 0)], "arm": -12, "robe": "idle", "boots": (15, 35, 98), "shadow": 22},
    "melee": {"body": [("t", 4, 0), ("r", 6, 25, 98)], "arm": -4, "robe": "walk",
              "boots": (10, 40, 98), "shadow": 22},
    # Arm lowered from the design's -48 so the wand points along the spell's flight path
    "cast":  {"body": [("r", -3, 25, 98)], "arm": -8, "robe": "idle", "boots": (15, 35, 98), "shadow": 22},
    "hit":   {"body": [("t", -5, 0), ("r", -9, 25, 98)], "arm": 75, "robe": "walk",
              "boots": (17, 33, 98), "shadow": 22},
    "ko":    {"body": [("t", 25, -22), ("r", -90, 25, 97)], "arm": 95, "robe": "idle",
              "boots": (17, 33, 98), "shadow": 32},
}

INK = hx("#1A1424")
BOOT = hx("#1A1424")
WAND = hx("#7A4E2A")
WAND_GRIP = hx("#3E2614")
BLUSH = hx("#FF8FA3")
WHITE = (255, 255, 255)
STAR_GOLD = hx("#F5C542")
SPARK = hx("#FFE680")
SHIELD_FILL = hx("#9FD3FF")
SHIELD_RIM = hx("#CFEBFF")


# ---------------- Geometry helpers ----------------
_path_cache = {}


def path_points(d, steps=6):
    """Turn a simple SVG path (absolute M/L/Q/Z only) into a list of points."""
    if d in _path_cache:
        return _path_cache[d]
    tokens = re.findall(r"[MLQZ]|-?\d*\.?\d+", d)
    pts, i, cmd = [], 0, None
    while i < len(tokens):
        if tokens[i] in "MLQZ":
            cmd = tokens[i]
            i += 1
            if cmd == "Z":
                continue
        if cmd in ("M", "L"):
            pts.append((float(tokens[i]), float(tokens[i + 1])))
            i += 2
        elif cmd == "Q":
            (x0, y0) = pts[-1]
            cx, cy, x1, y1 = (float(t) for t in tokens[i:i + 4])
            for s in range(1, steps + 1):
                t = s / steps
                u = 1 - t
                pts.append((u * u * x0 + 2 * u * t * cx + t * t * x1,
                            u * u * y0 + 2 * u * t * cy + t * t * y1))
            i += 4
        else:
            i += 1
    _path_cache[d] = pts
    return pts


def ellipse_points(cx, cy, rx, ry, n=18):
    return [(cx + rx * math.cos(2 * math.pi * k / n), cy + ry * math.sin(2 * math.pi * k / n))
            for k in range(n)]


def star_points(cx, cy, r, points=4, inner=0.26):
    pts = []
    for k in range(points * 2):
        a = math.pi * k / points - math.pi / 2
        rr = r if k % 2 == 0 else r * inner
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def _apply(ops, x, y):
    """Apply SVG-style transforms; the innermost (last) one acts first."""
    for op in reversed(ops):
        if op[0] == "t":
            x, y = x + op[1], y + op[2]
        else:
            a = math.radians(op[1])
            cx, cy = op[2], op[3]
            dx, dy = x - cx, y - cy
            x = cx + dx * math.cos(a) - dy * math.sin(a)
            y = cy + dx * math.sin(a) + dy * math.cos(a)
    return x, y


# ---------------- Painter ----------------
class _Pen:
    """Maps design coordinates to the screen and draws anti-aliased shapes."""

    def __init__(self, surf, x, y, facing, scale):
        self.surf, self.x, self.y, self.facing, self.scale = surf, x, y, facing, scale

    def pt(self, ops, px, py):
        px, py = _apply(ops, px, py)
        if self.facing < 0:
            px = 50 - px
        return round(self.x + px * self.scale), round(self.y + py * self.scale)

    def poly(self, ops, pts, color):
        if len(pts) < 3:
            return
        ipts = [self.pt(ops, px, py) for px, py in pts]
        gfxdraw.filled_polygon(self.surf, ipts, color)
        if len(color) == 3:                       # skip AA edge on translucent shapes
            gfxdraw.aapolygon(self.surf, ipts, color)

    def path(self, ops, d, color):
        self.poly(ops, path_points(d), color)

    def circle(self, ops, cx, cy, r, color):
        x, y = self.pt(ops, cx, cy)
        r = max(1, round(r * self.scale))
        gfxdraw.filled_circle(self.surf, x, y, r, color)
        if len(color) == 3:
            gfxdraw.aacircle(self.surf, x, y, r, color)

    def ellipse(self, ops, cx, cy, rx, ry, color):
        self.poly(ops, ellipse_points(cx, cy, rx, ry), color)

    def rect(self, ops, x, y, w, h, color):
        self.poly(ops, [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], color)

    def line(self, ops, p1, p2, color, width):
        pygame.draw.line(self.surf, color, self.pt(ops, *p1), self.pt(ops, *p2),
                         max(1, round(width * self.scale)))

    def polyline(self, ops, pts, color, width):
        for a, b in zip(pts, pts[1:]):
            self.line(ops, a, b, color, width)


def draw_wizard(surf, look_name, pose_name, x, y, facing=1, scale=1.0,
                white=False, tick=0, ground=100):
    """Draw a wizard whose 50x100 hitbox has its top-left corner at (x, y).

    look_name: key of LOOKS     pose_name: key of POSES
    facing: 1 = right, -1 = left   white: hit-flash palette
    tick: frame counter for small animations   ground: local y of the floor
    """
    look = LOOKS[look_name]
    pose = POSES[pose_name]
    c = WHITE_PAL if white else look["pal"]
    pen = _Pen(surf, x, y, facing, scale)
    body = pose["body"]
    arm = body + [("r", pose["arm"], 31, 50)]

    # Shadow on the floor, smaller the higher the wizard is
    height = max(0, ground - 100)
    rx = max(8, pose["shadow"] - height * 0.08)
    pen.ellipse([], 25, ground, rx, 3.5, (0, 0, 0, 90))

    # Back cape and scarf tail
    pen.path(body, "M18 48 Q10 58 11 72 L18 73 Q19 60 24 50 Z", c["dark"])
    pen.path(body, "M15 45 L10 64 L16 65 L20 47 Z", c["trim"])

    # Boots, robe, hem and belt
    b1, b2, by = pose["boots"]
    pen.ellipse(body, b1, by, 7, 3.5, BOOT)
    pen.ellipse(body, b2, by, 7, 3.5, BOOT)
    robe, hem = ROBES[pose["robe"]]
    pen.path(body, robe, c["robe"])
    pen.path(body, "M25 50 L33 94 L24 96 Z", with_alpha(c["dark"], 0.55))
    pen.path(body, hem, c["trim"])
    pen.rect(body, 14, 41, 22, 7, c["trim"])
    pen.rect(body, 20, 41, 3, 7, c["dark"])
    pen.rect(body, 27, 41, 3, 7, c["dark"])

    # Head
    pen.path(body, look["hair"], c["hair"])
    pen.circle(body, 25, 31, 11, c["skin"])
    pen.circle(body, 31, 34.5, 2.2, with_alpha(BLUSH, 0.45))
    if pose_name == "ko":
        pen.line(body, (28.5, 28), (32.5, 32), INK, 1.5)
        pen.line(body, (32.5, 28), (28.5, 32), INK, 1.5)
    else:
        pen.ellipse(body, 30.5, 30, 1.6, 2.2, INK)
        pen.line(body, (28, 26.3), (33.6, 27), INK, 1.4)
    pen.polyline(body, path_points("M29.8 36.6 Q31.8 37.6 33.4 36.4"), INK, 1.1)
    if look["beard"]:
        pen.path(body, look["beard"], c["trim"])

    # Hat
    pen.path(body, look["hat"], c["hat"])
    pen.poly(body, [(13.5, 22), (36.5, 22), (35, 17), (15, 17)], c["band"])
    pen.ellipse(body, 25, 22.5, 18, 3.6, c["hat"])

    # Wand arm
    pen.line(arm, (49, 50.5), (71, 50.5), WAND, 2.6)
    pen.line(arm, (49, 50.5), (56, 50.5), WAND_GRIP, 3.6)
    pen.rect(arm, 29, 45.5, 18, 10, c["robe"])
    pen.rect(arm, 42, 45.5, 4, 10, c["trim"])
    pen.circle(arm, 48.5, 50.5, 3.6, c["skin"])
    pen.circle(arm, 71.5, 50.5, 2.3, c["glow"])

    if pose_name == "cast":                       # glowing orb at the wand tip
        pen.circle(arm, 74, 50.5, 13, with_alpha(c["glow"], 0.25))
        pen.circle(arm, 74, 50.5, 7, with_alpha(c["glow"], 0.7))
        pen.circle(arm, 74, 50.5, 3.5, WHITE)
        pen.poly(arm, star_points(86, 40, 5), WHITE)
        pen.poly(arm, star_points(80, 64, 4), c["glow"])

    if pose_name == "melee":                      # crescent swipe + star flash
        pen.path(arm, "M70 26 Q100 50.5 70 75 Q86 50.5 70 26 Z", with_alpha(WHITE, 0.85))
        pen.poly(arm, star_points(80, 50.5, 12), c["glow"])

    if pose_name == "block":                      # shield bubble
        pen.circle([], 25, 50, 62, with_alpha(SHIELD_FILL, 0.2))
        cx, cy = pen.pt([], 25, 50)
        pygame.draw.circle(surf, SHIELD_RIM, (cx, cy), round(62 * scale), max(2, round(2.5 * scale)))
        a0, a1 = math.atan2(14 - 50, -22 - 25), math.atan2(-7 - 50, 16 - 25)
        glint = [(25 + 58 * math.cos(a0 + (a1 - a0) * k / 8), 50 + 58 * math.sin(a0 + (a1 - a0) * k / 8))
                 for k in range(9)]
        pen.polyline([], glint, WHITE, 3)
        pen.poly([], star_points(78, 18, 5), WHITE)

    if pose_name == "hit":                        # impact sparks
        for p1, p2 in (((50, 20), (62, 12)), ((54, 34), (70, 32)), ((50, 48), (64, 56)), ((44, 10), (48, -2))):
            pen.line([], p1, p2, WHITE, 3)
        pen.poly([], star_points(58, 26, 7), SPARK)

    if pose_name == "ko":                         # stars circling the head
        for k in range(3):
            a = tick * 0.08 + k * 2 * math.pi / 3
            sx, sy = -16 + 16 * math.cos(a), 58 + 5 * math.sin(a)
            pen.poly([], star_points(sx, sy, 5, points=5, inner=0.45),
                     WHITE if k == 1 else STAR_GOLD)
