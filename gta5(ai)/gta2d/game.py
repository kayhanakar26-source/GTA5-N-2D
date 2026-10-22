"""Oyun döngüsü ve tüm sistemlerin birbirine baglanmasi."""
import math
import os
import random

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
from pygame.math import Vector2

from . import settings as S
from . import art
from .audio import Audio
from .city import City
from .entities import (Bullet, Car, Corpse, FloatingText, NPC, Particle,
                       Pickup, Player)
from .hud import Hud
from .utils import clamp, get_font, random_unit, unit


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



