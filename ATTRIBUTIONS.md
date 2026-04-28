# Attributions

Echo IRIS is built on top of open source software. This file lists every
upstream component the production system depends on at runtime, the license
under which each component is released, and a brief note on how Echo IRIS
uses it. License information was verified against upstream sources at the
time of the v1.0.0 release.

The Echo IRIS source code in this repository is released under the MIT
License (see `LICENSE`). The attributions below cover dependencies, not the
project's own code.

Important license interaction. One of the runtime dependencies (Ultralytics
YOLO11) is released under AGPL-3.0. This affects how the combined system
may be redistributed. See the YOLO11 entry in the Vision and Object Detection
section below for the full explanation. Future ECE 202 teams and downstream
forkers should read that section before incorporating Echo IRIS into a
proprietary or commercial product.

## Language Model

**Qwen 3.5 2B** (`qwen3.5:2b` in the Ollama library)

License: Apache License 2.0
Upstream: Alibaba Cloud, distributed via Ollama at https://ollama.com/library/qwen3.5
Used as: primary conversational LLM and vision-language model. Loaded via the
Ollama HTTP API at `localhost:11434/api/chat`. Multimodal model, accepts text
and image input, 256K context window.

Note for Marc to verify before commit. The repo synthesis handoff specifies
the exact model tag as `qwen3.5:2b-q4_K_M` (Q4_K_M quantization variant).
The reconstructed v3.4 source in the 16GBPipelineFixes RepoContext shows
`MODEL_NAME = "qwen3.5:2b"` (no quantization suffix, default Q8_0 at 2.7 GB).
These two values do not reconcile. Confirm against the actual file at
`~/echo-iris/software/echo_iris_16gb.py` on the Pi and update this attribution
to match. The Apache 2.0 license applies to either variant.

## Speech Recognition

**Vosk** (Python bindings for the Kaldi-based Vosk API)

License: Apache License 2.0
Upstream: Alpha Cephei Inc., https://github.com/alphacep/vosk-api
Used as: offline speech recognition. The KaldiRecognizer class is initialized
at 48000 Hz and handles 48 kHz to 16 kHz resampling internally via Kaldi
LinearResample.

**vosk-model-small-en-us-0.15** (English acoustic model, 40 MB)

License: Apache License 2.0 (per the Vosk model release page)
Upstream: https://alphacephei.com/vosk/models
Used as: the loaded recognizer model.

## Text to Speech

**Piper** (release 2023.11.14-2)

License: MIT
Upstream: rhasspy/piper, https://github.com/rhasspy/piper
Used as: neural text to speech synthesis. The Piper binary is invoked as a
subprocess and its raw 22050 Hz 16-bit signed mono PCM output is fed into a
pygame.mixer.Sound buffer for playback through the Waveshare USB sound card.

Note. The original rhasspy/piper repository is now archived. Active
development has moved to OHF-Voice/piper1-gpl, which uses the GPL licensed
espeak-ng phonemizer. Echo IRIS uses the older MIT-licensed release
2023.11.14-2 binary.

**en_GB-vctk-medium voice model** (speaker ID 2)

License: CC BY 4.0 (per the model card on the Piper voices Hugging Face
repository, which inherits from the VCTK Corpus license)
Upstream: rhasspy/piper-voices, https://huggingface.co/rhasspy/piper-voices
Used as: the British English voice model loaded by the Piper binary at
runtime.

**piper-phonemize** (transitive dependency)

License: GPL (espeak-ng)
Note. The Piper binary calls espeak-ng for phonemization. The GPL applies to
the phonemizer at runtime and does not affect the redistribution of the WAV
audio Piper produces. Echo IRIS distributes neither the Piper binary nor the
espeak-ng library, only the calling code.

## LLM Runtime

**Ollama**

License: MIT
Upstream: ollama/ollama, https://github.com/ollama/ollama
Used as: the local model server that hosts qwen3.5:2b and exposes it via
HTTP at `localhost:11434`. Installed on the Pi via Pi-Apps.

**llama.cpp / ggml** (transitive dependency, statically linked into Ollama)

License: MIT
Upstream: ggerganov/llama.cpp, distributed within the Ollama binary
Note. Ollama statically links llama.cpp. The MIT license requires
attribution of the ggml authors. This entry satisfies that requirement for
any distribution of Echo IRIS that bundles or recommends the Ollama binary.

## Embeddings (RAG, runtime-disabled)

**nomic-embed-text v1.5** (`nomic-embed-text:v1.5` in the Ollama library)

License: Apache License 2.0
Upstream: nomic-ai, https://huggingface.co/nomic-ai/nomic-embed-text-v1.5
Used as: the embedding model for the optional `iris_rag.py` retrieval
pipeline. The pipeline is intentionally disabled at runtime via a try/except
import guard for the demo-day build, but the dependency is still listed
because the module ships in `/software/`.

## Audio Plumbing

**pygame** (mixer subsystem)

License: LGPL
Upstream: https://www.pygame.org
Used as: the audio mixer that plays both Piper TTS output and SoundManager
sound effects through a single ALSA client, avoiding the device contention
that occurs when separate aplay subprocesses compete for the Waveshare card.

**ALSA / aplay / arecord** (system tools)

License: LGPL (ALSA)
Upstream: https://www.alsa-project.org
Used as: the audio capture path. `arecord` is invoked as a subprocess and
its stdout is piped directly into Vosk. The Python audio libraries
PyAudio and sounddevice were both tested and rejected because of word
doubling artifacts with the K1 wireless lavalier microphone.

## Vision and Object Detection

**Ultralytics YOLO11** (yolo11n, the nano variant)

License: GNU Affero General Public License v3.0 (AGPL-3.0)
Upstream: ultralytics/ultralytics, https://github.com/ultralytics/ultralytics
Used as: real-time object detection model. YOLO11n weights are deployed to
the Sony IMX500 on camera neural processor in Sony's RPK format. Detection
runs continuously on the camera silicon while the voice agent is active,
producing labeled bounding boxes on the live preview window so visitors can
see themselves and surrounding objects highlighted while chatting with IRIS.

License note. The Ultralytics AGPL-3.0 license is strong copyleft. Any
larger work that incorporates YOLO11 at runtime, including this project as
a whole when running, falls under AGPL-3.0 obligations: the complete
corresponding source code of the larger work must be made available under
AGPL-3.0 to anyone who uses the system, including over a network. Echo IRIS
satisfies this by virtue of being a fully public open source repository.
The Echo IRIS source code in this repository remains MIT licensed (see
`LICENSE`), but downstream forkers who combine this code with YOLO11 in
any product or service inherit the AGPL-3.0 obligation for the combined
work. Commercial deployment that does not satisfy AGPL-3.0 requires an
Ultralytics Enterprise License, available at https://www.ultralytics.com/license.

**COCO dataset** (Common Objects in Context)

License: Creative Commons Attribution 4.0 (CC BY 4.0) for the annotations,
Flickr terms for the underlying images
Upstream: https://cocodataset.org
Used as: the training dataset for the pretrained YOLO11n weights. The 80
COCO classes are what `iris_detector.py` recognizes (person, chair,
backpack, laptop, etc.).

Citation. Lin, T.-Y., Maire, M., Belongie, S., Bourdev, L., Girshick, R.,
Hays, J., Perona, P., Ramanan, D., Zitnick, C. L., and Dollar, P. (2014).
Microsoft COCO: Common Objects in Context. arXiv:1405.0312.

**Sony IMX500 on-camera neural processor**

License: hardware (no software license applies to the silicon itself).
Sony provides conversion tools and a runtime under their own terms.
Upstream: Raspberry Pi IMX500 AI Camera documentation
Used as: the substrate that runs YOLO11n inference on-camera at low latency
without consuming Pi CPU cycles. Detection results are returned to the host
over the CSI interface and consumed through the Picamera2 Python interface
in `iris_detector.py`.

**Picamera2 and libcamera**

License: BSD 2-Clause (Picamera2) and LGPL 2.1 (libcamera)
Upstream: https://github.com/raspberrypi/picamera2 and https://libcamera.org
Used as: the Python interface for the IMX500 camera. Picamera2 provides
the live preview window and surfaces the on-camera detection output to
`iris_detector.py` for natural-language formatting (including the irregular
plurals dictionary that turns "1 person, 3 person" into "one person and
three people").

**rpicam-apps** (`rpicam-still`, `rpicam-hello`)

License: BSD 2-Clause
Upstream: https://github.com/raspberrypi/rpicam-apps
Used as: still capture for the LLM-based vision queries (the qwen3.5:2b
"describe what you see" code path). `rpicam-still` replaced the deprecated
`libcamera-still` on Raspberry Pi OS Bookworm.

## Python Standard Dependencies

**requests** (Apache 2.0), **pygame** (LGPL), **vosk** (Apache 2.0).
Pinned versions are listed in `requirements.txt`.

## Microcontroller

**Arduino IDE / arduino-cli**

License: AGPL 3.0 (Arduino IDE), GPL 3.0 (arduino-cli)
Upstream: https://www.arduino.cc
Used as: development and flashing toolchain for the Arduino Nano R4 sketch
that drives the discrete LED status indicators and the pan/tilt servos via
direct PWM on pins D9 and D10.

**Arduino core for Renesas (`arduino:renesas_uno`)**

License: LGPL 2.1
Upstream: https://github.com/arduino/ArduinoCore-renesas
Used as: the board package for the Arduino Nano R4 (ABX00143) Renesas RA4M1
microcontroller.

**Servo library** (Arduino core)

License: LGPL 2.1
Used as: pan/tilt servo control on the Nano R4 after the Arducam B0283
PCA9685 controller failed I2C detection.

## Hardware Platform Acknowledgments

The mini-Jeep chassis is the Cars4Kids "Gravity" platform, sold as the
XGRAVITY in its US white-trim variant. Specifications and the spec source
URL are documented in `/hardware/platform_specs.md`. No software license
applies to the chassis. The acknowledgment is included for traceability
because future ECE 202 teams will need to know the exact platform to source
replacement parts.

## Data Sources

Sound effects in `/software/sounds/` are sourced from CC0 and freely
licensed libraries, specifically SoundBible, Freesound, and OpenGameArt.
Each file's origin is documented in the SoundManager source comments.
No copyrighted audio (movie clips, song clips, franchise sound effects) is
included. All effects were normalized with `sox` to approximately 0.10 RMS
before commit.

## Reference Projects

The architectural pattern of routing TTS through a single pygame mixer to
avoid ALSA contention with simultaneous sound effect playback is adapted
from BMO by brenpoly, https://www.youtube.com/@brenpoly The audio resampling
approach, the sound effect timing pattern, and the chat memory persistence
pattern were also informed by that project.

## Licenses Not Distributed in This Repository

The full text of each upstream license is not included in this repository.
Each component above links to its upstream project where the canonical
license text lives. Future ECE 202 teams or downstream forkers who
distribute Echo IRIS as part of a larger product should retrieve and bundle
the appropriate license texts from each upstream source per that license's
redistribution requirements.
