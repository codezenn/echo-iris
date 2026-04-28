# Setup Guide: 8GB Build (DEMO_MODE)

This guide walks a future ECE 202 team through a full from-scratch
build of the Echo IRIS 8GB demo path on a Raspberry Pi 5 (8GB).

The 8GB build is the crash-proof fallback. It runs without an LLM. All
voice responses come from a keyword-indexed dictionary called
`DEMO_ANSWERS`. If you are setting up the production build with vision,
LLM, and the full multi-module architecture, follow `setup_guide_16gb.md`
instead.

## Prerequisites

Hardware:

- Raspberry Pi 5, 8GB RAM
- microSD card, 32GB or larger, or NVMe SSD with M.2 HAT+
- Raspberry Pi 5 active cooler
- USB-C power supply rated 5V at 5A or better. The Argon PWR GaN 27W
  is tested working. Lower-rated supplies may trigger undervoltage
  events. See `troubleshooting.md` for the full power supply test
  results.
- USB sound card for speaker output. The Waveshare USB TO AUDIO is the
  reference unit.
- USB microphone. The K1 wireless lavalier is the reference unit but
  any USB Audio Class mic will work. The K1 only operates at 48 kHz so
  the script's downsample path applies.
- Speaker, 3.5 mm input
- HDMI display and keyboard for first boot. Headless setup is possible
  but not documented here.

Software you will install:

- Raspberry Pi OS 64-bit Bookworm
- Python 3.11 (ships with Bookworm)
- Vosk small English model
- Piper TTS with the en_GB-vctk-medium voice
- A handful of Python packages

Time required: roughly 90 minutes of active work, plus model downloads.

## Step 1: Install Raspberry Pi OS

Use the official Raspberry Pi Imager from `raspberrypi.com/software`.
Select `Raspberry Pi OS (64-bit)` based on Bookworm. Configure the
hostname, username, and Wi-Fi during the imager's pre-write
configuration step. The reference deployment uses hostname
`raspberrypi` and username `penrose`. You can use anything you want.

Boot the Pi from the imaged storage. Complete the first-boot wizard
and apply pending updates:

```
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

## Step 2: Verify the power supply

Before installing anything else, confirm the Pi is not throttling:

```
vcgencmd get_throttled
```

Expected output: `throttled=0x0`. Any other value indicates undervoltage
and you should resolve power supply issues before proceeding. See
`troubleshooting.md` for the throttle flag reference table.

Enable persistent journaling so you can review crash logs across
reboots:

```
sudo mkdir -p /var/log/journal
sudo systemctl restart systemd-journald
```

## Step 3: Install system dependencies

```
sudo apt install -y python3-pip python3-venv git \
    alsa-utils libasound2-dev portaudio19-dev \
    ffmpeg sox libsox-fmt-all
```

`alsa-utils` provides `aplay` and `arecord` which the script invokes
directly. `portaudio19-dev` is required for any future PyAudio install
even though the production audio path bypasses it. `sox` is used for
sound effect normalization.

## Step 4: Install Vosk

```
pip install vosk --break-system-packages
```

`--break-system-packages` is required because Bookworm enforces PEP 668
externally managed environments by default. The flag is the
project-standard way to install into the system Python on this
deployment.

Download the small Vosk English model:

```
mkdir -p ~/model
cd ~/model
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15/* .
rmdir vosk-model-small-en-us-0.15
rm vosk-model-small-en-us-0.15.zip
```

The model is roughly 107 MB extracted. The script expects to find it at
`~/model/`.

Do not use the larger lgraph model on the 8GB build. It exceeded RAM
when running concurrently with Ollama in mid-development.

## Step 5: Install Piper

```
mkdir -p ~/iris_voice
cd ~/iris_voice
wget https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_aarch64.tar.gz
tar -xzf piper_linux_aarch64.tar.gz
rm piper_linux_aarch64.tar.gz
```

Download the en_GB-vctk-medium voice model:

```
cd ~/iris_voice
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/vctk/medium/en_GB-vctk-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/vctk/medium/en_GB-vctk-medium.onnx.json
```

The Piper binary lives at `~/iris_voice/piper/piper`. The voice model
lives at `~/iris_voice/en_GB-vctk-medium.onnx`. The script expects both
paths.

Test Piper:

```
echo "Echo IRIS is ready" | ~/iris_voice/piper/piper \
    --model ~/iris_voice/en_GB-vctk-medium.onnx \
    --speaker 2 \
    --output_raw | aplay -r 22050 -f S16_LE -t raw
```

You should hear "Echo IRIS is ready" through the default audio output.
If you hear nothing, the speaker is on a USB device that is not the
default output and you will configure routing in step 7.

## Step 6: Install Python packages

```
pip install pyaudio requests --break-system-packages
```

The 8GB build keeps the package list intentionally minimal. Anything
beyond this is for the 16GB production build.

## Step 7: Verify audio devices

List input and output devices:

```
arecord -l
aplay -l
```

Note the card numbers for the USB mic and the USB speaker. The Pi
assigns these in enumeration order, which can change on reboot. The
script's `find_usb_audio()` function detects them at startup so you do
not need to hardcode anything. Verify that both devices appear and
are not on the same card.

If you are using the K1 lavalier mic, it appears as a USB Composite
Device. The Waveshare speaker appears as PnP Audio Device. The
production `find_usb_audio()` distinguishes between them. Earlier
versions did not and routed both streams to whichever device the OS
enumerated first.

Test the speaker explicitly:

```
speaker-test -D plughw:N,0 -c 2 -t wav
```

Substitute your speaker's card number for `N`. Use `plughw` not `hw`
on the Waveshare. The raw `hw` device rejects mono audio.

## Step 8: Clone the repository

```
cd ~
git clone https://github.com/codezenn/echo-iris.git
```

The 8GB script lives at `~/echo-iris/software/echo_iris_8gb.py`.

## Step 9: First run

```
cd ~/echo-iris/software
python3 echo_iris_8gb.py
```

Expected behavior at startup: the script prints the detected USB audio
card numbers, the loaded Vosk model, and the Piper paths. It then
plays a startup confirmation through the speaker and begins listening
for the wake word.

Wake word triggers include `hello`, `hey`, `iris`, and the Vosk
mishearing variants `aris`, `virus`, and others recorded in the
production wake word list.

Test the demo flow with a known DEMO_ANSWERS keyword such as
"who built you" or "what software do you use".

## Step 10: Optional bash alias

Add to `~/.bashrc`:

```
alias iris='cd ~/echo-iris/software && python3 echo_iris_8gb.py 2>/dev/null'
```

The `2>/dev/null` redirect suppresses harmless ALSA and JACK warnings
that PyAudio probes on startup.

Reload:

```
source ~/.bashrc
```

You can now launch the script with `iris` from any terminal.

## Pre-demo checklist

Run through this list before running a public demo. The 30 minutes
before the demo is the wrong time to find out a card number changed.

```
vcgencmd get_throttled
arecord -l
aplay -l
ls ~/model/am
ls ~/iris_voice/piper/piper
ls ~/iris_voice/en_GB-vctk-medium.onnx
```

Each command should succeed. The throttle output should read
`throttled=0x0`. The four file listings should print without a
"No such file" error.

Run the script. Listen for the startup confirmation. Speak a wake word
followed by a known DEMO_ANSWERS query. Confirm the response plays
back through the correct speaker. Reboot the Pi and run the
verification once more. Card numbers can swap.

## Known issues

The Bookworm `.desktop` launcher path is unreliable. Double-clicking a
correctly-formatted desktop file launches inconsistently under labwc.
Use the bash alias or run the script from a terminal until this is
resolved upstream.

Single common words spoken by the audience can match keywords by
accident. The production keyword list filters single-word triggers but
new keywords added to `DEMO_ANSWERS` should follow the multi-word rule.

For a complete failure-mode reference including audio routing recovery,
power supply diagnostics, and the one-camera-rule for the IMX500,
see `troubleshooting.md`.
