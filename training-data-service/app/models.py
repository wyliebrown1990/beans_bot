from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from flask_login import UserMixin
from datetime import datetime

Base = declarative_base()

class Users(UserMixin, Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    account_created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    date_joined = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    location_input = Column(String(255), nullable=True)
    job_situation = Column(String(255), nullable=False)
    resumes = relationship("Resumes", backref="user", lazy=True)

    interview_history = relationship("InterviewHistory", back_populates="user")

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
    question = Column(String(200), nullable=False)
    question_id = Column(Integer, ForeignKey('questions.id'), nullable=False)
    answer = Column(Text, nullable=True)
    feedback = Column(String(1000), nullable=True)
    score = Column(Integer, nullable=True)
    skip_next_time = Column(Boolean, nullable=False, default=False)
    session_score_average = Column(Integer, nullable=True)
    session_top_score = Column(String(100), nullable=True)
    session_low_score = Column(String(100), nullable=True)
    session_summary_next_steps = Column(Text, nullable=True)

    user = relationship("Users", back_populates="interview_history")
    question_rel = relationship("Questions", back_populates="interview_history")

class JobDescriptions(Base):
    __tablename__ = 'job_descriptions'
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
    job_responsibilities = Column(ARRAY(String), nullable=True)
    personal_qualifications = Column(ARRAY(String), nullable=True)
    Required_technical_skills = Column(ARRAY(String), nullable=True)
    Required_soft_skills = Column(ARRAY(String), nullable=True)

    # Company Information
    company_name = Column(String(100), nullable=True)
    company_size = Column(String(50), nullable=True)
    company_industry = Column(String(100), nullable=True)
    company_mission_and_values = Column(Text, nullable=True)

    # Requirements and Qualifications
    education_background = Column(ARRAY(String), nullable=True)
    required_professional_experiences = Column(ARRAY(String), nullable=True)
    nice_to_have_experiences = Column(ARRAY(String), nullable=True)
    required_skill_sets = Column(ARRAY(String), nullable=True)

    # Keywords Analysis
    keywords_analysis = Column(ARRAY(String), nullable=True)

class Resumes(Base):
    __tablename__ = 'resumes'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    username = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False)
    file_uploaded = Column(String(255), nullable=True)
    header_text = Column(Text, nullable=True)
    top_section_summary = Column(Text, nullable=True)
    top_section_list_of_achievements = Column(ARRAY(Text), nullable=True)
    education = Column(Text, nullable=True)
    bottom_section_list_of_achievements = Column(ARRAY(Text), nullable=True)
    achievements_and_awards = Column(ARRAY(Text), nullable=True)
    job_title_1 = Column(String(255), nullable=True)
    job_title_1_start_date = Column(DateTime, nullable=True)
    job_title_1_end_date = Column(DateTime, nullable=True)
    job_title_1_length = Column(String(50), nullable=True)
    job_title_1_location = Column(String(255), nullable=True)
    job_title_1_description = Column(Text, nullable=True)
    job_title_2 = Column(String(255), nullable=True)
    job_title_2_start_date = Column(DateTime, nullable=True)
    job_title_2_end_date = Column(DateTime, nullable=True)
    job_title_2_length = Column(String(50), nullable=True)
    job_title_2_location = Column(String(255), nullable=True)
    job_title_2_description = Column(Text, nullable=True)
    job_title_3 = Column(String(255), nullable=True)
    job_title_3_start_date = Column(DateTime, nullable=True)
    job_title_3_end_date = Column(DateTime, nullable=True)
    job_title_3_length = Column(String(50), nullable=True)
    job_title_3_location = Column(String(255), nullable=True)
    job_title_3_description = Column(Text, nullable=True)
    job_title_4 = Column(String(255), nullable=True)
    job_title_4_start_date = Column(DateTime, nullable=True)
    job_title_4_end_date = Column(DateTime, nullable=True)
    job_title_4_length = Column(String(50), nullable=True)
    job_title_4_location = Column(String(255), nullable=True)
    job_title_4_description = Column(Text, nullable=True)
    job_title_5 = Column(String(255), nullable=True)
    job_title_5_start_date = Column(DateTime, nullable=True)
    job_title_5_end_date = Column(DateTime, nullable=True)
    job_title_5_length = Column(String(50), nullable=True)
    job_title_5_location = Column(String(255), nullable=True)
    job_title_5_description = Column(Text, nullable=True)
    job_title_6 = Column(String(255), nullable=True)
    job_title_6_start_date = Column(DateTime, nullable=True)
    job_title_6_end_date = Column(DateTime, nullable=True)
    job_title_6_length = Column(String(50), nullable=True)
    job_title_6_location = Column(String(255), nullable=True)
    job_title_6_description = Column(Text, nullable=True)
    key_technical_skills = Column(ARRAY(String), nullable=True)
    key_soft_skills = Column(ARRAY(String), nullable=True)
    top_listed_skill_keyword = Column(String(255), nullable=True)
    second_most_top_listed_skill_keyword = Column(String(255), nullable=True)
    third_most_top_listed_skill_keyword = Column(String(255), nullable=True)
    fourth_most_top_listed_skill_keyword = Column(String(255), nullable=True)
    certifications_and_awards = Column(ARRAY(Text), nullable=True)
    most_recent_successful_project = Column(Text, nullable=True)
    areas_for_improvement = Column(Text, nullable=True)
    questions_about_experience = Column(Text, nullable=True)
    resume_length = Column(String(50), nullable=True)
    top_challenge = Column(Text, nullable=True)

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
    question = Column(String(1000), nullable=False)
    description = Column(String(1000), nullable=True)
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
