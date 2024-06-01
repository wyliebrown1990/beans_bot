import os
from flask import Flask, render_template, request, redirect, url_for
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ProgrammingError

load_dotenv()

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
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

def create_table_if_not_exists():
    try:
        SpecificInterviewData.__table__.create(engine, checkfirst=True)
    except ProgrammingError:
        pass

create_table_if_not_exists()
Session = sessionmaker(bind=engine)
session = Session()

@app.route('/')
def index():
    job_title = request.args.get('job_title')
    company_name = request.args.get('company_name')
    industry = request.args.get('industry')
    username = request.args.get('username')

    if job_title == 'generic':
        return redirect(url_for('generic_interview'))
    elif job_title and company_name and industry and username:
        return redirect(url_for('specific_interview', job_title=job_title, company_name=company_name, industry=industry, username=username))
    else:
        return "Invalid URL parameters", 400

@app.route('/generic_interview')
def generic_interview():
    first_question = "I'm all ears and whiskers! Tell me about your purr-sonal work experience and background. Can you share the tail of your career so far? I'd love to hear about the pawsitive impact you've made in your previous jobs."
    return render_template('generic_interview.html', first_question=first_question)

@app.route('/specific_interview')
def specific_interview():
    job_title = request.args.get('job_title')
    company_name = request.args.get('company_name')
    industry = request.args.get('industry')
    username = request.args.get('username')
    first_question = "I'm all ears and whiskers! Tell me about your purr-sonal work experience and background. Can you share the tail of your career so far? I'd love to hear about the pawsitive impact you've made in your previous jobs."
    return render_template('specific_interview.html', first_question=first_question, job_title=job_title, company_name=company_name, industry=industry, username=username)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5012)