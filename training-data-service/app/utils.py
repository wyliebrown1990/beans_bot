import os
import uuid
import glob
import requests
from io import BytesIO
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import ProgrammingError
from openai import OpenAI  # Ensure OpenAI is imported correctly
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from datetime import datetime
from flask_login import UserMixin
import numpy as np
import re
import logging
from dotenv import load_dotenv
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
import yt_dlp
import whisper
from googleapiclient.discovery import build

# Import models from app package
from app.models import TrainingData, ProcessStatus
# Import app from app package to access config
from app import app
from app.database import get_db

# Load environment variables
load_dotenv()

youtube_api_key = os.getenv('GOOGLE_API_KEY')
cookies_file = os.getenv('COOKIES_FILE')
ffmpeg_location = os.getenv('FFMPEG_LOCATION')

# Initialize the OpenAI chat model
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=openai_api_key)

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# Set the save directory after importing app
save_dir = app.config['UPLOAD_FOLDER']
transcription_dir = os.path.join(save_dir, "youtube")
os.makedirs(transcription_dir, exist_ok=True)

# Initialize YouTube API client
youtube = build('youtube', 'v3', developerKey=youtube_api_key)

def update_process_status(username, job_title, company_name, status):
    username = username.lower().strip()
    job_title = job_title.lower().strip()
    company_name = company_name.lower().strip()
    print(f"Updating status for user: {username}, job: {job_title}, company: {company_name} to status: {status}")
    response = requests.post('http://localhost:5011/update_status', json={
        'username': username,
        'job_title': job_title,
        'company_name': company_name,
        'status': status
    })
    print(f"Status update response: {response.status_code} - {response.text}")

def load_training_data(db: Session, job_title: str, company_name: str):
    job_title = job_title.lower().strip()
    company_name = company_name.lower().strip()
    logging.debug(f"Loading training data for job title: {job_title}, company name: {company_name}")
    training_data = db.query(TrainingData).filter(
        func.lower(TrainingData.job_title) == job_title,
        func.lower(TrainingData.company_name) == company_name
    ).first()
    logging.debug(f"Retrieved training data: {training_data}")
    if training_data:
        logging.debug(f"Data: {training_data.data[:100]}...")  # Log first 100 characters of data
    return training_data

def generate_summary(text):
    openai_api_key = os.getenv("OPENAI_API_KEY")
    model = ChatOpenAI(api_key=openai_api_key)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert in summarizing the content of files. Return a 1000 character summary of the file I submit to you."),
        ("user", text)
    ])

    chain = prompt | model
    response = chain.invoke({"messages": []})

    # Extract response content
    response_content = response.content.strip()

    # Print the response content for debugging
    print("Response Content:", response_content)

    return response_content


def store_training_data(db_session, training_data):
    logging.debug(f"Storing training data: {training_data}")
    logging.debug(f"Data: {training_data.data[:100]}...")  # Log first 100 characters of data
    db_session.add(training_data)
    try:
        db_session.commit()  # Ensure the session is committed
        logging.debug(f"Stored training data with ID: {training_data.id}")
    except Exception as e:
        logging.error(f"Error committing training data to the database: {str(e)}")
        db_session.rollback()
        raise e

def process_file(file_path, job_title, company_name, username):
    filename = os.path.basename(file_path)
    logging.debug(f"Processing file: {filename}")

    try:
        update_process_status(username, job_title, company_name, f'Processing file: {filename}')
        with open(file_path, "r") as f:
            file_content = f.read()

        # Generate summary using ChatGPT
        summary = generate_summary(file_content)

        with app.app_context():
            db = next(get_db())
            job_title = job_title.lower().strip()
            company_name = company_name.lower().strip()

            new_training_data = TrainingData(
                job_title=job_title,
                company_name=company_name,
                data=summary,
                processed_files=filename
            )
            store_training_data(db, new_training_data)

        update_process_status(username, job_title, company_name, f'File processed successfully: {filename}')
    except Exception as e:
        logging.error(f"Error processing file {filename}: {str(e)}")
        update_process_status(username, job_title, company_name, f'Error processing file: {filename}')

def process_raw_text(job_title, company_name, raw_text, username):
    try:
        update_process_status(username, job_title, company_name, 'Processing raw text')

        # Generate summary using ChatGPT
        summary = generate_summary(raw_text)

        with app.app_context():
            db = next(get_db())
            job_title_lower = job_title.lower().strip()
            company_name_lower = company_name.lower().strip()

            existing_files = db.query(TrainingData.processed_files).filter_by(job_title=job_title_lower, company_name=company_name_lower).all()
            raw_text_count = sum(1 for files in existing_files for file in files.processed_files.split(',') if 'raw_text' in file)
            processed_file_name = f"raw_text_{raw_text_count + 1}"

            new_training_data = TrainingData(
                job_title=job_title_lower,
                company_name=company_name_lower,
                data=summary,
                processed_files=processed_file_name
            )
            store_training_data(db, new_training_data)

        update_process_status(username, job_title, company_name, f'Raw text processed successfully: {processed_file_name}')
    except Exception as e:
        logging.error(f"Error processing raw text: {str(e)}")
        update_process_status(username, job_title, company_name, 'Error processing raw text')
    cleanup_uploads_folder()

def download_and_transcribe(video, job_title, company_name, username):
    video_url = video['url']
    video_title = sanitize_filename(video['title'])

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(save_dir, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'cookiefile': cookies_file,
        'ffmpeg_location': ffmpeg_location
    }

    try:
        update_process_status(username, job_title, company_name, f'Downloading and transcribing video: {video_title}')
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            audio_file_path = ydl.prepare_filename(info_dict).replace('.webm', '.mp3')

        if not os.path.exists(audio_file_path):
            return

        model = whisper.load_model("base")
        result = model.transcribe(audio_file_path)

        transcription_file_name = f"{video_title}.txt"
        transcription_file_path = os.path.join(transcription_dir, transcription_file_name)
        with open(transcription_file_path, "w") as f:
            f.write(result["text"])

        os.remove(audio_file_path)

        with open(transcription_file_path, "r") as f:
            transcription_content = f.read()

        # Generate summary using ChatGPT
        summary = generate_summary(transcription_content)

        with app.app_context():
            db = next(get_db())
            job_title = job_title.lower().strip()
            company_name = company_name.lower().strip()

            new_training_data = TrainingData(
                job_title=job_title,
                company_name=company_name,
                data=summary,
                processed_files=transcription_file_name
            )
            store_training_data(db, new_training_data)

        update_process_status(username, job_title, company_name, f'Video transcribed: {video_title}')
    except Exception as e:
        logging.error(f"Error downloading and transcribing video {video_title}: {str(e)}")
        update_process_status(username, job_title, company_name, f'Error downloading/transcribing video: {video_title}')

def transcribe_videos(channel_id, num_videos, job_title, company_name, username):
    try:
        update_process_status(username, job_title, company_name, 'Transcribing videos')
        video_urls = get_video_urls_from_channel(channel_id, num_videos)
        for video in video_urls:
            download_and_transcribe(video, job_title.lower().strip(), company_name.lower().strip(), username)
        cleanup_uploads_folder()
        update_process_status(username, job_title, company_name, 'Videos transcribed successfully')
    except Exception as e:
        logging.error(f"Error transcribing videos: {str(e)}")
        update_process_status(username, job_title, company_name, 'Error transcribing videos')

def process_youtube_urls(youtube_urls, job_title, company_name, username):
    try:
        update_process_status(username, job_title, company_name, 'Processing YouTube URLs')
        for url in youtube_urls:
            video_id = url.split('v=')[-1]
            request = youtube.videos().list(part="snippet", id=video_id)
            response = request.execute()
            if response['items']:
                video_title = response['items'][0]['snippet']['title']
            else:
                video_title = 'Unknown Title'
            video = {
                'url': url,
                'title': video_title  # Use actual video title
            }
            download_and_transcribe(video, job_title.lower().strip(), company_name.lower().strip(), username)
        cleanup_uploads_folder()
        update_process_status(username, job_title, company_name, 'YouTube URLs processed successfully')
    except Exception as e:
        logging.error(f"Error processing YouTube URLs: {str(e)}")
        update_process_status(username, job_title, company_name, 'Error processing YouTube URLs')

def cleanup_uploads_folder():
    txt_files = glob.glob(os.path.join(app.config['UPLOAD_FOLDER'], '*.txt'))
    for txt_file in txt_files:
        try:
            os.remove(txt_file)
            logging.info(f"Deleted file: {txt_file}")
        except Exception as e:
            logging.error(f"Error deleting file {txt_file}: {e}")

def get_video_urls_from_channel(channel_id, num_videos):
    video_data = []
    next_page_token = None

    while len(video_data) < num_videos:
        request = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            maxResults=min(50, num_videos - len(video_data)),
            pageToken=next_page_token,
            type="video",
            order="date"
        )

        # Log the request URL for debugging
        logging.debug(f"Request URL: {request.uri}")

        try:
            response = request.execute()
        except Exception as e:
            logging.error(f"Error executing YouTube API request: {e}")
            raise e

        for item in response['items']:
            video_data.append({
                'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                'title': item['snippet']['title'],
                'publishedAt': item['snippet']['publishedAt']
            })

        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break

    video_data.sort(key=lambda x: datetime.strptime(x['publishedAt'], '%Y-%m-%dT%H:%M:%SZ'), reverse=True)
    return video_data[:num_videos]

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)
