"""Oyun içi arayüz, minimap, menüler ve crosshair."""
import math

import pygame
from pygame.math import Vector2

from . import settings as S
from . import art
from .utils import (clamp, draw_bar, draw_star, draw_text, fmt_time,
                    format_money, get_font)


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
