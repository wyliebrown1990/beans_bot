from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

Base = declarative_base()
engine = None
SessionLocal = None

def init_db(db_url):
    global engine
    global SessionLocal
    engine = create_engine(db_url)
    SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
    Base.metadata.create_all(bind=engine)

class User(UserMixin, Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    resume_text_full = Column(Text, nullable=True)
    key_technical_skills = Column(Text, nullable=True)
    key_soft_skills = Column(Text, nullable=True)
    most_recent_job_title = Column(String(255), nullable=True)
    second_most_recent_job_title = Column(String(255), nullable=True)
    most_recent_job_title_summary = Column(Text, nullable=True)
    second_most_recent_job_title_summary = Column(Text, nullable=True)
    top_listed_skill_keyword = Column(String(255), nullable=True)
    second_most_top_listed_skill_keyword = Column(String(255), nullable=True)
    third_most_top_listed_skill_keyword = Column(String(255), nullable=True)
    fourth_most_top_listed_skill_keyword = Column(String(255), nullable=True)
    educational_background = Column(Text, nullable=True)
    certifications_and_awards = Column(Text, nullable=True)
    most_recent_successful_project = Column(Text, nullable=True)
    areas_for_improvement = Column(Text, nullable=True)
    questions_about_experience = Column(Text, nullable=True)
    resume_length = Column(Text, nullable=True)
    top_challenge = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
