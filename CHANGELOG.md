# Changelog

All notable changes to Echo IRIS are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-22

First public release. This is the demo-day version of Echo IRIS as it ran at
the ECE 202 final demonstration in Room C105/107 at Colorado State University.
The system is built around a Raspberry Pi 5 (16GB) inside a white XGRAVITY
mini-Jeep platform and runs a fully local voice agent with vision, scoreboard,
personality switching, easter eggs, and a multi-module Python architecture.

### Added

The voice agent script `echo_iris_16gb.py` v3.4 became the production entry
point for demo day. It auto-detects audio cards via `arecord -l` and `aplay -l`
on startup, captures audio through an `arecord` subprocess pipe at 48000 Hz,
feeds the stream to a Vosk recognizer that handles 48 kHz to 16 kHz
resampling internally via Kaldi LinearResample, dispatches recognized text
through a check chain of easter eggs, personality switches, scoreboard
triggers, vision triggers, and a `DEMO_ANSWERS` keyword fast path before
falling back to the LLM, then routes Piper TTS output through `pygame.mixer`
to avoid ALSA contention with the simultaneous sound effect player.

The supporting helper modules shipped in their final form: `sound_manager.py`
for startup, acknowledgment, easter egg, error, and reply indicator sounds
plus thinking sounds the team chose to disable by raising thresholds to 999;
`scoreboard.py` for tracking demo-day conversation counts with trigger
phrases like how many people have you talked to; `personality_manager.py`
for switching between professional, playful, and pirate modes defined in
`personalities.json`; `chat_memory.py` for sliding-window conversation
history of 16 turns persisted to disk via atomic write; `easter_eggs.py`
for hidden grade-response, nine-plus-ten, and other surprise interactions;
`iris_detector.py` for Sony IMX500 on-camera object detection with
irregular-plurals support; `iris_rag.py` for an optional retrieval pipeline
that is intentionally disabled at runtime via a try/except wrapper; and
`run.sh` as a bash wrapper that auto-restarts the agent after Ctrl+C.

Six v3.4 fixes shipped that made demo day work. The DEMO display path
gained a `wrap_print("IRIS", demo_answer)` call so visitors saw the answer
text in the terminal alongside hearing it. Greeting keywords changed from
`how are you` to `how are you doing` and `how are you today` to stop the
question how are you able to see from incorrectly matching the greeting
entry. The creators DEMO answer keyword list expanded with `who created`
and `created you`. The Ollama timeout went from 45 to 60 seconds to absorb
cold-start latency. SDL audio environment variables now set before the
pygame import so the mixer binds to the correct ALSA card. Conversation
mode reworked so the loop stays in listening state after `process_input`
returns, letting visitors ask follow-up questions without re-saying the
wake word for 12 seconds.

DEMO_ANSWERS keyword fast path covers approximately 80 to 90 percent of
expected demo-day questions in under 100 milliseconds, bypassing the LLM
entirely for the most common interactions. The eight categories at release
are who_are_you, software, ai_models, hardware, goals, creators,
capabilities, and greeting.

Live YOLO11n object detection runs concurrently with the voice agent
throughout the entire session. The Sony IMX500 AI camera executes the
YOLO11n nano model on its on-camera neural processor and returns labeled
bounding boxes to the host. `iris_detector.py` consumes those detections
through Picamera2 and presents a live preview window with boxes drawn over
the camera feed, so visitors see themselves and surrounding objects
highlighted in real time while chatting with IRIS. The detection runs at
zero Pi CPU cost since inference happens on the camera silicon. This is
distinct from the LLM-based vision path (qwen3.5:2b describing what it
sees), which is triggered only on phrases like "what do you see" and uses
`rpicam-still` for one-shot frame capture. The two vision paths are
complementary: continuous YOLO bounding boxes for visual feedback,
triggered LLM scene description for spoken responses.

A green Jeep cross-collaboration shipped a separate 16GB Pi build that adds
voice-controlled motor drive using two Cytron MDD10A motor drivers. Code
for that variant is documented in the architecture notes but lives in a
sibling repository.

### Changed

The Arducam B0283 PCA9685 servo controller failed I2C detection on both
Pi I2C buses and on the Arduino Nano R4 I2C bus during pre-demo
diagnostics. Servo control switched to direct PWM on Nano R4 pins D9 (pan)
and D10 (tilt). This is the supported control path going forward, not a
workaround.

The WS2812B addressable LED strip failed during installation the day
before demo. The team replaced it with discrete LEDs on a breadboard
driven by the Arduino over the same single-character serial protocol
(W/L/T/S/E states at 115200 baud over /dev/ttyACM0). The LED bridge
sketch on the Nano R4 was updated accordingly.

`sound_manager.py` AUDIODEV environment variable changed from `plughw:2,0`
to `plughw:3,0` to match the post-reboot card ordering observed on demo day.
The thinking sound thresholds (tick-tock at 10 seconds, muscle car at
30 seconds) were raised to 999 in the same file, effectively disabling
both sounds during LLM response wait. The acknowledgment beep alone
provides sufficient feedback that IRIS heard the question.

`personality_manager.py` gained a `parrot` alias in all four `SWITCH_PATTERNS`
regex alternatives, mapping to `pirate` inside `check_switch()` after the
`lower()` call. Vosk frequently transcribes the spoken word pirate as
parrot, and adding the alias prevents the switch from silently failing.

`easter_eggs.py` `NINE_TEN_PATTERN` regex updated to include `posts` as an
alternative to `plus`, since Vosk consistently mishears nine plus ten as
nine posts ten. The patched regex is `r"(?:nine|9)\s*(?:plus|posts|\+)\s*(?:ten|10)"`.

`MODEL_NAME` set to `qwen3.5:2b-q4_K_M` specifically. The Q4_K_M quantization
was kept for known-working stability over a researched but never-benchmarked
gemma3:1b swap.

`MIC_DEVICE` set to `hw:2,0` and `SPEAKER_OUTPUT` set to `plughw:3,0` after
the demo-day audio card swap. The K1 wireless lavalier microphone was
detected as a USB Composite Device on card 2 (capture only, 48 kHz), and
the Waveshare USB Audio speaker was detected as a USB PnP Device on card 3.
The card numbers can swap unpredictably on reboot, and the troubleshooting
guide documents the verification steps to take after every boot.

`num_ctx` reduced to 2048 and `num_predict` capped at 100 tokens. Voice
responses target 3 to 4 sentences (50 to 75 words). The cap hard-limits
LLM output regardless of system prompt instructions, holding response
time within an acceptable demo-day window.

A `sanitize()` defense-in-depth function strips non-ASCII from all LLM
and vision output before it reaches print or speak. Raspberry Pi OS
Bookworm sets the system locale to latin-1, and any em dash, smart quote,
or emoji in LLM output otherwise crashes the print loop. Sanitize is
applied inside `wrap_print`, `speak`, on the return value of
`query_ollama`, and on the return value of `capture_and_describe`.

### Removed

The legacy monolithic `echo_iris.py` v3.1 is no longer the entry point.
The 8GB build path uses `echo_iris_8gb.py` and the 16GB production build
uses `echo_iris_16gb.py`. All shared functionality has been extracted into
the helper modules listed in the Added section.

`iris_rag.py` runtime activation removed for demo day. The system prompt
plus DEMO_ANSWERS keyword coverage handled all expected questions without
needing the embedding-based retrieval pipeline. The module remains in the
repository, gated behind a try/except import guard, so future teams can
re-enable it after resolving its ChromaDB import dependency on Python 3.13
and ARM64.

The `iris_rag_cache.json` file is excluded from version control via
`.gitignore`. The cache contains 26 chunks of 768-dimensional embeddings
that should be regenerated per machine, not committed.

### Known Issues

LLM response time runs 28 to 41 seconds for 100-token capped responses on
the Pi 5. The qwen3.5:2b multimodal model generates at approximately 3.45
tokens per second and carries 1.38 GB of vision encoder overhead even on
text-only requests. DEMO_ANSWERS handles the common path, but free-form
LLM questions are slow. A text-only model swap (gemma3:1b was researched)
is the most likely speed improvement and is documented as future work in
`/docs/architecture.md`.

`rpicam-still` consecutive captures sometimes time out at 10 seconds. The
first capture in a session works reliably. Subsequent captures within the
same session occasionally fail with "Command timed out after 10 seconds."
Increasing the timeout, adding inter-capture delay, or using `--immediate`
not yet tested.

Vosk small model accuracy degrades at 3 to 6 feet from the wireless
lavalier mic. Documented mishearings include parrot for pirate, posts
for plus, owners were for what, and areas for iris. The personality
manager and easter eggs modules now include alias entries for the most
common substitutions. Demo-day mitigation is to clip the mic close to
the speaker.

Audio device card numbers can swap on reboot. The kernel enumerates USB
audio devices in unpredictable order. After every boot, the script's
MIC_DEVICE, SPEAKER_OUTPUT, and AUDIODEV (in both `echo_iris_16gb.py`
and `sound_manager.py`) need verification against `aplay -l` and
`arecord -l` output. A udev rule for persistent device naming is the
proper fix and is documented as future work.

Bookworm system locale defaults to latin-1 on the first-boot wizard.
The `sanitize()` function works around this at the application level,
but the proper fix (locale-gen and update-locale to en_US.UTF-8) was
not applied to the demo-day Pi.

`iris_rag.py` import fails on the production Pi due to ChromaDB
dependency issues on Python 3.13 / ARM64. The try/except wrapper handles
the failure gracefully, and RAG is intentionally disabled.

Mid-conversation sound effect playback can conflict with `pygame.mixer`
TTS output in rare cases. Startup sound conflict was resolved by routing
both Piper and SoundManager through a single mixer instance. Mid-conversation
remains an open edge case.

### Deferred Work

Several v3.5 checklist items did not ship to demo day. They are documented
honestly here and reframed as future-work invitations in `/docs/architecture.md`.

Claude API integration for online fallback when WiFi is available was
researched but not implemented. The dual offline/online conversation mode
remains a future improvement.

Gemma3:1b text-only model swap was researched but not benchmarked. This
is the most likely path to faster LLM response times.

Evdev keyboard hotkey for instant speech cancel was scoped but not built.
The current cancel path requires a Ctrl+C interrupt and full process
restart via `run.sh`.

Streaming Ollama cancel mid-generation was not implemented. The agent
waits for the full response before speaking. A streaming variant would
let users interrupt mid-response.

Pirate voice using a different Piper speaker ID was not implemented for
demo day. Pirate mode currently uses the same speaker 2 as professional
and playful modes, with personality coming entirely from the system prompt
and word choice.

WS2812B addressable LED strip integration was abandoned the day before
demo after the strip failed during installation. Discrete LEDs on a
breadboard driven by the Arduino were the demo-day workaround. Returning
to addressable LEDs is straightforward future work.

RAG re-enable on a future Python version where ChromaDB ARM64 wheels are
stable.

Real-time split-screen Pygame display for the KYY 15.6 inch monitor (left
panel scrolling conversation, right panel camera feed, bottom status bar)
was planned but not built.

48 kHz to 16 kHz Vosk downsampling work item is settled, not deferred.
Kaldi LinearResample inside the Vosk recognizer handles the conversion
internally when the recognizer is initialized at 48000 Hz. Listed here
only to clarify that earlier project notes calling this an outstanding
item are out of date.

[1.0.0]: https://github.com/codezenn/echo-iris/releases/tag/v1.0.0
