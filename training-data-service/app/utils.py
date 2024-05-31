import os
from werkzeug.utils import secure_filename
import numpy as np
from app.models import TrainingData
from langchain_community.embeddings import OpenAIEmbeddings
import logging

def load_training_data(job_title, company_name):
    return TrainingData.query.filter_by(job_title=job_title, company_name=company_name).first()

def create_chunks_and_embeddings_from_file(file_path):
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


def create_chunks_and_embeddings(data):
    logging.debug("Processing raw text data")
    chunk_size = 1000
    chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
    embedder = OpenAIEmbeddings()
    embeddings = embedder.embed_documents(chunks)
    embedding_array = np.array(embeddings).astype('float32')
    logging.debug(f"Created {len(chunks)} chunks and embeddings for raw text")
    return chunks, embedding_array