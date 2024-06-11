import os
import uuid
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
from elevenlabs.client import ElevenLabs

# Import models from app package
from app.models import TrainingData, InterviewAnswer, User

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

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

# Initialize the OpenAI chat model
openai_api_key = os.getenv("OPENAI_API_KEY")
model = ChatOpenAI(model="gpt-3.5-turbo", api_key=openai_api_key, temperature=0.5)

# In-memory store for chat histories and most recent question and responses
chat_histories = {}
most_recent_question = ""
user_responses = {"resume_user_response": None, "career_user_responses": []}

def get_session_history(session_id: str) -> ChatMessageHistory:
    if session_id not in chat_histories:
        chat_histories[session_id] = ChatMessageHistory()
    return chat_histories[session_id]

def users_training_data(session: Session, user_id: int, job_title: str, company_name: str):
    # Query all rows for the given user_id, job_title, and company_name, ordered by updated_at in descending order
    training_data_rows = session.query(TrainingData).filter_by(user_id=user_id, job_title=job_title, company_name=company_name).order_by(TrainingData.updated_at.desc()).all()
    
    data_dict = {}
    
    if training_data_rows:
        for i, training_data in enumerate(training_data_rows):
            suffix = "" if i == 0 else f"_{i + 1}"
            
            data_dict[f"file_summary{suffix}"] = str(training_data.file_summary)
            data_dict[f"top_topics{suffix}"] = str(training_data.top_topics)
            data_dict[f"primary_products_and_services{suffix}"] = str(training_data.primary_products_and_services)
            data_dict[f"target_market{suffix}"] = str(training_data.target_market)
            data_dict[f"market_position{suffix}"] = str(training_data.market_position)
            data_dict[f"required_skills{suffix}"] = str(training_data.required_skills)
            data_dict[f"unique_selling_proposition{suffix}"] = str(training_data.unique_selling_proposition)

    if not data_dict:
        print("No training data found for the given user_id, job_title, and company_name.")
    
    print("Returning data_dict:", data_dict)  # Debug print
    return data_dict




def generate_next_question(job_title, company_name, industry, session_history, session, training_data):
    global most_recent_question

    file_summary = training_data.get("file_summary", "")

    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are the world’s best interview coach. I have hired you to conduct a mock interview with me. You should ask me a new question you haven’t already asked. The question should challenge my ability to work as a {job_title} at {company_name} company in the {industry} industry. Here is more context about {company_name}: {file_summary}."),
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

    return (resume_text_full, top_technical_skills, most_recent_job_title, most_recent_company_name, most_recent_experience_summary, industry_expertise, top_soft_skills)

def get_resume_question_answer(session: Session, username: str, job_title: str, company_name: str, industry: str, resume_user_response: str, file_summary: str):
    global most_recent_question, user_responses

    resume_data = get_user_resume_data(session, username)
    if not resume_data:
        return {"response": "No resume data found for user.", "score": "N/A", "next_question": "N/A"}

    (resume_text_full, top_technical_skills, most_recent_job_title, most_recent_company_name,
     most_recent_experience_summary, industry_expertise, top_soft_skills) = resume_data

    # Prompt 1: Analyze the user's answer
    analysis_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are helping me land a new job by conducting a mock interview with me. I’m interviewing to be a {job_title} at {company_name} company in the {industry} industry. You just asked me the question: 'tell me about your professional experience and how it relates to this role at {company_name}'. I am going to answer you and I want you to give me a critical critique of how well I answered the question. Specifically check that my answer followed these best practices: Is there an opening, middle and closing? Did my opening answer the question, without adding extra ideas or unnecessary words? Did the middle of my answer give details that support my opening sentence? Did I give one, two, or three details? Did I follow the STAR format (situation, task, action, result)? Once I finished my answer did I say something that showed I was finished? You can also reference this information about me: I was most recently a {most_recent_job_title} at {most_recent_company_name} company. I have experience in: {most_recent_experience_summary}. Here is more context about the company {company_name} I’m interviewing to work at: {file_summary}."),
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
    next_question = generate_next_question(job_title, company_name, industry, session_history, session, training_data={"file_summary": file_summary})

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


def get_career_experience_answer(session: Session, username: str, job_title: str, company_name: str, industry: str, career_user_response: str, file_summary: str):
    global most_recent_question, user_responses

    resume_data = get_user_resume_data(session, username)
    if not resume_data:
        return {"response": "No resume data found for user.", "score": "N/A", "next_question": "N/A"}

    (resume_text_full, top_technical_skills, most_recent_job_title, most_recent_company_name,
     most_recent_experience_summary, industry_expertise, top_soft_skills) = resume_data

    # Prompt 1: Analyze the user's answer
    analysis_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are helping me land a new job by conducting a mock interview with me. I’m interviewing to be a {job_title} at {company_name} company in the {industry} industry. You just asked me the question: {most_recent_question}. Give me a very critical critique of how well I answered the question. Specifically check that my answer followed these best practices: Is there an opening, middle and closing? Did my opening answer the question, without adding extra ideas or unnecessary words? Did the middle of my answer give details that support my opening sentence? Did I give one, two, or three details? Did I follow the STAR format (situation, task, action, result)? Once I finished my answer did I say something that showed I was finished? For more context: I was most recently a {most_recent_job_title} at {most_recent_company_name} company. I have experience in: {most_recent_experience_summary}. Here is more context about the company {company_name} I’m interviewing to work at: {file_summary}. Based on my experience and the context about {company_name} and my specific answer please give me feedback."),
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
    next_question = generate_next_question(job_title, company_name, industry, session_history, session, training_data={"file_summary": file_summary})

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
