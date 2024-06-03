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


def query_faiss_index(index, embedding_array, query_embedding, k=5):
    D, I = index.search(np.array([query_embedding]), k)
    return [embedding_array[i] for i in I[0]]

def get_initial_question(training_data, industry, job_title, company_name):
   print("Entering get_initial_question function")
   chunks = training_data.data.split('\n')
   print(f"Chunks: {chunks[:5]}")  # Print first 5 chunks for debug
   embedding_array = np.frombuffer(training_data.embeddings, dtype='float32').reshape(-1, 1536)
   print(f"Embedding array shape: {embedding_array.shape}")
   dimension = embedding_array.shape[1]
   index = faiss.IndexFlatL2(dimension)
   index.add(embedding_array)

   query_text = f"How would a {job_title} demonstrate knowledge of {company_name} in the {industry} industry?"
   example_query_embedding = embedder.embed_query(query_text)
   print(f"Example query embedding: {example_query_embedding[:5]}")  # Print first 5 values
   relevant_embeddings = query_faiss_index(index, embedding_array, example_query_embedding)
   print(f"Relevant embeddings: {relevant_embeddings}")
   relevant_chunks = [chunks[np.where(embedding_array == emb)[0][0]] for emb in relevant_embeddings]
   print(f"Relevant chunks: {relevant_chunks}")
   relevant_context = " ".join(relevant_chunks)
   print(f"Relevant context: {relevant_context}")

   prompt = ChatPromptTemplate.from_messages([
       ("system", f"You are helping me land a new job by conducting a mock interview with me. You should ask me a new question each time that is related to {job_title} job role at {company_name} company in the {industry} industry. Your questions should test my knowledge of the {job_title} job role and {company_name} company. You should challenge me to give concise and relevant answers. Here is some context about {company_name}: {relevant_context}"),
       MessagesPlaceholder(variable_name="messages"),
   ])

   chain = prompt | model
   initial_prompt = "Ask a challenging interview question."
   response = chain.invoke({"messages": [HumanMessage(content=initial_prompt)]})
   print("Leaving get_initial_question function")

   return response.content

def get_next_question(session, session_id, user_response, job_title, company_name, industry):
   session_history = get_session_history(session_id)
   session_history.add_message(HumanMessage(content=user_response))

   training_data = load_training_data(session, job_title, company_name)
   chunks = training_data.data.split('\n')
   embedding_array = np.frombuffer(training_data.embeddings, dtype='float32').reshape(-1, 1536)
   dimension = embedding_array.shape[1]
   index = faiss.IndexFlatL2(dimension)
   index.add(embedding_array)

   response_embedding = embedder.embed_query(user_response)
   relevant_embeddings_for_fact_checking = query_faiss_index(index, embedding_array, response_embedding)
   relevant_chunks_for_fact_checking = [chunks[np.where(embedding_array == emb)[0][0]] for emb in relevant_embeddings_for_fact_checking]
   relevant_context_for_fact_checking = " ".join(relevant_chunks_for_fact_checking)

   fact_check_prompt = ChatPromptTemplate.from_messages([
       ("system", f"Give me critical feedback on how well I answered your last question. Specifically call out the following: Was my answer concise? Did I provide a STAR (Situation, Task, Action, and Result) formatted answer? Did I use too many filler words? Did I provide an answer that was specific to being a {job_title} at {company_name}? Finally, you must always score my answer from between 0 being the worst answer and 10 being the best. Always return a score out of 10. Once you complete giving feedback, move on to ask me a new question you haven’t asked before in this interview. If you need additional context about being a {job_title} at {company_name}, use this: {relevant_context_for_fact_checking}"),
       ("user", user_response),
       MessagesPlaceholder(variable_name="messages"),
   ])

   fact_check_chain = fact_check_prompt | model
   fact_check_response = fact_check_chain.invoke({"messages": session_history.messages})
   fact_check_feedback = fact_check_response.content

   score = extract_score(fact_check_feedback)

   relevant_embeddings_for_next_question = query_faiss_index(index, embedding_array, response_embedding)
   relevant_chunks_for_next_question = [chunks[np.where(embedding_array == emb)[0][0]] for emb in relevant_embeddings_for_next_question]
   relevant_context_for_next_question = " ".join(relevant_chunks_for_next_question)

   next_question_prompt = ChatPromptTemplate.from_messages([
       ("system", f"You are helping me land a new job by conducting a mock interview with me. You should ask me a new question each time that is related to {job_title} job role at {company_name} company. You should reference this Context: {relevant_context_for_next_question}"),
       MessagesPlaceholder(variable_name="messages"),
   ])

   next_question_chain = next_question_prompt | model
   next_question_response = next_question_chain.invoke({"messages": session_history.messages})
   next_question = next_question_response.content
   session_history.add_message(AIMessage(content=next_question))

   new_answer = InterviewAnswer(
       job_title=job_title,
       company_name=company_name,
       industry=industry,
       question=session_history.messages[-2].content,
       answer=user_response,
       critique=fact_check_feedback,
       score=score
   )
   session.add(new_answer)
   session.commit()

   return {
       "next_question": next_question,
       "fact_check_feedback": fact_check_feedback,
       "score": score
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
            username = request.args.get('username')

            print(f"Parameters received: job_title={job_title}, company_name={company_name}, industry={industry}, username={username}")

            training_data = load_training_data(session, job_title, company_name)
            if training_data:
                print("Training data found")
                initial_question = get_initial_question(training_data, industry, job_title, company_name)
                session_id = os.urandom(24).hex()
                session_history = get_session_history(session_id)
                session_history.add_message(AIMessage(content=initial_question))
                return render_template('start_interview.html', question=initial_question, session_id=session_id, job_title=job_title, company_name=company_name, industry=industry, username=username)
            else:
                print("No training data found")
                return render_template('index.html', message="No training data found. To improve results please provide a file path to training data:", job_title=job_title, company_name=company_name, industry=industry)
        
        if request.method == 'POST':
            print("POST request received at /start_interview")
            job_title = request.form['job_title']
            company_name = request.form['company_name']
            industry = request.form['industry']
            username = request.form['username']
            session_id = request.form['session_id']
            user_response = request.form['answer_1']

            print(f"Form data received: job_title={job_title}, company_name={company_name}, industry={industry}, username={username}, session_id={session_id}")

            results = get_next_question(session, session_id, user_response, job_title, company_name, industry)

            return jsonify({
                'feedback_response': results['fact_check_feedback'],
                'score_response': results['score'],
                'next_question_response': results['next_question']
            })

