import os
import numpy as np
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import OpenAIEmbeddings
from werkzeug.utils import secure_filename
from docx import Document
import fitz  # PyMuPDF

from .models import User, SessionLocal, EmbeddingIDMapping

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_user_by_username(username):
    session = SessionLocal()
    try:
        return session.query(User).filter_by(username=username).first()
    finally:
        session.close()

def get_user_by_email(email):
    session = SessionLocal()
    try:
        return session.query(User).filter_by(email=email).first()
    finally:
        session.close()

def extract_text_from_file(file_path):
    _, file_extension = os.path.splitext(file_path)
    file_extension = file_extension.lower()
    
    if file_extension == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    elif file_extension == '.docx':
        doc = Document(file_path)
        return '\n'.join([para.text for para in doc.paragraphs])
    elif file_extension == '.pdf':
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    else:
        raise ValueError("Unsupported file format")

def create_chunks_and_embeddings_from_file(file_path, api_key):
    embedder = OpenAIEmbeddings(openai_api_key=api_key)
    data = extract_text_from_file(file_path)
    chunk_size = 1000
    chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
    embeddings = []
    for chunk in chunks:
        embedding = embedder.embed_documents([chunk])
        if isinstance(embedding, list) and len(embedding) == 1:
            embedding = np.array(embedding[0])  # Convert to NumPy array
        if embedding.shape[0] == 1536:  # Ensure embedding has correct dimensions
            embeddings.append(embedding)
        else:
            print(f"Skipping chunk with incorrect embedding shape: {embedding.shape}")
    if len(embeddings) == 0:
        raise ValueError("No valid embeddings generated.")
    embedding_array = np.vstack(embeddings).astype('float32')
    print(f"Final embedding array shape: {embedding_array.shape}")
    return chunks, embedding_array


def store_embeddings_and_mappings(db_session, user, embeddings, table_name):
    db_session.add(user)
    db_session.commit()
    for i, _ in enumerate(embeddings):
        mapping = EmbeddingIDMapping(db_id=user.id, faiss_id=i, table_name=table_name, username=user.username)
        db_session.add(mapping)
    db_session.commit()

