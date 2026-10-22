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
