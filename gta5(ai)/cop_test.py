"""Polis yapay zekasi / A* yaklasma testi (basliksiz)."""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from gta2d.game import Game, InputState


def main():
    game = Game()
    game.start_game()
    game.override_input = InputState()
    game.player.wanted = 5.0
    game.player.crime_timer = 999.0
    game.player.pos = game.city.player_spawn.copy()

    best = 9999.0
    for second in range(1, 21):
        for _ in range(60):
            game.update(1 / 60)
        cops = [n for n in game.npcs if n.kind == "cop" and n.alive]
        dists = sorted((n.pos - game.player.pos).length() for n in cops)
        near = dists[0] if dists else 9999.0
        best = min(best, near)
        los = sum(1 for n in cops if not game.city.line_blocked(n.pos, game.player.pos))
        print(f"t={second:2d}s  cops={len(cops)}  nearest={near:7.1f}  "
              f"los={los}  state={cops[0].state if cops else '-'}  best={best:.1f}")
        if best < 260:
            break
    print("best distance:", round(best, 1))
    pygame.quit()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
