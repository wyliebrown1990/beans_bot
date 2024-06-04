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
last_question = ""
training_data_answer = ""

# Helper functions
def get_session_history(session_id: str) -> ChatMessageHistory:
   if session_id not in chat_histories:
       chat_histories[session_id] = {
           'history': ChatMessageHistory(),
           'session_state': {
               'session_id': session_id,
               'first_answer': None,
               'last_question': None
           }
       }
   return chat_histories[session_id]['history']

# Function to load relevant training data on company and job title
def load_training_data(session: Session, job_title, company_name):
   logging.debug(f"Querying for job_title: '{job_title}', company_name: '{company_name}'")
   training_data = session.query(TrainingData).filter_by(job_title=job_title, company_name=company_name).first()
   if training_data:
       logging.debug(f"Found training data: {training_data}")
   else:
       logging.debug("No training data found")
   return training_data

# Function to load relevant resume embeddings for a user
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

# Function to create faiss index
def create_faiss_index(embedding_array):
   dimension = embedding_array.shape[1]
   index = faiss.IndexFlatL2(dimension)
   index.add(embedding_array)
   return index

# Function to query the faiss index for embeddings
def query_faiss_index(index, embedding_array, query_embedding, k=5):
   D, I = index.search(np.array([query_embedding]), k)
   return [embedding_array[i] for i in I[0]], I[0]

# Function to generate next interview question relevant to company and job title
def generate_next_question(session_history: ChatMessageHistory, job_title: str, company_name: str, industry: str):
   print("Entering generate_next_question function")
   prompt = ChatPromptTemplate.from_messages([
       ("system", f"You are the world’s best interview coach. I have hired you to conduct a mock interview with me. You should ask me a new question you haven’t already asked. The question should challenge my ability to work as a {job_title} at {company_name} company in the {industry} industry."),
       MessagesPlaceholder(variable_name="messages"),
   ])
   chain = prompt | model
   response = chain.invoke({"messages": session_history.messages})
   print("Leaving generate_next_question function")
   return response.content

# Function that runs after user answers the first interview question about themself
def get_resume_question_answer(session: Session, session_id: str, username: str, job_title: str, company_name: str, industry: str, resume_user_response: str):
    user = load_user_resume_embeddings(session, username)
    if not user or not user.resume_embeddings:
        print("No resume embeddings found for user")
        return {"feedback": "No resume embeddings found for user.", "score": "N/A", "next_question": "N/A"}

    embedding_array = np.frombuffer(user.resume_embeddings, dtype='float32').reshape(-1, 1536)
    index = create_faiss_index(embedding_array)

    query_text = f"Tell me about your professional experience and how it relates to this role at {company_name}"
    query_embedding = embedder.embed_query(query_text)

    print(f"Query text for FAISS index: {query_text}")
    print(f"Query embedding: {query_embedding[:5]}")  # Print first 5 values

    D, I = index.search(np.array([query_embedding]), 5)
    relevant_embeddings = [embedding_array[i] for i in I[0]]
    print(f"Relevant embeddings: {relevant_embeddings}")

    # Retrieve the actual text chunks from the resume
    chunks = user.resume_data.split('\n')  # Assuming user.resume_data contains the resume text split into chunks
    relevant_text_chunks = [chunks[i] for i in I[0]]
    print(f"Actual text retrieved from embeddings: {relevant_text_chunks}")

    resume_context = " ".join(relevant_text_chunks)

    session_history = get_session_history(session_id)
    session_state = chat_histories[session_id]['session_state']
    session_state['resume_user_response'] = resume_user_response  # Store the first answer

    feedback_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are interviewing me for a {job_title} position at {company_name} company in the {industry} industry. You just asked me: 'tell me about your professional experience and how it relates to this role at {company_name}'. I just answered: {resume_user_response}. Now critique my answer specifically looking for the following: Did I start with my most recent experience? Did I present something I’m proud of? Did I explain my career goals and how working as a {job_title} at {company_name} will help me achieve them? Check my resume to ensure my answers are relevant and accurate: {resume_context}"),
        ("user", resume_user_response),
        MessagesPlaceholder(variable_name="messages"),
    ])

    feedback_chain = feedback_prompt | model
    feedback_response = feedback_chain.invoke({"messages": session_history.messages}).content

    # Step to score the answer
    score_prompt = ChatPromptTemplate.from_messages([
        ("system", f"Score my answer to the question 'tell me about your professional experience and how it relates to this role at {company_name}' from 0 to 10. Here is the answer: {resume_user_response} and my resume context: {resume_context}"),
        ("user", resume_user_response),
        MessagesPlaceholder(variable_name="messages"),
    ])

    score_chain = score_prompt | model
    score_response = score_chain.invoke({"messages": session_history.messages}).content
    score = extract_score(score_response)

    # Step to ask the next question
    next_question = generate_next_question(session_history, job_title, company_name, industry)

    return {
        "feedback": feedback_response,
        "score": score,
        "next_question": next_question
    }



# Function to handle subsequent training data answers
def get_training_data_answers(session: Session, session_id: str, username: str, job_title: str, company_name: str, industry: str, answer: str, last_question: str):
   # Get the session history
   session_history = get_session_history(session_id)

   # Step 1: Generate feedback for the most recent answer
   training_data = load_training_data(session, job_title, company_name)
   chunks = training_data.data.split('\n')
   embedding_array = np.frombuffer(training_data.embeddings, dtype='float32').reshape(-1, 1536)
   index = create_faiss_index(embedding_array)

   query_embedding = embedder.embed_query(last_question)
   print(f"Query text for FAISS index: {last_question}")
   print(f"Query embedding: {query_embedding[:5]}")  # Print first 5 values

   relevant_embeddings, indices = query_faiss_index(index, embedding_array, query_embedding)
   print(f"Relevant embeddings: {relevant_embeddings}")

   relevant_chunks = [chunks[i] for i in indices]
   relevant_context = " ".join(relevant_chunks)
   print(f"Training data context retrieved from embeddings: {relevant_context}")

   # Printing the actual text chunks retrieved from embeddings
   actual_text_chunks = [chunks[i] for i in indices]
   print(f"Actual text retrieved from embeddings: {actual_text_chunks}")

   feedback_prompt = ChatPromptTemplate.from_messages([
       ("system", f"You are the world’s best interview coach. I have hired you to conduct a mock interview with me. Give me critical feedback analyzing the answer I just gave to your last question: “{last_question}”. My answer was: “{answer}”. Reference this specific context about {company_name} company: {relevant_context}"),
       MessagesPlaceholder(variable_name="messages"),
   ])

   feedback_chain = feedback_prompt | model
   feedback_response = feedback_chain.invoke({"messages": session_history.messages}).content

   # Step 2: Generate a score for the most recent answer
   score_prompt = ChatPromptTemplate.from_messages([
       ("system", f"Score my answer to the question 'tell me about your professional experience and how it relates to this role at {company_name}' from 0 to 10. Here is the answer: {answer} and my context: {relevant_context}"),
       MessagesPlaceholder(variable_name="messages"),
   ])

   score_chain = score_prompt | model
   score_response = score_chain.invoke({"messages": session_history.messages}).content
   score = extract_score(score_response)

   # Step 3: Generate the next question
   next_question = generate_next_question(session_history, job_title, company_name, industry)

   return {
       "feedback": feedback_response,
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

           # Store session state
           chat_histories[session_id]['session_state']['last_question'] = initial_question

           return render_template('start_interview.html', question=initial_question, session_id=session_id, job_title=job_title, company_name=company_name, industry=industry, username=username)

       if request.method == 'POST':
           print("POST request received at /start_interview")
           job_title = request.form['job_title']
           company_name = request.form['company_name']
           industry = request.form['industry']
           username = request.form['username']
           session_id = request.form['session_id']
           answer = request.form['answer_1']

           print(f"Form data received: job_title={job_title}, company_name={company_name}, industry={industry}, username={username}, session_id={session_id}")

           session_history = get_session_history(session_id)
           session_state = chat_histories[session_id]['session_state']

           if not session_state['first_answer']:
               # Handle the first answer (resume question)
               session_state['first_answer'] = answer
               results = get_resume_question_answer(session, session_id, username, job_title, company_name, industry, answer)
           else:
               # Handle subsequent answers (training data questions)
               last_question = session_state['last_question']
               results = get_training_data_answers(session, session_id, username, job_title, company_name, industry, answer, last_question)
               session_state['last_question'] = results['next_question']

           return jsonify({
               'feedback_response': results["feedback"],
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
