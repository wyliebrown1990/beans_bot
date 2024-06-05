from flask import render_template, request, redirect, jsonify, url_for
from app import app
from app.database import get_db
from app.models import TrainingData
from app.utils import secure_filename, load_training_data, create_chunks_and_embeddings_from_file, create_chunks_and_embeddings, store_training_data, process_raw_text, process_file
import os
import threading
import logging
from googleapiclient.discovery import build
import yt_dlp
import whisper
from datetime import datetime
import re
import numpy as np
import glob


logging.basicConfig(level=logging.DEBUG)

# Global variable to store transcriptions
transcriptions = []
status = []

# Load environment variables
youtube_api_key = os.getenv('GOOGLE_API_KEY')
cookies_file = os.getenv('COOKIES_FILE')
ffmpeg_location = os.getenv('FFMPEG_LOCATION')
save_dir = app.config['UPLOAD_FOLDER']
transcription_dir = os.path.join(save_dir, "youtube")
os.makedirs(transcription_dir, exist_ok=True)

# Initialize YouTube API client
youtube = build('youtube', 'v3', developerKey=youtube_api_key)

# Function to delete files from uploads folder after processed
def cleanup_uploads_folder():
    txt_files = glob.glob(os.path.join(save_dir, '*.txt'))
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

def download_and_transcribe(video, job_title, company_name, username):
    global status
    video_url = video['url']
    video_title = sanitize_filename(video['title'])

    status.append(f"Downloading {video_title}")

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

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_url, download=True)
        audio_file_path = ydl.prepare_filename(info_dict).replace('.webm', '.mp3')

    if not os.path.exists(audio_file_path):
        status.append(f"Error: Audio file not found for {video_title}")
        return

    status.append(f"Saving TXT file {video_title}")

    model = whisper.load_model("base")
    result = model.transcribe(audio_file_path)

    transcription_file_name = f"{video_title}.txt"
    transcription_file_path = os.path.join(transcription_dir, transcription_file_name)
    # Ensure the directory for the transcription file exists
    if not os.path.exists(os.path.dirname(transcription_file_path)):
        os.makedirs(os.path.dirname(transcription_file_path))

    with open(transcription_file_path, "w") as f:
        f.write(result["text"])

    os.remove(audio_file_path)

    status.append(f"Chunking {video_title}")
    chunks, embedding_array = create_chunks_and_embeddings_from_file(transcription_file_path)

    status.append(f"Embedding {video_title}")

    with app.app_context():
        db = next(get_db())
        job_title = job_title.lower().strip()
        company_name = company_name.lower().strip()
        new_training_data = TrainingData(
            job_title=job_title,
            company_name=company_name,
            data='\n'.join(chunks),
            chunk_text='\n'.join(chunks),
            embeddings=embedding_array.tobytes(),
            processed_files=transcription_file_name  # Save only the file name
        )
        db.add(new_training_data)
        db.commit()
        store_training_data(db, new_training_data)

    status.append(f"{video_title} complete")

def transcribe_videos(channel_id, num_videos, job_title, company_name, username):
    global status
    status = []
    try:
        video_urls = get_video_urls_from_channel(channel_id, num_videos)
        for video in video_urls:
            download_and_transcribe(video, job_title.lower().strip(), company_name.lower().strip(), username)
        status.append("All videos processed successfully")
        cleanup_uploads_folder()
    except Exception as e:
        status.append(f"Error: {str(e)}")

@app.route('/youtube_transcription', methods=['POST'])
def youtube_transcription():
    global status
    status = []
    job_title = request.form['job_title']
    company_name = request.form['company_name']
    industry = request.form['industry']
    username = request.form['username']
    channel_id = request.form['channel_id']
    num_videos = int(request.form['num_videos'])
    threading.Thread(target=transcribe_videos, args=(channel_id, num_videos, job_title.lower().strip(), company_name.lower().strip(), username)).start()
    return redirect(url_for('progress', job_title=job_title.lower().strip(), company_name=company_name.lower().strip(), industry=industry.lower().strip(), username=username))

@app.route('/youtube_urls_transcription', methods=['POST'])
def youtube_urls_transcription():
    global status
    status = []
    job_title = request.form['job_title']
    company_name = request.form['company_name']
    industry = request.form['industry']
    username = request.form['username']
    youtube_urls = request.form['youtube_urls'].strip().split('\n')
    youtube_urls = [url.strip() for url in youtube_urls if url.strip()]
    threading.Thread(target=process_youtube_urls, args=(youtube_urls, job_title, company_name, username)).start()
    return redirect(url_for('progress', job_title=job_title.lower().strip(), company_name=company_name.lower().strip(), industry=industry.lower().strip(), username=username))

def process_youtube_urls(youtube_urls, job_title, company_name, username):
    global status
    status = []
    try:
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
        status.append("All videos processed successfully")
        cleanup_uploads_folder()
    except Exception as e:
        status.append(f"Error: {str(e)}")

@app.route('/file_upload', methods=['POST'])
def file_upload():
    global status
    status = []
    job_title = request.form['job_title']
    company_name = request.form['company_name']
    industry = request.form['industry']
    username = request.form['username']
    files = request.files.getlist('files')

    for file in files:
        if file and file.filename.endswith('.txt'):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            # Start a new thread for further processing after saving the file
            threading.Thread(target=process_file, args=(file_path, job_title, company_name, username)).start()

    return redirect(url_for('progress', job_title=job_title, company_name=company_name, industry=industry, username=username))


@app.route('/raw_text_submission', methods=['POST'])
def raw_text_submission():
    global status
    status = []
    job_title = request.form['job_title']
    company_name = request.form['company_name']
    industry = request.form['industry']
    username = request.form['username']
    raw_text = request.form['raw_text']
    threading.Thread(target=process_raw_text, args=(job_title, company_name, raw_text, username)).start()
    return redirect(url_for('progress', job_title=job_title, company_name=company_name, industry=industry, username=username))

@app.route('/progress')
def progress():
    global status
    job_title = request.args.get('job_title')
    company_name = request.args.get('company_name')
    industry = request.args.get('industry')
    username = request.args.get('username')
    return render_template('progress.html', job_title=job_title, company_name=company_name, industry=industry, username=username, status=status)

@app.route('/progress_data')
def progress_data():
    global status
    return jsonify(status)

@app.route('/upload_options', methods=['GET'])
def upload_options():
    job_title = request.args.get('job_title')
    company_name = request.args.get('company_name')
    industry = request.args.get('industry')
    username = request.args.get('username')

    # Perform the lookup in the TrainingData table
    with app.app_context():
        db = next(get_db())
        training_data_exists = db.query(TrainingData).filter_by(job_title=job_title, company_name=company_name).first() is not None

    if training_data_exists:
        message = f"It looks like I already have training data on the {job_title} job at {company_name} company. Feel free to add more or proceed to interview now."
    else:
        message = f"It looks like I don't have any training data on the {job_title} job at {company_name} company. If you want a more targeted interview please add more, otherwise, feel free to move onto a more generic interview experience."

    return render_template('upload_options.html', job_title=job_title, company_name=company_name, industry=industry, username=username, message=message)

@app.route('/', methods=['GET', 'POST'])
def index():
    username = request.args.get('username')
    if request.method == 'POST':
        job_title = request.form['job_title']
        company_name = request.form['company_name']
        industry = request.form['industry']
        username = request.form['username']  # Ensure username is taken from the form

        # Perform the lookup in the TrainingData table
        with app.app_context():
            db = next(get_db())
            training_data_exists = db.query(TrainingData).filter_by(job_title=job_title, company_name=company_name).first() is not None

        if training_data_exists:
            message = f"It looks like I already have training data on the {job_title} job at {company_name} company. Feel free to add more or proceed to interview now."
        else:
            message = f"It looks like I don't have any training data on the {job_title} job at {company_name} company. If you want a more targeted interview please add more, otherwise, feel free to move onto a more generic interview experience."

        return redirect(url_for('upload_options', job_title=job_title, company_name=company_name, industry=industry, username=username))

    return render_template('index.html', username=username)
