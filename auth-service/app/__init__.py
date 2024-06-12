import os
from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv
from .config import Config
from .models import init_db

# Load environment variables from .env file
load_dotenv()

# Debugging: Print the loaded environment variables
print(f"DATABASE_URL: {os.getenv('DATABASE_URL')}")
print(f"SECRET_KEY: {os.getenv('SECRET_KEY')}")
print(f"OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY')}")

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Ensure the environment variable is loaded
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL is not set")
    
    # Configure the app
    app.config.from_object(Config)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url  # Set the database URL

    login_manager.init_app(app)
    init_db(app.config['SQLALCHEMY_DATABASE_URI'])
    
    # Ensure upload directory exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    with app.app_context():
        from .routes import auth_bp
        app.register_blueprint(auth_bp)
    
    login_manager.login_view = 'auth.login'
    
    app.debug = True  # Enable debug mode
    
    return app

app = create_app()
