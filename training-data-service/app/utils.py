import os
import glob
import requests
from sqlalchemy.orm import Session
from werkzeug.utils import secure_filename
import numpy as np
from app.models import TrainingData
from langchain_openai import OpenAIEmbeddings
import logging
from app import app
from app.database import get_db
import re
import yt_dlp
import whisper
from googleapiclient.discovery import build
from datetime import datetime
import faiss

# Load environment variables
youtube_api_key = os.getenv('GOOGLE_API_KEY')
cookies_file = os.getenv('COOKIES_FILE')
ffmpeg_location = os.getenv('FFMPEG_LOCATION')
save_dir = app.config['UPLOAD_FOLDER']
transcription_dir = os.path.join(save_dir, "youtube")
os.makedirs(transcription_dir, exist_ok=True)

# Initialize YouTube API client
youtube = build('youtube', 'v3', developerKey=youtube_api_key)

FAISS_INDEX_PATH = os.path.join('beans_bot', 'training-data-service', 'faiss_index.idx')

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

def create_chunks_and_embeddings_from_file(file_path: str):
    logging.debug(f"Processing file: {file_path}")
    with open(file_path, "r") as f:
        data = f.read()
    chunk_size = 1000
    chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
    embedder = OpenAIEmbeddings()
    embeddings = []
    for i, chunk in enumerate(chunks):
        embedding = embedder.embed_documents([chunk])
        if isinstance(embedding, list) and len(embedding) == 1:
            embedding = np.array(embedding[0])  # Convert to NumPy array
        logging.debug(f"Chunk {i} embedding shape: {embedding.shape}")
        if embedding.shape[0] == 1536:  # Ensure embedding has correct dimensions
            embeddings.append(embedding)
        else:
            logging.error(f"Chunk {i} has incorrect embedding shape: {embedding.shape}. Skipping this chunk.")
    if len(embeddings) == 0:
        raise ValueError("No valid embeddings generated.")
    embedding_array = np.vstack(embeddings).astype('float32')
    logging.debug(f"Created {len(chunks)} chunks and embeddings")
    return chunks, embedding_array


def create_chunks_and_embeddings(data: str):
    logging.debug("Processing raw text data")
    chunk_size = 1000
    chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
    embedder = OpenAIEmbeddings()
    embeddings = []
    for i, chunk in enumerate(chunks):
        embedding = embedder.embed_documents([chunk])
        if isinstance(embedding, list) and len(embedding) == 1:
            embedding = np.array(embedding[0])  # Convert to NumPy array
        logging.debug(f"Chunk {i} embedding shape: {embedding.shape}")
        if embedding.shape[0] == 1536:  # Ensure embedding has correct dimensions
            embeddings.append(embedding)
        else:
            logging.error(f"Chunk {i} has incorrect embedding shape: {embedding.shape}. Skipping this chunk.")
    if len(embeddings) == 0:
        raise ValueError("No valid embeddings generated.")
    embedding_array = np.vstack(embeddings).astype('float32')
    logging.debug(f"Created {len(chunks)} chunks and embeddings for raw text")
    return chunks, embedding_array



def store_training_data(db_session, training_data):
    logging.debug(f"Storing training data: {training_data}")
    logging.debug(f"Data: {training_data.data[:100]}...")  # Log first 100 characters of data
    db_session.add(training_data)
    db_session.commit()  # Ensure the session is committed
    logging.debug(f"Stored training data with ID: {training_data.id}")

# Update FAISS index

def normalize_l2(x):
    x = np.array(x)
    if x.ndim == 1:
        norm = np.linalg.norm(x)
        if norm == 0:
            return x
        return x / norm
    else:
        norm = np.linalg.norm(x, 2, axis=1, keepdims=True)
        return np.where(norm == 0, x, x / norm)

def check_existing_embeddings(db_session: Session, expected_dim: int = 1536):
    all_embeddings = db_session.query(TrainingData.embeddings).all()
    for i, embedding in enumerate(all_embeddings):
        if embedding[0]:
            array = np.frombuffer(embedding[0], dtype=np.float32)
            if array.shape[0] != expected_dim:
                logging.error(f"Existing embedding at index {i} has incorrect shape: {array.shape}")
                db_session.query(TrainingData).filter(TrainingData.embeddings == embedding[0]).delete()
    db_session.commit()

def update_faiss_index(db_session: Session):
    # Directory where the FAISS index file will be stored
    faiss_index_path = os.path.join(os.getcwd(), 'beans_bot', 'training-data-service', 'faiss_index.idx')
    faiss_index_dir = os.path.dirname(faiss_index_path)

    # Ensure the directory exists
    if not os.path.exists(faiss_index_dir):
        os.makedirs(faiss_index_dir)

    # Check existing embeddings and remove incorrect ones
    check_existing_embeddings(db_session)

    # Retrieve all embeddings from the database
    all_embeddings = db_session.query(TrainingData.embeddings).all()
    embeddings = [normalize_l2(np.frombuffer(embedding[0], dtype=np.float32)) for embedding in all_embeddings if embedding[0]]

    if embeddings:
        # Create a FAISS index
        embeddings_matrix = np.vstack(embeddings)
        index = faiss.IndexFlatL2(embeddings_matrix.shape[1])
        index.add(embeddings_matrix)
        
        # Save the FAISS index to a file
        faiss.write_index(index, faiss_index_path)
        logging.debug(f"FAISS index updated and saved to {faiss_index_path}")
    else:
        logging.debug("No embeddings found to create FAISS index.")

def process_file(file_path, job_title, company_name, username):
    filename = os.path.basename(file_path)
    logging.debug(f"Processing file: {filename}")

    try:
        update_process_status(username, job_title, company_name, f'Processing file: {filename}')
        chunks, embedding_array = create_chunks_and_embeddings_from_file(file_path)
        logging.debug(f"Created chunks and embeddings for file: {filename}")

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
                processed_files=filename
            )
            db.add(new_training_data)
            store_training_data(db, new_training_data)

            # Update FAISS index
            update_faiss_index(db)
            
            db.commit()
            logging.debug(f"Committed changes to the database for file: {filename}")
        update_process_status(username, job_title, company_name, f'File processed successfully: {filename}')
    except Exception as e:
        logging.error(f"Error processing file {filename}: {str(e)}")
        update_process_status(username, job_title, company_name, f'Error processing file: {filename}')

def process_raw_text(job_title, company_name, raw_text, username):
    try:
        update_process_status(username, job_title, company_name, 'Processing raw text')
        chunks, embedding_array = create_chunks_and_embeddings(raw_text)
        logging.debug(f"Created chunks and embeddings for raw text")

        with app.app_context():
            db = next(get_db())
            job_title = job_title.lower().strip()
            company_name = company_name.lower().strip()

            existing_files = db.query(TrainingData.processed_files).filter_by(job_title=job_title, company_name=company_name).all()
            raw_text_count = sum(1 for files in existing_files for file in files.processed_files.split(',') if 'raw_text' in file)
            processed_file_name = f"raw_text_{raw_text_count + 1}"

            new_training_data = TrainingData(
                job_title=job_title,
                company_name=company_name,
                data='\n'.join(chunks),
                chunk_text='\n'.join(chunks),
                embeddings=embedding_array.tobytes(),
                processed_files=processed_file_name
            )
            db.add(new_training_data)
            store_training_data(db, new_training_data)

            # Update FAISS index
            update_faiss_index(db)

            db.commit()
        update_process_status(username, job_title, company_name, f'Raw text processed successfully: {processed_file_name}')
    except Exception as e:
        logging.error(f"Error processing raw text: {str(e)}")
        update_process_status(username, job_title, company_name, 'Error processing raw text')
    cleanup_uploads_folder()

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
        # Ensure the directory for the transcription file exists
        if not os.path.exists(os.path.dirname(transcription_file_path)):
            os.makedirs(os.path.dirname(transcription_file_path))

        with open(transcription_file_path, "w") as f:
            f.write(result["text"])

        os.remove(audio_file_path)

        chunks, embedding_array = create_chunks_and_embeddings_from_file(transcription_file_path)

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
            store_training_data(db, new_training_data)

            # Update FAISS index
            update_faiss_index(db)

            db.commit()
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

def query_faiss_index(query: str):
    if not os.path.exists(FAISS_INDEX_PATH):
        logging.error(f"FAISS index file not found at {FAISS_INDEX_PATH}")
        return "Career context from FAISS index based on the query."

    try:
        index = faiss.read_index(FAISS_INDEX_PATH)
        embedder = OpenAIEmbeddings()
        query_embedding = embedder.embed_query(query)
        query_vector = np.array(query_embedding, dtype=np.float32)
        D, I = index.search(query_vector.reshape(1, -1), 5)
        results = [index.reconstruct(int(idx)) for idx in I[0]]
        logging.debug(f"FAISS query results: {results}")
        return results[0] if results else "No relevant data found in the FAISS index."
    except Exception as e:
        logging.error(f"Error querying FAISS index: {str(e)}")
        return "Error querying FAISS index."
