from sqlalchemy import Column, Integer, String, LargeBinary
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

