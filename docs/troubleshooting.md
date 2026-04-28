# Troubleshooting

This document collects the failure modes that cost us the most time
during development, the diagnosis steps we used to identify them, and
the recovery procedures that worked. It is organized by subsystem.
Future ECE 202 teams who hit any of these symptoms should be able to
recognize the failure here, run the diagnosis, and recover without
rediscovering the path.

## Audio

The audio subsystem is the most fragile part of the runtime. USB card
numbering changes between reboots, ALSA device routing differs between
device types, and the wireless lavalier mic only operates at one sample
rate. Most audio bugs trace back to one of these three.

### USB card numbers swap on reboot

Symptom: voice agent starts cleanly but the mic produces silence, or
the speaker plays into the wrong device, or both. `arecord -l` and
`aplay -l` show the same physical devices but at different card numbers
than the previous boot.

Cause: Linux assigns USB sound card numbers in enumeration order. On a
Pi 5 with multiple USB audio devices, the order is not deterministic
across reboots.

Diagnosis:

```
arecord -l
aplay -l
```

The K1 lavalier mic appears as a USB Composite Device. The Waveshare
USB sound card appears as PnP Audio Device. Either may land on any
card number from 1 upward.

Recovery: the production script calls `find_usb_audio()` at startup
which scans for both devices by name fragment and returns the current
card numbers. The function is the canonical way to handle the swap. Do
not hardcode card numbers in the script. If you must verify before a
demo, run `arecord -l` and `aplay -l` and confirm the script's
detection log matches.

### Composite versus PnP device routing

Symptom: mic is silent, or speaker output goes to the wrong device, or
the script picks one USB device for both input and output.

Cause: a single regex on "USB" in device name will match both the
Composite (mic) and PnP (speaker) devices. The original
`find_usb_audio()` did this and routed both streams to whichever device
the OS enumerated first.

Recovery: the patched `find_usb_audio()` distinguishes Composite from
PnP by name fragment and returns separate card numbers for the input
and the output. The patch ships in v1.0. If you write a new audio
detector, treat input and output as independent searches against
distinct name fragments.

### plughw versus hw on the Waveshare speaker

Symptom: speaker rejects mono S16_LE 22050 Hz audio with a format
mismatch error when invoked through `aplay -D hw:N,0`.

Cause: the Waveshare USB sound card refuses mono on the raw `hw`
device. ALSA's `plughw` plugin transparently converts mono to stereo
and the card accepts it.

Recovery: use `plughw:N,0` in the aplay command and in any sound
manager configuration. Never use `hw:N,0` on the Waveshare. The
sound_manager helper module is configured for plughw by default. The
pygame.mixer playback path on the 16GB build is independent of this
issue because it talks to ALSA at a different layer.

### K1 lavalier mic 48 kHz behavior

Symptom: the mic only reports a single supported sample rate and Vosk
expects 16 kHz audio, but the K1 will not produce it.

Cause: the K1 wireless lavalier dongle exposes 48 kHz as its only
supported rate over its USB Audio Class interface.

Recovery: capture at 48 kHz and resample in process to 16 kHz before
feeding Vosk. The production audio path uses `arecord -D hw:N,0 -f
S16_LE -r 48000 -c 1 -q` piped to a Kaldi LinearResample inside the
Vosk wrapper. The downsampling is settled in v1.0 and is not deferred
work.

### PyAudio word-doubling artifact

Symptom: Vosk transcripts contain doubled or echoed words, especially
at the start of utterances. Recognition accuracy is acceptable on the
older wired mic but degrades sharply on the K1.

Cause: PyAudio's buffering interacts poorly with the K1 dongle. The
exact root cause was not isolated. The artifact disappeared when the
audio path was switched to an `arecord` subprocess.

Recovery: do not read the K1 with PyAudio. Use the `arecord`
subprocess pattern documented in the production script. The PyAudio
import is no longer used on the audio capture path in v1.0.

## Vision

The Sony IMX500 ships with two failure modes worth knowing about. Both
are recoverable but the firmware upload lock is the more disruptive of
the two.

### IMX500 firmware upload lock

Symptom: `rpicam-hello` or any Picamera2-based script hangs on startup
with a message about firmware upload, or fails immediately with a
firmware error. The camera does not stream. Subsequent attempts produce
the same failure even after software reboot.

Cause: the IMX500 contains an RP2040 microcontroller that handles
on-camera firmware loading. Once the RP2040 is in a partially loaded
state, it does not respond to soft reset. The firmware upload pipeline
will not recover until the RP2040 is power-cycled at the hardware
level.

Recovery: full power cycle of the Pi, with at least a 15 second wait
between unplugging USB-C power and replugging it. Do not use `sudo
reboot`. Do not unplug and immediately replug. The RP2040 needs the
wait to fully de-energize. After the cold start, `rpicam-hello`
recovers. This procedure ran twice on demo day and worked both times.

### rpicam-still timeouts on consecutive captures

Symptom: the first vision-triggered capture succeeds. A second capture
within a few seconds times out or hangs.

Cause: `rpicam-still` on Bookworm does not always release the camera
cleanly between invocations when called rapidly in succession.

Recovery: enforce a minimum interval between captures in the calling
code. The triggered-vision path in `iris_detector.py` calls
`rpicam-still` once per LLM request and discards multi-image requests
to Ollama because qwen3.5 vision through Ollama only handles one image
per call anyway. Treat the one-capture-per-request rule as a hard
constraint.

### Picamera2 Wayland positioning

Symptom: the Picamera2 preview window appears at an arbitrary screen
position on launch, sometimes off-screen on the KYY HDMI monitor.

Cause: under Wayland, Picamera2's preview cannot reliably set its own
window position. X11 had a working API for this. Wayland does not.

Recovery: position the window after launch using a window manager
keybind, or accept the placement and use the YOLO11n bounding box
overlay from a fixed-position alternative if visual presentation
matters. There is no clean code-side fix on Bookworm Wayland.

### libcamera-* commands deprecated

Symptom: tutorials or older docs reference `libcamera-hello` or
`libcamera-still` and they fail with command-not-found.

Cause: Bookworm renamed the user-facing commands to `rpicam-hello` and
`rpicam-still`. The libcamera library is still in use under the hood.
The renamed commands are not aliases and the old names are gone.

Recovery: use `rpicam-hello` and `rpicam-still` everywhere. Add
`--nopreview` to production calls to suppress the preview window when
the script handles its own display.

## LLM

The LLM path is the slowest part of the production build and the place
where the model's quirks show up most visibly. The two recurring issues
are response latency and the qwen3 reasoning chain.

### qwen3 thinking mode infinite loop

Symptom: an LLM call returns a response containing a long internal
reasoning chain prefixed with text like `<think>` and the actual answer
arrives late or never. Some calls never return.

Cause: the qwen3 family supports a reasoning mode that runs an internal
chain-of-thought before the final response. The mode is on by default
in the Ollama API. The chain occasionally fails to terminate in a small
percentage of calls, blocking the response.

Recovery: set `think: False` at the top level of the Ollama API
request payload. It must be at the top level, not nested inside
`options`, and not in the prompt as a `/no_think` prefix. The prompt
prefix does not work reliably and is not the documented disable
mechanism.

The production script sets this on every call. If you add a new code
path that calls Ollama, copy the payload structure from the existing
calls.

### LLM response latency

Symptom: a complete LLM round trip takes more than 30 seconds and the
audience experience suffers visibly.

Cause: a 2B-parameter model on a Pi 5 is genuinely slow. Cold starts
add seconds. Long context inflates the per-token time.

Recovery: the production build sets `num_ctx: 2048` and
`num_predict: 100` in the Ollama options to bound the work. The Ollama
service is configured with `KEEP_ALIVE=-1`, `MAX_LOADED_MODELS=1`, and
`NUM_PARALLEL=1` via systemd override so the model stays resident. With
these settings, a typical text-only response lands at 28 to 41
seconds. A vision response lands around 90 seconds. If the response
exceeds these ranges by a wide margin, the system is likely thermally
throttling or hitting swap.

### Ollama health check

Diagnosis: confirm the service is up and the expected models are
loaded.

```
systemctl status ollama
ollama list
curl http://localhost:11434/api/tags
```

The active models list should include `qwen3.5:2b-q4_K_M`,
`nomic-embed-text:v1.5`, and `qwen3:0.6b`. If the service is up but a
model is missing, run `ollama pull <model>` to fetch it.

### Cold start exceeds timeout

Symptom: the very first LLM call after boot times out and IRIS
responds with the timeout fallback phrase. Subsequent calls succeed.

Cause: Ollama loads the model on first request unless the keep-alive
configuration is set. Loading a 2B model from disk on a Pi 5 takes more
than the script's default timeout.

Recovery: warm the model before the demo with `ollama run qwen3.5:2b-q4_K_M
"hello"`. The keep-alive override prevents unload between calls but
does not avoid the first load. The 16GB setup guide includes this in
the pre-demo checklist.

## Hardware and Power

Power problems were the single largest category of hardware failure on
the project. The throttle flag is the first place to look when the Pi
behaves erratically.

### Throttle flag interpretation

The Pi exposes its current throttle status through `vcgencmd`.

```
vcgencmd get_throttled
```

The output is a single hexadecimal value. The bits map to undervoltage,
frequency cap, throttling, and soft-temperature events, both currently
active and any-time-since-last-boot.

Reference table for values seen during this project:

```
0x0       OK. No undervoltage, no throttling.
0x1       Undervoltage currently active.
0x10000   Undervoltage occurred since boot. Now recovered.
0x50000   Undervoltage and throttling occurred since boot. Power supply
          is borderline at minimum and inadequate at peak load.
```

Treat any nonzero value as a power problem. Do not run the voice agent
under stress until the value reads `0x0` consistently across reboots
under load.

### Power supply test results

The table below summarizes units tested during the project against the
loaded Pi 5 stack: Pi, NVMe, USB hub, Waveshare audio, K1 dongle, IMX500
camera, KYY display, UPS HAT, Arduino Nano R4. Future teams testing
other units should add rows rather than replace these.

| Supply | Result | Notes |
|---|---|---|
| Anker PowerCore 3 5000 | Failed | Triggered `0x50000` under load. Removed from the project. |
| Apple 30W USB-C | Failed | Voltage held around 0.90 V at the test rail under load. Insufficient even at idle plus camera. |
| Apple 96W USB-C | Worked | Used as interim during early dev. Replaced by Argon for cost. |
| Argon PWR GaN 27W | Worked | `vcgencmd get_throttled` confirmed `0x0`. Permanent desk supply. |
| Baseus 65W power bank | Untested at scale | Theoretical mobile fit. Requires a 5 A E-Marked USB-C cable. Not stress-tested under demo conditions. |

### Diagnosing undervoltage

The kernel logs an undervoltage event with a clear message:

```
hwmon hwmon4: Undervoltage detected
hwmon hwmon4: Voltage normalised
```

The pair indicates a transient. Persistent undervoltage logs the first
without the second. Enable persistent journaling so the logs survive
the reboot you will be tempted to do mid-debug:

```
sudo mkdir -p /var/log/journal
sudo systemctl restart systemd-journald
```

### Undervoltage masquerading as a software bug

Symptom: random crashes, audio glitches, USB device disappearance, file
system errors that come and go, the voice agent freezing partway
through a response. No clean Python traceback.

Cause: when the Pi browns out under peak load, USB devices reset, ALSA
streams glitch, and processes die without consistent error messages.
The symptoms look like a software bug at every layer.

Recovery: check `vcgencmd get_throttled` first, every time, before
investigating any random crash. If the value is nonzero, treat it as
the root cause and do not start chasing the apparent symptom.

## Arduino and Servos

The bracket and LED control path went through one major rework when the
on-bracket PWM driver failed. The current state is direct PWM from the
Arduino. Future teams who try to revive the original PCA9685 path
should know what they are walking into.

### Nano R4 not detected on /dev/ttyACM0

Symptom: `ls /dev/ttyACM*` shows no device. `dmesg` shows no USB CDC
ACM enumeration. The Nano R4 LED is on but the OS does not see it.

Cause: the USB cable is a charge-only cable. Its data lines are not
connected. The Nano R4 powers up and runs but cannot enumerate.

Recovery: replace the cable with a known data-capable USB-A to
USB-C or USB-A to USB-Mini cable. This is the single most common
Arduino setup mistake on the project. Keep one labeled data-capable
cable in the kit.

### dialout group permission silent failure

Symptom: a Python `serial.Serial("/dev/ttyACM0", 115200)` call returns
a permission-denied error, or worse, a successful object that silently
discards writes. LED states never change despite the script running
without errors.

Cause: the Pi user is not in the `dialout` group. Some Python serial
implementations swallow the permission error.

Recovery:

```
sudo usermod -a -G dialout $USER
```

Reboot. Confirm with `groups | grep dialout`. Do not run the voice
agent as sudo to work around this. Sudo breaks the audio pipeline.

### PCA9685 unresponsive on the Arducam B0283

Symptom: the I2C bus shows the UPS HAT at `0x42` but no device at
`0x40`. `i2cdetect -y 1` confirms the bus is alive. The bracket arrives
assembled and the on-board PCA9685 LED is lit.

Cause: indeterminate. The PCA9685 is genuinely unresponsive on both the
Pi 5 I2C bus and the Nano R4 I2C bus. Diagnosis was not pursued past a
point of returns.

Recovery: drive the two servos directly from Nano R4 PWM pins D9 (pan)
and D10 (tilt). The shipped firmware sketch on the Nano R4 includes
the direct-PWM servo handler. The PCA9685 is left on the bracket as
inert hardware. Future teams who want to revisit it should start with a
multimeter continuity test on the Arducam UC-751 PCB before assuming
the chip itself is bad.

### Servo power routing

Critical rule: servo and LED power comes from the UPS HAT USB output.
Not from the Nano R4 5V pin.

The Nano R4 5V pin is rated for roughly 500 mA. A two-servo plus LED
load pulls multiples of that at peak. Powering the load from the Nano
will brown out the board and may cause permanent damage. The UPS HAT
USB output is sized for the load and is on the same regulated rail as
the Pi.

The data and ground lines run through the Nano. Power does not.

### never install rpi_ws281x

Even though the WS2812B strip was abandoned, the warning stands for
future teams who try to drive an LED strip from the Pi GPIO directly.
Installing `rpi_ws281x` reconfigures the Pi's PWM hardware and breaks
Piper TTS audio. The breakage is not obvious until you try to play
audio. Roll back the install if it happens.

The recommended path for any addressable LED work is to keep the
Arduino bridge and update the Arduino sketch. The Pi does not drive
LED data directly.
