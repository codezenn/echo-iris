import os
import json
import pyaudio
import requests
import subprocess
import datetime
import time
import signal
import sys
import random
import textwrap

os.environ["PYTHONUNBUFFERED"] = "1"

# ============================================================
#  ECHO IRIS v3.1 -- Demo-Ready Agent
#  Project: ECE 202 | Team: Marc, Obaid, Giovanni
#
#  - Auto-detects USB audio device (no more manual index)
#  - Contextual acknowledgments per answer category
#  - DEMO_MODE bypasses LLM entirely (crash-proof)
#  - Set DEMO_MODE = False for free LLM conversation
# ============================================================

# --- AUTO-DETECT USB AUDIO DEVICE ---
def find_usb_audio():
    """Auto-detect USB audio device index and hw card number."""
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        d = p.get_device_info_by_index(i)
        if "usb" in d["name"].lower() and d["maxInputChannels"] > 0:
            name = d["name"]
            hw_num = "0"
            if "hw:" in name:
                hw_num = name.split("hw:")[1].split(",")[0]
            print(f"  USB Audio found: index={i}, hw={hw_num} ({name})")
            p.terminate()
            return i, hw_num
    print("  WARNING: No USB audio device found, defaulting to 0")
    p.terminate()
    return 0, "0"

MIC_DEVICE_INDEX, USB_HW_NUM = find_usb_audio()

# --- CONFIGURATION ---
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen3.5:2b"
VOSK_MODEL_PATH = "/home/penrose/model"
PIPER_PATH = "/home/penrose/iris_voice/piper/piper"
PIPER_MODEL = "/home/penrose/iris_voice/en_GB-vctk-medium.onnx"
PIPER_SPEAKER = 2
MAX_TOKENS = 60
CHAT_LOG_FILE = "/home/penrose/iris_chat_log.txt"
TERM_WIDTH = 115

WAKE_WORDS = ["hello", "hey", "iris", "hello iris", "hey iris",
              "hi", "high", "aris", "virus", "hi iris"]

LISTEN_TIMEOUT = 12
SILENCE_TIMEOUT = 3.0
OLLAMA_TIMEOUT = 30
DEMO_MODE = True
MIN_WORDS_FOR_ANSWER = 2

# Track recently used acks to avoid repeats
recent_acks = []
MAX_RECENT_ACKS = 4

REPEAT_PHRASES = [
    "Sorry, I did not catch that. Could you say that again?",
    "I missed that. Can you repeat your question?",
    "Could you say that one more time?",
]

REDIRECT_PHRASES = [
    "I am not sure about that one. Try asking me about my goals, my hardware, my AI models, or what I can do!",
    "That is a bit outside my expertise. Ask me about the ECE 202 project, my creators, or my capabilities!",
    "Hmm, I do not have an answer for that. I know a lot about my hardware, my AI models, and what I can do though!",
]

DEFAULT_ACKS = [
    "Sure thing!", "Great question!", "Let me think.", "Good one!",
    "On it!", "Interesting!", "Let me check.", "One moment!",
    "Glad you asked!", "Alright!", "Let me tell you!",
]

GREETING = (
    "Hello, nice to meet you! My name is IRIS, it stands for "
    "Intelligent Raspberry-Pi Imaging System. What would you like to know?"
)

# --- DEMO ANSWERS ---
DEMO_ANSWERS = [
    {
        "name": "software",
        "acks": ["Great question!", "Let me break it down!", "Glad you asked!"],
        "keywords": ["software", "code", "programming", "python", "how does it work",
                     "how do you work", "tech stack", "stack", "language",
                     "vosk", "piper", "whisper", "open wake", "ollama",
                     "how were you made", "how were you built",
                     "how are you built", "what runs you"],
        "answer": (
            "My entire software stack runs on Python. For speech recognition I use Vosk, "
            "which transcribes my audio locally with no internet. My brain for conversation "
            "is llama 3.2, a one billion parameter language model served through Ollama. "
            "For text to speech I use Piper, which gives me my voice. My object detection "
            "runs YOLO 11 nano through the Sony IMX500 camera's built-in neural processor. "
            "Everything is open source and runs completely offline on my Raspberry Pi."
        )
    },
    {
        "name": "ai_models",
        "acks": ["Good question!", "Let me break it down!", "Sure thing!"],
        "keywords": ["model", "models", "ai model", "what model", "running",
                     "llama", "yolo", "program", "brain",
                     "modeled", "motto", "module"],
        "answer": (
            "For this test demo I am using the llama 3.2 one billion parameter model "
            "as my brain for conversation, and for my object detection I use YOLO 11 nano "
            "trained on the COCO dataset. Everything runs locally on my Raspberry Pi 5 "
            "with no cloud needed."
        )
    },
    {
        "name": "goals",
        "acks": ["Great question!", "Glad you asked!", "Sure thing!"],
        "keywords": ["goal", "goals", "project", "ece 202", "ece202", "purpose",
                     "why built", "why made", "plan", "plans", "semester",
                     "mission", "objective", "trying to do", "working on",
                     "her goal", "your goal", "the goal"],
        "answer": (
            "My creators Marc, Obaid, and Giovanni are building me for ECE 202 at "
            "Colorado State University. Their goals are to add voice interactivity to "
            "my object detection capabilities, enable communication between me and the "
            "original IRIS vehicle, and design a 3D printed speaker mount. The bigger "
            "vision is to pave the way for autonomous driving and smart robotics research. "
            "Would you like me to demonstrate what I am capable of?"
        )
    },
    {
        "name": "who_are_you",
        "acks": ["Great question!", "Let me introduce myself!", "Sure thing!"],
        "keywords": ["who are you", "your name", "what are you", "introduce",
                     "about you", "tell me about you", "tell me about yourself",
                     "what is iris", "whats iris",
                     "who is iris", "who iris", "are you"],
        "answer": (
            "I am IRIS, the Intelligent Raspberry-Pi Imaging System. I am an AI-powered "
            "mini-Jeep built by Marc Sibaja, Obaid Almutairi, and Giovanni Guerra for "
            "ECE 202 at Colorado State University. I can detect objects in real time and "
            "have a conversation with you, all running on edge hardware with no internet needed."
        )
    },
    {
        "name": "hardware",
        "acks": ["Let me show you what I am made of!", "Great question!", "Sure thing!"],
        "keywords": ["hardware", "specs", "components", "parts", "built with",
                     "made of", "camera", "power", "battery",
                     "inside", "equipment", "tech"],
        "answer": (
            "I run on a Raspberry Pi 5 with 16 gigabytes of RAM, a Sony IMX500 AI Camera "
            "with a built-in neural processor, and a 256 gigabyte NVMe SSD for fast storage. "
            "I am powered by a Baseus 65 watt power bank with a UPS HAT for backup power, "
            "and I have an active cooler to keep my brain from overheating."
        )
    },
    {
        "name": "creators",
        "acks": ["Let me introduce the team!", "Great question!", "Glad you asked!"],
        "keywords": ["creator", "creators", "who made", "who built", "team",
                     "marc", "obaid", "giovanni", "gio", "teammates",
                     "partners", "members", "group", "crew", "the group",
                     "whos in", "who's in", "who is in", "tell me about the"],
        "answer": (
            "I was built by three ECE 202 students at Colorado State University. "
            "Marc Sibaja is the project lead and built my AI agent and voice system. "
            "Giovanni Guerra designed and 3D printed my custom parts and enclosures. "
            "Obaid Almutairi assembled the Jeep and put all the hardware together. "
            "All three of them are equal contributors to the project."
        )
    },
    {
        "name": "demo",
        "acks": ["I am happy to answer that!", "Let me tell you!", "Sure thing!"],
        "keywords": ["demonstrate", "demo", "show me", "capable", "can you do",
                     "what do you do", "what can you", "abilities", "features",
                     "do you do", "what you do", "function",
                     "what do you", "what you", "what do", "where do you"],
        "answer": (
            "I can detect objects in real time using my camera and tell you what I see, "
            "like people, cars, and animals. I can also have a conversation with you about "
            "the project, my hardware, or anything else you are curious about. Everything "
            "runs locally on my Raspberry Pi with no internet connection needed."
        )
    },
    {
        "name": "yes_continue",
        "acks": ["Absolutely!", "You got it!", "Here we go!", "Of course!"],
        "keywords": ["yes", "yeah", "sure", "okay", "go ahead",
                     "please", "do it", "lets go", "yes please",
                     "yep", "yup", "definitely", "totally",
                     "will squeeze", "we'll squeeze", "squeeze"],
        "answer": (
            "I can detect objects in real time using my Sony IMX500 AI camera. "
            "Right now I can identify over 80 types of objects including people, cars, "
            "dogs, chairs, and even stop signs. Ask me to look around and I will tell "
            "you what I see!"
        )
    },
    {
        "name": "csu",
        "acks": ["Go Rams!", "Great question!", "Glad you asked!"],
        "keywords": ["csu", "colorado state", "university", "school", "campus",
                     "college", "engineering", "ece", "department", "rams"],
        "answer": (
            "I was built at Colorado State University in the Electrical and Computer "
            "Engineering department. My creators Marc, Obaid, and Giovanni built me "
            "as part of their ECE 202 class project to showcase what AI can do on "
            "affordable edge hardware."
        )
    },
    {
        "name": "iris_v1",
        "acks": ["Good question!", "Let me tell you!", "Sure thing!"],
        "keywords": ["original", "first", "version one", "v1", "1.0", "iris one",
                     "last year", "before", "previous", "old one", "green",
                     "other jeep", "other car", "first iris", "iris one"],
        "answer": (
            "IRIS 1.0 was built last year and could do real-time object detection "
            "displayed on a screen mounted on a green Jeep. I am IRIS 2.0, also called "
            "IRIS Echo. I am the upgraded version with voice interaction, a new white Jeep, "
            "and the ability to communicate with the original IRIS vehicle."
        )
    },
    {
        "name": "thanks",
        "acks": ["I appreciate you!", "Glad you enjoyed it!", "That means a lot!"],
        "keywords": ["thank you", "thanks a lot", "thanks so much",
                     "that's cool", "that's awesome", "that's amazing",
                     "that's impressive", "good job", "well done",
                     "nice job", "amazing work", "good job thank",
                     "thank you goodbye", "thank you bye", "thanks"],
        "answer": (
            "Thank you! I love showing off what I can do. If you have any other "
            "questions about my hardware, my AI models, or the ECE 202 project, "
            "feel free to ask!"
        )
    },
    {
        "name": "goodbye",
        "acks": ["Take care!", "Until next time!", "See you later!"],
        "keywords": ["goodbye", "bye bye", "see you later", "that's all",
                     "no more questions", "i'm done", "all done",
                     "bye", "see ya", "later", "gotta go"],
        "answer": (
            "It was great talking to you! I hope you learned a little about what "
            "AI can do on edge hardware. Come say hello anytime!"
        )
    },
]

# --- SYSTEM PROMPT (only used when DEMO_MODE = False) ---
SYSTEM_PROMPT = (
    "Your name is IRIS, the Intelligent Raspberry-Pi Imaging System. "
    "You are an AI-powered mini-Jeep built by Marc Sibaja, Obaid Almutairi, "
    "and Giovanni Guerra for ECE 202 at Colorado State University. "
    "\n"
    "Team roles: Marc is the project lead who built the AI agent and voice system. "
    "Giovanni designed and 3D printed the custom parts and enclosures. "
    "Obaid assembled the Jeep and hardware. All three are equal contributors. "
    "\n"
    "Hardware: Raspberry Pi 5 16GB, Sony IMX500 AI Camera, 256GB NVMe SSD, "
    "KYY 15.6 inch monitor, Baseus 65W power bank, UPS HAT, active cooler. "
    "\n"
    "Software: Python, Vosk (speech recognition), Piper TTS (voice output), "
    "Ollama with llama3.2 1B (conversation), YOLO11n with COCO (object detection). "
    "Everything runs locally and offline. "
    "\n"
    "RULES: Reply in 1-2 sentences MAX. Plain text only, no formatting. "
    "Be friendly and concise. Always credit all three creators by name. "
    "Never invent specs or capabilities. If unsure, say you do not know."
)

MAX_HISTORY = 10
conversation_history = []


def print_wrapped(text, prefix="[IRIS]: "):
    available = TERM_WIDTH - len(prefix)
    lines = textwrap.wrap(text, width=available)
    for i, line in enumerate(lines):
        if i == 0:
            print(f"{prefix}{line}")
        else:
            print(f"{' ' * len(prefix)}{line}")


def log_chat(role, text):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(CHAT_LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {role.upper()}: {text}\n")


def flush_mic(stream):
    """Drain buffered audio by reading and discarding. Never stops the stream."""
    time.sleep(0.3)
    try:
        for _ in range(10):
            avail = stream.get_read_available()
            if avail > 0:
                stream.read(avail, exception_on_overflow=False)
            else:
                break
    except Exception:
        pass


def speak_text(text, stream=None):
    if not text.strip():
        return
    text = text.replace("*", "").replace("#", "")
    try:
        piper_process = subprocess.Popen(
            [PIPER_PATH, "--model", PIPER_MODEL, "--speaker", str(PIPER_SPEAKER), "--output_raw"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        aplay_process = subprocess.Popen(
            ["aplay", "-D", f"plughw:{USB_HW_NUM},0", "-r", "22050", "-f", "S16_LE", "-t", "raw"],
            stdin=piper_process.stdout,
            stderr=subprocess.DEVNULL,
        )
        piper_process.stdin.write(text.encode("utf-8"))
        piper_process.stdin.close()
        piper_process.wait()
        aplay_process.wait()
    except Exception as e:
        print(f"[TTS ERROR] {e}")

    if stream:
        flush_mic(stream)


def get_ack(entry=None):
    """Pick a contextual acknowledgment from the matched entry, avoiding repeats."""
    global recent_acks

    if entry and "acks" in entry:
        choices = entry["acks"]
    else:
        choices = DEFAULT_ACKS

    available = [p for p in choices if p not in recent_acks]
    if not available:
        recent_acks.clear()
        available = choices

    phrase = random.choice(available)
    recent_acks.append(phrase)
    if len(recent_acks) > MAX_RECENT_ACKS:
        recent_acks.pop(0)

    return phrase


def check_demo_answer(user_text):
    lower = user_text.lower()
    for entry in DEMO_ANSWERS:
        for keyword in entry["keywords"]:
            if keyword in lower:
                return entry["answer"], entry
    return None, None


def contains_wake_word(text):
    lower = text.lower()
    for wake in WAKE_WORDS:
        if wake in lower:
            return True
    return False


def query_ollama(user_text, stream):
    """Handle a user question."""

    word_count = len(user_text.split())

    # Step 1: Check demo answers (keyword match)
    demo_answer, demo_entry = check_demo_answer(user_text)

    if demo_answer:
        ack = get_ack(demo_entry)
        print(f"[IRIS]: {ack}")
        speak_text(ack, stream)
        print_wrapped(demo_answer)
        speak_text(demo_answer, stream)
        conversation_history.append({"role": "user", "content": user_text})
        conversation_history.append({"role": "assistant", "content": f"{ack} {demo_answer}"})
        log_chat("user", user_text)
        log_chat("iris (demo)", f"{ack} {demo_answer}")
        return demo_answer

    # Step 2: Too short and no match -- ask to repeat
    if word_count < MIN_WORDS_FOR_ANSWER:
        repeat_msg = random.choice(REPEAT_PHRASES)
        print_wrapped(repeat_msg)
        speak_text(repeat_msg, stream)
        log_chat("user", user_text)
        log_chat("iris", f"(repeat: {repeat_msg})")
        return repeat_msg

    # Step 3: In demo mode, redirect instead of using LLM
    if DEMO_MODE:
        redirect_msg = random.choice(REDIRECT_PHRASES)
        print_wrapped(redirect_msg)
        speak_text(redirect_msg, stream)
        log_chat("user", user_text)
        log_chat("iris (redirect)", redirect_msg)
        return redirect_msg

    # Step 4: Not demo mode -- use LLM (only when DEMO_MODE = False)
    ack = get_ack()
    print(f"[IRIS]: {ack}")
    speak_text(ack, stream)

    conversation_history.append({"role": "user", "content": user_text})
    log_chat("user", user_text)

    if len(conversation_history) > MAX_HISTORY:
        conversation_history[:] = conversation_history[-MAX_HISTORY:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": True,
        "options": {
            "num_predict": MAX_TOKENS,
            "num_thread": 2,
            "temperature": 0.7,
            "top_p": 0.9,
        }
    }

    full_response = ""
    try:
        response = requests.post(OLLAMA_URL, json=payload, stream=True, timeout=OLLAMA_TIMEOUT)
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                token = chunk.get("message", {}).get("content", "")
                if token:
                    token = token.replace("*", "").replace("#", "")
                    full_response += token
                if chunk.get("done", False):
                    break
    except requests.exceptions.Timeout:
        full_response = "Hmm, let me get back to you on that. Could you ask me again?"
    except requests.exceptions.RequestException as e:
        full_response = "Sorry, my brain is not responding right now. Try again."
        print(f"\n[ERROR] Ollama: {e}")

    print_wrapped(full_response)
    speak_text(full_response, stream)
    conversation_history.append({"role": "assistant", "content": full_response})
    log_chat("iris", full_response)
    return full_response


def run_iris():
    print("=" * 42)
    print("  ECHO IRIS v3.1 -- Demo-Ready Agent")
    print("=" * 42)

    if DEMO_MODE:
        print("  [DEMO MODE] LLM disabled, crash-proof")
    else:
        print("  [FULL MODE] LLM enabled for free chat")
    print(f"  Wake words: {', '.join(WAKE_WORDS[:5])}...")

    if not os.path.exists(VOSK_MODEL_PATH):
        print(f"ERROR: Vosk model not found at {VOSK_MODEL_PATH}")
        exit(1)

    from vosk import Model, KaldiRecognizer
    vosk_model = Model(VOSK_MODEL_PATH)
    p = pyaudio.PyAudio()

    try:
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=8000,
            input_device_index=MIC_DEVICE_INDEX,
        )
        stream.start_stream()
    except Exception as e:
        print(f"ERROR: Could not open microphone -- {e}")
        exit(1)

    print(f"\n  Model: {MODEL_NAME} | Max tokens: {MAX_TOKENS}")
    print(f"  Chat log: {CHAT_LOG_FILE}")
    print("\n--- ECHO IRIS PROTOCOL ACTIVE ---")
    print("Say 'hello' or 'iris' to wake me up!\n")

    rec = KaldiRecognizer(vosk_model, 16000)

    while True:
        # === Phase 1: Wait for wake word ===
        data = stream.read(4000, exception_on_overflow=False)

        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text = result.get("text", "").strip()

            if text and contains_wake_word(text):
                # === Phase 2: Greet ===
                print("\n** IRIS ACTIVATED **")
                print_wrapped(GREETING)
                speak_text(GREETING, stream)
                log_chat("system", f"Wake word: {text}")
                log_chat("iris", GREETING)

                # === Phase 3: Conversation loop ===
                conv_rec = KaldiRecognizer(vosk_model, 16000)

                while True:
                    print("\nListening for your question...")
                    last_speech_time = time.time()
                    got_any_speech = False
                    user_text = None

                    while True:
                        elapsed = time.time() - last_speech_time
                        if elapsed > LISTEN_TIMEOUT:
                            break

                        data = stream.read(4000, exception_on_overflow=False)

                        if conv_rec.AcceptWaveform(data):
                            result = json.loads(conv_rec.Result())
                            user_text = result.get("text", "").strip()
                            if user_text:
                                break
                        else:
                            partial = json.loads(conv_rec.PartialResult())
                            if partial.get("partial", ""):
                                got_any_speech = True
                                last_speech_time = time.time()

                    if user_text is None and got_any_speech:
                        final = json.loads(conv_rec.FinalResult())
                        user_text = final.get("text", "").strip()

                    if not user_text:
                        print("(no question heard -- going back to sleep)")
                        speak_text("I will be here if you need me. Just say hello!", stream)
                        print("\nSay 'hello' or 'iris' to wake me up!\n")
                        break

                    if contains_wake_word(user_text) and len(user_text.split()) <= 2:
                        print(f"\n[YOU]: {user_text}")
                        print_wrapped(GREETING)
                        speak_text(GREETING, stream)
                        conv_rec = KaldiRecognizer(vosk_model, 16000)
                        continue

                    print(f"\n[YOU]: {user_text}")
                    query_ollama(user_text, stream)
                    conv_rec = KaldiRecognizer(vosk_model, 16000)

                conversation_history.clear()
                recent_acks.clear()
                rec = KaldiRecognizer(vosk_model, 16000)
                flush_mic(stream)


def main():
    def signal_handler(sig, frame):
        print("\n\nIRIS shutting down. Goodbye!")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    while True:
        try:
            run_iris()
        except KeyboardInterrupt:
            print("\n\nIRIS shutting down. Goodbye!")
            break
        except Exception as e:
            print(f"\n[CRASH] IRIS error: {e}")
            print("[AUTO-RESTART] Restarting in 3 seconds...\n")
            log_chat("system", f"CRASH: {e} -- auto-restarting")
            time.sleep(3)
            conversation_history.clear()


if __name__ == "__main__":
    main()
