from flask import Flask, send_from_directory
from .config import DATABASE_URL
from .utils import create_table_if_not_exists, setup_database
from .routes import setup_routes
from .models import Base, TrainingData, InterviewAnswer, User
import os

app = Flask(__name__)

# Setup database
engine, session = setup_database(DATABASE_URL)
Base.metadata.create_all(engine)  # Create tables based on models
create_table_if_not_exists(engine)

# Setup routes
setup_routes(app, session)

# Serve static files from audio_files directory
@app.route('/audio_files/<path:filename>')
def serve_audio(filename):
    directory = os.path.join(app.root_path, '..', 'audio_files')
    file_path = os.path.join(directory, filename)
    print(f"Serving audio file from: {file_path}")
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
    return send_from_directory(directory, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5013)
