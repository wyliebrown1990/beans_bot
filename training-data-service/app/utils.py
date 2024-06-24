import os
import json
import logging
import glob
from sqlalchemy.orm import sessionmaker
from flask import current_app
from app.models import JobDescriptionAnalysis
from app.database import get_db
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_message_histories import ChatMessageHistory
import requests
import fitz  # PyMuPDF for PDF processing
import docx
import re

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Initialize the OpenAI chat model
openai_api_key = os.getenv("OPENAI_API_KEY")
model = ChatOpenAI(api_key=openai_api_key)

def update_process_status(app, user_id, status):
    with app.app_context():
        try:
            logging.debug(f"Updating status for user_id: {user_id} to status: {status}")
            response = requests.post('http://localhost:5011/update_status', json={
                'user_id': user_id,
                'status': status
            })
            logging.debug(f"Status update response: {response.status_code} - {response.text}")
            if response.status_code != 200:
                logging.error(f"Failed to update status for user_id: {user_id}. Status: {status}")
        except Exception as e:
            logging.error(f"Exception while updating status for user_id: {user_id}. Status: {status}. Error: {str(e)}")

def process_text(app, text, user_id):
    with app.app_context():
        try:
            update_process_status(app, user_id, "Processing text submission")
            cleaned_text = text.strip()  # Simple text cleaning
            analysis = get_job_description_analysis(cleaned_text)
            store_analysis_data(analysis, user_id)
            update_process_status(app, user_id, "Processing complete")
        except Exception as e:
            logging.error(f"Error in process_text: {str(e)}")
            update_process_status(app, user_id, f"Processing error: {str(e)}")

def process_file(app, file_path, user_id):
    with app.app_context():
        try:
            update_process_status(app, user_id, "Processing file upload")
            if file_path.endswith('.pdf'):
                extracted_text = extract_text_from_pdf(file_path)
            elif file_path.endswith('.docx'):
                extracted_text = extract_text_from_docx(file_path)
            elif file_path.endswith('.txt'):
                with open(file_path, 'r') as f:
                    extracted_text = f.read()
            else:
                raise ValueError("Unsupported file type")

            cleaned_text = extracted_text.strip()
            update_process_status(app, user_id, "Analyzing job description")
            analysis = get_job_description_analysis(cleaned_text)
            store_analysis_data(analysis, user_id)
            update_process_status(app, user_id, "Processing complete")
        except Exception as e:
            logging.error(f"Error in process_file: {str(e)}")
            update_process_status(app, user_id, f"Processing error: {str(e)}")

def extract_text_from_pdf(file_path):
    text = ""
    doc = fitz.open(file_path)
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text += page.get_text()
    return text

def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

#Don't change any of the code in this function. The Goal of the function is to take the job_description_text and invoke the openai chat model to return a JSON analysis. The JSON needs to be formatted correctly so that the response_json can then be stored in the database.
def get_job_description_analysis(job_description_text):
    openai_api_key = os.getenv("OPENAI_API_KEY")
    model = ChatOpenAI(api_key=openai_api_key, model="gpt-4-turbo-preview")

    prompt_text = (
        "You are a professional Job Description analyst. Your job is to take the job description that I am sending you in my user message and extract the details below. "
        "Please extract the relevant information from the following job description and return the results in JSON format. If a job description is missing any detail, then return a JSON value of null for that field. "
        "Desired Output in JSON Format: {{\"job_details\": {{\"title\": \"Senior Software Engineer\", \"level\": \"Mid-Senior level\", \"location\": \"New York, NY (Hybrid)\", \"type\": \"Full-time\", \"salary\": \"$175K/yr - $205K/yr\", \"responsibilities\": [\"Lead design and implementation of technical solutions\", \"Collaborate with product designers, product managers, and other engineers\", \"Investigate design approaches, prototype technology\", \"Continuous improvement in software and development processes\", \"Write automated tests\", \"Mentor other engineers\"], "
        "\"personal_qualifications\": [\"Excellent written, verbal, and presentation skills\", \"Ability to thrive in a fast-paced startup environment\", \"Detail oriented with excellent organizational skills\", \"Ability to work independently and be a self-motivator\"]}}, "
        "\"company_information\": {{\"name\": \"K Health\", \"size\": \"201-500 employees\", \"industry\": \"Telehealth and AI Healthcare\", \"mission_and_values\": \"Use the power of AI to get everyone access to higher quality healthcare at more affordable costs\"}}, "
        "\"requirements_and_qualifications\": {{\"education_background\": [\"Bachelor's degree in Computer Science, Engineering, or a related field\"], \"required_professional_experiences\": [\"5+ years of software engineering experience\", \"Experience with highly-scalable, distributed systems\", \"Experience in designing and developing services with APIs\"], \"nice_to_have_experiences\": [\"Experience with modern cloud technologies such as Docker, Kubernetes, Kafka, GCP/AWS suite\"]}}, \"required_skill_sets\": [\"Node.js\", \"TypeScript\", \"GraphQL\", \"Apollo Federation\", \"Problem Solving\", \"Excellent verbal and written communication skills\"]}}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", prompt_text),
        ("user", "{job_description_text}")
    ])

    logging.debug(f"Prompt created: {prompt}")

    chain = prompt | model

    input_data = {
        "job_description_text": job_description_text.strip()
    }
    logging.debug(f"Input data to chain.invoke: {input_data}")

    response = chain.invoke(input_data)
    logging.debug("Response received from chain.invoke")

    response_content = response.content.strip()
    logging.debug(f"Response content: {response_content}")

    if not response_content:
        logging.error("Received empty response from chain.invoke")
        raise ValueError("Received empty response from chain.invoke")

    try:
        # Remove markdown formatting if present
        if response_content.startswith("```json") and response_content.endswith("```"):
            response_content = response_content[7:-3].strip()
        
        # Attempt to parse the JSON response
        response_json = json.loads(response_content)
        logging.debug(f"Response JSON: {response_json}")
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON response: {str(e)}")
        logging.error(f"Response content was: {response_content}")  # Log the problematic response
        
        # Attempt to handle and fix minor formatting issues
        response_content = response_content.replace("```json", "").replace("```", "").strip()
        try:
            response_json = json.loads(response_content)
            logging.debug(f"Recovered JSON: {response_json}")
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON response after recovery attempt: {str(e)}")
            raise ValueError(f"Error decoding JSON response: {str(e)}")

    # Validate that essential keys are present
    required_keys = ["job_details", "company_information", "requirements_and_qualifications", "required_skill_sets"]
    for key in required_keys:
        if key not in response_json:
            response_json[key] = None

    return response_json

def store_analysis_data(response_json, user_id):
    with current_app.app_context():
        db_session = next(get_db())
        
        # Ensure all required keys are present in response_json
        required_keys = ["job_details", "company_information", "requirements_and_qualifications", "required_skill_sets"]
        for key in required_keys:
            if key not in response_json:
                response_json[key] = None

        job_details = response_json.get("job_details", {})
        company_information = response_json.get("company_information", {})
        requirements_and_qualifications = response_json.get("requirements_and_qualifications", {})
        required_skill_sets = response_json.get("required_skill_sets", [])

        # Safely join fields if they are lists, otherwise use an empty string
        job_responsibilities = "\n".join(job_details.get("responsibilities", [])) if isinstance(job_details.get("responsibilities"), list) else ""
        personal_qualifications = "\n".join(job_details.get("personal_qualifications", [])) if isinstance(job_details.get("personal_qualifications"), list) else ""
        education_background = "\n".join(requirements_and_qualifications.get("education_background", [])) if isinstance(requirements_and_qualifications.get("education_background"), list) else ""
        required_professional_experiences = "\n".join(requirements_and_qualifications.get("required_professional_experiences", [])) if isinstance(requirements_and_qualifications.get("required_professional_experiences"), list) else ""
        nice_to_have_experiences = "\n".join(requirements_and_qualifications.get("nice_to_have_experiences", [])) if isinstance(requirements_and_qualifications.get("nice_to_have_experiences"), list) else ""
        required_skill_sets_str = "\n".join(required_skill_sets) if isinstance(required_skill_sets, list) else ""

        # Create a new JobDescriptionAnalysis object
        job_description = JobDescriptionAnalysis(
            user_id=user_id,
            job_title=job_details.get("title"),
            job_level=job_details.get("level"),
            job_location=job_details.get("location"),
            job_type=job_details.get("type"),
            job_salary=job_details.get("salary"),
            job_responsibilities=job_responsibilities,
            personal_qualifications=personal_qualifications,
            company_name=company_information.get("name"),
            company_size=company_information.get("size"),
            company_industry=company_information.get("industry"),
            company_mission_and_values=company_information.get("mission_and_values"),
            education_background=education_background,
            required_professional_experiences=required_professional_experiences,
            nice_to_have_experiences=nice_to_have_experiences,
            required_skill_sets=required_skill_sets_str
        )

        # Add the new job description analysis to the session and commit
        try:
            db_session.add(job_description)
            db_session.commit()
            logging.info(f"Stored job description analysis for user_id: {user_id}")
        except Exception as e:
            logging.error(f"Error storing job description analysis: {str(e)}")
            db_session.rollback()

def cleanup_uploads_folder(app):
    save_dir = app.config['UPLOAD_FOLDER']
    files = glob.glob(os.path.join(save_dir, '*'))
    for file in files:
        try:
            os.remove(file)
            logging.info(f"Deleted file: {file}")
        except Exception as e:
            logging.error(f"Error deleting file {file}: {e}")
