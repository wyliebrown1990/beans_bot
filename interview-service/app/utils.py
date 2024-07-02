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
from app.models import JobDescriptionAnalysis, User, InterviewHistory, Questions

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# Set up logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure ffmpeg is found
ffmpeg_location = os.getenv('FFMPEG_LOCATION')
AudioSegment.converter = which("ffmpeg") or ffmpeg_location

# Initialize the OpenAI chat model
openai_api_key = os.getenv("OPENAI_API_KEY")
model = ChatOpenAI(model="gpt-3.5-turbo", api_key=openai_api_key, temperature=0.5)

# Initialize database session
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = SessionLocal()

# Define the global variables
most_recent_answer = None
most_recent_row = None
used_questions_table_ids = []

#Cleans up values from questions table:
def capitalize_sentences(text):
    return '. '.join(sentence.capitalize() for sentence in text.split('. '))


#Start of generating unique IDs:

def generate_session_id():
    return random.randint(100000, 999999)

def ensure_unique_session_id(user_id):
    while True:
        session_id = generate_session_id()
        existing_session = db_session.query(InterviewHistory).filter_by(user_id=user_id, session_id=session_id).first()
        if not existing_session:
            return session_id

#Start of interview_history storing functions:
        
def store_question(question, user_id, session_id, is_initial=False):
   user = db_session.query(User).filter_by(id=user_id).first()
   job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()

   if not user or not job_description:
       raise ValueError("User or job description not found")

   new_interview_history = InterviewHistory(
       id=random.randint(1, 2147483647),
       session_id=session_id,
       user_id=user_id,
       created_at=datetime.utcnow(),
       updated_at=datetime.utcnow(),
       job_title=job_description.job_title,
       company_name=job_description.company_name,
       company_industry=job_description.company_industry,
       question=question,
       question_id=0,
       answer=None,
       feedback=None,
       score=None,
       skip_next_time=False,
       session_score_average=None,
       session_top_score=None,
       session_low_score=None,
       session_summary_next_steps=None
   )

   db_session.add(new_interview_history)
   db_session.commit()
   print("Question stored:", question)

def store_feedback(feedback, user_id, session_id):
    try:
        # Query for the row with the matching session_id and user_id that has no feedback value
        interview_history = db_session.query(InterviewHistory).filter_by(user_id=user_id, session_id=session_id).filter(InterviewHistory.feedback == None).order_by(InterviewHistory.created_at.asc()).first()
        
        if interview_history:
            interview_history.feedback = feedback
            interview_history.updated_at = datetime.utcnow()
            db_session.commit()
            print("Feedback stored:", feedback)
        else:
            print("No matching interview history found to store feedback.")
    except Exception as e:
        print(f"Error storing feedback: {e}")

def store_user_answer(answer, user_id, session_id):
    global most_recent_answer, most_recent_row
    try:
        # Query for the row with the matching session_id and user_id that has no answer value
        interview_history = db_session.query(InterviewHistory).filter_by(user_id=user_id, session_id=session_id).filter(InterviewHistory.answer == None).order_by(InterviewHistory.created_at.asc()).first()
        
        if interview_history:
            interview_history.answer = answer
            interview_history.updated_at = datetime.utcnow()
            db_session.commit()
            most_recent_answer = answer  # Update the global variable for the most recent answer
            most_recent_row = interview_history.id  # Update the global variable for the most recent row ID
            print(f"User answer stored in row ID: {most_recent_row}, Answer: {answer}")
        else:
            raise ValueError("No matching interview history found to store answer or answer already exists.")
    except Exception as e:
        print(f"Error storing user answer: {e}")

def store_score(row_id, score):
    try:
        # Check if interview history exists
        interview_history = db_session.query(InterviewHistory).filter_by(id=row_id).first()
        if not interview_history:
            raise ValueError(f"No matching interview history found to store score for row ID: {row_id}")

        # Check if score already exists
        if interview_history.score is not None:
            raise ValueError(f"Score already exists for row ID: {row_id}")

        # Store the score
        interview_history.score = score
        db_session.commit()
        print(f"Stored score: {score} for row ID: {row_id}")
    except Exception as e:
        print(f"Error storing score: {e}")


#Start of Scoring function: 
def get_score(user_id, session_id):
    global most_recent_answer
    try:
        print("Starting get_score function...")

        user = db_session.query(User).filter_by(id=user_id).first()
        job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()

        if not user or not job_description:
            raise ValueError("User or job description not found")

        print("User and Job Description found.")

        # Ensure that we have the most recent answer from the global variable
        user_response = most_recent_answer
        if not user_response:
            raise ValueError("No answers stored in the global variable")

        score_prompt = ChatPromptTemplate.from_messages([
            ("system", f"Score the answer I am sending you to the question 'tell me about your professional experience and how it relates to this role at {job_description.company_name}' from 0 to 10. "
                       f"It should be incredibly hard to score an 8, 9, or 10 unless you decide the answer was very good. When scoring, keep in mind that I was most recently a {user.most_recent_job_title}. "
                       f"I have experience in: {user.key_soft_skills} and {user.key_technical_skills}. "
                       "Don't return any text in your response. Only return a single integer for the score ranging between 1-10. For example your response should be: 1 or 2 or 3 or 4 or 5 or 6 or 7 or 8 or 9 or 10."),
            ("user", user_response),
            MessagesPlaceholder(variable_name="messages"),
        ])

        score_chain = score_prompt | model
        print("Sending score prompt to OpenAI API...")

        score_response = score_chain.invoke({"messages": [HumanMessage(content=user_response)]})

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

        store_score(most_recent_row, score)
        return score
    except Exception as e:
        print(f"Error in get_score function: {e}")
        return None



#Start of Feedback functions: 

def get_intro_question_feedback(user_id, session_id):
    try:
        global most_recent_answer
        user = db_session.query(User).filter_by(id=user_id).first()
        job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()

        if not user or not job_description:
            raise ValueError("User or job description not found")

        job_title = job_description.job_title
        company_name = job_description.company_name
        industry = job_description.company_industry

        interview_history = db_session.query(InterviewHistory).filter_by(user_id=user_id, session_id=session_id).order_by(InterviewHistory.created_at.desc()).first()
        if not interview_history or not interview_history.answer:
            raise ValueError("No answers stored")

        most_recent_answer = interview_history.answer

        # Generate the next question first
        next_question = get_resume_question_1(user_id, session_id)

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

        feedback_response = analysis_chain.invoke({"messages": [HumanMessage(content=most_recent_answer)]})

        feedback = feedback_response.content if feedback_response.content else "No feedback found"
        store_feedback(feedback, user_id, session_id)

        # Generate and store the score after the feedback
        score = get_score(user_id, session_id)
        store_score(most_recent_row, score)  # Update to use most_recent_row
        return {"next_question_response": next_question, "feedback": feedback, "score": score}
    except Exception as e:
        print(f"Error in get_intro_question_feedback function: {e}")
        return {"error": "Could not generate feedback."}

    
def get_resume_question_1_feedback(user_id, session_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()

        if not user or not job_description:
            raise ValueError("User or job description not found")

        job_title = job_description.job_title
        company_name = job_description.company_name
        industry = job_description.company_industry

        # Get the most recent answer
        interview_history = db_session.query(InterviewHistory).filter_by(user_id=user_id, session_id=session_id).order_by(InterviewHistory.created_at.desc()).first()
        if not interview_history or not interview_history.answer:
            raise ValueError("No answers stored")

        most_recent_answer = interview_history.answer

        # Get the most recent question
        most_recent_question = interview_history.question

        # Generate the next question first
        next_question = get_resume_question_2(user_id, session_id)

        feedback_prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are helping me land a new job by conducting realistic job interviews with me. "
                       f"I’m interviewing to be a {job_title} at {company_name} company in the {industry} industry. "
                       f"You just asked me the question: {most_recent_question}. "
                       "I am going to answer you and I want you to give me a very critical critique of how well I answered the question. "
                       "Specifically, check that my answer followed these best practices: Did I give a relevant example of a time I used the technical skill in your question? Did the example follow the STAR (Situation, Task, Action, and Result) format? "
                       "Did I answer the question in a reasonable amount of time that lasted no more than 3 minutes? "
                       "Finally, please give me a recommendation on how I could have presented my experience better. "
                       f"When you are critiquing me please refer to my resume information which you have on a piece of paper in front of you. "
                       f"The resume shows: I was most recently a {user.most_recent_job_title} "
                       f"I have experience in: {user.most_recent_job_title_summary} and {user.second_most_recent_job_title_summary}."),
            ("user", most_recent_answer),
            MessagesPlaceholder(variable_name="messages"),
        ])

        analysis_chain = feedback_prompt | model

        feedback_response = analysis_chain.invoke({"messages": [HumanMessage(content=most_recent_answer)]})

        feedback = feedback_response.content if feedback_response.content else "No feedback found"
        print(f"Generated feedback: {feedback}")

        # Store the feedback
        store_feedback(feedback, user_id, session_id)

        # Generate and store the score after the feedback
        score = get_score(user_id, session_id)
        if score is not None:
            print(f"Calling store_score with score: {score}")
            store_score(interview_history.id, score)
        else:
            print("Score was not generated, store_score will not be called.")

        return {"next_question_response": next_question, "feedback": feedback, "score": score}
    except Exception as e:
        print(f"Error in get_resume_question_1_feedback function: {e}")
        return {"error": "Could not generate feedback."}



def get_resume_question_2_feedback(user_id, session_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()

        if not user or not job_description:
            raise ValueError("User or job description not found")

        job_title = job_description.job_title
        company_name = job_description.company_name
        industry = job_description.company_industry

        # Get the most recent answer
        interview_history = db_session.query(InterviewHistory).filter_by(user_id=user_id, session_id=session_id).order_by(InterviewHistory.created_at.desc()).first()
        if not interview_history or not interview_history.answer:
            raise ValueError("No answers stored")

        most_recent_answer = interview_history.answer

        # Get the most recent question
        most_recent_question = interview_history.question

        # Generate the next question first
        next_question = get_resume_question_3(user_id, session_id)

        feedback_prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are helping me land a new job by conducting realistic job interviews with me. "
                       f"I’m interviewing to be a {job_title} at {company_name} company in the {industry} industry. "
                       f"You just asked me the question: {most_recent_question}. "
                       "I am going to answer you and I want you to give me a very critical critique of how well I answered the question. "
                       "Specifically, check that my answer followed these best practices: Did I give a relevant example of a time I used the technical skill in your question? Did the example follow the STAR (Situation, Task, Action, and Result) format? "
                       "Did I answer the question in a reasonable amount of time that lasted no more than 3 minutes? "
                       "Finally, please give me a recommendation on how I could have presented my experience better. "
                       f"When you are critiquing me please refer to my resume information which you have on a piece of paper in front of you. "
                       f"The resume shows: I was most recently a {user.most_recent_job_title} "
                       f"I have experience in: {user.most_recent_job_title_summary} and {user.second_most_recent_job_title_summary}."),
            ("user", most_recent_answer),
            MessagesPlaceholder(variable_name="messages"),
        ])

        analysis_chain = feedback_prompt | model

        feedback_response = analysis_chain.invoke({"messages": [HumanMessage(content=most_recent_answer)]})

        feedback = feedback_response.content if feedback_response.content else "No feedback found"
        logger.info(f"Generated feedback: {feedback}")

        # Store the feedback
        store_feedback(feedback, user_id, session_id)

        # Generate and store the score after the feedback
        score = get_score(user_id, session_id)
        if score is not None:
            logger.info(f"Calling store_score with score: {score}")
            store_score(interview_history.id, score)
        else:
            logger.info("Score was not generated, store_score will not be called.")

        return {"next_question_response": next_question, "feedback": feedback, "score": score}
    except Exception as e:
        logger.error(f"Error in get_resume_question_2_feedback function: {e}")
        return {"error": "Could not generate feedback."}

    
def get_resume_question_3_feedback(user_id, session_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()

        if not user or not job_description:
            raise ValueError("User or job description not found")

        job_title = job_description.job_title
        company_name = job_description.company_name
        industry = job_description.company_industry

        # Get the most recent answer
        interview_history = db_session.query(InterviewHistory).filter_by(user_id=user_id, session_id=session_id).order_by(InterviewHistory.created_at.desc()).first()
        if not interview_history or not interview_history.answer:
            raise ValueError("No answers stored")

        most_recent_answer = interview_history.answer
        most_recent_successful_project = user.most_recent_successful_project
        job_responsibilities = job_description.job_responsibilities
        required_professional_experiences = job_description.required_professional_experiences

        # Generate the next question first
        next_question = get_resume_question_4(user_id, session_id)

        feedback_prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are helping me land a new job by conducting realistic job interviews with me. "
                       f"I’m interviewing to be a {job_title} at {company_name} company in the {industry} industry. "
                       f"You just asked me the question: {interview_history.question}. "
                       "I am going to answer you and I want you to give me a very critical critique of how well I answered the question. "
                       "Specifically, check that my answer followed these best practices: Did I give a relevant example of a time I used the technical skill in your question? Did the example follow the STAR (Situation, Task, Action, and Result) format? "
                       "Did I answer the question in a reasonable amount of time that lasted no more than 3 minutes? "
                       "Finally, please give me a recommendation on how I could have presented my experience better. "
                       f"When you are critiquing me please refer to my resume information which you have on a piece of paper in front of you. "
                       f"The resume shows: I was most recently a {user.most_recent_job_title} "
                       f"I have experience in: {user.most_recent_job_title_summary} and {user.second_most_recent_job_title_summary}."),
            ("user", most_recent_answer),
            MessagesPlaceholder(variable_name="messages"),
        ])

        analysis_chain = feedback_prompt | model

        feedback_response = analysis_chain.invoke({"messages": [HumanMessage(content=most_recent_answer)]})

        feedback = feedback_response.content if feedback_response.content else "No feedback found"
        print(f"Generated feedback: {feedback}")

        # Store the feedback
        store_feedback(feedback, user_id, session_id)

        # Generate and store the score after the feedback
        score = get_score(user_id, session_id)
        if score is not None:
            print(f"Calling store_score with score: {score}")
            store_score(interview_history.id, score)
        else:
            print("Score was not generated, store_score will not be called.")

        return {"next_question_response": next_question, "feedback": feedback, "score": score}
    except Exception as e:
        print(f"Error in get_resume_question_3_feedback function: {e}")
        return {"error": "Could not generate feedback."}

def get_resume_question_4_feedback(user_id, session_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()

        if not user or not job_description:
            raise ValueError("User or job description not found")

        job_title = job_description.job_title
        company_name = job_description.company_name
        industry = job_description.company_industry

        # Get the most recent answer
        interview_history = db_session.query(InterviewHistory).filter_by(user_id=user_id, session_id=session_id).order_by(InterviewHistory.created_at.desc()).first()
        if not interview_history or not interview_history.answer:
            raise ValueError("No answers stored")

        most_recent_answer = interview_history.answer
        most_recent_question = interview_history.question
        most_recent_successful_project = user.most_recent_successful_project

        # Generate the next question first
        next_question = get_behavioral_question_1(user_id, session_id)

        feedback_prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are helping me land a new job by conducting realistic job interviews with me. "
                       f"I’m interviewing to be a {job_title} at {company_name} company in the {industry} industry. "
                       f"You just asked me the question: {most_recent_question}. "
                       "I am going to answer you and I want you to give me a very critical critique of how well I answered the question. "
                       "Specifically, check that my answer followed these best practices: Did I give a relevant example of a time I used the technical skill in your question? Did the example follow the STAR (Situation, Task, Action, and Result) format? "
                       "Did I answer the question in a reasonable amount of time that lasted no more than 3 minutes? "
                       "Finally, please give me a recommendation on how I could have presented my experience better. "
                       f"When you are critiquing me please refer to my resume information which you have on a piece of paper in front of you. "
                       f"The resume shows: I was most recently a {user.most_recent_job_title} "
                       f"I have experience in: {user.most_recent_job_title_summary} and {user.second_most_recent_job_title_summary}."),
            ("user", most_recent_answer),
            MessagesPlaceholder(variable_name="messages"),
        ])

        analysis_chain = feedback_prompt | model

        feedback_response = analysis_chain.invoke({"messages": [HumanMessage(content=most_recent_answer)]})

        feedback = feedback_response.content if feedback_response.content else "No feedback found"
        logger.info(f"Generated feedback: {feedback}")

        # Store the feedback
        store_feedback(feedback, user_id, session_id)

        # Generate and store the score after the feedback
        score = get_score(user_id, session_id)
        if score is not None:
            logger.info(f"Calling store_score with score: {score}")
            store_score(interview_history.id, score)
        else:
            logger.info("Score was not generated, store_score will not be called.")

        return {"next_question_response": next_question, "feedback": feedback, "score": score}
    except Exception as e:
        logger.error(f"Error in get_resume_question_4_feedback function: {e}")
        return {"error": "Could not generate feedback."}

    
def get_behavioral_question_1_feedback(user_id, session_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()
        
        if not user or not job_description:
            raise ValueError("User or job description not found")

        job_title = job_description.job_title
        company_name = job_description.company_name
        industry = job_description.company_industry

        # Get the most recent answer
        interview_history = db_session.query(InterviewHistory).filter_by(user_id=user_id, session_id=session_id).order_by(InterviewHistory.created_at.desc()).first()
        if not interview_history or not interview_history.answer:
            raise ValueError("No answers stored")

        most_recent_answer = interview_history.answer
        most_recent_question = interview_history.question

        # Get the most recent ID from the global variable
        if not used_questions_table_ids:
            raise ValueError("No used question IDs found")
        
        most_recent_question_id = used_questions_table_ids[-1]
        
        # Fetch the description of the question from the questions table
        question_row = db_session.query(Questions).filter_by(id=most_recent_question_id).first()
        if not question_row:
            raise ValueError("Question not found in questions table")

        question_description = question_row.description

        # Generate the next question first
        next_question = get_behavioral_question_2(user_id, session_id)

        feedback_prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are helping me land a new job by conducting realistic job interviews with me. "
                       f"I’m interviewing to be a {job_title} at {company_name} company in the {industry} industry. "
                       f"You just asked me the question: {most_recent_question}. "
                       "I am going to answer you and I want you to give me a very critical critique of how well I answered the question. "
                       f"As the interviewer, you asked me this question because: {question_description}. Did my answer accomplish this? "
                       "Did I answer the question in a reasonable amount of time that lasted no more than 3 minutes? "
                       "Finally, please give me a recommendation on how I could have presented my experience better."),
            ("user", most_recent_answer),
            MessagesPlaceholder(variable_name="messages"),
        ])

        analysis_chain = feedback_prompt | model

        feedback_response = analysis_chain.invoke({"messages": [HumanMessage(content=most_recent_answer)]})

        feedback = feedback_response.content if feedback_response.content else "No feedback found"
        logger.info(f"Generated feedback: {feedback}")

        # Store the feedback
        store_feedback(feedback, user_id, session_id)

        # Generate and store the score after the feedback
        score = get_score(user_id, session_id)
        if score is not None:
            logger.info(f"Calling store_score with score: {score}")
            store_score(interview_history.id, score)
        else:
            logger.info("Score was not generated, store_score will not be called.")

        return {"next_question_response": next_question, "feedback": feedback, "score": score}
    except Exception as e:
        logger.error(f"Error in get_behavioral_question_1_feedback function: {e}")
        return {"error": "Could not generate feedback."}
    
def get_behavioral_question_2_feedback(user_id, session_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()
        
        if not user or not job_description:
            raise ValueError("User or job description not found")

        job_title = job_description.job_title
        company_name = job_description.company_name
        industry = job_description.company_industry

        # Get the most recent answer
        interview_history = db_session.query(InterviewHistory).filter_by(user_id=user_id, session_id=session_id).order_by(InterviewHistory.created_at.desc()).first()
        if not interview_history or not interview_history.answer:
            raise ValueError("No answers stored")

        most_recent_answer = interview_history.answer
        most_recent_question = interview_history.question

        # Get the most recent ID from the global variable
        if not used_questions_table_ids:
            raise ValueError("No used question IDs found")
        
        most_recent_question_id = used_questions_table_ids[-1]
        
        # Fetch the description of the question from the questions table
        question_row = db_session.query(Questions).filter_by(id=most_recent_question_id).first()
        if not question_row:
            raise ValueError("Question not found in questions table")

        question_description = question_row.description

        # Generate the next question first
        next_question = get_situational_question_1(user_id, session_id)

        feedback_prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are helping me land a new job by conducting realistic job interviews with me. "
                       f"I’m interviewing to be a {job_title} at {company_name} company in the {industry} industry. "
                       f"You just asked me the question: {most_recent_question}. "
                       "I am going to answer you and I want you to give me a very critical critique of how well I answered the question. "
                       f"As the interviewer, you asked me this question because: {question_description}. Did my answer accomplish this? "
                       "Did I answer the question in a reasonable amount of time that lasted no more than 3 minutes? "
                       "Finally, please give me a recommendation on how I could have presented my experience better."),
            ("user", most_recent_answer),
            MessagesPlaceholder(variable_name="messages"),
        ])

        analysis_chain = feedback_prompt | model

        feedback_response = analysis_chain.invoke({"messages": [HumanMessage(content=most_recent_answer)]})

        feedback = feedback_response.content if feedback_response.content else "No feedback found"
        logger.info(f"Generated feedback: {feedback}")

        # Store the feedback
        store_feedback(feedback, user_id, session_id)

        # Generate and store the score after the feedback
        score = get_score(user_id, session_id)
        if score is not None:
            logger.info(f"Calling store_score with score: {score}")
            store_score(interview_history.id, score)
        else:
            logger.info("Score was not generated, store_score will not be called.")

        return {"next_question_response": next_question, "feedback": feedback, "score": score}
    except Exception as e:
        logger.error(f"Error in get_behavioral_question_2_feedback function: {e}")
        return {"error": "Could not generate feedback."}

def get_situational_question_1_feedback(user_id, session_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()
        
        if not user or not job_description:
            raise ValueError("User or job description not found")

        job_title = job_description.job_title
        company_name = job_description.company_name
        industry = job_description.company_industry

        # Get the most recent answer
        interview_history = db_session.query(InterviewHistory).filter_by(user_id=user_id, session_id=session_id).order_by(InterviewHistory.created_at.desc()).first()
        if not interview_history or not interview_history.answer:
            raise ValueError("No answers stored")

        most_recent_answer = interview_history.answer
        most_recent_question = interview_history.question

        # Get the most recent ID from the global variable
        if not used_questions_table_ids:
            raise ValueError("No used question IDs found")
        
        most_recent_question_id = used_questions_table_ids[-1]
        
        # Fetch the description of the question from the questions table
        question_row = db_session.query(Questions).filter_by(id=most_recent_question_id).first()
        if not question_row:
            raise ValueError("Question not found in questions table")

        question_description = question_row.description

        # Generate the next question first
        next_question = get_personality_question_1(user_id, session_id)

        feedback_prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are helping me land a new job by conducting realistic job interviews with me. "
                       f"I’m interviewing to be a {job_title} at {company_name} company in the {industry} industry. "
                       f"You just asked me the question: {most_recent_question}. "
                       "I am going to answer you and I want you to give me a very critical critique of how well I answered the question. "
                       f"As the interviewer, you asked me this question because: {question_description}. Did my answer accomplish this? "
                       "Did I answer the question in a reasonable amount of time that lasted no more than 3 minutes? "
                       "Finally, please give me a recommendation on how I could have presented my experience better."),
            ("user", most_recent_answer),
            MessagesPlaceholder(variable_name="messages"),
        ])

        analysis_chain = feedback_prompt | model

        feedback_response = analysis_chain.invoke({"messages": [HumanMessage(content=most_recent_answer)]})

        feedback = feedback_response.content if feedback_response.content else "No feedback found"
        logger.info(f"Generated feedback: {feedback}")

        # Store the feedback
        store_feedback(feedback, user_id, session_id)

        # Generate and store the score after the feedback
        score = get_score(user_id, session_id)
        if score is not None:
            logger.info(f"Calling store_score with score: {score}")
            store_score(interview_history.id, score)
        else:
            logger.info("Score was not generated, store_score will not be called.")

        return {"next_question_response": next_question, "feedback": feedback, "score": score}
    except Exception as e:
        logger.error(f"Error in get_situational_question_1_feedback function: {e}")
        return {"error": "Could not generate feedback."}

def get_personality_question_1_feedback(user_id, session_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()
        
        if not user or not job_description:
            raise ValueError("User or job description not found")

        job_title = job_description.job_title
        company_name = job_description.company_name
        industry = job_description.company_industry

        # Get the most recent answer
        interview_history = db_session.query(InterviewHistory).filter_by(user_id=user_id, session_id=session_id).order_by(InterviewHistory.created_at.desc()).first()
        if not interview_history or not interview_history.answer:
            raise ValueError("No answers stored")

        most_recent_answer = interview_history.answer
        most_recent_question = interview_history.question

        # Get the most recent ID from the global variable
        if not used_questions_table_ids:
            raise ValueError("No used question IDs found")
        
        most_recent_question_id = used_questions_table_ids[-1]
        
        # Fetch the description of the question from the questions table
        question_row = db_session.query(Questions).filter_by(id=most_recent_question_id).first()
        if not question_row:
            raise ValueError("Question not found in questions table")

        question_description = question_row.description

        # Generate the next question first
        next_question = get_motivational_question_1(user_id, session_id)

        feedback_prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are helping me land a new job by conducting realistic job interviews with me. "
                       f"I’m interviewing to be a {job_title} at {company_name} company in the {industry} industry. "
                       f"You just asked me the question: {most_recent_question}. "
                       "I am going to answer you and I want you to give me a very critical critique of how well I answered the question. "
                       f"As the interviewer, you asked me this question because: {question_description}. Did my answer accomplish this? "
                       "Did I answer the question in a reasonable amount of time that lasted no more than 3 minutes? "
                       "Finally, please give me a recommendation on how I could have presented my experience better."),
            ("user", most_recent_answer),
            MessagesPlaceholder(variable_name="messages"),
        ])

        analysis_chain = feedback_prompt | model

        feedback_response = analysis_chain.invoke({"messages": [HumanMessage(content=most_recent_answer)]})

        feedback = feedback_response.content if feedback_response.content else "No feedback found"
        logger.info(f"Generated feedback: {feedback}")

        # Store the feedback
        store_feedback(feedback, user_id, session_id)

        # Generate and store the score after the feedback
        score = get_score(user_id, session_id)
        if score is not None:
            logger.info(f"Calling store_score with score: {score}")
            store_score(interview_history.id, score)
        else:
            logger.info("Score was not generated, store_score will not be called.")

        return {"next_question_response": next_question, "feedback": feedback, "score": score}
    except Exception as e:
        logger.error(f"Error in get_personality_question_1_feedback function: {e}")
        return {"error": "Could not generate feedback."}

def get_motivational_question_1_feedback(user_id, session_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()
        
        if not user or not job_description:
            raise ValueError("User or job description not found")

        job_title = job_description.job_title
        company_name = job_description.company_name
        industry = job_description.company_industry

        # Get the most recent answer
        interview_history = db_session.query(InterviewHistory).filter_by(user_id=user_id, session_id=session_id).order_by(InterviewHistory.created_at.desc()).first()
        if not interview_history or not interview_history.answer:
            raise ValueError("No answers stored")

        most_recent_answer = interview_history.answer
        most_recent_question = interview_history.question

        # Get the most recent ID from the global variable
        if not used_questions_table_ids:
            raise ValueError("No used question IDs found")
        
        most_recent_question_id = used_questions_table_ids[-1]
        
        # Fetch the description of the question from the questions table
        question_row = db_session.query(Questions).filter_by(id=most_recent_question_id).first()
        if not question_row:
            raise ValueError("Question not found in questions table")

        question_description = question_row.description

        # Generate the next question first
        next_question = get_competency_question_1(user_id, session_id)

        feedback_prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are helping me land a new job by conducting realistic job interviews with me. "
                       f"I’m interviewing to be a {job_title} at {company_name} company in the {industry} industry. "
                       f"You just asked me the question: {most_recent_question}. "
                       "I am going to answer you and I want you to give me a very critical critique of how well I answered the question. "
                       f"As the interviewer, you asked me this question because: {question_description}. Did my answer accomplish this? "
                       "Did I answer the question in a reasonable amount of time that lasted no more than 3 minutes? "
                       "Finally, please give me a recommendation on how I could have presented my experience better."),
            ("user", most_recent_answer),
            MessagesPlaceholder(variable_name="messages"),
        ])

        analysis_chain = feedback_prompt | model

        feedback_response = analysis_chain.invoke({"messages": [HumanMessage(content=most_recent_answer)]})

        feedback = feedback_response.content if feedback_response.content else "No feedback found"
        logger.info(f"Generated feedback: {feedback}")

        # Store the feedback
        store_feedback(feedback, user_id, session_id)

        # Generate and store the score after the feedback
        score = get_score(user_id, session_id)
        if score is not None:
            logger.info(f"Calling store_score with score: {score}")
            store_score(interview_history.id, score)
        else:
            logger.info("Score was not generated, store_score will not be called.")

        return {"next_question_response": next_question, "feedback": feedback, "score": score}
    except Exception as e:
        logger.error(f"Error in get_motivational_question_1_feedback function: {e}")
        return {"error": "Could not generate feedback."}

def get_competency_question_1_feedback(user_id, session_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()
        
        if not user or not job_description:
            raise ValueError("User or job description not found")

        job_title = job_description.job_title
        company_name = job_description.company_name
        industry = job_description.company_industry

        # Get the most recent answer
        interview_history = db_session.query(InterviewHistory).filter_by(user_id=user_id, session_id=session_id).order_by(InterviewHistory.created_at.desc()).first()
        if not interview_history or not interview_history.answer:
            raise ValueError("No answers stored")

        most_recent_answer = interview_history.answer
        most_recent_question = interview_history.question

        # Get the most recent ID from the global variable
        if not used_questions_table_ids:
            raise ValueError("No used question IDs found")
        
        most_recent_question_id = used_questions_table_ids[-1]
        
        # Fetch the description of the question from the questions table
        question_row = db_session.query(Questions).filter_by(id=most_recent_question_id).first()
        if not question_row:
            raise ValueError("Question not found in questions table")

        question_description = question_row.description

        # Generate the next question first
        next_question = get_ethical_question_1(user_id, session_id)

        feedback_prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are helping me land a new job by conducting realistic job interviews with me. "
                       f"I’m interviewing to be a {job_title} at {company_name} company in the {industry} industry. "
                       f"You just asked me the question: {most_recent_question}. "
                       "I am going to answer you and I want you to give me a very critical critique of how well I answered the question. "
                       f"As the interviewer, you asked me this question because: {question_description}. Did my answer accomplish this? "
                       "Did I answer the question in a reasonable amount of time that lasted no more than 3 minutes? "
                       "Finally, please give me a recommendation on how I could have presented my experience better."),
            ("user", most_recent_answer),
            MessagesPlaceholder(variable_name="messages"),
        ])

        analysis_chain = feedback_prompt | model

        feedback_response = analysis_chain.invoke({"messages": [HumanMessage(content=most_recent_answer)]})

        feedback = feedback_response.content if feedback_response.content else "No feedback found"
        logger.info(f"Generated feedback: {feedback}")

        # Store the feedback
        store_feedback(feedback, user_id, session_id)

        # Generate and store the score after the feedback
        score = get_score(user_id, session_id)
        if score is not None:
            logger.info(f"Calling store_score with score: {score}")
            store_score(interview_history.id, score)
        else:
            logger.info("Score was not generated, store_score will not be called.")

        return {"next_question_response": next_question, "feedback": feedback, "score": score}
    except Exception as e:
        logger.error(f"Error in get_competency_question_1_feedback function: {e}")
        return {"error": "Could not generate feedback."}
    
def get_ethical_question_1_feedback(user_id, session_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()
        
        if not user or not job_description:
            raise ValueError("User or job description not found")

        job_title = job_description.job_title
        company_name = job_description.company_name
        industry = job_description.company_industry

        # Get the most recent answer
        interview_history = db_session.query(InterviewHistory).filter_by(user_id=user_id, session_id=session_id).order_by(InterviewHistory.created_at.desc()).first()
        if not interview_history or not interview_history.answer:
            raise ValueError("No answers stored")

        most_recent_answer = interview_history.answer
        most_recent_question = interview_history.question

        # Get the most recent ID from the global variable
        if not used_questions_table_ids:
            raise ValueError("No used question IDs found")
        
        most_recent_question_id = used_questions_table_ids[-1]
        
        # Fetch the description of the question from the questions table
        question_row = db_session.query(Questions).filter_by(id=most_recent_question_id).first()
        if not question_row:
            raise ValueError("Question not found in questions table")

        question_description = question_row.description

        # Generate the next question first
        next_question = get_last_question(user_id, session_id)

        feedback_prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are helping me land a new job by conducting realistic job interviews with me. "
                       f"I’m interviewing to be a {job_title} at {company_name} company in the {industry} industry. "
                       f"You just asked me the question: {most_recent_question}. "
                       "I am going to answer you and I want you to give me a very critical critique of how well I answered the question. "
                       f"As the interviewer, you asked me this question because: {question_description}. Did my answer accomplish this? "
                       "Did I answer the question in a reasonable amount of time that lasted no more than 3 minutes? "
                       "Finally, please give me a recommendation on how I could have presented my experience better."),
            ("user", most_recent_answer),
            MessagesPlaceholder(variable_name="messages"),
        ])

        analysis_chain = feedback_prompt | model

        feedback_response = analysis_chain.invoke({"messages": [HumanMessage(content=most_recent_answer)]})

        feedback = feedback_response.content if feedback_response.content else "No feedback found"
        logger.info(f"Generated feedback: {feedback}")

        # Store the feedback
        store_feedback(feedback, user_id, session_id)

        # Generate and store the score after the feedback
        score = get_score(user_id, session_id)
        if score is not None:
            logger.info(f"Calling store_score with score: {score}")
            store_score(interview_history.id, score)
        else:
            logger.info("Score was not generated, store_score will not be called.")

        return {"next_question_response": next_question, "feedback": feedback, "score": score}
    except Exception as e:
        logger.error(f"Error in get_ethical_question_1_feedback function: {e}")
        return {"error": "Could not generate feedback."}

def get_last_question_feedback(user_id, session_id):
    try:
        print("Starting get_last_question_feedback function...")
        
        user = db_session.query(User).filter_by(id=user_id).first()
        job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()
        
        if not user or not job_description:
            raise ValueError("User or job description not found")

        job_title = job_description.job_title
        company_name = job_description.company_name
        industry = job_description.company_industry

        print(f"User found: {user}")
        print(f"Job description found: {job_description}")

        # Get the most recent answer
        interview_history = db_session.query(InterviewHistory).filter_by(user_id=user_id, session_id=session_id).order_by(InterviewHistory.created_at.desc()).first()
        if not interview_history or not interview_history.answer:
            raise ValueError("No answers stored")

        most_recent_answer = interview_history.answer
        most_recent_question = interview_history.question

        print(f"Most recent answer: {most_recent_answer}")
        print(f"Most recent question: {most_recent_question}")

        feedback_prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are helping me land a new job by conducting realistic job interviews with me. "
                       f"I’m interviewing to be a {job_title} at {company_name} company in the {industry} industry. "
                       f"You just asked me the question: {most_recent_question}. "
                       "I am going to answer you and I want you to give me a very critical critique of how well I answered the question. "
                       "You should specifically consider if the questions that I asked are good questions to ask a Recruiter during your first interview. "
                       "Finally, please give me a few examples of good questions to ask a Recruiter from the HR department in your first interview in the interview process."),
            ("user", most_recent_answer),
            MessagesPlaceholder(variable_name="messages"),
        ])

        analysis_chain = feedback_prompt | model

        feedback_response = analysis_chain.invoke({"messages": [HumanMessage(content=most_recent_answer)]})

        feedback = feedback_response.content if feedback_response.content else "No feedback found"
        print(f"Generated feedback: {feedback}")

        # Store the feedback
        store_feedback(feedback, user_id, session_id)

        # Generate and store the score after the feedback
        score = get_score(user_id, session_id)
        if score is not None:
            print(f"Calling store_score with score: {score}")
            store_score(interview_history.id, score)
        else:
            print("Score was not generated, store_score will not be called.")

        return {"next_question_response": "No next question", "feedback": feedback, "score": score}
    except Exception as e:
        logger.error(f"Error in get_last_question_feedback function: {e}")
        print(f"Error in get_last_question_feedback function: {e}")
        return {"error": "Could not generate feedback."}



#Start of question functions: 

def intro_question(user_id, session_id):
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
           store_question(intro_question_text, user_id, session_id, is_initial=True)
           return intro_question_text
       else:
           return "Error: User or job description not found."
   except Exception as e:
       print(f"Error generating intro question: {e}")
       return "Error: Could not generate intro question."

def get_resume_question_1(user_id, session_id):
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

        prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are the world's best interview coach. We are conducting a mock interview where I am interviewing for the role of {job_title} at {job_description.company_name} company. "
                       f"I want you to ask me a question as if you are the actual hiring manager. You have my resume in front of you. "
                       f"You can see from my resume that my top technical skills are: {key_technical_skills}. "
                       f"You have the job description in front of you which shows that the job responsibilities are: {job_responsibilities} and the required professional experiences are: {required_professional_experiences}. "
                       "Identify similarities in the job description and my top technical skills."
                       "Select one of my top technical skills that matches the job description and ask me to elaborate on how I developed and have used that technical skill in the past."),
            MessagesPlaceholder(variable_name="messages"),
        ])

        chain = prompt | model
        response = chain.invoke({"messages": []})

        question = response.content
        store_question(question, user_id, session_id)
        return question
    except Exception as e:
        print(f"Error in get_resume_question_1 function: {e}")
        return "Error: Could not generate resume question 1."

def get_resume_question_2(user_id, session_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()

        if not user or not job_description:
            raise ValueError("User or job description not found")

        job_title = user.most_recent_job_title
        key_soft_skills = user.key_soft_skills

        job_responsibilities = job_description.job_responsibilities
        required_professional_experiences = job_description.required_professional_experiences
        required_skill_sets = job_description.required_skill_sets

        prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are the world's best interview coach. We are conducting a mock interview where I am interviewing for the role of {job_title} at {job_description.company_name} company. "
                       f"You can see from my resume that my top soft skills are: {key_soft_skills}. "
                       f"You have the job description I’m interviewing for in front of you which shows that the job responsibilities are: {job_responsibilities} and the required professional experiences are: {required_professional_experiences}. "
                       "Identify similarities in the job description and my top soft skills. "
                       "Select one of my top soft skills that matches the job description and ask me to elaborate on how I developed and have used that soft skill in the past."),
            MessagesPlaceholder(variable_name="messages"),
        ])

        chain = prompt | model
        response = chain.invoke({"messages": []})

        question = response.content
        store_question(question, user_id, session_id)
        return question
    except Exception as e:
        print(f"Error in get_resume_question_2 function: {e}")
        return "Error: Could not generate resume question 2."
    
def get_resume_question_3(user_id, session_id):
    try:
        # Fetch user information
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:
            raise ValueError("User not found")
        
        # Fetch job description information
        job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()
        if not job_description:
            raise ValueError("Job description not found")

        # Extract necessary details
        job_title = user.most_recent_job_title
        most_recent_successful_project = user.most_recent_successful_project
        company_name = job_description.company_name
        job_responsibilities = job_description.job_responsibilities
        required_professional_experiences = job_description.required_professional_experiences

        logger.info(f"Generating question for user: {user_id}, job title: {job_title}, project: {most_recent_successful_project}")

        # Prepare the chat prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are the world's best interview coach. We are conducting a mock interview where I am interviewing for the role of {job_title} at {company_name} company. "
                       f"You can see from my resume that my most recent successful project was: {most_recent_successful_project}. "
                       f"You have the job description I’m interviewing for in front of you which shows that the job responsibilities are: {job_responsibilities} and the required professional experiences are: {required_professional_experiences}. "
                       f"Start your next question with, \"I noticed from your resume that a recent accomplishment was {most_recent_successful_project}\". Follow that up by asking me to explain how I contributed and helped lead the team to the success of that project."),
            MessagesPlaceholder(variable_name="messages"),
        ])

        # Add debug statement to check the prompt structure
        logger.debug(f"Prompt structure: {prompt}")

        # Invoke the model to generate the response
        chain = prompt | model
        response = chain.invoke({"messages": [], "most_recent_successful_project": most_recent_successful_project})

        # Extract and store the question
        question = response.content
        if not question:
            raise ValueError("Generated question is empty")
        store_question(question, user_id, session_id)
        logger.info(f"Generated question: {question}")
        return question
    except ValueError as ve:
        logger.error(f"ValueError in get_resume_question_3 function: {ve}")
        return f"Error: {ve}"
    except Exception as e:
        logger.error(f"Unexpected error in get_resume_question_3 function: {e}")
        return "Error: Could not generate resume question 3."


def get_resume_question_4(user_id, session_id):
    try:
        # Fetch user information
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:
            raise ValueError("User not found")
        
        # Fetch job description information
        job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()
        if not job_description:
            raise ValueError("Job description not found")

        # Extract necessary details
        job_title = user.most_recent_job_title
        top_challenge = user.top_challenge
        company_name = job_description.company_name
        job_responsibilities = job_description.job_responsibilities
        required_professional_experiences = job_description.required_professional_experiences

        logger.info(f"Generating question for user: {user_id}, job title: {job_title}, challenge: {top_challenge}")

        # Prepare the chat prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are the world's best interview coach. We are conducting a mock interview where I am interviewing for the role of {job_title} at {company_name} company. "
                       f"You have my resume in front of you and you can see that a really challenging project I worked on is: {top_challenge}. "
                       f"Start your next question with, \"I noticed from your resume that a really interesting project you worked on was: {top_challenge}\". Follow that up by asking me to explain what challenges I faced while working on this project."),
            MessagesPlaceholder(variable_name="messages"),
        ])

        # Add debug statement to check the prompt structure
        logger.debug(f"Prompt structure: {prompt}")

        # Invoke the model to generate the response
        chain = prompt | model
        response = chain.invoke({"messages": [], "top_challenge": top_challenge})

        # Extract and store the question
        question = response.content
        if not question:
            raise ValueError("Generated question is empty")
        store_question(question, user_id, session_id)
        logger.info(f"Generated question: {question}")
        return question
    except ValueError as ve:
        logger.error(f"ValueError in get_resume_question_4 function: {ve}")
        return f"Error: {ve}"
    except Exception as e:
        logger.error(f"Unexpected error in get_resume_question_4 function: {e}")
        return "Error: Could not generate resume question 4."

def get_behavioral_question_1(user_id, session_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()

        if not user:
            raise ValueError("User not found")

        # Fetch username
        username = user.username

        # Query to get a behavioral question that hasn't been used yet
        question_row = db_session.query(Questions).filter(
            Questions.question_type == "behavioral questions",
            ~Questions.id.in_(used_questions_table_ids)
        ).first()

        if not question_row:
            raise ValueError("No available behavioral questions found")

        # Add the question ID to the used list
        used_questions_table_ids.append(question_row.id)

        # Clean and format the question
        question = capitalize_sentences(question_row.question)
        final_question = f"Thanks {username}! Now I’d like to cover a behavioral question. {question}"

        store_question(final_question, user_id, session_id)
        return final_question
    except Exception as e:
        logger.error(f"Error in get_behavioral_question_1 function: {e}")
        return "Error: Could not generate behavioral question 1."

def get_behavioral_question_2(user_id, session_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()

        if not user:
            raise ValueError("User not found")

        # Fetch username
        username = user.username

        # Query to get a behavioral question that hasn't been used yet
        question_row = db_session.query(Questions).filter(
            Questions.question_type == "behavioral questions",
            ~Questions.id.in_(used_questions_table_ids)
        ).first()

        if not question_row:
            raise ValueError("No available behavioral questions found")

        # Add the question ID to the used list
        used_questions_table_ids.append(question_row.id)

        # Clean and format the question
        question = capitalize_sentences(question_row.question)
        final_question = f"Thanks {username}! {question}"

        store_question(final_question, user_id, session_id)
        return final_question
    except Exception as e:
        logger.error(f"Error in get_behavioral_question_2 function: {e}")
        return "Error: Could not generate behavioral question 2."

def get_situational_question_1(user_id, session_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()

        if not user:
            raise ValueError("User not found")

        # Fetch username
        username = user.username

        # Query to get a situational question that hasn't been used yet
        question_row = db_session.query(Questions).filter(
            Questions.question_type == "situatinoal questions",  # Note the typo here
            ~Questions.id.in_(used_questions_table_ids)
        ).first()

        if not question_row:
            raise ValueError("No available situational questions found")

        # Add the question ID to the used list
        used_questions_table_ids.append(question_row.id)

        # Clean and format the question
        question = capitalize_sentences(question_row.question)
        final_question = f"Thanks again {username}! {question}"

        store_question(final_question, user_id, session_id)
        return final_question
    except Exception as e:
        logger.error(f"Error in get_situational_question_1 function: {e}")
        return "Error: Could not generate situational question 1."

def get_personality_question_1(user_id, session_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()

        if not user:
            raise ValueError("User not found")

        # Query to get a personality question that hasn't been used yet
        question_row = db_session.query(Questions).filter(
            Questions.question_type == "personality questions",
            ~Questions.id.in_(used_questions_table_ids)
        ).first()

        if not question_row:
            raise ValueError("No available personality questions found")

        # Add the question ID to the used list
        used_questions_table_ids.append(question_row.id)

        # Clean and format the question
        question = capitalize_sentences(question_row.question)
        final_question = f"{question}"

        store_question(final_question, user_id, session_id)
        return final_question
    except Exception as e:
        logger.error(f"Error in get_personality_question_1 function: {e}")
        return "Error: Could not generate personality question 1."

def get_motivational_question_1(user_id, session_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()

        if not user:
            raise ValueError("User not found")

        # Query to get a motivational question that hasn't been used yet
        question_row = db_session.query(Questions).filter(
            Questions.question_type == "motivational questions",
            ~Questions.id.in_(used_questions_table_ids)
        ).first()

        if not question_row:
            raise ValueError("No available motivational questions found")

        # Add the question ID to the used list
        used_questions_table_ids.append(question_row.id)

        # Clean and format the question
        question = capitalize_sentences(question_row.question)
        final_question = f"{question}"

        store_question(final_question, user_id, session_id)
        return final_question
    except Exception as e:
        logger.error(f"Error in get_motivational_question_1 function: {e}")
        return "Error: Could not generate motivational question 1."

def get_competency_question_1(user_id, session_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()

        if not user:
            raise ValueError("User not found")

        # Query to get a competency-based question that hasn't been used yet
        question_row = db_session.query(Questions).filter(
            Questions.question_type == "competency based questions",
            ~Questions.id.in_(used_questions_table_ids)
        ).first()

        if not question_row:
            raise ValueError("No available competency based questions found")

        # Add the question ID to the used list
        used_questions_table_ids.append(question_row.id)

        # Clean and format the question
        question = capitalize_sentences(question_row.question)
        final_question = f"{question}"

        store_question(final_question, user_id, session_id)
        return final_question
    except Exception as e:
        logger.error(f"Error in get_competency_question_1 function: {e}")
        return "Error: Could not generate competency question 1."

def get_ethical_question_1(user_id, session_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()

        if not user:
            raise ValueError("User not found")

        # Query to get an ethical question that hasn't been used yet
        question_row = db_session.query(Questions).filter(
            Questions.question_type == "ethical questions",
            ~Questions.id.in_(used_questions_table_ids)
        ).first()

        if not question_row:
            raise ValueError("No available ethical questions found")

        # Add the question ID to the used list
        used_questions_table_ids.append(question_row.id)

        # Clean and format the question
        question = capitalize_sentences(question_row.question)
        final_question = f"{question}"

        store_question(final_question, user_id, session_id)
        return final_question
    except Exception as e:
        logger.error(f"Error in get_ethical_question_1 function: {e}")
        return "Error: Could not generate ethical question 1."

def get_last_question(user_id, session_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()

        if not user or not job_description:
            raise ValueError("User or job description not found")

        # Extract necessary details
        job_title = job_description.job_title
        company_name = job_description.company_name

        # Generate the last question
        last_question = (f"It looks like we’re almost out of time and I want to give you a chance to ask me some questions. "
                         f"Please go ahead and ask me whatever questions you have about {company_name}, the {job_title} role or anything that has come up during this interview. "
                         "I will then give you feedback on your questions.")

        store_question(last_question, user_id, session_id)
        return last_question
    except Exception as e:
        logger.error(f"Error in get_last_question function: {e}")
        return "Error: Could not generate the last question."

