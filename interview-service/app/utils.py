import os
import uuid
from io import BytesIO
from sqlalchemy import create_engine, Column, Integer, String, Text, LargeBinary, DateTime, TIMESTAMP, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import ProgrammingError
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from datetime import datetime
from flask_login import UserMixin
import faiss
import numpy as np
import re
import logging
from dotenv import load_dotenv
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

def text_to_speech_file(text: str) -> str:
    # Handle empty text case
    if not text.strip():
        print("Text is empty, skipping text-to-speech conversion.")
        return ""

    try:
        # Calling the text_to_speech conversion API with detailed parameters
        response = elevenlabs_client.text_to_speech.convert(
            voice_id="xU744AaoW3SYWVj6TN6H", # Knightley - dapper and deep narrator
            optimize_streaming_latency="0",
            output_format="mp3_22050_32",
            text=text,
            model_id="eleven_turbo_v2", # use the turbo model for low latency, for other languages use the `eleven_multilingual_v2`
            voice_settings=VoiceSettings(
                stability=0.0,
                similarity_boost=1.0,
                style=0.0,
                use_speaker_boost=True,
            ),
        )

        # Generating a unique file name for the output MP3 file
        save_file_path = os.path.join("audio_files", f"{uuid.uuid4()}.mp3")

        # Ensure the directory exists
        os.makedirs(os.path.dirname(save_file_path), exist_ok=True)

        # Writing the audio to a file
        with open(save_file_path, "wb") as f:
            for chunk in response:
                if chunk:
                    f.write(chunk)

        print(f"{save_file_path}: A new audio file was saved successfully!")

        # Return the path of the saved audio file
        return save_file_path

    except ApiError as e:
        print(f"Error generating speech: {e}")
        return ""
    

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

# In-memory store for chat histories and most recent question and responses
chat_histories = {}
most_recent_question = ""
user_responses = {"resume_user_response": None, "career_user_responses": []}

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

def generate_next_question(job_title, company_name, industry, session_history, career_context):
    global most_recent_question
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are the world’s best interview coach. I have hired you to conduct a mock interview with me. You should ask me a new question you haven’t already asked. The question should challenge my ability to work as a {job_title} at {company_name} company in the {industry} industry. Here is more context about {company_name}: {career_context}."),
        MessagesPlaceholder(variable_name="messages"),
    ])

    chain = prompt | model
    response = chain.invoke({"messages": session_history.messages})
    most_recent_question = response.content  # Store the generated question
    print("Most Recent Question:", most_recent_question)
    return most_recent_question

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

def query_faiss_index(query: str):
    # Placeholder function to simulate querying FAISS index
    # This should be replaced with the actual code to query your FAISS index
    # For demonstration purposes, it returns a static string
    return "Career context from FAISS index based on the query."

def get_resume_question_answer(session: Session, username: str, job_title: str, company_name: str, industry: str, resume_user_response: str, career_context: str):
    global most_recent_question, user_responses

    resume_data = get_user_resume_data(session, username)
    if not resume_data:
        return {"response": "No resume data found for user.", "score": "N/A", "next_question": "N/A"}

    (resume_text_full, top_technical_skills, most_recent_job_title, most_recent_company_name,
     most_recent_experience_summary, industry_expertise, top_soft_skills) = resume_data

    # Prompt 1: Analyze the user's answer
    analysis_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are helping me land a new job by conducting a mock interview with me. I’m interviewing to be a {job_title} at {company_name} company in the {industry} industry. You just asked me the question: 'tell me about your professional experience and how it relates to this role at {company_name}'. I am going to answer you and I want you to give me a critical critique of how well I answered the question. Specifically check that my answer followed these best practices: Is there an opening, middle and closing? Did my opening answer the question, without adding extra ideas or unnecessary words? Did the middle of my answer give details that support my opening sentence? Did I give one, two, or three details? Did I follow the STAR format (situation, task, action, result)? Once I finished my answer did I say something that showed I was finished? You can also reference this information about me: I was most recently a {most_recent_job_title} at {most_recent_company_name} company. I have experience in: {most_recent_experience_summary}. Here is more context about the company {company_name} I’m interviewing to work at: {career_context}."),
        ("user", resume_user_response),
        MessagesPlaceholder(variable_name="messages"),
    ])

    analysis_chain = analysis_prompt | model
    analysis_response = analysis_chain.invoke({"messages": [HumanMessage(content=resume_user_response)]}).content

    # Prompt 2: Score the user's answer
    score_prompt = ChatPromptTemplate.from_messages([
        ("system", f"Score the answer I am sending you to the question 'tell me about your professional experience and how it relates to this role at {company_name}' from 0 to 10. I was most recently a {most_recent_job_title} at {most_recent_company_name} company. I have experience in: {most_recent_experience_summary}."),
        ("user", resume_user_response),
        MessagesPlaceholder(variable_name="messages"),
    ])

    score_chain = score_prompt | model
    score_response = score_chain.invoke({"messages": [HumanMessage(content=resume_user_response)]})
    score = extract_score(score_response.content)

    # Handle cases where the score response is empty or does not contain a number
    if not score or not score.isdigit():
        score = None

    # Generate the next question with career context
    session_history = get_session_history(os.urandom(24).hex())
    next_question = generate_next_question(job_title, company_name, industry, session_history, career_context)

    # Store the response in the database
    new_answer = InterviewAnswer(
        job_title=job_title,
        company_name=company_name,
        industry=industry,
        question="Tell me about your professional experience and how it relates to this role at {company_name}",  # Last question asked before the user's answer
        answer=resume_user_response,
        critique=analysis_response,
        score=score if score else "N/A"  # Store "N/A" if score is None
    )
    session.add(new_answer)
    session.commit()

    return {
        "analysis_response": analysis_response,
        "score": score if score else "N/A",
        "next_question": next_question
    }

def get_career_experience_answer(session: Session, username: str, job_title: str, company_name: str, industry: str, career_user_response: str, career_context: str):
    global most_recent_question, user_responses

    resume_data = get_user_resume_data(session, username)
    if not resume_data:
        return {"response": "No resume data found for user.", "score": "N/A", "next_question": "N/A"}

    (resume_text_full, top_technical_skills, most_recent_job_title, most_recent_company_name,
     most_recent_experience_summary, industry_expertise, top_soft_skills) = resume_data

    # Prompt 1: Analyze the user's answer
    analysis_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are helping me land a new job by conducting a mock interview with me. I’m interviewing to be a {job_title} at {company_name} company in the {industry} industry. You just asked me the question: {most_recent_question}. Give me a very critical critique of how well I ansered the question. Specifically check that my answer followed these best practices: Is there an opening, middle and closing? Did my opening answer the question, without adding extra ideas or unnecessary words? Did the middle of my answer give details that support my opening sentence? Did I give one, two, or three details? Did I follow the STAR format (situation, task, action, result)? Once I finished my answer did I say something that showed I was finished? For more context: I was most recently a {most_recent_job_title} at {most_recent_company_name} company. I have experience in: {most_recent_experience_summary}. Here is more context about the company {company_name} I’m interviewing to work at: {career_context}. Based on my experience and the context about {company_name} and my specific answer please give me feedback."),
        ("user", career_user_response),
        MessagesPlaceholder(variable_name="messages"),
    ])

    analysis_chain = analysis_prompt | model
    analysis_response = analysis_chain.invoke({"messages": [HumanMessage(content=career_user_response)]}).content

    # Prompt 2: Score the user's answer
    score_prompt = ChatPromptTemplate.from_messages([
        ("system", f"Score the answer I am sending you to the question {most_recent_question} from 0 to 10. I was most recently a {most_recent_job_title} at {most_recent_company_name} company. I have experience in: {most_recent_experience_summary}."),
        ("user", career_user_response),
        MessagesPlaceholder(variable_name="messages"),
    ])

    score_chain = score_prompt | model
    score_response = score_chain.invoke({"messages": [HumanMessage(content=career_user_response)]})
    score = extract_score(score_response.content)

    # Handle cases where the score response is empty or does not contain a number
    if not score or not score.isdigit():
        score = None

    # Generate the next question with career context
    session_history = get_session_history(os.urandom(24).hex())
    next_question = generate_next_question(job_title, company_name, industry, session_history, career_context)

    # Store the career user response
    user_responses["career_user_responses"].append(career_user_response)
    print("Career User Response:", career_user_response)
    print("Most Recent Question:", most_recent_question)

    # Store the response in the database
    new_answer = InterviewAnswer(
        job_title=job_title,
        company_name=company_name,
        industry=industry,
        question=most_recent_question,  # Last question asked before the user's answer
        answer=career_user_response,
        critique=analysis_response,
        score=score if score else "N/A"  # Store "N/A" if score is None
    )
    session.add(new_answer)
    session.commit()

    return {
        "analysis_response": analysis_response,
        "score": score if score else "N/A",
        "next_question": next_question
    }

def extract_score(feedback):
    match = re.search(r"\b(\d{1,2})\b", feedback)
    if match:
        return match.group(1)
    else:
        return "Score not found"
