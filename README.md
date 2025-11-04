# JARVIS – Voice-Activated AI Assistant

![JARVIS](https://img.shields.io/badge/JARVIS-AI_Assistant-blue?style=for-the-badge&logo=robot)
![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat&logo=python)
![Ollama](https://img.shields.io/badge/Ollama-Qwen3:4B-green?style=flat&logo=ollama)
![Status](https://img.shields.io/badge/Status-Active-success)

> **"Just say 'Jarvis' — and take control."**

A **real-time, voice-activated AI assistant** that listens for **"Jarvis"**, understands natural language, and executes system commands — powered by **Qwen3:4B LLM**, **LangChain**, and **Coqui TTS**.

---

## Features

| Feature | Description |
|--------|-----------|
| **Wake Word** | "Jarvis" — detected instantly using **Porcupine** |
| **Speech Recognition** | Real-time STT via **Google API** |
| **LLM Brain** | **Qwen3:4B** processes commands → JSON actions |
| **Voice Output** | Natural speech using **XTTS v2** (GPU-accelerated) |
| **10+ Commands** | Chrome, Shutdown, Time, Search, Notepad, Sleep, etc. |
| **Fallback Logic** | Keyword matching if LLM fails |
| **Sleep Mode** | Say "Jarvis, wake" to resume |
| **Full Logging** | Debug everything in `debug.log` |

---

## Demo Commands

```bash
"Jarvis, open Chrome"          → Opens Google Chrome
"Jarvis, shutdown the PC"      → Shuts down in 1 second
"Jarvis, what time is it?"     → "The current time is 3:45 PM"
"Jarvis, search Python"        → Opens Google search
"Jarvis, sleep"                → Enters low-power mode
"Jarvis, wake"                 → Resumes listening

Tech Stack
textPython 3.11
├── LangChain + Ollama (Qwen3:4B)
├── SpeechRecognition + PyAudio
├── Coqui TTS (XTTS v2) + PyTorch (CUDA)
├── Picovoice Porcupine + pvrecorder
└── subprocess, webbrowser, logging

Hardware Used

Laptop: MSI Sword 15
CPU: Intel i5-12th Gen
GPU: NVIDIA RTX 3050 (4GB)
RAM: 16GB DDR5
SSD: 1TB


Achieves < 3 seconds end-to-end response on this setup.


Setup (Step-by-Step)
1. Clone & Enter Project
bashgit clone https://github.com/RED1EYE/JARVIS-Voice-Activated-AI-Assistant.git
cd JARVIS-Voice-Activated-AI-Assistant
2. Install Ollama
Download Here → Install → Run:
bashollama serve
3. Download Qwen3:4B Model
bashollama pull qwen3:4b
4. Install Python Packages
bashpip install -r requirements.txt

Use CUDA-enabled PyTorch:
bashpip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

5. Add Picovoice Access Key

Go to https://console.picovoice.ai
Get your free Access Key
Open jarvis.py → Find this line:
pythonaccess_key='cvYTWOesCJFVMdkRuPRrC4jkWnfYOw0KaNv1amgJ1NcXexMHy3I01g=='

Replace with your key.

6. Run JARVIS
bashpython jarvis.py
Say "Jarvis" →

Project Structure
textJARVIS-Voice-Activated-AI-Assistant/
├── jarvis.py              Main AI logic
├── jarvis_config.json     Start mode (normal/sleep)
├── requirements.txt       Dependencies
├── README.md              This file
├── .gitignore             Ignores logs, audio, venv
└── debug.log              Runtime logs (ignored)
Jarvi.py is for API based approach,much faster than LLM.(Using Groq API)
Configuration
Edit jarvis_config.json:
json{
  "start_mode": "normal"
}

"normal" → Starts listening immediately
"sleep" → Waits for "Jarvis, wake"


Debugging
Check debug.log for:

Raw LLM output
JSON parsing
Audio capture status
Fallback triggers

bashtype debug.log

Performance Metrics
MetricTimeWake Word Detection~80msSpeech → Text~1.2sLLM Inference (Qwen3:4B)~1.5sTTS Generation~0.8sTotal Response< 3.0s

Future Roadmap

 Offline STT (Whisper)
 Custom voice cloning
 Web dashboard
 Plugin system
 Multi-language support


Contributing

Fork the repo
Create a branch (git checkout -b feature/xyz)
Commit (git commit -m 'Add xyz')
Push & Open a Pull Request


License
textMIT License © RED1EYE

Author
RED1EYE
GitHub • Built with passion on MSI Sword 15
