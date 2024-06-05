from sqlalchemy import Column, Integer, String, LargeBinary
from app.database import Base

class TrainingData(Base):
    __tablename__ = 'training_data'
    id = Column(Integer, primary_key=True, index=True)
    job_title = Column(String, index=True)
    company_name = Column(String, index=True)
    data = Column(String)
    embeddings = Column(LargeBinary)
    processed_files = Column(String)

class EmbeddingIDMapping(Base):
    __tablename__ = 'embedding_id_mapping'
    id = Column(Integer, primary_key=True)
    db_id = Column(Integer, nullable=False)
    faiss_id = Column(Integer, nullable=False)
    table_name = Column(String(255), nullable=False)
    username = Column(String(150), nullable=False)  # Ensure this field is included
    chunk_text = Column(String, nullable=False)  # Add this line to store the chunk text
