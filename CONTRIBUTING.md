# Contributing to Echo IRIS

Echo IRIS is the end of semester deliverable for ECE 202 Group 35 at
Colorado State University, Spring 2026. The project is not under active
development. The repository is published as a permanent reference for
future ECE 202 teams, the open source community, and CSU department
recruiting.

The original team will respond to issues and pull requests on a
best effort basis through the summer of 2026 and may go quiet after that.
This document is for anyone picking up the codebase after that point.

## For Future ECE 202 Teams

If you are inheriting this project as the next generation of Group 35,
welcome. The codebase is yours. Fork the repository, rename the fork to
match your team identifier, and treat this version as your starting line.

Read these files in order before changing anything:

`README.md` for the high-level system overview.

`CHANGELOG.md` for what shipped at v1.0.0 and what was deferred. The
deferred work section is the natural list of features your team can take on.

`docs/architecture.md` for the module walkthrough and the design decisions
that shaped the system. The "Future Work" section calls out the known
weak points and the most likely paths to improvement.

`docs/troubleshooting.md` for the gotchas that took the original team time
to solve. Audio device card swaps on reboot, the IMX500 firmware lock that
needs a full USB C power cycle, the Bookworm latin-1 locale crash, and the
charge only USB cable trap on the Arduino Nano R4 are all documented.

`docs/setup_guide_16gb.md` for the from scratch Pi rebuild procedure. If
you are starting on fresh hardware, this is your sequence of operations.

`hardware/BOM.md` for the parts list with funding sources. Several
components (the WS2812B LED strip, the PCA9685 servo controller) were
abandoned and the BOM documents why.

The most valuable extensions Group 35 left for you. Voice announced YOLO
detections (the detection runs continuously today but IRIS does not narrate
what it sees unless asked). V2V communication via MQTT between the white
IRIS Jeep and the green Jeep. Autonomous lane following or
obstacle avoidance using the existing motor driver pattern from the green
Jeep team. A faster text-only LLM swap (gemma3:1b was researched but not
benchmarked).

If you have questions the documentation does not answer, open a GitHub
issue. Marc, Giovanni, and Obaid will respond when they can.

## For Open Source Forkers

If you are forking Echo IRIS for your own project (educational, hobby,
research), a few notes.

The codebase is MIT licensed (see `LICENSE`). One runtime dependency
(Ultralytics YOLO11) is AGPL-3.0, which has implications if you
redistribute the combined system. See `ATTRIBUTIONS.md` for the full
explanation.

The architecture is opinionated for a Raspberry Pi 5 with specific
peripherals (Sony IMX500 camera, Waveshare USB audio, K1 lavalier mic,
Arduino Nano R4). Porting to different hardware is straightforward but
not trivial. Audio device handling in particular assumes the
mic and speaker split visible in `find_usb_audio()` and requires
verification on your hardware.

The voice loop assumes a wake word + listen window model. If you want
continuous always on listening, the loop in `echo_iris_16gb.py` needs a
substantial rewrite.

The DEMO_ANSWERS keyword fast path is project specific. You will want to
replace its content for your own use case but can keep the pattern.

## Coding Conventions

The original team did not enforce strict style. The codebase reflects that
and follows Python defaults more than any explicit guide. If you are
adding code, the patterns below are what the existing modules follow.

Module imports go at the top of the file, grouped as standard library,
then third party, then project local. The project local block uses
`sys.path.insert` to add `~/echo-iris/software` so modules find each other
without a package install.

Configuration constants live near the top of each module in `UPPER_SNAKE`,
with a comment block above describing what may be tuned safely.

Audio settings (frame sizes, sample rates, device names) are hard coded
constants rather than runtime arguments. Changing them requires editing
the script. This is intentional. The original team learned which values
worked through painful trial and error and pinning them in source prevents
accidental regressions.

Function and method names use `snake_case`. Class names use `PascalCase`.
Module names use `snake_case` and match what they hold (`sound_manager.py`
exports `SoundManager`).

LLM output and any string headed for `print()` or `speak()` passes through
the `sanitize()` function in `echo_iris_16gb.py`. The Pi terminal uses
latin-1 encoding by default and any non-ASCII character (em dash, smart
quote, emoji) crashes the script. Sanitize is defense in depth and is
applied at multiple points.

Error handling favors graceful degradation over crashes. If the LLM times
out, IRIS picks a redirect phrase and continues. If `rpicam-still` fails,
the vision query returns a friendly error string. The `run.sh` wrapper
auto-restarts the agent on any uncaught exception, so even hard failures
are recoverable mid-demo.

Comments are sparse. The project favors descriptive variable and function
names over inline explanation. Where comments do appear, they explain
"why" rather than "what" (for example, why `frames_per_buffer` is locked
at 8000 in the 8GB build).

The chat memory pattern uses an atomic write (write to a temp file, then
rename) to prevent partial write corruption if the script crashes
mid update. New persistent state should follow the same pattern.

## Pull Request Etiquette

If you submit a pull request to this repository.

Open an issue first so the original team knows what you are working on
and can give feedback before you invest effort.

Keep changes focused. One feature or one bug fix per PR.

Update `CHANGELOG.md` with an entry under a new version heading describing
what your change does. Follow the Keep a Changelog 1.1.0 format already in
use.

If your change adds a new runtime dependency, update `ATTRIBUTIONS.md` and
`requirements.txt` accordingly. Verify the dependency's license is
compatible.

If your change modifies hardware behavior, update the relevant document in
`hardware/` and `docs/`.

The original team will review when they can. Do not expect immediate
turnaround. If a month passes with no response, you are welcome to fork
and continue independently.

## Reporting Issues

Open issues for bugs, documentation errors, or unclear setup steps. Be
specific about your hardware (Pi model and RAM, camera, audio devices,
power supply) since many problems are platform dependent.

For demo day related questions, the demo day script in
`docs/demo_day_script.md` captures what actually happened including the
failures. That document may already answer your question.

## Maintainers

Marc S., Giovanni G., Obaid A.

ECE 202 | Colorado State University | Spring 2026
