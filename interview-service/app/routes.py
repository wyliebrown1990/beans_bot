from flask import render_template, request, jsonify, redirect, url_for
from sqlalchemy.orm import Session
import faiss
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from .models import TrainingData, InterviewAnswer, User
import numpy as np
import os
import re
import logging

# Initialize the OpenAI chat model and embeddings model
openai_api_key = os.getenv("OPENAI_API_KEY")
model = ChatOpenAI(model="gpt-3.5-turbo", api_key=openai_api_key, temperature=0.5)
embedder = OpenAIEmbeddings(api_key=openai_api_key)

# In-memory store for chat histories
chat_histories = {}

# Helper functions
def get_session_history(session_id: str) -> ChatMessageHistory:
    if session_id not in chat_histories:
        chat_histories[session_id] = ChatMessageHistory()
    return chat_histories[session_id]

def load_training_data(session: Session, job_title, company_name):
    logging.debug(f"Querying for job_title: '{job_title}', company_name: '{company_name}'")
    training_data = session.query(TrainingData).filter_by(job_title=job_title, company_name=company_name).first()
    if training_data:
        logging.debug(f"Found training data: {training_data}")
    else:
        logging.debug("No training data found")
    return training_data

def load_user_resume_embeddings(session: Session, username: str):
    logging.debug(f"Querying for username: '{username}'")
    user = session.query(User).filter_by(username=username).first()
    if user:
        logging.debug(f"Found user: {user}")
        if user.resume_embeddings:
            logging.debug(f"Resume embeddings found: {user.resume_embeddings[:100]}...")  # Print first 100 bytes
    else:
        logging.debug("No user found")
    return user

def create_faiss_index(embedding_array):
    dimension = embedding_array.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embedding_array)
    return index

def query_faiss_index(index, embedding_array, query_embedding, k=5):
    D, I = index.search(np.array([query_embedding]), k)
    return [embedding_array[i] for i in I[0]]

def generate_next_question(job_title, company_name, industry, session_history):
    print("Entering generate_next_question function")
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are the world’s best interview coach. I have hired you to conduct a mock interview with me. You should ask me a new question you haven’t already asked. The question should challenge my ability to work as a {job_title} at {company_name} company in the {industry} industry."),
        MessagesPlaceholder(variable_name="messages"),
    ])

    chain = prompt | model
    response = chain.invoke({"messages": session_history.messages})
    last_question = response.content  # Store the generated question
    print("Leaving generate_next_question function")

    return last_question

def get_resume_question_answer(session: Session, username: str, job_title: str, company_name: str, industry: str, resume_user_response: str):
    user = load_user_resume_embeddings(session, username)
    if not user or not user.resume_embeddings:
        print("No resume embeddings found for user")
        return {"response": "No resume embeddings found for user.", "score": "N/A", "next_question": "N/A"}

    embedding_array = np.frombuffer(user.resume_embeddings, dtype='float32').reshape(-1, 1536)
    index = create_faiss_index(embedding_array)

    query_text = "Return a summary of my work experience, skill sets and notable accomplishments"
    query_embedding = embedder.embed_query(query_text)

    print(f"Query embedding: {query_embedding[:5]}")  # Print first 5 values
    relevant_embeddings = query_faiss_index(index, embedding_array, query_embedding)
    print(f"Relevant embeddings: {relevant_embeddings}")

    relevant_chunks = [embedding_array[np.where(embedding_array == emb)[0][0]] for emb in relevant_embeddings]
    resume_context = " ".join([str(chunk) for chunk in relevant_chunks])
    print(f"Resume context: {resume_context}")

    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are helping me land a new job by conducting a mock interview with me. I’m interviewing to be a {job_title} at {company_name} company in the {industry} industry. Your questions should test my knowledge of the {job_title} job role and {company_name} company. I just answered the question 'tell me about your professional experience and how it relates to this role at {company_name}'. Respond to me analyzing how good my answer was and reference my resume experience here: {resume_context}"),
        ("user", resume_user_response),
        MessagesPlaceholder(variable_name="messages"),
    ])

    chain = prompt | model
    response = chain.invoke({"messages": [HumanMessage(content=resume_user_response)]}).content

    # Step to score the answer
    score_prompt = ChatPromptTemplate.from_messages([
        ("system", f"Score my answer to the question 'tell me about your professional experience and how it relates to this role at {company_name}' from 0 to 10. Here is the answer: {resume_user_response} and my resume context: {resume_context}"),
        ("user", resume_user_response),
        MessagesPlaceholder(variable_name="messages"),
    ])

    score_chain = score_prompt | model
    score_response = score_chain.invoke({"messages": [HumanMessage(content=resume_user_response)]})
    score = extract_score(score_response.content)

    # Generate the next question
    session_history = get_session_history(os.urandom(24).hex())
    next_question = generate_next_question(job_title, company_name, industry, session_history)

    return {
        "response": response,
        "score": score,
        "next_question": next_question
    }

def extract_score(feedback):
    match = re.search(r"\b(\d{1,2})\b", feedback)
    if match:
        return match.group(1)
    else:
        return "Score not found"

def setup_routes(app_instance, session_instance):
    global session
    session = session_instance

    @app_instance.route('/start_interview', methods=['GET', 'POST'])
    def start_interview():
        if request.method == 'GET':
            print("GET request received at /start_interview")
            job_title = request.args.get('job_title').strip().lower()
            company_name = request.args.get('company_name').strip().lower()
            industry = request.args.get('industry').strip().lower()
            username = request.args.get('username').strip().lower()

            print(f"Parameters received: job_title={job_title}, company_name={company_name}, industry={industry}, username={username}")

            initial_question = f"Tell me about your professional experience and how it relates to this role at {company_name}"
            session_id = os.urandom(24).hex()
            session_history = get_session_history(session_id)
            session_history.add_message(AIMessage(content=initial_question))

            return render_template('start_interview.html', question=initial_question, session_id=session_id, job_title=job_title, company_name=company_name, industry=industry, username=username)
        
        if request.method == 'POST':
            print("POST request received at /start_interview")
            job_title = request.form['job_title']
            company_name = request.form['company_name']
            industry = request.form['industry']
            username = request.form['username']
            session_id = request.form['session_id']
            resume_user_response = request.form['answer_1']

            print(f"Form data received: job_title={job_title}, company_name={company_name}, industry={industry}, username={username}, session_id={session_id}")

            results = get_resume_question_answer(session, username, job_title, company_name, industry, resume_user_response)

            session_history = get_session_history(session_id)
            session_history.add_message(AIMessage(content=results["response"]))
            session_history.add_message(AIMessage(content=results["next_question"]))

            # Update the last_question variable
            global last_question
            last_question = results["next_question"]

            return jsonify({
                'feedback_response': results["response"],
                'score_response': results["score"],
                'next_question_response': results["next_question"]
            })

    @app_instance.route('/get_similar_resumes', methods=['GET'])
    def get_similar_resumes():
        username = request.args.get('username').strip().lower()
        query_text = request.args.get('query_text').strip().lower()

        with app.app_context():
            similar_embeddings = get_similar_resume_embeddings(session, username, query_text)

        if similar_embeddings is None:
            return jsonify({"error": "No embeddings found for the specified user"}), 404

        return jsonify({"similar_embeddings": [emb.tolist() for emb in similar_embeddings]})