from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TrainingData(Base):
    __tablename__ = 'training_data'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)  # New column for user_id
    job_title = Column(String(100), nullable=False)
    company_name = Column(String(100), nullable=False)
    file_summary = Column(String, nullable=False)  # Renamed from data to file_summary
    processed_files = Column(String, nullable=False)
    top_topics = Column(Text, nullable=True)  # New column for top_topics
    primary_products_and_services = Column(Text, nullable=True)  # New column for primary_products_and_services
    target_market = Column(Text, nullable=True)  # New column for target_market
    market_position = Column(Text, nullable=True)  # New column for market_position
    required_skills = Column(Text, nullable=True)  # New column for required_skills
    unique_selling_proposition = Column(Text, nullable=True)  # New column for unique_selling_proposition

class ProcessStatus(Base):
    __tablename__ = 'process_status'
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, index=True)
    job_title = Column(String, nullable=False, index=True)
    company_name = Column(String, nullable=False, index=True)
    status = Column(Text, nullable=False)
