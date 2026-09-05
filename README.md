# Gemini Real-Time Voice Assistant

This is a real-time, continuous voice-to-voice AI assistant built in Python using the Gemini Live API. It operates seamlessly without requiring a wake word or manual button presses, enabling natural, hands-free conversations directly through your computer's microphone and speakers.

## Features
* **Ultra-Low Latency:** Uses asynchronous programming (`asyncio`) and chunked audio streaming to simultaneously send input and receive AI output without freezing the application.
* **No Wake Word Required:** Leverages Gemini's native Voice Activity Detection (VAD) to automatically sense when you stop speaking and instantly trigger a response.
* **Acoustic Echo Prevention:** Features a custom asynchronous queue system that dynamically mutes the microphone input while the AI is speaking, preventing the model from hearing its own voice and delaying the conversation.
* **Native Audio Processing:** Powered by the `gemini-2.5-flash-native-audio` model for direct speech-to-speech interaction, completely bypassing slow text-to-speech (TTS) or speech-to-text (STT) conversions.

## Prerequisites
* Python 3.8+
* A working microphone and speaker setup
* A Google Gemini API Key

## Installation

1. **Clone or setup the repository:**
   Ensure you are in your project directory (`src`).

2. **Create and activate a virtual environment (recommended):**
   ```bash
   python -m venv myvenv
   
   # On Windows:
   myvenv\Scripts\activate
   # On macOS/Linux:
   source myvenv/bin/activate
