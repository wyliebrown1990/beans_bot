from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from .config import Config
from .models import Base

# Database setup
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['DEBUG'] = True  # Enable debug mode

    Base.metadata.create_all(bind=engine)

    from .routes import main
    app.register_blueprint(main)

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()

    return app

app = create_app()
