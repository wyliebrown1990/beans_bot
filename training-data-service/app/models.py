from sqlalchemy import Column, Integer, String, LargeBinary, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TrainingData(Base):
    __tablename__ = 'training_data'
    id = Column(Integer, primary_key=True)
    job_title = Column(String(100), nullable=False)
    company_name = Column(String(100), nullable=False)
    data = Column(String, nullable=False)
    processed_files = Column(String, nullable=False)

class ProcessStatus(Base):
    __tablename__ = 'process_status'
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, index=True)
    job_title = Column(String, nullable=False, index=True)
    company_name = Column(String, nullable=False, index=True)
    status = Column(Text, nullable=False)