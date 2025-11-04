import os
import subprocess
import webbrowser
from groq import Groq
from TTS.api import TTS
import pvporcupine
import pvrecorder
import json
import warnings
import logging
import speech_recognition as sr
import datetime
import torch
import re

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler('debug.log', mode='a', encoding='utf-8'),
    logging.StreamHandler()
])

# Suppress warnings
warnings.filterwarnings('ignore')

# Load config
def load_config():
    try:
        with open('jarvis_config.json', 'r') as f:
            return json.load(f)
    except:
        return {"start_mode": "normal", "groq_api_key": ""}

config = load_config()
start_mode = config.get("start_mode", "normal")
GROQ_API_KEY = config.get("groq_api_key") or os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    logging.error("Groq API key not found! Set it in jarvis_config.json or GROQ_API_KEY env variable")
    exit()

# Initialize Groq client
try:
    groq_client = Groq(api_key=GROQ_API_KEY)
    logging.info("Groq client initialized successfully")
except Exception as e:
    logging.error(f"Groq client initialization failed: {e}")
    exit()

# Initialize SpeechRecognition
try:
    recognizer = sr.Recognizer()
    logging.info("SpeechRecognizer initialized successfully.")
except Exception as e:
    logging.error(f"SpeechRecognition initialization failed: {e}")
    exit()

# Initialize other components
porcupine = pvporcupine.create(access_key='cvYTWOesCJFVMdkRuPRrC4jkWnfYOw0KaNv1amgJ1NcXexMHy3I01g==', keywords=['jarvis'])
recorder = pvrecorder.PvRecorder(device_index=-1, frame_length=porcupine.frame_length)

try:
    tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False)
    tts.to('cuda' if torch.cuda.is_available() else 'cpu')
    logging.info("TTS initialized successfully on GPU" if torch.cuda.is_available() else "TTS initialized on CPU")
except Exception as e:
    logging.error(f"TTS initialization failed: {e}")
    exit()

# Conversation history for context
conversation_history = []

def speak(text, lang='en'):
    try:
        tts.tts_to_file(text=text, file_path="output.wav", language=lang, speaker="Ana Florence")
        os.system("start output.wav")
    except Exception as e:
        logging.error(f"TTS error: {e}")

def listen_for_command():
    for attempt in range(2):
        try:
            logging.debug(f"Recording command audio (attempt {attempt + 1})...")
            with sr.Microphone() as source:
                logging.info("Adjusting for ambient noise (1 second)...")
                recognizer.adjust_for_ambient_noise(source, duration=1)
                logging.info("Listening for speech (max 5 seconds)...")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            logging.info("Audio captured. Transcribing with Google API...")
            try:
                command = recognizer.recognize_google(audio).lower().strip()
                lang = 'en'
                logging.debug(f"Transcribed command: {command}, language: {lang}")
                if not command or command in ['shut up', 'nd nd', 'todo', 'great turner']:
                    logging.warning("Empty or invalid transcription, retrying...")
                    speak("I didn't catch that. Please say your command clearly.")
                    continue
                backdoor_code = "override"
                if command.endswith(backdoor_code):
                    command = command[:-len(backdoor_code)].strip()
                    logging.debug(f"Backdoor code detected, command: {command}")
                return command, lang
            except Exception as e:
                logging.error(f"Transcription error: {e}")
                speak("Error transcribing audio. Please try again.")
                return None, None
        except sr.WaitTimeoutError:
            logging.warning("No audio detected within 5 seconds")
            speak("No command heard. Please try again.")
            return None, None
        except sr.UnknownValueError:
            logging.warning("Google could not understand audio, retrying...")
            speak("I didn't catch that. Please say your command clearly.")
            continue
        except sr.RequestError as e:
            logging.error(f"Google SpeechRecognition API error: {e}")
            speak("Error in speech recognition. Check internet connection and try again.")
            return None, None
        except Exception as e:
            logging.error(f"Unexpected error occurred: {e}")
            if attempt == 1:
                speak("Failed to understand command. Please try again.")
                return None, None
    return None, None

def get_groq_response(command):
    """Get JSON response from Groq API"""
    try:
        system_prompt = """You are JARVIS, an AI assistant that processes voice commands and returns ONLY valid JSON.

CRITICAL RULES:
1. Return ONLY a JSON object, nothing else
2. No explanations, no markdown, no thinking out loud
3. Format: {"action": "ACTION_NAME", "params": {...}}

Available actions:
- shutdown: {"action": "shutdown", "params": {}}
- open_chrome: {"action": "open_chrome", "params": {"url": "google.com"}}
- open_notepad: {"action": "open_notepad", "params": {}}
- time: {"action": "time", "params": {}}
- lock_laptop: {"action": "lock_laptop", "params": {}}
- search: {"action": "search", "params": {"query": "search term"}}
- research: {"action": "research", "params": {"topic": "research topic"}}
- make_folder: {"action": "make_folder", "params": {"folder_name": "name"}}
- add_file: {"action": "add_file", "params": {"file_name": "name.txt"}}
- sleep: {"action": "sleep", "params": {}}
- stop: {"action": "stop", "params": {}}
- chat: {"action": "chat", "params": {"response": "your response"}}

Examples:
User: "shutdown the computer"
{"action": "shutdown", "params": {}}

User: "what time is it"
{"action": "time", "params": {}}

User: "search for python tutorials"
{"action": "search", "params": {"query": "python tutorials"}}

User: "tell me a joke"
{"action": "chat", "params": {"response": "Why did the programmer quit? They didn't get arrays!"}}"""

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (last 5 exchanges)
        for msg in conversation_history[-10:]:
            messages.append(msg)
        
        # Add current command
        messages.append({"role": "user", "content": command})
        
        logging.debug(f"Sending to Groq: {command}")
        
        # Call Groq API with llama-3.3-70b-versatile (fast and accurate)
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # You can also use "mixtral-8x7b-32768" or "llama-3.1-8b-instant"
            messages=messages,
            temperature=0.0,
            max_tokens=200,
            response_format={"type": "json_object"}  # Forces JSON output
        )
        
        response_text = response.choices[0].message.content
        logging.debug(f"Groq response: {response_text}")
        
        # Update conversation history
        conversation_history.append({"role": "user", "content": command})
        conversation_history.append({"role": "assistant", "content": response_text})
        
        # Keep history manageable
        if len(conversation_history) > 20:
            conversation_history.pop(0)
            conversation_history.pop(0)
        
        return response_text
        
    except Exception as e:
        logging.error(f"Groq API error: {e}")
        return None

def clean_and_parse_json(response):
    """Parse JSON from Groq response"""
    try:
        if not response:
            return None
        
        # Try direct JSON parse first (Groq usually returns clean JSON)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Fallback: extract JSON from response
        json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0).strip()
            return json.loads(json_str)
        
        logging.warning(f"Could not parse JSON from: {response[:200]}")
        return None
        
    except Exception as e:
        logging.error(f"Error parsing JSON: {e}")
        return None

def parse_command_fallback(command):
    """Fallback parser for common commands when API fails"""
    command = command.lower().strip()
    
    if any(keyword in command for keyword in ['shutdown', 'shut down', 'power off', 'turn off']):
        return {'action': 'shutdown', 'params': {}}
    
    if any(keyword in command for keyword in ['chrome', 'open chrome', 'google chrome']):
        return {'action': 'open_chrome', 'params': {'url': 'google.com'}}
    
    if 'notepad' in command:
        return {'action': 'open_notepad', 'params': {}}
    
    if any(keyword in command for keyword in ['time', 'what time']):
        return {'action': 'time', 'params': {}}
    
    if 'lock' in command:
        return {'action': 'lock_laptop', 'params': {}}
    
    if 'sleep' in command:
        return {'action': 'sleep', 'params': {}}
    
    if any(keyword in command for keyword in ['exit', 'goodbye', 'stop', 'quit']):
        return {'action': 'stop', 'params': {}}
    
    if any(keyword in command for keyword in ['search', 'google', 'look up']):
        query = re.sub(r'(search|google|look up|for)\s*', '', command).strip()
        return {'action': 'search', 'params': {'query': query}}
    
    return {'action': 'chat', 'params': {'response': 'I\'m not sure how to handle that command.'}}

def execute_action(action, params):
    try:
        logging.debug(f"Executing action: {action}, params: {params}")
        if action == 'open_chrome':
            url = params.get('url', 'https://www.google.com')
            if not url.startswith('http'):
                url = 'https://' + url
            webbrowser.open(url)
            speak("Opening Chrome.")
        elif action == 'open_notepad':
            subprocess.run('notepad' if os.name == 'nt' else 'open -a TextEdit')
            speak("Opening Notepad.")
        elif action == 'time':
            current_time = datetime.datetime.now().strftime("%H:%M")
            speak(f"The current time is {current_time}")
        elif action == 'search':
            query = params.get('query', '')
            if query:
                webbrowser.open(f'https://www.google.com/search?q={query}')
                speak(f"Searching for {query}.")
            else:
                speak("Please specify what to search for.")
        elif action == 'research':
            topic = params.get('topic', '')
            if topic:
                webbrowser.open(f'https://grok.x.ai/?q={topic}')
                speak(f"Researching {topic}.")
            else:
                speak("Please specify what to research.")
        elif action == 'make_folder':
            folder = params.get('folder_name', 'new_folder')
            os.makedirs(folder, exist_ok=True)
            speak("Folder created.")
        elif action == 'add_file':
            file = params.get('file_name', 'new_file.txt')
            open(file, 'w').close()
            speak("File added.")
        elif action == 'code':
            code_snippet = params.get('code', '')
            with open('generated_code.py', 'w') as f:
                f.write(code_snippet)
            speak("Code generated in generated_code.py.")
        elif action == 'lock_laptop':
            subprocess.run(['rundll32.exe', 'user32.dll,LockWorkStation'])
            speak("Locking laptop.")
        elif action == 'shutdown':
            speak("Shutting down.")
            subprocess.run(['shutdown', '/s', '/t', '1'], check=True)
        elif action == 'sleep':
            return 'sleep'
        elif action == 'stop':
            return 'stop'
        elif action == 'chat':
            response_text = params.get('response', 'I\'m here to help!')
            speak(response_text)
        else:
            logging.warning(f"Unknown action: {action}")
            speak("I'm not sure how to handle that command.")
        return None
    except Exception as e:
        logging.error(f"Error executing action: {e}")
        speak(f"Error executing action: {e}")
        return None

if start_mode == "sleep":
    speak("JARVIS in sleep mode. Say 'Jarvis, wake' to resume.")
else:
    speak("JARVIS online.")
    recorder.start()

while True:
    try:
        if start_mode == "sleep":
            with sr.Microphone() as source:
                logging.debug("Adjusting for ambient noise for wake word...")
                recognizer.adjust_for_ambient_noise(source, duration=1)
                logging.debug("Listening for wake word...")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            try:
                command = recognizer.recognize_google(audio).lower().strip()
                if command == 'wake':
                    speak("I'm back.")
                    recorder.start()
                    start_mode = "normal"
                    continue
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                logging.error(f"Google SpeechRecognition API error: {e}")
                speak("Error in speech recognition. Check internet connection.")
                continue
        else:
            pcm = recorder.read()
            keyword_index = porcupine.process(pcm)
            if keyword_index >= 0:
                speak("Yes?")
                command, lang = listen_for_command()
                if command:
                    logging.debug(f"Processing command: {command}")
                    action_data = None
                    
                    # Try Groq API first
                    response = get_groq_response(command)
                    if response:
                        action_data = clean_and_parse_json(response)
                    
                    # Fallback to keyword-based parser if API fails
                    if not action_data or 'action' not in action_data:
                        logging.info("Using fallback command parser")
                        action_data = parse_command_fallback(command)
                        logging.debug(f"Fallback action data: {action_data}")
                    
                    # Execute the action
                    if action_data and 'action' in action_data:
                        result = execute_action(action_data['action'], action_data.get('params', {}))
                        
                        if result == 'sleep':
                            speak("Going to sleep. Say 'Jarvis, wake' to resume.")
                            recorder.stop()
                            start_mode = "sleep"
                        elif result == 'stop':
                            speak("Shutting down JARVIS.")
                            recorder.stop()
                            break
                    else:
                        logging.error(f"Failed to parse command: {command}")
                        speak("I couldn't understand that command. Please try again.")
                        
    except KeyboardInterrupt:
        logging.info("JARVIS interrupted by user")
        speak("Shutting down JARVIS.")
        recorder.stop()
        break
    except Exception as e:
        logging.error(f"Main loop error: {e}")
        speak("An error occurred. Please try again.")

