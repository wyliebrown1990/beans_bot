from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session, relationship
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

Base = declarative_base()
engine = None
SessionLocal = None

def init_db(db_url):
    global engine
    global SessionLocal
    engine = create_engine(db_url)
    SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
    Base.metadata.create_all(bind=engine)

class User(UserMixin, Base):
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
    resumes = relationship("Resume", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Resume(Base):
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
