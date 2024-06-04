# interview-service/models.py
from sqlalchemy import create_engine, Column, Integer, String, Text, LargeBinary, TIMESTAMP, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class TrainingData(Base):
    __tablename__ = 'training_data'
    id = Column(Integer, primary_key=True)
    job_title = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=False)
    data = Column(Text, nullable=False)
    embeddings = Column(LargeBinary, nullable=True)
    processed_files = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

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

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    resume_embeddings = Column(LargeBinary, nullable=True)
    resume_data = Column(Text, nullable=True)  # New column for resume text data
    processed_files = Column(String(255), nullable=True)  # New column for file names
    created_at = Column(DateTime, default=datetime.utcnow)  # New column for timestamp

class EmbeddingIDMapping(Base):
    __tablename__ = 'embedding_id_mapping'
    id = Column(Integer, primary_key=True)
    db_id = Column(Integer, nullable=False)
    faiss_id = Column(Integer, nullable=False)
    table_name = Column(String(255), nullable=False)
    username = Column(String(150), nullable=False)
