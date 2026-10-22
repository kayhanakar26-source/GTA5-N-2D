"""Prosedurel 2D sehir: sokaklar, binalar, parklar ve çarpışma sistemi."""
import heapq
import math
import random

import pygame
from pygame.math import Vector2

from . import settings as S
from .utils import clamp, draw_star, get_glow


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
