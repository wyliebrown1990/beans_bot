import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from flask_session import Session

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Configuration settings
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key_here')  # Ensure this line is added
app.config['SESSION_TYPE'] = 'filesystem'  # This can be 'filesystem', 'redis', etc.
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')  # Use a directory within your project
app.config['MAX_CONTENT_PATH'] = 100000

# Initialize Flask-Session
Session(app)

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Ensure the upload directory exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Import routes and models after app and db initialization
from app import routes, models

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5011)
