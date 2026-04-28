# Platform Specifications

The Echo IRIS mini-Jeep chassis is a Cars4Kids "Gravity" 12-volt children's
electric ride-on, sold in the US under the XGRAVITY brand. The white
variant is the IRIS platform. The same OEM chassis in metallic black is
the platform used by the green Jeep team for their voice-controlled motor
drive variant.

## Brand Note

The chassis ships under multiple brand names from the same OEM. XGRAVITY
is the US-market label visible on the body trim. Cars4Kids Trading is the
reseller whose product page documents the specifications.

Spec source: https://www.cars4kidstrading.com/product/electric-childrens-jeep-gravity-metallic-black-12-volts/

When sourcing replacement parts, search for both "XGRAVITY" and "Cars4Kids
Gravity" since vendor listings vary.

## Specifications

| Parameter                    | Value                       |
|------------------------------|-----------------------------|
| Battery                      | 12V, 7Ah sealed lead-acid   |
| Motors                       | 2 x 45W DC                  |
| Drive configuration          | Two-wheel rear drive        |
| Speed range                  | 3 to 6 km/h                 |
| Maximum load                 | 60 kg                       |
| Vehicle dimensions (L x W x H) | 126 x 78 x 79 cm          |
| Charging time                | 8 to 12 hours typical       |
| Operating time per charge    | 1 to 2 hours typical        |
| Remote control               | 2.4 GHz parental override   |
| Tires                        | Hard plastic, non-pneumatic |

## Why The Onboard Battery Is Not Used For Pi Power

The original project plan considered tapping the Jeep's 12V 7Ah battery
to power the Raspberry Pi, the camera, the LEDs, and the Arduino. This
approach was abandoned for two reasons.

The 7Ah capacity is small. A Raspberry Pi 5 under load draws roughly 2A
at 5V (10W). At a generous 70 percent step-down efficiency from 12V to 5V,
the Pi alone would draw approximately 1.2A from the 12V battery. The IMX500
camera, the USB peripherals, and the Arduino add another 0.5A. That puts
the total Pi-stack draw at 1.7A, which is roughly a quarter of the
battery's 7Ah capacity per hour. With the motors also drawing from the
same battery during driving demos, the Pi would either share a degraded
voltage rail with the motor controller or starve the motors of current.

The motor controller PWM noise on the 12V rail would couple into the Pi's
power supply unless heavily filtered. The Pi 5 is sensitive to undervoltage
and brownouts (verified during early testing) and the resulting throttle
flag conditions would degrade Vosk and Ollama performance unpredictably.

The decision: power the Pi stack from a separate USB-C source (Argon PWR
GaN 27W on the desk during development, UPS HAT B with internal batteries
during demos) and leave the Jeep battery for the original drive system.
The green Jeep variant takes a different approach since their primary
demonstration is voice-controlled motor drive rather than voice
conversation.

## Modifications Made

The chassis ships as a functional ride-on toy. Echo IRIS modifies it as
follows.

The hood mounts the Pi enclosure (3D printed, see `/3d-models/`).

The lid is modified to expose the camera through a custom Arducam B0283
pan/tilt bracket. The original bracket pocket and ribbon cable slot were
designed for the IMX500 + OSOYOO 300mm cable assembly.

The dashboard area mounts the KYY 15.6 inch HDMI monitor that displays
the live camera feed with YOLO bounding boxes.

The roll bar area mounts the discrete LED strip used for status indication
(replacing the originally planned WS2812B addressable strip that failed
during installation).

The interior houses the wireless lavalier microphone receiver and the
Waveshare USB sound card.

The drive system is unmodified. The original 12V battery, motor controller,
and remote control are intact and functional. Echo IRIS does not currently
control the drive system. Future ECE 202 teams adding autonomous driving
will need to either hijack the existing motor controller or replace it
with a Pi-controlled equivalent (the green Jeep team's Cytron MDD10A
pattern is the most documented example).

## Sourcing

The XGRAVITY platform is available through Cars4Kids Trading and similar
ride-on toy vendors at the link in the Brand Note section above. List
prices have varied between approximately 200 and 400 USD over the project
period depending on color and stock. Group 35 inherited its chassis from
the previous IRIS team rather than purchasing new.

## For Replacement Parts

Common wear items if you keep the chassis in service across multiple
semesters: 12V 7Ah sealed lead-acid battery (standard, available from
multiple sources for ~25 USD), the 2.4 GHz remote, and the rear-wheel
motor brushes. The OEM motor controller does fail occasionally and is
not user-serviceable. A replacement motor controller is the most likely
single-point failure for the platform.
