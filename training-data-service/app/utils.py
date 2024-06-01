import os
from sqlalchemy.orm import Session
from werkzeug.utils import secure_filename
import numpy as np
from app.models import TrainingData
from langchain_community.embeddings import OpenAIEmbeddings
import logging

def load_training_data(db: Session, job_title: str, company_name: str):
    return db.query(TrainingData).filter_by(job_title=job_title, company_name=company_name).first()

def create_chunks_and_embeddings_from_file(file_path: str):
    logging.debug(f"Processing file: {file_path}")
    with open(file_path, "r") as f:
        data = f.read()
    chunk_size = 1000
    chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
    embedder = OpenAIEmbeddings()
    embeddings = embedder.embed_documents(chunks)
    embedding_array = np.array(embeddings).astype('float32')
    logging.debug(f"Created {len(chunks)} chunks and embeddings")
    return chunks, embedding_array

def create_chunks_and_embeddings(data: str):
    logging.debug("Processing raw text data")
    chunk_size = 1000
    chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
    embedder = OpenAIEmbeddings()
    embeddings = embedder.embed_documents(chunks)
    embedding_array = np.array(embeddings).astype('float32')
    logging.debug(f"Created {len(chunks)} chunks and embeddings for raw text")
    return chunks, embedding_array
