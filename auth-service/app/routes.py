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
    get_resume_analysis
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
            
            user.top_technical_skills = response_data.get("top_technical_skills", "")
            user.most_recent_job_title = response_data.get("most_recent_job_title", "")
            user.most_recent_company_name = response_data.get("most_recent_company_name", "")
            user.most_recent_experience_summary = response_data.get("most_recent_experience_summary", "")
            user.industry_expertise = response_data.get("industry_expertise", "")
            user.top_soft_skills = response_data.get("top_soft_skills", "")

            session.add(user)
            session.commit()

            flash('User registered successfully')
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid file format. Please upload a .docx, .pdf, or .txt file.')
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
