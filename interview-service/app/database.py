from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from .config import Config

# Database setup
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))