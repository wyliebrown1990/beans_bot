import os
from flask import Flask
from dotenv import load_dotenv
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from app.models import JobDescriptionAnalysis, ProcessStatus, User, Questions

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration settings
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key_here')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['MAX_CONTENT_PATH'] = 100000
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Allow up to 16 MB uploads

# Initialize Flask-Session
Session(app)

# Ensure the upload directory exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Initialize the database
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

# Import models
from app import models

# Create tables if they don't exist
models.Base.metadata.create_all(bind=engine)

# Import routes
from app.routes import setup_routes
setup_routes(app, db_session)
