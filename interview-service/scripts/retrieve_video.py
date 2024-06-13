import sys
import os
from dotenv import load_dotenv

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models import VideoRecordingLog
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load environment variables from a .env file
load_dotenv()

# Retrieve the DATABASE_URL from the environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("No DATABASE_URL found in environment variables")

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

video_id = 1  # Replace with the actual video ID

video_record = session.query(VideoRecordingLog).filter_by(id=video_id).first()

if video_record:
    video_data = video_record.video_data
    with open('retrieved_video.webm', 'wb') as f:
        f.write(video_data)
    print("Video data has been written to retrieved_video.webm")
else:
    print("No video record found with the specified ID")
