# Bill of Materials

This document lists every component used in the Echo IRIS production build
as it shipped on demo day, April 22, 2026. Components are grouped by
subsystem. The Funding column indicates how the component was acquired.

Pricing reflects the spring 2026 acquisition cost where documented in the
project budget spreadsheet. Components not on the original budget show
representative April 2026 retail prices verified at the time of repo
finalization. Where prices have wide market variance (consumer electronics
sold under multiple brands, items typically sold in multi-packs), the
representative single-unit price is shown. Items marked [TBD] reflect a
specific gap Marc plans to fill before final BOM lock.

Funding source legend:
- Department: ECE department funds, processed through Jackie's purchasing
- Personal: Out-of-pocket purchase by a team member
- Inherited: Carried over from the previous IRIS team or already in the lab

## Compute

| Component                       | Quantity | Funding    | Unit Cost (USD) | Notes |
|---------------------------------|----------|------------|-----------------|-------|
| Raspberry Pi 5 (16GB)           | 1        | Department | $205.94         | Production board, primary system. DigiKey. |
| Raspberry Pi 5 (8GB)            | 1        | Inherited  | --              | Development and DEMO_MODE fallback. |
| Raspberry Pi 5 Active Cooler    | 1        | Department | $5.00           | Required for thermal stability under qwen3.5:2b load. DigiKey. |
| 256GB NVMe SSD + M.2 HAT+ bundle| 1        | Department | $90.00          | Original boot drive bundle from Canakit. The 256GB is the Samsung that later became the SD-card backup. The M.2 HAT+ is the production NVMe interface. |
| 512GB BIWIN NVMe SSD            | 1        | Department | [TBD]           | Separate later purchase from DigiKey to expand storage. Replaced the 256GB as production boot drive. Original purchase price not on the budget spreadsheet. |
| Argon PWR GaN 27W USB-C PD      | 1        | Personal   | $19.99          | Desk power supply during development. Pi 5 official equivalent. |

## Vision

| Component                        | Quantity | Funding    | Unit Cost (USD) | Notes |
|----------------------------------|----------|------------|-----------------|-------|
| Sony IMX500 AI Camera            | 1        | Department | $70.00          | Runs YOLO11n on-camera at zero Pi CPU cost. DigiKey. |
| Arducam B0283 pan/tilt bracket   | 1        | Department | $26.99          | Mechanical bracket only. Servos run via direct Nano R4 PWM after PCA9685 dead. Arducam direct or Amazon. |
| OSOYOO 300mm camera ribbon cable | 1        | Department | $8.99           | Sold only as 3-cable pack (80/150/300mm) on Amazon at this price. Equivalent single-cable at Adafruit ~$1.50. |

## Audio

| Component                       | Quantity | Funding    | Unit Cost (USD) | Notes |
|---------------------------------|----------|------------|-----------------|-------|
| Wireless K1 lavalier mic        | 1        | Personal   | $19.99          | USB Composite Device, 48 kHz capture only. K1 is a generic Amazon model designator across many sellers; lock by ASIN if reordering. |
| Waveshare USB Audio sound card  | 1        | Department | $14.99          | USB PnP Device for speaker output. Waveshare SKU 18833. |
| Speaker (3W class-D, 4 ohm)     | 1        | Inherited  | $1.95           | Adafruit PID 1314 reference price. Mounted in 3D printed front-facing case. |
| USB-A to USB-C mic adapter      | 1        | Personal   | $5.99           | Specifically USB-A male to USB-C female (do not confuse with the inverse). |

## Microcontroller

| Component                       | Quantity | Funding    | Unit Cost (USD) | Notes |
|---------------------------------|----------|------------|-----------------|-------|
| Arduino Nano R4 (ABX00143)      | 1        | Department | $13.30          | Renesas RA4M1, 5V native logic. Arduino direct store, with headers. |
| Data-capable USB cable          | 1        | Personal   | $5.99           | USB-A to USB-C, USB 2.0 data. Charge-only cables prevent device detection on /dev/ttyACM0. |

## Power

| Component                       | Quantity | Funding    | Unit Cost (USD) | Notes |
|---------------------------------|----------|------------|-----------------|-------|
| Waveshare UPS HAT (B)           | 1        | Department | $34.00          | Pogo pin connection, leaves GPIO header free. Note: budget spreadsheet listed UPS HAT (E) but actual hardware in production is HAT (B). The (B) and (E) are different products. See note below. |
| 18650 Li-ion cells (2-pack)     | 1        | Department | $14.00          | UPS HAT (B) batteries. Amazon. |
| Baseus 65W power bank           | 1        | Personal   | $45.00          | 20000mAh, USB-C PD 3.0. Mobile demo backup. Street price varies $33-55 depending on coupons; $45 is mid-range reference. |

## Display

| Component                       | Quantity | Funding    | Unit Cost (USD) | Notes |
|---------------------------------|----------|------------|-----------------|-------|
| KYY 15.6" portable HDMI monitor | 1        | Department | $66.00          | Live camera feed with YOLO bounding boxes. Amazon. |

## LED Status Indicator

| Component                                    | Quantity | Funding    | Unit Cost (USD) | Notes |
|----------------------------------------------|----------|------------|-----------------|-------|
| Discrete 5mm LEDs (red, yellow, green, blue) | 4        | Inherited  | $9.00           | Sold as multi-color assortment kit (typically 100+ LEDs). Per-LED cost is negligible. Replaced WS2812B after pre-demo failure. |
| Half-size solderless breadboard              | 1        | Inherited  | $5.95           | Adafruit PID 64 reference price. Generics on Amazon $1-3 each. |
| 220 ohm 1/4W resistors                       | 4        | Inherited  | $0.75           | Adafruit 25-pack reference. Per-resistor cost is negligible. |
| 22 AWG hookup wire (multi-color set)         | 1        | Inherited  | $13.99          | TUOFENG/Plusivo 6-color kit on Amazon. |

## USB Infrastructure

| Component                       | Quantity | Funding    | Unit Cost (USD) | Notes |
|---------------------------------|----------|------------|-----------------|-------|
| Official Raspberry Pi USB 3 Hub | 1        | Department | $12.00          | 4-port USB 3.0 hub with captive USB-A upstream cable. Optional USB-C 5V/3A power input. |

## Platform

| Component                       | Quantity | Funding    | Unit Cost (USD) | Notes |
|---------------------------------|----------|------------|-----------------|-------|
| XGRAVITY mini-Jeep (white)      | 1        | Inherited  | --              | Cars4Kids "Gravity" 12V chassis. See platform_specs.md. No US retail SKU. Comparable 12V single-seat ride-on Jeeps run $249-$349 from US retailers (MagicCars, Walmart, Costway). |

## Shipping and Taxes

| Item                            | Cost (USD)  | Notes |
|---------------------------------|-------------|-------|
| Anticipated Shipping + Taxes    | $38.00      | Per original department budget. Covers all spreadsheet items above. |

## Abandoned Components

These components were ordered and tested but did not ship in the final
build. They are listed here for accounting transparency and to spare
future ECE 202 teams from making the same purchases.

| Component                       | Quantity | Funding    | Unit Cost (USD) | Why Abandoned |
|---------------------------------|----------|------------|-----------------|---------------|
| WS2812B addressable LED strip (5V, 60 LED/m, 1m) | 1 | Department | $14.95 | Failed during installation the day before demo. Replaced with discrete LEDs on breadboard. |
| Arducam B0283 PCA9685 servo controller | (included with B0283) | Department | -- | Failed I2C detection on both Pi I2C buses and on Nano R4 I2C bus. Servos run via direct Nano R4 PWM on D9/D10 instead. |
| 74AHCT125 level shifter         | 1        | Personal   | $1.50           | Removed from BOM after Nano R4 confirmed 5V native. Not needed. |

## Cross-Collaboration (Green Jeep)

The green Jeep team uses a separate parts list for their voice-controlled
motor drive variant. The components below are theirs, not Group 35's, and
are listed only for reference since the two builds share infrastructure.

| Component                       | Quantity | Approx Cost (USD) | Notes |
|---------------------------------|----------|-------------------|-------|
| Raspberry Pi 5 (16GB)           | 1        | $205.94           | Separate Pi from IRIS production. |
| Cytron MDD10A motor driver      | 2        | $29.90 each       | Drives the Jeep motors via voice command. Cytron direct. |
| Sony IMX500 AI Camera           | 1        | $70.00            | Same model as IRIS. |

## Cost Summary

### Department-funded (production IRIS build)

| Category                  | Subtotal (USD) |
|---------------------------|----------------|
| Compute                   | $300.94        |
| Vision                    | $105.98        |
| Audio                     | $14.99         |
| Microcontroller           | $13.30         |
| Power                     | $48.00         |
| Display                   | $66.00         |
| USB Infrastructure        | $12.00         |
| Shipping + Taxes          | $38.00         |
| Abandoned (WS2812B strip) | $14.95         |
| Department subtotal       | $614.16        |
| 512GB BIWIN NVMe          | [TBD]          |

### Personally-funded (out of pocket by team members)

| Category                  | Subtotal (USD) |
|---------------------------|----------------|
| Compute (Argon PWR)       | $19.99         |
| Audio (mic, USB adapter)  | $25.98         |
| Microcontroller (cable)   | $5.99          |
| Power (Baseus power bank) | $45.00         |
| Abandoned (74AHCT125)     | $1.50          |
| Personal subtotal         | $98.46         |

### Inherited (no acquisition cost this semester)

Raspberry Pi 5 (8GB), speaker, LEDs and breadboard parts, XGRAVITY chassis.
Reference replacement cost approximately $30-40 for the small parts plus
$249-$349 if a comparable chassis needed to be sourced new.

### Project Total

Department plus Personal totals approximately $712.62 plus the 512GB BIWIN
NVMe drive cost. The original department budget approved at $522.94
covered the seven items on the original spreadsheet plus shipping and
taxes. Actual department spending exceeded that figure once the Arducam
B0283, OSOYOO cable, Waveshare USB Audio, Arduino Nano R4, Pi USB Hub,
and WS2812B strip were added during development. The 512GB BIWIN was a
separate later purchase whose price should be added to this total.

## Notes on the UPS HAT (B) vs (E) Discrepancy

The original budget spreadsheet listed "UPS HAT (E)" at $34, but the
hardware that actually shipped on demo day is UPS HAT (B). These are
different Waveshare products and they are not interchangeable.

UPS HAT (B). Waveshare SKU 20567. Pogo pin connection. 5V/5A output.
Charges from an 8.4V barrel jack. Uses 2 x 18650 Li-ion cells. April 2026
US price approximately $30. This is what shipped.

UPS HAT (E). Newer Waveshare SKU. Pogo pin connection. 5V/6A output.
Charges over USB-C PD up to 40W bidirectional. Uses 4 x 21700 Li-ion
cells. April 2026 US price approximately $45-55.

The $34 paid figure on the spreadsheet is closer to UPS HAT (B) pricing
than to (E) pricing. Most likely the original budget mislabeled the
model number, or substitution happened during purchasing. For the BOM
of record, the deployed hardware is UPS HAT (B) and the cost figure
remains $34 as paid.

## Notes for Future Teams

The Sony IMX500 is the single highest-value Department component in the
build. It is also the most fragile from a software standpoint. Budget
time for IMX500 firmware setup and the Picamera2 quirks documented in
docs/troubleshooting.md.

The wireless K1 lavalier mic was personal hardware acquired specifically
for this project. A wired lavalier or USB conference mic would work fine
and be cheaper. The "K1" model designator is shared across many no-brand
Amazon sellers, so quality varies. Lock by ASIN if your team reorders.

The KYY portable monitor is convenient but not strictly necessary for a
demo if you can mount a small HDMI screen permanently in the Jeep.

The Argon PWR GaN 27W is overkill for the Pi 5 alone but provides
headroom for USB peripherals and prevents undervoltage warnings during
startup. The official Raspberry Pi 27W USB-C supply works equally well
at slightly lower cost.

UPS HAT (B) is the project-correct variant for two reasons: pogo pin
connection leaves the GPIO header free, and 5V/5A is sufficient for the
Pi 5 plus IMX500 plus Arduino plus USB peripherals. UPS HAT (E) adds
USB-C PD charging and 5V/6A output for $15-20 more, useful if your team
expects higher current draw or wants USB-C charging convenience. The C
and D variants block GPIO and conflict with other HATs.
