import os
import uuid
from pydub import AudioSegment
from pydub.utils import which
from io import BytesIO
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import ProgrammingError
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from openai import OpenAI
from datetime import datetime
from flask_login import UserMixin
import re
import logging
from dotenv import load_dotenv
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs, ApiError

# Import models from app package
from app.models import JobDescriptionAnalysis, User, InterviewHistory, Questions

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# Ensure ffmpeg is found
ffmpeg_location = os.getenv('FFMPEG_LOCATION')
AudioSegment.converter = which("ffmpeg") or ffmpeg_location

# Initialize the OpenAI chat model
openai_api_key = os.getenv("OPENAI_API_KEY")
model = ChatOpenAI(model="gpt-3.5-turbo", api_key=openai_api_key, temperature=0.5)

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

        save_file_path = os.path.join("audio_files", f"{uuid.uuid4()}.mp3")
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

def get_answer_1():
    # Placeholder for get_answer_1 function
    return {
        "status": "success",
        "message": "Answer received and processed."
    }

def intro_question(user_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()

        if not user or not job_description:
            raise ValueError("User or Job Description not found")

        username = user.username
        job_title = job_description.job_title
        company_name = job_description.company_name

        return f"Hi {username}, thanks for taking this meeting to discuss the {job_title} role at {company_name}. I'm excited to learn more about you. Could you please start by telling me more about yourself? Specifically, what professional experiences have you had that make you a good fit for the {job_title} role at {company_name}?"
    except Exception as e:
        print(f"Error generating intro question: {e}")
        return "An error occurred while generating the initial question."

def write_interview_history_table():
    print("this is a placeholder")

def get_score():
    print("this is a placeholder")
