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
from elevenlabs.client import ElevenLabs, ApiError

# Import models from app package
from app.models import TrainingData, InterviewAnswer, User, VideoRecordingLog
from app.resume_utils import get_user_resume_data

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
interview_answers_question_history = ""  # New global variable for question history

def get_session_history(session_id: str) -> ChatMessageHistory:
    if session_id not in chat_histories:
        chat_histories[session_id] = ChatMessageHistory()
    return chat_histories[session_id]


def users_training_data(session, user_id, job_title, company_name):
    try:
        logging.debug(f"Fetching training data for user_id: {user_id}, job_title: {job_title}, company_name: {company_name}")
        
        # Fetch the User object
        user = session.query(User).filter_by(id=user_id).one_or_none()
        if not user:
            logging.error(f"User not found for user_id: {user_id}")
            return {}

        # Fetch the most recent TrainingData object
        training_data = session.query(TrainingData).filter_by(user_id=user_id, job_title=job_title, company_name=company_name).order_by(TrainingData.created_at.desc()).first()
        if not training_data:
            logging.error(f"Training data not found for user_id: {user_id}, job_title: {job_title}, company_name: {company_name}")
            return {}

        resume_data = get_user_resume_data(session, user.username)
        if not resume_data:
            logging.error(f"No resume data found for user: {user.username}")
            return {}

        (resume_text_full, key_technical_skills, key_soft_skills, most_recent_job_title, second_most_recent_job_title,
         most_recent_job_title_summary, second_most_recent_job_title_summary, top_listed_skill_keyword,
         second_most_top_listed_skill_keyword, third_most_top_listed_skill_keyword, fourth_most_top_listed_skill_keyword,
         educational_background, certifications_and_awards, most_recent_successful_project, areas_for_improvement,
         questions_about_experience, resume_length, top_challenge) = resume_data

        # Log the resume data fetched
        logging.debug(f"Resume data fetched for user: {user.username}")
        logging.debug(f"Resume Text Full: {resume_text_full}")
        logging.debug(f"Key Technical Skills: {key_technical_skills}")
        logging.debug(f"Most Recent Job Title: {most_recent_job_title}")
        logging.debug(f"Second Most Recent Job Title: {second_most_recent_job_title}")
        logging.debug(f"Most Recent Job Title Summary: {most_recent_job_title_summary}")
        logging.debug(f"Second Most Recent Job Title Summary: {second_most_recent_job_title_summary}")
        logging.debug(f"Top Listed Skill Keyword: {top_listed_skill_keyword}")
        logging.debug(f"Second Most Top Listed Skill Keyword: {second_most_top_listed_skill_keyword}")
        logging.debug(f"Third Most Top Listed Skill Keyword: {third_most_top_listed_skill_keyword}")
        logging.debug(f"Fourth Most Top Listed Skill Keyword: {fourth_most_top_listed_skill_keyword}")
        logging.debug(f"Educational Background: {educational_background}")
        logging.debug(f"Certifications and Awards: {certifications_and_awards}")
        logging.debug(f"Most Recent Successful Project: {most_recent_successful_project}")
        logging.debug(f"Areas for Improvement: {areas_for_improvement}")
        logging.debug(f"Questions About Experience: {questions_about_experience}")
        logging.debug(f"Resume Length: {resume_length}")
        logging.debug(f"Top Challenge: {top_challenge}")

        # Construct the training data dictionary from the TrainingData object
        training_data_dict = {
            "file_summary": training_data.file_summary,
            "top_topics": training_data.top_topics,
            "primary_products_and_services": training_data.primary_products_and_services,
            "target_market": training_data.target_market,
            "market_position": training_data.market_position,
            "required_skills": training_data.required_skills,
            "unique_selling_proposition": training_data.unique_selling_proposition,
            "key_technical_skills": key_technical_skills,  # Updated to use key_technical_skills from resume data
            "key_soft_skills": key_soft_skills  # Include key soft skills from resume data
        }

        # Log the constructed training data
        logging.debug(f"Constructed training data: {training_data_dict}")

        return training_data_dict
    except Exception as e:
        logging.error(f"Error in users_training_data: {e}", exc_info=True)
        return {}


        # Log the constructed training data
        logging.debug(f"Constructed training data: {training_data_dict}")

        return training_data_dict
    except Exception as e:
        logging.error(f"Error in users_training_data: {e}", exc_info=True)
        return {}


# used to download csv transcript
def fetch_interview_data(session: Session, session_id: str):
    interview_data = session.query(InterviewAnswer).filter_by(session_id=session_id).all()
    if not interview_data:
        print("No interview data found for the given session_id.")
    return interview_data


# Renamed question generation functions
def generate_question_2(job_title, company_name, industry, session_history, session, training_data, keys_to_include):
    global most_recent_question, interview_answers_question_history
    print("Starting generate_question_2")

    key_technical_skills = training_data.get("key_technical_skills", "")
    prompt_variables = {key: training_data.get(key, "") for key in keys_to_include}
    prompt_str = " ".join([f"{key}: {value}" for key, value in prompt_variables.items()])

    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are the world's best interview coach. We are conducting an interview and I want you to ask me a question as if you are the actual hiring manager so that this interview feels real. You can see from my resume that my top technical skills are: {key_technical_skills}. Choose a relevant skill from my list of top technical skills and ask me to explain how I have used that skill in the past."),
        MessagesPlaceholder(variable_name="messages"),
    ])

    chain = prompt | model
    print("Sending prompt to OpenAI API for generating second question...")
    print(f"Prompt: {prompt}")

    response = chain.invoke({"messages": session_history.messages})

    most_recent_question = response.content
    interview_answers_question_history += f"\n{most_recent_question}"  # Update the question history
    print("Updated most_recent_question in generate_question_2:", most_recent_question)
    print("Updated interview_answers_question_history in generate_question_2:", interview_answers_question_history)
    print("generate_question_2 completed.")
    return most_recent_question

def generate_question_3(job_title, company_name, industry, session_history, session, training_data, keys_to_include):
    global most_recent_question, interview_answers_question_history
    print("Starting generate_question_3")

    # Ensure specific keys like key_soft_skills and most_recent_job_title are included in the prompt
    key_soft_skills = training_data.get("key_soft_skills", "")
    most_recent_job_title = training_data.get("most_recent_job_title", "")

    # Dynamically construct the prompt based on provided keys
    prompt_variables = {key: training_data.get(key, "") for key in keys_to_include}
    prompt_str = " ".join([f"{key}: {value}" for key, value in prompt_variables.items()])

    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are the world's best interview coach. We are conducting an interview and I want you to ask me a question as if you are the actual hiring manager so that this interview feels real. You have my resume in front of you where you can see that my top soft skills are: {key_soft_skills}. My most recent job title is {most_recent_job_title}. Ask me a question about how I have used some of my soft skills listed in my resume as a {most_recent_job_title}."),
        MessagesPlaceholder(variable_name="messages"),
    ])
    print(f"Prompt created: {prompt}")

    chain = prompt | model
    print("Sending prompt to OpenAI API for generating third question...")
    print(f"Prompt: {prompt}")

    response = chain.invoke({"messages": session_history.messages})

    # Explicitly set most_recent_question with the new question
    most_recent_question = response.content
    interview_answers_question_history += f"\n{most_recent_question}"  # Update the question history
    print("Updated most_recent_question in generate_question_3:", most_recent_question)
    print("generate_question_3 completed.")
    return most_recent_question

def generate_question_4(job_title, company_name, industry, session_history, session, training_data, keys_to_include):
    global most_recent_question, interview_answers_question_history
    print("Starting generate_question_4")

    # Ensure specific key like most_recent_successful_project is included in the prompt
    most_recent_successful_project = training_data.get("most_recent_successful_project", "")

    # Dynamically construct the prompt based on provided keys
    prompt_variables = {key: training_data.get(key, "") for key in keys_to_include}
    prompt_str = " ".join([f"{key}: {value}" for key, value in prompt_variables.items()])

    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are the world's best interview coach. We are conducting an interview and I want you to ask me a question as if you are the actual hiring manager so that this interview feels real. You have my resume in front of you and you can see that my most successful project was: {most_recent_successful_project}. Start your next question with, \"I noticed from your resume that a recent accomplishment was {most_recent_successful_project}\". Follow that up by asking me to explain how I contributed and helped lead the team to the success of that project."),
        MessagesPlaceholder(variable_name="messages"),
    ])

    chain = prompt | model
    print("Sending prompt to OpenAI API for generating fourth question...")
    print(f"Prompt: {prompt}")

    response = chain.invoke({"messages": session_history.messages})

    # Explicitly set most_recent_question with the new question
    most_recent_question = response.content
    interview_answers_question_history += f"\n{most_recent_question}"  # Update the question history
    print("Updated most_recent_question in generate_question_4:", most_recent_question)
    print("generate_question_4 completed.")
    return most_recent_question

def generate_question_5(job_title, company_name, industry, session_history, session, training_data, keys_to_include):
    global most_recent_question, interview_answers_question_history
    print("Starting generate_question_5")

    # Ensure specific key like top_challenge is included in the prompt
    top_challenge = training_data.get("top_challenge", "")

    # Dynamically construct the prompt based on provided keys
    prompt_variables = {key: training_data.get(key, "") for key in keys_to_include}
    prompt_str = " ".join([f"{key}: {value}" for key, value in prompt_variables.items()])

    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are the world's best interview coach. We are conducting an interview and I want you to ask me a question as if you are the actual hiring manager so that this interview feels real. You have my resume in front of you and you can see that a really challenging project I worked on is: {top_challenge}. Start your next question with, \"I noticed from your resume that a really interesting project you worked on was: {top_challenge}\". Follow that up by asking me to explain what challenges I faced while working on this project."),
        MessagesPlaceholder(variable_name="messages"),
    ])

    chain = prompt | model
    print("Sending prompt to OpenAI API for generating fifth question...")
    print(f"Prompt: {prompt}")

    response = chain.invoke({"messages": session_history.messages})

    # Explicitly set most_recent_question with the new question
    most_recent_question = response.content
    interview_answers_question_history += f"\n{most_recent_question}"  # Update the question history
    print("Updated most_recent_question in generate_question_5:", most_recent_question)
    print("generate_question_5 completed.")
    return most_recent_question

def generate_infinite_questions(job_title, company_name, industry, session_history, session, training_data, keys_to_include):
    global most_recent_question, interview_answers_question_history
    print("Starting generate_infinite_questions")

    chat_history_messages = session_history.messages
    chat_history = "\n".join([f"{message.__class__.__name__}: {message.content}" for message in chat_history_messages])

    print(f"Chat History for prompt: {chat_history}")
    print(f"Interview Answers Question History for prompt: {interview_answers_question_history}")

    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are the world's best interview coach. We are conducting an interview and I want you to ask me a question as if you are the actual hiring manager so that this interview feels real. I’m interviewing to be a {job_title} at {company_name} company. Please ask me a relevant question that would be asked in a job interview with someone who wants to get hired as a {job_title} at {company_name}. Do not ask me a question that is similar to one you have asked before. I’m going to be sending you our interview we’ve had so far. Again, do not ask a question similar to one that is in our interview history I send to you now."),
        ("user", f"{interview_answers_question_history}"),
        MessagesPlaceholder(variable_name="messages"),
    ])

    chain = prompt | model
    print("Sending prompt to OpenAI API for generating infinite question...")
    print(f"Prompt: {prompt}")

    response = chain.invoke({"messages": session_history.messages})

    most_recent_question = response.content
    interview_answers_question_history += f"\n{most_recent_question}"  # Update the question history
    print("Updated most_recent_question in generate_infinite_questions:", most_recent_question)
    print("Updated interview_answers_question_history in generate_infinite_questions:", interview_answers_question_history)
    print("generate_infinite_questions completed.")
    return most_recent_question



# Renamed answer functions
def get_answer_1(session: Session, username: str, job_title: str, company_name: str, industry: str, user_response: str, file_summary: str, session_id: str, training_data: dict, keys_to_include: list):
    global most_recent_question, user_responses
    print("Starting get_answer_1")

    resume_data = get_user_resume_data(session, username)
    if not resume_data:
        return {"response": "No resume data found for user.", "score": "N/A", "next_question": "N/A"}

    # Convert the resume_data tuple to a dictionary using keys
    resume_keys = [
        "resume_text_full", "key_technical_skills", "key_soft_skills", "most_recent_job_title", 
        "second_most_recent_job_title", "most_recent_job_title_summary", "second_most_recent_job_title_summary", 
        "top_listed_skill_keyword", "second_most_top_listed_skill_keyword", "third_most_top_listed_skill_keyword", 
        "fourth_most_top_listed_skill_keyword", "educational_background", "certifications_and_awards", 
        "most_recent_successful_project", "areas_for_improvement", "questions_about_experience", 
        "resume_length", "top_challenge"
    ]
    resume_data_dict = dict(zip(resume_keys, resume_data))

    # Combine resume_data_dict and training_data
    combined_data = {**resume_data_dict, **training_data}

    # Extract relevant data based on keys_to_include
    data_to_include = {key: combined_data.get(key, "") for key in keys_to_include}

    # Prepare the analysis prompt with included data
    analysis_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are helping me land a new job by conducting realistic interviews with me. I’m interviewing to be a {job_title} at {company_name} company in the {industry} industry. You just asked me the question: 'tell me about your professional experience and how it relates to this role at {company_name}'. I am going to answer you and I want you to give me a very critical critique of how well I answered the question. Specifically, check that my answer followed these best practices: Is there an opening, middle and closing? Did my opening answer the question, without adding extra ideas or unnecessary words? Did the middle of my answer give details that support my opening sentence? Did I give one, two, or three details? Once I finished my answer did I say something that showed I was finished? Did I answer the question in a reasonable amount of time that lasted no more than 2 minutes? Finally, please give me a recommendation on how I could have presented my experience better. When you are critiquing me please refer to my resume information which you have on a piece of paper in front of you. The resume shows: I was most recently a {data_to_include.get('most_recent_job_title')}. I have experience in: {data_to_include.get('key_technical_skills')} and {data_to_include.get('key_soft_skills')}. Here is my full resume: {data_to_include.get('resume_text_full')}."),
        ("user", user_response),
        MessagesPlaceholder(variable_name="messages"),
    ])

    analysis_chain = analysis_prompt | model
    print("Sending analysis prompt to OpenAI API...")

    analysis_response = analysis_chain.invoke({"messages": [HumanMessage(content=user_response)]}).content

    # Prepare the score prompt with included data
    score_prompt = ChatPromptTemplate.from_messages([
        ("system", f"Score the answer I am sending you to the question 'tell me about your professional experience and how it relates to this role at {company_name}' from 0 to 10. It should be incredibly hard to score an 8, 9 or 10 unless you decide the answer was very good. When scoring, keep in mind that I was most recently a {data_to_include.get('most_recent_job_title')}. I have experience in: {data_to_include.get('key_soft_skills')} and {data_to_include.get('key_technical_skills')}."),
        ("user", user_response),
        MessagesPlaceholder(variable_name="messages"),
    ])

    score_chain = score_prompt | model
    print("Sending score prompt to OpenAI API...")

    score_response = score_chain.invoke({"messages": [HumanMessage(content=user_response)]})

    score = extract_score(score_response.content)

    # Handle cases where the score response is empty or does not contain a number
    if not score or not score.isdigit():
        score = None

    # Generate the next question with career context
    session_history = get_session_history(os.urandom(24).hex())
    next_question = generate_question_2(job_title, company_name, industry, session_history, session, combined_data, keys_to_include)

    # Update most_recent_question with the new question
    most_recent_question = next_question
    print("Updated most_recent_question in get_answer_1:", most_recent_question)

    # Store the response in the database
    new_answer = InterviewAnswer(
        session_id=session_id,  # Make sure to include session_id
        job_title=job_title,
        company_name=company_name,
        industry=industry,
        question="Tell me about your professional experience and how it relates to this role at {company_name}",  # Last question asked before the user's answer
        answer=user_response,
        critique=analysis_response,
        score=score if score else "N/A"  # Store "N/A" if score is None
    )
    session.add(new_answer)
    session.commit()

    print("get_answer_1 completed.")
    return {
        "analysis_response": analysis_response,
        "score": score if score else "N/A",
        "next_question": next_question
    }


def get_answer_2(session: Session, username: str, job_title: str, company_name: str, industry: str, user_response: str, file_summary: str, session_id: str, training_data: dict, keys_to_include: list):
    global most_recent_question, user_responses
    print("Starting get_answer_2")

    resume_data = get_user_resume_data(session, username)
    if not resume_data:
        return {"response": "No resume data found for user.", "score": "N/A", "next_question": "N/A"}

    # Convert the resume_data tuple to a dictionary using keys
    resume_keys = [
        "resume_text_full", "key_technical_skills", "key_soft_skills", "most_recent_job_title", 
        "second_most_recent_job_title", "most_recent_job_title_summary", "second_most_recent_job_title_summary", 
        "top_listed_skill_keyword", "second_most_top_listed_skill_keyword", "third_most_top_listed_skill_keyword", 
        "fourth_most_top_listed_skill_keyword", "educational_background", "certifications_and_awards", 
        "most_recent_successful_project", "areas_for_improvement", "questions_about_experience", 
        "resume_length", "top_challenge"
    ]
    resume_data_dict = dict(zip(resume_keys, resume_data))

    # Combine resume_data_dict and training_data
    combined_data = {**resume_data_dict, **training_data}

    # Extract relevant data based on keys_to_include
    data_to_include = {key: combined_data.get(key, "") for key in keys_to_include}

    # Prepare the analysis prompt with included data
    analysis_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are helping me land a new job by conducting realistic interviews with me. I'm interviewing to be a {job_title} at {company_name} company in the {industry} industry. You just asked me the question: {most_recent_question}. I am going to answer you and I want you to give me a very critical critique of how well I answered the question. Specifically, check that my answer followed these best practices: Is there an opening, middle and closing? Did my opening answer the question, without adding extra ideas or unnecessary words? Did the middle of my answer give details that support my opening sentence? Did I give one, two, or three details? Did I follow the STAR format (situation, task, action, result)? Did I keep my answer under 3 minutes long? Once I finished my answer did I say something that showed I was finished? For more context: I was most recently a {data_to_include.get('most_recent_job_title')}. I have experience in: {data_to_include.get('key_technical_skills')} and {data_to_include.get('key_soft_skills')}. Here is more context about the company {company_name} I'm interviewing to work at: {file_summary}."),
        ("user", user_response),
        MessagesPlaceholder(variable_name="messages"),
    ])

    analysis_chain = analysis_prompt | model
    print("Sending analysis prompt to OpenAI API...")

    analysis_response = analysis_chain.invoke({"messages": [HumanMessage(content=user_response)]}).content

    # Prepare the score prompt with included data
    score_prompt = ChatPromptTemplate.from_messages([
        ("system", f"Score the answer I am sending you to the question {most_recent_question} from 0 to 10. It should be incredibly hard to score an 8, 9 or 10 unless you decide the answer was very good. Keep in mind I was most recently a {data_to_include.get('most_recent_job_title')}. I have experience in: {data_to_include.get('key_soft_skills')} and {data_to_include.get('key_technical_skills')}."),
        ("user", user_response),
        MessagesPlaceholder(variable_name="messages"),
    ])

    score_chain = score_prompt | model
    print("Sending score prompt to OpenAI API...")

    score_response = score_chain.invoke({"messages": [HumanMessage(content=user_response)]})

    score = extract_score(score_response.content)

    # Handle cases where the score response is empty or does not contain a number
    if not score or not score.isdigit():
        score = None

    # Generate the next question with career context
    session_history = get_session_history(os.urandom(24).hex())
    next_question = generate_question_3(job_title, company_name, industry, session_history, session, combined_data, keys_to_include)

    # Update most_recent_question with the new question
    most_recent_question = next_question

    # Store the career user response
    user_responses["career_user_responses"].append(user_response)
    print("Career User Response:", user_response)
    print("Most Recent Question:", most_recent_question)

    # Store the response in the database
    new_answer = InterviewAnswer(
        session_id=session_id,  # Make sure to include session_id
        job_title=job_title,
        company_name=company_name,
        industry=industry,
        question=most_recent_question,  # Last question asked before the user's answer
        answer=user_response,
        critique=analysis_response,
        score=score if score else "N/A"  # Store "N/A" if score is None
    )
    session.add(new_answer)
    session.commit()

    print("get_answer_2 completed.")
    return {
        "analysis_response": analysis_response,
        "score": score if score else "N/A",
        "next_question": next_question
    }


def get_answer_3(session, username, job_title, company_name, industry, user_response, file_summary: str, session_id, training_data: dict, keys_to_include: list):
    global most_recent_question, user_responses
    print("Starting get_answer_3")

    resume_data = get_user_resume_data(session, username)
    if not resume_data:
        return {"response": "No resume data found for user.", "score": "N/A", "next_question": "N/A"}

    # Convert the resume_data tuple to a dictionary using keys
    resume_keys = [
        "resume_text_full", "key_technical_skills", "key_soft_skills", "most_recent_job_title", 
        "second_most_recent_job_title", "most_recent_job_title_summary", "second_most_recent_job_title_summary", 
        "top_listed_skill_keyword", "second_most_top_listed_skill_keyword", "third_most_top_listed_skill_keyword", 
        "fourth_most_top_listed_skill_keyword", "educational_background", "certifications_and_awards", 
        "most_recent_successful_project", "areas_for_improvement", "questions_about_experience", 
        "resume_length", "top_challenge"
    ]
    resume_data_dict = dict(zip(resume_keys, resume_data))

    # Combine resume_data_dict and training_data
    combined_data = {**resume_data_dict, **training_data}

    # Extract relevant data based on keys_to_include
    data_to_include = {key: combined_data.get(key, "") for key in keys_to_include}

    # Prompt 1: Analyze the user's answer
    analysis_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are helping me land a new job by conducting realistic interviews with me. I'm interviewing to be a {job_title} at {company_name} company in the {industry} industry. You just asked me the question: {most_recent_question}. I am going to answer you and I want you to give me a very critical critique of how well I answered the question. Specifically, check that my answer followed these best practices: Is there an opening, middle and closing? Did my opening answer the question, without adding extra ideas or unnecessary words? Did the middle of my answer give details that support my opening sentence? Did I give one, two, or three details? Did I follow the STAR format (situation, task, action, result)? Did I keep my answer under 3 minutes long? Once I finished my answer did I say something that showed I was finished? Did I keep my answer under 3 minutes long? For more context: I was most recently a {data_to_include.get('most_recent_job_title')}. I have experience in: {data_to_include.get('key_technical_skills')} and {data_to_include.get('key_soft_skills')}. Here is more context about the company {company_name} I'm interviewing to work at: {file_summary}."),
        ("user", user_response),
        MessagesPlaceholder(variable_name="messages"),
    ])

    analysis_chain = analysis_prompt | model
    print("Sending analysis prompt to OpenAI API...")

    analysis_response = analysis_chain.invoke({"messages": [HumanMessage(content=user_response)]}).content

    # Prepare the score prompt with included data
    score_prompt = ChatPromptTemplate.from_messages([
        ("system", f"Score the answer I am sending you to the question {most_recent_question} from 0 to 10. It should be incredibly hard to score an 8, 9 or 10 unless you decide the answer was very good. Keep in mind I was most recently a {data_to_include.get('most_recent_job_title')}. I have experience in: {data_to_include.get('key_technical_skills')} and {data_to_include.get('key_soft_skills')}."),
        ("user", user_response),
        MessagesPlaceholder(variable_name="messages"),
    ])

    score_chain = score_prompt | model
    print("Sending score prompt to OpenAI API...")

    score_response = score_chain.invoke({"messages": [HumanMessage(content=user_response)]})

    score = extract_score(score_response.content)

    # Handle cases where the score response is empty or does not contain a number
    if not score or not score.isdigit():
        score = None

    # Generate the next question with career context
    session_history = get_session_history(os.urandom(24).hex())
    next_question = generate_question_4(job_title, company_name, industry, session_history, session, combined_data, keys_to_include)

    # Update most_recent_question with the new question
    most_recent_question = next_question

    # Store the career user response
    user_responses["career_user_responses"].append(user_response)
    print("Career User Response:", user_response)
    print("Most Recent Question:", most_recent_question)

    # Store the response in the database
    new_answer = InterviewAnswer(
        session_id=session_id,  # Make sure to include session_id
        job_title=job_title,
        company_name=company_name,
        industry=industry,
        question=most_recent_question,  # Last question asked before the user's answer
        answer=user_response,
        critique=analysis_response,
        score=score if score else "N/A"  # Store "N/A" if score is None
    )
    session.add(new_answer)
    session.commit()

    print("get_answer_3 completed.")
    return {
        "analysis_response": analysis_response,
        "score": score if score else "N/A",
        "next_question": next_question
    }

def get_answer_4(session, username, job_title, company_name, industry, user_response, file_summary: str, session_id, training_data: dict, keys_to_include: list):
    global most_recent_question, user_responses
    print("Starting get_answer_4")

    resume_data = get_user_resume_data(session, username)
    if not resume_data:
        return {"response": "No resume data found for user.", "score": "N/A", "next_question": "N/A"}

    # Convert the resume_data tuple to a dictionary using keys
    resume_keys = [
        "resume_text_full", "key_technical_skills", "key_soft_skills", "most_recent_job_title",
        "second_most_recent_job_title", "most_recent_job_title_summary", "second_most_recent_job_title_summary",
        "top_listed_skill_keyword", "second_most_top_listed_skill_keyword", "third_most_top_listed_skill_keyword",
        "fourth_most_top_listed_skill_keyword", "educational_background", "certifications_and_awards",
        "most_recent_successful_project", "areas_for_improvement", "questions_about_experience",
        "resume_length", "top_challenge"
    ]
    resume_data_dict = dict(zip(resume_keys, resume_data))

    # Combine resume_data_dict and training_data
    combined_data = {**resume_data_dict, **training_data}

    # Extract relevant data based on keys_to_include
    data_to_include = {key: combined_data.get(key, "") for key in keys_to_include}

    # Prompt 1: Analyze the user's answer
    analysis_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are helping me land a new job by conducting realistic interviews with me. I'm interviewing to be a {job_title} at {company_name} company in the {industry} industry. You just asked me the question: {most_recent_question}. I am going to answer you and I want you to give me a very critical critique of how well I answered the question. Specifically, check that my answer followed these best practices: Is there an opening, middle and closing? Did my opening answer the question, without adding extra ideas or unnecessary words? Did the middle of my answer give details that support my opening sentence? Did I give one, two, or three details? Did I follow the STAR format (situation, task, action, result)? Did I keep my answer under 3 minutes long? Once I finished my answer did I say something that showed I was finished? Did I keep my answer under 3 minutes long? For more context: I was most recently a {data_to_include.get('most_recent_job_title')}. I have experience in: {data_to_include.get('key_technical_skills')} and {data_to_include.get('key_soft_skills')}. Here is more context about the company {company_name} I'm interviewing to work at: {file_summary}."),
        ("user", user_response),
        MessagesPlaceholder(variable_name="messages"),
    ])

    analysis_chain = analysis_prompt | model
    print("Sending analysis prompt to OpenAI API...")

    analysis_response = analysis_chain.invoke({"messages": [HumanMessage(content=user_response)]}).content

    # Prepare the score prompt with included data
    score_prompt = ChatPromptTemplate.from_messages([
        ("system", f"Score the answer I am sending you to the question {most_recent_question} from 0 to 10. It should be incredibly hard to score an 8, 9 or 10 unless you decide the answer was very good. Keep in mind I was most recently a {data_to_include.get('most_recent_job_title')}. I have experience in: {data_to_include.get('key_technical_skills')} and {data_to_include.get('key_soft_skills')}."),
        ("user", user_response),
        MessagesPlaceholder(variable_name="messages"),
    ])

    score_chain = score_prompt | model
    print("Sending score prompt to OpenAI API...")

    score_response = score_chain.invoke({"messages": [HumanMessage(content=user_response)]})

    score = extract_score(score_response.content)

    # Handle cases where the score response is empty or does not contain a number
    if not score or not score.isdigit():
        score = None

    # Generate the next question with career context
    session_history = get_session_history(os.urandom(24).hex())
    next_question = generate_question_5(job_title, company_name, industry, session_history, session, combined_data, keys_to_include)

    # Update most_recent_question with the new question
    most_recent_question = next_question

    # Store the career user response
    user_responses["career_user_responses"].append(user_response)
    print("Career User Response:", user_response)
    print("Most Recent Question:", most_recent_question)

    # Store the response in the database
    new_answer = InterviewAnswer(
        session_id=session_id,  # Make sure to include session_id
        job_title=job_title,
        company_name=company_name,
        industry=industry,
        question=most_recent_question,  # Last question asked before the user's answer
        answer=user_response,
        critique=analysis_response,
        score=score if score else "N/A"  # Store "N/A" if score is None
    )
    session.add(new_answer)
    session.commit()

    print("get_answer_4 completed.")
    return {
        "analysis_response": analysis_response,
        "score": score if score else "N/A",
        "next_question": next_question
    }

def get_infinite_answers(session, username, job_title, company_name, industry, user_response, file_summary: str, session_id, training_data: dict, keys_to_include: list):
    global most_recent_question, user_responses, interview_answers_question_history
    print("Starting get_infinite_answers")

    resume_data = get_user_resume_data(session, username)
    if not resume_data:
        return {"response": "No resume data found for user.", "score": "N/A", "next_question": "N/A"}

    # Convert the resume_data tuple to a dictionary using keys
    resume_keys = [
        "resume_text_full", "key_technical_skills", "key_soft_skills", "most_recent_job_title",
        "second_most_recent_job_title", "most_recent_job_title_summary", "second_most_recent_job_title_summary",
        "top_listed_skill_keyword", "second_most_top_listed_skill_keyword", "third_most_top_listed_skill_keyword",
        "fourth_most_top_listed_skill_keyword", "educational_background", "certifications_and_awards",
        "most_recent_successful_project", "areas_for_improvement", "questions_about_experience",
        "resume_length", "top_challenge"
    ]
    resume_data_dict = dict(zip(resume_keys, resume_data))

    # Combine resume_data_dict and training_data
    combined_data = {**resume_data_dict, **training_data}

    # Extract relevant data based on keys_to_include
    data_to_include = {key: combined_data.get(key, "") for key in keys_to_include}

    # Prompt 1: Analyze the user's answer
    analysis_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are helping me land a new job by conducting realistic interviews with me. I'm interviewing to be a {job_title} at {company_name} company in the {industry} industry. You just asked me the question: {most_recent_question}. I am going to answer you and I want you to give me a very critical critique of how well I answered the question. Specifically, check that my answer followed these best practices: Is there an opening, middle and closing? Did my opening answer the question, without adding extra ideas or unnecessary words? Did the middle of my answer give details that support my opening sentence? Did I give one, two, or three details? Did I follow the STAR format (situation, task, action, result)? Did I keep my answer under 3 minutes long? Once I finished my answer did I say something that showed I was finished? Did I keep my answer under 3 minutes long? For more context: I was most recently a {data_to_include.get('most_recent_job_title')}. I have experience in: {data_to_include.get('key_technical_skills')} and {data_to_include.get('key_soft_skills')}. Here is more context about the company {company_name} I'm interviewing to work at: {file_summary}."),
        ("user", user_response),
        MessagesPlaceholder(variable_name="messages"),
    ])

    analysis_chain = analysis_prompt | model
    print("Sending analysis prompt to OpenAI API...")

    analysis_response = analysis_chain.invoke({"messages": [HumanMessage(content=user_response)]}).content

    # Prepare the score prompt with included data
    score_prompt = ChatPromptTemplate.from_messages([
        ("system", f"Score the answer I am sending you to the question {most_recent_question} from 0 to 10. It should be incredibly hard to score an 8, 9 or 10 unless you decide the answer was very good. Keep in mind I was most recently a {data_to_include.get('most_recent_job_title')}. I have experience in: {data_to_include.get('key_technical_skills')} and {data_to_include.get('key_soft_skills')}."),
        ("user", user_response),
        MessagesPlaceholder(variable_name="messages"),
    ])

    score_chain = score_prompt | model
    print("Sending score prompt to OpenAI API...")

    score_response = score_chain.invoke({"messages": [HumanMessage(content=user_response)]})

    score = extract_score(score_response.content)

    # Handle cases where the score response is empty or does not contain a number
    if not score or not score.isdigit():
        score = None

    # Generate the next question with career context
    session_history = get_session_history(os.urandom(24).hex())
    next_question = generate_infinite_questions(job_title, company_name, industry, session_history, session, combined_data, keys_to_include)

    # Update most_recent_question with the new question
    most_recent_question = next_question

    # Store the career user response
    user_responses["career_user_responses"].append(user_response)
    print("Career User Response:", user_response)
    print("Most Recent Question:", most_recent_question)

    # Store the response in the database
    new_answer = InterviewAnswer(
        session_id=session_id,  # Make sure to include session_id
        job_title=job_title,
        company_name=company_name,
        industry=industry,
        question=most_recent_question,  # Last question asked before the user's answer
        answer=user_response,
        critique=analysis_response,
        score=score if score else "N/A"  # Store "N/A" if score is None
    )
    session.add(new_answer)
    session.commit()

    print("get_infinite_answers completed.")
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

