import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')  # Use a directory within your project
app.config['MAX_CONTENT_PATH'] = 100000

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Ensure the upload directory exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

from app import routes, models  # Import routes and models

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5011)
