import os
from docx import Document
import fitz  # PyMuPDF
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, scoped_session
from .models import User, Base
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import json

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

def setup_database(database_url):
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    return engine, Session()

def create_table_if_not_exists(engine, table):
    if not inspect(engine).has_table(table.__tablename__):
        table.__table__.create(engine)

# Add the following imports at the top of the file
from sqlalchemy.orm import scoped_session

# Initialize the database
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def get_resume_analysis(resume_text):
    openai_api_key = os.getenv('OPENAI_API_KEY')
    model = ChatOpenAI(openai_api_key=openai_api_key)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a world class job coach helping me prepare for my job interview. Based on the resume I give you please return JSON formatted summaries of my top 3 technical skills as top_technical_skills TEXT, my most recent job title as most_recent_job_title VARCHAR(255), my most recent company name as most_recent_company_name VARCHAR(255), a short summary of my most recent job experience at my most_recent company as most_recent_experience_summary TEXT, a short summary of my experience in specific job industries as industry_expertise TEXT, and my top 3 soft skills as top_soft_skills TEXT."),
        ("user", resume_text)
    ])

    chain = prompt | model
    response = chain.invoke({"messages": []})

    # Extract response content
    response_content = response.content.strip()
    
    # Print the response content for debugging
    print("Response Content:", response_content)
    
    response_json = json.loads(response_content)  # Ensure response is valid JSON
    
    # Print the parsed JSON data for debugging
    print("Response JSON:", response_json)
    
    return response_json
