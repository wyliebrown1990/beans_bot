from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os
from .models import User, SessionLocal
from .utils import get_user_by_username, get_user_by_email, allowed_file, create_chunks_and_embeddings_from_file, store_embeddings_and_mappings
from . import login_manager  # Import login_manager

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
            flash('Looks like you used the wrong password. Please try again.')
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
            chunks, embeddings = create_chunks_and_embeddings_from_file(file_path, current_app.config['OPENAI_API_KEY'])
            user = User(
                username=username, 
                email=email,
                resume_embeddings=embeddings.tobytes(),
                resume_data='\n'.join(chunks),  # Store the extracted text data
                processed_files=filename  # Store the uploaded file name
            )
            user.set_password(password)
            store_embeddings_and_mappings(session, user, embeddings, 'users')
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
