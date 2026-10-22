"""Kucuk, tamamen prosedurel ses motoru (harici dosya gerektirmez)."""
import array
import math
import random

import pygame

from .utils import clamp


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
