import os
import re
import uuid
import random
from pydub import AudioSegment
from pydub.utils import which
from io import BytesIO
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import ProgrammingError
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from openai import OpenAI
from datetime import datetime
from flask_login import UserMixin
import re
import logging
from dotenv import load_dotenv
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs, ApiError

# Import models from app package
from app.models import JobDescriptions, Users, InterviewHistory, Questions, Resumes
from app.database import db_session

from flask import session

def set_most_recent_question_answer(question, answer):
    session['most_recent_question'] = question
    session['most_recent_answer'] = answer

def get_most_recent_question_answer():
    return session.get('most_recent_question'), session.get('most_recent_answer')


load_dotenv()

# Set up logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the OpenAI chat model
openai_api_key = os.getenv("OPENAI_API_KEY")
model = ChatOpenAI(model="gpt-3.5-turbo", api_key=openai_api_key, temperature=0.5)

# Initialize database session
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = SessionLocal()

def fetch_interview_data(user_id):
    job_details = db_session.query(JobDescriptions).filter_by(user_id=user_id).first()
    return job_details

def get_user_by_id(user_id):
    user = db_session.query(Users).filter_by(id=user_id).first()
    return user

# Begins the first round of question, score, feedback functions 

def get_first_question(username, user_id):
    job_details = fetch_interview_data(user_id)
    job_title = job_details.job_title
    company_name = job_details.company_name
    company_industry = job_details.company_industry

    question = (f"Hello {username}! Thanks for meeting with me today. My name is Beans. "
                f"I’m the hiring manager for the {job_title} role on our team at {company_name}. "
                f"I’d love to start by getting to know you and your background as it relates to this role. "
                f"Then we’ll go over some more details about your background and experiences, as well as, "
                f"discuss some topics about the {company_industry} industry. Can you please start by telling me about yourself?")
    
    return question

def get_first_score(answer, user_id):
    job_details = fetch_interview_data(user_id)
    job_title = job_details.job_title
    company_name = job_details.company_name
    company_industry = job_details.company_industry

    most_recent_question, _ = get_most_recent_question_answer()

    score_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are a career coach conducting a mock job interview with me. I’m interviewing to be a {job_title} at {company_name} company in the {company_industry} industry. "
                   f"You just asked me this question: {most_recent_question} "
                   "Your job is to give me an honest and critical score that ranges between 1-10. You are scoring me based on how accurate my answer was, how concise it was and how well I used realistic examples to illustrate my relevant experience. "
                   "Don't return any text in your response. Only return a single integer for the score ranging between 1-10 where 10 is the best. For example your response should be: 1 or 2 or 3 or 4 or 5 or 6 or 7 or 8 or 9 or 10."),
        ("user", answer),
        MessagesPlaceholder(variable_name="messages"),
    ])

    score_chain = score_prompt | model
    score_response = score_chain.invoke({"messages": [HumanMessage(content=answer)]})

    # Print the raw response from the chat model
    print(f"Score response from chat model: {score_response}")

    # Extract and clean the score from the response
    score_text = score_response.content.strip() if score_response.content else None
    print(f"Extracted score text: {score_text}")

    # Use regex to find the first integer in the response
    score_match = re.search(r'\b\d+\b', score_text)
    if score_match:
        score = int(score_match.group())
        print(f"Extracted score: {score}")
    else:
        print("No integer found in score response, setting score to None")
        score = None

    return score


def get_first_feedback(answer, user_id):
    job_details = fetch_interview_data(user_id)
    user = get_user_by_id(user_id)
    username = user.username

    most_recent_question, _ = get_most_recent_question_answer()

    feedback_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are helping me land a new job by conducting realistic interviews with me. "
                   f"I’m interviewing to be a {job_details.job_title} at {job_details.company_name} company in the {job_details.company_industry} industry. "
                   f"You just asked me the question: '{most_recent_question}'. "
                   "I am going to answer you and I want you to give me a very critical critique of how well I answered the question. "
                   "Specifically, check that my answer followed these best practices: Is there an opening, middle and closing? "
                   "Did my opening answer the question, without adding extra ideas or unnecessary words? "
                   "Did the middle of my answer give details that support my opening sentence? Did I give one, two, or three details? "
                   "Once I finished my answer did I say something that showed I was finished? "
                   "Did I answer the question in a reasonable amount of time that lasted no more than 2 minutes? "
                   "Finally, please give me a recommendation on how I could have presented my experience better."),
        ("user", answer),
        MessagesPlaceholder(variable_name="messages"),
    ])

    analysis_chain = feedback_prompt | model

    feedback_response = analysis_chain.invoke({"messages": [HumanMessage(content=answer)]})

    # Print the raw response from the chat model
    print(f"Feedback response from chat model: {feedback_response}")

    # Extract and clean the feedback from the response
    feedback_text = feedback_response.content.strip() if feedback_response.content else "No feedback received"
    print(f"Extracted feedback text: {feedback_text}")

    return feedback_text


# Begins the second round of question, score and feedback functions

def get_second_question(user_id):
    job_details = fetch_interview_data(user_id)
    resume_details = db_session.query(Resumes).filter_by(user_id=user_id).first()

    job_title = job_details.job_title
    company_name = job_details.company_name
    job_responsibilities = job_details.job_responsibilities
    required_professional_experiences = job_details.required_professional_experiences
    key_technical_skills = resume_details.key_technical_skills

    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are the world's best interview coach. We are conducting a mock interview where I am interviewing for the role of {job_title} at {company_name} company. "
                   f"I want you to ask me a question as if you are the actual hiring manager. You have my resume in front of you. "
                   f"You can see from my resume that my top technical skills are: {key_technical_skills}. "
                   f"You have the job description in front of you which shows that the job responsibilities are: {job_responsibilities} and the required professional experiences are: {required_professional_experiences}. "
                   "Identify similarities in the job description and my top technical skills. "
                   "Select one of my top technical skills that matches the job description and ask me to elaborate on how I developed and have used that technical skill in the past."),
        MessagesPlaceholder(variable_name="messages"),
    ])

    chain = prompt | model
    response = chain.invoke({"messages": []})

    # Print the raw response from the chat model
    print(f"Second question response from chat model: {response}")

    # Extract and clean the response from the chat model
    question_text = response.content.strip() if response.content else "No question generated"
    print(f"Extracted question text: {question_text}")

    return question_text

def get_second_score(answer, user_id):
    job_details = fetch_interview_data(user_id)
    job_title = job_details.job_title
    company_name = job_details.company_name
    company_industry = job_details.company_industry

    most_recent_question, _ = get_most_recent_question_answer()

    score_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are a career coach conducting a mock job interview with me. I’m interviewing to be a {job_title} at {company_name} company in the {company_industry} industry. "
                   f"You just asked me this question: {most_recent_question} "
                   "Your job is to give me an honest and critical score that ranges between 1-10. You are scoring me based on how accurate my answer was, how concise it was and how well I used realistic examples to illustrate my relevant experience. "
                   "Don't return any text in your response. Only return a single integer for the score ranging between 1-10 where 10 is the best. For example your response should be: 1 or 2 or 3 or 4 or 5 or 6 or 7 or 8 or 9 or 10."),
        ("user", answer),
        MessagesPlaceholder(variable_name="messages"),
    ])

    score_chain = score_prompt | model
    score_response = score_chain.invoke({"messages": [HumanMessage(content=answer)]})

    # Print the raw response from the chat model
    print(f"Score response from chat model: {score_response}")

    # Extract and clean the score from the response
    score_text = score_response.content.strip() if score_response.content else None
    print(f"Extracted score text: {score_text}")

    # Use regex to find the first integer in the response
    score_match = re.search(r'\b\d+\b', score_text)
    if score_match:
        score = int(score_match.group())
        print(f"Extracted score: {score}")
    else:
        print("No integer found in score response, setting score to None")
        score = None

    return score

def get_second_feedback(answer, user_id):
    job_details = fetch_interview_data(user_id)
    user = get_user_by_id(user_id)
    username = user.username

    most_recent_question, _ = get_most_recent_question_answer()

    feedback_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are helping me land a new job by conducting realistic interviews with me. "
                   f"I’m interviewing to be a {job_details.job_title} at {job_details.company_name} company in the {job_details.company_industry} industry. "
                   f"You just asked me the question: '{most_recent_question}'. "
                   "I am going to answer you and I want you to give me a very critical critique of how well I answered the question. "
                   "Specifically, check that my answer followed these best practices: Did I give an example of a specific project where I used this technical skill? "
                   "Did I demonstrate a deep technical knowledge of the technical skill asked about? "
                   "Did I demonstrate critical thinking and problem-solving skills in my answer? "
                   "Did I quantify the impact of the results of a specific project where I used this skill? "
                   "Did I answer the question in a reasonable amount of time that lasted no more than 2 minutes? "
                   "Finally, please give me a recommendation on how I could have presented my experience better."),
        ("user", answer),
        MessagesPlaceholder(variable_name="messages"),
    ])

    analysis_chain = feedback_prompt | model

    feedback_response = analysis_chain.invoke({"messages": [HumanMessage(content=answer)]})

    # Print the raw response from the chat model
    print(f"Feedback response from chat model: {feedback_response}")

    # Extract and clean the feedback from the response
    feedback_text = feedback_response.content.strip() if feedback_response.content else "No feedback received"
    print(f"Extracted feedback text: {feedback_text}")

    return feedback_text

def get_third_question(user_id):
    job_details = fetch_interview_data(user_id)
    resume_details = db_session.query(Resumes).filter_by(user_id=user_id).first()

    job_title = job_details.job_title
    company_name = job_details.company_name
    job_responsibilities = job_details.job_responsibilities
    required_professional_experiences = job_details.required_professional_experiences
    key_soft_skills = resume_details.key_soft_skills

    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are the world's best interview coach. We are conducting a mock interview where I am interviewing for the role of {job_title} at {company_name} company. "
                   f"I want you to ask me a question as if you are the actual hiring manager. You have my resume in front of you. "
                   f"You can see from my resume that my top soft skills are: {key_soft_skills}. "
                   f"You have the job description in front of you which shows that the job responsibilities are: {job_responsibilities} and the required professional experiences are: {required_professional_experiences}. "
                   "Identify similarities in the job description and my top soft skills. "
                   "Select one of my top soft skills that matches the job description and ask me to elaborate on how I developed and have used that soft skill in a specific project in the past."),
        MessagesPlaceholder(variable_name="messages"),
    ])

    chain = prompt | model
    response = chain.invoke({"messages": []})

    # Extract and clean the question from the response
    question_text = response.content.strip() if response.content else "No question generated"
    print(f"Extracted question text: {question_text}")

    return question_text

def get_third_score(answer, user_id):
    job_details = fetch_interview_data(user_id)
    job_title = job_details.job_title
    company_name = job_details.company_name
    company_industry = job_details.company_industry

    most_recent_question, _ = get_most_recent_question_answer()

    score_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are a career coach conducting a mock job interview with me. I’m interviewing to be a {job_title} at {company_name} company in the {company_industry} industry. "
                   f"You just asked me this question: {most_recent_question} "
                   "Your job is to give me an honest and critical score that ranges between 1-10. You are scoring me based on how accurate my answer was, how concise it was and how well I used realistic examples to illustrate my relevant experience. "
                   "Don't return any text in your response. Only return a single integer for the score ranging between 1-10 where 10 is the best. For example your response should be: 1 or 2 or 3 or 4 or 5 or 6 or 7 or 8 or 9 or 10."),
        ("user", answer),
        MessagesPlaceholder(variable_name="messages"),
    ])

    score_chain = score_prompt | model
    score_response = score_chain.invoke({"messages": [HumanMessage(content=answer)]})

    # Print the raw response from the chat model
    print(f"Score response from chat model: {score_response}")

    # Extract and clean the score from the response
    score_text = score_response.content.strip() if score_response.content else None
    print(f"Extracted score text: {score_text}")

    # Use regex to find the first integer in the response
    score_match = re.search(r'\b\d+\b', score_text)
    if score_match:
        score = int(score_match.group())
        print(f"Extracted score: {score}")
    else:
        print("No integer found in score response, setting score to None")
        score = None

    return score

def get_third_feedback(answer, user_id):
    job_details = fetch_interview_data(user_id)
    most_recent_question, _ = get_most_recent_question_answer()

    feedback_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are helping me land a new job by conducting realistic interviews with me. "
                   f"I’m interviewing to be a {job_details.job_title} at {job_details.company_name} company in the {job_details.company_industry} industry. "
                   f"You just asked me the question: '{most_recent_question}'. "
                   "I am going to answer you and I want you to give me a very critical critique of how well I answered the question."
                   "Specifically, check that my answer followed these best practices: Did I give an example of a specific project where I used this soft skill? "
                   "Did I clearly define my role and actions in my example? "
                   "Did I share the results of my actions and what I learned from the specific project? "
                   "Did I answer the question in a reasonable amount of time that lasted no more than 2 minutes? "
                   "Finally, please give me a recommendation on how I could have presented my experience better."),
        ("user", answer),
        MessagesPlaceholder(variable_name="messages"),
    ])

    analysis_chain = feedback_prompt | model

    feedback_response = analysis_chain.invoke({"messages": [HumanMessage(content=answer)]})

    # Print the raw response from the chat model
    print(f"Feedback response from chat model: {feedback_response}")

    # Extract and clean the feedback from the response
    feedback_text = feedback_response.content.strip() if feedback_response.content else "No feedback received"
    print(f"Extracted feedback text: {feedback_text}")

    return feedback_text

def get_fourth_question(user_id):
    job_details = fetch_interview_data(user_id)
    resume_details = db_session.query(Resumes).filter_by(user_id=user_id).first()
    
    job_title = job_details.job_title
    company_name = job_details.company_name
    most_recent_successful_project = resume_details.most_recent_successful_project

    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are the world's best interview coach. We are conducting a mock interview where I am interviewing for the role of {job_title} at {company_name} company. "
                   f"I want you to ask me a question as if you are the actual hiring manager. You have my resume in front of you. "
                   f"You can see from my resume that my most recent successful project was: {most_recent_successful_project}. "
                   f"Start your next question with, 'I noticed from your resume that a recent accomplishment was {most_recent_successful_project}'. "
                   "Follow that up by asking me to explain how I contributed and helped lead the team to the success of that project."),
        MessagesPlaceholder(variable_name="messages"),
    ])

    chain = prompt | model
    response = chain.invoke({"messages": []})

    # Print the raw response from the chat model
    print(f"Question response from chat model: {response}")

    # Extract and clean the question from the response
    question_text = response.content.strip() if response.content else "No question generated"
    print(f"Extracted question text: {question_text}")

    return question_text

def get_fourth_score(answer, user_id):
    job_details = fetch_interview_data(user_id)
    job_title = job_details.job_title
    company_name = job_details.company_name
    company_industry = job_details.company_industry

    most_recent_question, _ = get_most_recent_question_answer()

    score_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are a career coach conducting a mock job interview with me. I’m interviewing to be a {job_title} at {company_name} company in the {company_industry} industry. "
                   f"You just asked me this question: {most_recent_question} "
                   "Your job is to give me an honest and critical score that ranges between 1-10. You are scoring me based on how accurate my answer was, how concise it was and how well I used realistic examples to illustrate my relevant experience. "
                   "Don't return any text in your response. Only return a single integer for the score ranging between 1-10 where 10 is the best. For example your response should be: 1 or 2 or 3 or 4 or 5 or 6 or 7 or 8 or 9 or 10."),
        ("user", answer),
        MessagesPlaceholder(variable_name="messages"),
    ])

    score_chain = score_prompt | model
    score_response = score_chain.invoke({"messages": [HumanMessage(content=answer)]})

    # Print the raw response from the chat model
    print(f"Score response from chat model: {score_response}")

    # Extract and clean the score from the response
    score_text = score_response.content.strip() if score_response.content else None
    print(f"Extracted score text: {score_text}")

    # Use regex to find the first integer in the response
    score_match = re.search(r'\b\d+\b', score_text)
    if score_match:
        score = int(score_match.group())
        print(f"Extracted score: {score}")
    else:
        print("No integer found in score response, setting score to None")
        score = None

    return score

def get_fourth_feedback(answer, user_id):
    job_details = fetch_interview_data(user_id)
    most_recent_question, _ = get_most_recent_question_answer()

    feedback_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are helping me land a new job by conducting realistic interviews with me. "
                   f"I’m interviewing to be a {job_details.job_title} at {job_details.company_name} company in the {job_details.company_industry} industry. "
                   f"You just asked me the question: '{most_recent_question}'. "
                   "I am going to answer you and I want you to give me a very critical critique of how well I answered the question. "
                   "Specifically, check that my answer followed these best practices: Did I clearly outline my role and responsibilities in the project discussed? "
                   "Did I demonstrate aspects of being a strong team member or leader in the project? "
                   "Did I share the results of my actions and what I learned from the specific project? "
                   "Did I answer the question in a reasonable amount of time that lasted no more than 2 minutes? "
                   "Finally, please give me a recommendation on how I could have presented my experience better."),
        ("user", answer),
        MessagesPlaceholder(variable_name="messages"),
    ])

    analysis_chain = feedback_prompt | model

    feedback_response = analysis_chain.invoke({"messages": [HumanMessage(content=answer)]})

    # Print the raw response from the chat model
    print(f"Feedback response from chat model: {feedback_response}")

    # Extract and clean the feedback from the response
    feedback_text = feedback_response.content.strip() if feedback_response.content else "No feedback received"
    print(f"Extracted feedback text: {feedback_text}")

    return feedback_text


def get_fifth_question():
    # Add a debug statement to see if the function is being called
    print("Fetching a behavioral question from the database")

    try:
        # Query the database for a random behavioral question
        behavioral_questions = db_session.query(Questions).filter_by(question_type='behavioral questions').all()

        # Debugging: print out the retrieved questions
        print(f"Behavioral questions found: {len(behavioral_questions)}")
        for question in behavioral_questions:
            print(f"Question: {question.question}, ID: {question.id}, Type: {question.question_type}")

        # Select a random question if available
        if behavioral_questions:
            selected_question = random.choice(behavioral_questions)
            print(f"Selected question: {selected_question.question}, ID: {selected_question.id}")
            return selected_question.question, selected_question.id
        else:
            print("No behavioral questions found in the database")
            raise ValueError("No behavioral questions found in the database.")

    except Exception as e:
        # Print any exception that occurs
        print(f"Error while fetching behavioral questions: {e}")
        raise

# Enable SQLAlchemy logging to see the generated SQL queries
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)


# Enable SQLAlchemy logging to see the generated SQL queries
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)



def get_fifth_score(answer, user_id):
    job_details = fetch_interview_data(user_id)
    job_title = job_details.job_title
    company_name = job_details.company_name
    company_industry = job_details.company_industry

    most_recent_question, _ = get_most_recent_question_answer()

    score_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are a career coach conducting a mock job interview with me. I’m interviewing to be a {job_title} at {company_name} company in the {company_industry} industry. "
                   f"You just asked me this question: {most_recent_question} "
                   "Your job is to give me an honest and critical score that ranges between 1-10. You are scoring me based on how accurate my answer was, how concise it was and how well I used realistic examples to illustrate my relevant experience. "
                   "If my answer is less than 100 characters then you should always give a 1 as the score."
                   "Don't return any text in your response. Only return a single integer for the score ranging between 1-10 where 10 is the best. For example your response should be: 1 or 2 or 3 or 4 or 5 or 6 or 7 or 8 or 9 or 10."),
        ("user", answer),
        MessagesPlaceholder(variable_name="messages"),
    ])

    score_chain = score_prompt | model
    score_response = score_chain.invoke({"messages": [HumanMessage(content=answer)]})

    # Print the raw response from the chat model
    print(f"Score response from chat model: {score_response}")

    # Extract and clean the score from the response
    score_text = score_response.content.strip() if score_response.content else None
    print(f"Extracted score text: {score_text}")

    # Use regex to find the first integer in the response
    score_match = re.search(r'\b\d+\b', score_text)
    if score_match:
        score = int(score_match.group())
        print(f"Extracted score: {score}")
    else:
        print("No integer found in score response, setting score to None")
        score = None

    return score

def get_fifth_feedback(answer, user_id, question_id):
    job_details = fetch_interview_data(user_id)
    job_title = job_details.job_title
    company_name = job_details.company_name
    company_industry = job_details.company_industry

    most_recent_question, _ = get_most_recent_question_answer()

    # Fetch the description from the questions table using question_id
    question_data = db_session.query(Questions).filter_by(id=question_id).first()
    description = question_data.description if question_data else "No specific description available."

    feedback_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are helping me land a new job by conducting realistic interviews with me. "
                   f"I’m interviewing to be a {job_title} at {company_name} company in the {company_industry} industry. "
                   f"You just asked me the question: '{most_recent_question}'. "
                   "I am going to answer you and I want you to give me a very critical critique of how well I answered the question. "
                   f"Specifically, {description} "
                   "Did my answer meet that specific description? "
                   "Did I answer the question in a reasonable amount of time that lasted no more than 2 minutes? "
                   "Finally, please give me a recommendation on how I could have presented my experience better."),
        ("user", answer),
        MessagesPlaceholder(variable_name="messages"),
    ])

    analysis_chain = feedback_prompt | model

    feedback_response = analysis_chain.invoke({"messages": [HumanMessage(content=answer)]})

    # Print the raw response from the chat model
    print(f"Feedback response from chat model: {feedback_response}")

    # Extract and clean the feedback from the response
    feedback_text = feedback_response.content.strip() if feedback_response.content else "No feedback received"
    print(f"Extracted feedback text: {feedback_text}")

    return feedback_text

def get_sixth_question():
    # Add a debug statement to see if the function is being called
    print("Fetching a situational question from the database")

    try:
        # Query the database for a random situational question
        situational_questions = db_session.query(Questions).filter_by(question_type='situational questions').all()

        # Debugging: print out the retrieved questions
        print(f"Situational questions found: {len(situational_questions)}")
        for question in situational_questions:
            print(f"Question: {question.question}, ID: {question.id}, Type: {question.question_type}")

        # Select a random question if available
        if situational_questions:
            selected_question = random.choice(situational_questions)
            print(f"Selected question: {selected_question.question}, ID: {selected_question.id}")
            return selected_question.question, selected_question.id
        else:
            print("No situational questions found in the database")
            raise ValueError("No situational questions found in the database.")

    except Exception as e:
        # Print any exception that occurs
        print(f"Error while fetching situational questions: {e}")
        raise

# Enable SQLAlchemy logging to see the generated SQL queries
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

def get_sixth_score(answer, user_id):
    job_details = fetch_interview_data(user_id)
    job_title = job_details.job_title
    company_name = job_details.company_name
    company_industry = job_details.company_industry

    most_recent_question, _ = get_most_recent_question_answer()

    score_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are a career coach conducting a mock job interview with me. I’m interviewing to be a {job_title} at {company_name} company in the {company_industry} industry. "
                   f"You just asked me this question: {most_recent_question} "
                   "Your job is to give me an honest and critical score that ranges between 1-10. You are scoring me based on how accurate my answer was, how concise it was and how well I used realistic examples to illustrate my relevant experience. "
                   "If my answer is less than 100 characters then you should always give a 1 as the score."
                   "Don't return any text in your response. Only return a single integer for the score ranging between 1-10 where 10 is the best. For example your response should be: 1 or 2 or 3 or 4 or 5 or 6 or 7 or 8 or 9 or 10."),
        ("user", answer),
        MessagesPlaceholder(variable_name="messages"),
    ])

    score_chain = score_prompt | model
    score_response = score_chain.invoke({"messages": [HumanMessage(content=answer)]})

    # Print the raw response from the chat model
    print(f"Score response from chat model: {score_response}")

    # Extract and clean the score from the response
    score_text = score_response.content.strip() if score_response.content else None
    print(f"Extracted score text: {score_text}")

    # Use regex to find the first integer in the response
    score_match = re.search(r'\b\d+\b', score_text)
    if score_match:
        score = int(score_match.group())
        print(f"Extracted score: {score}")
    else:
        print("No integer found in score response, setting score to None")
        score = None

    return score

def get_sixth_feedback(answer, user_id, question_id):
    job_details = fetch_interview_data(user_id)
    job_title = job_details.job_title
    company_name = job_details.company_name
    company_industry = job_details.company_industry

    most_recent_question, _ = get_most_recent_question_answer()

    # Fetch the description from the questions table using question_id
    question_data = db_session.query(Questions).filter_by(id=question_id).first()
    description = question_data.description if question_data else "No specific description available."

    feedback_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are helping me land a new job by conducting realistic interviews with me. "
                   f"I’m interviewing to be a {job_title} at {company_name} company in the {company_industry} industry. "
                   f"You just asked me the question: '{most_recent_question}'. "
                   "I am going to answer you and I want you to give me a very critical critique of how well I answered the question. "
                   f"Specifically, {description} "
                   "Did my answer meet that specific description? "
                   "Did I answer the question in a reasonable amount of time that lasted no more than 2 minutes? "
                   "Finally, please give me a recommendation on how I could have presented my experience better."),
        ("user", answer),
        MessagesPlaceholder(variable_name="messages"),
    ])

    analysis_chain = feedback_prompt | model

    feedback_response = analysis_chain.invoke({"messages": [HumanMessage(content=answer)]})

    # Print the raw response from the chat model
    print(f"Feedback response from chat model: {feedback_response}")

    # Extract and clean the feedback from the response
    feedback_text = feedback_response.content.strip() if feedback_response.content else "No feedback received"
    print(f"Extracted feedback text: {feedback_text}")

    return feedback_text


def get_seventh_question():
    print("Fetching a personality question from the database")
    question_data = db_session.query(Questions).filter_by(question_type='personality questions').order_by(func.random()).first()
    
    if not question_data:
        raise ValueError("No personality questions found in the database.")
    
    question = question_data.question
    question_id = question_data.id
    
    print(f"Fetched question: {question} with ID: {question_id}")
    return question, question_id

def get_seventh_score(answer, user_id):
    job_details = fetch_interview_data(user_id)
    job_title = job_details.job_title
    company_name = job_details.company_name
    company_industry = job_details.company_industry

    most_recent_question, _ = get_most_recent_question_answer()

    score_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are a career coach conducting a mock job interview with me. I’m interviewing to be a {job_title} at {company_name} company in the {company_industry} industry. "
                   f"You just asked me this question: {most_recent_question} "
                   "Your job is to give me an honest and critical score that ranges between 1-10. You are scoring me based on how accurate my answer was, how concise it was and how well I used realistic examples to illustrate my relevant experience. "
                   "If my answer is less than 100 characters then you should always give a 1 as the score. "
                   "Don't return any text in your response. Only return a single integer for the score ranging between 1-10 where 10 is the best. For example your response should be: 1 or 2 or 3 or 4 or 5 or 6 or 7 or 8 or 9 or 10."),
        ("user", answer),
        MessagesPlaceholder(variable_name="messages"),
    ])

    score_chain = score_prompt | model
    score_response = score_chain.invoke({"messages": [HumanMessage(content=answer)]})

    # Print the raw response from the chat model
    print(f"Score response from chat model: {score_response}")

    # Extract and clean the score from the response
    score_text = score_response.content.strip() if score_response.content else None
    print(f"Extracted score text: {score_text}")

    # Use regex to find the first integer in the response
    score_match = re.search(r'\b\d+\b', score_text)
    if score_match:
        score = int(score_match.group())
        print(f"Extracted score: {score}")
    else:
        print("No integer found in score response, setting score to None")
        score = None

    return score

def get_seventh_feedback(answer, user_id, question_id):
    job_details = fetch_interview_data(user_id)
    job_title = job_details.job_title
    company_name = job_details.company_name
    company_industry = job_details.company_industry

    most_recent_question, _ = get_most_recent_question_answer()

    # Fetch the description from the questions table using question_id
    question_data = db_session.query(Questions).filter_by(id=question_id).first()
    description = question_data.description if question_data else "No specific description available."

    feedback_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are helping me land a new job by conducting realistic interviews with me. "
                   f"I’m interviewing to be a {job_title} at {company_name} company in the {company_industry} industry. "
                   f"You just asked me the question: '{most_recent_question}'. "
                   "I am going to answer you and I want you to give me a very critical critique of how well I answered the question. "
                   f"Specifically, {description} "
                   "Did my answer meet that specific description? "
                   "Did I answer the question in a reasonable amount of time that lasted no more than 2 minutes? "
                   "Finally, please give me a recommendation on how I could have presented my experience better."),
        ("user", answer),
        MessagesPlaceholder(variable_name="messages"),
    ])

    analysis_chain = feedback_prompt | model

    feedback_response = analysis_chain.invoke({"messages": [HumanMessage(content=answer)]})

    # Print the raw response from the chat model
    print(f"Feedback response from chat model: {feedback_response}")

    # Extract and clean the feedback from the response
    feedback_text = feedback_response.content.strip() if feedback_response.content else "No feedback received"
    print(f"Extracted feedback text: {feedback_text}")

    return feedback_text


def get_eighth_question(username):
    return "How do you stay updated with industry trends?"

def get_eighth_feedback(answer):
    return "Great approach"

def get_eighth_score(answer):
    return 9

def get_ninth_question(username):
    return "Can you describe a time when you had to learn something quickly?"

def get_ninth_feedback(answer):
    return "Well handled"

def get_ninth_score(answer):
    return 8

def get_tenth_question(username):
    return "How do you handle conflicts at work?"

def get_tenth_feedback(answer):
    return "Good conflict resolution"

def get_tenth_score(answer):
    return 9

def get_last_question(username):
    return (f"Thanks {username}. It looks like we need to start wrapping up this call. "
            f"I’ve really enjoyed getting to know you. Before we end the call, however, "
            f"do you have any questions for me? I’d be happy to answer what I can about the company, "
            f"the role, or anything else that comes to mind. Please ask me all of the questions that you have in your response to this.")

def get_last_score(answer):
    return 7

def get_last_feedback(answer):
    return "That was a great question."

def get_summary_message():
    return "Great job!"
