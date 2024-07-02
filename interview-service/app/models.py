from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from flask_login import UserMixin
from datetime import datetime

Base = declarative_base()

class InterviewHistory(Base):
    __tablename__ = 'interview_history'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    job_title = Column(String(100), nullable=True)
    job_level = Column(String(50), nullable=True)
    company_name = Column(String(100), nullable=True)
    company_industry = Column(String(100), nullable=True)
    question = Column(Text, nullable=False)
    question_id = Column(Integer, ForeignKey('questions.id'), nullable=False)
    answer = Column(Text, nullable=True)
    feedback = Column(Text, nullable=True)
    score = Column(Integer, nullable=True)
    skip_next_time = Column(Boolean, nullable=False, default=False)
    session_score_average = Column(Float, nullable=True)  # Change to Float
    session_top_score = Column(String(100), nullable=True)
    session_low_score = Column(String(100), nullable=True)
    session_summary_next_steps = Column(Text, nullable=True)

    user = relationship("User", back_populates="interview_history")
    question_rel = relationship("Questions", back_populates="interview_history")

class JobDescriptionAnalysis(Base):
    __tablename__ = 'job_description_analysis'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Job Details
    job_title = Column(String(100), nullable=True)
    job_level = Column(String(50), nullable=True)
    job_location = Column(String(100), nullable=True)
    job_type = Column(String(50), nullable=True)
    job_salary = Column(String(50), nullable=True)
    job_responsibilities = Column(Text, nullable=True)
    personal_qualifications = Column(Text, nullable=True)

    # Company Information
    company_name = Column(String(100), nullable=True)
    company_size = Column(String(50), nullable=True)
    company_industry = Column(String(100), nullable=True)
    company_mission_and_values = Column(Text, nullable=True)

    # Requirements and Qualifications
    education_background = Column(Text, nullable=True)
    required_professional_experiences = Column(Text, nullable=True)
    nice_to_have_experiences = Column(Text, nullable=True)
    required_skill_sets = Column(Text, nullable=True)

class User(UserMixin, Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    resume_text_full = Column(Text, nullable=True)
    key_technical_skills = Column(Text, nullable=True)
    key_soft_skills = Column(Text, nullable=True)
    most_recent_job_title = Column(String(255), nullable=True)
    second_most_recent_job_title = Column(String(255), nullable=True)
    most_recent_job_title_summary = Column(Text, nullable=True)
    second_most_recent_job_title_summary = Column(Text, nullable=True)
    top_listed_skill_keyword = Column(String(255), nullable=True)
    second_most_top_listed_skill_keyword = Column(String(255), nullable=True)
    third_most_top_listed_skill_keyword = Column(String(255), nullable=True)
    fourth_most_top_listed_skill_keyword = Column(String(255), nullable=True)
    educational_background = Column(Text, nullable=True)
    certifications_and_awards = Column(Text, nullable=True)
    most_recent_successful_project = Column(Text, nullable=True)
    areas_for_improvement = Column(Text, nullable=True)
    questions_about_experience = Column(Text, nullable=True)
    resume_length = Column(Text, nullable=True)
    top_challenge = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    interview_history = relationship("InterviewHistory", back_populates="user")

class Questions(Base):
    __tablename__ = 'questions'
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_user_submitted = Column(Boolean, nullable=False)
    is_role_specific = Column(Boolean, nullable=False)
    is_resume_specific = Column(Boolean, nullable=False)
    is_question_ai_generated = Column(Boolean, nullable=False)
    question_type = Column(String(50), nullable=False)
    question = Column(String(200), nullable=False)
    description = Column(String(200), nullable=True)
    job_title = Column(String(50), nullable=True)
    user_id = Column(Integer, nullable=True)

    interview_history = relationship("InterviewHistory", back_populates="question_rel")

    def to_dict(self):
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_user_submitted': self.is_user_submitted,
            'is_role_specific': self.is_role_specific,
            'is_resume_specific': self.is_resume_specific,
            'is_question_ai_generated': self.is_question_ai_generated,
            'question_type': self.question_type,
            'question': self.question,
            'description': self.description,
            'job_title': self.job_title,
            'user_id': self.user_id
        }
