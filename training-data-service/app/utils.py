import os
from sqlalchemy.orm import Session
from werkzeug.utils import secure_filename
import numpy as np
from app.models import TrainingData, EmbeddingIDMapping
from langchain_community.embeddings import OpenAIEmbeddings
import logging

def load_training_data(db: Session, job_title: str, company_name: str):
    logging.debug(f"Loading training data for job title: {job_title}, company name: {company_name}")
    training_data = db.query(TrainingData).filter_by(job_title=job_title, company_name=company_name).first()
    logging.debug(f"Retrieved training data: {training_data}")
    if training_data:
        logging.debug(f"Data: {training_data.data[:100]}...")  # Log first 100 characters of data
    return training_data

def create_chunks_and_embeddings_from_file(file_path: str):
    logging.debug(f"Processing file: {file_path}")
    with open(file_path, "r") as f:
        data = f.read()
    chunk_size = 1000
    chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
    embedder = OpenAIEmbeddings()
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
    logging.debug(f"Created {len(chunks)} chunks and embeddings")
    return chunks, embedding_array

def create_chunks_and_embeddings(data: str):
    logging.debug("Processing raw text data")
    chunk_size = 1000
    chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
    embedder = OpenAIEmbeddings()
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
    logging.debug(f"Created {len(chunks)} chunks and embeddings for raw text")
    return chunks, embedding_array

def store_training_data_and_mappings(db_session, training_data, embeddings, username, chunks):
    logging.debug(f"Storing training data: {training_data}")
    logging.debug(f"Data: {training_data.data[:100]}...")  # Log first 100 characters of data
    logging.debug(f"Embeddings: {len(embeddings)} embeddings")
    db_session.add(training_data)
    db_session.commit()
    logging.debug(f"Stored training data with ID: {training_data.id}")
    
    for i, chunk in enumerate(chunks):
        mapping = EmbeddingIDMapping(db_id=training_data.id, faiss_id=i, table_name='training_data', username=username, chunk_text=chunk)
        db_session.add(mapping)
    db_session.commit()
    logging.debug("Stored embedding ID mappings")





def process_file(file, job_title, company_name, username):
    global status
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    logging.debug(f"Saved file to {file_path}")

    status.append(f"Processing {filename}")
    chunks, embedding_array = create_chunks_and_embeddings_from_file(file_path)
    logging.debug(f"Created chunks and embeddings for file: {filename}")

    with app.app_context():
        db = next(get_db())
        job_title = job_title.lower().strip()
        company_name = company_name.lower().strip()
        training_data = load_training_data(db, job_title, company_name)
        existing_files = training_data.processed_files.split(',') if training_data and training_data.processed_files else []
        
        if filename not in existing_files:
            if training_data:
                logging.debug(f"Updating existing training data with ID: {training_data.id}")
                training_data.data += '\n' + '\n'.join(chunks)
                existing_embeddings = np.frombuffer(training_data.embeddings, dtype='float32').reshape(-1, 1536)
                if embedding_array.size > 0:
                    if len(embedding_array.shape) == 1:
                        embedding_array = embedding_array.reshape(1, -1)
                    training_data.embeddings = np.concatenate((existing_embeddings, embedding_array), axis=0).tobytes()
                training_data.processed_files += ',' + filename
            else:
                logging.debug("Creating new training data entry")
                new_training_data = TrainingData(
                    job_title=job_title,
                    company_name=company_name,
                    data='\n'.join(chunks),
                    embeddings=embedding_array.tobytes(),
                    processed_files=filename
                )
                db.add(new_training_data)
                training_data = new_training_data
            store_training_data_and_mappings(db, training_data, embedding_array, username)
        db.commit()
        logging.debug(f"Committed changes to the database for file: {filename}")
    status.append(f"{filename} uploaded")

def process_raw_text(job_title, company_name, raw_text, username):
    global status
    status.append(f"Processing raw text for {job_title} at {company_name}")
    chunks, embedding_array = create_chunks_and_embeddings(raw_text)
    with app.app_context():
        db = next(get_db())
        job_title = job_title.lower().strip()
        company_name = company_name.lower().strip()
        training_data = load_training_data(db, job_title, company_name)
        if training_data:
            training_data.data += '\n' + '\n'.join(chunks)
            existing_embeddings = np.frombuffer(training_data.embeddings, dtype='float32').reshape(-1, 1536)
            if embedding_array.size > 0:
                if len(embedding_array.shape) == 1:
                    embedding_array = embedding_array.reshape(1, -1)
                training_data.embeddings = np.concatenate((existing_embeddings, embedding_array), axis=0).tobytes()
        else:
            new_training_data = TrainingData(
                job_title=job_title,
                company_name=company_name,
                data='\n'.join(chunks),
                embeddings=embedding_array.tobytes(),
            )
            db.add(new_training_data)
            training_data = new_training_data
        store_training_data_and_mappings(db, training_data, embedding_array, username, chunks)
        db.commit()
    status.append(f"Raw text for {job_title} at {company_name} processed successfully")
    cleanup_uploads_folder()
