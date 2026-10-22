"""Prosedurel sprite ve arayüz görselleri."""
import math

import pygame
from pygame.math import Vector2

from . import settings as S
from .utils import clamp, get_font

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
