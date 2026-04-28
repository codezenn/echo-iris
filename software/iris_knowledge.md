# Echo IRIS Knowledge Base
# Used by iris_rag.py for Retrieval-Augmented Generation
# Each section separated by --- is treated as one retrievable chunk
# Keep each chunk focused on one topic and under 300 words

---
## Project Overview
Echo IRIS is an AI-powered voice-interactive agent built on a mini-Jeep platform.
It is a functional extension of IRIS 1.0, an existing ECE 202 platform at Colorado State University
designed for real-time object detection. IRIS stands for Intelligent Raspberry-Pi Imaging System.
Echo IRIS adds a full voice interaction layer, allowing IRIS to listen for spoken prompts,
process them locally on-device, and respond audibly in real time using a custom embedded AI pipeline.
The system operates autonomously on battery power with no dependency on external servers or the internet.

---
## Team
Echo IRIS was built by three ECE 202 students at Colorado State University.
Marc Sibaja is the project lead responsible for the AI agent, voice pipeline, and software architecture.
Giovanni Guerra is responsible for 3D design and printing, including the speaker mount, Pi enclosure, and LED housing.
Obaid Almutairi is responsible for Jeep and Pi assembly, wiring, GPIO connections, and power integration.
All three are equal contributors to the project.

---
## Hardware
Echo IRIS runs on a Raspberry Pi 5 with 8 gigabytes of RAM.
The vision system uses a Sony IMX500 AI Camera with a built-in neural processor for object detection.
Storage is handled by a 256 gigabyte NVMe SSD connected via M.2 HAT+.
Power is supplied by a Baseus 65 watt power bank with 20,000 milliamp hours of capacity and Power Delivery 3.0 support.
A UPS HAT with 18650 batteries provides backup power to prevent crashes during mobile operation.
A KYY 15.6 inch portable monitor displays real-time bounding boxes and system diagnostics.
A Raspberry Pi Active Cooler manages thermal output under heavy AI workloads.
A USB microphone handles voice input for speech recognition.
The total estimated hardware cost is approximately 590 dollars.

---
## Software Stack
The entire software stack runs on Python 3.
Speech recognition is handled by Vosk using a small offline model that requires no internet connection.
Text-to-speech output uses Piper TTS with a British English voice model called en_GB-vctk-medium.
The conversational AI uses Qwen3 0.6 billion parameter model served through Ollama, running completely offline on the Pi.
Object detection runs YOLO 11 nano through the Sony IMX500 camera's built-in neural processor.
Embeddings for the RAG system use nomic-embed-text v1.5 served through Ollama.
Everything runs locally with no cloud dependency.

---
## Language Model - Qwen3 0.6b
IRIS uses the Qwen3 0.6 billion parameter model as its conversational brain.
This model was chosen because it is extremely lightweight at only 522 megabytes, making it ideal for running
on a Raspberry Pi 5 with limited CPU resources alongside Vosk and Piper simultaneously.
Qwen3 0.6b is developed by Alibaba Cloud and is fully open source under the Apache 2.0 license.
It supports thinking mode for complex reasoning and non-thinking mode for fast direct responses.
IRIS uses non-thinking mode to keep voice responses quick and natural.
The model runs through Ollama, a local model runtime that manages loading and inference on the Pi CPU.
Qwen3 0.6b was selected over larger models like Qwen3 1.7b or llama3.2 because response speed matters
more than raw intelligence for a voice agent in a live demo environment.
When the 16 gigabyte Raspberry Pi 5 arrives, the team plans to upgrade to a larger model like Qwen3.5 4b
for richer, more detailed conversations.

---
## RAG - Retrieval Augmented Generation
RAG stands for Retrieval-Augmented Generation. It is a technique that improves AI responses by first
searching a knowledge base for relevant information, then passing that information to a language model
to generate an accurate answer.
Without RAG, a language model can only answer based on what it learned during training, which may be
outdated or incomplete. With RAG, the model is given fresh, specific context at query time.
IRIS uses RAG to answer questions that are not covered by its scripted keyword answers.
When a user asks something IRIS does not have a scripted response for, the RAG system converts the
question into a numerical embedding using nomic-embed-text, searches the iris_knowledge.md file for the
most similar chunks, and feeds those chunks to Qwen3 0.6b to generate a contextual answer.
This means IRIS can answer detailed questions about its hardware, software, team, and project goals
without needing every possible question pre-programmed in advance.
The RAG system runs entirely offline on the Raspberry Pi with no internet connection required.

---
## Embeddings and nomic-embed-text
An embedding is a numerical representation of text that captures its meaning as a vector of numbers.
Similar pieces of text will have similar embeddings, which allows the RAG system to find relevant
knowledge chunks by measuring how close two embeddings are in vector space.
IRIS uses nomic-embed-text version 1.5 as its embedding model, served through Ollama.
It is only 274 megabytes, runs fast on CPU, and outperforms OpenAI text-embedding-ada-002 on benchmarks.
When IRIS starts up, it embeds all chunks in the iris_knowledge.md file and caches them to disk.
On subsequent startups the cache is loaded instantly, so there is no delay building the index.
When a user asks a question, the question is embedded and compared to all cached chunk embeddings
using cosine similarity to find the most relevant context.

---
## Ollama
Ollama is a local model runtime that makes it easy to download and run open source language models
on consumer hardware. It handles model loading, quantization, and inference through a simple API.
IRIS uses Ollama to serve two models simultaneously: nomic-embed-text for embeddings and Qwen3 0.6b
for conversation. Both run completely offline on the Raspberry Pi CPU with no internet required.
Ollama is accessed through its REST API at localhost port 11434. The IRIS Python scripts send HTTP
requests to Ollama to generate embeddings and chat responses.
Ollama automatically uses quantized GGUF model formats which compress model weights to reduce memory
usage and speed up inference on CPU hardware like the Raspberry Pi.

---
## Voice Pipeline
IRIS listens passively for a wake word such as hello or iris.
When activated, IRIS greets the user and enters a conversation loop.
User speech is transcribed by Vosk in real time on the Pi CPU.
Matched questions are answered instantly from a keyword database.
Unknown questions are answered using the RAG system which retrieves relevant knowledge and passes it to the language model.
IRIS speaks responses using Piper TTS piped through aplay to a USB speaker.
The microphone is flushed after each response to prevent audio feedback.
If no question is heard within 12 seconds, IRIS goes back to sleep.

---
## Object Detection
IRIS uses a Sony IMX500 AI Camera with an on-board neural processor.
The object detection model is YOLO 11 nano trained on the COCO dataset.
It can identify over 80 types of objects including people, cars, dogs, chairs, and stop signs.
Detection runs on the camera's built-in chip, offloading computation from the Raspberry Pi CPU.
This allows object detection and voice interaction to run simultaneously without performance conflicts.
Bounding boxes and confidence scores are displayed in real time on the KYY portable monitor.

---
## IRIS 1.0 vs Echo IRIS
IRIS 1.0 was built by a previous ECE 202 team and featured real-time object detection on a green Jeep.
Echo IRIS is IRIS 2.0, also referred to as Echo IRIS, and is mounted on a white Jeep platform.
The key upgrades in Echo IRIS are a full voice interaction layer, a custom 3D printed speaker mount,
and planned vehicle-to-vehicle communication with IRIS 1.0 via MQTT.
The long-term vision includes autonomous driving, cooperative navigation, and smart robotics research.

---
## ECE 202 and Colorado State University
ECE 202 is an Electrical and Computer Engineering course at Colorado State University in Fort Collins, Colorado.
The course involves hands-on hardware and software projects using embedded systems.
Echo IRIS was proposed as a multi-semester platform that future ECE 202 teams can build on.
The project has been pitched to the department as a platform for high school recruiting demonstrations.
The ECE department may use the GitHub repository and GitHub Pages site to showcase the project publicly.

---
## Goals and Future Development
The primary goals for Spring 2026 are voice interactivity, object detection integration,
vehicle-to-vehicle communication via MQTT, and a 3D printed speaker mount.
Future development includes YOLO-based object detection with voice announcements,
V2V communication between two IRIS vehicles, autonomous driving capabilities, and a GitHub Pages public site.
The repository is designed to outlive the semester so future teams can continue development.

---
## Demo Day
Demo day is in April 2026 as part of ECE 202 at Colorado State University.
The team plans to demonstrate real-time voice interaction, object detection, and IRIS's ability to
answer questions about the project, its hardware, and its creators.
IRIS runs in demo mode during the presentation, which uses keyword-matched answers for reliability.
The RAG system handles questions outside the scripted answers.
The goal is to win best project in the class.

---
## Power System
The mobile power system uses a Baseus 65 watt power bank as the primary source.
A UPS HAT with two 18650 lithium-ion batteries provides uninterruptible backup power.
This prevents sudden shutdowns when the Jeep is moving or the power bank is swapped.
The Raspberry Pi 5 requires a stable 5 volt 5 amp power supply to prevent CPU throttling.
Earlier testing revealed undervoltage as the root cause of all system crashes and instability.
The 96 watt Apple USB-C adapter was confirmed as sufficient for bench testing.

---
## Edge AI and Why It Matters
Edge AI means running artificial intelligence models directly on a local device instead of sending
data to a remote server or cloud. IRIS is a demonstration of edge AI because every component of its
AI pipeline runs on the Raspberry Pi with no internet connection.
The benefits of edge AI include privacy since no data leaves the device, low latency since there is
no network round trip, and reliability since the system works even without wifi.
Running AI on a Raspberry Pi is impressive because the hardware is only 80 dollars yet can handle
speech recognition, text to speech, object detection, language model inference, and vector search
all simultaneously. This shows that powerful AI does not require expensive cloud infrastructure.
Edge AI is a growing field with applications in robotics, autonomous vehicles, medical devices,
and smart home systems. Echo IRIS is a small scale demonstration of what is possible at the edge.

---
## How Speech Recognition Works
When a user speaks to IRIS, the audio is captured by a USB microphone at 16,000 samples per second.
Vosk processes the raw audio stream in real time using a pre-trained acoustic model and a language model
to convert sound into text. This process is called automatic speech recognition or ASR.
Vosk is unique because it runs entirely offline using a small 40 megabyte model optimized for edge devices.
It uses a technique called Kaldi under the hood, which is the same framework used in many enterprise
speech recognition systems. The small model trades some accuracy for speed, which is the right tradeoff
for a voice agent where response time matters more than perfect transcription.
IRIS listens continuously in a loop, reading chunks of audio and feeding them to Vosk until a full
utterance is detected. Partial results are tracked to reset the silence timer and keep the session alive
while the user is still speaking.

---
## How the Voice Sounds Natural - Piper TTS
IRIS uses Piper TTS to convert text responses into spoken audio. Piper is a neural text-to-speech engine
developed by Nabu Casa, the company behind Home Assistant. It uses a neural vocoder to generate natural
sounding speech from text, which is a major upgrade over older robotic TTS systems like Festival or eSpeak.
The voice model IRIS uses is called en_GB-vctk-medium, a British English voice trained on the VCTK dataset
which contains recordings from dozens of real speakers. Speaker number 2 was selected for IRIS because
it has a clear, professional tone suitable for a demo environment.
Piper runs as a subprocess and pipes raw audio directly to aplay, the ALSA audio player, which outputs
through the USB speaker. This approach avoids loading audio libraries into Python memory and keeps the
pipeline fast and lightweight.

---
## IRIS vs Alexa Siri and Google Assistant
The key difference between IRIS and cloud assistants like Alexa, Siri, and Google Assistant is that
IRIS runs entirely on-device with no internet connection required. Cloud assistants send your voice
to remote servers to process, which requires internet, introduces latency, and raises privacy concerns
because your voice data is stored by the company.
IRIS processes everything locally on a Raspberry Pi that costs about 80 dollars. This means it works
without wifi, responds without network delay, and never sends any data outside the device.
Cloud assistants also depend on subscription services and can be shut down by the company at any time.
IRIS is fully open source, meaning anyone can inspect, modify, or extend the code for free.
The tradeoff is that IRIS is less capable than cloud assistants on general knowledge questions, but for
a focused application like answering questions about the project it is equally effective and far more private.

---
## Hardest Parts to Build - Challenges and Lessons Learned
The most challenging part of building Echo IRIS was diagnosing system crashes that appeared random.
After extensive debugging, all crashes were traced to a single root cause: undervoltage. The Raspberry Pi 5
requires a stable 5 volt 5 amp power supply, and early testing used insufficient power adapters which
caused the CPU to throttle and the system to shut down unpredictably.
The second major challenge was audio architecture. Early versions of the script stopped and restarted
the microphone stream between responses, which caused degraded speech recognition quality. The fix was
to keep the stream running continuously and flush the buffer after each response instead.
A third challenge was model selection. Larger language models caused 100 percent CPU usage and crashed
the voice pipeline. This led to the decision to use demo mode with keyword matching as the primary answer
system and reserve the language model for RAG fallback queries only.
These challenges taught the team that on edge hardware, stability and efficiency matter more than
raw capability, and that systematic debugging always beats guessing.

---
## What is a Raspberry Pi
A Raspberry Pi is a small single-board computer about the size of a credit card. It was originally
designed as an affordable educational computer to teach programming and electronics to students.
The Raspberry Pi 5 used in IRIS costs around 80 dollars and contains a quad-core ARM processor running
at 2.4 gigahertz, up to 8 gigabytes of RAM, USB ports, GPIO pins for connecting hardware, a camera
connector, and PCIe support for fast SSD storage.
Despite its small size, the Raspberry Pi 5 is powerful enough to run a full Linux operating system,
multiple AI models simultaneously, real-time object detection, and a voice interaction pipeline.
This makes it ideal for embedded AI projects like IRIS where portability, low power consumption,
and low cost are important. The entire IRIS platform runs on battery power from a power bank,
something that would be impossible with a traditional desktop or server computer.

---
## MQTT and Vehicle to Vehicle Communication
MQTT stands for Message Queuing Telemetry Transport. It is a lightweight messaging protocol designed
for devices with limited resources that need to communicate over a network efficiently.
Echo IRIS plans to use MQTT to enable vehicle-to-vehicle communication between the white Jeep and
the original green IRIS 1.0 Jeep. This would allow the two vehicles to share information such as
what objects each one detects, their positions, and status updates in real time.
MQTT works using a publish and subscribe model. One device publishes a message to a topic and any
device subscribed to that topic receives the message instantly. This is more efficient than direct
device-to-device communication because a central broker manages the routing.
The long-term vision is for the two IRIS vehicles to cooperate on tasks, share sensor data, and
eventually coordinate autonomous navigation. This is a foundational step toward the multi-agent
robotics systems used in real-world autonomous vehicle research.

---
## Cost Breakdown
The total estimated cost of Echo IRIS is approximately 590 dollars.
The Raspberry Pi 5 with 8 gigabytes of RAM costs 80 dollars and serves as the main computing unit.
The Sony IMX500 AI Camera costs 70 dollars and handles real-time object detection on its built-in chip.
The Baseus 65 watt power bank costs 90 dollars and provides mobile battery power with Power Delivery 3.0.
The official Raspberry Pi NVMe SSD and M.2 HAT plus costs 90 dollars and provides fast storage for AI models.
The KYY 15.6 inch portable monitor costs 70 dollars and displays the object detection feed and diagnostics.
The UPS HAT costs 33 dollars and provides uninterruptible power to prevent crashes during movement.
The 18650 battery pack costs 15 dollars and powers the UPS HAT.
The Raspberry Pi Active Cooler costs 8 dollars and keeps the CPU cool under heavy AI workloads.
Shipping and taxes add approximately 33 dollars to the total.
This demonstrates that a full AI robotics platform with voice, vision, and language capabilities
can be built for under 600 dollars using consumer off-the-shelf components.
