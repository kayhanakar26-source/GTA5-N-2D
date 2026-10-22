"""SOKAKLAR 2D - tek dosyalik, prosedurel 2D acik dunya oyunu.

Kurulum:
    pip install "pygame>=2.5.0,<3"
Calistirma:
    python sokaklar_2d.py

Kontroller:
    WASD / Yon tuslari : yurume, arac surme
    Fare               : nisan alma
    Sol tik            : ates etme (ilk mermi nisangahin tam uzerine gider)
    1 / 2 / 3          : tabanca / makineli tabanca / pompali tufek
    R                  : sarjor degistir
    E                  : araca bin / in
    SPACE              : el freni
    M                  : sesi ac / kapat
    F3                 : debug bilgisi
    ESC                : duraklat / geri
    8828               : god mode (hasar ve mermi sinirsiz; tekrar yazinca kapanir)
"""

import os
import sys
import math
import random

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
from pygame.math import Vector2


# ===========================================================================
# MODUL: utils
# ===========================================================================

"""Kucuk yardimci fonksiyonlar."""
import math
import random

import pygame
from pygame.math import Vector2


def clamp(value, low, high):
    return low if value < low else high if value > high else value


def lerp(a, b, t):
    return a + (b - a) * t


def damp(current, target, speed, dt):
    return current + (target - current) * (1.0 - math.exp(-speed * dt))


def angle_diff(target, current):
    """Iki aci arasindaki -pi..pi araligindaki en kisa fark."""
    d = (target - current + math.pi) % (math.tau) - math.pi
    return d


def angle_lerp(current, target, speed, dt):
    return current + angle_diff(target, current) * (1.0 - math.exp(-speed * dt))


def rotate(vec, angle):
    c = math.cos(angle)
    s = math.sin(angle)
    return Vector2(vec.x * c - vec.y * s, vec.x * s + vec.y * c)


def star_points(cx, cy, outer, inner, count=5, rotation=-math.pi / 2):
    points = []
    for i in range(count * 2):
        r = outer if i % 2 == 0 else inner
        a = rotation + i * math.pi / count
        points.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return points


def draw_star(surface, cx, cy, outer, inner, color, width=0):
    pygame.draw.polygon(surface, color, star_points(cx, cy, outer, inner), width)


_FONT_CACHE = {}


def get_font(size, bold=False):
    key = (size, bold)
    font = _FONT_CACHE.get(key)
    if font is None:
        try:
            font = pygame.font.SysFont("segoe ui", size, bold=bold)
        except Exception:
            font = pygame.font.Font(None, size + 4)
        _FONT_CACHE[key] = font
    return font


def draw_text(surface, text, size, pos, color, anchor="topleft", bold=False,
              shadow=True, alpha=255, font=None):
    if font is None:
        font = get_font(size, bold)
    img = font.render(str(text), True, color)
    if alpha < 255:
        img.set_alpha(alpha)
    rect = img.get_rect(**{anchor: pos})
    if shadow:
        sh = font.render(str(text), True, (5, 6, 9))
        if alpha < 255:
            sh.set_alpha(alpha)
        surface.blit(sh, sh.get_rect(**{anchor: (pos[0] + 2, pos[1] + 2)}))
    surface.blit(img, rect)
    return rect


def draw_panel(surface, rect, fill=(14, 16, 22, 205), border=None,
               radius=12, width=1):
    rect = pygame.Rect(rect)
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, fill, panel.get_rect(), border_radius=radius)
    if border is not None:
        pygame.draw.rect(panel, border, panel.get_rect(), width, border_radius=radius)
    surface.blit(panel, rect.topleft)
    return rect


def draw_bar(surface, rect, value, maximum, back, fill, border=None, radius=4,
             vertical=False):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, back, rect, border_radius=radius)
    ratio = clamp(value / maximum if maximum else 0, 0, 1)
    if ratio > 0:
        if vertical:
            h = max(2, int(rect.h * ratio))
            r = pygame.Rect(rect.x, rect.bottom - h, rect.w, h)
        else:
            r = pygame.Rect(rect.x, rect.y, max(2, int(rect.w * ratio)), rect.h)
        pygame.draw.rect(surface, fill, r, border_radius=radius)
    if border is not None:
        pygame.draw.rect(surface, border, rect, 1, border_radius=radius)


def format_money(amount):
    return f"{int(amount):,}".replace(",", ".")


def fmt_time(seconds):
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def screen_to_world(pos, camera):
    return Vector2(pos[0] + camera.x, pos[1] + camera.y)


def make_ellipse_shadow(w, h, alpha=90):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(surf, (0, 0, 0, alpha), surf.get_rect())
    return surf


_GLOW_CACHE = {}


def get_glow(radius, color):
    key = (int(radius), color)
    surf = _GLOW_CACHE.get(key)
    if surf is None:
        size = int(radius * 2)
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        for i in range(9, 0, -1):
            a = int(16 + (9 - i) * 2)
            rr = int(radius * i / 9)
            pygame.draw.circle(surf, (*color, a), (radius, radius), rr)
        _GLOW_CACHE[key] = surf
    return surf


def random_unit(rng=random):
    a = rng.uniform(0, math.tau)
    return Vector2(math.cos(a), math.sin(a))


def unit(v):
    v = Vector2(v)
    length = v.length()
    if length < 1e-9:
        return Vector2(1, 0)
    return v / length


def point_segment_distance(p, a, b):
    ab = b - a
    if ab.length_squared() == 0:
        return (p - a).length()
    t = clamp((p - a).dot(ab) / ab.length_squared(), 0, 1)
    return (p - (a + ab * t)).length()


# ===========================================================================
# MODUL: settings
# ===========================================================================

"""SOKAKLAR 2D - genel ayarlar ve oyun verileri."""

TITLE = "SOKAKLAR 2D"
SCREEN_W = 1280
SCREEN_H = 720
FPS = 60

# ---------------------------------------------------------------------------
# Sehir izgarasi
# ---------------------------------------------------------------------------
TILE = 48
ROAD_W = 3          # yol genisligi (tile)
BLOCK_W = 10        # blok ici genisligi (tile)
BLOCK_H = 8         # blok ici yuksekligi (tile)
COLS = 6            # yatay blok sayisi
ROWS = 5            # dikey blok sayisi

MAP_W = COLS * BLOCK_W + (COLS + 1) * ROAD_W   # 81 tile
MAP_H = ROWS * BLOCK_H + (ROWS + 1) * ROAD_W   # 58 tile
WORLD_W = MAP_W * TILE                          # 3888 px
WORLD_H = MAP_H * TILE                          # 2784 px

# Tile turleri
ROAD = 0
WALK = 1
BUILDING = 2
GRASS = 3
LOT = 4

# ---------------------------------------------------------------------------
# Renkler
# ---------------------------------------------------------------------------
ASPHALT = (53, 56, 64)
ASPHALT_DARK = (44, 47, 54)
ASPHALT_LIGHT = (63, 66, 75)
SIDEWALK = (132, 136, 146)
SIDEWALK_LIGHT = (151, 155, 164)
SIDEWALK_DARK = (108, 112, 122)
CURB = (180, 181, 175)
GRASS = (77, 125, 76)
GRASS_DARK = (63, 105, 63)
GRASS_LIGHT = (94, 144, 85)
LOT_GROUND = (61, 63, 70)
LINE_WHITE = (224, 221, 205)
LINE_YELLOW = (218, 180, 65)
SHADOW = (28, 29, 34)

PLAYER_BODY = (42, 122, 128)
PLAYER_BODY_DARK = (31, 89, 94)
PLAYER_PANTS = (55, 61, 75)
SKIN = (206, 161, 122)
SKIN_DARK = (166, 120, 88)
HAIR = (48, 39, 34)

COP_BLUE = (47, 72, 133)
COP_BLUE_DARK = (32, 49, 93)
COP_SKIN = (196, 152, 111)
COP_HAT = (28, 38, 68)

BLOOD = (116, 20, 26)
BLOOD_DARK = (77, 13, 18)
MUZZLE = (255, 219, 112)
BULLET = (255, 240, 174)
SMOKE = (126, 128, 134)
FIRE = (240, 112, 42)

UI_BG = (14, 16, 22, 205)
UI_BG_LIGHT = (25, 28, 37, 225)
UI_BORDER = (64, 70, 84)
UI_TEXT = (231, 234, 240)
UI_DIM = (148, 154, 166)
UI_ACCENT = (247, 199, 64)
UI_RED = (226, 75, 66)
UI_GREEN = (89, 199, 119)
UI_BLUE = (83, 149, 230)

CAR_COLORS = [
    (183, 59, 52), (50, 103, 176), (211, 178, 63), (63, 143, 101),
    (203, 205, 212), (58, 62, 73), (191, 111, 49), (116, 74, 148),
    (90, 160, 168), (153, 153, 145),
]

# ---------------------------------------------------------------------------
# Silahlar
# ---------------------------------------------------------------------------
WEAPONS = {
    "pistol": {
        "name": "TABANCA", "damage": 28, "delay": 0.24, "spread": 0.028,
        "speed": 1560, "pellets": 1, "mag": 12, "reload": 1.05,
        "range": 1050, "shake": 3.2, "recoil": 0.0, "sound": "shot",
        "sound_radius": 780, "tracer": (255, 233, 150), "icon": "pistol",
    },
    "smg": {
        "name": "MAKİNELİ TABANCA", "damage": 16, "delay": 0.082, "spread": 0.085,
        "speed": 1650, "pellets": 1, "mag": 32, "reload": 1.45,
        "range": 1150, "shake": 2.4, "recoil": 1.0, "sound": "smg",
        "sound_radius": 900, "tracer": (255, 218, 120), "icon": "smg",
    },
    "shotgun": {
        "name": "POMPALI TÜFEK", "damage": 13, "delay": 0.82, "spread": 0.16,
        "speed": 1380, "pellets": 6, "mag": 6, "reload": 1.9,
        "range": 620, "shake": 7.5, "recoil": 5.0, "sound": "shotgun",
        "sound_radius": 1050, "tracer": (255, 204, 120), "icon": "shotgun",
    },
}
WEAPON_ORDER = ["pistol", "smg", "shotgun"]
START_AMMO = {
    "pistol": [12, 96],
    "smg": [32, 160],
    "shotgun": [6, 24],
}

# ---------------------------------------------------------------------------
# Araclar
# ---------------------------------------------------------------------------
CARS = {
    "sedan": {
        "label": "Sedan", "size": (78, 38), "max_speed": 550, "accel": 470,
        "brake": 900, "turn": 2.65, "health": 120, "grip": 6.4, "mass": 1.0,
    },
    "sport": {
        "label": "Spor", "size": (84, 36), "max_speed": 760, "accel": 660,
        "brake": 1000, "turn": 3.15, "health": 95, "grip": 5.4, "mass": 0.9,
    },
    "van": {
        "label": "Minibüs", "size": (90, 46), "max_speed": 420, "accel": 360,
        "brake": 720, "turn": 2.05, "health": 210, "grip": 7.4, "mass": 1.6,
    },
    "taxi": {
        "label": "Taksi", "size": (78, 38), "max_speed": 520, "accel": 445,
        "brake": 860, "turn": 2.6, "health": 110, "grip": 6.4, "mass": 1.0,
    },
}

# Ses / efekt esikleri
COP_SPEED = 205
PED_SPEED_MIN = 42
PED_SPEED_MAX = 78
MAX_BULLETS = 220
MAX_PARTICLES = 700
MAX_CORPSES = 30

# Ayni dosyadaki ayarlara kisa erisim (eski modul arayuzu).
S = sys.modules[__name__]


# ===========================================================================
# MODUL: art
# ===========================================================================

"""Prosedurel sprite ve arayüz görselleri."""
import math

import pygame
from pygame.math import Vector2


_CAR_SPRITES = {}
_SHADOWS = {}
_WEAPON_ICONS = {}


def get_shadow(w, h, alpha=86):
    key = (int(w), int(h), alpha)
    surf = _SHADOWS.get(key)
    if surf is None:
        surf = pygame.Surface((max(2, int(w)), max(2, int(h))), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (0, 0, 0, alpha), surf.get_rect())
        _SHADOWS[key] = surf
    return surf


def get_car_sprite(kind, color):
    key = (kind, color)
    surf = _CAR_SPRITES.get(key)
    if surf is not None:
        return surf
    w, h = S.CARS[kind]["size"]
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    dark = tuple(max(0, v - 65) for v in color)
    light = tuple(min(255, v + 35) for v in color)
    glass = (45, 61, 74)
    glass_light = (84, 114, 132)

    # Tekerlekler
    wheel_col = (24, 25, 29)
    wheel_hi = (49, 51, 57)
    axle_f = int(w * 0.68)
    axle_r = int(w * 0.27)
    wheel_w = max(12, int(w * 0.20))
    wheel_h = max(5, int(h * 0.16))
    for ax in (axle_r, axle_f):
        for wy in (-2, h - wheel_h + 2):
            rect = pygame.Rect(ax - wheel_w // 2, wy, wheel_w, wheel_h)
            pygame.draw.rect(surf, wheel_col, rect, border_radius=3)
            pygame.draw.rect(surf, wheel_hi, rect.inflate(-3, -3), 1, border_radius=2)

    body = pygame.Rect(2, 3, w - 4, h - 6)
    # Alt gövde / tamponlar
    pygame.draw.rect(surf, dark, body, border_radius=int(h * 0.26))
    inner = body.inflate(-3, -3)
    pygame.draw.rect(surf, color, inner, border_radius=int(h * 0.24))
    # Ön ve arka tampon
    pygame.draw.rect(surf, dark, (w - 8, 6, 6, h - 12), border_radius=3)
    pygame.draw.rect(surf, dark, (2, 6, 5, h - 12), border_radius=3)
    # Kaput ve bagaj çizgileri
    pygame.draw.line(surf, light, (int(w * 0.73), 6), (int(w * 0.73), h - 6), 1)
    pygame.draw.line(surf, tuple(max(0, v - 25) for v in color),
                     (int(w * 0.24), 7), (int(w * 0.24), h - 7), 1)

    if kind == "van":
        roof = pygame.Rect(int(w * 0.20), 6, int(w * 0.52), h - 12)
        pygame.draw.rect(surf, tuple(min(255, v + 18) for v in color), roof, border_radius=6)
        # Ön cam
        pygame.draw.polygon(surf, glass, [
            (int(w * 0.72), 7), (int(w * 0.82), int(h * 0.2)),
            (int(w * 0.82), int(h * 0.8)), (int(w * 0.72), h - 7)])
        pygame.draw.line(surf, glass_light, (int(w * 0.73), int(h * 0.22)),
                         (int(w * 0.73), int(h * 0.78)), 2)
        pygame.draw.line(surf, dark, (int(w * 0.56), 8), (int(w * 0.56), h - 8), 2)
        pygame.draw.rect(surf, (226, 226, 218), (int(w * 0.4), int(h * 0.36),
                                                  int(w * 0.1), int(h * 0.28)), 1, border_radius=2)
    else:
        roof_len = 0.36 if kind == "sport" else 0.34
        roof_x = int(w * 0.40)
        roof = pygame.Rect(roof_x, 6, int(w * roof_len), h - 12)
        # Arka cam
        pygame.draw.polygon(surf, glass, [
            (roof.x, 8), (roof.x + int(w * 0.08), 5),
            (roof.x + int(w * 0.08), h - 5), (roof.x, h - 8)])
        pygame.draw.rect(surf, glass, roof, border_radius=5)
        pygame.draw.rect(surf, glass_light, roof.inflate(-4, -6), 1, border_radius=4)
        # Ön cam
        pygame.draw.polygon(surf, glass, [
            (roof.right, 7), (roof.right + int(w * 0.13), 9),
            (roof.right + int(w * 0.13), h - 9), (roof.right, h - 7)])
        pygame.draw.line(surf, glass_light, (roof.right + 3, 11), (roof.right + 3, h - 11), 1)
        # Orta çizgi
        pygame.draw.line(surf, tuple(min(255, v + 25) for v in color),
                         (roof.right + int(w * 0.15), 7),
                         (roof.right + int(w * 0.15), h - 7), 1)
        if kind == "sport":
            pygame.draw.line(surf, (233, 230, 218), (int(w * 0.2), h // 2),
                             (w - 9, h // 2), 3)
        if kind == "taxi":
            pygame.draw.rect(surf, (235, 218, 118),
                             (w // 2 - 10, h // 2 - 5, 20, 10), border_radius=2)
            font = get_font(7, True)
            img = font.render("TAKSI", True, (30, 30, 30))
            surf.blit(img, img.get_rect(center=(w // 2, h // 2)))

    # Yan aynalar
    pygame.draw.rect(surf, dark, (int(w * 0.57), 1, 7, 4), border_radius=2)
    pygame.draw.rect(surf, dark, (int(w * 0.57), h - 5, 7, 4), border_radius=2)
    # Farlar / stoplar
    for fy in (8, h - 14):
        pygame.draw.rect(surf, (247, 230, 169), (w - 6, fy, 4, 6), border_radius=2)
        pygame.draw.rect(surf, (191, 50, 40), (1, fy, 4, 6), border_radius=2)
    # Kapı çizgisi
    pygame.draw.line(surf, dark, (int(w * 0.52), 5), (int(w * 0.52), h - 5), 1)
    pygame.draw.arc(surf, light, inner, -1.2, 1.2, 1)
    _CAR_SPRITES[key] = surf
    return surf


def get_weapon_icon(name, scale=1.0):
    key = (name, scale)
    surf = _WEAPON_ICONS.get(key)
    if surf is not None:
        return surf
    base = pygame.Surface((76, 34), pygame.SRCALPHA)
    metal = (194, 198, 205)
    dark = (72, 77, 88)
    grip = (94, 66, 43)
    if name == "pistol":
        pygame.draw.rect(base, dark, (8, 10, 50, 9), border_radius=2)
        pygame.draw.rect(base, metal, (10, 8, 46, 7), border_radius=2)
        pygame.draw.rect(base, metal, (20, 15, 15, 5), border_radius=1)
        pygame.draw.polygon(base, grip, [(28, 18), (38, 18), (34, 30), (25, 30)])
        pygame.draw.rect(base, dark, (55, 9, 9, 9), border_radius=2)
        pygame.draw.rect(base, metal, (56, 10, 7, 7), border_radius=1)
    elif name == "smg":
        pygame.draw.rect(base, dark, (4, 8, 56, 11), border_radius=2)
        pygame.draw.rect(base, metal, (6, 7, 54, 8), border_radius=2)
        pygame.draw.rect(base, metal, (28, 14, 9, 16), border_radius=1)
        pygame.draw.polygon(base, grip, [(30, 25), (38, 25), (36, 33), (27, 33)])
        pygame.draw.rect(base, dark, (58, 9, 13, 7), border_radius=2)
        pygame.draw.rect(base, metal, (60, 10, 9, 5), border_radius=1)
        pygame.draw.rect(base, metal, (40, 22, 14, 4), border_radius=1)
    elif name == "shotgun":
        pygame.draw.rect(base, dark, (5, 9, 60, 8), border_radius=2)
        pygame.draw.rect(base, metal, (5, 8, 58, 6), border_radius=2)
        pygame.draw.rect(base, (126, 85, 54), (10, 14, 24, 8), border_radius=2)
        pygame.draw.polygon(base, (100, 68, 45), [(17, 20), (29, 20), (27, 30), (19, 30)])
        pygame.draw.rect(base, metal, (34, 12, 22, 5), border_radius=1)
        pygame.draw.rect(base, dark, (62, 8, 10, 8), border_radius=2)
        pygame.draw.rect(base, metal, (64, 9, 6, 6), border_radius=1)
    base = pygame.transform.rotozoom(base, 0, scale)
    _WEAPON_ICONS[key] = base
    return base


def make_vignette(width, height):
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    steps = 90
    for i in range(steps):
        t = i / steps
        alpha = int(70 * (1.0 - t) ** 2.2)
        if alpha <= 0:
            continue
        pygame.draw.line(surf, (4, 5, 8, alpha), (0, i), (width, i))
        pygame.draw.line(surf, (4, 5, 8, alpha), (0, height - 1 - i), (width, height - 1 - i))
        pygame.draw.line(surf, (4, 5, 8, alpha), (i, 0), (i, height))
        pygame.draw.line(surf, (4, 5, 8, alpha), (width - 1 - i, 0), (width - 1 - i, height))
    return surf


def draw_muzzle_flash(surface, pos, angle, scale=1.0, color=(255, 224, 131)):
    d = Vector2(math.cos(angle), math.sin(angle))
    p = Vector2(pos)
    for i, (length, width) in enumerate(((30, 7), (18, 11), (12, 15))):
        tip = p + d * (length * scale)
        perp = Vector2(-d.y, d.x) * (width * scale * 0.5)
        a = (255, 255, 225)
        poly = [p - perp, tip, p + perp]
        pygame.draw.polygon(surface, color if i < 2 else a, poly)
    pygame.draw.circle(surface, (255, 248, 211), (int(p.x), int(p.y)), int(4 * scale))


def draw_player(surface, pos, angle, walk, walk_phase, in_car=False, recoil=0.0):
    """Ekran koordinatinda oyuncuyu cizer."""
    p = Vector2(pos)
    d = Vector2(math.cos(angle), math.sin(angle))
    perp = Vector2(-d.y, d.x)
    if in_car:
        hand = p + d * 15
        pygame.draw.line(surface, S.PLAYER_BODY_DARK, (int(p.x), int(p.y)),
                         (int(hand.x), int(hand.y)), 4)
        pygame.draw.circle(surface, S.SKIN, (int(hand.x), int(hand.y)), 3)
        gun = hand + d * 11
        pygame.draw.line(surface, (37, 40, 48), (int(hand.x), int(hand.y)),
                         (int(gun.x), int(gun.y)), 4)
        return
    shadow = get_shadow(30, 16, 92)
    surface.blit(shadow, shadow.get_rect(center=(p.x + 4, p.y + 8)))

    swing = math.sin(walk_phase) * 5.0 * walk
    for side in (-1, 1):
        foot = p + perp * (side * 5) + d * (swing * side)
        pygame.draw.circle(surface, (37, 40, 49), (int(foot.x), int(foot.y + 2)), 4)
    body_col = S.PLAYER_BODY
    pygame.draw.circle(surface, (21, 26, 31), (int(p.x + 2), int(p.y + 3)), 11)
    pygame.draw.circle(surface, body_col, (int(p.x), int(p.y)), 10)
    pygame.draw.circle(surface, S.PLAYER_BODY_DARK, (int(p.x), int(p.y)), 10, 2)
    # omuzlar
    shoulder = p + d * 1
    for side in (-1, 1):
        sp = shoulder + perp * (side * 10)
        pygame.draw.circle(surface, S.PLAYER_BODY_DARK, (int(sp.x), int(sp.y)), 4)
    # kafa
    head = p + d * 2.5
    pygame.draw.circle(surface, (25, 24, 23), (int(head.x + 1), int(head.y + 2)), 6)
    pygame.draw.circle(surface, S.SKIN, (int(head.x), int(head.y)), 6)
    pygame.draw.circle(surface, S.HAIR, (int(head.x - d.x * 2), int(head.y - d.y * 2)), 5)
    pygame.draw.circle(surface, (233, 195, 158), (int(head.x + d.x * 2 - 1), int(head.y + d.y * 2 - 1)), 2)
    # silah kolu
    hand = p + d * (15 - recoil) + perp * 5
    pygame.draw.line(surface, S.PLAYER_BODY_DARK, (int(p.x), int(p.y)),
                     (int(hand.x), int(hand.y)), 5)
    pygame.draw.circle(surface, S.SKIN, (int(hand.x), int(hand.y)), 3)
    gun = hand + d * 12
    pygame.draw.line(surface, (37, 40, 48), (int(hand.x), int(hand.y)),
                     (int(gun.x), int(gun.y)), 4)
    pygame.draw.circle(surface, (118, 123, 133), (int(gun.x), int(gun.y)), 2)


def draw_npc(surface, npc):
    p = npc.pos
    d = Vector2(math.cos(npc.angle), math.sin(npc.angle))
    perp = Vector2(-d.y, d.x)
    shadow = get_shadow(28, 15, 78)
    surface.blit(shadow, shadow.get_rect(center=(p.x + 3, p.y + 7)))
    walk = 1.0 if npc.moving else 0.0
    swing = math.sin(npc.anim) * 4.5 * walk
    for side in (-1, 1):
        foot = p + perp * (side * 4.5) + d * (swing * side)
        pygame.draw.circle(surface, (39, 41, 47), (int(foot.x), int(foot.y + 2)), 3)
    body = npc.body_color
    pygame.draw.circle(surface, (23, 25, 30), (int(p.x + 2), int(p.y + 3)), 9)
    pygame.draw.circle(surface, body, (int(p.x), int(p.y)), 8)
    pygame.draw.circle(surface, npc.body_dark, (int(p.x), int(p.y)), 8, 2)
    head = p + d * 2
    pygame.draw.circle(surface, (24, 23, 23), (int(head.x + 1), int(head.y + 2)), 5)
    pygame.draw.circle(surface, npc.skin, (int(head.x), int(head.y)), 5)
    if npc.kind == "cop":
        pygame.draw.circle(surface, S.COP_HAT, (int(head.x - d.x), int(head.y - d.y)), 4)
        pygame.draw.rect(surface, (218, 192, 76), (int(head.x) - 1, int(head.y) - 2, 3, 2))
        hand = p + d * 13 + perp * 4
        pygame.draw.line(surface, S.COP_BLUE_DARK, (int(p.x), int(p.y)),
                         (int(hand.x), int(hand.y)), 4)
        gun = hand + d * 9
        pygame.draw.line(surface, (35, 37, 43), (int(hand.x), int(hand.y)),
                         (int(gun.x), int(gun.y)), 3)
    else:
        pygame.draw.circle(surface, npc.hair, (int(head.x - d.x * 1.5), int(head.y - d.y * 1.5)), 4)
        hand = p + d * 10 + perp * 4
        pygame.draw.circle(surface, npc.skin, (int(hand.x), int(hand.y)), 2)


def draw_corpse(surface, corpse):
    p = corpse.pos
    angle = corpse.angle
    d = Vector2(math.cos(angle), math.sin(angle))
    perp = Vector2(-d.y, d.x)
    pygame.draw.ellipse(surface, (90, 14, 19),
                        (p.x - 22, p.y - 13, 44, 26))
    pygame.draw.ellipse(surface, (58, 16, 20),
                        (p.x - 15, p.y - 8, 30, 16))
    pygame.draw.line(surface, corpse.body_dark, p - d * 10, p + d * 8, 9)
    pygame.draw.circle(surface, corpse.skin, (int(p.x + d.x * 11), int(p.y + d.y * 11)), 5)
    pygame.draw.line(surface, (51, 36, 28), p - perp * 6, p - perp * 15, 4)
    pygame.draw.line(surface, corpse.body_dark, p + perp * 5, p + perp * 14, 4)

# Ayni dosyadaki sanat fonksiyonlarina kisa erisim.
art = sys.modules[__name__]


# ===========================================================================
# MODUL: audio
# ===========================================================================

"""Kucuk, tamamen prosedurel ses motoru (harici dosya gerektirmez)."""
import array
import math
import random

import pygame



RATE = 22050


def _clip(v):
    return max(-32767, min(32767, int(v)))


def _noise_burst(duration, amp=0.65, lowpass=0.35, decay=3.0, thump=0.0,
                 thump_freq=90.0):
    n = max(1, int(RATE * duration))
    data = array.array("h")
    last = 0.0
    for i in range(n):
        t = i / n
        white = random.uniform(-1.0, 1.0)
        last += (white - last) * lowpass
        env = (1.0 - t) ** decay
        value = last * amp * env
        if thump > 0.0:
            value += math.sin(i / RATE * math.tau * thump_freq) * thump * env
        data.append(_clip(value * 32767))
    return pygame.mixer.Sound(buffer=data.tobytes())


def _tone(freq_start, freq_end, duration, amp=0.25, wave="sine", decay=1.5):
    n = max(1, int(RATE * duration))
    data = array.array("h")
    phase = 0.0
    for i in range(n):
        t = i / n
        freq = freq_start + (freq_end - freq_start) * t
        phase += math.tau * freq / RATE
        env = (1.0 - t) ** decay
        if wave == "square":
            s = 1.0 if math.sin(phase) > 0 else -1.0
        else:
            s = math.sin(phase)
        data.append(_clip(s * amp * env * 32767))
    return pygame.mixer.Sound(buffer=data.tobytes())


def _click(duration=0.05, amp=0.3, freq=1600):
    n = max(1, int(RATE * duration))
    data = array.array("h")
    phase = 0.0
    for i in range(n):
        t = i / n
        phase += math.tau * freq / RATE
        env = (1.0 - t) ** 5
        s = math.sin(phase) + random.uniform(-0.5, 0.5)
        data.append(_clip(s * amp * env * 32767))
    return pygame.mixer.Sound(buffer=data.tobytes())


class Audio:
    def __init__(self):
        self.enabled = False
        self.muted = False
        self.master = 0.65
        self.sounds = {}
        try:
            pygame.mixer.pre_init(RATE, -16, 1, 512)
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            pygame.mixer.set_num_channels(24)
            self.enabled = True
        except Exception:
            self.enabled = False
            return

        try:
            self.sounds = {
                "shot": _noise_burst(0.13, 0.62, 0.55, 3.6, 0.35, 110),
                "smg": _noise_burst(0.075, 0.5, 0.6, 4.2, 0.2, 130),
                "shotgun": _noise_burst(0.30, 0.8, 0.32, 2.4, 0.55, 72),
                "cop_shot": _noise_burst(0.10, 0.35, 0.5, 4.0, 0.2, 120),
                "explosion": _noise_burst(0.75, 0.9, 0.10, 1.7, 0.5, 46),
                "crash": _noise_burst(0.28, 0.55, 0.22, 2.5, 0.3, 60),
                "hit": _noise_burst(0.09, 0.4, 0.18, 4.0, 0.25, 70),
                "door": _click(0.09, 0.22, 240),
                "empty": _click(0.035, 0.25, 2100),
                "reload": _click(0.11, 0.22, 900),
                "pickup": _tone(640, 1080, 0.16, 0.2, "sine", 2.0),
                "health": _tone(520, 820, 0.22, 0.18, "sine", 1.4),
                "wanted": _tone(240, 400, 0.35, 0.15, "square", 1.2),
                "siren": _tone(720, 980, 0.55, 0.1, "sine", 0.8),
            }
        except Exception:
            self.enabled = False
            self.sounds = {}

    def toggle_mute(self):
        self.muted = not self.muted
        if self.enabled:
            pygame.mixer.stop()

    def play(self, name, volume=1.0, pos=None, listener=None, max_dist=1600.0):
        if not self.enabled or self.muted:
            return
        sound = self.sounds.get(name)
        if sound is None:
            return
        vol = volume
        if pos is not None and listener is not None:
            dist = (pos - listener).length()
            if dist > max_dist:
                return
            vol *= max(0.0, 1.0 - dist / max_dist) ** 1.5
        vol = clamp(vol * self.master, 0.0, 1.0)
        if vol < 0.02:
            return
        try:
            channel = sound.play()
            if channel is not None:
                channel.set_volume(vol)
        except Exception:
            pass


# ===========================================================================
# MODUL: city
# ===========================================================================

"""Prosedurel 2D sehir: sokaklar, binalar, parklar ve çarpışma sistemi."""
import heapq
import math
import random

import pygame
from pygame.math import Vector2



ROOF_COLORS = [
    (125, 92, 84), (103, 109, 128), (135, 112, 86), (94, 118, 112),
    (126, 100, 135), (111, 115, 105), (143, 122, 92), (92, 98, 114),
    (119, 88, 94), (105, 124, 135),
]

AWNING_COLORS = [
    (168, 64, 57), (54, 100, 150), (60, 130, 96), (190, 146, 55),
    (120, 76, 140), (90, 94, 108),
]

PARK_PATHS = (157, 150, 133)


class Tree:
    __slots__ = ("pos", "canopy", "trunk", "shade", "phase")

    def __init__(self, pos, canopy, trunk, shade, phase):
        self.pos = pos
        self.canopy = canopy
        self.trunk = trunk
        self.shade = shade
        self.phase = phase


class Building:
    __slots__ = ("rect", "roof", "edge", "trim", "details", "awning", "awning_rect")

    def __init__(self, rect, roof, edge, trim, details, awning, awning_rect):
        self.rect = rect
        self.roof = roof
        self.edge = edge
        self.trim = trim
        self.details = details
        self.awning = awning
        self.awning_rect = awning_rect


class City:
    def __init__(self, seed=7):
        self.rng = random.Random(seed)
        self.seed = seed
        self.tiles = [[S.ROAD for _ in range(S.MAP_W)] for _ in range(S.MAP_H)]
        self.solid = [[False for _ in range(S.MAP_W)] for _ in range(S.MAP_H)]
        self.buildings = []
        self.trees = []
        self.obstacles = []          # (Vector2, yariçap) yuvarlak çarpışma cisimleri
        self.parks = []
        self.fountains = []
        self.benches = []
        self.parking_spots = []
        self.block_rects = []        # px cinsinden blok iç alanları
        self.v_strips = []
        self.h_strips = []
        self.intersections = []
        self._props = []
        self.wanted_spawn_points = []
        self._generate()
        self.surface = self._render()
        self.minimap = self._render_minimap()

    # ------------------------------------------------------------------ üretim
    def _generate(self):
        rng = self.rng
        for c in range(S.COLS + 1):
            x = c * (S.BLOCK_W + S.ROAD_W) * S.TILE
            self.v_strips.append((x, S.ROAD_W * S.TILE))
        for r in range(S.ROWS + 1):
            y = r * (S.BLOCK_H + S.ROAD_W) * S.TILE
            self.h_strips.append((y, S.ROAD_W * S.TILE))
        for r in range(S.ROWS + 1):
            for c in range(S.COLS + 1):
                self.intersections.append(Vector2(
                    c * (S.BLOCK_W + S.ROAD_W) * S.TILE + S.ROAD_W * S.TILE / 2,
                    r * (S.BLOCK_H + S.ROAD_W) * S.TILE + S.ROAD_W * S.TILE / 2,
                ))

        for r in range(S.ROWS):
            for c in range(S.COLS):
                x0 = S.ROAD_W + c * (S.BLOCK_W + S.ROAD_W)
                y0 = S.ROAD_W + r * (S.BLOCK_H + S.ROAD_W)
                self._make_block(x0, y0, c, r)

        for ty in range(S.MAP_H):
            for tx in range(S.MAP_W):
                if self.tiles[ty][tx] == S.WALK:
                    self.wanted_spawn_points.append(Vector2(
                        (tx + 0.5) * S.TILE, (ty + 0.5) * S.TILE))
        self.wanted_spawn_points.sort(
            key=lambda p: (p - Vector2(S.WORLD_W / 2, S.WORLD_H / 2)).length_squared())
        self.player_spawn = self.wanted_spawn_points[0].copy()

    def _make_block(self, x0, y0, c, r):
        rng = self.rng
        for ty in range(y0, y0 + S.BLOCK_H):
            for tx in range(x0, x0 + S.BLOCK_W):
                self.tiles[ty][tx] = S.WALK
        block_px = pygame.Rect(x0 * S.TILE, y0 * S.TILE,
                               S.BLOCK_W * S.TILE, S.BLOCK_H * S.TILE)
        self.block_rects.append(block_px)

        roll = rng.random()
        if roll < 0.145:
            self._make_park(x0, y0)
        elif roll < 0.26:
            self._make_lot(x0, y0)
        else:
            zone = pygame.Rect(x0 + 1, y0 + 1, S.BLOCK_W - 2, S.BLOCK_H - 2)
            rects = []
            self._split_zone(zone, rects, 0)
            for rect in rects:
                self._make_building(rect)

        # Kaldırım köşelerine sokak lambaları / yangın muslukları
        corners = [(x0, y0), (x0 + S.BLOCK_W - 1, y0),
                   (x0, y0 + S.BLOCK_H - 1), (x0 + S.BLOCK_W - 1, y0 + S.BLOCK_H - 1)]
        rng.shuffle(corners)
        for i, (cx, cy) in enumerate(corners[:2]):
            pos = Vector2((cx + 0.5) * S.TILE, (cy + 0.5) * S.TILE)
            self._props.append(("lamp", pos))
        if rng.random() < 0.65:
            cx, cy = corners[2]
            self._props.append(("hydrant", Vector2((cx + 0.5) * S.TILE, (cy + 0.5) * S.TILE)))
        if rng.random() < 0.4:
            cx, cy = corners[0]
            self._props.append(("bin", Vector2((cx + 0.5) * S.TILE, (cy + 0.5) * S.TILE)))

    def _split_zone(self, zone, out, depth):
        rng = self.rng
        can_x = zone.w >= 5
        can_y = zone.h >= 5
        if depth >= 2 or (not can_x and not can_y):
            out.append(zone.copy())
            return
        if depth == 1 and rng.random() < 0.3:
            out.append(zone.copy())
            return
        if can_x and (not can_y or zone.w >= zone.h):
            cut = rng.randint(2, zone.w - 3)
            a = pygame.Rect(zone.x, zone.y, cut, zone.h)
            b = pygame.Rect(zone.x + cut + 1, zone.y, zone.w - cut - 1, zone.h)
            self._split_zone(a, out, depth + 1)
            self._split_zone(b, out, depth + 1)
        elif can_y:
            cut = rng.randint(2, zone.h - 3)
            a = pygame.Rect(zone.x, zone.y, zone.w, cut)
            b = pygame.Rect(zone.x, zone.y + cut + 1, zone.w, zone.h - cut - 1)
            self._split_zone(a, out, depth + 1)
            self._split_zone(b, out, depth + 1)
        else:
            out.append(zone.copy())

    def _make_building(self, tile_rect):
        rng = self.rng
        for ty in range(tile_rect.y, tile_rect.bottom):
            for tx in range(tile_rect.x, tile_rect.right):
                self.tiles[ty][tx] = S.BUILDING
                self.solid[ty][tx] = True
        rect = pygame.Rect(tile_rect.x * S.TILE, tile_rect.y * S.TILE,
                           tile_rect.w * S.TILE, tile_rect.h * S.TILE)
        base = rng.choice(ROOF_COLORS)
        jitter = rng.randint(-9, 9)
        roof = tuple(clamp(v + jitter, 0, 255) for v in base)
        edge = tuple(max(0, v - 34) for v in roof)
        trim = tuple(min(255, v + 22) for v in roof)
        details = []
        # Çatı detayları
        pad = 12
        attempts = rng.randint(2, 5)
        for _ in range(attempts):
            if rect.w < 90 or rect.h < 70:
                break
            kind = rng.random()
            if kind < 0.6:
                w = rng.randint(18, max(20, min(44, rect.w // 3)))
                h = rng.randint(14, max(16, min(34, rect.h // 3)))
                x = rng.randint(rect.x + pad, rect.right - w - pad)
                y = rng.randint(rect.y + pad, rect.bottom - h - pad)
                details.append(("ac", pygame.Rect(x, y, w, h),
                                rng.choice([(146, 150, 156), (127, 132, 140), (164, 166, 168)])))
            elif kind < 0.82:
                w = rng.randint(24, 50)
                h = rng.randint(10, 18)
                if rect.w > w + pad * 2 and rect.h > h + pad * 2:
                    x = rng.randint(rect.x + pad, rect.right - w - pad)
                    y = rng.randint(rect.y + pad, rect.bottom - h - pad)
                    details.append(("vent", pygame.Rect(x, y, w, h), None))
            else:
                r = rng.randint(12, 20)
                if rect.w > r * 2 + pad * 2 and rect.h > r * 2 + pad * 2:
                    x = rng.randint(rect.x + r + pad, rect.right - r - pad)
                    y = rng.randint(rect.y + r + pad, rect.bottom - r - pad)
                    details.append(("tank", Vector2(x, y), r))
        # Giriş tenteleri (alt kenara doğru)
        awning = rng.choice(AWNING_COLORS)
        aw = min(rect.w - 18, rng.randint(46, 90))
        ax = rng.randint(rect.x + 9, rect.right - aw - 9)
        awning_rect = pygame.Rect(ax, rect.bottom - 5, aw, 12)
        self.buildings.append(Building(rect, roof, edge, trim, details, awning, awning_rect))

    def _make_park(self, x0, y0):
        rng = self.rng
        for ty in range(y0, y0 + S.BLOCK_H):
            for tx in range(x0, x0 + S.BLOCK_W):
                self.tiles[ty][tx] = S.GRASS
        rect = pygame.Rect(x0 * S.TILE, y0 * S.TILE, S.BLOCK_W * S.TILE, S.BLOCK_H * S.TILE)
        fountain = Vector2(rect.center)
        self.fountains.append(fountain.copy())
        self.obstacles.append((fountain.copy(), 34))
        self.parks.append(rect)
        # Ağaçlar
        tries = 0
        while len([t for t in self.trees if rect.collidepoint(t.pos)]) < rng.randint(3, 6) and tries < 40:
            tries += 1
            p = Vector2(rng.uniform(rect.x + 60, rect.right - 60),
                        rng.uniform(rect.y + 60, rect.bottom - 60))
            if (p - fountain).length() < 120:
                continue
            if any((p - t.pos).length() < 70 for t in self.trees):
                continue
            canopy = rng.randint(22, 31)
            self.trees.append(Tree(p, canopy, rng.randint(9, 12),
                                   int((p - fountain).length()) % 3, rng.uniform(0, 6)))
        # Banklar
        for off in ((-78, 0), (78, 0), (0, -78), (0, 78)):
            p = Vector2(fountain) + Vector2(off)
            self.benches.append((p, 0 if off[0] else math.pi / 2))

    def _make_lot(self, x0, y0):
        rng = self.rng
        for ty in range(y0, y0 + S.BLOCK_H):
            for tx in range(x0, x0 + S.BLOCK_W):
                self.tiles[ty][tx] = S.LOT
        rect = pygame.Rect(x0 * S.TILE, y0 * S.TILE, S.BLOCK_W * S.TILE, S.BLOCK_H * S.TILE)
        self.parks.append(rect)  # minimap için yeşil olmasın diye ayrı kontrol edilir
        count = rng.randint(3, 5)
        for i in range(count):
            x = rect.x + S.TILE * 1.3 + i * S.TILE * 1.75
            if x > rect.right - S.TILE:
                break
            if rng.random() < 0.75:
                self.parking_spots.append((Vector2(x, rect.y + S.TILE * 1.5), math.pi / 2))
            if rng.random() < 0.75:
                self.parking_spots.append((Vector2(x, rect.bottom - S.TILE * 1.5), -math.pi / 2))

    # ------------------------------------------------------------- çarpışma
    def tile_at(self, tx, ty):
        if 0 <= tx < S.MAP_W and 0 <= ty < S.MAP_H:
            return self.tiles[ty][tx]
        return -1

    def tile_at_pos(self, x, y):
        return self.tile_at(int(x // S.TILE), int(y // S.TILE))

    def is_solid_tile(self, tx, ty):
        if not (0 <= tx < S.MAP_W and 0 <= ty < S.MAP_H):
            return True
        return self.solid[ty][tx]

    def is_solid_pos(self, x, y):
        return self.is_solid_tile(int(x // S.TILE), int(y // S.TILE))

    def is_free(self, pos, radius=10.0):
        if pos.x - radius < 0 or pos.y - radius < 0 or pos.x + radius > S.WORLD_W or pos.y + radius > S.WORLD_H:
            return False
        tx0 = int((pos.x - radius) // S.TILE)
        tx1 = int((pos.x + radius) // S.TILE)
        ty0 = int((pos.y - radius) // S.TILE)
        ty1 = int((pos.y + radius) // S.TILE)
        for ty in range(ty0, ty1 + 1):
            for tx in range(tx0, tx1 + 1):
                if self.is_solid_tile(tx, ty):
                    r = pygame.Rect(tx * S.TILE, ty * S.TILE, S.TILE, S.TILE)
                    cx = clamp(pos.x, r.left, r.right)
                    cy = clamp(pos.y, r.top, r.bottom)
                    if (pos.x - cx) ** 2 + (pos.y - cy) ** 2 < radius * radius:
                        return False
        for op, orad in self.obstacles:
            if (pos - op).length_squared() < (radius + orad) ** 2:
                return False
        return True

    def resolve_circle(self, pos, radius):
        """pos'u yerinde iter ve toplam itme vektörünü döndürür."""
        total = Vector2()
        for _ in range(2):
            tx0 = max(0, int((pos.x - radius) // S.TILE))
            tx1 = min(S.MAP_W - 1, int((pos.x + radius) // S.TILE))
            ty0 = max(0, int((pos.y - radius) // S.TILE))
            ty1 = min(S.MAP_H - 1, int((pos.y + radius) // S.TILE))
            for ty in range(ty0, ty1 + 1):
                for tx in range(tx0, tx1 + 1):
                    if not self.solid[ty][tx]:
                        continue
                    r = pygame.Rect(tx * S.TILE, ty * S.TILE, S.TILE, S.TILE)
                    cx = clamp(pos.x, r.left, r.right)
                    cy = clamp(pos.y, r.top, r.bottom)
                    dx = pos.x - cx
                    dy = pos.y - cy
                    d2 = dx * dx + dy * dy
                    if d2 < radius * radius:
                        if d2 > 0.0001:
                            d = math.sqrt(d2)
                            nx, ny = dx / d, dy / d
                            pen = radius - d
                        else:
                            # Merkez dikdörtgenin içinde: en kısa kenardan it
                            left = pos.x - r.left
                            right = r.right - pos.x
                            top = pos.y - r.top
                            bottom = r.bottom - pos.y
                            m = min(left, right, top, bottom)
                            if m == left:
                                nx, ny, pen = -1.0, 0.0, left + radius
                            elif m == right:
                                nx, ny, pen = 1.0, 0.0, right + radius
                            elif m == top:
                                nx, ny, pen = 0.0, -1.0, top + radius
                            else:
                                nx, ny, pen = 0.0, 1.0, bottom + radius
                        pos.x += nx * pen
                        pos.y += ny * pen
                        total.x += nx * pen
                        total.y += ny * pen
            for op, orad in self.obstacles:
                dx = pos.x - op.x
                dy = pos.y - op.y
                d2 = dx * dx + dy * dy
                min_d = radius + orad
                if d2 < min_d * min_d:
                    d = math.sqrt(d2)
                    if d < 0.001:
                        nx, ny = 1.0, 0.0
                    else:
                        nx, ny = dx / d, dy / d
                    pen = min_d - d
                    pos.x += nx * pen
                    pos.y += ny * pen
                    total.x += nx * pen
                    total.y += ny * pen
        # Dünya sınırları
        if pos.x < radius:
            total.x += radius - pos.x
            pos.x = radius
        elif pos.x > S.WORLD_W - radius:
            total.x -= pos.x - (S.WORLD_W - radius)
            pos.x = S.WORLD_W - radius
        if pos.y < radius:
            total.y += radius - pos.y
            pos.y = radius
        elif pos.y > S.WORLD_H - radius:
            total.y -= pos.y - (S.WORLD_H - radius)
            pos.y = S.WORLD_H - radius
        return total

    def line_blocked(self, a, b, step=14.0):
        d = b - a
        length = d.length()
        if length < 1:
            return False
        n = int(length / step) + 1
        for i in range(1, n):
            p = a + d * (i / n)
            if self.is_solid_pos(p.x, p.y):
                return True
        return False

    def _nearest_free_tile(self, tx, ty, max_radius=4):
        if not self.is_solid_tile(tx, ty):
            return tx, ty
        for radius in range(1, max_radius + 1):
            for oy in range(-radius, radius + 1):
                for ox in range(-radius, radius + 1):
                    nx, ny = tx + ox, ty + oy
                    if 0 <= nx < S.MAP_W and 0 <= ny < S.MAP_H and not self.solid[ny][nx]:
                        return nx, ny
        return None

    def find_path(self, start, goal, max_nodes=2600):
        """Tile tabanli A*; sokakta dolasan polisler icin."""
        sx = int(clamp(start[0] // S.TILE, 0, S.MAP_W - 1))
        sy = int(clamp(start[1] // S.TILE, 0, S.MAP_H - 1))
        gx = int(clamp(goal[0] // S.TILE, 0, S.MAP_W - 1))
        gy = int(clamp(goal[1] // S.TILE, 0, S.MAP_H - 1))
        s = self._nearest_free_tile(sx, sy)
        g = self._nearest_free_tile(gx, gy)
        if s is None or g is None:
            return []
        sx, sy = s
        gx, gy = g
        if (sx, sy) == (gx, gy):
            return [Vector2((gx + 0.5) * S.TILE, (gy + 0.5) * S.TILE)]

        def heuristic(x, y):
            dx = abs(x - gx)
            dy = abs(y - gy)
            return (dx + dy) + (1.41421356 - 2.0) * min(dx, dy)

        open_heap = [(heuristic(sx, sy), 0.0, sx, sy)]
        g_score = {(sx, sy): 0.0}
        came = {}
        closed = set()
        visited = 0
        found = False
        while open_heap:
            _, cost, x, y = heapq.heappop(open_heap)
            if (x, y) in closed:
                continue
            closed.add((x, y))
            if (x, y) == (gx, gy):
                found = True
                break
            visited += 1
            if visited > max_nodes:
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                           (1, 1), (1, -1), (-1, 1), (-1, -1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < S.MAP_W and 0 <= ny < S.MAP_H):
                    continue
                if self.solid[ny][nx]:
                    continue
                if dx and dy:
                    if self.solid[y][nx] or self.solid[ny][x]:
                        continue
                step = 1.41421356 if (dx and dy) else 1.0
                ng = cost + step
                if ng < g_score.get((nx, ny), 1e9):
                    g_score[(nx, ny)] = ng
                    came[(nx, ny)] = (x, y)
                    heapq.heappush(open_heap, (ng + heuristic(nx, ny), ng, nx, ny))
        if not found:
            return []
        cells = []
        cur = (gx, gy)
        while cur != (sx, sy):
            cells.append(cur)
            cur = came.get(cur)
            if cur is None:
                return []
        cells.reverse()
        # Gereksiz ara noktalari ele
        points = [Vector2((x + 0.5) * S.TILE, (y + 0.5) * S.TILE) for x, y in cells]
        if len(points) > 2:
            simplified = [points[0]]
            i = 0
            while i < len(points) - 1:
                j = min(len(points) - 1, i + 5)
                chosen = i + 1
                while j > i + 1:
                    if not self.line_blocked(points[i], points[j], 10.0):
                        chosen = j
                        break
                    j -= 1
                simplified.append(points[chosen])
                i = chosen
            points = simplified
        return points

    def road_angle_at(self, pos, rng=None):
        rng = rng or self.rng
        vertical = any(x0 <= pos.x <= x0 + w for x0, w in self.v_strips)
        horizontal = any(y0 <= pos.y <= y0 + h for y0, h in self.h_strips)
        if vertical and not horizontal:
            return rng.choice((math.pi / 2, -math.pi / 2))
        if horizontal and not vertical:
            return rng.choice((0.0, math.pi))
        return rng.choice((0.0, math.pi / 2, math.pi, -math.pi / 2))

    # ---------------------------------------------------------------- sorgular
    def random_walk_point(self, rng=None):
        rng = rng or self.rng
        for _ in range(30):
            p = rng.choice(self.wanted_spawn_points)
            p = p + Vector2(rng.uniform(-14, 14), rng.uniform(-14, 14))
            if self.is_free(p, 12):
                return p
        return self.player_spawn.copy()

    def random_road_point(self, rng=None):
        rng = rng or self.rng
        for _ in range(50):
            p = Vector2(rng.uniform(S.TILE, S.WORLD_W - S.TILE),
                        rng.uniform(S.TILE, S.WORLD_H - S.TILE))
            if self.tile_at_pos(p.x, p.y) == S.ROAD and self.is_free(p, 16):
                return p
        return self.intersections[0].copy()

    def random_spawn_away(self, center, min_dist, max_dist, rng=None, need_free=True):
        rng = rng or self.rng
        best = None
        for _ in range(70):
            p = rng.choice(self.wanted_spawn_points)
            d = (p - center).length()
            if min_dist <= d <= max_dist:
                if self.is_free(p, 12):
                    return p.copy()
                best = p.copy()
        if best is not None:
            return best
        # Sokak ortasında dene
        p = self.random_road_point(rng)
        for _ in range(20):
            if min_dist <= (p - center).length() <= max_dist:
                return p
            p = self.random_road_point(rng)
        return p

    def lane_target(self, intersection, direction):
        offset = S.ROAD_W * S.TILE * 0.23
        perp = Vector2(-direction.y, direction.x)
        return intersection + perp * offset

    # ---------------------------------------------------------------- çizim
    def _render(self):
        rng = random.Random(self.seed * 977 + 13)
        world = pygame.Surface((S.WORLD_W, S.WORLD_H)).convert()
        world.fill(S.ASPHALT)

        # Asfalt dokusu
        for _ in range(7000):
            x = rng.randrange(S.WORLD_W)
            y = rng.randrange(S.WORLD_H)
            c = rng.choice([(60, 63, 71), (46, 49, 56), (70, 72, 80)])
            world.set_at((x, y), c)
        for _ in range(45):
            w = rng.randint(30, 130)
            h = rng.randint(18, 80)
            x = rng.randrange(S.WORLD_W - w)
            y = rng.randrange(S.WORLD_H - h)
            col = rng.choice([S.ASPHALT_DARK, (58, 61, 69)])
            pygame.draw.rect(world, col, (x, y, w, h), border_radius=8)

        # Zemin tile'ları
        for ty in range(S.MAP_H):
            for tx in range(S.MAP_W):
                t = self.tiles[ty][tx]
                if t == S.ROAD:
                    continue
                x = tx * S.TILE
                y = ty * S.TILE
                rect = pygame.Rect(x, y, S.TILE, S.TILE)
                v = ((tx * 31 + ty * 17) % 5) - 2
                if t == S.WALK:
                    color = (S.SIDEWALK[0] + v, S.SIDEWALK[1] + v, S.SIDEWALK[2] + v)
                    world.fill(color, rect)
                    pygame.draw.line(world, S.SIDEWALK_DARK, (x, y + S.TILE - 1), (x + S.TILE, y + S.TILE - 1))
                    pygame.draw.line(world, S.SIDEWALK_DARK, (x + S.TILE - 1, y), (x + S.TILE - 1, y + S.TILE))
                    if rng.random() < 0.08:
                        pygame.draw.line(world, (104, 108, 118),
                                         (x + rng.randint(4, 40), y + rng.randint(4, 40)),
                                         (x + rng.randint(4, 40), y + rng.randint(4, 40)), 1)
                elif t == S.GRASS:
                    color = (S.GRASS[0] + v, S.GRASS[1] + v, S.GRASS[2] + v)
                    world.fill(color, rect)
                    for _ in range(3):
                        gx = x + rng.randint(3, S.TILE - 3)
                        gy = y + rng.randint(3, S.TILE - 3)
                        col = rng.choice([S.GRASS_DARK, S.GRASS_LIGHT])
                        pygame.draw.line(world, col, (gx, gy), (gx + rng.randint(-4, 4), gy - rng.randint(3, 6)), 1)
                elif t == S.LOT:
                    world.fill(S.LOT_GROUND, rect)
                    world.fill((56, 58, 65) if v < 0 else (66, 68, 75), rect.inflate(-6, -6))

        # Park yolları ve çeşmeler
        for rect in self.parks:
            if self.tile_at_pos(rect.centerx, rect.centery) != S.GRASS:
                continue
            pygame.draw.rect(world, PARK_PATHS, (rect.centerx - 23, rect.y + 8, 46, rect.h - 16))
            pygame.draw.rect(world, PARK_PATHS, (rect.x + 8, rect.centery - 23, rect.w - 16, 46))
            pygame.draw.rect(world, (140, 134, 118), (rect.centerx - 23, rect.y + 8, 46, rect.h - 16), 2)
            pygame.draw.rect(world, (140, 134, 118), (rect.x + 8, rect.centery - 23, rect.w - 16, 46), 2)
            pygame.draw.circle(world, (145, 139, 122), rect.center, 70)
            pygame.draw.circle(world, (160, 153, 134), rect.center, 64)
            pygame.draw.circle(world, (138, 132, 116), rect.center, 64, 2)

        # Otopark çizgileri
        for pos, ang in self.parking_spots:
            d = Vector2(math.cos(ang), math.sin(ang))
            perp = Vector2(-d.y, d.x)
            for side in (-1, 1):
                a = pos + perp * side * 38 - d * 42
                b = pos + perp * side * 38 + d * 42
                pygame.draw.line(world, (218, 218, 208), a, b, 2)

        # Yol çizgileri
        self._draw_road_markings(world, rng)
        self._draw_intersections(world)

        # Bina gölgeleri ve binaları
        for b in self.buildings:
            pygame.draw.rect(world, S.SHADOW, b.rect.move(9, 11))
        for b in self.buildings:
            self._draw_building(world, b, rng)

        # Ağaçlar
        for tree in self.trees:
            self._draw_tree(world, tree)

        # Çeşmeler
        for p in self.fountains:
            pygame.draw.circle(world, (91, 86, 78), p + Vector2(5, 6), 38)
            pygame.draw.circle(world, (139, 132, 116), p, 38)
            pygame.draw.circle(world, (100, 95, 85), p, 38, 4)
            pygame.draw.circle(world, (61, 116, 140), p, 30)
            pygame.draw.circle(world, (84, 148, 170), p, 26)
            pygame.draw.arc(world, (183, 220, 228), pygame.Rect(p.x - 24, p.y - 24, 48, 48), 3.5, 5.6, 3)
            pygame.draw.circle(world, (150, 196, 205), p, 5)
            pygame.draw.circle(world, (204, 234, 238), p, 2)

        # Banklar
        for p, ang in self.benches:
            d = Vector2(math.cos(ang), math.sin(ang))
            perp = Vector2(-d.y, d.x)
            pygame.draw.rect(world, (82, 59, 40),
                             pygame.Rect(int(p.x - 17), int(p.y - 7), 34, 14), border_radius=3)
            pygame.draw.rect(world, (128, 94, 61),
                             pygame.Rect(int(p.x - 15), int(p.y - 6), 30, 12), border_radius=3)
            for k in (-9, 0, 9):
                a = p + d * k + perp * 14
                b = p + d * k - perp * 14
                pygame.draw.line(world, (74, 53, 36), a, b, 2)

        # Sokak eşyaları
        for kind, p in self._props:
            self._draw_prop(world, kind, p)

        # Yol / kaldırım birleşim çizgileri
        for br in self.block_rects:
            pygame.draw.rect(world, (184, 184, 176), br.inflate(8, 8), 2, border_radius=2)

        return world

    def _draw_road_markings(self, world, rng):
        # Yatay yollarda şerit çizgileri
        for y0, w in self.h_strips:
            cy = int(y0 + w / 2)
            x = 12
            while x < S.WORLD_W:
                skip = False
                for vx, vw in self.v_strips:
                    if vx - 30 < x < vx + vw + 30:
                        skip = True
                        break
                if not skip:
                    pygame.draw.line(world, S.LINE_YELLOW, (x, cy), (x + 30, cy), 4)
                x += 62
        # Dikey yollarda şerit çizgileri
        for x0, w in self.v_strips:
            cx = int(x0 + w / 2)
            y = 12
            while y < S.WORLD_H:
                skip = False
                for hy, hh in self.h_strips:
                    if hy - 30 < y < hy + hh + 30:
                        skip = True
                        break
                if not skip:
                    pygame.draw.line(world, S.LINE_YELLOW, (cx, y), (cx, y + 30), 4)
                y += 62

        # Yol kenarı beyaz çizgileri
        for br in self.block_rects:
            r = br.inflate(10, 10)
            pygame.draw.line(world, (206, 204, 194), r.topleft, r.topright, 2)
            pygame.draw.line(world, (206, 204, 194), r.topleft, r.bottomleft, 2)
            pygame.draw.line(world, (206, 204, 194), r.bottomleft, r.bottomright, 2)
            pygame.draw.line(world, (206, 204, 194), r.topright, r.bottomright, 2)

        # Rastgele mazgal ve yama
        for _ in range(55):
            p = self.random_road_point(rng)
            if rng.random() < 0.5:
                pygame.draw.circle(world, (38, 40, 46), p, 9)
                pygame.draw.circle(world, (70, 73, 80), p, 7, 2)
                for k in (-4, 0, 4):
                    pygame.draw.line(world, (47, 49, 56), (p.x - 6, p.y + k), (p.x + 6, p.y + k), 1)
            else:
                r = pygame.Rect(p.x - 18, p.y - 12, 36, 24)
                pygame.draw.rect(world, (47, 50, 58), r, border_radius=4)
                pygame.draw.rect(world, (61, 64, 72), r, 2, border_radius=4)

    def _draw_intersections(self, world):
        for c in range(S.COLS + 1):
            for r in range(S.ROWS + 1):
                x0 = c * (S.BLOCK_W + S.ROAD_W) * S.TILE
                y0 = r * (S.BLOCK_H + S.ROAD_W) * S.TILE
                rw = S.ROAD_W * S.TILE
                # Yaya geçidi bantları (dört kenar)
                stripe = (232, 229, 216)
                # kuzey / güney
                for side in (-1, 1):
                    by = y0 - 52 if side < 0 else y0 + rw + 6
                    if 0 <= by < S.WORLD_H - 46:
                        for i in range(5):
                            sx = x0 + 10 + i * 26
                            pygame.draw.rect(world, stripe, (sx, by, 15, 40), border_radius=2)
                # batı / doğu
                for side in (-1, 1):
                    bx = x0 - 52 if side < 0 else x0 + rw + 6
                    if 0 <= bx < S.WORLD_W - 46:
                        for i in range(5):
                            sy = y0 + 10 + i * 26
                            pygame.draw.rect(world, stripe, (bx, sy, 40, 15), border_radius=2)

    def _draw_building(self, world, b, rng):
        rect = b.rect
        pygame.draw.rect(world, b.roof, rect)
        # Çatı dokusu
        for i in range(6):
            gx = rng.randint(rect.x + 8, rect.right - 8)
            gy = rng.randint(rect.y + 8, rect.bottom - 8)
            col = tuple(clamp(v + rng.randint(-8, 8), 0, 255) for v in b.roof)
            pygame.draw.line(world, col, (gx, gy), (gx + rng.randint(8, 28), gy), 1)
        pygame.draw.rect(world, b.edge, rect, 4)
        pygame.draw.rect(world, b.trim, rect.inflate(-12, -12), 2)
        # Parapet gölgesi
        pygame.draw.line(world, tuple(max(0, v - 22) for v in b.roof),
                         (rect.x + 4, rect.y + 5), (rect.right - 4, rect.y + 5), 2)
        # Çatı detayları
        for kind, obj, extra in b.details:
            if kind == "ac":
                pygame.draw.rect(world, (45, 47, 53), obj.move(3, 4), border_radius=3)
                pygame.draw.rect(world, extra, obj, border_radius=3)
                pygame.draw.rect(world, tuple(max(0, v - 32) for v in extra), obj, 2, border_radius=3)
                for k in range(3):
                    yy = obj.y + 4 + k * (obj.h - 8) // 2
                    pygame.draw.line(world, (88, 91, 98), (obj.x + 4, yy), (obj.right - 4, yy), 1)
            elif kind == "vent":
                pygame.draw.rect(world, (47, 50, 56), obj.move(2, 3), border_radius=4)
                pygame.draw.rect(world, b.trim, obj, border_radius=4)
                pygame.draw.rect(world, b.edge, obj, 2, border_radius=4)
                pygame.draw.line(world, b.edge, (obj.x + 6, obj.centery), (obj.right - 6, obj.centery), 1)
            elif kind == "tank":
                c = obj
                pygame.draw.circle(world, (41, 45, 50), c + Vector2(4, 5), extra)
                pygame.draw.circle(world, (115, 118, 121), c, extra)
                pygame.draw.circle(world, (150, 152, 154), c, max(2, extra - 6))
                pygame.draw.circle(world, (91, 94, 98), c, extra, 2)
                pygame.draw.line(world, (95, 98, 102), (c.x - extra + 3, c.y), (c.x + extra - 3, c.y), 1)
        # Giriş tentesi
        aw = b.awning_rect
        pygame.draw.rect(world, (37, 39, 44), aw.move(2, 4), border_radius=3)
        pygame.draw.rect(world, b.awning, aw, border_radius=3)
        for i in range(3):
            sx = aw.x + 6 + i * (aw.w - 12) / 3
            pygame.draw.line(world, tuple(min(255, v + 30) for v in b.awning), (sx, aw.y + 2), (sx, aw.bottom - 2), 2)
        pygame.draw.rect(world, tuple(max(0, v - 35) for v in b.awning), aw, 1, border_radius=3)

    def _draw_tree(self, world, tree):
        p = tree.pos
        pygame.draw.ellipse(world, (38, 55, 39),
                            (p.x - tree.canopy + 8, p.y - tree.canopy * 0.7 + 10,
                             tree.canopy * 2, tree.canopy * 1.4))
        pygame.draw.circle(world, (92, 65, 43), p + Vector2(2, 3), tree.trunk)
        pygame.draw.circle(world, (79, 54, 35), p, tree.trunk)
        shades = [(52, 92, 54), (63, 108, 62), (77, 126, 70), (95, 144, 82)]
        for i, ratio in enumerate((1.0, 0.78, 0.55, 0.32)):
            off = 9 * (1.0 - ratio)
            col = shades[i]
            pygame.draw.circle(world, col, (p.x - off, p.y - off * 0.6), int(tree.canopy * ratio))
        pygame.draw.circle(world, (111, 158, 91),
                           (p.x - tree.canopy * 0.26, p.y - tree.canopy * 0.3),
                           max(2, int(tree.canopy * 0.24)))

    def _draw_prop(self, world, kind, p):
        if kind == "lamp":
            pygame.draw.circle(world, (32, 34, 39), p + Vector2(3, 4), 8)
            pygame.draw.circle(world, (83, 87, 95), p, 7)
            pygame.draw.circle(world, (146, 149, 154), p, 4)
            pygame.draw.circle(world, (241, 219, 144), p, 2)
            pygame.draw.circle(world, (255, 240, 186), p, 1)
        elif kind == "hydrant":
            pygame.draw.circle(world, (38, 40, 45), p + Vector2(2, 3), 6)
            pygame.draw.rect(world, (169, 58, 48), (p.x - 5, p.y - 4, 10, 12), border_radius=3)
            pygame.draw.circle(world, (209, 79, 64), p, 5)
            pygame.draw.rect(world, (128, 41, 35), (p.x - 7, p.y + 2, 14, 3), border_radius=1)
        elif kind == "bin":
            pygame.draw.circle(world, (32, 34, 39), p + Vector2(2, 3), 8)
            pygame.draw.circle(world, (59, 74, 62), p, 8)
            pygame.draw.circle(world, (89, 107, 91), p, 6)
            pygame.draw.circle(world, (50, 61, 52), p, 3)

    def _render_minimap(self):
        scale = 3
        surf = pygame.Surface((S.MAP_W * scale, S.MAP_H * scale)).convert()
        surf.fill((30, 32, 38))
        for ty in range(S.MAP_H):
            for tx in range(S.MAP_W):
                t = self.tiles[ty][tx]
                if t == S.ROAD:
                    col = (53, 56, 64)
                elif t == S.WALK:
                    col = (105, 109, 117)
                elif t == S.BUILDING:
                    col = (164, 165, 167)
                elif t == S.GRASS:
                    col = (67, 110, 66)
                else:
                    col = (72, 74, 81)
                pygame.draw.rect(surf, col, (tx * scale, ty * scale, scale, scale))
        for p in self.fountains:
            mx = int(p.x / S.WORLD_W * S.MAP_W * scale)
            my = int(p.y / S.WORLD_H * S.MAP_H * scale)
            pygame.draw.circle(surf, (82, 148, 171), (mx, my), 2)
        pygame.draw.rect(surf, (26, 28, 33), surf.get_rect(), 2)
        return surf


# ===========================================================================
# MODUL: entities
# ===========================================================================

"""Oyuncu, araçlar, NPC'ler, mermiler ve efektler."""
import math
import random

import pygame
from pygame.math import Vector2



# ---------------------------------------------------------------------------
# Parçacıklar
# ---------------------------------------------------------------------------
class Particle:
    __slots__ = ("pos", "vel", "life", "max_life", "size", "grow", "color",
                 "kind", "drag", "gravity", "angle")

    def __init__(self, pos, vel, life, size, color, kind="circle", drag=3.0,
                 gravity=0.0, grow=0.0, angle=0.0):
        self.pos = Vector2(pos)
        self.vel = Vector2(vel)
        self.life = life
        self.max_life = life
        self.size = size
        self.color = color
        self.kind = kind
        self.drag = drag
        self.gravity = gravity
        self.grow = grow
        self.angle = angle

    def update(self, dt):
        self.life -= dt
        self.pos += self.vel * dt
        if self.drag:
            self.vel *= math.exp(-self.drag * dt)
        if self.gravity:
            self.vel.y += self.gravity * dt
        self.size += self.grow * dt
        return self.life > 0

    def draw(self, surface, cam):
        sx = self.pos.x - cam.x
        sy = self.pos.y - cam.y
        if sx < -40 or sy < -40 or sx > S.SCREEN_W + 40 or sy > S.SCREEN_H + 40:
            return
        t = max(0.0, self.life / self.max_life)
        if self.kind == "smoke":
            col = (int(105 * t + 48), int(107 * t + 50), int(112 * t + 54))
            r = max(1, int(self.size * (1.3 - t * 0.3)))
            pygame.draw.circle(surface, col, (int(sx), int(sy)), r)
        elif self.kind == "fire":
            col = (int(45 + 210 * t), int(40 + 155 * t), int(30 + 70 * t))
            r = max(1, int(self.size * (0.35 + t * 0.7)))
            pygame.draw.circle(surface, col, (int(sx), int(sy)), r)
        elif self.kind == "flash":
            radius = max(4, int(self.size * (0.65 + 0.35 * t)))
            glow = get_glow(radius, (255, 198, 112))
            surface.blit(glow, (int(sx - radius), int(sy - radius)),
                         special_flags=pygame.BLEND_ADD)
            pygame.draw.circle(surface, (255, 246, 214), (int(sx), int(sy)),
                               max(2, int(radius * 0.4)))
        elif self.kind == "blood":
            r = max(1, int(self.size * (0.4 + t * 0.6)))
            pygame.draw.circle(surface, self.color, (int(sx), int(sy)), r)
        elif self.kind == "spark":
            pygame.draw.circle(surface, (255, 246, 198), (int(sx), int(sy)), max(1, int(self.size * t)))
            pygame.draw.line(surface, self.color, (sx, sy),
                             (sx - self.vel.x * 0.012, sy - self.vel.y * 0.012), 1)
        elif self.kind == "casing":
            pygame.draw.rect(surface, (214, 177, 84),
                             (int(sx), int(sy), max(2, int(self.size)), max(1, int(self.size * 0.5))))
        elif self.kind == "ring":
            r = int(8 + self.size * (1.0 - t))
            pygame.draw.circle(surface, self.color, (int(sx), int(sy)), r, 2)
        else:
            pygame.draw.circle(surface, self.color, (int(sx), int(sy)), max(1, int(self.size * t)))


class FloatingText:
    def __init__(self, pos, text, color, size=16):
        self.pos = Vector2(pos)
        self.text = text
        self.color = color
        self.size = size
        self.life = 1.25
        self.max_life = 1.25

    def update(self, dt):
        self.life -= dt
        self.pos.y -= 32 * dt
        return self.life > 0

    def draw(self, surface, cam):
        alpha = int(255 * clamp(self.life / self.max_life, 0, 1))
        font = get_font(self.size, True)
        img = font.render(self.text, True, self.color)
        img.set_alpha(alpha)
        shadow = font.render(self.text, True, (6, 7, 10))
        shadow.set_alpha(alpha)
        x = int(self.pos.x - cam.x)
        y = int(self.pos.y - cam.y)
        surface.blit(shadow, shadow.get_rect(center=(x + 1, y + 2)))
        surface.blit(img, img.get_rect(center=(x, y)))


# ---------------------------------------------------------------------------
# Mermiler
# ---------------------------------------------------------------------------
class Bullet:
    def __init__(self, pos, angle, spec, owner="player"):
        self.pos = Vector2(pos)
        self.prev = self.pos.copy()
        self.vel = Vector2(math.cos(angle), math.sin(angle)) * spec["speed"]
        self.damage = spec["damage"]
        self.owner = owner
        self.range = spec.get("range", 1000)
        self.life = self.range / spec["speed"]
        self.color = spec.get("tracer", (255, 238, 160))
        self.alive = True
        self.length = 22 if owner == "player" else 16

    def update(self, dt, game):
        if not self.alive:
            return
        self.prev = self.pos.copy()
        self.pos += self.vel * dt
        self.life -= dt
        if self.life <= 0:
            self.alive = False
            return
        dist = (self.pos - self.prev).length()
        steps = max(1, int(dist / 7))
        for i in range(1, steps + 1):
            p = self.prev.lerp(self.pos, i / steps)
            if game.city.is_solid_pos(p.x, p.y):
                game.bullet_hit_wall(p, self)
                self.alive = False
                return
            for car in game.cars:
                if not car.alive:
                    continue
                if self.owner == "player" and game.player.car is car:
                    continue
                if car.overlaps_circle(p, 3):
                    game.bullet_hit_car(car, self, p)
                    self.alive = False
                    return
            if self.owner == "player":
                for npc in game.npcs:
                    if npc.alive and (npc.pos - p).length_squared() < 15 * 15:
                        npc.hurt(self.damage, game, self.vel)
                        self.alive = False
                        return
            else:
                pl = game.player
                if not pl.dead and pl.car is None and (pl.pos - p).length_squared() < 13 * 13:
                    pl.hurt(self.damage, game, self.pos)
                    self.alive = False
                    return

    def draw(self, surface, cam):
        d = self.vel.normalize()
        a = self.pos - d * self.length
        b = self.pos
        pygame.draw.line(surface, (255, 248, 210), (int(a.x - cam.x), int(a.y - cam.y)),
                         (int(b.x - cam.x), int(b.y - cam.y)), 2)
        pygame.draw.circle(surface, self.color, (int(b.x - cam.x), int(b.y - cam.y)), 2)


# ---------------------------------------------------------------------------
# Araçlar
# ---------------------------------------------------------------------------
class Car:
    def __init__(self, pos, angle, kind, color, traffic=False):
        self.pos = Vector2(pos)
        self.angle = float(angle)
        self.kind = kind
        self.spec = S.CARS[kind]
        self.color = color
        self.width, self.height = self.spec["size"]
        self.vel = Vector2()
        self.health = self.spec["health"]
        self.max_health = self.health
        self.alive = True
        self.controlled = False
        self.traffic = traffic
        self.sprite = art.get_car_sprite(kind, color)
        self.wreck_sprite = self.sprite.copy()
        self.wreck_sprite.fill((82, 82, 82), special_flags=pygame.BLEND_MULT)
        self.hit_cd = 0.0
        self.impact_cd = 0.0
        self.skid_cd = 0.0
        self.smoke_cd = 0.0
        self.stuck_time = 0.0
        self.offroad_time = 0.0
        self.brake = False
        self.driver_visible = False
        self.nav_from = (0, 0)
        self.nav_to = (0, 0)
        self.nav_dir = Vector2(1, 0)
        self.target = Vector2(pos)
        self.cruise = 150.0
        self.dead_timer = 0.0
        self.prev_wheels = None

    # -- yardımcılar -------------------------------------------------------
    @property
    def forward(self):
        return Vector2(math.cos(self.angle), math.sin(self.angle))

    @property
    def right(self):
        return Vector2(-math.sin(self.angle), math.cos(self.angle))

    @property
    def speed(self):
        return self.vel.length()

    def setup_traffic(self, city, rng):
        self.traffic = True
        self.controlled = False
        while True:
            c = rng.randint(0, S.COLS)
            r = rng.randint(0, S.ROWS)
            options = []
            if c < S.COLS:
                options.append((1, 0))
            if c > 0:
                options.append((-1, 0))
            if r < S.ROWS:
                options.append((0, 1))
            if r > 0:
                options.append((0, -1))
            if not options:
                continue
            direction = Vector2(rng.choice(options))
            start = city.intersections[r * (S.COLS + 1) + c]
            next_i = Vector2(c + int(direction.x), r + int(direction.y))
            target_center = city.intersections[int(next_i.y) * (S.COLS + 1) + int(next_i.x)]
            self.nav_from = (c, r)
            self.nav_to = (int(next_i.x), int(next_i.y))
            self.nav_dir = direction
            self.angle = math.atan2(direction.y, direction.x)
            self.target = city.lane_target(target_center, direction)
            start_lane = city.lane_target(start, direction)
            self.pos = start_lane + direction * rng.uniform(24, 100)
            self.vel = Vector2()
            break
        self.cruise = rng.uniform(125, 170)

    def local_point(self, world_point):
        return rotate(Vector2(world_point) - self.pos, -self.angle)

    def overlaps_circle(self, point, radius):
        lp = self.local_point(point)
        return (abs(lp.x) <= self.width * 0.5 + radius and
                abs(lp.y) <= self.height * 0.5 + radius)

    def push_out_circle(self, point, radius):
        lp = self.local_point(point)
        hw = self.width * 0.5 + radius
        hh = self.height * 0.5 + radius
        if abs(lp.x) >= hw or abs(lp.y) >= hh:
            return None
        dx = hw - abs(lp.x)
        dy = hh - abs(lp.y)
        if dx < dy:
            push = Vector2(dx * (1 if lp.x >= 0 else -1), 0)
        else:
            push = Vector2(0, dy * (1 if lp.y >= 0 else -1))
        return rotate(push, self.angle)

    def _resolve_body(self, city):
        fwd = self.forward
        total = Vector2()
        for off in (-self.width * 0.32, 0, self.width * 0.32):
            p = self.pos + fwd * off
            push = city.resolve_circle(p, self.height * 0.5)
            total += push
        if total.length_squared() > 0:
            self.pos += total
        return total

    def _surface_factor(self, city):
        tile = city.tile_at_pos(self.pos.x, self.pos.y)
        if tile == S.GRASS:
            return 0.58, 0.75
        if tile == S.WALK:
            return 0.82, 0.9
        if tile == S.LOT:
            return 0.9, 0.95
        return 1.0, 1.0

    # -- fizik -------------------------------------------------------------
    def drive(self, dt, game, throttle=0.0, steer=0.0, handbrake=False):
        if not self.alive:
            return
        city = game.city
        speed_factor, grip_factor = self._surface_factor(city)
        fwd = self.forward
        right = self.right
        v_fwd = self.vel.dot(fwd)
        v_lat = self.vel.dot(right)
        max_fwd = self.spec["max_speed"] * speed_factor

        if throttle > 0.05:
            if v_fwd < max_fwd:
                accel = self.spec["accel"] * throttle * (1.0 - 0.45 * max(0.0, v_fwd) / max_fwd)
                v_fwd += accel * dt
        elif throttle < -0.05:
            if v_fwd > 12.0:
                v_fwd -= self.spec["brake"] * (-throttle) * dt
            else:
                v_fwd -= self.spec["accel"] * 0.52 * (-throttle) * dt

        if abs(throttle) > 0.05:
            v_fwd *= math.exp(-0.24 * dt)
        else:
            v_fwd *= math.exp(-1.7 * dt)
        if handbrake:
            v_fwd *= math.exp(-2.25 * dt)
            v_lat *= math.exp(-1.15 * dt)
        else:
            v_lat *= math.exp(-self.spec["grip"] * grip_factor * dt)
        v_fwd = clamp(v_fwd, -max_fwd * 0.38, max_fwd)
        self.vel = fwd * v_fwd + right * v_lat

        steer_amount = clamp(abs(v_fwd) / 150.0, 0.0, 1.0)
        if v_fwd < -2:
            steer_amount *= -1
        turn = self.spec["turn"] * (1.0 + (0.22 if handbrake else 0))
        self.angle += steer * turn * steer_amount * dt
        self.brake = throttle < -0.05 or handbrake

        self.pos += self.vel * dt
        push = self._resolve_body(city)
        impact = 0.0
        if push.length_squared() > 0.01:
            n = push.normalize()
            vn = self.vel.dot(n)
            if vn < 0:
                impact = -vn
                self.vel -= n * vn * 1.25
        if impact > 115 and self.impact_cd <= 0:
            self.health -= impact * 0.085
            self.impact_cd = 0.35
            game.on_car_crash(self, impact)
            if self.health <= 0:
                game.explode_car(self)

        self._skid_and_effects(dt, game, v_lat, handbrake, v_fwd)
        self._hit_people(dt, game)
        if self.health <= 0:
            game.explode_car(self)

    def _skid_and_effects(self, dt, game, v_lat, handbrake, v_fwd):
        speed = abs(v_fwd)
        if speed > 110 and (abs(v_lat) > 62 or handbrake):
            self.skid_cd -= dt
            if self.skid_cd <= 0:
                self.skid_cd = 0.022
                fwd = self.forward
                right = self.right
                rear = self.pos - fwd * self.width * 0.34
                for side in (-1, 1):
                    wheel = rear + right * side * self.height * 0.36
                    if self.prev_wheels is not None:
                        old = self.prev_wheels[0 if side < 0 else 1]
                        pygame.draw.line(game.city.surface, (37, 39, 46),
                                         (int(old.x), int(old.y)), (int(wheel.x), int(wheel.y)), 5)
                    if self.prev_wheels is None:
                        self.prev_wheels = [wheel.copy(), wheel.copy()]
                    else:
                        self.prev_wheels[0 if side < 0 else 1] = wheel.copy()
                if random.random() < 0.3:
                    game.spawn_smoke(self.pos + self.forward * -8, 1, dark=True)
        else:
            self.prev_wheels = None
        if self.health < self.max_health * 0.42:
            self.smoke_cd -= dt
            if self.smoke_cd <= 0:
                self.smoke_cd = 0.16 if self.health < self.max_health * 0.2 else 0.4
                p = self.pos + self.forward * self.width * 0.34 + random_unit() * 8
                game.spawn_car_smoke(p, self.health < self.max_health * 0.2)

    def _hit_people(self, dt, game):
        self.hit_cd = max(0.0, self.hit_cd - dt)
        speed = self.vel.length()
        hit_speed = speed
        for npc in game.npcs:
            if not npc.alive:
                continue
            if abs(npc.pos.x - self.pos.x) > 70 or abs(npc.pos.y - self.pos.y) > 70:
                continue
            if self.overlaps_circle(npc.pos, 8):
                if hit_speed > 85 and self.hit_cd <= 0:
                    imp = unit(self.vel) * (hit_speed * 0.7) + random_unit() * 40
                    npc.knock += imp
                    npc.hurt(max(16, hit_speed * 0.17), game, self.vel,
                             by_player=self.controlled)
                    game.on_person_hit_by_car(npc, self, hit_speed)
                    self.hit_cd = 0.6
                    self.vel *= 0.94
                else:
                    push = self.push_out_circle(npc.pos, 8)
                    if push:
                        npc.pos += push * 0.5
        pl = game.player
        if not pl.dead and pl.car is None and self.overlaps_circle(pl.pos, 10):
            if speed > 100 and self.hit_cd <= 0:
                pl.knock += unit(self.vel) * (speed * 0.75)
                pl.hurt(16 + speed * 0.035, game, self.pos)
                game.on_person_hit_by_car(pl, self, speed)
                game.shake(10)
                self.hit_cd = 0.6
            else:
                push = self.push_out_circle(pl.pos, 10)
                if push:
                    pl.pos += push

    # -- trafik ------------------------------------------------------------
    def update(self, dt, game):
        if not self.alive:
            self.dead_timer += dt
            return
        self.impact_cd = max(0.0, self.impact_cd - dt)
        self.hit_cd = max(0.0, self.hit_cd - dt)
        if self.controlled:
            return
        if self.traffic:
            self._traffic_update(dt, game)
        else:
            if self.vel.length_squared() > 1:
                self.vel *= math.exp(-4 * dt)
                self.pos += self.vel * dt
                self._resolve_body(game.city)

    def _traffic_update(self, dt, game):
        city = game.city
        to_target = self.target - self.pos
        dist = to_target.length()
        if dist < 62 or (dist < 130 and unit(to_target).dot(self.forward) < -0.15):
            self._choose_next_leg(game)
            to_target = self.target - self.pos
            dist = to_target.length()
        if dist > 1:
            desired = math.atan2(to_target.y, to_target.x)
        else:
            desired = self.angle
        delta = angle_diff(desired, self.angle)
        steer = clamp(delta * 2.4, -1.0, 1.0)
        if abs(delta) > 1.15:
            steer = clamp(delta * 3.0, -1.0, 1.0)
        throttle = 0.52
        if abs(delta) > 0.75:
            throttle = 0.28
        if dist < 110:
            throttle = min(throttle, 0.2)
        # Önünde engel var mı?
        ahead = self.forward
        for other in game.cars:
            if other is self or not other.alive:
                continue
            rel = other.pos - self.pos
            d = rel.length()
            if d < 118 and d > 0.1 and rel.dot(ahead) > d * 0.55:
                throttle = 0.0
                self.brake = True
                break
        if throttle > 0:
            for npc in game.npcs:
                if not npc.alive:
                    continue
                rel = npc.pos - self.pos
                d = rel.length()
                if d < 92 and d > 0.1 and rel.dot(ahead) > d * 0.6:
                    throttle = 0.0
                    break
        pl = game.player
        if pl.car is None and not pl.dead:
            rel = pl.pos - self.pos
            d = rel.length()
            if d < 100 and d > 0.1 and rel.dot(ahead) > d * 0.55:
                throttle = 0.0

        # Trafik aracı seyir hızını aşmasın; virajları daha rahat alsın.
        if self.speed > self.cruise * 1.12:
            throttle = -0.4
        elif self.speed > self.cruise:
            throttle = min(throttle, 0.0)

        if city.tile_at_pos(self.pos.x, self.pos.y) == S.ROAD:
            self.offroad_time = max(0.0, self.offroad_time - dt * 2.0)
        else:
            self.offroad_time += dt
        if self.speed < 22 and throttle <= 0.05:
            self.stuck_time += dt
        else:
            self.stuck_time = 0.0

        if self.offroad_time > 1.6 or self.stuck_time > 5.0:
            if (self.pos - pl.position).length() > 700:
                self._reset_traffic(game)
                return
            # Oyuncunun yakınında teleport etmek yerine geri dön.
            self.angle += math.pi
            self.vel *= -0.25
            self.stuck_time = 0.0
            self.offroad_time = 0.0
            self.drive(dt, game, 0.5, 0.0, False)
            return

        self.drive(dt, game, throttle, steer, False)

    def _reset_traffic(self, game):
        """Tıkanan veya yoldan çıkan trafik aracını uygun bir şeride taşı."""
        for _ in range(24):
            self.setup_traffic(game.city, game.rng)
            if (self.pos - game.player.position).length() < 700:
                continue
            if any(o is not self and o.alive and (o.pos - self.pos).length() < 140
                   for o in game.cars):
                continue
            break
        self.vel = Vector2()
        self.stuck_time = 0.0
        self.offroad_time = 0.0
        self.hit_cd = 0.0

    def _choose_next_leg(self, game, force=False):
        city = game.city
        c, r = self.nav_to
        options = []
        if c < S.COLS:
            options.append((1, 0))
        if c > 0:
            options.append((-1, 0))
        if r < S.ROWS:
            options.append((0, 1))
        if r > 0:
            options.append((0, -1))
        back = (-int(self.nav_dir.x), -int(self.nav_dir.y))
        filtered = [o for o in options if o != back]
        choices = filtered or options
        if not choices:
            return
        # Çoğunlukla düz git
        straight = (int(self.nav_dir.x), int(self.nav_dir.y))
        if straight in choices and random.random() < 0.55:
            nxt = straight
        else:
            nxt = random.choice(choices)
        self.nav_from = (c, r)
        self.nav_to = (c + nxt[0], r + nxt[1])
        self.nav_dir = Vector2(nxt)
        nc, nr = self.nav_to
        center = city.intersections[nr * (S.COLS + 1) + nc]
        self.target = city.lane_target(center, self.nav_dir)
        self.cruise = random.uniform(125, 175)

    # -- hasar / patlama ---------------------------------------------------
    def hurt(self, amount, game, source=None):
        if not self.alive:
            return
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            game.explode_car(self)

    def draw(self, surface, cam, player_car=False, aim_angle=0.0):
        pos = self.pos - cam
        shadow = art.get_shadow(self.width * 1.18, self.height * 1.26, 95 if self.alive else 70)
        surface.blit(shadow, shadow.get_rect(center=(int(pos.x + 4), int(pos.y + 7))))
        sprite = self.sprite if self.alive else self.wreck_sprite
        rotated = pygame.transform.rotate(sprite, -math.degrees(self.angle))
        rect = rotated.get_rect(center=(int(pos.x), int(pos.y)))
        surface.blit(rotated, rect)
        if self.alive:
            # Fren lambaları
            if self.brake or self.health < self.max_health * 0.35:
                fwd = self.forward
                right = self.right
                for side in (-1, 1):
                    lp = self.pos - fwd * self.width * 0.46 + right * side * self.height * 0.27
                    sx = lp.x - cam.x
                    sy = lp.y - cam.y
                    pygame.draw.circle(surface, (226, 48, 38), (int(sx), int(sy)), 4)
                    pygame.draw.circle(surface, (255, 140, 100), (int(sx), int(sy)), 2)
            if player_car:
                d = Vector2(math.cos(aim_angle), math.sin(aim_angle))
                side = 1 if d.dot(self.right) >= 0 else -1
                start = pos + self.right * side * (self.height * 0.48)
                hand = start + d * 13
                gun = hand + d * 10
                pygame.draw.line(surface, (31, 89, 94), (int(start.x), int(start.y)),
                                 (int(hand.x), int(hand.y)), 5)
                pygame.draw.circle(surface, (206, 161, 122), (int(hand.x), int(hand.y)), 3)
                pygame.draw.line(surface, (38, 40, 47), (int(hand.x), int(hand.y)),
                                 (int(gun.x), int(gun.y)), 4)
                pygame.draw.circle(surface, (126, 130, 138), (int(gun.x), int(gun.y)), 2)


# ---------------------------------------------------------------------------
# NPC'ler
# ---------------------------------------------------------------------------
PED_SHIRTS = [
    (163, 76, 68), (70, 103, 154), (196, 158, 67), (89, 145, 101),
    (145, 92, 151), (196, 196, 190), (95, 99, 112), (177, 109, 62),
    (80, 146, 149), (118, 88, 126),
]
PED_HAIR = [(41, 33, 28), (66, 48, 34), (24, 24, 26), (109, 82, 50), (75, 57, 46)]


class NPC:
    def __init__(self, pos, kind="ped", rng=None):
        rng = rng or random
        self.kind = kind
        self.pos = Vector2(pos)
        self.angle = rng.uniform(0, math.tau)
        self.body_color = S.COP_BLUE if kind == "cop" else rng.choice(PED_SHIRTS)
        self.body_dark = S.COP_BLUE_DARK if kind == "cop" else tuple(
            max(0, v - 42) for v in self.body_color)
        self.skin = S.COP_SKIN if kind == "cop" else rng.choice([(201, 157, 120), (172, 126, 92), (140, 96, 68), (224, 184, 148)])
        self.hair = rng.choice(PED_HAIR) if kind == "ped" else S.COP_HAT
        self.hp = 105 if kind == "cop" else rng.randint(52, 72)
        self.max_hp = self.hp
        self.alive = True
        self.speed = 0.0
        self.base_speed = rng.uniform(S.PED_SPEED_MIN, S.PED_SPEED_MAX) if kind == "ped" else S.COP_SPEED
        self.anim = rng.uniform(0, 10)
        self.moving = False
        self.knock = Vector2()
        self.walk_dir = random_unit(rng)
        self.timer = rng.uniform(1.0, 4.0)
        self.panic = 0.0
        self.panic_src = None
        self.shoot_cd = rng.uniform(0.6, 1.4)
        self.state = "walk"
        self.leave_timer = 0.0
        self.stuck_time = 0.0
        self.strafe_dir = rng.choice((-1, 1))
        self.remove = False
        self.hit_flash = 0.0
        self.path = []
        self.path_i = 0
        self.path_time = 0.0
        self.by_player = False

    def scare(self, source):
        if self.kind != "ped" or not self.alive:
            return
        self.panic = random.uniform(3.0, 6.5)
        self.panic_src = Vector2(source)
        self.state = "panic"

    def hurt(self, amount, game, direction=None, by_player=True):
        if not self.alive:
            return
        self.hp -= amount
        self.hit_flash = 0.15
        if by_player:
            self.by_player = True
        if direction is not None and direction.length_squared() > 0:
            self.knock += unit(direction) * 55
        if self.kind == "ped":
            self.scare(game.player.position)
        game.spawn_blood(self.pos, direction if direction is not None else Vector2(1, 0), 6)
        game.audio.play("hit", 0.45, self.pos, game.player.position)
        if self.hp <= 0:
            self.alive = False
            game.on_npc_died(self)

    def update(self, dt, game):
        if not self.alive:
            return
        self.hit_flash = max(0.0, self.hit_flash - dt)
        self.anim += dt * (3.0 + self.speed * 0.045)
        if self.knock.length_squared() > 4:
            self.pos += self.knock * dt
            self.knock *= math.exp(-4.2 * dt)
            game.city.resolve_circle(self.pos, 9.5)
        if self.kind == "ped":
            self._update_ped(dt, game)
        else:
            self._update_cop(dt, game)

    def _update_ped(self, dt, game):
        if self.panic > 0:
            self.panic -= dt
            speed = 190
            if self.panic_src is not None:
                away = self.pos - self.panic_src
                if away.length_squared() < 1:
                    away = Vector2(1, 0)
                dirv = away.normalize()
            else:
                dirv = self.walk_dir
            dirv = rotate(dirv, math.sin(self.anim * 0.7) * 0.15)
            self._move(dt, dirv, speed, game)
            if self.panic <= 0:
                self.state = "walk"
                self.timer = 0
            return
        # Oyuncu silahını yakınındaki yayaya doğrultursa panik
        pl = game.player
        if not pl.dead and pl.car is None:
            to_ped = self.pos - pl.pos
            d = to_ped.length()
            if d < 280 and d > 1:
                aim = Vector2(math.cos(pl.angle), math.sin(pl.angle))
                if aim.dot(to_ped / d) > 0.955 and pl.muzzle_timer <= 0:
                    if random.random() < dt * 1.6:
                        self.scare(pl.pos)
                        return
        self.timer -= dt
        if self.timer <= 0 or (self.pos - (self.pos + self.walk_dir * 80)).length() < 1:
            self.timer = random.uniform(2.5, 6.5)
            self.walk_dir = random_unit()
        speed = self.base_speed
        push = self._move(dt, self.walk_dir, speed, game)
        if push.length_squared() > 0.2:
            self.walk_dir = rotate(self.walk_dir, random.uniform(1.0, 2.2))
            self.timer = random.uniform(1.5, 3.5)

    def _update_cop(self, dt, game):
        pl = game.player
        target = pl.position
        dist = (target - self.pos).length()
        if pl.dead or pl.wanted < 0.7:
            self.state = "leave"
            self.leave_timer += dt
            if self.leave_timer > 16:
                self.remove = True
                return
            away = self.pos - target
            if away.length_squared() < 1:
                away = Vector2(1, 0)
            self._move(dt, away.normalize(), self.base_speed * 0.85, game)
            return
        self.state = "chase"
        los = not game.city.line_blocked(self.pos, target)
        desired_angle = math.atan2(target.y - self.pos.y, target.x - self.pos.x)
        self.angle = desired_angle
        self.shoot_cd -= dt
        if los and dist < 500:
            # Çatışma mesafesi
            if dist > 300:
                move = (target - self.pos).normalize()
            elif dist < 110:
                move = (self.pos - target).normalize()
            else:
                perp = Vector2(-math.sin(desired_angle), math.cos(desired_angle))
                move = perp * self.strafe_dir * 0.6
                if random.random() < dt * 0.4:
                    self.strafe_dir *= -1
            self._move(dt, move, self.base_speed * 0.65, game)
            self.path_time = 0.0
            if self.shoot_cd <= 0 and dist > 55:
                self.shoot_cd = random.uniform(0.72, 1.15)
                spread = 0.035 + max(0.0, dist - 200) * 0.00011
                aim = math.atan2(target.y - self.pos.y, target.x - self.pos.x) + random.uniform(-spread, spread)
                muzzle = self.pos + Vector2(math.cos(aim), math.sin(aim)) * 16
                game.spawn_cop_bullet(muzzle, aim, self)
                game.spawn_muzzle_flash(muzzle, aim, 0.55)
                game.audio.play("cop_shot", 0.7, self.pos, game.player.position, 1400)
        else:
            # Binalarin etrafindan A* ile dolan
            self.path_time -= dt
            if self.path_time <= 0 or not self.path:
                self.path = game.city.find_path(self.pos, target)
                self.path_i = 0
                self.path_time = random.uniform(1.0, 1.7)
            while self.path_i < len(self.path) and (self.path[self.path_i] - self.pos).length() < 28:
                self.path_i += 1
            if self.path_i < len(self.path):
                move = unit(self.path[self.path_i] - self.pos)
            else:
                move = target - self.pos
                move = unit(move) if move.length_squared() > 1 else Vector2()
            push = self._move(dt, move, self.base_speed, game)
            if push.length_squared() > 0.5:
                self.path_time = 0.0
                alt = rotate(move, 1.25 * self.strafe_dir)
                self._move(dt, alt, self.base_speed * 0.75, game)
                if self.stuck_time > 0.7:
                    self.strafe_dir *= -1
                    self.stuck_time = 0
                else:
                    self.stuck_time += dt

    def _move(self, dt, direction, speed, game):
        if direction.length_squared() < 0.0001:
            return Vector2()
        self.angle = math.atan2(direction.y, direction.x)
        self.pos += direction * speed * dt
        self.speed = speed
        self.moving = True
        push = game.city.resolve_circle(self.pos, 9.5)
        if push.length_squared() > 0.01:
            self.moving = False
        return push

    def draw(self, surface, cam):
        art.draw_npc(surface, NPCView(self.pos - cam, self))


class NPCView:
    """art.draw_npc icin ekran koordinatli basit görünüm."""
    __slots__ = ("pos", "angle", "body_color", "body_dark", "skin", "hair",
                 "kind", "moving", "anim")

    def __init__(self, pos, npc):
        self.pos = pos
        self.angle = npc.angle
        self.body_color = npc.body_color
        self.body_dark = npc.body_dark
        self.skin = npc.skin
        self.hair = npc.hair
        self.kind = npc.kind
        self.moving = npc.moving
        self.anim = npc.anim


# ---------------------------------------------------------------------------
# Oyuncu
# ---------------------------------------------------------------------------
class Player:
    def __init__(self, pos):
        self.pos = Vector2(pos)
        self.angle = -math.pi / 2
        self.health = 100.0
        self.max_health = 100.0
        self.armor = 0.0
        self.money = 250
        self.wanted = 0.0
        self.crime_timer = 0.0
        self.dead = False
        self.car = None
        self.weapon = "pistol"
        self.mag = {k: v[0] for k, v in S.START_AMMO.items()}
        self.reserve = {k: v[1] for k, v in S.START_AMMO.items()}
        self.shoot_cd = 0.0
        self.reload_timer = 0.0
        self.reload_total = 0.0
        self.muzzle_timer = 0.0
        self.hit_flash = 0.0
        self.invuln = 0.0
        self.walk_phase = 0.0
        self.moving = False
        self.knock = Vector2()
        self.recoil = 0.0
        self.deaths = 0
        self.kills = 0

    @property
    def position(self):
        return self.car.pos if self.car is not None else self.pos

    @property
    def weapon_spec(self):
        return S.WEAPONS[self.weapon]

    @property
    def reloading(self):
        return self.reload_timer > 0

    def update_timers(self, dt, game):
        self.shoot_cd = max(0.0, self.shoot_cd - dt)
        self.muzzle_timer = max(0.0, self.muzzle_timer - dt)
        self.hit_flash = max(0.0, self.hit_flash - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.recoil *= math.exp(-12 * dt)
        if self.reload_timer > 0:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                self.reload_timer = 0
                spec = self.weapon_spec
                need = spec["mag"] - self.mag[self.weapon]
                take = min(need, self.reserve[self.weapon])
                self.mag[self.weapon] += take
                self.reserve[self.weapon] -= take
                game.audio.play("reload", 0.6)

    def switch_weapon(self, index, game):
        if index < 0 or index >= len(S.WEAPON_ORDER):
            return
        name = S.WEAPON_ORDER[index]
        if name == self.weapon:
            return
        self.weapon = name
        self.reload_timer = 0
        game.audio.play("door", 0.25)
        game.show_hint(f"{S.WEAPONS[name]['name']}", 1.1)

    def start_reload(self, game):
        if getattr(game, "god_mode", False):
            return False
        if self.reloading:
            return False
        spec = self.weapon_spec
        if self.mag[self.weapon] >= spec["mag"] or self.reserve[self.weapon] <= 0:
            return False
        self.reload_total = spec["reload"]
        self.reload_timer = spec["reload"]
        game.audio.play("reload", 0.55)
        return True

    def try_shoot(self, game, target, angle=None):
        god = getattr(game, "god_mode", False)
        if self.dead or self.shoot_cd > 0 or (self.reloading and not god):
            return False
        if god and self.reloading:
            self.reload_timer = 0.0
        spec = self.weapon_spec
        if not god:
            if self.mag[self.weapon] <= 0:
                if self.reserve[self.weapon] > 0:
                    self.start_reload(game)
                else:
                    game.audio.play("empty", 0.4)
                    self.shoot_cd = 0.25
                return False
            self.mag[self.weapon] -= 1
        self.shoot_cd = spec["delay"]
        target = Vector2(target)
        if angle is None:
            angle = math.atan2(target.y - self.position.y, target.x - self.position.x)
        self.angle = angle
        self.muzzle_timer = 0.07
        self.recoil = spec["recoil"]
        # Namlu, hedefe dogrudan nisan alir: yakin mesafede kayma olmaz.
        game.player_fired(self, target, spec)
        if not god and self.mag[self.weapon] == 0:
            self.start_reload(game)
        return True

    def hurt(self, amount, game, source=None):
        if getattr(game, "god_mode", False):
            return
        if self.dead or self.invuln > 0:
            return
        self.invuln = 0.09
        if self.armor > 0:
            absorbed = min(self.armor, amount * 0.62)
            self.armor -= absorbed
            amount -= absorbed
        self.health -= amount
        self.hit_flash = 0.35
        game.on_player_hurt(amount, source)
        if self.health <= 0:
            self.health = 0
            game.on_player_died()
        else:
            game.audio.play("hit", 0.75)

    def heal(self, amount):
        self.health = min(self.max_health, self.health + amount)

    def add_wanted(self, amount, game):
        self.wanted = clamp(self.wanted + amount, 0.0, 5.0)
        self.crime_timer = 10.0
        if amount > 0.25:
            game.wanted_flash = 1.0
            game.audio.play("wanted", 0.35)

    def move_on_foot(self, dt, game, move):
        if self.dead or self.car is not None:
            return
        speed = 245.0
        if move.length_squared() > 0:
            move = move.normalize()
            self.pos += move * speed * dt
            self.walk_phase += dt * 12.0
            self.moving = True
        else:
            self.moving = False
        if self.knock.length_squared() > 1:
            self.pos += self.knock * dt
            self.knock *= math.exp(-5.5 * dt)
        game.city.resolve_circle(self.pos, 11)

    def draw(self, surface, cam):
        if self.car is not None or self.dead:
            return
        pos = self.pos - cam
        art.draw_player(surface, pos, self.angle, 1.0 if self.moving else 0.0,
                        self.walk_phase, in_car=False, recoil=self.recoil)


# ---------------------------------------------------------------------------
# Toplanabilirler / cesetler
# ---------------------------------------------------------------------------
class Pickup:
    def __init__(self, pos, kind, amount):
        self.pos = Vector2(pos)
        self.kind = kind
        self.amount = amount
        self.t = random.uniform(0, 10)
        self.alive = True

    def update(self, dt):
        self.t += dt

    def draw(self, surface, cam):
        bob = math.sin(self.t * 3.2) * 3
        p = Vector2(self.pos.x - cam.x, self.pos.y - cam.y + bob)
        if p.x < -30 or p.y < -30 or p.x > S.SCREEN_W + 30 or p.y > S.SCREEN_H + 30:
            return
        colors = {
            "health": (73, 206, 111),
            "armor": (85, 150, 238),
            "ammo": (238, 194, 75),
            "cash": (90, 210, 120),
        }
        col = colors.get(self.kind, (220, 220, 220))
        glow = get_glow(24, col)
        surface.blit(glow, (p.x - 24, p.y - 24), special_flags=pygame.BLEND_ADD)
        pygame.draw.circle(surface, (26, 29, 35), (int(p.x + 2), int(p.y + 4)), 12)
        pygame.draw.circle(surface, (242, 239, 225), (int(p.x), int(p.y)), 11)
        pygame.draw.circle(surface, col, (int(p.x), int(p.y)), 9)
        if self.kind == "health":
            pygame.draw.rect(surface, (250, 250, 246), (int(p.x) - 2, int(p.y) - 6, 4, 12))
            pygame.draw.rect(surface, (250, 250, 246), (int(p.x) - 6, int(p.y) - 2, 12, 4))
        elif self.kind == "armor":
            pygame.draw.polygon(surface, (234, 245, 255), [
                (p.x - 5, p.y - 5), (p.x, p.y - 8), (p.x + 5, p.y - 5),
                (p.x + 3, p.y + 5), (p.x, p.y + 8), (p.x - 3, p.y + 5)])
        elif self.kind == "ammo":
            pygame.draw.rect(surface, (62, 53, 34), (int(p.x) - 4, int(p.y) - 5, 8, 11), border_radius=1)
            pygame.draw.rect(surface, (255, 241, 173), (int(p.x) - 3, int(p.y) - 4, 6, 7), border_radius=1)
            pygame.draw.circle(surface, (216, 166, 62), (int(p.x), int(p.y) - 4), 3)
        elif self.kind == "cash":
            font = get_font(14, True)
            img = font.render("$", True, (18, 88, 43))
            surface.blit(img, img.get_rect(center=(int(p.x), int(p.y))))


class Corpse:
    def __init__(self, pos, angle, skin, body_dark, kind="ped"):
        self.pos = Vector2(pos)
        self.angle = angle
        self.skin = skin
        self.body_dark = body_dark
        self.kind = kind
        self.timer = 45.0

    def update(self, dt):
        self.timer -= dt
        return self.timer > 0

    def draw(self, surface, cam):
        art.draw_corpse(surface, CorpseView(self.pos - cam, self.angle, self.skin, self.body_dark))


class CorpseView:
    __slots__ = ("pos", "angle", "skin", "body_dark")

    def __init__(self, pos, angle, skin, body_dark):
        self.pos = pos
        self.angle = angle
        self.skin = skin
        self.body_dark = body_dark


# ===========================================================================
# MODUL: hud
# ===========================================================================

"""Oyun içi arayüz, minimap, menüler ve crosshair."""
import math

import pygame
from pygame.math import Vector2



def _make_red_vignette(width, height):
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    steps = 90
    for i in range(steps):
        t = i / steps
        alpha = int(120 * (1.0 - t) ** 2.4)
        if alpha <= 0:
            continue
        col = (145, 10, 14, alpha)
        pygame.draw.line(surf, col, (0, i), (width, i))
        pygame.draw.line(surf, col, (0, height - 1 - i), (width, height - 1 - i))
        pygame.draw.line(surf, col, (i, 0), (i, height))
        pygame.draw.line(surf, col, (width - 1 - i, 0), (width - 1 - i, height))
    return surf


class Hud:
    def __init__(self):
        self.vignette = art.make_vignette(S.SCREEN_W, S.SCREEN_H)
        self.damage_vignette = _make_red_vignette(S.SCREEN_W, S.SCREEN_H)
        self.panel_cache = {}
        self.flash_surface = pygame.Surface((S.SCREEN_W, S.SCREEN_H))
        self.flash_surface.fill((255, 200, 128))
        self.overlay = pygame.Surface((S.SCREEN_W, S.SCREEN_H), pygame.SRCALPHA)
        self.overlay.fill((5, 6, 9, 162))
        self.overlay_pause = pygame.Surface((S.SCREEN_W, S.SCREEN_H), pygame.SRCALPHA)
        self.overlay_pause.fill((5, 6, 9, 165))
        self.overlay_death = pygame.Surface((S.SCREEN_W, S.SCREEN_H), pygame.SRCALPHA)
        self.overlay_death.fill((24, 4, 6, 200))
        self.minimap_rect = pygame.Rect(18, S.SCREEN_H - 208, 259, 190)
        self.map_pos = (26, S.SCREEN_H - 200)
        self.weapon_rect = pygame.Rect(S.SCREEN_W - 348, S.SCREEN_H - 122, 330, 104)
        self.car_rect = pygame.Rect(S.SCREEN_W - 348, S.SCREEN_H - 186, 330, 48)
        self.menu_tips = [
            "Polislerden kaçmak için araç kullan; yıldızlar zamanla söner.",
            "Yayalar silah sesinden korkar. Kalabalıkta ateş etmek dikkat çeker.",
            "Araç hasarı arttıkça duman çıkar; patlamadan önce in.",
            "Şarjör bitince R tuşuyla yenisini takabilirsin.",
            "Can, zırh ve cephane kutuları minimapte renkli noktalar olarak görünür.",
        ]

    def _panel(self, surface, rect, fill=(14, 16, 22, 208), border=(58, 63, 76), radius=12):
        key = (rect.w, rect.h, fill, border, radius)
        img = self.panel_cache.get(key)
        if img is None:
            img = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(img, fill, img.get_rect(), border_radius=radius)
            if border:
                pygame.draw.rect(img, border, img.get_rect(), 1, border_radius=radius)
            self.panel_cache[key] = img
        surface.blit(img, rect.topleft)

    # ------------------------------------------------------------------ HUD
    def draw(self, screen, game):
        player = game.player
        self._draw_static_overlays(screen, player)
        if game.flash_amt > 0.01:
            self.flash_surface.set_alpha(int(118 * clamp(game.flash_amt, 0, 1)))
            screen.blit(self.flash_surface, (0, 0))
        self._draw_health(screen, player, game)
        self._draw_wanted_money(screen, player, game)
        self._draw_minimap(screen, game)
        self._draw_weapon(screen, player, game)
        if player.car is not None:
            self._draw_car_panel(screen, player.car)
            self._draw_drive_hint(screen)
        else:
            self._draw_foot_hint(screen, game)
        self._draw_hint_toast(screen, game)
        if game.state == "play":
            self._draw_crosshair(screen, game, player)
        self._draw_top_flash(screen, game)

    def _draw_static_overlays(self, screen, player):
        screen.blit(self.vignette, (0, 0))
        if player.hit_flash > 0:
            self.damage_vignette.set_alpha(int(255 * clamp(player.hit_flash / 0.35, 0, 1)))
            screen.blit(self.damage_vignette, (0, 0))
        if player.health < 28:
            alpha = int(50 + 30 * abs(math.sin(pygame.time.get_ticks() * 0.004)))
            self.damage_vignette.set_alpha(alpha)
            screen.blit(self.damage_vignette, (0, 0))

    def _draw_health(self, screen, player, game):
        rect = pygame.Rect(18, 18, 344, 98)
        self._panel(screen, rect)
        draw_text(screen, "SAĞLIK", 13, (34, 31), S.UI_DIM, bold=True)
        hp_ratio = player.health / player.max_health
        hp_col = S.UI_GREEN if hp_ratio > 0.5 else (S.UI_ACCENT if hp_ratio > 0.25 else S.UI_RED)
        draw_text(screen, f"{int(player.health)}", 20, (346, 28), S.UI_TEXT,
                  anchor="topright", bold=True)
        draw_bar(screen, (34, 52, 312, 13), player.health, player.max_health,
                 (34, 37, 45), hp_col, (18, 20, 26))
        draw_text(screen, "ZIRH", 11, (34, 74), S.UI_DIM, bold=True)
        draw_bar(screen, (80, 76, 174, 8), player.armor, 100,
                 (34, 37, 45), S.UI_BLUE)
        draw_text(screen, f"{int(player.armor)}", 13, (346, 71), S.UI_DIM,
                  anchor="topright", bold=True)
        if getattr(game, "god_mode", False):
            draw_text(screen, "GOD MODE", 11, (34, 92), S.UI_ACCENT, bold=True)
        # küçük sağlık artı simgesi
        pygame.draw.rect(screen, hp_col, (301, 30, 4, 12), border_radius=1)
        pygame.draw.rect(screen, hp_col, (297, 34, 12, 4), border_radius=1)

    def _draw_wanted_money(self, screen, player, game):
        rect = pygame.Rect(S.SCREEN_W - 300, 18, 282, 112)
        self._panel(screen, rect)
        draw_text(screen, "ARANIYOR", 12, (rect.x + 16, 30), S.UI_DIM, bold=True)
        active = int(math.ceil(player.wanted - 0.001)) if player.wanted > 0.03 else 0
        for i in range(5):
            cx = rect.x + 29 + i * 37
            cy = 63
            if i < active:
                pulse = 1.0
                if game.wanted_flash > 0 and i == active - 1:
                    pulse = 1.0 + 0.28 * game.wanted_flash
                draw_star(screen, cx, cy, 13 * pulse, 5.8 * pulse, S.UI_ACCENT)
                draw_star(screen, cx - 1, cy - 1, 6, 2.6, (255, 238, 160))
            else:
                draw_star(screen, cx, cy, 13, 5.8, (70, 73, 84), width=2)
        pygame.draw.line(screen, (48, 52, 63), (rect.x + 14, 86), (rect.right - 14, 86), 1)
        draw_text(screen, "$", 17, (rect.x + 16, 94), S.UI_GREEN, bold=True)
        draw_text(screen, format_money(player.money), 22, (rect.x + 36, 90),
                  (238, 241, 230), bold=True)
        if active > 0:
            draw_text(screen, f"{active} YILDIZ", 11, (rect.right - 16, 97),
                      (201, 158, 63), anchor="topright", bold=True)

    def _draw_minimap(self, screen, game):
        self._panel(screen, self.minimap_rect, (10, 12, 17, 220), (63, 68, 81))
        screen.blit(game.city.minimap, self.map_pos)
        mx0, my0 = self.map_pos
        mw, mh = game.city.minimap.get_size()
        sx = mw / S.WORLD_W
        sy = mh / S.WORLD_H

        # yayalar
        for npc in game.npcs:
            if not npc.alive:
                continue
            x = mx0 + npc.pos.x * sx
            y = my0 + npc.pos.y * sy
            if npc.kind == "cop":
                pygame.draw.circle(screen, (234, 75, 63), (int(x), int(y)), 3)
                pygame.draw.circle(screen, (255, 170, 160), (int(x), int(y)), 1)
        # arabalar
        for car in game.cars:
            if not car.alive:
                continue
            x = mx0 + car.pos.x * sx
            y = my0 + car.pos.y * sy
            if game.player.car is car:
                continue
            pygame.draw.rect(screen, (207, 210, 216), (int(x) - 1, int(y) - 1, 3, 3))
        # toplanabilirler
        for p in game.pickups:
            if not p.alive:
                continue
            col = {"health": (73, 206, 111), "armor": (85, 150, 238),
                   "ammo": (238, 194, 75), "cash": (90, 210, 120)}.get(p.kind, (220, 220, 220))
            pygame.draw.circle(screen, col, (int(mx0 + p.pos.x * sx), int(my0 + p.pos.y * sy)), 2)
        # oyuncu
        pos = game.player.position
        px = mx0 + pos.x * sx
        py = my0 + pos.y * sy
        angle = game.player.car.angle if game.player.car else game.player.angle
        d = Vector2(math.cos(angle), math.sin(angle))
        perp = Vector2(-d.y, d.x)
        tip = Vector2(px, py) + d * 7
        left = Vector2(px, py) - d * 4 + perp * 4
        right = Vector2(px, py) - d * 4 - perp * 4
        pygame.draw.polygon(screen, (255, 225, 105), [tip, left, right])
        pygame.draw.polygon(screen, (39, 39, 42), [tip, left, right], 1)
        pygame.draw.rect(screen, (160, 164, 174), (mx0, my0, mw, mh), 1)
        draw_text(screen, "N", 10, (mx0 + mw - 9, my0 + 5), (205, 205, 195), anchor="topright", bold=True)

    def _draw_weapon(self, screen, player, game):
        rect = self.weapon_rect
        self._panel(screen, rect)
        spec = player.weapon_spec
        draw_text(screen, spec["name"], 13, (rect.x + 16, rect.y + 13), S.UI_TEXT, bold=True)
        icon = art.get_weapon_icon(player.weapon, 0.95)
        screen.blit(icon, icon.get_rect(topright=(rect.right - 14, rect.y + 8)))
        ammo = player.mag[player.weapon]
        reserve = player.reserve[player.weapon]
        god = getattr(game, "god_mode", False)
        ammo_text = "∞" if god else f"{ammo}"
        draw_text(screen, ammo_text, 31, (rect.x + 14, rect.y + 31),
                  S.UI_ACCENT if (god or ammo > 0) else S.UI_RED, bold=True)
        ammo_w = get_font(31, True).size(ammo_text)[0]
        draw_text(screen, "/ ∞" if god else f"/ {reserve}", 16,
                  (rect.x + 22 + ammo_w, rect.y + 45), S.UI_DIM, bold=True)
        # silah yuvaları
        for i, name in enumerate(S.WEAPON_ORDER):
            chip = pygame.Rect(rect.x + 16 + i * 28, rect.bottom - 27, 23, 17)
            active = name == player.weapon
            pygame.draw.rect(screen, S.UI_ACCENT if active else (37, 41, 51), chip, border_radius=4)
            pygame.draw.rect(screen, (86, 92, 106), chip, 1, border_radius=4)
            draw_text(screen, str(i + 1), 11, chip.center,
                      (24, 25, 28) if active else S.UI_DIM, anchor="center", bold=True, shadow=False)
        if player.reloading:
            frac = 1.0 - player.reload_timer / player.reload_total if player.reload_total else 0
            draw_text(screen, "ŞARJÖR", 10, (rect.x + 112, rect.bottom - 24), S.UI_DIM, bold=True)
            draw_bar(screen, (rect.x + 163, rect.bottom - 21, 145, 7), frac, 1.0,
                     (34, 37, 45), S.UI_ACCENT)
        else:
            draw_text(screen, "R — ŞARJÖR", 10, (rect.x + 112, rect.bottom - 24),
                      (111, 117, 130), bold=True)

    def _draw_car_panel(self, screen, car):
        rect = self.car_rect
        self._panel(screen, rect, (14, 16, 22, 205), (58, 63, 76), 10)
        draw_text(screen, car.spec["label"].upper(), 12, (rect.x + 14, rect.y + 9), S.UI_DIM, bold=True)
        draw_bar(screen, (rect.x + 14, rect.y + 27, 140, 7), car.health, car.max_health,
                 (34, 37, 45), S.UI_GREEN if car.health > car.max_health * 0.4 else S.UI_RED)
        kmh = int(car.speed * 0.235)
        draw_text(screen, f"{kmh}", 26, (rect.right - 14, rect.y + 2), S.UI_TEXT,
                  anchor="topright", bold=True)
        draw_text(screen, "km/sa", 11, (rect.right - 16, rect.y + 30), S.UI_DIM,
                  anchor="topright", bold=True)
        if car.health < car.max_health * 0.3:
            draw_text(screen, "ARAÇ HASARLI", 10, (rect.x + 160, rect.y + 10),
                      S.UI_RED, bold=True)

    def _draw_foot_hint(self, screen, game):
        player = game.player
        if player.dead:
            return
        near = game.nearest_car
        if near is not None:
            text = "E — ARACA BİN"
            font = get_font(14, True)
            tw = font.size(text)[0]
            rect = pygame.Rect(S.SCREEN_W // 2 - tw // 2 - 18, S.SCREEN_H - 57, tw + 36, 32)
            self._panel(screen, rect, (12, 14, 20, 215), (68, 74, 88), 8)
            draw_text(screen, text, 14, (rect.centerx, rect.centery - 1), S.UI_TEXT,
                      anchor="center", bold=True)
            # araç üstünde küçük işaret
            p = near.pos - game.cam
            pygame.draw.polygon(screen, S.UI_ACCENT, [
                (p.x - 6, p.y - 60), (p.x + 6, p.y - 60), (p.x, p.y - 49)])
        else:
            draw_text(screen, "WASD  HAREKET        SOL TIK  ATEŞ        E  ARAÇ",
                      11, (S.SCREEN_W // 2, S.SCREEN_H - 30), (171, 176, 187),
                      anchor="center", bold=True, alpha=220)

    def _draw_drive_hint(self, screen):
        draw_text(screen, "E  ARAÇTAN İN        BOŞLUK  EL FRENİ        FARE  ATEŞ",
                  11, (S.SCREEN_W // 2, S.SCREEN_H - 30), (183, 187, 196),
                  anchor="center", bold=True, alpha=225)

    def _draw_hint_toast(self, screen, game):
        if game.hint_timer <= 0 or not game.hint:
            return
        alpha = int(255 * clamp(game.hint_timer / 0.45, 0, 1))
        font = get_font(14, True)
        tw = font.size(game.hint)[0]
        rect = pygame.Rect(S.SCREEN_W // 2 - tw // 2 - 20, 22, tw + 40, 30)
        self._panel(screen, rect, (12, 14, 20, 220), (64, 70, 84), 8)
        draw_text(screen, game.hint, 14, rect.center, S.UI_ACCENT, anchor="center",
                  bold=True, alpha=alpha)

    def _draw_crosshair(self, screen, game, player):
        mx, my = game.mouse_screen
        spread = 8 + player.recoil * 2.4
        if player.car is not None:
            spread += 3
        col = (248, 246, 234)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a = (mx + dx * spread, my + dy * spread)
            b = (mx + dx * (spread + 6), my + dy * (spread + 6))
            pygame.draw.line(screen, (18, 19, 23), (a[0] + 1, a[1] + 1), (b[0] + 1, b[1] + 1), 2)
            pygame.draw.line(screen, col, a, b, 2)
        pygame.draw.circle(screen, (18, 19, 23), (mx + 1, my + 1), 3)
        pygame.draw.circle(screen, col, (mx, my), 2)
        pygame.draw.circle(screen, (229, 228, 218), (mx, my), int(spread + 10), 1)

    def _draw_top_flash(self, screen, game):
        if game.wanted_flash <= 0:
            return
        alpha = int(130 * game.wanted_flash)
        for i in range(16):
            col = (207, 57, 51, alpha) if i % 2 == 0 else (55, 95, 194, alpha)
            pygame.draw.rect(screen, col, (i * S.SCREEN_W / 16, 0, S.SCREEN_W / 16 + 1, 4))

    # --------------------------------------------------------------- ekranlar
    def draw_menu(self, screen, game):
        screen.blit(self.overlay, (0, 0))
        t = pygame.time.get_ticks() / 1000.0
        rect = pygame.Rect(0, 0, 760, 492)
        rect.center = (S.SCREEN_W // 2, S.SCREEN_H // 2 + 8)
        self._panel(screen, rect, (12, 14, 20, 230), (68, 74, 88), 16)
        draw_text(screen, "SOKAKLAR", 84, (S.SCREEN_W // 2 + 3, 100), (18, 16, 12),
                  anchor="midtop", bold=True)
        draw_text(screen, "SOKAKLAR", 84, (S.SCREEN_W // 2, 96), S.UI_ACCENT,
                  anchor="midtop", bold=True)
        draw_text(screen, "2D AÇIK DÜNYA AKSİYONU", 15, (S.SCREEN_W // 2, 188),
                  (188, 191, 199), anchor="midtop", bold=True)
        pygame.draw.line(screen, (59, 64, 78), (rect.x + 70, 224), (rect.right - 70, 224), 1)
        draw_text(screen, "Şehre hoş geldin. Kurallar yok, sadece sonuçlar var.",
                  15, (S.SCREEN_W // 2, 240), (159, 165, 177), anchor="midtop")

        col1 = rect.x + 84
        col2 = rect.x + 402
        y = 294
        controls = [
            ("WASD", "Hareket / araç kullan"),
            ("FARE", "Nişan al"),
            ("SOL TIK", "Ateş et"),
            ("E", "Araca bin / in"),
            ("BOŞLUK", "El freni"),
            ("R", "Şarjör değiştir"),
        ]
        for i, (key, desc) in enumerate(controls[:3]):
            self._control_row(screen, col1, y + i * 34, key, desc)
        for i, (key, desc) in enumerate(controls[3:]):
            self._control_row(screen, col2, y + i * 34, key, desc)
        y2 = 408
        draw_text(screen, "1  2  3  silah seç        M  ses        ESC  duraklat",
                  12, (S.SCREEN_W // 2, y2 + 4), (137, 143, 156), anchor="midtop", bold=True)

        pygame.draw.line(screen, (48, 53, 65), (rect.x + 84, 444), (rect.right - 84, 444), 1)
        tip_rect = pygame.Rect(0, 0, 552, 60)
        tip_rect.center = (S.SCREEN_W // 2, 478)
        self._panel(screen, tip_rect, (18, 21, 28, 190), (49, 55, 68), 8)
        pygame.draw.rect(screen, S.UI_ACCENT, (tip_rect.x + 11, tip_rect.y + 12, 3, 36),
                         border_radius=2)
        draw_text(screen, "İPUCU", 10, (tip_rect.x + 24, tip_rect.y + 10),
                  S.UI_ACCENT, bold=True)
        tip = self.menu_tips[int(t / 7) % len(self.menu_tips)]
        draw_text(screen, tip, 13, (tip_rect.x + 24, tip_rect.y + 27),
                  (183, 188, 199), bold=False)

        pulse = 0.5 + 0.5 * math.sin(t * 3.2)
        col = (247, 199, 64) if pulse > 0.25 else (210, 170, 66)
        draw_text(screen, "ENTER  /  BOŞLUK  —  OYUNA BAŞLA", 20,
                  (S.SCREEN_W // 2, rect.bottom - 58), col, anchor="midtop", bold=True)
        draw_text(screen, "ESC — ÇIKIŞ", 12, (S.SCREEN_W // 2, rect.bottom - 25),
                  (121, 126, 139), anchor="midtop", bold=True)

    def _control_row(self, screen, x, y, key, desc):
        font = get_font(11, True)
        w = font.size(key)[0] + 18
        chip = pygame.Rect(x, y, w, 24)
        pygame.draw.rect(screen, (30, 34, 43), chip, border_radius=5)
        pygame.draw.rect(screen, (72, 78, 92), chip, 1, border_radius=5)
        draw_text(screen, key, 11, chip.center, S.UI_TEXT, anchor="center", bold=True, shadow=False)
        draw_text(screen, desc, 13, (x + w + 12, y + 4), (174, 179, 190), bold=False)

    def draw_pause(self, screen, game):
        screen.blit(self.overlay_pause, (0, 0))
        rect = pygame.Rect(0, 0, 560, 390)
        rect.center = (S.SCREEN_W // 2, S.SCREEN_H // 2)
        self._panel(screen, rect, (12, 14, 20, 240), (70, 76, 90), 16)
        draw_text(screen, "DURAKLATILDI", 38, (rect.centerx, rect.y + 36), S.UI_TEXT,
                  anchor="midtop", bold=True)
        draw_text(screen, "Şehir seni bekliyor.", 13, (rect.centerx, rect.y + 88),
                  (142, 148, 160), anchor="midtop")
        rows = [
            ("WASD", "Hareket / sürüş"),
            ("FARE + SOL TIK", "Nişan al ve ateş et"),
            ("E", "Araç al / in"),
            ("R", "Şarjör değiştir"),
            ("1 2 3", "Silah seç"),
            ("M", "Sesi aç / kapat"),
        ]
        y = rect.y + 130
        for i, (key, desc) in enumerate(rows):
            self._control_row(screen, rect.x + 80, y + i * 32, key, desc)
        draw_text(screen, "ESC — DEVAM ET", 16, (rect.centerx - 110, rect.bottom - 48),
                  S.UI_ACCENT, anchor="center", bold=True)
        draw_text(screen, "Q — ANA MENÜ", 16, (rect.centerx + 110, rect.bottom - 48),
                  (160, 165, 176), anchor="center", bold=True)

    def draw_death(self, screen, game):
        screen.blit(self.overlay_death, (0, 0))
        rect = pygame.Rect(0, 0, 620, 400)
        rect.center = (S.SCREEN_W // 2, S.SCREEN_H // 2)
        self._panel(screen, rect, (20, 10, 12, 238), (105, 42, 44), 16)
        draw_text(screen, "ÖLDÜN", 78, (rect.centerx + 3, rect.y + 33), (20, 5, 7),
                  anchor="midtop", bold=True)
        draw_text(screen, "ÖLDÜN", 78, (rect.centerx, rect.y + 28), (214, 62, 58),
                  anchor="midtop", bold=True)
        draw_text(screen, "Sokaklar acımasızdır.", 14, (rect.centerx, rect.y + 126),
                  (182, 154, 154), anchor="midtop")
        y = rect.y + 174
        draw_text(screen, f"PARA  ${format_money(game.player.money)}", 15,
                  (rect.centerx - 160, y), (221, 224, 216), bold=True)
        draw_text(screen, f"ÖLDÜRME  {game.player.kills}", 15,
                  (rect.centerx + 160, y), (221, 224, 216), anchor="topright", bold=True)
        draw_text(screen, f"SÜRE  {fmt_time(game.play_time)}", 15,
                  (rect.centerx, y + 32), (163, 169, 180), anchor="midtop", bold=True)
        draw_text(screen, "SON ARANMA", 10, (rect.centerx, y + 68), S.UI_DIM,
                  anchor="midtop", bold=True)
        active = int(math.ceil(game.player.wanted - 0.001)) if game.player.wanted > 0.03 else 0
        for i in range(5):
            cx = rect.centerx - 72 + i * 36
            if i < active:
                draw_star(screen, cx, y + 99, 11, 4.8, S.UI_ACCENT)
            else:
                draw_star(screen, cx, y + 99, 11, 4.8, (70, 73, 84), width=2)
        draw_text(screen, "R — YENİDEN BAŞLA", 19, (rect.centerx, rect.bottom - 78),
                  S.UI_ACCENT, anchor="midtop", bold=True)
        draw_text(screen, "Q — ANA MENÜ", 12, (rect.centerx, rect.bottom - 39),
                  (151, 155, 167), anchor="midtop", bold=True)


# ===========================================================================
# MODUL: game
# ===========================================================================

"""Oyun döngüsü ve tüm sistemlerin birbirine baglanmasi."""
import math
import os
import random

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
from pygame.math import Vector2



COP_SPEC = {
    "damage": 9, "delay": 0.9, "spread": 0.04, "speed": 1320,
    "range": 900, "pellets": 1, "tracer": (255, 190, 150), "shake": 0.0,
}
KEYPAD_DIGITS = {getattr(pygame, f"K_KP{i}"): str(i) for i in range(10)}


class InputState:
    def __init__(self):
        self.move = Vector2()
        self.aim_world = Vector2()
        self.fire = False
        self.handbrake = False
        self.throttle = 0.0
        self.steer = 0.0
        self.mouse = (S.SCREEN_W // 2, S.SCREEN_H // 2)


class Game:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        pygame.display.set_caption(S.TITLE)
        self.screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))
        self.clock = pygame.time.Clock()
        pygame.mouse.set_visible(True)
        self.audio = Audio()
        self.hud = Hud()
        self.running = True
        self.state = "menu"
        self.state_time = 0.0
        self.play_time = 0.0
        self.debug = False
        self.god_mode = False
        self.cheat_buffer = ""
        self._cheat_prev_weapon = None
        self.mouse_screen = (S.SCREEN_W // 2, S.SCREEN_H // 2)
        self.input = InputState()
        self.override_input = None
        self.wanted_flash = 0.0
        self.shake_amt = 0.0
        self.flash_amt = 0.0
        self.hint = ""
        self.hint_timer = 0.0
        self.cam = Vector2()
        self.menu_dirty = False
        self.nearest_car = None
        self.rng = random.Random()

        self.city = City(self.rng.randint(1, 999999))
        self.new_game(regenerate=False)
        self.state = "menu"
        self.menu_dirty = False
        self.sync_mouse()

    # ------------------------------------------------------------------ kurulum
    def new_game(self, regenerate=False):
        if regenerate or not hasattr(self, "city"):
            self.city = City(self.rng.randint(1, 999999))
        self.player = Player(self.city.player_spawn.copy())
        self.cars = []
        self.npcs = []
        self.bullets = []
        self.particles = []
        self.corpses = []
        self.texts = []
        self.pickups = []
        self.play_time = 0.0
        self.state_time = 0.0
        self.wanted_flash = 0.0
        self.shake_amt = 0.0
        self.flash_amt = 0.0
        self.hint = ""
        self.hint_timer = 0.0
        self.cop_spawn_cd = 2.0
        self.ped_spawn_cd = 4.0
        self.pickup_spawn_cd = 20.0
        self.traffic_spawn_cd = 24.0
        self.override_input = None
        self.nearest_car = None
        self._create_cars()
        self._create_peds(32)
        self._create_pickups()
        self.cam = self.player.position - Vector2(S.SCREEN_W / 2, S.SCREEN_H / 2)
        self._clamp_cam()
        self.nearest_car = self._find_nearest_car()

    def _random_car_look(self, rng):
        kind = rng.choices(["sedan", "taxi", "sport", "van"], [5, 2, 2, 2])[0]
        color = rng.choice(S.CAR_COLORS)
        if kind == "taxi":
            color = (218, 184, 61)
        return kind, color

    def _cars_overlap(self, pos, dist=100):
        for car in self.cars:
            if (car.pos - pos).length() < dist:
                return True
        return False

    def _create_cars(self):
        rng = random.Random(self.city.seed ^ 0x51A7)
        # Otopark araçları
        for pos, angle in self.city.parking_spots:
            if rng.random() > 0.55:
                continue
            kind, color = self._random_car_look(rng)
            if self.city.is_free(pos, 22) and not self._cars_overlap(pos, 92):
                self.cars.append(Car(pos, angle, kind, color))
        # Kaldırım kenarına park etmiş araçlar
        curb_count = 0
        for br in self.city.block_rects:
            if curb_count >= 13:
                break
            if rng.random() > 0.3:
                continue
            side = rng.choice(("top", "bottom", "left", "right"))
            if side == "top":
                pos = Vector2(rng.uniform(br.x + 80, br.right - 80), br.y - 32)
                angle = rng.choice((0.0, math.pi))
            elif side == "bottom":
                pos = Vector2(rng.uniform(br.x + 80, br.right - 80), br.bottom + 32)
                angle = rng.choice((0.0, math.pi))
            elif side == "left":
                pos = Vector2(br.x - 32, rng.uniform(br.y + 80, br.bottom - 80))
                angle = rng.choice((math.pi / 2, -math.pi / 2))
            else:
                pos = Vector2(br.right + 32, rng.uniform(br.y + 80, br.bottom - 80))
                angle = rng.choice((math.pi / 2, -math.pi / 2))
            if self.city.tile_at_pos(pos.x, pos.y) != S.ROAD:
                continue
            if (pos - self.player.pos).length() < 105:
                continue
            if self.city.is_free(pos, 26) and not self._cars_overlap(pos, 110):
                kind, color = self._random_car_look(rng)
                self.cars.append(Car(pos, angle, kind, color))
                curb_count += 1
        # Trafik
        for _ in range(9):
            for _try in range(20):
                pos = self.city.random_road_point(rng)
                if (pos - self.player.pos).length() < 320:
                    continue
                kind, color = self._random_car_look(rng)
                car = Car(pos, 0, kind, color, traffic=True)
                car.setup_traffic(self.city, rng)
                if self.city.is_free(car.pos, 30) and not self._cars_overlap(car.pos, 150):
                    self.cars.append(car)
                    break
        # Oyuncunun yakınına kullanılabilir bir araç koy.
        # Önce yolu tercih et: park yerinde doğan araç trafiğe takılmasın.
        close_exists = any((c.pos - self.player.pos).length() < 118 for c in self.cars)
        if not close_exists:
            placed = False
            for prefer_road in (True, False):
                if placed:
                    break
                for dist in (92, 116, 142, 170, 195):
                    if placed:
                        break
                    for k in range(24):
                        a = k / 24 * math.tau + 0.2
                        p = self.player.pos + Vector2(math.cos(a), math.sin(a)) * dist
                        if p.x < 80 or p.y < 80 or p.x > S.WORLD_W - 80 or p.y > S.WORLD_H - 80:
                            continue
                        tile = self.city.tile_at_pos(p.x, p.y)
                        if prefer_road and tile != S.ROAD:
                            continue
                        if not prefer_road and tile not in (S.ROAD, S.LOT):
                            continue
                        if not self.city.is_free(p, 30) or self._cars_overlap(p, 115):
                            continue
                        angle = self.city.road_angle_at(p, rng)
                        fwd = Vector2(math.cos(angle), math.sin(angle))
                        # Aracın önünde en az 90 px boşluk olsun.
                        ahead = p + fwd * 95
                        if not self.city.is_free(ahead, 26):
                            continue
                        if any((c.pos - ahead).length() < 80 for c in self.cars):
                            continue
                        self.cars.append(Car(p, angle, "sedan", (183, 59, 52)))
                        placed = True
                        break

    def _create_peds(self, count):
        rng = random.Random(self.city.seed ^ 0x2C0F)
        for _ in range(count):
            pos = self.city.random_spawn_away(self.player.pos, 230, 2200, rng)
            self.npcs.append(NPC(pos, "ped", rng))

    def _create_pickups(self):
        rng = random.Random(self.city.seed ^ 0x77AB)
        kinds = ["health", "armor", "ammo", "cash", "health", "cash", "ammo", "cash"]
        for kind in kinds:
            pos = self.city.random_spawn_away(self.player.pos, 220, 1400, rng)
            amount = rng.randint(15, 45) if kind == "cash" else 0
            self.pickups.append(Pickup(pos, kind, amount))
        # İlk yardım çantası başlangıca yakın olsun
        for _ in range(20):
            p = self.player.pos + random_unit(rng) * rng.uniform(300, 600)
            if 0 < p.x < S.WORLD_W and 0 < p.y < S.WORLD_H and self.city.is_free(p, 12):
                self.pickups.append(Pickup(p, "health", 0))
                break

    def _find_nearest_car(self):
        if self.player.dead or self.player.car is not None:
            return None
        best = None
        best_d = 118.0
        for car in self.cars:
            if not car.alive:
                continue
            d = (car.pos - self.player.pos).length()
            if d < best_d:
                best_d = d
                best = car
        return best

    # ------------------------------------------------------------------ input
    def gather_input(self):
        if self.override_input is not None:
            self.input = self.override_input
            self.mouse_screen = self.override_input.mouse
            return self.override_input
        keys = pygame.key.get_pressed()
        inp = InputState()
        left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        up = keys[pygame.K_w] or keys[pygame.K_UP]
        down = keys[pygame.K_s] or keys[pygame.K_DOWN]
        inp.move = Vector2((1 if right else 0) - (1 if left else 0),
                           (1 if down else 0) - (1 if up else 0))
        inp.throttle = (1.0 if up else 0.0) - (1.0 if down else 0.0)
        inp.steer = (1.0 if right else 0.0) - (1.0 if left else 0.0)
        inp.handbrake = keys[pygame.K_SPACE]
        inp.fire = pygame.mouse.get_pressed()[0]
        self.mouse_screen = pygame.mouse.get_pos()
        inp.mouse = self.mouse_screen
        inp.aim_world = Vector2(self.mouse_screen) + self.cam
        self.input = inp
        return inp

    def _update_aim(self, inp):
        anchor = self.player.position
        aim = inp.aim_world - anchor
        if aim.length_squared() > 4:
            self.player.angle = math.atan2(aim.y, aim.x)

    # --------------------------------------------------------------- sifreler
    def _track_god_code(self, event):
        mods = getattr(event, "mod", 0)
        if mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT | pygame.KMOD_META):
            self.cheat_buffer = ""
            return
        ch = getattr(event, "unicode", "")
        if ch and ch.isdigit():
            digit = ch[-1]
        elif pygame.K_0 <= event.key <= pygame.K_9:
            digit = chr(event.key)
        elif event.key in KEYPAD_DIGITS:
            digit = KEYPAD_DIGITS[event.key]
        else:
            self.cheat_buffer = ""
            return
        if not self.cheat_buffer:
            self._cheat_prev_weapon = self.player.weapon
        self.cheat_buffer = (self.cheat_buffer + digit)[-4:]
        if self.cheat_buffer == "8828":
            self.cheat_buffer = ""
            self._toggle_god_mode()

    def _toggle_god_mode(self):
        self.god_mode = not self.god_mode
        p = self.player
        p.reload_timer = 0.0
        if self.god_mode:
            for name, spec in S.WEAPONS.items():
                p.mag[name] = spec["mag"]
                p.reserve[name] = max(p.reserve[name], spec["mag"] * 4)
            if self._cheat_prev_weapon in S.WEAPONS:
                p.weapon = self._cheat_prev_weapon
            self.show_hint("GOD MODE AÇIK: HASAR VE MERMİ SINIRSIZ", 3.0)
            self.audio.play("wanted", 0.6)
        else:
            self.show_hint("GOD MODE KAPALI", 1.8)
            self.audio.play("empty", 0.4)

    # ------------------------------------------------------------------ döngü
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._track_god_code(event)
                if event.key == pygame.K_m:
                    self.audio.toggle_mute()
                    self.show_hint("SES KAPALI" if self.audio.muted else "SES AÇIK", 1.1)
                elif self.state == "menu":
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                        self.start_game()
                    elif event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_F3:
                        self.debug = not self.debug
                elif self.state == "play":
                    self._handle_play_key(event)
                elif self.state == "paused":
                    if event.key == pygame.K_ESCAPE:
                        self.state = "play"
                        self.sync_mouse()
                    elif event.key == pygame.K_q:
                        self.go_menu()
                    elif event.key == pygame.K_F3:
                        self.debug = not self.debug
                elif self.state == "dead":
                    if event.key == pygame.K_r:
                        self.restart()
                    elif event.key == pygame.K_q:
                        self.go_menu()
                    elif event.key == pygame.K_ESCAPE:
                        self.go_menu()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if self.state == "menu" and event.button == 1:
                    self.start_game()
                elif self.state == "play":
                    if event.button == 4 or event.button == 5:
                        self._cycle_weapon(1 if event.button == 4 else -1)
            elif event.type == pygame.MOUSEWHEEL:
                if self.state == "play":
                    self._cycle_weapon(1 if event.y < 0 else -1)

    def _handle_play_key(self, event):
        if event.key == pygame.K_ESCAPE:
            self.state = "paused"
            self.sync_mouse()
        elif event.key == pygame.K_e:
            self.interact_vehicle()
        elif event.key == pygame.K_r:
            self.player.start_reload(self)
        elif event.key == pygame.K_1:
            self.player.switch_weapon(0, self)
        elif event.key == pygame.K_2:
            self.player.switch_weapon(1, self)
        elif event.key == pygame.K_3:
            self.player.switch_weapon(2, self)
        elif event.key == pygame.K_F3:
            self.debug = not self.debug

    def _cycle_weapon(self, step):
        try:
            idx = S.WEAPON_ORDER.index(self.player.weapon)
        except ValueError:
            idx = 0
        self.player.switch_weapon((idx + step) % len(S.WEAPON_ORDER), self)

    def start_game(self):
        if self.menu_dirty:
            self.new_game(regenerate=True)
        self.menu_dirty = False
        self.state = "play"
        self.play_time = 0.0
        self.state_time = 0.0
        self.nearest_car = self._find_nearest_car()
        self.show_hint("Sokaklar senin. İyi eğlenceler!", 2.4)
        self.sync_mouse()

    def restart(self):
        self.new_game(regenerate=True)
        self.state = "play"
        self.play_time = 0.0
        self.menu_dirty = False
        self.show_hint("Yeni bir gün, yeni bir kaos.", 2.0)
        self.sync_mouse()

    def go_menu(self):
        self.state = "menu"
        self.menu_dirty = True
        self.state_time = 0.0
        self.override_input = None
        self.sync_mouse()

    def sync_mouse(self):
        pygame.mouse.set_visible(self.state != "play")

    # ------------------------------------------------------------- etkileşim
    def interact_vehicle(self):
        if self.player.car is not None:
            self.exit_car()
            return
        car = self._find_nearest_car()
        if car is None:
            self.show_hint("Yakında araç yok", 1.1)
            return
        self.player.car = car
        car.controlled = True
        car.traffic = False
        car.brake = False
        self.player.pos = car.pos.copy()
        self.nearest_car = None
        self.audio.play("door", 0.7)
        self.show_hint(f"{car.spec['label'].upper()}  •  E ile in", 1.8)

    def _find_exit_pos(self, car):
        candidates = []
        for side in (-1, 1):
            for forward_off in (-0.12, 0.06, 0.2):
                p = (car.pos + car.right * side * (car.height * 0.5 + 22)
                     + car.forward * car.width * forward_off)
                candidates.append(p)
        for p in candidates:
            if not self.city.is_free(p, 12):
                continue
            blocked = any(c is not car and c.alive and c.overlaps_circle(p, 11)
                          for c in self.cars)
            if not blocked:
                return p
        return None

    def exit_car(self):
        car = self.player.car
        if car is None:
            return
        if car.speed > 330:
            self.show_hint("Araç çok hızlı — yavaşla!", 1.2)
            return
        pos = self._find_exit_pos(car)
        if pos is None:
            self.show_hint("Kapı bloke!", 1.2)
            return
        car.controlled = False
        car.brake = True
        car.traffic = False
        car.vel *= 0.22
        self.player.car = None
        self.player.pos = pos
        self.player.angle = car.angle
        self.player.invuln = 0.35
        self.player.knock = Vector2()
        self.audio.play("door", 0.6)
        self.nearest_car = car

    def _collide_player_cars(self):
        p = self.player
        for car in self.cars:
            if not car.alive or car is p.car:
                continue
            push = car.push_out_circle(p.pos, 10)
            if push is not None:
                p.pos += push
        self.city.resolve_circle(p.pos, 11)

    # ------------------------------------------------------------------ update
    def update(self, dt):
        self.state_time += dt
        self.play_time += dt
        inp = self.gather_input()
        self.hint_timer = max(0.0, self.hint_timer - dt)
        if self.hint_timer <= 0:
            self.hint = ""
        self.wanted_flash = max(0.0, self.wanted_flash - dt * 1.8)
        self.shake_amt *= math.exp(-8.5 * dt)
        if self.shake_amt < 0.08:
            self.shake_amt = 0.0
        self.flash_amt = max(0.0, self.flash_amt - dt * 3.4)

        p = self.player
        self._update_aim(inp)
        p.update_timers(dt, self)

        if p.car is not None:
            car = p.car
            car.drive(dt, self, inp.throttle, inp.steer, inp.handbrake)
        else:
            p.move_on_foot(dt, self, inp.move)
            self._collide_player_cars()

        if inp.fire and not p.dead:
            p.try_shoot(self, inp.aim_world)

        for car in list(self.cars):
            if car is p.car:
                continue
            if car.alive:
                car.update(dt, self)
            else:
                car.dead_timer += dt
                if car.dead_timer < 9 and random.random() < dt * 2.0:
                    self.spawn_car_smoke(car.pos + random_unit() * 20, car.dead_timer < 3)
        self.resolve_car_collisions()
        self.cars = [c for c in self.cars if c.alive or c.dead_timer < 55]

        for npc in list(self.npcs):
            if npc.alive:
                npc.update(dt, self)
        self.npcs = [n for n in self.npcs if n.alive and not n.remove]

        for b in self.bullets:
            b.update(dt, self)
        self.bullets = [b for b in self.bullets if b.alive]

        for item in self.pickups:
            item.update(dt)
            if p.car is None and not p.dead:
                if (item.pos - p.pos).length_squared() < 26 * 26:
                    item.alive = False
                    self._collect_pickup(item)
        self.pickups = [i for i in self.pickups if i.alive]

        self.particles = [pt for pt in self.particles if pt.update(dt)]
        self.texts = [t for t in self.texts if t.update(dt)]
        self.corpses = [c for c in self.corpses if c.update(dt)]

        self._update_spawns(dt)
        self._update_camera(dt)
        self.nearest_car = self._find_nearest_car()

        if p.dead and self.state != "dead":
            self.on_player_died()

    def update_dead(self, dt):
        self.state_time += dt
        self.shake_amt *= math.exp(-8.5 * dt)
        self.flash_amt = max(0.0, self.flash_amt - dt * 3.4)
        self.particles = [pt for pt in self.particles if pt.update(dt)]
        self.texts = [t for t in self.texts if t.update(dt)]
        self.corpses = [c for c in self.corpses if c.update(dt)]

    def _update_camera(self, dt):
        p = self.player
        focus = p.position.copy()
        if p.car is not None:
            focus += p.car.forward * min(p.car.speed * 0.22, 70)
        aim = self.input.aim_world - focus
        aim.x = clamp(aim.x * 0.13, -85, 85)
        aim.y = clamp(aim.y * 0.13, -55, 55)
        target = focus - Vector2(S.SCREEN_W / 2, S.SCREEN_H / 2) + aim
        target.x = clamp(target.x, 0, S.WORLD_W - S.SCREEN_W)
        target.y = clamp(target.y, 0, S.WORLD_H - S.SCREEN_H)
        t = 1.0 - math.exp(-7.5 * dt)
        self.cam += (target - self.cam) * t
        self._clamp_cam()

    def _clamp_cam(self):
        self.cam.x = clamp(self.cam.x, 0, S.WORLD_W - S.SCREEN_W)
        self.cam.y = clamp(self.cam.y, 0, S.WORLD_H - S.SCREEN_H)

    def _update_spawns(self, dt):
        p = self.player
        if p.crime_timer > 0:
            p.crime_timer -= dt
        elif p.wanted > 0:
            p.wanted = max(0.0, p.wanted - dt * 0.07)

        active_cops = sum(1 for n in self.npcs if n.kind == "cop" and n.alive)
        if p.wanted >= 0.7 and not p.dead:
            target_cops = min(8, int(math.ceil(p.wanted * 1.6)))
            self.cop_spawn_cd -= dt
            if active_cops < target_cops and self.cop_spawn_cd <= 0:
                if active_cops == 0:
                    self.show_hint("POLİSLER PEŞİNDE!", 2.2)
                self._spawn_cop()
                self.cop_spawn_cd = max(1.2, 3.4 - p.wanted * 0.35)
        else:
            self.cop_spawn_cd = max(self.cop_spawn_cd, 1.0)

        active_peds = sum(1 for n in self.npcs if n.kind == "ped" and n.alive)
        self.ped_spawn_cd -= dt
        if active_peds < 27 and self.ped_spawn_cd <= 0:
            pos = self.city.random_spawn_away(p.position, 750, 2400, self.rng)
            self.npcs.append(NPC(pos, "ped", self.rng))
            active_peds += 1
            self.ped_spawn_cd = 2.5

        self.pickup_spawn_cd -= dt
        if self.pickup_spawn_cd <= 0 and len(self.pickups) < 12:
            kind = self.rng.choices(["health", "armor", "ammo", "cash"], [2, 2, 3, 4])[0]
            pos = self.city.random_spawn_away(p.position, 320, 1200, self.rng)
            amount = self.rng.randint(12, 38) if kind == "cash" else 0
            self.pickups.append(Pickup(pos, kind, amount))
            self.pickup_spawn_cd = self.rng.uniform(17, 24)

        traffic = sum(1 for c in self.cars if c.traffic and c.alive)
        self.traffic_spawn_cd -= dt
        if traffic < 7 and self.traffic_spawn_cd <= 0:
            for _ in range(12):
                pos = self.city.random_road_point(self.rng)
                if (pos - p.position).length() < 500:
                    continue
                if self._cars_overlap(pos, 130):
                    continue
                kind, color = self._random_car_look(self.rng)
                car = Car(pos, 0, kind, color, traffic=True)
                car.setup_traffic(self.city, self.rng)
                if self._cars_overlap(car.pos, 120):
                    continue
                self.cars.append(car)
                break
            self.traffic_spawn_cd = self.rng.uniform(20, 30)

    def _spawn_cop(self):
        pos = self.city.random_spawn_away(self.player.position, 820, 1800, self.rng)
        cop = NPC(pos, "cop", self.rng)
        self.npcs.append(cop)
        self.audio.play("siren", 0.5, pos, self.player.position, 2400)

    def resolve_car_collisions(self):
        alive = [c for c in self.cars if c.alive]
        for i in range(len(alive)):
            a = alive[i]
            for j in range(i + 1, len(alive)):
                b = alive[j]
                if not a.alive:
                    break
                if not b.alive:
                    continue
                delta = b.pos - a.pos
                if delta.length_squared() > (a.width + b.width + 30) ** 2:
                    continue
                total_push = Vector2()
                damage = 0.0
                forward_a = a.forward
                forward_b = b.forward
                for oa in (-a.width * 0.32, 0.0, a.width * 0.32):
                    pa = a.pos + forward_a * oa
                    for ob in (-b.width * 0.32, 0.0, b.width * 0.32):
                        pb = b.pos + forward_b * ob
                        d = pb - pa
                        r = a.height * 0.46 + b.height * 0.46
                        d2 = d.length_squared()
                        if 0.0001 < d2 < r * r:
                            dist = math.sqrt(d2)
                            n = d / dist
                            pen = r - dist
                            mass_sum = a.spec["mass"] + b.spec["mass"]
                            push_a = pen * (b.spec["mass"] / mass_sum) * 0.75
                            push_b = pen * (a.spec["mass"] / mass_sum) * 0.75
                            a.pos -= n * push_a
                            b.pos += n * push_b
                            total_push += n * pen
                            rel = (a.vel - b.vel).dot(n)
                            if rel > 80:
                                damage = max(damage, rel * 0.045)
                if total_push.length_squared() > 0.01:
                    n = total_push.normalize()
                    va = a.vel.dot(n)
                    if va > 0:
                        a.vel -= n * va * 0.3
                    vb = b.vel.dot(n)
                    if vb < 0:
                        b.vel -= n * vb * 0.3
                    a._resolve_body(self.city)
                    b._resolve_body(self.city)
                    if damage > 3 and a.impact_cd <= 0 and b.impact_cd <= 0:
                        a.hurt(damage, self)
                        b.hurt(damage, self)
                        a.impact_cd = b.impact_cd = 0.45
                        mid = (a.pos + b.pos) * 0.5
                        self.spawn_sparks(mid, (b.vel - a.vel), 7)
                        if self.player.car in (a, b):
                            self.shake(9)
                            self.audio.play("crash", 0.7)
                        elif (mid - self.player.position).length() < 900:
                            self.audio.play("crash", 0.45, mid, self.player.position, 1600)

    def _collect_pickup(self, item):
        p = self.player
        if item.kind == "health":
            p.heal(35)
            self.show_hint("CAN +35", 1.0)
            self.audio.play("health", 0.7)
            self.texts.append(FloatingText(p.pos + Vector2(0, -20), "+35 CAN", (93, 226, 128)))
        elif item.kind == "armor":
            p.armor = min(100.0, p.armor + 50)
            self.show_hint("ZIRH +50", 1.0)
            self.audio.play("pickup", 0.7)
            self.texts.append(FloatingText(p.pos + Vector2(0, -20), "+50 ZIRH", (105, 163, 245)))
        elif item.kind == "ammo":
            spec = p.weapon_spec
            gained = spec["mag"] * 2
            p.reserve[p.weapon] += gained
            self.show_hint(f"{spec['name']} CEPHANESİ +{gained}", 1.2)
            self.audio.play("pickup", 0.65)
            self.texts.append(FloatingText(p.pos + Vector2(0, -20), f"+{gained} CEPHANE", (243, 202, 91)))
        elif item.kind == "cash":
            p.money += item.amount
            self.audio.play("pickup", 0.6)
            self.texts.append(FloatingText(p.pos + Vector2(0, -20), f"+${item.amount}",
                                           (99, 224, 135)))

    def show_hint(self, text, duration=1.5):
        self.hint = text
        self.hint_timer = duration

    def shake(self, amount):
        self.shake_amt = min(34.0, max(self.shake_amt, amount))

    # ---------------------------------------------------------------- efektler
    def _add_particle(self, particle):
        if len(self.particles) < S.MAX_PARTICLES:
            self.particles.append(particle)

    def spawn_blood(self, pos, direction, count=6, decal=True, big=False):
        d = Vector2(direction)
        if d.length_squared() < 0.001:
            d = Vector2(1, 0)
        d = d.normalize()
        for _ in range(count):
            vel = d * random.uniform(50, 230) + random_unit() * random.uniform(20, 120)
            self._add_particle(Particle(pos, vel, random.uniform(0.28, 0.75),
                                        random.uniform(2.0, 4.3), S.BLOOD,
                                        kind="blood", drag=2.8))
        if decal:
            n = 4 if big else 2
            for _ in range(n):
                p = Vector2(pos) + random_unit() * random.uniform(2, 16 if big else 9)
                x = int(clamp(p.x, 2, S.WORLD_W - 3))
                y = int(clamp(p.y, 2, S.WORLD_H - 3))
                if self.city.is_solid_pos(x, y):
                    continue
                pygame.draw.circle(self.city.surface, S.BLOOD_DARK,
                                   (x, y), random.randint(2, 6 if big else 4))
                if big and random.random() < 0.6:
                    pygame.draw.ellipse(self.city.surface, (69, 12, 17),
                                        (x - 11, y - 5, 22, 10))

    def spawn_sparks(self, pos, direction, count=5):
        d = Vector2(direction)
        if d.length_squared() > 0.1:
            d = d.normalize()
        else:
            d = Vector2(1, 0)
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(60, 260)
            vel = Vector2(math.cos(angle), math.sin(angle)) * speed + d * random.uniform(20, 110)
            self._add_particle(Particle(pos, vel, random.uniform(0.12, 0.36),
                                        random.uniform(1.5, 3.2),
                                        random.choice([(255, 209, 110), (255, 160, 71), (255, 240, 200)]),
                                        kind="spark", drag=3.5, gravity=190))

    def spawn_smoke(self, pos, count=1, dark=False):
        for _ in range(count):
            col = (92, 94, 101) if dark else (132, 134, 141)
            self._add_particle(Particle(
                Vector2(pos) + random_unit() * 5,
                random_unit() * random.uniform(8, 38) + Vector2(0, -12),
                random.uniform(0.55, 1.15), random.uniform(5, 11), col,
                kind="smoke", drag=1.4, grow=7.0))

    def spawn_car_smoke(self, pos, burning=False):
        self.spawn_smoke(pos, 1, dark=not burning)
        if burning and random.random() < 0.8:
            self._add_particle(Particle(
                Vector2(pos) + random_unit() * 8,
                Vector2(random.uniform(-20, 20), random.uniform(-45, -12)),
                random.uniform(0.25, 0.6), random.uniform(4, 8),
                random.choice([(255, 155, 55), (239, 91, 36)]),
                kind="fire", drag=0.8))

    def spawn_muzzle_flash(self, pos, angle, scale=1.0):
        d = Vector2(math.cos(angle), math.sin(angle))
        for _ in range(3):
            self._add_particle(Particle(
                Vector2(pos), d * random.uniform(30, 110) + random_unit() * 25,
                random.uniform(0.035, 0.085), random.uniform(3, 7) * scale,
                random.choice([(255, 239, 184), (255, 205, 91), (255, 167, 65)]),
                kind="fire", drag=2.0))
        self._add_particle(Particle(pos, d * 30, 0.06, 9 * scale,
                                    (255, 242, 190), kind="fire", drag=0))

    def spawn_casing(self, pos, angle):
        d = Vector2(math.cos(angle), math.sin(angle))
        perp = Vector2(-d.y, d.x)
        vel = perp * random.uniform(80, 170) + d * random.uniform(-20, 30)
        self._add_particle(Particle(pos, vel, random.uniform(0.35, 0.75),
                                    2.2, (221, 180, 76), kind="casing", drag=2.0))

    def spawn_explosion(self, pos):
        p = Vector2(pos)
        for _ in range(16):
            d = random_unit()
            self._add_particle(Particle(
                p + d * random.uniform(4, 28), d * random.uniform(30, 160) + Vector2(0, -25),
                random.uniform(0.65, 1.35), random.uniform(4, 12),
                (72, 72, 78), kind="smoke", drag=1.3, grow=16))
        for _ in range(38):
            d = random_unit()
            self._add_particle(Particle(
                p + d * random.uniform(2, 22), d * random.uniform(70, 360),
                random.uniform(0.34, 1.0), random.uniform(5, 15),
                random.choice([(255, 219, 125), (255, 156, 57), (238, 86, 34)]),
                kind="fire", drag=2.2, grow=8))
        for size, life in ((26, 0.16), (16, 0.12), (9, 0.1)):
            self._add_particle(Particle(p, (0, 0), life, size, (255, 246, 214),
                                        kind="flash", drag=0))
        for _ in range(20):
            d = random_unit()
            self._add_particle(Particle(
                p, d * random.uniform(140, 420), random.uniform(0.3, 0.8),
                random.uniform(1.5, 3.5),
                random.choice([(255, 223, 134), (255, 160, 70)]),
                kind="spark", drag=2.4, gravity=260))
        self._add_particle(Particle(p, (0, 0), 0.55, 68, (255, 156, 61), kind="ring", drag=0))
        self._add_particle(Particle(p, (0, 0), 0.8, 92, (102, 102, 106), kind="ring", drag=0))
        # Kalıcı is ve leke
        for _ in range(10):
            q = p + random_unit() * random.uniform(12, 55)
            pygame.draw.circle(self.city.surface, (30, 30, 33),
                               (int(clamp(q.x, 2, S.WORLD_W - 2)),
                                int(clamp(q.y, 2, S.WORLD_H - 2))),
                               random.randint(6, 23))
        pygame.draw.circle(self.city.surface, (22, 22, 24),
                           (int(clamp(p.x, 2, S.WORLD_W - 2)),
                            int(clamp(p.y, 2, S.WORLD_H - 2))), 40)

    # ------------------------------------------------------------------ silah
    def _player_muzzle_origin(self, player, angle):
        d = Vector2(math.cos(angle), math.sin(angle))
        if player.car is not None:
            car = player.car
            side = 1 if d.dot(car.right) >= 0 else -1
            return car.pos + car.right * side * (car.height * 0.5 + 3) + d * car.width * 0.05
        perp = Vector2(-d.y, d.x)
        return player.pos + d * 24 + perp * 3

    def player_fired(self, player, target, spec):
        target = Vector2(target)
        facing = target - player.position
        aim_angle = math.atan2(facing.y, facing.x) if facing.length_squared() > 1.0 else player.angle
        origin = self._player_muzzle_origin(player, aim_angle)
        # Namludan hedefe dogrudan ates: yakin mesafede paralaks kaymasi olmaz.
        to_target = target - origin
        angle = math.atan2(to_target.y, to_target.x) if to_target.length_squared() > 4.0 else aim_angle
        for i in range(spec["pellets"]):
            # Ilk mermi her zaman nisangahin tam uzerine gider.
            a = angle if i == 0 else angle + random.uniform(-spec["spread"], spec["spread"])
            self.bullets.append(Bullet(origin, a, spec, "player"))
        if len(self.bullets) > S.MAX_BULLETS:
            del self.bullets[:-S.MAX_BULLETS]
        scale = 0.8 if player.car is not None else (1.35 if spec["pellets"] > 1 else 1.0)
        self.spawn_muzzle_flash(origin, angle, scale)
        self.spawn_casing(origin, angle)
        self.audio.play(spec["sound"], 0.8, origin, player.position, 2500)
        self.shake(spec["shake"])
        player.add_wanted(0.105, self)
        for npc in self.npcs:
            if npc.kind == "ped" and npc.alive:
                if (npc.pos - origin).length() < spec["sound_radius"]:
                    npc.scare(origin)

    def spawn_cop_bullet(self, pos, angle, npc):
        self.bullets.append(Bullet(pos, angle, COP_SPEC, "cop"))
        if len(self.bullets) > S.MAX_BULLETS:
            del self.bullets[:-S.MAX_BULLETS]

    def bullet_hit_wall(self, point, bullet):
        self.spawn_sparks(point, -bullet.vel, 4)
        if random.random() < 0.7:
            x = int(clamp(point.x, 0, S.WORLD_W - 1))
            y = int(clamp(point.y, 0, S.WORLD_H - 1))
            pygame.draw.circle(self.city.surface, (28, 29, 33), (x, y), random.randint(1, 2))
        if (point - self.player.position).length() < 600:
            self.audio.play("hit", 0.16, point, self.player.position, 700)

    def bullet_hit_car(self, car, bullet, point):
        car.hurt(bullet.damage * 0.8, self)
        self.spawn_sparks(point, -bullet.vel, 5)
        if car.alive:
            self.audio.play("hit", 0.35, point, self.player.position, 1200)
        if car is self.player.car:
            self.shake(3.5)

    def on_car_crash(self, car, impact):
        self.spawn_sparks(car.pos + car.forward * car.width * 0.45, -car.forward * 60, 5)
        if car is self.player.car:
            self.shake(min(17.0, impact * 0.045))
            self.audio.play("crash", 0.75)
        else:
            self.audio.play("crash", 0.5, car.pos, self.player.position, 1200)

    # --------------------------------------------------------------- ölümler
    def on_person_hit_by_car(self, entity, car, speed):
        pos = entity.pos.copy()
        if entity is not self.player:
            self.spawn_blood(pos, car.vel, 4)
        self.audio.play("hit", 0.65, pos, self.player.position, 1300)
        if entity is self.player:
            self.shake(9)

    def on_npc_died(self, npc):
        self.corpses.append(Corpse(npc.pos.copy(), npc.angle, npc.skin, npc.body_dark, npc.kind))
        if len(self.corpses) > S.MAX_CORPSES:
            self.corpses = self.corpses[-S.MAX_CORPSES:]
        self.spawn_blood(npc.pos, random_unit(), 13, decal=True, big=True)
        if npc.by_player:
            self.player.kills += 1
            if npc.kind == "cop":
                self.player.add_wanted(0.85, self)
            else:
                self.player.add_wanted(0.32, self)
        if npc.kind == "cop":
            self.pickups.append(Pickup(npc.pos + random_unit() * 14, "ammo", 0))
        else:
            roll = random.random()
            if roll < 0.45:
                self.pickups.append(Pickup(npc.pos + random_unit() * 13, "cash",
                                           random.randint(8, 42)))
            elif roll < 0.62:
                self.pickups.append(Pickup(npc.pos + random_unit() * 13, "ammo", 0))
        self.audio.play("hit", 0.5, npc.pos, self.player.position, 900)

    def explode_car(self, car):
        if getattr(car, "exploded", False):
            return
        car.exploded = True
        car.alive = False
        car.health = 0
        car.dead_timer = 0.0
        car.controlled = False
        car.vel = Vector2()
        was_player_car = self.player.car is car
        if was_player_car:
            pos = self._find_exit_pos(car)
            if pos is None:
                pos = car.pos + car.right * (car.height * 0.5 + 28)
                self.city.resolve_circle(pos, 12)
            self.player.car = None
            self.player.pos = pos
            self.player.angle = car.angle
            self.player.invuln = 0.0
            self.player.knock = Vector2()
            self.show_hint("ARAÇ PATLADI!", 2.0)
        self.spawn_explosion(car.pos)
        self.shake(29)
        d_player = (car.pos - self.player.position).length()
        self.flash_amt = max(self.flash_amt, clamp(1.15 - d_player / 460.0, 0.0, 0.9))
        self.audio.play("explosion", 1.0, car.pos, self.player.position, 2800)

        for other in list(self.cars):
            if other is car or not other.alive:
                continue
            d = (other.pos - car.pos).length()
            if d < 190:
                other.hurt(22 + 68 * (1 - d / 190), self)
                push = other.pos - car.pos
                if push.length_squared() > 0.1:
                    other.vel += push.normalize() * 80
        for npc in list(self.npcs):
            if not npc.alive:
                continue
            d = (npc.pos - car.pos).length()
            if d < 190:
                npc.knock = unit(npc.pos - car.pos) * (200 * (1 - d / 190) + 50)
                npc.hurt(20 + 80 * (1 - d / 190), self, npc.pos - car.pos)
        p = self.player
        if not p.dead and p.car is None:
            d = (p.pos - car.pos).length()
            if d < 170:
                p.hurt(18 + 44 * (1 - d / 170), self, car.pos)

    def on_player_hurt(self, amount, source):
        self.shake(min(15.0, 4 + amount * 0.35))
        if random.random() < 0.6:
            self.spawn_blood(self.player.pos, random_unit(), 3)

    def on_player_died(self):
        p = self.player
        if p.dead:
            return
        p.dead = True
        pos = p.position.copy()
        if p.car is not None:
            p.car.controlled = False
            p.car.brake = True
            p.car.traffic = False
            p.car.vel *= 0.1
            p.pos = pos
            p.car = None
        self.corpses.append(Corpse(pos, p.angle, S.SKIN, S.PLAYER_BODY_DARK, "player"))
        self.spawn_blood(pos, random_unit(), 16, decal=True, big=True)
        self.audio.play("hit", 1.0)
        self.state = "dead"
        self.state_time = 0.0
        self.nearest_car = None
        self.sync_mouse()

    # ------------------------------------------------------------------ çizim
    def _render_camera(self):
        if self.state == "menu":
            t = pygame.time.get_ticks() / 1000.0
            cam = self.cam.copy()
            cam += Vector2(math.sin(t * 0.13) * 55, math.cos(t * 0.1) * 28)
        else:
            cam = self.cam.copy()
            if self.shake_amt > 0.1:
                cam += Vector2(random.uniform(-1, 1), random.uniform(-1, 1)) * self.shake_amt * 0.38
        cam.x = int(round(clamp(cam.x, 0, S.WORLD_W - S.SCREEN_W)))
        cam.y = int(round(clamp(cam.y, 0, S.WORLD_H - S.SCREEN_H)))
        return cam

    def draw(self):
        cam = self._render_camera()
        self.cam_render = cam
        self.screen.blit(self.city.surface, (0, 0),
                         area=pygame.Rect(int(cam.x), int(cam.y), S.SCREEN_W, S.SCREEN_H))

        for corpse in self.corpses:
            corpse.draw(self.screen, cam)
        for item in self.pickups:
            item.draw(self.screen, cam)

        drawables = []
        for car in self.cars:
            drawables.append((car.pos.y, 0, car))
        for npc in self.npcs:
            if npc.alive:
                drawables.append((npc.pos.y, 1, npc))
        p = self.player
        if not p.dead and p.car is None:
            drawables.append((p.pos.y, 2, p))
        drawables.sort(key=lambda item: (item[0], item[1]))
        for _, kind, obj in drawables:
            if kind == 0:
                obj.draw(self.screen, cam, player_car=(obj is p.car), aim_angle=p.angle)
            else:
                obj.draw(self.screen, cam)

        for bullet in self.bullets:
            bullet.draw(self.screen, cam)
        for particle in self.particles:
            particle.draw(self.screen, cam)
        for text in self.texts:
            text.draw(self.screen, cam)

        if self.state in ("play", "paused") and not p.dead and p.muzzle_timer > 0:
            origin = self._player_muzzle_origin(p, p.angle) - cam
            scale = 1.25 if p.weapon == "shotgun" else 0.85
            if p.car is not None:
                scale = 0.7
            art.draw_muzzle_flash(self.screen, origin, p.angle, scale)

        if self.state == "menu":
            self.hud.draw_menu(self.screen, self)
        elif self.state == "dead":
            self.hud.draw(self.screen, self)
            self.hud.draw_death(self.screen, self)
        elif self.state == "paused":
            self.hud.draw(self.screen, self)
            self.hud.draw_pause(self.screen, self)
        else:
            self.hud.draw(self.screen, self)

        if self.debug:
            fps = int(self.clock.get_fps())
            draw_text(self.screen, f"FPS {fps}  ARAÇ {len(self.cars)}  NPC {len(self.npcs)}  "
                                   f"MERMİ {len(self.bullets)}  PARÇACIK {len(self.particles)}",
                      12, (S.SCREEN_W // 2, S.SCREEN_H - 12), (210, 214, 220),
                      anchor="midbottom", bold=True)

    def run(self):
        while self.running:
            dt = min(0.033, self.clock.tick(S.FPS) / 1000.0)
            self.handle_events()
            if self.state == "play":
                self.update(dt)
            elif self.state == "dead":
                self.update_dead(dt)
            self.draw()
            pygame.display.flip()
        pygame.quit()


# ===========================================================================
# GIRIS NOKTASI
# ===========================================================================
def main():
    Game().run()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        print("\nOyun beklenmedik bir hata ile kapandi. Hata detaylari yukarida.")
        if sys.stdin and sys.stdin.isatty():
            input("Kapatmak icin ENTER'a basin...")
