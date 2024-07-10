import os
import uuid
from pydub import AudioSegment
from pydub.utils import which
from flask import current_app
from elevenlabs.client import ElevenLabs, ApiError
from elevenlabs import VoiceSettings

# Ensure environment variables are set
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    print("ELEVENLABS_API_KEY environment variable not set")
else:
    print(f"ELEVENLABS_API_KEY is set")

ffmpeg_location = os.getenv('FFMPEG_LOCATION')
if not ffmpeg_location:
    print("FFMPEG_LOCATION environment variable not set")
else:
    print(f"FFMPEG_LOCATION is set to {ffmpeg_location}")

# Ensure the converter for pydub is set
AudioSegment.converter = which("ffmpeg") or os.getenv('FFMPEG_LOCATION')

# Initialize ElevenLabs client
elevenlabs_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

def text_to_speech_file(text: str, voice_id: str) -> str:
    if not text.strip():
        print("Text is empty, skipping text-to-speech conversion.")
        return ""

    try:
        response = elevenlabs_client.text_to_speech.convert(
            voice_id=voice_id,
            optimize_streaming_latency="0",
            output_format="mp3_22050_32",
            text=text,
            model_id="eleven_turbo_v2",
            voice_settings=VoiceSettings(
                stability=0.0,
                similarity_boost=1.0,
                style=0.0,
                use_speaker_boost=True,
            ),
        )

        audio_folder = os.path.join(current_app.root_path, 'audio_files')
        # Remove existing files in the folder
        for filename in os.listdir(audio_folder):
            file_path = os.path.join(audio_folder, filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)

        save_file_path = os.path.join(audio_folder, f"{uuid.uuid4()}.mp3")
        os.makedirs(os.path.dirname(save_file_path), exist_ok=True)

        with open(save_file_path, "wb") as f:
            for chunk in response:
                if chunk:
                    f.write(chunk)

        print(f"{save_file_path}: A new audio file was saved successfully!")
        return save_file_path
    except ApiError as e:
        print(f"Error generating speech: {e}")
        return ""