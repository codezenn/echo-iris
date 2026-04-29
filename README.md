# Echo IRIS

A voice interactive AI agent on a mini-Jeep platform. Built for ECE 202 at
Colorado State University, Spring 2026. This is the end-of-semester archive
of the Group 35 deliverable.

**Status.** v1.0.0 released April 22, 2026. Demo day shipped in Room C105/107.
This repository is the permanent home for the codebase, hardware
documentation, 3D models, and setup guides. Future ECE 202 teams are
encouraged to fork, extend, and pick up where Group 35 left off.

## What IRIS Stands For

Intelligent Raspberry-Pi Imaging System.

| Letter | Meaning      |
|--------|--------------|
| I      | Intelligent  |
| R      | Raspberry Pi |
| I      | Imaging      |
| S      | System       |

## What It Does

Walk up to the Jeep, say "hello IRIS," and ask a question. IRIS hears you
through a wireless lavalier mic, recognizes your speech locally with Vosk,
checks your question against a fast path keyword dictionary for common demo
questions, and either responds instantly or hands the question to a local
qwen3.5:2b language model running through Ollama. Piper text to speech
voices the answer through a USB sound card. Throughout the entire session,
a Sony IMX500 AI camera runs YOLO11n object detection on its on-camera
neural processor and shows visitors a live preview window with bounding
boxes drawn over themselves and surrounding objects. Ask "what do you see"
and IRIS uses the qwen3.5:2b vision model to describe the scene in spoken
English. Switch personalities by saying "switch to pirate mode" or "go
playful." Everything runs locally on the Pi with no cloud dependency.

<img width="648" height="778" alt="Picture1" src="https://github.com/user-attachments/assets/3c6c4ea0-048e-467c-aaee-ffaf2ea344c3" />

## Team

| Member          | Role                                                   |
|-----------------|--------------------------------------------------------|
| Marc S.     | Project lead. AI agent, voice pipeline, software       |
| Giovanni G. | 3D design and printing. Speaker mount, Pi enclosure    |
| Obaid A. | Hardware. Jeep assembly, wiring, GPIO, power           |

## Key Features

Wake word listening with conversation mode. After IRIS responds, the agent
stays in listening mode for 12 seconds so visitors can ask follow up
questions without resaying the wake word.

Local speech recognition via Vosk at 48 kHz. No internet required.

Local language model. qwen3.5:2b runs through Ollama on the Pi. The system
prompt and DEMO_ANSWERS keyword fast path handle approximately 80 percent
of expected demo day questions in under 100 milliseconds. The LLM handles
everything else.

Concurrent live object detection. YOLO11n runs continuously on the Sony
IMX500 on camera neural processor at zero Pi CPU cost. Visitors see
themselves highlighted with bounding boxes throughout the conversation.

On demand LLM vision. Ask "what do you see" and the qwen3.5:2b vision model
captures a frame and describes the scene in spoken English.

Three personality modes. Professional, playful, and pirate. Switch by voice
command at any time.

Conversation scoreboard. IRIS counts how many people it has talked to and
will tell you the count when asked.

Easter eggs. A few hidden surprises for the curious. Try asking what grade
the project deserves.

Chat memory. Conversation history persists across turns within a session
and is logged to disk for review.

Live status indicators. Discrete LEDs driven by an Arduino Nano R4 over
serial show wake/listen/think/speak/error states.

## Architecture at a Glance

```
arecord (48 kHz) -> Vosk -> [easter eggs / personality switch / scoreboard
                            / vision trigger / DEMO_ANSWERS / LLM]
                         -> Piper TTS -> pygame.mixer -> USB speaker

Sony IMX500 NPU -> YOLO11n -> Picamera2 -> live preview window (concurrent)

Voice trigger ("what do you see") -> rpicam-still -> qwen3.5:2b vision -> spoken response
```

For the full architecture writeup, see [docs/architecture.md](docs/architecture.md).

## Hardware Highlights

The full bill of materials with funding sources and unit costs lives in
[hardware/BOM.md](hardware/BOM.md). The headline components are below.

| Component                | Notes                                          |
|--------------------------|------------------------------------------------|
| Raspberry Pi 5 (16GB)    | Production board, NVMe boot                    |
| Sony IMX500 AI Camera    | Runs YOLO11n on-camera at zero Pi CPU cost     |
| Wireless K1 Lavalier Mic | 48 kHz USB Composite Device                    |
| Waveshare USB Sound Card | Speaker output, USB PnP Device                 |
| Arduino Nano R4          | LED status indicators, pan/tilt servos via PWM |
| UPS HAT B                | Backup power, pogo pin connection (GPIO free)  |
| 512GB NVMe via M.2 HAT+  | Boot drive, primary storage                    |
| XGRAVITY Mini-Jeep       | Cars4Kids "Gravity" platform, white variant    |

For the chassis specifications and the spec source URL, see
[hardware/platform_specs.md](hardware/platform_specs.md).

## Software Stack

| Component             | Tool                                       |
|-----------------------|--------------------------------------------|
| Speech recognition    | Vosk (small English model, offline)        |
| Language model        | qwen3.5:2b via Ollama                      |
| Text to speech        | Piper, en_GB-vctk-medium voice             |
| Object detection      | YOLO11n on Sony IMX500 NPU                 |
| Vision (on demand)    | qwen3.5:2b vision via Ollama               |
| Camera interface      | Picamera2, rpicam-still                    |
| Audio playback        | pygame.mixer                               |
| Microcontroller       | Arduino Nano R4 (Renesas RA4M1)            |
| Operating system      | Raspberry Pi OS Bookworm 64-bit            |
| Language              | Python 3                                   |

For full upstream license information including the AGPL-3.0 implication
that flows from YOLO11, see [ATTRIBUTIONS.md](ATTRIBUTIONS.md).

## Two Build Paths

Echo IRIS supports two hardware targets with two separate scripts.

**8GB Pi build** (`echo_iris_8gb.py`). The original development Pi.
DEMO_MODE keyword only path with no LLM at runtime, used for fallback and
crash proof demonstrations. Setup steps in
[docs/setup_guide_8gb.md](docs/setup_guide_8gb.md).

**16GB Pi build** (`echo_iris_16gb.py`). The production demo day script.
Full multi module architecture with LLM, vision, personalities, scoreboard,
and easter eggs. Setup steps in
[docs/setup_guide_16gb.md](docs/setup_guide_16gb.md).

## Repository Structure

```
echo-iris/
├── software/
│   ├── echo_iris_8gb.py        # 8GB Pi entry point (DEMO_MODE keyword path)
│   ├── echo_iris_16gb.py       # 16GB Pi entry point (production)
│   ├── iris_detector.py        # IMX500 + YOLO11n live detection
│   ├── iris_monitor.py         # UPS and system monitor
│   ├── iris_rag.py             # Optional retrieval pipeline (runtime-disabled)
│   ├── iris_knowledge.md       # 26-chunk RAG knowledge base
│   ├── sound_manager.py        # Sound effects via pygame.mixer
│   ├── scoreboard.py           # Conversation counter
│   ├── personality_manager.py  # Professional / playful / pirate
│   ├── personalities.json      # Personality definitions
│   ├── chat_memory.py          # 16-turn sliding-window history
│   ├── easter_eggs.py          # Hidden interactions
│   ├── run.sh                  # Auto-restart wrapper
│   ├── requirements.txt        # Pinned Python dependencies
│   └── README.md               # Module index
├── hardware/
│   ├── BOM.md                  # Full bill of materials
│   ├── platform_specs.md       # Cars4Kids Gravity chassis
│   ├── wiring_diagrams/
│   └── assembly_photos/
├── 3d-models/
│   ├── prototypes/
│   ├── speaker_case_final.stl
│   ├── pi_enclosure.stl
│   ├── led_housing.stl
│   ├── camera_klammer.stl
│   ├── nano_clip.stl
│   └── README.md               # Print settings
├── docs/
│   ├── architecture.md
│   ├── demo_day_script.md
│   ├── setup_guide_8gb.md
│   ├── setup_guide_16gb.md
│   └── troubleshooting.md
├── README.md
├── LICENSE
├── ATTRIBUTIONS.md
├── CHANGELOG.md
├── CONTRIBUTING.md
└── .gitignore
```

## Getting Started

For a complete from scratch setup on a fresh Raspberry Pi, follow the setup
guide that matches your build target. The 8GB guide is the simpler path and
covers the demo mode only configuration. The 16GB guide covers the full
production stack including Ollama, the qwen3.5:2b model pull, the IMX500
firmware setup, the audio device verification routine, and the Arduino LED
bridge flashing.

[docs/setup_guide_8gb.md](docs/setup_guide_8gb.md)

[docs/setup_guide_16gb.md](docs/setup_guide_16gb.md)

## Quick Start (already configured)

```
cd ~/echo-iris/software
./run.sh
```

The `run.sh` wrapper auto restarts the agent after Ctrl+C. To run the
script directly without auto restart, use `python3 echo_iris_16gb.py` for
the production build or `python3 echo_iris_8gb.py` for the 8GB build.

IRIS will play a startup sound, speak a greeting, and begin listening for
its wake word.

## Documentation

[CHANGELOG.md](CHANGELOG.md). Full version history, what shipped, what was
deferred, and known issues.

[ATTRIBUTIONS.md](ATTRIBUTIONS.md). Upstream open source dependencies and
their licenses, including the AGPL 3.0 interaction from YOLO11.

[docs/architecture.md](docs/architecture.md). System architecture, module
walkthrough, design decisions, and future work invitations.

[docs/troubleshooting.md](docs/troubleshooting.md). Audio routing, vision
recovery, LLM latency, undervoltage diagnosis, Arduino cable traps.

[docs/demo_day_script.md](docs/demo_day_script.md). The actual moments from
demo day, including what failed and what saved the run.

[CONTRIBUTING.md](CONTRIBUTING.md). Guidance for future ECE 202 teams,
open source forkers, and anyone extending the codebase.

## Sister Project

A green Jeep variant runs voice-controlled motor drive on a separate 16GB
Pi using two Cytron MDD10A motor drivers. That code lives in a sibling
repository maintained by the green Jeep team.

## Future Development

This repository is designed to outlive the semester. Future teams might
take on any of the following.

Voice-announced YOLO detections. The detection runs continuously today but
IRIS does not narrate what it sees unless asked. Adding a "narration mode"
that periodically speaks new detections would close the loop.

V2V communication. The original proposal called for MQTT-based message
passing between the white IRIS Jeep and the green Jeep. Architecture is
documented but not built.

Autonomous driving. The combination of YOLO11n object detection, the
existing motor driver pattern from the green Jeep, and the voice control
layer is the foundation for an autonomous lane following or
obstacle avoidance demo.

Faster LLM. The current qwen3.5:2b takes 28 to 41 seconds for free form
questions. A text only model swap (gemma3:1b was researched but not
benchmarked) is the most likely speed improvement.

WS2812B addressable LED strip. The original plan called for an addressable
strip, which failed during installation the day before demo and was
replaced with discrete LEDs. Returning to addressable LEDs is straightforward.

RAG reenable. The `iris_rag.py` module is shipped but disabled at runtime
because of ChromaDB ARM64 import issues on Python 3.13. A future Python
version or a different vector store would unblock it.

Real time split screen display. A planned Pygame UI for the KYY 15.6 inch
monitor with scrolling conversation panel and live camera feed was not
built.

Pirate voice. Pirate mode currently uses the same Piper speaker as
professional and playful. A separate gravelly voice would land the bit.

Streaming Ollama cancel. Mid response interrupt would let visitors stop
IRIS when answers run long.

For the complete deferred work list, see [CHANGELOG.md](CHANGELOG.md).

## License

Echo IRIS source code is released under the MIT License. See [LICENSE](LICENSE)
for the full text.

One runtime dependency (Ultralytics YOLO11) is released under AGPL-3.0,
which has implications for downstream redistribution. See
[ATTRIBUTIONS.md](ATTRIBUTIONS.md) for the full explanation. Future ECE 202
teams and downstream forkers should read the attributions before
incorporating Echo IRIS into a proprietary product.

## Acknowledgments

Professor Olivera, ECE 202, Colorado State University. Steve Henry,
Engineer in Residence. Arjunbabu Vasantharaj, ECE 202 TA. Jackie at the
ECE department for purchasing coordination. The CSU Engineering I2P Lab
for 3D printer access. The green Jeep team for the cross collaboration on
voice controlled motor drive. The open source projects that made this
possible: Ollama, Vosk, Piper, Ultralytics, the Raspberry Pi Foundation,
and Sony for the IMX500.

ECE 202 | Colorado State University | Spring 2026
