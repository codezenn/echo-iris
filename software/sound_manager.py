"""
Echo IRIS - SoundManager
Handles all sound effect playback through pygame.mixer.
Routes audio to the Waveshare USB sound card. Card number is detected at runtime; defaults to plughw:3,0 but verify with `aplay -l` before deployment since USB enumeration order can swap on reboot.

Usage:
    from sound_manager import SoundManager
    sm = SoundManager()       # initializes pygame.mixer, plays startup chime
    sm.play_ack()             # random ack variant
    sm.start_thinking()       # starts 10s/30s timer system
    sm.stop_thinking()        # stops all thinking/long-response sounds
    sm.play_error()           # alternating error sounds
    sm.play_swoosh()          # short reply flourish
    sm.play_easter_egg("21")  # twenty_one.wav
    sm.play_easter_egg("race")  # engine_rev.wav
    sm.test_all()             # audition every sound in sequence
"""

import os
import random
import threading
import time

# Route SDL audio to Waveshare before importing pygame
os.environ["SDL_AUDIODRIVER"] = "alsa"
os.environ["AUDIODEV"] = "plughw:3,0"

import pygame

SOUNDS_DIR = os.path.expanduser("~/echo-iris/software/sounds")
SAMPLE_RATE = 22050


class SoundManager:
    def __init__(self, play_startup=True):
        pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1, buffer=2048)

        # Reserve channels: 0=ack, 1=thinking, 2=long_response, 3=effects/easter
        pygame.mixer.set_num_channels(4)
        self.ch_ack = pygame.mixer.Channel(0)
        self.ch_thinking = pygame.mixer.Channel(1)
        self.ch_long = pygame.mixer.Channel(2)
        self.ch_effects = pygame.mixer.Channel(3)

        # Load all sounds
        self.startup = self._load("startup", "keys_ignition.wav")
        self.ack_variants = [
            self._load("ack", "ack_short.wav"),
            self._load("ack", "ack_medium.wav"),
            self._load("ack", "ack_full.wav"),
        ]
        self.thinking = self._load("thinking", "tick_tock.wav")
        self.long_response = self._load("reply", "muscle_car.wav")
        self.swoosh = self._load("reply", "swoosh.wav")
        self.error_sounds = [
            self._load("error", "computer_error.wav"),
            self._load("error", "tires_squealing.wav"),
        ]
        self.easter_21 = self._load("easter", "twenty_one.wav")
        self.easter_race = self._load("easter", "engine_rev.wav")

        # State tracking
        self._error_index = 0
        self._thinking_timer = None
        self._thinking_active = False
        self._timer_lock = threading.Lock()

        if play_startup:
            self.play_startup()

    def _load(self, folder, filename):
        """Load a WAV file as a pygame.mixer.Sound object."""
        path = os.path.join(SOUNDS_DIR, folder, filename)
        if not os.path.exists(path):
            print(f"[SoundManager] WARNING: missing {path}")
            return None
        return pygame.mixer.Sound(path)

    def play_startup(self):
        """Play the startup chime. Blocks until complete."""
        if self.startup:
            self.ch_effects.play(self.startup)
            while self.ch_effects.get_busy():
                time.sleep(0.05)

    def play_ack(self):
        """Play a random ack variant. Non-blocking."""
        sound = random.choice(self.ack_variants)
        if sound:
            self.ch_ack.play(sound)

    def start_thinking(self):
        """Start the thinking timer system.
        At 10s: tick_tock starts looping.
        At 30s: tick_tock stops, muscle_car plays once, tick_tock resumes.
        Call stop_thinking() when the LLM response arrives.
        """
        with self._timer_lock:
            self._thinking_active = True
            self._thinking_start = time.monotonic()
            self._thinking_timer = threading.Thread(
                target=self._thinking_loop, daemon=True
            )
            self._thinking_timer.start()

    def _thinking_loop(self):
        """Background thread managing thinking sound thresholds."""
        thinking_started = False
        long_played = False

        while True:
            with self._timer_lock:
                if not self._thinking_active:
                    break
                elapsed = time.monotonic() - self._thinking_start

            if elapsed >= 999 and not long_played:
                # Stop tick_tock, play muscle_car once, resume tick_tock
                self.ch_thinking.stop()
                if self.long_response:
                    self.ch_long.play(self.long_response)
                    # Wait for muscle_car to finish before resuming tick_tock
                    while self.ch_long.get_busy():
                        with self._timer_lock:
                            if not self._thinking_active:
                                self.ch_long.stop()
                                return
                        time.sleep(0.05)
                # Resume tick_tock loop
                with self._timer_lock:
                    if not self._thinking_active:
                        return
                if self.thinking:
                    self.ch_thinking.play(self.thinking, loops=-1)
                long_played = True

            elif elapsed >= 999 and not thinking_started:
                if self.thinking:
                    self.ch_thinking.play(self.thinking, loops=-1)
                thinking_started = True

            time.sleep(0.1)

    def stop_thinking(self):
        """Stop all thinking and long-response sounds. Returns elapsed seconds."""
        with self._timer_lock:
            self._thinking_active = False
            elapsed = time.monotonic() - self._thinking_start if hasattr(self, "_thinking_start") else 0
        self.ch_thinking.stop()
        self.ch_long.stop()
        return elapsed

    def play_swoosh(self):
        """Play the short-reply swoosh. Non-blocking."""
        if self.swoosh:
            self.ch_effects.play(self.swoosh)

    def play_error(self):
        """Play an alternating error sound. Non-blocking."""
        sound = self.error_sounds[self._error_index]
        if sound:
            self.ch_effects.play(sound)
        self._error_index = (self._error_index + 1) % len(self.error_sounds)

    def play_easter_egg(self, egg_type):
        """Play an easter egg sound. Blocks until complete.
        egg_type: '21' for twenty_one, 'race' for engine_rev
        """
        sound = None
        if egg_type == "21":
            sound = self.easter_21
        elif egg_type == "race":
            sound = self.easter_race
        if sound:
            self.ch_effects.play(sound)
            while self.ch_effects.get_busy():
                time.sleep(0.05)

    def play_reply_indicator(self, llm_elapsed):
        """Call after LLM response arrives. Plays swoosh if fast (<5s)."""
        if llm_elapsed < 5:
            self.play_swoosh()

    def test_all(self):
        """Audition every sound with labels. For debugging and demo setup."""
        import subprocess

        PIPER_BIN = os.path.expanduser("~/iris_voice/piper/piper")
        PIPER_MODEL = os.path.expanduser("~/iris_voice/en_GB-vctk-medium.onnx")
        SPEAKER_OUTPUT = "plughw:3,0"

        def announce(text):
            piper_cmd = [
                PIPER_BIN, "--model", PIPER_MODEL,
                "--speaker", "2", "--output-raw",
            ]
            aplay_cmd = [
                "aplay", "-D", SPEAKER_OUTPUT,
                "-r", "22050", "-f", "S16_LE", "-c", "1", "-q",
            ]
            piper_proc = subprocess.Popen(
                piper_cmd, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            )
            aplay_proc = subprocess.Popen(
                aplay_cmd, stdin=piper_proc.stdout, stderr=subprocess.DEVNULL,
            )
            piper_proc.stdin.write(text.encode("utf-8"))
            piper_proc.stdin.close()
            aplay_proc.wait()
            piper_proc.wait()

        tests = [
            ("Startup sound", lambda: self._play_and_wait(self.startup, self.ch_effects)),
            ("Acknowledgment short", lambda: self._play_and_wait(self.ack_variants[0], self.ch_ack)),
            ("Acknowledgment medium", lambda: self._play_and_wait(self.ack_variants[1], self.ch_ack)),
            ("Acknowledgment full", lambda: self._play_and_wait(self.ack_variants[2], self.ch_ack)),
            ("Thinking tick tock", lambda: self._play_timed(self.thinking, self.ch_thinking, 4)),
            ("Long response muscle car", lambda: self._play_and_wait(self.long_response, self.ch_long)),
            ("Short reply swoosh", lambda: self._play_and_wait(self.swoosh, self.ch_effects)),
            ("Error computer", lambda: self._play_and_wait(self.error_sounds[0], self.ch_effects)),
            ("Error tires", lambda: self._play_and_wait(self.error_sounds[1], self.ch_effects)),
            ("Easter egg engine rev", lambda: self._play_and_wait(self.easter_race, self.ch_effects)),
            ("Easter egg twenty one", lambda: self._play_and_wait(self.easter_21, self.ch_effects)),
        ]

        for label, play_fn in tests:
            announce(label)
            time.sleep(0.3)
            play_fn()
            time.sleep(0.5)

        announce("Sound test complete.")

    def _play_and_wait(self, sound, channel):
        if sound:
            channel.play(sound)
            while channel.get_busy():
                time.sleep(0.05)

    def _play_timed(self, sound, channel, seconds):
        if sound:
            channel.play(sound, loops=-1)
            time.sleep(seconds)
            channel.stop()

    def shutdown(self):
        """Clean up pygame.mixer."""
        self.stop_thinking()
        pygame.mixer.quit()
