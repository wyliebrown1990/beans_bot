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
    job_title = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=False)
    data = Column(Text, nullable=False)
    chunk_text = Column(Text, nullable=False)
    embeddings = Column(LargeBinary, nullable=False)
    processed_files = Column(Text, nullable=True)
    faiss_index_id = Column(Integer, ForeignKey('faiss_index.id'), nullable=True)
    faiss_index = relationship("FaissIndex", back_populates="training_data")

class FaissIndex(Base):
    __tablename__ = 'faiss_index'
    id = Column(Integer, primary_key=True)
    index_data = Column(LargeBinary, nullable=False)
    training_data = relationship("TrainingData", back_populates="faiss_index")

class InterviewAnswer(Base):
    __tablename__ = 'interview_answers'
    id = Column(Integer, primary_key=True)
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
