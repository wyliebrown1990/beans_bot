from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from .models import User
from .utils import (
    get_user_by_username, 
    get_user_by_email, 
    allowed_file, 
    extract_text_from_file, 
    SessionLocal, 
    get_resume_analysis,
    output_checker,
    get_resume_analysis_2
)
from . import login_manager
import json

auth_bp = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    session = SessionLocal()
    try:
        return session.query(User).get(user_id)
    finally:
        session.close()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = get_user_by_email(email)
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('auth.home'))
        else:
            flash('Invalid email or password. Please try again.')
    return render_template('login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            file = request.files['resume']
            session = SessionLocal()
            existing_user_by_username = get_user_by_username(username)
            existing_user_by_email = get_user_by_email(email)
            if existing_user_by_email:
                flash('That email is already registered. Would you like to login?')
                return redirect(url_for('auth.signup'))
            if existing_user_by_username:
                flash('That username is already registered. Please try something new.')
                return redirect(url_for('auth.signup'))
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                resume_text = extract_text_from_file(file_path)
                user = User(username=username, email=email, resume_text_full=resume_text)
                user.set_password(password)
                session.add(user)
                session.commit()

                # Send resume text to ChatGPT and update user record with the response
                response_data = get_resume_analysis(resume_text)

                # Print the response data for debugging
                print("Response Data:", response_data)

                if not output_checker(response_data):
                    response_data = get_resume_analysis_2(resume_text)
                
                user.key_technical_skills = ', '.join(response_data.get("key_technical_skills", []))
                user.key_soft_skills = ', '.join(response_data.get("key_soft_skills", []))
                user.most_recent_job_title = response_data.get("most_recent_job_title", "")
                user.second_most_recent_job_title = response_data.get("second_most_recent_job_title", "")
                user.most_recent_job_title_summary = response_data.get("most_recent_job_title_summary", "")
                user.second_most_recent_job_title_summary = response_data.get("second_most_recent_job_title_summary", "")
                user.top_listed_skill_keyword = response_data.get("top_listed_skill_keyword", "")
                user.second_most_top_listed_skill_keyword = response_data.get("second_most_top_listed_skill_keyword", "")
                user.third_most_top_listed_skill_keyword = response_data.get("third_most_top_listed_skill_keyword", "")
                user.fourth_most_top_listed_skill_keyword = response_data.get("fourth_most_top_listed_skill_keyword", "")
                user.educational_background = response_data.get("educational_background", "")
                user.certifications_and_awards = ', '.join(response_data.get("certifications_and_awards", []))
                user.most_recent_successful_project = response_data.get("most_recent_successful_project", "")
                user.areas_for_improvement = response_data.get("areas_for_improvement", "")
                user.questions_about_experience = response_data.get("questions_about_experience", "")
                user.resume_length = response_data.get("resume_length", "")
                user.top_challenge = response_data.get("top_challenge", "")

                session.add(user)
                session.commit()

                # Delete the resume file after successfully writing data to the database
                if os.path.exists(file_path):
                    os.remove(file_path)

                flash('User registered successfully')
                return redirect(url_for('auth.login'))
            else:
                flash('Invalid file format. Please upload a .docx, .pdf, or .txt file.')
        except Exception as e:
            print(f"Error: {e}")
            flash('We encountered an error. Try uploading your resume in a different format please.')
            return redirect(url_for('auth.signup'))
    return render_template('signup.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/')
def home():
    if current_user.is_authenticated:
        return render_template('home.html')
    else:
        return redirect(url_for('auth.login'))
