import random
from app.database import db_session
from app.models import InterviewHistory

#Start of generating unique IDs:

def generate_session_id():
    return random.randint(100000, 999999)

def ensure_unique_session_id(user_id):
    while True:
        session_id = generate_session_id()
        existing_session = db_session.query(InterviewHistory).filter_by(user_id=user_id, session_id=session_id).first()
        if not existing_session:
            return session_id
