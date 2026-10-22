"""Gelistirme icin basliksiz goruntu testi."""
import math
import os
import sys
import traceback

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
from pygame.math import Vector2

from gta2d import settings as S
from gta2d.game import Game, InputState

OUT = os.path.join(os.environ.get("TEMP", "."), "opencode", "gta2d_shots")
os.makedirs(OUT, exist_ok=True)


def shot(game, name):
    game.draw()
    pygame.image.save(game.screen, os.path.join(OUT, name))
    print("saved", os.path.join(OUT, name))


def pick_drive_car(game):
    """Onunde bosluk olan, yol uzerindeki bir araci sec."""
    city = game.city

    def clear(car):
        if city.tile_at_pos(car.pos.x, car.pos.y) != S.ROAD:
            return False
        for d in (70, 130, 190):
            q = car.pos + car.forward * d
            if not city.is_free(q, 24):
                return False
            if any((c.pos - q).length() < 65 for c in game.cars
                   if c is not car and c.alive):
                return False
        return True

    candidates = sorted((c for c in game.cars if c.alive and clear(c)),
                        key=lambda c: (c.pos - game.player.pos).length())
    return candidates[0] if candidates else game._find_nearest_car()


def main():
    game = Game()
    print("state", game.state, "player", game.player.pos, "cars", len(game.cars),
          "npcs", len(game.npcs), "pickups", len(game.pickups))
    shot(game, "01_menu.png")
    game.start_game()

    inp = InputState()
    inp.mouse = (800, 360)
    game.override_input = inp
    inp.aim_world = game.player.pos + Vector2(300, 0)
    for i in range(90):
        inp.aim_world = game.player.pos + Vector2(300, 60)
        if i == 20:
            print("nearest car", game._find_nearest_car())
        game.update(1 / 60)
    shot(game, "02_walk.png")

    car = pick_drive_car(game)
    print("car enter", car)
    if car is not None:
        # Test icin temiz bir yol aracina gec.
        game.player.pos = car.pos.copy()
        game.interact_vehicle()
        inp.throttle = 1.0
        inp.steer = 0.0
        for i in range(120):
            inp.aim_world = game.player.position + Vector2(400, 0)
            game.update(1 / 60)
        print("speed after 2s", round(game.player.car.speed, 1) if game.player.car else None)
        inp.fire = True
        inp.steer = 0.55
        for i in range(60):
            inp.aim_world = game.player.position + Vector2(300, 200)
            game.update(1 / 60)
        inp.fire = False
        inp.throttle = 0.0
        inp.steer = 0.0
        shot(game, "03_car.png")
        print("car pos", game.player.position, "speed", game.player.car.speed if game.player.car else None)

        # ates testi (aractan inip)
        inp.throttle = -1.0
        inp.steer = 0.0
        for _ in range(24):
            game.update(1 / 60)
        inp.throttle = 0.0
        if game.player.car is not None:
            game.exit_car()
        if game.player.car is not None:
            test_car = game.player.car
            test_car.controlled = False
            game.player.car = None
            game.player.pos = test_car.pos + test_car.right * 44
            game.city.resolve_circle(game.player.pos, 11)
        print("on foot", game.player.car is None, "hp", int(game.player.health))
        game.player.weapon = "smg"
        game.player.mag["smg"] = 32
        inp.fire = True
        for i in range(30):
            inp.aim_world = game.player.pos + Vector2(240, 120)
            game.update(1 / 60)
        inp.fire = False
        shot(game, "04_shooting.png")

    # polis testi: A* polislerin yaklasmasi ve cok yakin ekran goruntusu
    game.player.health = 100.0
    game.player.armor = 60.0
    game.player.wanted = 5.0
    game.player.crime_timer = 999.0
    game.player.invuln = 999.0
    nearest = 9999.0
    cop_close = False
    for i in range(1500):
        cops = [n for n in game.npcs if n.kind == "cop" and n.alive]
        if cops:
            near_cop = min(cops, key=lambda n: (n.pos - game.player.pos).length())
            inp.aim_world = near_cop.pos.copy()
        else:
            inp.aim_world = game.player.pos + Vector2(200, 100)
        game.update(1 / 60)
        cops = [n for n in game.npcs if n.kind == "cop" and n.alive]
        if cops:
            nearest = min((n.pos - game.player.pos).length() for n in cops)
        if i % 60 == 59:
            los = sum(1 for n in cops if not game.city.line_blocked(n.pos, game.player.pos))
            print(f"polis {int((i + 1) / 60)}s  adet={len(cops)}  en_yakin={nearest:.0f}  los={los}")
        if i >= 90 and cops and nearest < 300:
            cop_close = True
            for _ in range(14):
                cops = [n for n in game.npcs if n.kind == "cop" and n.alive]
                if cops:
                    near_cop = min(cops, key=lambda n: (n.pos - game.player.pos).length())
                    inp.aim_world = near_cop.pos.copy()
                game.update(1 / 60)
            cops = [n for n in game.npcs if n.kind == "cop" and n.alive]
            if cops:
                nearest = min((n.pos - game.player.pos).length() for n in cops)
            break
    shot(game, "05_cops.png")
    print("cop close", cop_close, "nearest", round(nearest, 1),
          "cops", sum(1 for n in game.npcs if n.kind == "cop"),
          "cop_bullets", sum(1 for b in game.bullets if b.owner == "cop"))

    # yakin patlama testi: oyuncunun hemen yanindaki araci patlat
    game.player.invuln = 3.0
    game.player.wanted = 0.0
    game.player.crime_timer = 0.0
    game.npcs = [n for n in game.npcs if n.kind != "cop"]
    candidates = [c for c in game.cars if c.alive]
    if candidates:
        target = min(candidates, key=lambda c: (c.pos - game.player.pos).length())
        spot = None
        for dist in (150, 175, 200):
            for k in range(24):
                a = k / 24 * math.tau
                p = target.pos + Vector2(math.cos(a), math.sin(a)) * dist
                if not game.city.is_free(p, 14):
                    continue
                if any(c is not target and c.alive and (c.pos - p).length() < 65
                       for c in game.cars):
                    continue
                spot = p
                break
            if spot is not None:
                break
        if spot is not None:
            game.player.pos = spot
        game.cam = game.player.pos - Vector2(S.SCREEN_W / 2, S.SCREEN_H / 2)
        game._clamp_cam()
        print("explode", target.pos, "player", game.player.pos)
        game.explode_car(target)
        for _ in range(4):
            game.update(1 / 60)
        shot(game, "06_explosion.png")
        for _ in range(18):
            game.update(1 / 60)
        shot(game, "06b_smoke.png")

    # menu testi
    game.player.health = 0
    game.on_player_died()
    game.draw()
    pygame.image.save(game.screen, os.path.join(OUT, "07_dead.png"))
    print("saved", os.path.join(OUT, "07_dead.png"))
    game.go_menu()
    shot(game, "08_menu_again.png")
    print("player dead", game.player.dead, "state", game.state)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
