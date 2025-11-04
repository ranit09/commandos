import os
import subprocess
import webbrowser
from langchain_community.llms import Ollama
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
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
        return {"start_mode": "normal"}

config = load_config()
start_mode = config.get("start_mode", "normal")

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
                    speak("I didn't catch that. Please say your command clearly, like 'shutdown'.")
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
            speak("I didn't catch that. Please say your command clearly, like 'shutdown'.")
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

def initialize_llm():
    try:
        # Use a smaller, more memory-efficient model
        llm = Ollama(
            model="qwen3:4b",  # Consider using "llama3.2:1b" or "phi3:mini" for better memory usage
            temperature=0.0,  # Set to 0 for maximum determinism
            num_ctx=512  # Reduce context window to save memory
        )
        memory = ConversationBufferMemory()
        
        # Simplified prompt that's more direct
        prompt = PromptTemplate(
            input_variables=["history", "input"],
            template="""Return ONLY valid JSON. No thinking, no explanations.

Format: {{"action": "ACTION_NAME", "params": {{}}}}

Commands:
shutdown → {{"action": "shutdown", "params": {{}}}}
open chrome → {{"action": "open_chrome", "params": {{"url": "google.com"}}}}
open notepad → {{"action": "open_notepad", "params": {{}}}}
what time → {{"action": "time", "params": {{}}}}
lock → {{"action": "lock_laptop", "params": {{}}}}
search X → {{"action": "search", "params": {{"query": "X"}}}}
sleep → {{"action": "sleep", "params": {{}}}}
exit → {{"action": "stop", "params": {{}}}}
other → {{"action": "chat", "params": {{"response": "I'm here to help!"}}}}

User: {input}
JSON:"""
        )
        return LLMChain(llm=llm, prompt=prompt, memory=memory)
    except Exception as e:
        logging.error(f"LLM initialization failed: {e}")
        exit()

def clean_llm_response(response):
    """Clean LLM response to extract pure JSON - FIXED VERSION"""
    if not response:
        return None
    
    try:
        # Remove thinking blocks (all variations)
        response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE)
        response = re.sub(r'<thinking>.*?</thinking>', '', response, flags=re.DOTALL | re.IGNORECASE)
        response = re.sub(r'</think>.*$', '', response, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove markdown code blocks
        response = re.sub(r'```json\s*', '', response, flags=re.IGNORECASE)
        response = re.sub(r'```\s*', '', response)
        
        # Remove common prefixes
        response = re.sub(r'^.*?(?=\{)', '', response, flags=re.DOTALL)
        
        # FIXED: Extract the OUTERMOST JSON object that contains "action" key
        # This regex specifically looks for objects with "action" key
        json_match = re.search(r'\{"action":\s*"[^"]+",\s*"params":\s*\{[^}]*\}\}', response, re.DOTALL)
        
        if json_match:
            json_str = json_match.group(0).strip()
            logging.debug(f"Extracted JSON: {json_str}")
            return json_str
        
        # Fallback: try to find any valid JSON with action key
        json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0).strip()
            logging.debug(f"Extracted JSON (fallback): {json_str}")
            return json_str
        
        logging.warning(f"No valid JSON with 'action' key found in response: {response[:200]}")
        return None
    except Exception as e:
        logging.error(f"Error cleaning LLM response: {e}")
        return None

def parse_command_fallback(command):
    """Fallback parser for common commands when LLM fails"""
    command = command.lower().strip()
    
    # Shutdown patterns
    if any(keyword in command for keyword in ['shutdown', 'shut down', 'power off', 'turn off']):
        return {'action': 'shutdown', 'params': {}}
    
    # Chrome patterns
    if any(keyword in command for keyword in ['chrome', 'open chrome', 'google chrome']):
        return {'action': 'open_chrome', 'params': {'url': 'google.com'}}
    
    # Notepad patterns
    if 'notepad' in command:
        return {'action': 'open_notepad', 'params': {}}
    
    # Time patterns
    if any(keyword in command for keyword in ['time', 'what time']):
        return {'action': 'time', 'params': {}}
    
    # Lock patterns
    if 'lock' in command:
        return {'action': 'lock_laptop', 'params': {}}
    
    # Sleep patterns
    if 'sleep' in command:
        return {'action': 'sleep', 'params': {}}
    
    # Stop patterns
    if any(keyword in command for keyword in ['exit', 'goodbye', 'stop', 'quit']):
        return {'action': 'stop', 'params': {}}
    
    # Search patterns
    if any(keyword in command for keyword in ['search', 'google', 'look up']):
        query = re.sub(r'(search|google|look up|for)\s*', '', command).strip()
        return {'action': 'search', 'params': {'query': query}}
    
    # Default to chat
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
    chain = None
else:
    speak("JARVIS online.")
    chain = initialize_llm()
    recorder.start()

while True:
    try:
        if start_mode == "sleep" or chain is None:
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
                    chain = initialize_llm()
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
                    response = None
                    action_data = None
                    
                    # Try LLM first (with retry)
                    for attempt in range(2):
                        try:
                            logging.debug(f"Attempting LLM chain run (attempt {attempt + 1})...")
                            response = chain.run(input=command)
                            logging.debug(f"Raw LLM response: {response[:500]}")  # Log first 500 chars
                            
                            # Clean and extract JSON
                            json_str = clean_llm_response(response)
                            if json_str:
                                action_data = json.loads(json_str)
                                
                                # Validate that we have the action key
                                if 'action' in action_data:
                                    logging.debug(f"Successfully parsed action data: {action_data}")
                                    break
                                else:
                                    logging.warning(f"Parsed JSON missing 'action' key: {action_data}")
                                    action_data = None
                            else:
                                logging.warning(f"Failed to extract JSON from response (attempt {attempt + 1})")
                        except json.JSONDecodeError as e:
                            logging.error(f"JSON parsing error (attempt {attempt + 1}): {e}, extracted: {json_str}")
                        except Exception as e:
                            logging.error(f"LLM chain error (attempt {attempt + 1}): {e}")
                            # If it's a memory error, wait a moment before retry
                            if "system memory" in str(e).lower():
                                logging.warning("Memory error detected, waiting 2 seconds before retry...")
                                import time
                                time.sleep(2)
                        
                        if attempt == 1:
                            logging.warning("LLM failed after retries, using fallback parser")
                    
                    # Fallback to keyword-based parser if LLM fails
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
                            chain = None
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