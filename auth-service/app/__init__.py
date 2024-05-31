import os
from flask import Flask
from flask_login import LoginManager
from .config import Config
from .models import init_db

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
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

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5010)
