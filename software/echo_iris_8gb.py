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
#  ECHO IRIS v3.2 -- 8GB Edition with RAG
#  Project: ECE 202 | Team: Marc, Obaid, Giovanni
#  Colorado State University | Spring 2026
#
#  Optimized for Raspberry Pi 5 (8GB RAM)
#  DEMO_MODE = True  | RAG enabled | Small Vosk model
#  Upgrade path: see echo_iris_16gb.py for larger model
#
#  Answer flow:
#    1. Keyword match  → instant scripted answer
#    2. RAG lookup     → nomic-embed-text + qwen3.5:0.8b
#    3. Low confidence → redirect phrase
# ============================================================

# --- DYNAMIC PATHS (works on any machine) ---
HOME            = os.path.expanduser("~")
VOSK_MODEL_PATH = os.path.join(HOME, "model")
PIPER_PATH      = os.path.join(HOME, "iris_voice", "piper", "piper")
PIPER_MODEL     = os.path.join(HOME, "iris_voice", "en_GB-vctk-medium.onnx")
CHAT_LOG_FILE   = os.path.join(HOME, "iris_chat_log.txt")

# --- AUTO-DETECT USB AUDIO DEVICE ---
def find_usb_audio():
    """Auto-detect USB mic and USB speaker separately."""
    p = pyaudio.PyAudio()
    mic_index = None
    mic_name = ""
    spk_hw = "0"
    spk_name = ""
    for i in range(p.get_device_count()):
        d = p.get_device_info_by_index(i)
        name = d["name"].lower()
        if "usb" not in name:
            continue
        if "composite" in name and d["maxInputChannels"] > 0:
            mic_index = i
            mic_name = d["name"]
        elif "pnp" in name:
            if d["maxInputChannels"] > 0 and mic_index is None:
                mic_index = i
                mic_name = d["name"]
            hw = "0"
            if "hw:" in d["name"]:
                hw = d["name"].split("hw:")[1].split(",")[0]
            spk_hw = hw
            spk_name = d["name"]
    if mic_index is None:
        for i in range(p.get_device_count()):
            d = p.get_device_info_by_index(i)
            if "usb" in d["name"].lower() and d["maxInputChannels"] > 0:
                mic_index = i
                mic_name = d["name"]
                break
    if mic_index is None:
        mic_index = 0
    print(f"  Mic: index={mic_index} ({mic_name})")
    print(f"  Speaker: hw={spk_hw} ({spk_name})")
    p.terminate()
    return mic_index, spk_hw
MIC_DEVICE_INDEX, USB_HW_NUM = find_usb_audio()

# --- CONFIGURATION ---
OLLAMA_URL           = "http://localhost:11434/api/chat"
MODEL_NAME           = "qwen3:0.6b"
PIPER_SPEAKER        = 2
MAX_TOKENS           = 60
TERM_WIDTH           = 115
LISTEN_TIMEOUT       = 12
SILENCE_TIMEOUT      = 3.0
OLLAMA_TIMEOUT       = 30
MIN_WORDS_FOR_ANSWER = 2
RAG_ENABLED          = True
WAKE_WORDS = ["hello", "hey", "iris", "hello iris", "hey iris",
              "hi", "high", "aris", "virus", "hi iris"]

# --- RAG SETUP ---
rag = None

def init_rag():
    """Initialize RAG module. Fails silently if unavailable."""
    global rag
    try:
        from iris_rag import IRISRag
        rag = IRISRag()
        rag.load()
        print("  RAG: Ready")
    except Exception as e:
        print(f"  RAG: Disabled ({e})")
        rag = None

# Track recently used acks to avoid repeats
recent_acks     = []
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
            "which transcribes audio locally with no internet required. My voice is powered "
            "by Piper TTS, a lightweight text to speech engine. My object detection runs "
            "through the Sony IMX500 camera's built-in neural processor. Everything is "
            "open source and runs completely offline on my Raspberry Pi."
        )
    },
    {
        "name": "ai_models",
        "acks": ["Good question!", "Let me break it down!", "Sure thing!"],
        "keywords": ["model", "models", "ai model", "what model", "running",
                     "llama", "yolo", "program", "brain",
                     "modeled", "motto", "module"],
        "answer": (
            "For object detection I use YOLO 11 nano trained on the COCO dataset, "
            "which runs directly on the Sony IMX500 camera's built-in neural processor. "
            "For speech recognition I use Vosk, a lightweight offline model optimized "
            "for edge hardware. Everything runs locally on my Raspberry Pi 5 with no "
            "cloud connection needed."
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
            "I run on a Raspberry Pi 5 with 8 gigabytes of RAM, a Sony IMX500 AI Camera "
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
                     "yep", "yup", "definitely", "totally"],
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
                     "other jeep", "other car", "first iris"],
        "answer": (
            "IRIS 1.0 was built last year and could do real-time object detection "
            "displayed on a screen mounted on a green Jeep. I am IRIS 2.0, also called "
            "Echo IRIS. I am the upgraded version with voice interaction, a new white Jeep, "
            "and the ability to communicate with the original IRIS vehicle."
        )
    },
    {
        "name": "thanks",
        "acks": ["I appreciate you!", "Glad you enjoyed it!", "That means a lot!"],
        "keywords": ["thank you", "thanks a lot", "thanks so much",
                     "that's cool", "that's awesome", "that's amazing",
                     "that's impressive", "good job", "well done",
                     "nice job", "amazing work", "thanks"],
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
    global recent_acks
    choices = entry["acks"] if entry and "acks" in entry else DEFAULT_ACKS
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
    """Handle a user question: keyword → RAG → redirect."""

    word_count = len(user_text.split())

    # Step 1: Keyword match — instant answer
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
        log_chat("iris (keyword)", f"{ack} {demo_answer}")
        return demo_answer

    # Step 2: Too short — ask to repeat
    if word_count < MIN_WORDS_FOR_ANSWER:
        repeat_msg = random.choice(REPEAT_PHRASES)
        print_wrapped(repeat_msg)
        speak_text(repeat_msg, stream)
        log_chat("user", user_text)
        log_chat("iris", f"(repeat: {repeat_msg})")
        return repeat_msg

    # Step 3: RAG lookup
    if RAG_ENABLED and rag and rag.loaded:
        ack = get_ack()
        print(f"[IRIS]: {ack}")
        speak_text(ack, stream)

        rag_answer, confidence = rag.query(user_text)
        if rag_answer:
            print_wrapped(rag_answer)
            speak_text(rag_answer, stream)
            conversation_history.append({"role": "user", "content": user_text})
            conversation_history.append({"role": "assistant", "content": rag_answer})
            log_chat("user", user_text)
            log_chat("iris (rag)", f"[conf={confidence:.2f}] {rag_answer}")
            return rag_answer

    # Step 4: Redirect
    redirect_msg = random.choice(REDIRECT_PHRASES)
    print_wrapped(redirect_msg)
    speak_text(redirect_msg, stream)
    log_chat("user", user_text)
    log_chat("iris (redirect)", redirect_msg)
    return redirect_msg


def run_iris():
    print("=" * 42)
    print("  ECHO IRIS v3.2 -- 8GB Edition + RAG")
    print("=" * 42)
    print(f"  Model:     {MODEL_NAME}")
    print(f"  RAG:       {'Enabled' if RAG_ENABLED else 'Disabled'}")
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

    print(f"  Chat log:  {CHAT_LOG_FILE}")
    print("\n--- ECHO IRIS PROTOCOL ACTIVE ---")
    print("Say 'hello' or 'iris' to wake me up!\n")

    rec = KaldiRecognizer(vosk_model, 16000)

    while True:
        data = stream.read(4000, exception_on_overflow=False)
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text = result.get("text", "").strip()

            if text and contains_wake_word(text):
                print("\n** IRIS ACTIVATED **")
                print_wrapped(GREETING)
                speak_text(GREETING, stream)
                log_chat("system", f"Wake word: {text}")
                log_chat("iris", GREETING)

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

    if RAG_ENABLED:
        print("\nInitializing RAG...")
        init_rag()

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
