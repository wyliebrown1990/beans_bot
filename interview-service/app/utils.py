import os
import uuid
from io import BytesIO
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import ProgrammingError
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from openai import OpenAI
from datetime import datetime
from flask_login import UserMixin
import faiss
import numpy as np
import re
import logging
from dotenv import load_dotenv
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

# Import models from app package
from app.models import TrainingData, FaissIndex, InterviewAnswer, User

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

def text_to_speech_file(text: str, voice_id: str) -> str:
    # Handle empty text case
    if not text.strip():
        print("Text is empty, skipping text-to-speech conversion.")
        return ""

    try:
        # Calling the text_to_speech conversion API with detailed parameters
        response = elevenlabs_client.text_to_speech.convert(
            voice_id=voice_id,
            optimize_streaming_latency="0",
            output_format="mp3_22050_32",
            text=text,
            model_id="eleven_turbo_v2",  # use the turbo model for low latency, for other languages use the `eleven_multilingual_v2`
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

def create_table_if_not_exists(engine):
    try:
        TrainingData.__table__.create(engine, checkfirst=True)
        FaissIndex.__table__.create(engine, checkfirst=True)
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
    training_data = session.query(TrainingData).filter(
        func.lower(TrainingData.job_title) == job_title.lower(),
        func.lower(TrainingData.company_name) == company_name.lower()
    ).first()
    if training_data:
        logging.debug(f"Found training data: {training_data}")
    else:
        logging.debug("No training data found")
    return training_data


def generate_next_question(job_title, company_name, industry, session_history, session):
    global most_recent_question

    # Query FAISS index for company information
    company_info = query_faiss_index(f"What does {company_name} do and what are their main product features?", session)
    print(f"Retrieved company information: {company_info}")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are the world’s best interview coach. I have hired you to conduct a mock interview with me. You should ask me a new question you haven’t already asked. The question should challenge my ability to work as a {job_title} at {company_name} company in the {industry} industry. Here is more context about {company_name}: {company_info}."),
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

def query_faiss_index(query: str, session: Session) -> str:
    # Load FAISS index from the database
    faiss_index_record = session.query(FaissIndex).first()
    if not faiss_index_record:
        logging.error("FAISS index not found in the database.")
        return "Error querying FAISS index: Index not found in database."

    try:
        # Deserialize the FAISS index
        index = faiss.deserialize_index(faiss_index_record.index_data)
        
        # Create an embedding for the query
        query_embedding = embedder.embed_documents([query])[0]
        query_vector = np.array(query_embedding, dtype=np.float32)

        # Search the FAISS index
        D, I = index.search(query_vector.reshape(1, -1), 5)
        print(f"Query embedding shape: {query_vector.shape}")
        print(f"Search results - Distances: {D}, Indices: {I}")

        # Retrieve the matched data
        matched_data = []
        for idx in I[0]:
            if idx != -1:
                training_data = session.query(TrainingData).filter_by(id=idx).first()
                if training_data:
                    # Convert embedding from bytes to numpy array if needed
                    embedding_array = np.frombuffer(training_data.embeddings, dtype=np.float32)
                    matched_data.append(training_data.data)
                    print(f"Retrieved data for index {idx}: {training_data.data[:100]}...")  # Log first 100 characters of data
                else:
                    logging.error(f"No training data found for index {idx}")
        
        return f"Retrieved information for query '{query}' from FAISS index: {matched_data}"
    except Exception as e:
        logging.error(f"Error querying FAISS index: {e}")
        return "Error querying FAISS index."



def fetch_data_from_storage(index_id: int) -> str:
    # Replace this function with actual implementation to fetch data
    # For example, querying a database or reading from a file
    return "Mock data for index ID: {}".format(index_id)

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
    next_question = generate_next_question(job_title, company_name, industry, session_history, session)


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


def get_career_experience_answer(session: Session, username: str, job_title: str, company_name: str, industry: str, career_user_response: str):
    global most_recent_question, user_responses

    # Fetch company context from FAISS index
    company_info = query_faiss_index(f"What does {company_name} do and what are their main product features?", session)

    resume_data = get_user_resume_data(session, username)
    if not resume_data:
        return {"response": "No resume data found for user.", "score": "N/A", "next_question": "N/A"}

    (resume_text_full, top_technical_skills, most_recent_job_title, most_recent_company_name,
     most_recent_experience_summary, industry_expertise, top_soft_skills) = resume_data

    # Prompt 1: Analyze the user's answer
    analysis_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are helping me land a new job by conducting a mock interview with me. I’m interviewing to be a {job_title} at {company_name} company in the {industry} industry. You just asked me the question: {most_recent_question}. Give me a very critical critique of how well I answered the question. Specifically check that my answer followed these best practices: Is there an opening, middle and closing? Did my opening answer the question, without adding extra ideas or unnecessary words? Did the middle of my answer give details that support my opening sentence? Did I give one, two, or three details? Did I follow the STAR format (situation, task, action, result)? Once I finished my answer did I say something that showed I was finished? For more context: I was most recently a {most_recent_job_title} at {most_recent_company_name} company. I have experience in: {most_recent_experience_summary}. Here is more context about the company {company_name} I’m interviewing to work at: {company_info}. Based on my experience and the context about {company_name} and my specific answer please give me feedback."),
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
    next_question = generate_next_question(job_title, company_name, industry, session_history, session)

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
