from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

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

class ProcessStatus(Base):
   __tablename__ = 'process_status'
   id = Column(Integer, primary_key=True)
   username = Column(String, nullable=False, index=True)
   job_title = Column(String, nullable=False, index=True)
   company_name = Column(String, nullable=False, index=True)
   status = Column(Text, nullable=False)
   created_at = Column(DateTime(timezone=True), server_default=func.now())
   updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

