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
    chunk_text = Column(String, nullable=False)
    embeddings = Column(LargeBinary, nullable=False)
    processed_files = Column(String, nullable=False)
    faiss_index_id = Column(Integer, ForeignKey('faiss_index.id'), nullable=True)
    faiss_index = relationship("FaissIndex", back_populates="training_data")

class FaissIndex(Base):
    __tablename__ = 'faiss_index'
    id = Column(Integer, primary_key=True)
    index_data = Column(LargeBinary, nullable=False)
    training_data = relationship("TrainingData", back_populates="faiss_index")

class ProcessStatus(Base):
    __tablename__ = 'process_status'
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, index=True)
    job_title = Column(String, nullable=False, index=True)
    company_name = Column(String, nullable=False, index=True)
    status = Column(Text, nullable=False)
