from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os
from langchain_openai import ChatOpenAI
from .models import User, Resume
from .utils import (
    get_user_by_username,
    get_user_by_email,
    allowed_file,
    extract_text_from_file,
    SessionLocal,
    get_resume_analysis,
    output_checker
)
from . import login_manager
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            return redirect(url_for('auth.redirect_to_service', username=user.username, user_id=user.id))
        else:
            flash('Invalid email or password. Please try again.')
    return render_template('login.html')

@auth_bp.route('/redirect_to_service')
@login_required
def redirect_to_service():
    username = request.args.get('username')
    user_id = request.args.get('user_id')
    return redirect(f'http://localhost:5011/?username={username}&user_id={user_id}')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            username = request.form['username'].lower()  # Convert to lowercase
            email = request.form['email']
            password = request.form['password']
            location_input = request.form['location_input']
            job_situation = request.form['job_situation']
            other_job_situation = request.form.get('other_job_situation', None)
            if job_situation == "Other":
                job_situation = other_job_situation

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

            user = User(username=username, email=email, location_input=location_input, job_situation=job_situation)
            user.set_password(password)
            session.add(user)
            session.commit()  # Commit the user data first to generate user.id

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                resume_text = extract_text_from_file(file_path)

                # Instantiate the ChatOpenAI model
                openai_api_key = os.getenv('OPENAI_API_KEY')
                model = ChatOpenAI(openai_api_key=openai_api_key)

                # Send resume text to ChatGPT and update user record with the response
                response_data = get_resume_analysis(model, resume_text)

                # Print the response data for debugging
                logger.info("Response Data: %s", response_data)

                resume = Resume(
                    user_id=user.id,
                    username=username,
                    email=email,
                    file_uploaded=filename,
                    header_text=response_data.get('header_text', ''),
                    top_section_summary=response_data.get('top_section_summary', ''),
                    top_section_list_of_achievements=response_data.get('top_section_list_of_achievements', []),
                    education=response_data.get('education', ''),
                    bottom_section_list_of_achievements=response_data.get('bottom_section_list_of_achievements', []),
                    achievements_and_awards=response_data.get('achievements_and_awards', []),
                    key_technical_skills=response_data.get('key_technical_skills', []),
                    key_soft_skills=response_data.get('key_soft_skills', []),
                    top_listed_skill_keyword=response_data.get('top_listed_skill_keyword', ''),
                    second_most_top_listed_skill_keyword=response_data.get('second_most_top_listed_skill_keyword', ''),
                    third_most_top_listed_skill_keyword=response_data.get('third_most_top_listed_skill_keyword', ''),
                    fourth_most_top_listed_skill_keyword=response_data.get('fourth_most_top_listed_skill_keyword', ''),
                    certifications_and_awards=response_data.get('certifications_and_awards', []),
                    most_recent_successful_project=response_data.get('most_recent_successful_project', ''),
                    areas_for_improvement=response_data.get('areas_for_improvement', ''),
                    questions_about_experience=response_data.get('questions_about_experience', ''),
                    resume_length=response_data.get('resume_length', ''),
                    top_challenge=response_data.get('top_challenge', '')
                )

                # Handle job titles with checks for None
                for i in range(1, 7):
                    job_key = f'job_title_{i}'
                    if job_key in response_data and response_data[job_key] is not None:
                        job_data = response_data[job_key]
                        setattr(resume, job_key, job_data.get('title', ''))
                        setattr(resume, f'{job_key}_start_date', job_data.get('start_date'))
                        setattr(resume, f'{job_key}_end_date', job_data.get('end_date'))
                        setattr(resume, f'{job_key}_length', job_data.get('length', ''))
                        setattr(resume, f'{job_key}_location', job_data.get('location', ''))
                        setattr(resume, f'{job_key}_description', job_data.get('description', ''))

                session.add(resume)
                session.commit()

                # Delete the resume file after successfully writing data to the database
                if os.path.exists(file_path):
                    os.remove(file_path)

                flash('User registered successfully')
                return redirect(url_for('auth.login'))
            else:
                # If no resume is uploaded, redirect with a message
                flash('User registered successfully. Please log in and upload your resume from the user portal.')
                return redirect(url_for('auth.login'))
        except Exception as e:
            logger.error("Error processing signup: %s", str(e))
            session.rollback()  # Rollback any changes on error
            existing_user = get_user_by_email(email)
            if existing_user:
                flash('It looks like I ran into an issue processing your resume, however, your username was created. Please feel free to login and resubmit your resume from the user portal.')
            else:
                flash('We encountered an unexpected error. Please try again or contact support.')
            return redirect(url_for('auth.signup'))
        finally:
            session.close()
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
