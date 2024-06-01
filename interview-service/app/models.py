from sqlalchemy import create_engine, Column, Integer, String, Text, LargeBinary, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

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
