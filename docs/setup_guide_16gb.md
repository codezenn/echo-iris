# Setup Guide: 16GB Production Build

This guide walks a future ECE 202 team through a full from-scratch
build of the Echo IRIS 16GB production path on a Raspberry Pi 5 (16GB).

The 16GB build is the full system: voice agent, persistent chat
memory, personality switching, scoreboard, easter eggs, runtime LLM
through Ollama, triggered LLM vision through the Sony IMX500, the
optional RAG module, and the Arduino LED bridge for status indication.

If you only need the demo path with no LLM, build the 8GB target
first using `setup_guide_8gb.md`. The 16GB build extends that
foundation rather than replacing it.

## Prerequisites

Hardware:

- Raspberry Pi 5, 16GB RAM
- NVMe SSD (256 GB or larger) on an M.2 HAT+ board. The boot from
  microSD path works but is not the production configuration.
- Pi 5 active cooler
- USB-C power supply rated 5V at 5A or better. The Argon PWR GaN 27W
  is tested working. Refer to `troubleshooting.md` before substituting.
- Sony IMX500 AI Camera, with a 300mm OSOYOO ribbon cable for routing
  to the camera bracket
- Arducam B0283 pan/tilt bracket. The on-bracket PCA9685 PWM driver is
  inert in the production build. The two servos run on direct PWM
  from Arduino Nano R4 pins D9 (pan) and D10 (tilt).
- Waveshare USB TO AUDIO sound card for speaker output
- K1 wireless lavalier mic, or equivalent USB Audio Class mic at 48 kHz
- Speaker, 3.5 mm input
- Arduino Nano R4 connected by a data-capable USB cable (charge-only
  cables will not enumerate the device)
- UPS HAT (B), pogo pin connection at I2C address `0x42`. Power for
  servos and LED hardware comes from the UPS HAT USB output.
- KYY 15.6 inch 1080p HDMI display
- Discrete status LEDs wired to Nano R4 GPIO

Software you will install:

- Raspberry Pi OS 64-bit Bookworm
- Vosk small English model
- Piper TTS with the en_GB-vctk-medium voice
- Ollama with `qwen3.5:2b-q4_K_M`, `qwen3:0.6b`, and `nomic-embed-text:v1.5`
- Picamera2, libcamera, rpicam-apps, plus IMX500 firmware tools
- arduino-cli with the Renesas UNO board package

Time required: roughly four hours of active work, plus model
downloads. The Ollama model pulls take the longest.

## Step 1: Install Raspberry Pi OS to NVMe

Use the Raspberry Pi Imager. Select `Raspberry Pi OS (64-bit)` based
on Bookworm. Image directly to the NVMe drive. Configure hostname,
username, and Wi-Fi during the imager's pre-write configuration step.
The reference deployment uses hostname `raspberrypi` and username
`penrose`.

Confirm the Pi boots from NVMe and not from microSD. The boot order
priority should be NVMe first. If the Pi boots from microSD with the
NVMe attached, run `sudo raspi-config`, navigate to Advanced Options,
Boot Order, and select NVMe.

After first boot, update:

```
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

## Step 2: Verify the power supply

Confirm no throttling before installing anything else:

```
vcgencmd get_throttled
```

Expected: `throttled=0x0`. Any other value indicates undervoltage.
Resolve power before continuing. See `troubleshooting.md` for the
throttle flag reference table.

Enable persistent journaling:

```
sudo mkdir -p /var/log/journal
sudo systemctl restart systemd-journald
```

## Step 3: System dependencies

```
sudo apt install -y python3-pip python3-venv git \
    alsa-utils libasound2-dev portaudio19-dev \
    ffmpeg sox libsox-fmt-all \
    libcamera-apps rpicam-apps python3-picamera2 \
    i2c-tools \
    build-essential cmake
```

`libcamera-apps` and `rpicam-apps` provide both the legacy and current
camera command names. The current names start with `rpicam-`. The old
`libcamera-` names are still present but should not be used in new
scripts on Bookworm. `python3-picamera2` is the Python binding the
production script uses for the YOLO11n preview pipeline.

`i2c-tools` provides `i2cdetect` for verifying the UPS HAT is visible
on the bus.

## Step 4: Pin the camera stack with apt-mark hold

Pi OS updates have broken the IMX500 firmware upload path mid-project
in the past. Pin the affected packages now to prevent silent breakage
on the next `apt upgrade`:

```
sudo apt-mark hold libcamera0.3 libcamera-apps rpicam-apps \
    python3-picamera2 firmware-tools-rpi
```

Verify the hold:

```
apt-mark showhold
```

The five packages should appear. To unpin in the future:

```
sudo apt-mark unhold <package>
```

Do not unpin without a clear reason. The hold is the project's
defense against the recurrence of a known upstream regression.

## Step 5: Verify the IMX500 camera

Connect the camera to the Pi 5 CSI port. The reference deployment uses
CAM/DISP 0. The 300mm ribbon cable's silver contacts face away from
the HDMI ports on the Pi 5 side. The camera-side orientation flips.

Test capture:

```
rpicam-hello --nopreview -t 2000
```

The camera should initialize, run for two seconds, and exit cleanly.
A successful first run with the IMX500 firmware loads the on-camera
RP2040. If the command hangs or fails with a firmware error, the
RP2040 is in a partially loaded state. Recovery requires a full
power cycle: unplug USB-C from the Pi, wait at least 15 seconds, and
replug. Do not use `sudo reboot`. The RP2040 needs the wait to fully
de-energize.

Once `rpicam-hello` succeeds, capture one still:

```
rpicam-still --nopreview -o /tmp/test.jpg -t 1000
```

The image should write to `/tmp/test.jpg`. Inspect it with any image
viewer.

Production rule: one image per Ollama vision request. Multi-image
requests crash the IMX500 firmware. The `iris_detector.py` module
enforces this.

## Step 6: Install Vosk and Piper

Same steps as the 8GB guide. Install Vosk:

```
pip install vosk --break-system-packages
mkdir -p ~/model
cd ~/model
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15/* .
rmdir vosk-model-small-en-us-0.15
rm vosk-model-small-en-us-0.15.zip
```

Install Piper:

```
mkdir -p ~/iris_voice
cd ~/iris_voice
wget https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_aarch64.tar.gz
tar -xzf piper_linux_aarch64.tar.gz
rm piper_linux_aarch64.tar.gz
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/vctk/medium/en_GB-vctk-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/vctk/medium/en_GB-vctk-medium.onnx.json
```

## Step 7: Install Ollama via Pi-Apps

Pi-Apps is the recommended path on Bookworm because it handles the
ARM64 native build and systemd integration cleanly. Install Pi-Apps:

```
wget -qO- https://raw.githubusercontent.com/Botspot/pi-apps/master/install | bash
```

Launch Pi-Apps from the desktop menu. Navigate to AI Tools, select
Ollama, install. Pi-Apps installs the native ARM64 binary and
configures the systemd service.

Verify the service is running:

```
systemctl status ollama
```

Confirm the API is reachable:

```
curl http://localhost:11434/api/tags
```

The response is valid JSON listing currently loaded models. The list
will be empty until you pull models in the next step.

## Step 8: Pull Ollama models

```
ollama pull qwen3.5:2b-q4_K_M
ollama pull qwen3:0.6b
ollama pull nomic-embed-text:v1.5
```

The `qwen3.5:2b-q4_K_M` model is the primary LLM and the vision model. It is
roughly 2.7 GB. The `qwen3:0.6b` model is the lightweight fallback
used by the RAG module if RAG is later re-enabled. The `nomic-embed-
text:v1.5` model produces embeddings for the RAG knowledge base.

Verify all three are present:

```
ollama list
```

Warm the primary model so the first script run does not hit a
cold-start timeout:

```
ollama run qwen3.5:2b-q4_K_M "hello"
```

## Step 9: Configure the Ollama systemd override

The default Ollama service unloads models after a few minutes of
inactivity. The production build needs the model to stay resident.
Create a systemd override:

```
sudo systemctl edit ollama.service
```

Paste the following into the override file:

```
[Service]
Environment="OLLAMA_KEEP_ALIVE=-1"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
Environment="OLLAMA_NUM_PARALLEL=1"
```

Save and exit. Reload systemd and restart Ollama:

```
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

`KEEP_ALIVE=-1` keeps the model resident indefinitely.
`MAX_LOADED_MODELS=1` and `NUM_PARALLEL=1` prevent Ollama from
spawning concurrent inference workers, which would push the Pi past
its memory budget under load.

## Step 10: Install Python packages

```
pip install requests pygame numpy serial pyaudio --break-system-packages
```

`pygame` is used for sound effect playback through `pygame.mixer` and
for the unified audio output path that bypasses ALSA contention with
`aplay`. `numpy` is required by the in-process cosine similarity
retriever in `iris_rag.py`. `serial` is used for the Arduino LED
bridge.

## Step 11: Add the user to the dialout group

Required for write access to `/dev/ttyACM0` on the Arduino bridge:

```
sudo usermod -a -G dialout $USER
sudo reboot
```

After reboot, verify:

```
groups | grep dialout
```

The output should include `dialout`. Do not run the voice agent as
sudo to work around missing dialout membership. Sudo breaks the audio
pipeline.

## Step 12: Install arduino-cli and the Nano R4 board package

```
mkdir -p ~/bin
cd ~/bin
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
arduino-cli core update-index
arduino-cli core install arduino:renesas_uno
```

The Renesas UNO core covers the Nano R4. Verify the install:

```
arduino-cli board listall | grep -i nano
```

Connect the Nano R4 via a data-capable USB cable. Confirm the device
enumerates:

```
ls /dev/ttyACM*
```

You should see `/dev/ttyACM0`. If you see nothing, the USB cable is
likely a charge-only cable. Swap it.

## Step 13: Verify audio devices

List devices:

```
arecord -l
aplay -l
```

The K1 lavalier mic appears as a USB Composite Device on its own card
number. The Waveshare speaker appears as PnP Audio Device on a
different card number. Both are picked up automatically by
`find_usb_audio()` at script startup.

Card numbers swap on reboot. The script handles the swap. Verify the
detection log on first run.

Test the speaker:

```
speaker-test -D plughw:N,0 -c 2 -t wav
```

Substitute the speaker card number for `N`. Use `plughw` not `hw`
on the Waveshare. The raw `hw` device rejects mono.

## Step 14: Verify the UPS HAT

```
i2cdetect -y 1
```

The UPS HAT B should appear at address `0x42`. The Arducam PCA9685 is
inert in this build but if you are also doing a continuity test, the
PCA9685 nominal address is `0x40`. The production build does not rely
on the PCA9685 responding.

## Step 15: Clone the repository

```
cd ~
git clone https://github.com/codezenn/echo-iris.git
```

The 16GB script lives at `~/echo-iris/software/echo_iris_16gb.py`.

## Step 16: First run

```
cd ~/echo-iris/software
python3 echo_iris_16gb.py
```

Expected startup output:

- detected USB audio card numbers for mic and speaker
- loaded Vosk model
- Piper paths verified
- Ollama health check passes
- Arduino bridge connected on `/dev/ttyACM0`
- IMX500 camera initialized
- startup confirmation plays through the speaker

Test a wake word followed by a question that exercises the LLM path,
such as "what do you think about the weather". The dispatch chain
should fall through DEMO_ANSWERS, build the Ollama payload, and
return a streamed response in the 28 to 41 second range.

Test the triggered vision path with "what do you see". The capture
takes roughly 90 seconds end to end on the 16GB build.

## Pre-demo checklist

Run through this before a public demo. Card numbers can swap. Camera
firmware can lock. Models can unload despite the systemd override if
the service was restarted.

```
vcgencmd get_throttled
arecord -l
aplay -l
ls /dev/ttyACM*
i2cdetect -y 1
ollama list
rpicam-hello --nopreview -t 2000
ollama run qwen3.5:2b-q4_K_M "hello"
```

Each command should succeed. The throttle should read `0x0`. The
Ollama list should include the three models. The camera should
initialize cleanly. The model warmup should complete in under five
seconds on the second run.

If `rpicam-hello` hangs, perform the IMX500 firmware recovery
procedure. Unplug USB-C. Wait at least 15 seconds. Replug. The
camera should now initialize.

## Known issues

Picamera2 preview window placement is unreliable under Wayland. The
window opens at an arbitrary screen position and cannot reliably be
moved by code. Reposition manually after launch or accept the
placement.

Concurrent `rpicam-still` calls within a few seconds will cause one
to time out. The production code enforces one capture per LLM
request.

For a complete failure-mode reference including audio routing
recovery, the IMX500 firmware lock recovery procedure with reasoning,
the qwen3 thinking-mode infinite loop trap, and the charge-only USB
cable trap, see `troubleshooting.md`.
