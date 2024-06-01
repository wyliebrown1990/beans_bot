import os
import re
from flask import render_template, request, redirect, url_for
from sqlalchemy.orm import sessionmaker
import numpy as np
import faiss
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import OpenAIEmbeddings
from .models import TrainingData  # Ensure TrainingData is imported

def setup_routes(app, session):

    @app.route('/', methods=['GET'])
    def index():
        job_title = request.args.get('job_title')
        company_name = request.args.get('company_name')
        industry = request.args.get('industry')
        username = request.args.get('username')

        print(f"Received parameters: job_title={job_title}, company_name={company_name}, industry={industry}, username={username}")

        if not username:
            return "Username is missing", 400

        if job_title == 'generic':
            print("Redirecting to generic_interview")
            return redirect(url_for('generic_interview', username=username))
        elif job_title and company_name and industry:
            print("Redirecting to specific_interview")
            return redirect(url_for('specific_interview', job_title=job_title, company_name=company_name, industry=industry, username=username))
        else:
            return render_template('index.html')  # Render index.html if no parameters or invalid parameters

    @app.route('/generic_interview')
    def generic_interview():
        username = request.args.get('username')
        first_question = "I'm all ears and whiskers! Tell me about your purr-sonal work experience and background. Can you share the tail of your career so far? I'd love to hear about the pawsitive impact you've made in your previous jobs."
        return render_template('generic_interview.html', first_question=first_question, username=username)

    @app.route('/specific_interview', methods=['GET', 'POST'])
    def specific_interview():
        if request.method == 'GET':
            job_title = request.args.get('job_title')
            company_name = request.args.get('company_name')
            industry = request.args.get('industry')
            username = request.args.get('username')
            first_question = f"Tell me about your professional experience and any relevant skills for working as a {job_title} at {company_name} company."
            return render_template('specific_interview.html', first_question=first_question, job_title=job_title, company_name=company_name, industry=industry, username=username)
        
        elif request.method == 'POST':
            answer_1 = request.form['answer_1']
            job_title = request.form['job_title']
            company_name = request.form['company_name']
            username = request.form['username']

            # Rebuild FAISS index for each session to ensure it's up-to-date
            index, id_map = get_faiss_index(session)
            query_text = "Return recent and relevant work experience"
            query_embedding = embedder.embed_query(query_text)
            query_embedding = np.array(query_embedding)  # Convert to NumPy array
            
            # Ensure the query embedding has the correct shape
            if query_embedding.ndim == 1:
                query_embedding = query_embedding.reshape(1, -1)
            
            # Debugging prints
            print(f"Query embedding shape: {query_embedding.shape}")
            print(f"FAISS index dimension: {index.d}")

            if query_embedding.shape[1] != index.d:
                raise ValueError(f"Query embedding dimension {query_embedding.shape[1]} does not match FAISS index dimension {index.d}")
            
            D, I = index.search(query_embedding, 5)
            print(f"FAISS search result IDs: {I[0]}")
            print(f"ID Map: {id_map}")
            result_id = id_map.get(int(I[0][0]), None)  # Map FAISS index ID to database ID
            print(f"FAISS result ID: {result_id}")
            
            if result_id is None:
                raise ValueError(f"No training data found for FAISS result ID {I[0][0]} in the ID map.")
            
            training_data = session.query(TrainingData).filter_by(id=result_id).first()
            if training_data is None:
                all_ids = [data.id for data in session.query(TrainingData).all()]
                raise ValueError(f"No training data found for ID {result_id}. Available IDs in the TrainingData table: {all_ids}")
            
            faiss_index_first_question = training_data.data

            # Chat model prompt for feedback
            prompt_1 = f"Compare my answer: {answer_1} with my recent work experience {faiss_index_first_question}. Respond with critical feedback about how well I answered the question: tell me about your professional experience and any relevant skills for working as a {job_title} at {company_name} company. Specifically check that in my answer I showed you why I’m the best candidate for this job, in terms of hard skills and experience as well as soft skills. Did I clearly provide an overview of my professional history, current role, and where I would like to go in the future? Did I prove that I’ve done my research and know how {job_title} and {company_name} company would be a logical next step in my career? Did I demonstrate that I can communicate clearly and effectively, connect with and react to other humans, and present myself professionally?"
            feedback_response = model(prompt_1)

            # Chat model prompt for score
            prompt_2 = f"I want you to only respond to me with a score of one number between 0 and 10 where 0 is awful and 10 is the best. Be critical and harsh and only give the very best answers a 9 or a 10. You are scoring based on my answer to the question: tell me about your professional experience and any relevant skills for working as a {job_title} at {company_name} company. Here is my answer: {answer_1}. Here is additional information about my resume: {faiss_index_first_question}."
            score_response = model(prompt_2)

            # FAISS index query for second question
            query_text_2 = f"Return a summary of the most important information about {company_name}"
            query_embedding_2 = embedder.embed_query(query_text_2)
            query_embedding_2 = np.array(query_embedding_2)  # Convert to NumPy array
            
            # Ensure the query embedding has the correct shape
            if query_embedding_2.ndim == 1:
                query_embedding_2 = query_embedding_2.reshape(1, -1)
            
            # Debugging prints
            print(f"Second query embedding shape: {query_embedding_2.shape}")

            if query_embedding_2.shape[1] != index.d:
                raise ValueError(f"Second query embedding dimension {query_embedding_2.shape[1]} does not match FAISS index dimension {index.d}")

            D, I = index.search(query_embedding_2, 5)
            print(f"FAISS second search result IDs: {I[0]}")
            result_id_2 = id_map.get(int(I[0][0]), None)  # Map FAISS index ID to database ID
            print(f"FAISS second result ID: {result_id_2}")
            
            if result_id_2 is None:
                raise ValueError(f"No training data found for FAISS result ID {I[0][0]} in the ID map.")
            
            training_data_2 = session.query(TrainingData).filter_by(id=result_id_2).first()
            if training_data_2 is None:
                all_ids = [data.id for data in session.query(TrainingData).all()]
                raise ValueError(f"No training data found for ID {result_id_2}. Available IDs in the TrainingData table: {all_ids}")
            
            faiss_index_second_question = training_data_2.data

            # Chat model prompt for next question
            prompt_3 = f"Ask me a new interview question but do not ask any questions you’ve asked me already in this interview. Your question should be very specific to what you would ask a {job_title} at {company_name} company. You can reference this information about {company_name} company: {faiss_index_second_question}"
            next_question_response = model(prompt_3)

            return render_template('specific_interview.html', first_question=answer_1, feedback_response=feedback_response, score_response=score_response, next_question_response=next_question_response, job_title=job_title, company_name=company_name, industry=industry, username=username)

# Ensure FAISS index and chat model setup are included
def get_faiss_index(session):
    training_data = session.query(TrainingData).all()
    embeddings = []
    id_map = {}
    for i, data in enumerate(training_data):
        embedding = np.frombuffer(data.embeddings, dtype='float32').reshape(-1, 1536)  # Reshape embeddings
        print(f"Adding embedding for training data ID {data.id} with shape {embedding.shape}")
        if embedding.shape[1] == 1536:  # Ensure the embedding has the correct shape
            embeddings.append(embedding)
            id_map[i] = data.id  # Map FAISS index ID to database ID
        else:
            print(f"Skipping embedding with incorrect shape: {embedding.shape}")

    if len(embeddings) == 0:
        raise ValueError("No valid embeddings found.")
    
    embedding_array = np.vstack(embeddings).astype('float32')
    print(f"Final embeddings array shape: {embedding_array.shape}")

    dimension = embedding_array.shape[1]  # Dynamically determine dimension
    index = faiss.IndexFlatL2(dimension)
    index.add(embedding_array)
    return index, id_map

# OpenAI chat model setup
api_key = os.getenv('OPENAI_API_KEY')
model = ChatOpenAI(model="gpt-3.5-turbo", api_key=api_key, temperature=0.5)
embedder = OpenAIEmbeddings(openai_api_key=api_key)
