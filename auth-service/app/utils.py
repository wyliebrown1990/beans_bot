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


from langchain_core.messages import SystemMessage, HumanMessage


def get_resume_analysis(resume_text):
   openai_api_key = os.getenv('OPENAI_API_KEY')
   model = ChatOpenAI(openai_api_key=openai_api_key)


   prompt_text = """
   You are going to receive a resume from me. I need you to extract specific information and present it in a structured JSON format. Please provide the following details:


   1. Key Technical Skills: Identify and list technical skills such as programming languages, cloud infrastructure experience, Excel formulas, or any similar examples found in the resume.
   2. Key Soft Skills: Identify and list soft skills such as teamwork, leadership, project management, or any similar examples found in the resume.
   3. Most Recent Job Title: Identify the most recent job title mentioned in the resume (e.g., Account Manager, Customer Success Manager, Account Executive).
   4. Second Most Recent Job Title: Identify the job title listed immediately before the most recent job title in time (e.g., the job title associated with years before the years of the most recent job title).
   5. Most Recent Job Title Summary: Provide a short paragraph summarizing the responsibilities and notable accomplishments described under the most recent job title.
   6. Second Most Recent Job Title Summary: Provide a short paragraph summarizing the responsibilities and notable accomplishments described under the second most recent job title.
   7. Top Listed Skill Keyword: Identify and return the most frequently mentioned skill keyword in the resume.
   8. Second Most Top Listed Skill Keyword: Identify and return the second most frequently mentioned skill keyword in the resume, different from the top listed skill keyword.
   9. Third Most Top Listed Skill Keyword: Identify and return the third most frequently mentioned skill keyword in the resume, different from the top listed skill keyword.
   10. Fourth Most Top Listed Skill Keyword: Identify and return the fourth most frequently mentioned skill keyword in the resume, different from the top listed skill keyword.
   11. Educational Background: Summarize the educational history, including the schools attended, degrees received, and GPA if mentioned. Provide a few sentences summarizing this information.
   12. Certifications and Awards: List any certifications and awards mentioned, starting with the most recently received.
   13. Most Recent Successful Project: Identify and summarize a specific project mentioned under the most recent job title that the candidate had the most success with.
   14. Areas for Improvement: Suggest any areas where the resume could be improved or additional information that could be included.
   15. Questions About Experience: Note any sections of the resume that are unclear or concerning, such as gaps between jobs or significant career transitions. Provide a short summary of these concerns.
   16. Resume Length: Evaluate the length of the resume. Is it too long or too short? Provide feedback on how to improve the length and amount of information.
   17. Top Challenge: Identify the most challenging project listed under the resume’s most recent job title. The project should be the most impressive and interesting. Return the description of the project in the resume.


   Here is the expected output JSON format:


   {{
     "key_technical_skills": [],
     "key_soft_skills": [],
     "most_recent_job_title": "",
     "second_most_recent_job_title": "",
     "most_recent_job_title_summary": "",
     "second_most_recent_job_title_summary": "",
     "top_listed_skill_keyword": "",
     "second_most_top_listed_skill_keyword": "",
     "third_most_top_listed_skill_keyword": "",
     "fourth_most_top_listed_skill_keyword": "",
     "educational_background": "",
     "certifications_and_awards": [],
     "most_recent_successful_project": "",
     "areas_for_improvement": "",
     "questions_about_experience": "",
     "resume_length": "",
     "top_challenge": ""
   }}


   Always return a value for every key.
   """


   messages = [
       SystemMessage(content=prompt_text),
       HumanMessage(content=resume_text)
   ]


   response = model(messages)


   # Extract response content
   response_content = response.content.strip()


   # Print the response content for debugging
   print("Response Content:", response_content)


   response_json = json.loads(response_content)  # Ensure response is valid JSON


   # Print the parsed JSON data for debugging
   print("Response JSON:", response_json)


   return response_json


def output_checker(response_json):
   global missing_json
   missing_json = [key for key, value in response_json.items() if not value]
   return len(missing_json) == 0


def get_resume_analysis_2(resume_text):
   openai_api_key = os.getenv('OPENAI_API_KEY')
   model = ChatOpenAI(openai_api_key=openai_api_key)


   missing_fields = ', '.join(missing_json)  # Convert list to a string


   prompt_text = f"""
   You are going to receive a resume from me. I need you to extract specific information and present it in a structured JSON format. Please provide the following details:


   1. Key Technical Skills: Identify and list technical skills such as programming languages, cloud infrastructure experience, Excel formulas, or any similar examples found in the resume.
   2. Key Soft Skills: Identify and list soft skills such as teamwork, leadership, project management, or any similar examples found in the resume.
   3. Most Recent Job Title: Identify the most recent job title mentioned in the resume (e.g., Account Manager, Customer Success Manager, Account Executive).
   4. Second Most Recent Job Title: Identify the job title listed immediately before the most recent job title in time (e.g., the job title associated with years before the years of the most recent job title).
   5. Most Recent Job Title Summary: Provide a short paragraph summarizing the responsibilities and notable accomplishments described under the most recent job title.
   6. Second Most Recent Job Title Summary: Provide a short paragraph summarizing the responsibilities and notable accomplishments described under the second most recent job title.
   7. Top Listed Skill Keyword: Identify and return the most frequently mentioned skill keyword in the resume.
   8. Second Most Top Listed Skill Keyword: Identify and return the second most frequently mentioned skill keyword in the resume, different from the top listed skill keyword.
   9. Third Most Top Listed Skill Keyword: Identify and return the third most frequently mentioned skill keyword in the resume, different from the top listed skill keyword.
   10. Fourth Most Top Listed Skill Keyword: Identify and return the fourth most frequently mentioned skill keyword in the resume, different from the top listed skill keyword.
   11. Educational Background: Summarize the educational history, including the schools attended, degrees received, and GPA if mentioned. Provide a few sentences summarizing this information.
   12. Certifications and Awards: List any certifications and awards mentioned, starting with the most recently received.
   13. Most Recent Successful Project: Identify and summarize a specific project mentioned under the most recent job title that the candidate had the most success with.
   14. Areas for Improvement: Suggest any areas where the resume could be improved or additional information that could be included.
   15. Questions About Experience: Note any sections of the resume that are unclear or concerning, such as gaps between jobs or significant career transitions. Provide a short summary of these concerns.
   16. Resume Length: Evaluate the length of the resume. Is it too long or too short? Provide feedback on how to improve the length and amount of information.
   17. Top Challenge: Identify the most challenging project listed under the resume’s most recent job title. The project should be the most impressive and interesting. Return the description of the project in the resume.


   Here is the expected output JSON format:


   {{
     "key_technical_skills": [],
     "key_soft_skills": [],
     "most_recent_job_title": "",
     "second_most_recent_job_title": "",
     "most_recent_job_title_summary": "",
     "second_most_recent_job_title_summary": "",
     "top_listed_skill_keyword": "",
     "second_most_top_listed_skill_keyword": "",
     "third_most_top_listed_skill_keyword": "",
     "fourth_most_top_listed_skill_keyword": "",
     "educational_background": "",
     "certifications_and_awards": [],
     "most_recent_successful_project": "",
     "areas_for_improvement": "",
     "questions_about_experience": "",
     "resume_length": "",
     "top_challenge": ""
   }}


   Please remember to return a result for {missing_fields} because you have missed this in the past.
   """


   messages = [
       SystemMessage(content=prompt_text),
       HumanMessage(content=resume_text)
   ]


   response = model(messages)


   # Extract response content
   response_content = response.content.strip()


   # Print the response content for debugging
   print("Response Content:", response_content)


   response_json = json.loads(response_content)  # Ensure response is valid JSON


   # Print the parsed JSON data for debugging
   print("Response JSON:", response_json)


   return response_json
