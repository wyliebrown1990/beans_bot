import os
from flask import Flask
from dotenv import load_dotenv
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration settings
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key_here')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['MAX_CONTENT_PATH'] = 100000

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

# Import routes
from app import routes

# Create tables if they don't exist
models.Base.metadata.create_all(bind=engine)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5011)
