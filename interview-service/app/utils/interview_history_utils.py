from app.models import InterviewHistory
from app.database import db_session
from datetime import datetime

def record_interview_history(session_id, user_id, question, answer, score, feedback, timer, interview_round, job_title, job_level, company_name, company_industry, question_id=None):
    interview_entry = InterviewHistory(
        session_id=session_id,
        user_id=user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),  # Manually set updated_at
        job_title=job_title,
        job_level=job_level,
        company_name=company_name,
        company_industry=company_industry,
        question=question,
        question_id=question_id if question_id is not None else None,
        answer=answer,
        feedback=feedback,
        score=score,
        timer=timer,
        interview_round=interview_round
    )
    db_session.add(interview_entry)
    db_session.commit()
    return interview_entry.id