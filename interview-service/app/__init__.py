from flask import Flask
from .config import Config
from .models import Base
from .database import db_session, engine  # Import from the new database module
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['DEBUG'] = True  # Enable debug mode

    Base.metadata.create_all(bind=engine)

    try:
        logger.debug("Attempting to import blueprints")
        from .routes import first_round_bp, second_round_bp, third_round_bp
        logger.debug("Imports successful")
    except ImportError as e:
        logger.error(f"Import error: {e}")
        raise

    app.register_blueprint(first_round_bp, url_prefix='/first_round')
    app.register_blueprint(second_round_bp, url_prefix='/second_round')
    app.register_blueprint(third_round_bp, url_prefix='/third_round')

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()

    return app

logger.debug("Creating app")
app = create_app()
logger.debug("App created")
