#!/usr/bin/env python3
"""
Phase 2: Audio Resampling Test v4
Echo IRIS 16GB Pipeline

Uses sounddevice callback capture at the mic's native 48kHz.
Passes 48kHz directly to Vosk KaldiRecognizer, which handles
internal resampling via Kaldi's LinearResample.
No manual downsampling. Matches the official Vosk test_microphone.py pattern.

Usage: python3 test_resample_vosk.py
"""

import json
import sys
import queue

try:
    import sounddevice as sd
except ImportError:
    print("ERROR: sounddevice not installed. Run: pip install sounddevice --break-system-packages")
    sys.exit(1)

try:
    from vosk import Model, KaldiRecognizer
except ImportError:
    print("ERROR: vosk not installed. Run: pip install vosk --break-system-packages")
    sys.exit(1)

VOSK_MODEL_PATH = "/home/penrose/model"
BLOCK_SIZE = 8000  # frames per callback (matches official example)

q = queue.Queue()


def audio_callback(indata, frames, time, status):
    """Called by sounddevice for each audio block."""
    if status:
        print(f"Audio status: {status}", file=sys.stderr)
    q.put(bytes(indata))


def find_k1_mic():
    """Find the K1 wireless mic (USB Composite Device)."""
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if dev["max_input_channels"] > 0 and "Composite" in dev["name"]:
            return i, dev
    return None, None


def main():
    print("=" * 60)
    print("Echo IRIS Phase 2: Audio Test v4 (sounddevice + native rate)")
    print("=" * 60)

    # ── Find mic ───────────────────────────────────────────────────
    mic_id, mic_info = find_k1_mic()
    if mic_id is None:
        print("ERROR: K1 mic not found.")
        print("\nAvailable input devices:")
        for i, dev in enumerate(sd.query_devices()):
            if dev["max_input_channels"] > 0:
                print(f"  [{i}] {dev['name']} ({int(dev['default_samplerate'])} Hz)")
        sys.exit(1)

    samplerate = int(mic_info["default_samplerate"])
    print(f"Found K1 mic: index={mic_id}, name='{mic_info['name']}'")
    print(f"Native sample rate: {samplerate} Hz (passed directly to Vosk)")
    print(f"Block size: {BLOCK_SIZE} frames")

    # ── Load Vosk model ────────────────────────────────────────────
    print(f"\nLoading Vosk model from {VOSK_MODEL_PATH}...")
    try:
        model = Model(VOSK_MODEL_PATH)
    except Exception as e:
        print(f"ERROR loading Vosk model: {e}")
        sys.exit(1)

    rec = KaldiRecognizer(model, samplerate)
    rec.SetWords(True)
    print(f"Vosk recognizer initialized at {samplerate} Hz (internal resample to model rate).")

    # ── Stream and recognize ───────────────────────────────────────
    print("\nSpeak now (Ctrl+C to stop).\n")

    partial_prev = ""

    try:
        with sd.RawInputStream(
            samplerate=samplerate,
            blocksize=BLOCK_SIZE,
            device=mic_id,
            dtype="int16",
            channels=1,
            callback=audio_callback
        ):
            while True:
                data = q.get()

                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "")
                    if text:
                        print(f"[FINAL] {text}")
                    partial_prev = ""
                else:
                    partial = json.loads(rec.PartialResult())
                    ptext = partial.get("partial", "")
                    if ptext and ptext != partial_prev:
                        print(f"  (partial) {ptext}", end="\r")
                        partial_prev = ptext

    except KeyboardInterrupt:
        final = json.loads(rec.FinalResult())
        text = final.get("text", "")
        if text:
            print(f"[FINAL] {text}")
        print("\nDone. Audio test v4 complete.")


if __name__ == "__main__":
    main()
