from sqlalchemy import create_engine, Column, Integer, String, Text, LargeBinary, TIMESTAMP, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from flask_login import UserMixin

Base = declarative_base()

class TrainingData(Base):
    __tablename__ = 'training_data'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    job_title = Column(String(100), nullable=False)
    company_name = Column(String(100), nullable=False)
    file_summary = Column(String, nullable=False)
    processed_files = Column(String, nullable=False)
    top_topics = Column(Text, nullable=True)
    primary_products_and_services = Column(Text, nullable=True)
    target_market = Column(Text, nullable=True)
    market_position = Column(Text, nullable=True)
    required_skills = Column(Text, nullable=True)
    unique_selling_proposition = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class InterviewAnswer(Base):
    __tablename__ = 'interview_answers'
    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), nullable=False)  # Add this line
    job_title = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=False)
    industry = Column(String(255), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    critique = Column(Text, nullable=False)
    score = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class User(UserMixin, Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    resume_text_full = Column(Text, nullable=True)
    top_technical_skills = Column(Text, nullable=True)
    most_recent_job_title = Column(String(255), nullable=True)
    most_recent_company_name = Column(String(255), nullable=True)
    most_recent_experience_summary = Column(Text, nullable=True)
    industry_expertise = Column(Text, nullable=True)
    top_soft_skills = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class VideoRecordingLog(Base):
    __tablename__ = 'video_recording_log'
    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), nullable=False)
    user_id = Column(Integer, nullable=False)
    job_role = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=False)
    video_data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
