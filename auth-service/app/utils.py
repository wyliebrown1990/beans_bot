import os
from docx import Document
import fitz  # PyMuPDF
from sqlalchemy import create_engine, inspect, insert
from sqlalchemy.orm import sessionmaker, scoped_session
from .models import User, Resume, Base
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
import json
import logging
from datetime import datetime

# Initialize the database
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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

def convert_to_date_format(date_str):
    if not date_str or date_str.lower() == "present":
        return date_str
    try:
        # Try parsing various formats
        for fmt in ("%B %Y", "%Y-%m-%d", "%Y-%m", "%m/%d/%Y", "%d/%m/%Y"):
            try:
                date = datetime.strptime(date_str, fmt)
                return date.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return date_str  # Return the original string if it cannot be parsed
    except Exception as e:
        logger.error(f"Error converting date {date_str}: {e}")
        return date_str

def get_resume_analysis(model, resume_text):
    prompt_text = """
    You are going to receive a resume from me. I need you to extract specific information and present it in a structured JSON format. Please provide the following details:

    1. Header Text: Extract the main header or summary at the top of the resume. If it doesn't exist return NULL.
    2. Top Section Summary: Summarize the top section of the resume. If it doesn't exist return NULL.
    3. Top Section List of Achievements: List the achievements mentioned in the top section. List all of them.
    4. Education: Summarize the educational background including institutions attended, degrees received, and any mentioned GPA. If it doesn't exist return NULL.
    5. Bottom Section List of Achievements: List the achievements mentioned in the bottom section. If it doesn't exist return NULL.
    6. Achievements and Awards: List any certifications and awards mentioned, starting with the most recent. List them all.
    7. Job Titles and Details: Extract details for up to six job titles including title, start date, end date, length, location, and description. Extract them in sequential order from most recent being Job title 1.
       - Job Title 1: Extract the job title.
       - Job Title 1 Start Date: Extract the start date. Return it in 'YYYY-MM-DD' format.
       - Job Title 1 End Date: Extract the end date. Return it in 'YYYY-MM-DD' format or 'Present' if it is the current job.
       - Job Title 1 Length: Extract the job duration.
       - Job Title 1 Location: Extract the job location.
       - Job Title 1 Description: Extract the job description.
       - Repeat for Job Title 2 through Job Title 6.
       - If you don't find up to 6 job titles then return NULL for those job titles.
    8. Key Technical Skills: Identify and list technical skills. List them all in order of relevance.
    9. Key Soft Skills: Identify and list soft skills. List them all in order of relevance.
    10. Top Listed Skill Keyword: Identify the most frequently mentioned skill keyword.
    11. Second Most Top Listed Skill Keyword: Identify the second most frequently mentioned skill keyword.
    12. Third Most Top Listed Skill Keyword: Identify the third most frequently mentioned skill keyword.
    13. Fourth Most Top Listed Skill Keyword: Identify the fourth most frequently mentioned skill keyword.
    14. Most Recent Successful Project: Summarize the most recent successful project mentioned.
    15. Areas for Improvement: Suggest any areas where the resume could be improved or additional information that could be included.
    16. Questions About Experience: Note any unclear or concerning sections such as gaps or significant transitions.
    17. Resume Length: Count and return the number of characters in the resume.
    18. Top Challenge: Identify the most challenging project listed and provide its description.

    Here is the expected output JSON format:

    {
      "header_text": "",
      "top_section_summary": "",
      "top_section_list_of_achievements": [],
      "education": "",
      "bottom_section_list_of_achievements": [],
      "achievements_and_awards": [],
      "job_title_1": {
        "title": "",
        "start_date": "",
        "end_date": "",
        "length": "",
        "location": "",
        "description": ""
      },
      "job_title_2": {
        "title": "",
        "start_date": "",
        "end_date": "",
        "length": "",
        "location": "",
        "description": ""
      },
      "job_title_3": {
        "title": "",
        "start_date": "",
        "end_date": "",
        "length": "",
        "location": "",
        "description": ""
      },
      "job_title_4": {
        "title": "",
        "start_date": "",
        "end_date": "",
        "length": "",
        "location": "",
        "description": ""
      },
      "job_title_5": {
        "title": "",
        "start_date": "",
        "end_date": "",
        "length": "",
        "location": "",
        "description": ""
      },
      "job_title_6": {
        "title": "",
        "start_date": "",
        "end_date": "",
        "length": "",
        "location": "",
        "description": ""
      },
      "key_technical_skills": [],
      "key_soft_skills": [],
      "top_listed_skill_keyword": "",
      "second_most_top_listed_skill_keyword": "",
      "third_most_top_listed_skill_keyword": "",
      "fourth_most_top_listed_skill_keyword": "",
      "certifications_and_awards": [],
      "most_recent_successful_project": "",
      "areas_for_improvement": "",
      "questions_about_experience": "",
      "resume_length": "",
      "top_challenge": ""
    }

    Always return a value for every key.
    """

    messages = [
        SystemMessage(content=prompt_text),
        HumanMessage(content=resume_text)
    ]

    logger.debug("Sending request to OpenAI with messages: %s", messages)
    response = model.invoke(messages)

    # Extract the content from the response
    if isinstance(response, dict) and 'choices' in response:
        response_content = response['choices'][0]['message']['content'].strip()
    elif hasattr(response, 'content'):
        response_content = response.content.strip()
    else:
        logger.error("Unexpected response format from OpenAI API: %s", response)
        raise ValueError("Unexpected response format from OpenAI API")

    # Remove triple backticks if they exist
    if response_content.startswith("```") and response_content.endswith("```"):
        response_content = response_content[3:-3].strip()

    logger.debug("Response Content: %s", response_content)

    try:
        response_json = json.loads(response_content)
    except json.JSONDecodeError as e:
        logger.error("JSON decode error: %s", e)
        logger.error("Response content that caused error: %s", response_content)
        raise ValueError("Failed to decode JSON response from OpenAI API")

    logger.debug("Response JSON: %s", response_json)

    # Convert date formats
    for i in range(1, 7):
            job_key = f"job_title_{i}"
            if job_key in response_json and isinstance(response_json[job_key], dict):
                for date_key in ['start_date', 'end_date']:
                    if date_key in response_json[job_key]:
                        date_value = response_json[job_key][date_key]
                        if date_value.lower() == 'present':
                            response_json[job_key][date_key] = None  # Use None for 'Present'
                        else:
                            response_json[job_key][date_key] = convert_to_date_format(date_value)

    return response_json

def output_checker(response_json):
    global missing_json
    missing_json = [key for key, value in response_json.items() if not value]
    
    print("Output Checker - Response JSON:", response_json)
    print("Output Checker - Missing JSON Fields:", missing_json)
    
    return len(missing_json) == 0

def store_resume_analysis(user_id, response_json):
    print("Store Resume Analysis - User ID:", user_id)
    print("Store Resume Analysis - Response JSON:", response_json)
    
    conn = engine.connect()

    stmt = insert(Resume).values(
        user_id=user_id,
        header_text=response_json['header_text'],
        top_section_summary=response_json['top_section_summary'],
        top_section_list_of_achievements=json.dumps(response_json['top_section_list_of_achievements']),
        education=response_json['education'],
        bottom_section_list_of_achievements=json.dumps(response_json['bottom_section_list_of_achievements']),
        achievements_and_awards=json.dumps(response_json['achievements_and_awards']),
        job_title_1=response_json['job_title_1']['title'],
        job_title_1_start_date=response_json['job_title_1']['start_date'],
        job_title_1_end_date=response_json['job_title_1']['end_date'],
        job_title_1_length=response_json['job_title_1']['length'],
        job_title_1_location=response_json['job_title_1']['location'],
        job_title_1_description=response_json['job_title_1']['description'],
        job_title_2=response_json['job_title_2']['title'],
        job_title_2_start_date=response_json['job_title_2']['start_date'],
        job_title_2_end_date=response_json['job_title_2']['end_date'],
        job_title_2_length=response_json['job_title_2']['length'],
        job_title_2_location=response_json['job_title_2']['location'],
        job_title_2_description=response_json['job_title_2']['description'],
        job_title_3=response_json['job_title_3']['title'],
        job_title_3_start_date=response_json['job_title_3']['start_date'],
        job_title_3_end_date=response_json['job_title_3']['end_date'],
        job_title_3_length=response_json['job_title_3']['length'],
        job_title_3_location=response_json['job_title_3']['location'],
        job_title_3_description=response_json['job_title_3']['description'],
        job_title_4=response_json['job_title_4']['title'],
        job_title_4_start_date=response_json['job_title_4']['start_date'],
        job_title_4_end_date=response_json['job_title_4']['end_date'],
        job_title_4_length=response_json['job_title_4']['length'],
        job_title_4_location=response_json['job_title_4']['location'],
        job_title_4_description=response_json['job_title_4']['description'],
        job_title_5=response_json['job_title_5']['title'],
        job_title_5_start_date=response_json['job_title_5']['start_date'],
        job_title_5_end_date=response_json['job_title_5']['end_date'],
        job_title_5_length=response_json['job_title_5']['length'],
        job_title_5_location=response_json['job_title_5']['location'],
        job_title_5_description=response_json['job_title_5']['description'],
        job_title_6=response_json['job_title_6']['title'],
        job_title_6_start_date=response_json['job_title_6']['start_date'],
        job_title_6_end_date=response_json['job_title_6']['end_date'],
        job_title_6_length=response_json['job_title_6']['length'],
        job_title_6_location=response_json['job_title_6']['location'],
        job_title_6_description=response_json['job_title_6']['description'],
        key_technical_skills=response_json['key_technical_skills'],
        key_soft_skills=response_json['key_soft_skills'],
        top_listed_skill_keyword=response_json['top_listed_skill_keyword'],
        second_most_top_listed_skill_keyword=response_json['second_most_top_listed_skill_keyword'],
        third_most_top_listed_skill_keyword=response_json['third_most_top_listed_skill_keyword'],
        fourth_most_top_listed_skill_keyword=response_json['fourth_most_top_listed_skill_keyword'],
        certifications_and_awards=json.dumps(response_json['certifications_and_awards']),
        most_recent_successful_project=response_json['most_recent_successful_project'],
        areas_for_improvement=response_json['areas_for_improvement'],
        questions_about_experience=response_json['questions_about_experience'],
        resume_length=response_json['resume_length'],
        top_challenge=response_json['top_challenge'],
        created_at=datetime.utcnow()
    )
    
    result = conn.execute(stmt)
    conn.close()
    
    print("Store Resume Analysis - Inserted Primary Key:", result.inserted_primary_key)
    
    return result.inserted_primary_key
