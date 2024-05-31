import os
import numpy as np
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import OpenAIEmbeddings
from werkzeug.utils import secure_filename
from docx import Document
import fitz  # PyMuPDF

from .models import User, SessionLocal

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
    model = ChatOpenAI(model="gpt-3.5-turbo", api_key=api_key, temperature=0.5)
    embedder = OpenAIEmbeddings(openai_api_key=api_key)
    
    data = extract_text_from_file(file_path)
    
    chunk_size = 1000
    chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
    embeddings = embedder.embed_documents(chunks)
    embedding_array = np.array(embeddings).astype('float32')
    
    return chunks, embedding_array
