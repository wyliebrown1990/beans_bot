from sqlalchemy import create_engine, Column, Integer, String, Text, Float, LargeBinary, DateTime, TIMESTAMP, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import ProgrammingError
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import os
import re
import logging
from datetime import datetime
from flask_login import UserMixin

Base = declarative_base()

class TrainingData(Base):
    __tablename__ = 'training_data'
    id = Column(Integer, primary_key=True)
    job_title = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=False)
    data = Column(Text, nullable=False)
    embeddings = Column(LargeBinary, nullable=True)
    processed_files = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

class InterviewAnswer(Base):
    __tablename__ = 'interview_answers'
    id = Column(Integer, primary_key=True)
    job_title = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=False)
    industry = Column(String(255), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    critique = Column(Text, nullable=False)
    score = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

class User(UserMixin, Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    resume_text_full = Column(Text, nullable=True)
    top_technical_skills = Column(Text, nullable=True)
    most_recent_job_title = Column(String(255), nullable=True)
    most_recent_company_name = Column(String(255), nullable=True)
    most_recent_experience_summary = Column(Text, nullable=True)
    industry_expertise = Column(Text, nullable=True)
    top_soft_skills = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

def create_table_if_not_exists(engine):
    try:
        TrainingData.__table__.create(engine, checkfirst=True)
        InterviewAnswer.__table__.create(engine, checkfirst=True)
        User.__table__.create(engine, checkfirst=True)
    except ProgrammingError:
        pass

def setup_database(database_url):
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    return engine, session

# Initialize the OpenAI chat model and embeddings model
openai_api_key = os.getenv("OPENAI_API_KEY")
model = ChatOpenAI(model="gpt-3.5-turbo", api_key=openai_api_key, temperature=0.5)
embedder = OpenAIEmbeddings(api_key=openai_api_key)

# In-memory store for chat histories
chat_histories = {}

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

def generate_next_question(job_title, company_name, industry, session_history):
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are the world’s best interview coach. I have hired you to conduct a mock interview with me. You should ask me a new question you haven’t already asked. The question should challenge my ability to work as a {job_title} at {company_name} company in the {industry} industry."),
        MessagesPlaceholder(variable_name="messages"),
    ])

    chain = prompt | model
    response = chain.invoke({"messages": session_history.messages})
    last_question = response.content
    return last_question

def get_user_resume_data(session: Session, username: str):
    user = session.query(User).filter_by(username=username).first()
    if not user:
        return None

    resume_text_full = user.resume_text_full
    top_technical_skills = user.top_technical_skills
    most_recent_job_title = user.most_recent_job_title
    most_recent_company_name = user.most_recent_company_name
    most_recent_experience_summary = user.most_recent_experience_summary
    industry_expertise = user.industry_expertise
    top_soft_skills = user.top_soft_skills

    return (resume_text_full, top_technical_skills, most_recent_job_title, most_recent_company_name,
            most_recent_experience_summary, industry_expertise, top_soft_skills)

def get_resume_question_answer(session: Session, username: str, job_title: str, company_name: str, industry: str, resume_user_response: str):
    resume_data = get_user_resume_data(session, username)
    if not resume_data:
        return {"response": "No resume data found for user.", "score": "N/A", "next_question": "N/A"}

    (resume_text_full, top_technical_skills, most_recent_job_title, most_recent_company_name,
     most_recent_experience_summary, industry_expertise, top_soft_skills) = resume_data

    print("Resume Data:", resume_data)

    # Prompt 1: Analyze the user's answer
    analysis_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are helping me land a new job by conducting a mock interview with me. I’m interviewing to be a {job_title} at {company_name} company in the {industry} industry. You just asked me the question: 'tell me about your professional experience and how it relates to this role at {company_name}'. I am going to answer you and I want you to give me an analysis of how well I answered the question. I was most recently a {most_recent_job_title} at {most_recent_company_name} company. I have experience in: {most_recent_experience_summary}."),
        ("user", resume_user_response),
        MessagesPlaceholder(variable_name="messages"),
    ])

    print("Analysis Prompt:", analysis_prompt)

    analysis_chain = analysis_prompt | model
    analysis_response = analysis_chain.invoke({"messages": [HumanMessage(content=resume_user_response)]}).content

    # Prompt 2: Score the user's answer
    score_prompt = ChatPromptTemplate.from_messages([
        ("system", f"Score the answer I am sending you to the question 'tell me about your professional experience and how it relates to this role at {company_name}' from 0 to 10. I was most recently a {most_recent_job_title} at {most_recent_company_name} company. I have experience in: {most_recent_experience_summary}."),
        ("user", resume_user_response),
        MessagesPlaceholder(variable_name="messages"),
    ])

    print("Score Prompt:", score_prompt)

    score_chain = score_prompt | model
    score_response = score_chain.invoke({"messages": [HumanMessage(content=resume_user_response)]})
    score = extract_score(score_response.content)

    # Generate the next question
    session_history = get_session_history(os.urandom(24).hex())
    next_question = generate_next_question(job_title, company_name, industry, session_history)

    # Combine responses into a single response
    combined_response = f"Analysis: {analysis_response}\n\nScore: {score}\n\nNext Question: {next_question}"

    return {
        "response": combined_response,
        "score": score,
        "next_question": next_question
    }

def extract_score(feedback):
    match = re.search(r"\b(\d{1,2})\b", feedback)
    if match:
        return match.group(1)
    else:
        return "Score not found"
