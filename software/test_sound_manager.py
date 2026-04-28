#!/usr/bin/env python3
"""
Echo IRIS - SoundManager Test
Run on Pi to test all sounds or individual categories.

Usage:
    python3 test_sound_manager.py             # full audition with Piper announcements
    python3 test_sound_manager.py startup     # just startup
    python3 test_sound_manager.py ack         # just ack (random)
    python3 test_sound_manager.py thinking    # 15s thinking demo (hear 10s threshold)
    python3 test_sound_manager.py error       # both error sounds
    python3 test_sound_manager.py swoosh      # short reply swoosh
    python3 test_sound_manager.py easter      # both easter eggs
    python3 test_sound_manager.py timer       # full 35s timer demo (hear both thresholds)
"""

import sys
import time

# Add the software directory to path so we can import sound_manager
sys.path.insert(0, "/home/penrose/echo-iris/software")
from sound_manager import SoundManager


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode == "all":
        print("Full sound test with Piper announcements...")
        sm = SoundManager(play_startup=False)
        sm.test_all()
        sm.shutdown()
        return

    # For individual tests, suppress startup chime
    sm = SoundManager(play_startup=False)

    if mode == "startup":
        print("Playing startup...")
        sm.play_startup()

    elif mode == "ack":
        print("Playing 3 random ack sounds...")
        for i in range(3):
            sm.play_ack()
            time.sleep(3)

    elif mode == "thinking":
        print("Starting thinking timer. Tick-tock begins at 10s...")
        sm.start_thinking()
        time.sleep(15)
        elapsed = sm.stop_thinking()
        print(f"Stopped after {elapsed:.1f}s")

    elif mode == "error":
        print("Playing error sound 1...")
        sm.play_error()
        time.sleep(3)
        print("Playing error sound 2...")
        sm.play_error()
        time.sleep(3)

    elif mode == "swoosh":
        print("Playing swoosh...")
        sm.play_swoosh()
        time.sleep(2)

    elif mode == "easter":
        print("Playing engine rev (race easter egg)...")
        sm.play_easter_egg("race")
        time.sleep(1)
        print("Playing twenty one...")
        sm.play_easter_egg("21")
        time.sleep(1)

    elif mode == "timer":
        print("Full timer demo: tick-tock at 10s, muscle car at 30s.")
        print("Running for 35 seconds...")
        sm.start_thinking()
        start = time.monotonic()
        while time.monotonic() - start < 35:
            elapsed = time.monotonic() - start
            print(f"\r  {elapsed:.0f}s elapsed...", end="", flush=True)
            time.sleep(1)
        print()
        elapsed = sm.stop_thinking()
        print(f"Stopped after {elapsed:.1f}s")

    else:
        print(f"Unknown mode: {mode}")
        print("Options: all, startup, ack, thinking, error, swoosh, easter, timer")

    sm.shutdown()


if __name__ == "__main__":
    main()
