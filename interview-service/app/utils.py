from sqlalchemy import create_engine, Column, Integer, String, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ProgrammingError

Base = declarative_base()

class SpecificInterviewData(Base):
    __tablename__ = 'specific_interview_data'
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False)
    username = Column(String, nullable=False)
    job_title = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    industry = Column(String, nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    answer_score = Column(Float, nullable=True)

def create_table_if_not_exists(engine):
    try:
        SpecificInterviewData.__table__.create(engine, checkfirst=True)
    except ProgrammingError:
        pass

def setup_database(database_url):
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    return engine, session