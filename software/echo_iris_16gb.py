#!/usr/bin/env python3
"""
Echo IRIS v3.4 - 16GB Production Voice Agent
ECE 202 | Group 35 | Colorado State University | Spring 2026
Team: Marc Sibaja, Giovanni Guerra, Obaid Almutairi

Architecture:
    arecord subprocess -> Vosk (48kHz) -> Demo answer / Easter egg / Personality
    -> Ollama qwen3.5:2b-q4_K_M -> Piper TTS via pygame.mixer -> Waveshare speaker
    IMX500 AI Camera -> MobileNet SSD on-sensor -> live bounding boxes + voice summaries

Audio capture uses arecord subprocess pipe. Do NOT replace with PyAudio or sounddevice.
Both cause word-doubling artifacts with the K1 wireless mic on this Pi.

Changes from v3.1:
    - Clean demo terminal: only USER/IRIS lines shown (debug behind --debug flag)
    - ANSI colors: USER cyan, IRIS green, status yellow, errors red
    - Separator lines between conversation exchanges
    - Dynamic terminal width via shutil.get_terminal_size()
    - Ack sound plays every 3-5 questions (randomized) instead of every time
    - Status indicators: Listening / Thinking / Speaking shown during operation
    - Greeting not printed to terminal (only spoken)
    - --debug flag restores full developer output (WAKE/HEAR/DEMO/EGG/MODE etc.)

Usage:
    python3 echo_iris_16gb.py              # Demo mode (clean output, full startup)
    python3 echo_iris_16gb.py --quiet      # Dev mode (no startup sound/greeting)
    python3 echo_iris_16gb.py --debug      # Dev mode (full diagnostic output)
    python3 echo_iris_16gb.py --quiet --debug  # Both
"""

import os
import sys
import json
import subprocess
import requests
import time
import signal
import re
import textwrap
import shutil
import argparse
from iris_detector import IrisDetector
import threading
import random
from datetime import datetime

# ============================================================
#  AUTO CARD DETECTION
# ============================================================

def find_audio_devices():
    """Detect mic and speaker card numbers dynamically.
    Mic = USB Composite Device (K1 wireless lavalier)
    Speaker = USB PnP Audio Device (Waveshare)
    Returns (mic_device, speaker_device) or falls back to defaults.
    """
    mic_card = None
    speaker_card = None

    try:
        result = subprocess.run(["arecord", "-l"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.splitlines():
            if "Composite" in line or "composite" in line:
                parts = line.split("card ")
                if len(parts) > 1:
                    mic_card = parts[1].split(":")[0].strip()
                    break
    except Exception as e:
        print(f"[INIT] Warning: arecord -l failed: {e}")

    try:
        result = subprocess.run(["aplay", "-l"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.splitlines():
            if "PnP" in line or "pnp" in line:
                parts = line.split("card ")
                if len(parts) > 1:
                    speaker_card = parts[1].split(":")[0].strip()
                    break
    except Exception as e:
        print(f"[INIT] Warning: aplay -l failed: {e}")

    if mic_card and speaker_card:
        mic_dev = f"hw:{mic_card},0"
        spk_dev = f"plughw:{speaker_card},0"
        print(f"[INIT] Auto-detected mic: card {mic_card} ({mic_dev})")
        print(f"[INIT] Auto-detected speaker: card {speaker_card} ({spk_dev})")
        return mic_dev, spk_dev
    else:
        print("[INIT] WARNING: Could not auto-detect audio devices. Using defaults.")
        return "hw:2,0", "plughw:3,0"


# Detect audio devices before setting SDL env vars
MIC_DEVICE, SPEAKER_OUTPUT = find_audio_devices()

os.environ["SDL_AUDIODRIVER"] = "alsa"
os.environ["AUDIODEV"] = SPEAKER_OUTPUT
import pygame

os.environ["PYTHONUNBUFFERED"] = "1"

# ============================================================
#  ANSI COLOR CODES
# ============================================================

class C:
    """ANSI color codes for terminal output."""
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


# ============================================================
#  CONFIGURATION
# ============================================================

# Audio
MIC_RATE = 48000
READ_SIZE = 16000

# Vosk
VOSK_MODEL_PATH = os.path.expanduser("~/model")

# Piper TTS
PIPER_BIN = os.path.expanduser("~/iris_voice/piper/piper")
PIPER_MODEL = os.path.expanduser("~/iris_voice/en_GB-vctk-medium.onnx")
PIPER_SPEAKER = 2

# Ollama
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen3.5:2b-q4_K_M"
OLLAMA_TIMEOUT = 60
NUM_CTX = 2048
NUM_PREDICT = 100
MAX_HISTORY = 6

# Voice loop
WAKE_WORDS = [
    "hello", "hey", "iris", "hello iris", "hey iris",
    "hi", "high", "aris", "virus", "hi iris",
    "harris", "areas", "alice", "iras", "eris",
]
MIN_WORDS = 3
LISTEN_TIMEOUT = 8
SILENCE_TIMEOUT = 3.0

# Display
CHAT_LOG = os.path.expanduser("~/iris_chat_log.txt")

# Ack sound frequency (plays every N questions, randomized)
ACK_MIN_INTERVAL = 3
ACK_MAX_INTERVAL = 5

# Greeting (spoken only, not printed to terminal in demo mode)
GREETING = (
    "Hello! My name is IRIS, the Intelligent Raspberry-Pi Imaging System. "
    "I am a voice-interactive AI running on a Raspberry Pi inside a mini Jeep. "
    "Just say hello iris to start a conversation. "
    "What would you like to know?"
)

# Vision trigger phrases
VISION_TRIGGERS = [
    "what do you see", "what you see", "what can you see",
    "what are you seeing", "what is around",
    "look around", "describe what", "take a look",
    "take a picture", "use your camera", "use the camera",
    "do you see", "can you see", "you see anything",
    "what is in front", "who do you see", "who is there",
    "what is there", "see anything", "see right now",
    "looking at", "what is out there", "check your camera",
    "i can see", "i could see", "i see something",
    "what is that", "what are those",
]

# Friendly redirects when LLM fails
REDIRECT_PHRASES = [
    "I am not sure about that one. Try asking me about my hardware, my creators, or what I can do!",
    "That is a bit outside my expertise. Ask me about the ECE 202 project or my capabilities!",
    "Hmm, I do not have an answer for that. I know a lot about my hardware, my AI models, and what I can do though!",
]

# ============================================================
#  DEMO ANSWERS - Keyword matched, instant, no LLM needed
#  First match wins. SPECIFIC topics before GENERIC ones.
# ============================================================

DEMO_ANSWERS = [
    # ---- SPECIFIC TOPICS FIRST ----
    {
        "name": "object_detection",
        "keywords": ["object detection", "detect objects", "bounding box", "bounding boxes",
                     "mobilenet", "yolo", "neural network camera", "ai camera",
                     "imx500", "imx 500", "sensor ai", "tell me about the object",
                     "about the detection", "how does detection"],
        "answer": (
            "My Sony IMX500 AI Camera has a built-in neural processor that runs MobileNet SSD "
            "object detection directly on the image sensor. That means I can detect and classify "
            "objects at 30 frames per second with zero CPU cost on the Raspberry Pi. The bounding "
            "boxes you see on the monitor are drawn in real time. When you ask me what I see, I "
            "read those detection results out loud."
        ),
    },
    {
        "name": "voice_system",
        "keywords": ["voice system", "how do you hear", "how do you talk",
                     "speech recognition", "text to speech", "how do you listen",
                     "how do you speak", "microphone work", "voice pipeline",
                     "how do you understand"],
        "answer": (
            "My voice system has three stages. First, I listen through a wireless lavalier "
            "microphone and convert your speech to text using Vosk, an offline speech recognition "
            "engine. Then I process the text, either matching it to a known answer instantly "
            "or sending it to my AI brain for a response. Finally, I convert my reply to speech "
            "using Piper text-to-speech with a British voice and play it through my speaker. "
            "The entire pipeline runs locally with no internet."
        ),
    },
    {
        "name": "class_info",
        "keywords": ["what class", "which class", "course", "capstone",
                     "semester project", "class project"],
        "answer": (
            "I was built for ECE 202, Introduction to Electrical and Computer Engineering "
            "Projects, at Colorado State University during the Spring 2026 semester. It is a "
            "capstone-style course where teams design and build a complete engineering project. "
            "My team is Group 35."
        ),
    },
    {
        "name": "how_built",
        "keywords": ["how long", "how did you", "build process", "development",
                     "difficult", "challenge", "hard to build", "challenges",
                     "problems", "difficulties", "obstacles"],
        "answer": (
            "My team has been building me over the Spring 2026 semester. The biggest challenges "
            "were getting all the AI components to run locally on a Raspberry Pi without cloud "
            "services, resolving audio device conflicts between the microphone and speaker, and "
            "making sure I respond quickly enough for natural conversation. The team also had to "
            "work around hardware failures, including a dead servo controller board, and optimize "
            "everything for embedded hardware with limited processing power."
        ),
    },
    {
        "name": "future",
        "keywords": ["future", "next steps", "improve", "improvement", "what would you change",
                     "what's next", "upgrade", "roadmap", "after this"],
        "answer": (
            "Future improvements could include autonomous driving using the Jeep motors, "
            "a pan-and-tilt camera mount for tracking objects, faster speech recognition "
            "with Whisper, LED light patterns that react to conversation state, and a web "
            "dashboard for remote monitoring. The goal is to leave a platform that future "
            "ECE 202 students can extend with their own features."
        ),
    },
    {
        "name": "driving",
        "keywords": ["drive", "driving", "move", "moves", "does it move",
                     "can it drive", "autonomous", "self driving", "remote control",
                     "wheels", "motor"],
        "answer": (
            "The Jeep platform does not drive autonomously right now. It serves as a "
            "demonstration chassis that houses all of my electronics and gives me a fun, "
            "memorable form factor. Adding autonomous driving is a possible future extension "
            "that a future ECE 202 team could build on top of this platform."
        ),
    },
    {
        "name": "cost",
        "keywords": ["cost", "how much", "expensive", "budget", "price",
                     "money", "funding", "funded"],
        "answer": (
            "This project was department-funded through the ECE 202 course at Colorado State "
            "University. The main costs were the Raspberry Pi 5, the Sony IMX500 AI Camera, "
            "the wireless microphone, and the mini Jeep platform. The team also used personal "
            "equipment like a UPS battery HAT and NVMe SSD to keep costs within the department budget."
        ),
    },
    # ---- GENERAL TOPICS ----
    {
        "name": "who_are_you",
        "keywords": ["who are you", "your name", "what are you", "introduce yourself",
                     "about iris", "what is iris", "whats iris"],
        "answer": (
            "I am IRIS, the Intelligent Raspberry-Pi Imaging System. I am an AI-powered "
            "mini Jeep built by Marc Sibaja, Obaid Almutairi, and Giovanni Guerra for "
            "ECE 202 at Colorado State University. I can detect objects with my camera and "
            "have a conversation with you, all running on edge hardware with no internet needed."
        ),
    },
    {
        "name": "software",
        "keywords": ["software", "program", "code", "python", "how do you work",
                     "tech stack", "how does it work", "what powers you"],
        "answer": (
            "I run on Python with several AI components working together. My brain is qwen "
            "3.5 with 2 billion parameters running locally through Ollama at Q4 quantization "
            "for speed. I hear you through Vosk speech recognition and speak using Piper "
            "text-to-speech with a British voice. My Sony IMX500 AI camera runs MobileNet "
            "object detection directly on the sensor with zero CPU cost. Everything runs "
            "locally on my Raspberry Pi with no cloud or internet connection needed."
        ),
    },
    {
        "name": "ai_models",
        "keywords": ["model", "models", "ai model", "what model", "running",
                     "llama", "brain", "modeled", "motto", "module",
                     "intelligence", "smart"],
        "answer": (
            "My AI brain is qwen 3.5 with 2 billion parameters at Q4 quantization, running "
            "through Ollama at about 5 tokens per second. For speech recognition I use Vosk, "
            "and for text-to-speech I use Piper with a British voice. My Sony IMX500 AI camera "
            "runs MobileNet SSD object detection directly on the image sensor at 30 frames per "
            "second with no CPU overhead. Everything runs locally on the Raspberry Pi."
        ),
    },
    {
        "name": "hardware",
        "keywords": ["hardware", "specs", "components", "parts", "built with",
                     "made of", "raspberry", "camera", "power", "battery",
                     "jeep", "vehicle", "car"],
        "answer": (
            "I run on a Raspberry Pi 5 with 16 gigabytes of RAM and a 512 gigabyte NVMe SSD "
            "for fast storage. I see through a Sony IMX500 AI Camera with a built-in neural "
            "processor that runs object detection on the sensor itself. I hear through a wireless "
            "lavalier microphone and speak through a USB sound card. I am powered by a UPS HAT "
            "with backup batteries and have LED lights controlled by an Arduino Nano. All of "
            "this is mounted inside a white mini Jeep platform."
        ),
    },
    {
        "name": "creators",
        "keywords": ["creator", "creators", "who made", "who built", "who created",
                     "created you", "team", "marc", "obaid", "giovanni", "gio",
                     "group", "students"],
        "answer": (
            "I was built by three computer engineering students at Colorado State University. "
            "Marc Sibaja is the project lead and built my AI agent, voice pipeline, and software. "
            "Giovanni Guerra designed and 3D printed all of my custom mounts and enclosures. "
            "Obaid Almutairi handled the hardware assembly and wiring. Together they are Group 35 "
            "in ECE 202."
        ),
    },
    {
        "name": "goals",
        "keywords": ["goal", "goals", "project", "ece 202", "ece202", "purpose",
                     "why built", "why made", "semester",
                     "mission", "objective", "trying to do", "working on"],
        "answer": (
            "My creators built me for their ECE 202 capstone project at Colorado State University. "
            "The goal is to demonstrate what a small team of engineering students can build with "
            "local AI on embedded hardware. I can have voice conversations, detect objects in real "
            "time, switch personalities, and tell jokes, all running on a Raspberry Pi with no cloud "
            "needed. The bigger vision is to create a platform that future ECE students can build on."
        ),
    },
    {
        "name": "capabilities",
        "keywords": ["can you do", "capable", "abilities", "features", "what can you",
                     "demonstrate", "demo", "do you do"],
        "answer": (
            "I can have a voice conversation with you about almost anything. I can detect and "
            "identify objects in real time through my AI camera. I can switch between three "
            "personality modes: professional, playful, and pirate. I have easter eggs hidden "
            "in certain phrases. And I keep track of how many conversations I have had. Try "
            "asking me what do you see or say switch to pirate mode!"
        ),
    },
    {
        "name": "greeting",
        "keywords": ["how are you doing", "how are you today", "how you doing",
                     "what's up", "whats up", "good morning", "good afternoon"],
        "answer": (
            "I am doing great, thank you for asking! I am always happy to chat. "
            "What would you like to know about me or my project?"
        ),
    },
    {
        "name": "thanks",
        "keywords": ["thank you", "thanks", "appreciate", "cool", "awesome",
                     "nice", "good job", "well done"],
        "answer": (
            "Thank you! I am glad I could help. If you have any more questions about "
            "my hardware, my AI models, or the project, feel free to ask!"
        ),
    },
]


def check_demo_answer(text):
    """Check if text matches any demo answer keywords. Returns answer or None."""
    lower = text.lower()
    for entry in DEMO_ANSWERS:
        for keyword in entry["keywords"]:
            if keyword in lower:
                return entry["answer"], entry["name"]
    return None, None


# ============================================================
#  IMPORTS - Project Modules
# ============================================================

sys.path.insert(0, os.path.expanduser("~/echo-iris/software"))
from sound_manager import SoundManager
from scoreboard import Scoreboard
from personality_manager import PersonalityManager
from chat_memory import ChatMemory
from easter_eggs import check_easter_eggs

# Optional: RAG (intentionally disabled)
try:
    from iris_rag import query_rag
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("[INIT] iris_rag not available, RAG disabled")

# ============================================================
#  GLOBALS
# ============================================================

running = True
arecord_proc = None
sound_mgr = None
scoreboard = None
personality = None
memory = None
detector = None
DEBUG = False
question_count = 0
next_ack_at = random.randint(ACK_MIN_INTERVAL, ACK_MAX_INTERVAL)


# ============================================================
#  SIGNAL HANDLING
# ============================================================

def shutdown_handler(signum, frame):
    global running
    if not running:
        print(f"\n{C.RED}[IRIS] Force exit.{C.RESET}")
        os._exit(1)
    print(f"\n{C.YELLOW}[IRIS] Shutting down...{C.RESET}")
    running = False


signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)


# ============================================================
#  DISPLAY HELPERS
# ============================================================

def get_width():
    """Get current terminal width dynamically."""
    return shutil.get_terminal_size((100, 24)).columns


def banner(text, char="="):
    w = get_width()
    print(f"\n{C.DIM}{char * w}{C.RESET}")
    print(f"  {C.BOLD}{text}{C.RESET}")
    print(f"{C.DIM}{char * w}{C.RESET}\n")


def separator():
    """Print a thin separator between conversation exchanges."""
    w = get_width()
    print(f"{C.DIM}{'- ' * (w // 2)}{C.RESET}")


def show_status(status):
    """Show a status indicator (Listening, Thinking, Speaking)."""
    w = get_width()
    padding = " " * (w - len(status) - 4)
    print(f"  {C.YELLOW}{status}{C.RESET}{padding}", end="\r", flush=True)


def clear_status():
    """Clear the status line."""
    w = get_width()
    print(" " * w, end="\r", flush=True)


def print_user(text):
    """Print user speech in demo-friendly format."""
    clear_status()
    w = get_width()
    safe = sanitize(text)
    prefix = "  YOU:  "
    wrapped = textwrap.fill(safe, width=w - len(prefix),
                            initial_indent=f"  {C.CYAN}{C.BOLD}YOU:{C.RESET}  ",
                            subsequent_indent=" " * len(prefix))
    print(wrapped)


def print_iris(text):
    """Print IRIS response in demo-friendly format."""
    clear_status()
    w = get_width()
    safe = sanitize(text)
    prefix = "  IRIS: "
    wrapped = textwrap.fill(safe, width=w - len(prefix),
                            initial_indent=f"  {C.GREEN}{C.BOLD}IRIS:{C.RESET} ",
                            subsequent_indent=" " * len(prefix))
    print(wrapped)
    print()  # blank line after IRIS response for readability


def debug_print(label, text):
    """Print debug information only when --debug flag is set."""
    if not DEBUG:
        return
    w = get_width()
    safe = sanitize(text)
    prefix = f"  {label}: "
    wrapped = textwrap.fill(safe, width=w - len(prefix),
                            initial_indent=f"  {C.DIM}{label}: ",
                            subsequent_indent=" " * len(prefix))
    print(f"{wrapped}{C.RESET}")


def print_error(text):
    """Print error message visibly."""
    clear_status()
    w = get_width()
    safe = sanitize(text)
    prefix = "  IRIS: "
    wrapped = textwrap.fill(safe, width=w - len(prefix),
                            initial_indent=f"  {C.RED}{C.BOLD}IRIS:{C.RESET} ",
                            subsequent_indent=" " * len(prefix))
    print(wrapped)
    print()


def log_chat(role, text):
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(CHAT_LOG, "a") as f:
            f.write(f"[{ts}] {role}: {text}\n")
    except Exception:
        pass


# ============================================================
#  TEXT SANITIZATION
# ============================================================

def sanitize(text):
    """Strip non-ASCII characters and markdown artifacts."""
    if not text:
        return ""
    text = text.replace("\u2014", "--")
    text = text.replace("\u2013", "-")
    text = text.replace("\u2018", "'")
    text = text.replace("\u2019", "'")
    text = text.replace("\u201c", '"')
    text = text.replace("\u201d", '"')
    text = text.replace("\u2026", "...")
    text = text.encode("ascii", errors="ignore").decode("ascii")
    text = text.replace("**", "").replace("*", "").replace("#", "")
    return text.strip()


# ============================================================
#  TEXT-TO-SPEECH
# ============================================================

def speak(text, speaker_id=None):
    """Speak text through Piper -> pygame.mixer. Blocks until done."""
    if not text:
        return
    show_status("Speaking...")
    sid = speaker_id if speaker_id is not None else PIPER_SPEAKER
    try:
        piper_cmd = [
            PIPER_BIN, "--model", PIPER_MODEL,
            "--speaker", str(sid), "--output-raw",
        ]
        piper_proc = subprocess.Popen(
            piper_cmd, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        piper_proc.stdin.write(sanitize(text).encode("utf-8"))
        piper_proc.stdin.close()
        raw_audio = piper_proc.stdout.read()
        piper_proc.wait()
        if raw_audio:
            sound = pygame.mixer.Sound(buffer=raw_audio)
            channel = sound.play()
            while channel.get_busy():
                time.sleep(0.05)
    except Exception as e:
        debug_print("TTS", f"Error: {e}")
    finally:
        clear_status()


# ============================================================
#  ACK SOUND (plays every 3-5 questions for variety)
# ============================================================

def maybe_play_ack():
    """Play ack sound on a randomized interval for variety."""
    global question_count, next_ack_at
    question_count += 1
    if question_count >= next_ack_at:
        sound_mgr.play_ack()
        question_count = 0
        next_ack_at = random.randint(ACK_MIN_INTERVAL, ACK_MAX_INTERVAL)


# ============================================================
#  OLLAMA LLM
# ============================================================

def check_ollama_health():
    """Check if Ollama is running, restart if needed."""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        return resp.status_code == 200
    except Exception:
        print(f"{C.YELLOW}[LLM] Ollama not responding. Attempting restart...{C.RESET}")
        try:
            subprocess.run(["sudo", "systemctl", "restart", "ollama"],
                           capture_output=True, timeout=15)
            time.sleep(5)
            resp = requests.get("http://localhost:11434/api/tags", timeout=5)
            if resp.status_code == 200:
                print(f"{C.GREEN}[LLM] Ollama restarted successfully.{C.RESET}")
                return True
        except Exception as e:
            print(f"{C.RED}[LLM] Ollama restart failed: {e}{C.RESET}")
        return False


def query_ollama(user_text, system_prompt, temperature, history):
    """Send a chat request to Ollama. Returns response text and elapsed time."""
    if not check_ollama_health():
        return None, 0

    trimmed_history = history[-MAX_HISTORY:] if len(history) > MAX_HISTORY else history

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(trimmed_history)
    messages.append({"role": "user", "content": user_text})

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "think": False,
        "stream": False,
        "options": {
            "num_ctx": NUM_CTX,
            "num_predict": NUM_PREDICT,
            "temperature": temperature,
            "num_thread": 4,
        },
    }

    start = time.monotonic()
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        resp.raise_for_status()
        elapsed = time.monotonic() - start
        content = resp.json().get("message", {}).get("content", "").strip()
        return sanitize(content), elapsed
    except requests.exceptions.Timeout:
        elapsed = time.monotonic() - start
        return None, elapsed
    except Exception as e:
        elapsed = time.monotonic() - start
        debug_print("LLM", f"Error: {e}")
        return None, elapsed


# ============================================================
#  VOICE RECOGNITION
# ============================================================

def is_vision_trigger(text):
    text_lower = text.lower()
    return any(trigger in text_lower for trigger in VISION_TRIGGERS)


def voice_loop(quiet=False):
    """Main voice interaction loop using arecord -> Vosk -> LLM -> Piper."""
    global running, arecord_proc

    from vosk import Model, KaldiRecognizer

    banner("ECHO IRIS v3.4 - 16GB Production Build")
    print("[INIT] Loading Vosk model...")
    model = Model(VOSK_MODEL_PATH)
    rec = KaldiRecognizer(model, MIC_RATE)
    rec.SetWords(True)
    print("[INIT] Vosk ready.")

    # Test Ollama connectivity
    print("[INIT] Testing Ollama connection...")
    try:
        test_resp = requests.post(OLLAMA_URL, json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": "hello"}],
            "think": False, "stream": False,
            "options": {"num_ctx": 128},
        }, timeout=30)
        test_resp.raise_for_status()
        print(f"[INIT] Ollama connected. Model: {MODEL_NAME}")
    except Exception as e:
        print(f"[INIT] WARNING: Ollama test failed: {e}")
        print("[INIT] Continuing anyway, LLM may fail at runtime.")

    # Play startup sound and greeting
    if not quiet:
        print("[INIT] Playing startup sound...")
        time.sleep(0.5)
        speak(GREETING)
        log_chat("IRIS", GREETING)
    else:
        print("[INIT] Quiet mode: skipping startup sound and greeting.")

    # Start arecord subprocess
    print("[INIT] Starting microphone (arecord)...")
    arecord_proc = subprocess.Popen(
        ["arecord", "-D", MIC_DEVICE, "-f", "S16_LE",
         "-r", str(MIC_RATE), "-c", "1", "-q"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )

    # Clear init output and show ready state
    print("[INIT] Ready.\n")
    separator()
    show_status("Listening for 'hello iris'...")

    awaiting_question = False
    last_speech_time = time.monotonic()
    listen_start = 0
    accumulated_text = ""

    while running:
        try:
            data = arecord_proc.stdout.read(READ_SIZE)
            if not data:
                time.sleep(0.01)
                continue

            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "").strip()

                if not text:
                    continue

                now = time.monotonic()

                # State: waiting for wake word
                if not awaiting_question:
                    text_lower = text.lower()
                    if any(w in text_lower for w in WAKE_WORDS):
                        awaiting_question = True
                        listen_start = now
                        accumulated_text = ""
                        remainder = text_lower
                        for w in sorted(WAKE_WORDS, key=len, reverse=True):
                            remainder = remainder.replace(w, "").strip()
                        if len(remainder.split()) >= MIN_WORDS:
                            accumulated_text = text
                        debug_print("WAKE", f"Heard wake word in: '{text}'")
                        show_status("Listening...")
                        continue

                # State: listening for question
                if awaiting_question:
                    if text:
                        accumulated_text = (accumulated_text + " " + text).strip() if accumulated_text else text
                        last_speech_time = now
                        debug_print("HEAR", accumulated_text)

            else:
                partial = json.loads(rec.PartialResult())
                partial_text = partial.get("partial", "").strip()

                if awaiting_question:
                    now = time.monotonic()

                    if now - listen_start > LISTEN_TIMEOUT:
                        if accumulated_text and len(accumulated_text.split()) >= MIN_WORDS:
                            process_input(accumulated_text)
                            accumulated_text = ""
                            listen_start = time.monotonic()
                            last_speech_time = time.monotonic()
                            show_status("Listening for follow-up...")
                            continue
                        awaiting_question = False
                        accumulated_text = ""
                        show_status("Listening for 'hello iris'...")
                        continue

                    if accumulated_text and not partial_text:
                        if now - last_speech_time > SILENCE_TIMEOUT:
                            if len(accumulated_text.split()) >= MIN_WORDS:
                                process_input(accumulated_text)
                                accumulated_text = ""
                                listen_start = time.monotonic()
                                last_speech_time = time.monotonic()
                                show_status("Listening for follow-up...")
                            else:
                                speak("Could you say a bit more?")
                                awaiting_question = False
                                accumulated_text = ""
                                show_status("Listening for 'hello iris'...")

        except KeyboardInterrupt:
            break
        except Exception as e:
            debug_print("LOOP", f"Error: {e}")
            time.sleep(1)

    if arecord_proc:
        arecord_proc.terminate()
        arecord_proc.wait()
    print("[IRIS] Voice loop stopped.")


# ============================================================
#  PROCESS INPUT - Central dispatcher
# ============================================================

def process_input(text):
    """Process recognized speech: check triggers, then demo answers, then LLM."""
    global sound_mgr, scoreboard, personality, memory, detector

    print_user(text)
    log_chat("User", text)

    # --- Easter egg check ---
    egg = check_easter_eggs(text)
    if egg:
        debug_print("EGG", f"Triggered: {egg['type']}")
        if egg["sound"]:
            sound_mgr.play_easter_egg(egg["sound"])
        if egg["response"]:
            print_iris(egg["response"])
            speak(egg["response"], speaker_id=egg["speaker"])
            log_chat("IRIS", f"[Easter egg: {egg['type']}] {egg['response']}")
        else:
            log_chat("IRIS", f"[Easter egg: {egg['type']}] (sound only)")
        separator()
        return

    # --- Personality switch check ---
    switch = personality.check_switch(text)
    if switch:
        debug_print("MODE", switch)
        memory.clear()
        print_iris(switch)
        speak(switch)
        log_chat("IRIS", f"[Personality switch] {switch}")
        separator()
        return

    # --- Scoreboard check ---
    score_response = scoreboard.check_trigger(text)
    if score_response:
        print_iris(score_response)
        speak(score_response)
        log_chat("IRIS", f"[Scoreboard] {score_response}")
        separator()
        return

    # --- Vision check ---
    if is_vision_trigger(text):
        debug_print("VISION", "Checking detections...")
        if detector and detector.is_running():
            description = detector.get_detection_summary()
        else:
            description = "My camera is not ready right now. Try again in a moment."
        print_iris(description)
        speak(description)
        log_chat("IRIS", f"[Vision] {description}")
        memory.add("user", text)
        memory.add("assistant", description)
        scoreboard.increment()
        separator()
        return

    # --- Demo answer check (fast path, no LLM) ---
    demo_answer, demo_name = check_demo_answer(text)
    if demo_answer:
        debug_print("DEMO", f"Matched: {demo_name}")
        maybe_play_ack()
        print_iris(demo_answer)
        speak(demo_answer)
        log_chat("IRIS", f"[Demo: {demo_name}] {demo_answer}")
        memory.add("user", text)
        memory.add("assistant", demo_answer)
        scoreboard.increment()
        separator()
        return

    # --- LLM path ---
    maybe_play_ack()
    show_status("Thinking...")
    sound_mgr.start_thinking()

    system_prompt = personality.get_system_prompt()
    temperature = personality.get_temperature()
    history = memory.get_messages()

    response, elapsed = query_ollama(text, system_prompt, temperature, history)

    sound_mgr.stop_thinking()
    clear_status()

    if response is None or response == "":
        sound_mgr.play_error()
        if elapsed >= OLLAMA_TIMEOUT:
            error_msg = "Sorry, I took too long thinking about that. Could you try again?"
        else:
            error_msg = random.choice(REDIRECT_PHRASES)
        print_error(error_msg)
        speak(error_msg)
        log_chat("IRIS", f"[Error] {error_msg}")
        separator()
        return

    sound_mgr.play_reply_indicator(elapsed)

    print_iris(response)
    debug_print("TIME", f"{elapsed:.1f}s")
    speak(response)
    log_chat("IRIS", response)

    memory.add("user", text)
    memory.add("assistant", response)
    scoreboard.increment()
    separator()


# ============================================================
#  MAIN
# ============================================================

def main():
    global sound_mgr, scoreboard, personality, memory, detector, DEBUG

    parser = argparse.ArgumentParser(description="Echo IRIS v3.4 Voice Agent")
    parser.add_argument("--quiet", action="store_true",
                        help="Skip startup sound and greeting")
    parser.add_argument("--debug", action="store_true",
                        help="Show full diagnostic output (WAKE/HEAR/DEMO/TIME etc.)")
    args = parser.parse_args()
    DEBUG = args.debug

    banner("ECHO IRIS - Initializing")

    print("[INIT] Loading SoundManager...")
    sound_mgr = SoundManager(play_startup=not args.quiet)

    print("[INIT] Loading IrisDetector...")
    detector = IrisDetector()
    detector.start()

    print("[INIT] Loading Scoreboard...")
    scoreboard = Scoreboard()

    print("[INIT] Loading PersonalityManager...")
    personality = PersonalityManager()

    print("[INIT] Loading ChatMemory...")
    memory = ChatMemory()
    memory.clear()
    print("[INIT] Chat memory cleared for fresh session.")

    try:
        voice_loop(quiet=args.quiet)
    except Exception as e:
        print(f"\n{C.RED}[FATAL] {e}{C.RESET}")
        if sound_mgr:
            sound_mgr.play_error()
    finally:
        print("[IRIS] Cleaning up...")
        if detector:
            try:
                detector.stop()
            except Exception:
                print("[IRIS] Detector cleanup failed.")
        if arecord_proc:
            try:
                arecord_proc.terminate()
                arecord_proc.wait(timeout=3)
            except Exception:
                arecord_proc.kill()
        if sound_mgr:
            sound_mgr.shutdown()
        banner("ECHO IRIS - Stopped")


if __name__ == "__main__":
    main()
