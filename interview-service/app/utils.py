import os
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
from app.models import JobDescriptionAnalysis, User, InterviewHistory, Questions

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# Ensure ffmpeg is found
ffmpeg_location = os.getenv('FFMPEG_LOCATION')
AudioSegment.converter = which("ffmpeg") or ffmpeg_location

# Initialize the OpenAI chat model
openai_api_key = os.getenv("OPENAI_API_KEY")
model = ChatOpenAI(model="gpt-3.5-turbo", api_key=openai_api_key, temperature=0.5)

# Global variables to store questions and answers
store_questions_asked = []
store_answers = []
global_feedback = None
global_score = None
session_id = None

# Initialize database session
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = SessionLocal()


def generate_session_id():
    return random.randint(100000, 999999)


def text_to_speech_file(text: str, voice_id: str) -> str:
    if not text.strip():
        print("Text is empty, skipping text-to-speech conversion.")
        return ""

    try:
        response = elevenlabs_client.text_to_speech.convert(
            voice_id=voice_id,
            optimize_streaming_latency="0",
            output_format="mp3_22050_32",
            text=text,
            model_id="eleven_turbo_v2",
            voice_settings=VoiceSettings(
                stability=0.0,
                similarity_boost=1.0,
                style=0.0,
                use_speaker_boost=True,
            ),
        )

        save_file_path = os.path.join("audio_files", f"{uuid.uuid4()}.mp3")
        os.makedirs(os.path.dirname(save_file_path), exist_ok=True)

        with open(save_file_path, "wb") as f:
            for chunk in response:
                if chunk:
                    f.write(chunk)

        print(f"{save_file_path}: A new audio file was saved successfully!")
        return save_file_path
    except ApiError as e:
        print(f"Error generating speech: {e}")
        return ""

def get_answer_1(answer):
    # Store the answer globally
    store_answers.append(answer)
    print("User response stored:", answer)

def intro_question(user_id):
    # Function to generate the introductory question based on the user's data
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()

        if user and job_description:
            username = user.username
            job_title = job_description.job_title
            company_name = job_description.company_name

            intro_question_text = (f"Hi {username}, thanks for taking this meeting to discuss the {job_title} role at {company_name}. "
                                   "I'm excited to learn more about you. Could you please start by telling me more about yourself? "
                                   f"Specifically, what professional experiences have you had that make you a good fit for the {job_title} role at {company_name}?")
            # Store the initial question globally with is_initial flag
            store_question(intro_question_text, is_initial=True)
            return intro_question_text
        else:
            return "Error: User or job description not found."
    except Exception as e:
        print(f"Error generating intro question: {e}")
        return "Error: Could not generate intro question."



def store_user_response(answer):
    # Function to store user responses globally
    store_answers.append(answer)
    print("User response stored:", answer)

def store_question(question, is_initial=False):
    if is_initial:
        store_questions_asked.append({"question": question, "type": "initial"})
    else:
        store_questions_asked.append({"question": question, "type": "follow_up"})
    print("Question stored:", question)


def get_last_question():
    # Function to get the last question asked
    if store_questions_asked:
        return store_questions_asked[-1]
    return None

def get_score(user_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()

        if not user:
            raise ValueError("User not found")

        if not store_answers or not store_questions_asked:
            raise ValueError("No answers or questions stored")

        most_recent_job_title = user.most_recent_job_title
        key_soft_skills = user.key_soft_skills
        key_technical_skills = user.key_technical_skills

        most_recent_answer = store_answers[-1]
        most_recent_question = store_questions_asked[-1]["question"]

        score_prompt = ChatPromptTemplate.from_messages([
            ("system", f"Score the answer I am sending you to the question '{most_recent_question}' from 0 to 10. "
                       f"It should be incredibly hard to score an 8, 9 or 10 unless you decide the answer was very good. "
                       f"When scoring, keep in mind that I was most recently a {most_recent_job_title}. "
                       f"I have experience in: {key_soft_skills} and {key_technical_skills}."),
            ("user", most_recent_answer),
            MessagesPlaceholder(variable_name="messages"),
        ])

        score_chain = score_prompt | model
        print("Sending score prompt to OpenAI API...")

        score_response = score_chain.invoke({"messages": [HumanMessage(content=most_recent_answer)]})

        score = extract_score(score_response.content)
        global global_score
        global_score = score  # Store the score globally
        return score
    except Exception as e:
        print(f"Error in get_score function: {e}")
        return "Error: Could not calculate score."



def extract_score(content):
    # Extract score from the response content
    score_match = re.search(r'\d+', content)
    if score_match:
        return int(score_match.group())
    return 0


def get_intro_question_feedback(user_id, session_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()

        if not user or not job_description:
            raise ValueError("User or job description not found")

        job_title = job_description.job_title
        company_name = job_description.company_name
        industry = job_description.company_industry

        if not store_answers or not store_questions_asked:
            raise ValueError("No answers or questions stored")

        most_recent_answer = store_answers[-1]

        feedback_prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are helping me land a new job by conducting realistic interviews with me. "
                       f"I’m interviewing to be a {job_title} at {company_name} company in the {industry} industry. "
                       f"You just asked me the question: 'tell me about your professional experience and how it relates to this role at {company_name}'. "
                       "I am going to answer you and I want you to give me a very critical critique of how well I answered the question. "
                       "Specifically, check that my answer followed these best practices: Is there an opening, middle and closing? "
                       "Did my opening answer the question, without adding extra ideas or unnecessary words? "
                       "Did the middle of my answer give details that support my opening sentence? Did I give one, two, or three details? "
                       "Once I finished my answer did I say something that showed I was finished? "
                       "Did I answer the question in a reasonable amount of time that lasted no more than 2 minutes? "
                       "Finally, please give me a recommendation on how I could have presented my experience better. "
                       f"When you are critiquing me please refer to my resume information which you have on a piece of paper in front of you. "
                       f"The resume shows: I was most recently a {user.most_recent_job_title} "
                       f"I have experience in: {user.most_recent_job_title_summary} and {user.second_most_recent_job_title_summary}."),
            ("user", most_recent_answer),
            MessagesPlaceholder(variable_name="messages"),
        ])

        analysis_chain = feedback_prompt | model
        print("Sending feedback prompt to OpenAI API...")

        feedback_response = analysis_chain.invoke({"messages": [HumanMessage(content=most_recent_answer)]})

        global global_feedback
        global_feedback = feedback_response.content

        global global_score
        global_score = get_score(user_id) if store_answers and store_questions_asked else None

        next_question = get_resume_question_1(user_id)

        # Immediately send the next question to the front end
        response_data = {
            "feedback_response": global_feedback,
            "score_response": global_score,
            "next_question_response": next_question
        }

        # Write to interview history table after sending response to the front end
        if store_answers and store_questions_asked:
            write_interview_history_table(user_id, session_id, is_initial=True)

        return response_data
    except Exception as e:
        print(f"Error in get_intro_question_feedback function: {e}")
        return {
            "feedback_response": "Error: Could not generate feedback.",
            "score_response": "Error: Could not calculate score.",
            "next_question_response": "Error: Could not generate next question."
        }



def write_interview_history_table(user_id, session_id, is_initial=False):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()

        if not user or not job_description:
            raise ValueError("User or job description not found")

        if not store_answers or not store_questions_asked:
            raise ValueError("No answers or questions stored")

        # Determine the question to store
        question = store_questions_asked[0]["question"] if is_initial else store_questions_asked[-1]["question"]

        new_interview_history = InterviewHistory(
            id=random.randint(1, 2147483647),  # Generate a unique id within the 32-bit integer range
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            job_title=job_description.job_title,
            company_name=job_description.company_name,
            company_industry=job_description.company_industry,
            question=question,
            question_id=0,  # Update this if you have question_id
            answer=store_answers[-1],
            feedback=global_feedback,
            score=global_score,
            skip_next_time=False,
            session_score_average=None,
            session_top_score=None,
            session_low_score=None,
            session_summary_next_steps=None
        )

        db_session.add(new_interview_history)
        db_session.commit()
        print("Interview history record added successfully.")
    except Exception as e:
        print(f"Error in write_interview_history_table function: {e}")




def get_resume_question_1(user_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()

        if not user or not job_description:
            raise ValueError("User or job description not found")

        job_title = user.most_recent_job_title
        key_technical_skills = user.key_technical_skills

        job_responsibilities = job_description.job_responsibilities
        required_professional_experiences = job_description.required_professional_experiences
        required_skill_sets = job_description.required_skill_sets

        print(f"Job Responsibilities: {job_responsibilities}")
        print(f"Required Professional Experiences: {required_professional_experiences}")
        print(f"Required Skill Sets: {required_skill_sets}")

        prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are the world's best interview coach. We are conducting an interview for the role of {job_title} at {job_description.company_name} company. "
                       f"I want you to ask me a question as if you are the actual hiring manager. You have my resume in front of you. "
                       f"You can see from my resume that my top technical skills are: {key_technical_skills}. "
                       f"You have the job description in front of you which shows that the job responsibilities are: {job_responsibilities} and the required professional experiences are: {required_professional_experiences}. "
                       f"It also shows that the required skill sets are: {required_skill_sets}. "
                       "Identify similarities in the job description and my top technical skills. "
                       "Pick the most relevant of my technical skills and ask me to go into more detail on how I have used a top technical skill in the past."),
            MessagesPlaceholder(variable_name="messages"),
        ])

        chain = prompt | model
        print("Sending prompt to OpenAI API for generating resume question 1...")
        print(f"Prompt: {prompt}")

        response = chain.invoke({"messages": []})

        question = response.content
        store_questions_asked.append(question)
        return question
    except Exception as e:
        print(f"Error in get_resume_question_1 function: {e}")
        return "Error: Could not generate resume question 1."
    
