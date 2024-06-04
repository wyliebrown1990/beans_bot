# interview-service/__init__.py
from flask import Flask
from .config import DATABASE_URL
from .utils import create_table_if_not_exists, setup_database
from .routes import setup_routes
from .models import Base

app = Flask(__name__)

# Setup database
engine, session = setup_database(DATABASE_URL)
Base.metadata.create_all(engine)  # Create tables based on models
create_table_if_not_exists(engine)

# Setup routes
setup_routes(app, session)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5013)
