from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class TrainingData(Base):
   __tablename__ = 'training_data'
   id = Column(Integer, primary_key=True)
   user_id = Column(Integer, nullable=False)
   job_title = Column(String(100), nullable=False)
   company_name = Column(String(100), nullable=False)
   file_summary = Column(String, nullable=False)
   processed_files = Column(String, nullable=False)
   top_topics = Column(Text, nullable=True)
   primary_products_and_services = Column(Text, nullable=True)
   target_market = Column(Text, nullable=True)
   market_position = Column(Text, nullable=True)
   required_skills = Column(Text, nullable=True)
   unique_selling_proposition = Column(Text, nullable=True)
   created_at = Column(DateTime(timezone=True), server_default=func.now())
   updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ProcessStatus(Base):
   __tablename__ = 'process_status'
   id = Column(Integer, primary_key=True)
   username = Column(String, nullable=False, index=True)
   job_title = Column(String, nullable=False, index=True)
   company_name = Column(String, nullable=False, index=True)
   status = Column(Text, nullable=False)
   created_at = Column(DateTime(timezone=True), server_default=func.now())
   updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

