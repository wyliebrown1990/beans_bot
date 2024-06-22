import os
import uuid
import glob
import requests
import json
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
from app.models import TrainingData, ProcessStatus
from app.database import get_db
from flask import current_app


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

# Initialize YouTube API client
youtube = build('youtube', 'v3', developerKey=youtube_api_key)

def get_save_dir(app):
    with app.app_context():
        save_dir = app.config['UPLOAD_FOLDER']
        transcription_dir = os.path.join(save_dir, "youtube")
        os.makedirs(transcription_dir, exist_ok=True)
    return save_dir, transcription_dir

def update_process_status(app, username, job_title, company_name, status):
    with app.app_context():
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



def process_file(app, file_path, job_title, company_name, username, user_id):
    with app.app_context():
        filename = os.path.basename(file_path)
        logging.debug(f"Processing file: {filename}")
        print(f"DEBUG: Processing file: {filename}, job_title: {job_title}, company_name: {company_name}, username: {username}, user_id: {user_id}")

        try:
            update_process_status(app, username, job_title, company_name, f'Processing file: {filename}')
            with open(file_path, "r") as f:
                file_content = f.read()
                print(f"DEBUG: File content loaded, length: {len(file_content)}")

            # Generate job description analysis using the new function
            analysis = get_job_description_analysis(file_content)
            print(f"DEBUG: Generated analysis: {analysis}")

            db = next(get_db())
            job_title = job_title.lower().strip()
            company_name = company_name.lower().strip()
            print(f"DEBUG: Inside app context, job_title: {job_title}, company_name: {company_name}, username: {username}, user_id: {user_id}")

            new_analysis = JobDescriptionAnalysis(
                user_id=user_id,
                job_title=analysis['job_details']['title'],
                job_level=analysis['job_details']['level'],
                job_location=analysis['job_details']['location'],
                job_type=analysis['job_details']['type'],
                job_salary=analysis['job_details']['salary'],
                job_responsibilities=json.dumps(analysis['job_details']['responsibilities']),
                personal_qualifications=json.dumps(analysis['job_details']['personal_qualifications']),
                company_name=analysis['company_information']['name'],
                company_size=analysis['company_information']['size'],
                company_industry=analysis['company_information']['industry'],
                company_mission_and_values=analysis['company_information']['mission_and_values'],
                education_background=json.dumps(analysis['requirements_and_qualifications']['education_background']),
                required_professional_experiences=json.dumps(analysis['requirements_and_qualifications']['required_professional_experiences']),
                nice_to_have_experiences=json.dumps(analysis['requirements_and_qualifications']['nice_to_have_experiences']),
                required_skill_sets=json.dumps(analysis['requirements_and_qualifications']['required_skill_sets'])
            )
            print(f"DEBUG: Prepared new_analysis: {new_analysis.__dict__}")
            store_analysis_data(db, new_analysis)

            update_process_status(app, username, job_title, company_name, f'File processed successfully: {filename}')
        except Exception as e:
            logging.error(f"Error processing file {filename}: {str(e)}")
            print(f"ERROR: Error processing file {filename}: {str(e)}")
            update_process_status(app, username, job_title, company_name, f'Error processing file: {filename}')
        finally:
            cleanup_uploads_folder(app)

def process_raw_text(app, job_title, company_name, raw_text, username, user_id):
    with app.app_context():
        try:
            update_process_status(app, username, job_title, company_name, 'Processing raw text')

            # Generate job description analysis using the new function
            analysis = get_job_description_analysis(raw_text)

            db = next(get_db())
            job_title_lower = job_title.lower().strip()
            company_name_lower = company_name.lower().strip()

            new_analysis = JobDescriptionAnalysis(
                user_id=user_id,
                job_title=analysis['job_details']['title'],
                job_level=analysis['job_details']['level'],
                job_location=analysis['job_details']['location'],
                job_type=analysis['job_details']['type'],
                job_salary=analysis['job_details']['salary'],
                job_responsibilities=json.dumps(analysis['job_details']['responsibilities']),
                personal_qualifications=json.dumps(analysis['job_details']['personal_qualifications']),
                company_name=analysis['company_information']['name'],
                company_size=analysis['company_information']['size'],
                company_industry=analysis['company_information']['industry'],
                company_mission_and_values=analysis['company_information']['mission_and_values'],
                education_background=json.dumps(analysis['requirements_and_qualifications']['education_background']),
                required_professional_experiences=json.dumps(analysis['requirements_and_qualifications']['required_professional_experiences']),
                nice_to_have_experiences=json.dumps(analysis['requirements_and_qualifications']['nice_to_have_experiences']),
                required_skill_sets=json.dumps(analysis['requirements_and_qualifications']['required_skill_sets'])
            )
            store_analysis_data(db, new_analysis)

            update_process_status(app, username, job_title, company_name, f'Raw text processed successfully')
        except Exception as e:
            logging.error(f"Error processing raw text: {str(e)}")
            update_process_status(app, username, job_title, company_name, 'Error processing raw text')
        finally:
            cleanup_uploads_folder(app)





def download_and_transcribe(app, video, job_title, company_name, username, user_id):
    with app.app_context():
        video_url = video['url']
        video_title = sanitize_filename(video['title'])

        save_dir, transcription_dir = get_save_dir(app)

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
            update_process_status(app, username, job_title, company_name, f'Downloading and transcribing video: {video_title}')
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

            db = next(get_db())
            job_title = job_title.lower().strip()
            company_name = company_name.lower().strip()

            new_training_data = TrainingData(
                user_id=user_id,
                job_title=job_title,
                company_name=company_name,
                file_summary=summary.get("file_summary", ""),
                top_topics=summary.get("top_topics", ""),
                primary_products_and_services=summary.get("primary_products_and_services", ""),
                target_market=summary.get("target_market", ""),
                market_position=summary.get("market_position", ""),
                required_skills=summary.get("required_skills", ""),
                unique_selling_proposition=summary.get("unique_selling_proposition", ""),
                processed_files=transcription_file_name
            )
            store_training_data(db, new_training_data)

            update_process_status(app, username, job_title, company_name, f'Video transcribed: {video_title}')
        except Exception as e:
            logging.error(f"Error downloading and transcribing video {video_title}: {str(e)}")
            update_process_status(app, username, job_title, company_name, f'Error downloading/transcribing video: {video_title}')
        finally:
            cleanup_uploads_folder(app)


def transcribe_videos(app, channel_id, num_videos, job_title, company_name, username, user_id):
    try:
        update_process_status(app, username, job_title, company_name, 'Transcribing videos')
        video_urls = get_video_urls_from_channel(channel_id, num_videos)
        for video in video_urls:
            download_and_transcribe(app, video, job_title.lower().strip(), company_name.lower().strip(), username, user_id)
        cleanup_uploads_folder(app)
        update_process_status(app, username, job_title, company_name, 'Videos transcribed successfully')
    except Exception as e:
        logging.error(f"Error transcribing videos: {str(e)}")
        update_process_status(app, username, job_title, company_name, 'Error transcribing videos')
    finally:
        cleanup_uploads_folder(app)

def process_youtube_urls(app, youtube_urls, job_title, company_name, username, user_id):
    try:
        update_process_status(app, username, job_title, company_name, 'Processing YouTube URLs')
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
            download_and_transcribe(app, video, job_title.lower().strip(), company_name.lower().strip(), username, user_id)
        cleanup_uploads_folder(app)
        update_process_status(app, username, job_title, company_name, 'YouTube URLs processed successfully')
    except Exception as e:
        logging.error(f"Error processing YouTube URLs: {str(e)}")
        update_process_status(app, username, job_title, company_name, 'Error processing YouTube URLs')
    finally:
        cleanup_uploads_folder(app)



def cleanup_uploads_folder(app):
    save_dir, transcription_dir = get_save_dir(app)

    # Remove all .txt files in the uploads folder
    txt_files = glob.glob(os.path.join(save_dir, '*.txt'))
    for txt_file in txt_files:
        try:
            os.remove(txt_file)
            logging.info(f"Deleted file: {txt_file}")
        except Exception as e:
            logging.error(f"Error deleting file {txt_file}: {e}")

    # Remove all .txt files in the uploads/youtube folder
    youtube_txt_files = glob.glob(os.path.join(transcription_dir, '*.txt'))
    for youtube_txt_file in youtube_txt_files:
        try:
            os.remove(youtube_txt_file)
            logging.info(f"Deleted file: {youtube_txt_file}")
        except Exception as e:
            logging.error(f"Error deleting file {youtube_txt_file}: {e}")



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


def get_job_description_analysis(job_description_text):
    openai_api_key = os.getenv('OPENAI_API_KEY')
    model = ChatOpenAI(openai_api_key=openai_api_key)

    prompt_text = """
    You are a professional Job Description analyst. Your job is to take the job description that I am sending you in my user message and extract the details below. Please extract the relevant information from the following job description and return the results in JSON format. The examples below are just examples of what you might find and extract from the job descriptions I send you. If a job description is missing any detail, then return a JSON value of null for that field.

    Desired Output in JSON Format:

    {{
      "job_details": {{
        "title": "Senior Software Engineer",
        "level": "Mid-Senior level",
        "location": "New York, NY (Hybrid)",
        "type": "Full-time",
        "salary": "$175K/yr - $205K/yr",
        "responsibilities": [
          "Lead design and implementation of technical solutions",
          "Collaborate with product designers, product managers, and other engineers",
          "Investigate design approaches, prototype technology",
          "Continuous improvement in software and development processes",
          "Write automated tests",
          "Mentor other engineers"
        ],
        "personal_qualifications": [
          "Excellent written, verbal, and presentation skills",
          "Ability to thrive in a fast-paced startup environment",
          "Detail oriented with excellent organizational skills",
          "Ability to work independently and be a self-motivator"
        ]
      }},
      "company_information": {{
        "name": "K Health",
        "size": "201-500 employees",
        "industry": "Telehealth and AI Healthcare",
        "mission_and_values": "Use the power of AI to get everyone access to higher quality healthcare at more affordable costs"
      }},
      "requirements_and_qualifications": {{
        "education_background": [
          "Bachelor's degree in Computer Science, Engineering, or a related field"
        ],
        "required_professional_experiences": [
          "5+ years of software engineering experience",
          "Experience with highly-scalable, distributed systems",
          "Experience in designing and developing services with APIs"
        ],
        "nice_to_have_experiences": [
          "Experience with modern cloud technologies such as Docker, Kubernetes, Kafka, GCP/AWS suite"
        ],
        "required_skill_sets": [
          "Node.js",
          "TypeScript",
          "GraphQL",
          "Apollo Federation",
          "Problem Solving",
          "Excellent verbal and written communication skills"
        ]
      }}
    }}
    """

    messages = [
        SystemMessage(content=prompt_text),
        HumanMessage(content=job_description_text)
    ]

    response = model(messages)

    # Extract response content
    response_content = response.content.strip()

    # Print the response content for debugging
    print("Response Content:", response_content)

    response_json = json.loads(response_content)  # Ensure response is valid JSON

    # Print the parsed JSON data for debugging
    print("Response JSON:", response_json)

    return response_json

def store_analysis_data(db_session, analysis_data):
    with current_app.app_context():
        logging.debug(f"Storing analysis data: {analysis_data}")
        db_session.add(analysis_data)
        try:
            db_session.commit()  # Ensure the session is committed
            logging.debug(f"Stored analysis data with ID: {analysis_data.id}")
            print(f"DEBUG: Analysis data stored with ID: {analysis_data.id}")
        except Exception as e:
            logging.error(f"Error committing analysis data to the database: {str(e)}")
            print(f"ERROR: Error committing analysis data to the database: {str(e)}")
            db_session.rollback()
            raise e
