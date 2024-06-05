from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os
import logging
import numpy as np  # Add this line to import numpy
from .models import User, SessionLocal, EmbeddingIDMapping  # Ensure EmbeddingIDMapping is imported
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
            user = User(username=username, email=email)
            user.set_password(password)
            user.resume_embeddings = embeddings.tobytes()
            session.add(user)
            session.commit()
            store_embeddings_and_mappings(session, user, embeddings, 'users', chunks)
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

@auth_bp.route('/view_resume_chunks', methods=['GET'])
@login_required
def view_resume_chunks():
    session = SessionLocal()
    try:
        logging.debug("Fetching user data from database")
        user = session.query(User).filter_by(username=current_user.username).first()
        if user:
            logging.debug(f"User found: {user.username}")
            if user.resume_embeddings:
                logging.debug("Resume embeddings found")
                embedding_array = np.frombuffer(user.resume_embeddings, dtype='float32').reshape(-1, 1536)
                chunks = session.query(EmbeddingIDMapping).filter_by(db_id=user.id).order_by(EmbeddingIDMapping.faiss_id).all()
                chunk_texts = [chunk.chunk_text for chunk in chunks]

                # Prepare data for rendering
                chunk_embedding_pairs = list(zip(chunk_texts, embedding_array.tolist()))

                return render_template('view_chunks.html', chunk_embedding_pairs=chunk_embedding_pairs)
            else:
                logging.debug("No resume embeddings found for user")
                return jsonify({"error": "No resume embeddings found."})
        else:
            logging.debug("User not found")
            return jsonify({"error": "User not found."})
    except Exception as e:
        logging.error(f"Error in view_chunks: {e}")
        return jsonify({"error": str(e)})
    finally:
        session.close()
