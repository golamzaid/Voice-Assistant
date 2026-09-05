import asyncio
import os
from pathlib import Path

import pyaudio
from dotenv import load_dotenv
from google import genai
from google.genai.types import AudioTranscriptionConfig, HttpOptions, LiveConnectConfig

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-3.1-flash-live-preview"

if not API_KEY:
    raise RuntimeError(
        f"GEMINI_API_KEY is missing. Add it to {PROJECT_ROOT / '.env'} "
        "as GEMINI_API_KEY=your_key"
    )

client = genai.Client(
    api_key=API_KEY,
    http_options=HttpOptions(api_version="v1beta")
)

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE_IN = 16000
RATE_OUT = 24000
CHUNK = 2048

audio = pyaudio.PyAudio()

mic_stream = audio.open(
    format=FORMAT, channels=CHANNELS, rate=RATE_IN, 
    input=True, frames_per_buffer=CHUNK
)
speaker_stream = audio.open(
    format=FORMAT, channels=CHANNELS, rate=RATE_OUT, 
    output=True, frames_per_buffer=CHUNK
)

config = LiveConnectConfig(
    response_modalities=["AUDIO"],
    input_audio_transcription=AudioTranscriptionConfig(),
    output_audio_transcription=AudioTranscriptionConfig(),
    system_instruction=(
        "You are a highly responsive voice assistant. Always understand Hindi, English, "
        "and Hinglish. Reply in the same language style as the user; default to natural "
        "Hindi/Hinglish, using English only when the user speaks English. Keep replies "
        "brief, clear, and conversational. Wait for the user to finish before replying."
    ),
)

# Queue prevents the network connection from choking while audio plays
audio_out_queue = asyncio.Queue()
is_model_speaking = False

async def mic_task(session):
    global is_model_speaking
    print("Microphone active... You can start speaking anytime!")
    try:
        while True:
            data = await asyncio.to_thread(mic_stream.read, CHUNK, exception_on_overflow=False)

            # Do not send speaker audio back to the model.
            if is_model_speaking:
                data = b'\x00' * len(data)

            await session.send_realtime_input(
                audio={"mime_type": "audio/pcm;rate=16000", "data": data}
            )
            await asyncio.sleep(0.001)
    except asyncio.CancelledError:
        raise
    except Exception as error:
        print(f"Microphone error: {error}")
        raise

async def speaker_task(session):
    try:
        while True:
            async for response in session.receive():
                server_content = getattr(response, "server_content", None)
                if server_content:
                    input_transcription = getattr(server_content, "input_transcription", None)
                    if input_transcription and getattr(input_transcription, "text", None):
                        print(f"You: {input_transcription.text}")

                    output_transcription = getattr(server_content, "output_transcription", None)
                    if output_transcription and getattr(output_transcription, "text", None):
                        print(f"Assistant: {output_transcription.text}")

                    model_turn = getattr(server_content, "model_turn", None)
                    if model_turn:
                        for part in model_turn.parts:
                            inline_data = getattr(part, "inline_data", None)
                            if inline_data and getattr(inline_data, "data", None):
                                await audio_out_queue.put(inline_data.data)
    except asyncio.CancelledError:
        raise
    except Exception as error:
        print(f"Gemini receive error: {error}")
        raise

async def play_audio_task():
    global is_model_speaking
    while True:
        data = await audio_out_queue.get()
        
        # Flag that the assistant is speaking so the mic sends silence
        is_model_speaking = True 
        await asyncio.to_thread(speaker_stream.write, data)
        
        if audio_out_queue.empty():
            # Wait a tiny fraction of a second for room echo to clear before opening mic again
            await asyncio.sleep(0.2)
            is_model_speaking = False
            
        audio_out_queue.task_done()

async def main():
    while True:
        try:
            async with client.aio.live.connect(model=MODEL, config=config) as session:
                print("Live session connected. Press Ctrl+C to stop.")

                await asyncio.gather(
                    mic_task(session),
                    speaker_task(session),
                    play_audio_task(),
                )
        except asyncio.CancelledError:
            raise
        except Exception as error:
            global is_model_speaking
            is_model_speaking = False
            print(f"Live session disconnected: {error}")
            print("Reconnecting in 2 seconds...")
            await asyncio.sleep(2)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting Assistant...")