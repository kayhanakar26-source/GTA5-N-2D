"""SOKAKLAR 2D - baslatici."""
import os
import sys

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from gta2d.game import Game


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
