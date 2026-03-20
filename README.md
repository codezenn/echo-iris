# Echo IRIS 
### Intelligent Raspberry-Pi Interactive System (IRIS)
**ECE 202 | Colorado State University | Spring 2026**

---

## Project Overview

Echo IRIS is an AI powered voice interactive agent built on a mini-Jeep platform. It is a functional extension of IRIS 1.0 (Intelligent Raspberry-Pi Imaging System), an existing ECE 202 platform designed for real time object detection.

This iteration introduces a full voice interaction layer allowing IRIS to listen for spoken prompts, process them locally on device, and respond audibly in real time using a custom embedded AI pipeline. The system is designed to operate autonomously on battery power during live demonstrations, with no dependency on external servers or internet connectivity.

Echo IRIS is intended to serve as a multi-semester platform. Future ECE 202 teams are encouraged to build on this repository, extend its capabilities, and contribute back to the codebase.

---

## What IRIS Stands For

| Letter | Meaning |
|--------|---------|
| I | Intelligent |
| R | Raspberry-Pi |
| I | Imaging |
| S | System |

---

## Team

| Member | Role |
|--------|------|
| Marc | Project Lead on AI agent, voice pipeline, software architecture |
| Giovanni | Lead on 3D Design & Printing speaker mount, Pi enclosure, LED housing |
| Obaid | Lead on Hardware Jeep and Pi assembly, wiring, GPIO, power integration |

---

## Key Features

- **Wake word detection**: IRIS listens passively and activates on a trigger phrase
- **On-device speech recognition**: powered by Vosk (no internet required)
- **Natural language responses**: keyword-matched response engine with contextual acknowledgments
- **Text-to-speech output**: Piper TTS with a British English voice model
- **Demo mode**: crash-proof, LLM-free mode optimized for live presentations
- **Real-time object detection**: Sony IMX500 AI camera with on-board neural processor
- **USB audio auto-detection**: automatically finds and configures USB audio devices at startup

---

## Hardware

| Component | Description | Cost |
|-----------|-------------|------|
| Raspberry Pi 5 (8GB) | Primary computing unit | — |
| Sony IMX500 AI Camera | On-board neural processor for object detection | $70.00 |
| Baseus 65W Power Bank | 20,000mAh PD 3.0 mobile power supply | $89.99 |
| UPS HAT (E) | Uninterruptible power supply for stable mobile operation | $32.99 |
| 18650 Batteries (2-pack) | Energy source for UPS HAT | $15.00 |
| KYY 15.6" Portable Monitor | Real-time display for bounding boxes and system diagnostics | $69.99 |
| Official RPi SSD + M.2 HAT+ | 256GB NVMe for fast model and OS storage | $89.95 |
| Raspberry Pi Active Cooler | Thermal management under heavy AI workloads | $7.69 |
| USB Microphone | Voice input for speech recognition | — |
| Mini-Jeep Platform | Base vehicle chassis | — |

**Estimated Total: ~$590**

---

## Software Stack

| Component | Tool |
|-----------|------|
| Speech Recognition | [Vosk](https://alphacephei.com/vosk/) (small model, offline) |
| Text-to-Speech | [Piper TTS](https://github.com/rhasspy/piper) — `en_GB-vctk-medium` |
| Object Detection | Sony IMX500 + custom model |
| Operating System | Raspberry Pi OS (64-bit) |
| Language | Python 3 |

---

## Repository Structure

```
/echo-iris
│
├── /software
│   ├── echo_iris.py              # Main voice agent script
│   ├── iris_monitor.py           # System/UPS monitor
│   ├── yolo_integration.py       # YOLO object detection + voice bridge
│   └── mqtt_client.py            # V2V MQTT communication (planned)
│
├── /hardware
│   ├── wiring_diagrams/          # GPIO pinouts, LED wiring, power layout
│   ├── BOM.md                    # Full bill of materials with links and costs
│   └── assembly_photos/          # Jeep assembly progress photos
│
├── /3d-models
│   ├── speaker_mount.stl
│   ├── pi_enclosure.stl
│   └── led_housing.stl
│
├── /docs
│   ├── setup_guide_8gb.md        # Full from-scratch install guide (8GB Pi 5)
│   ├── setup_guide_16gb.md       # Production Pi setup (in progress)
│   ├── demo_day_script.md        # Step-by-step demo flow for judges
│   └── troubleshooting.md        # Known issues and fixes
│
└── README.md
```

---

## Getting Started

For a complete from-scratch setup on a Raspberry Pi 5 (8GB), see [`docs/setup_guide_8gb.md`](docs/setup_guide_8gb.md).

### Quick Start (if already configured)

```bash
cd /home/penrose
python3 echo_iris.py
```

IRIS will speak a startup confirmation and begin listening for its wake word.

---

## Demo Video

> 🎬 *Demo video coming soon — to be recorded before Demo Day, April 2026.*

---

## Version History

| Version | Notes |
|---------|-------|
| v1.0 | Initial voice pipeline with wake word + Vosk + Piper |
| v2.4 | Audio architecture fix with stream stop/restart logic resolved |
| v3.1 | Demo mode added with crash-proof, LLM-free, 12 keyword categories |

---

## Future Development

This repository is designed to outlive the semester. Planned and aspirational features for future teams include:

- YOLO-based real time object detection with voice announcements
- V2V communication via MQTT between two IRIS vehicles
- Autonomous driving integration
- GitHub Pages public project site

---

## License

MIT License — see [`LICENSE`](LICENSE) for details.

---

*ECE 202 | Colorado State University | Spring 2026*
