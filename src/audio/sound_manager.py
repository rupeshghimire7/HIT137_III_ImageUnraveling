"""
sound_manager.py

SoundManager loads every .wav file in assets/sounds and plays them with
pygame.mixer: one looping background-music track plus short sound effects
that can overlap it.

Sound is optional. If pygame is not installed, or the computer has no
audio device (e.g. CI), every method quietly does nothing and the game
keeps working exactly as before.
"""

import os
from pathlib import Path

SOUNDS_DIR = Path(__file__).resolve().parents[2] / "assets" / "sounds"
MUSIC_FILE = "background_music.wav"
MUSIC_VOLUME = 0.35
EFFECT_VOLUME = 0.8


class SoundManager:
    """Plays background music and named sound effects (file name without
    the .wav extension, e.g. play("swap"))."""

    def __init__(self, sounds_dir=SOUNDS_DIR):
        self.sounds_dir = Path(sounds_dir)
        self.enabled = False
        self.muted = False
        self._effects = {}
        self._mixer = None

        try:
            os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
            import pygame

            pygame.mixer.init()
        except Exception as exc:  # no pygame or no audio device
            print(f"Sound disabled: {exc}")
            return

        self._mixer = pygame.mixer
        for path in sorted(self.sounds_dir.glob("*.wav")):
            if path.name == MUSIC_FILE:
                continue
            try:
                sound = pygame.mixer.Sound(str(path))
            except Exception as exc:
                print(f"Could not load sound {path.name}: {exc}")
                continue
            sound.set_volume(EFFECT_VOLUME)
            self._effects[path.stem] = sound
        self.enabled = True

    # ------------------------------------------------------------------ #
    # Sound effects
    # ------------------------------------------------------------------ #
    def play(self, name):
        """Play the effect `name` (e.g. "swap", "winner")."""
        if not self.enabled or self.muted:
            return
        sound = self._effects.get(name)
        if sound is not None:
            sound.play()

    # ------------------------------------------------------------------ #
    # Background music
    # ------------------------------------------------------------------ #
    def start_music(self):
        """Start (or restart) the background music, looping forever."""
        if not self.enabled or self.muted:
            return
        music = self.sounds_dir / MUSIC_FILE
        if not music.exists():
            return
        try:
            self._mixer.music.load(str(music))
            self._mixer.music.set_volume(MUSIC_VOLUME)
            self._mixer.music.play(loops=-1)
        except Exception as exc:
            print(f"Could not play background music: {exc}")

    def stop_music(self):
        if self.enabled:
            self._mixer.music.stop()

    def toggle_mute(self):
        """Turn all sound off/on. Returns True if now muted."""
        self.muted = not self.muted
        if self.enabled:
            if self.muted:
                self._mixer.music.pause()
                self._mixer.stop()
            else:
                self._mixer.music.unpause()
        return self.muted
