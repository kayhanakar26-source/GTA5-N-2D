"""Oyuncu, araçlar, NPC'ler, mermiler ve efektler."""
import math
import random

import pygame
from pygame.math import Vector2

from . import settings as S
from . import art
from .utils import (angle_diff, clamp, get_font, get_glow, random_unit,
                    rotate, unit)


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
