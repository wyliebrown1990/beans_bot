from sqlalchemy import Column, Integer, String, LargeBinary, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base

class TrainingData(Base):
    __tablename__ = 'training_data'
    id = Column(Integer, primary_key=True, index=True)
    job_title = Column(String, index=True)
    company_name = Column(String, index=True)
    data = Column(String)
    chunk_text = Column(String, nullable=False)
    embeddings = Column(LargeBinary)
    processed_files = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ProcessStatus(Base):
    __tablename__ = 'process_status'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, index=True)
    job_title = Column(String, nullable=False, index=True)
    company_name = Column(String, nullable=False, index=True)
    status = Column(Text, nullable=False)
