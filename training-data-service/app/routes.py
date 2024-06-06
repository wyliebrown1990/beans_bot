import os
import threading
import logging
from flask import render_template, request, redirect, url_for, jsonify
from app import app
from app.database import get_db
from app.models import TrainingData, ProcessStatus
from app.utils import secure_filename, load_training_data, create_chunks_and_embeddings_from_file, create_chunks_and_embeddings, store_training_data, process_raw_text, process_file, cleanup_uploads_folder, get_video_urls_from_channel, sanitize_filename, download_and_transcribe, transcribe_videos, process_youtube_urls
from sqlalchemy import func

logging.basicConfig(level=logging.DEBUG)

# Additional routes for process status updates
@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.json
    username = data.get('username')
    job_title = data.get('job_title')
    company_name = data.get('company_name')
    status = data.get('status')

    print(f"Received status update for user: {username}, job: {job_title}, company: {company_name} to status: {status}")

    with app.app_context():
        db = next(get_db())
        process_status = db.query(ProcessStatus).filter_by(username=username, job_title=job_title, company_name=company_name).first()
        if process_status:
            process_status.status = status
        else:
            process_status = ProcessStatus(username=username, job_title=job_title, company_name=company_name, status=status)
            db.add(process_status)
        db.commit()
    return jsonify({'status': 'success'})


@app.route('/get_status', methods=['GET'])
def get_status():
    username = request.args.get('username').lower().strip()
    job_title = request.args.get('job_title').lower().strip()
    company_name = request.args.get('company_name').lower().strip()

    print(f"Fetching status for user: {username}, job: {job_title}, company: {company_name}")

    with app.app_context():
        db = next(get_db())
        process_status = db.query(ProcessStatus).filter_by(username=username, job_title=job_title, company_name=company_name).first()
        if process_status:
            print(f"Status found: {process_status.status}")
            return jsonify({'status': process_status.status})
        else:
            print("No status found")
            return jsonify({'status': 'No status found'})


@app.route('/youtube_transcription', methods=['POST'])
def youtube_transcription():
   job_title = request.form['job_title']
   company_name = request.form['company_name']
   industry = request.form['industry']
   username = request.form['username']
   channel_id = request.form['channel_id']
   num_videos = int(request.form['num_videos'])
   threading.Thread(target=transcribe_videos, args=(channel_id, num_videos, job_title.lower().strip(), company_name.lower().strip(), username)).start()
   return redirect(url_for('progress', job_title=job_title.lower().strip(), company_name=company_name.lower().strip(), industry=industry.lower().strip(), username=username))

@app.route('/youtube_urls_transcription', methods=['POST'])
def youtube_urls_transcription():
   job_title = request.form['job_title']
   company_name = request.form['company_name']
   industry = request.form['industry']
   username = request.form['username']
   youtube_urls = request.form['youtube_urls'].strip().split('\n')
   youtube_urls = [url.strip() for url in youtube_urls if url.strip()]
   threading.Thread(target=process_youtube_urls, args=(youtube_urls, job_title, company_name, username)).start()
   return redirect(url_for('progress', job_title=job_title.lower().strip(), company_name=company_name.lower().strip(), industry=industry.lower().strip(), username=username))

@app.route('/file_upload', methods=['POST'])
def file_upload():
   job_title = request.form['job_title']
   company_name = request.form['company_name']
   industry = request.form['industry']
   username = request.form['username']
   files = request.files.getlist('files')

   for file in files:
       if file and file.filename.endswith('.txt'):
           filename = secure_filename(file.filename)
           file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
           file.save(file_path)
           threading.Thread(target=process_file, args=(file_path, job_title, company_name, username)).start()

   return redirect(url_for('progress', job_title=job_title, company_name=company_name, industry=industry, username=username))

@app.route('/raw_text_submission', methods=['POST'])
def raw_text_submission():
   job_title = request.form['job_title']
   company_name = request.form['company_name']
   industry = request.form['industry']
   username = request.form['username']
   raw_text = request.form['raw_text']
   threading.Thread(target=process_raw_text, args=(job_title, company_name, raw_text, username)).start()
   return redirect(url_for('progress', job_title=job_title, company_name=company_name, industry=industry, username=username))

@app.route('/progress')
def progress():
   job_title = request.args.get('job_title')
   company_name = request.args.get('company_name')
   industry = request.args.get('industry')
   username = request.args.get('username')
   print(f"Rendering progress page for {job_title} at {company_name}")
   return render_template('progress.html', job_title=job_title, company_name=company_name, industry=industry, username=username)

@app.route('/upload_options', methods=['GET'])
def upload_options():
    job_title = request.args.get('job_title').lower().strip()
    company_name = request.args.get('company_name').lower().strip()
    industry = request.args.get('industry')
    username = request.args.get('username')

    with app.app_context():
        db = next(get_db())
        training_data_exists = db.query(TrainingData).filter(
            func.lower(TrainingData.job_title) == job_title,
            func.lower(TrainingData.company_name) == company_name
        ).first() is not None

    if training_data_exists:
        message = f"It looks like I already have training data on the {job_title} job at {company_name} company. Feel free to add more or proceed to interview now."
    else:
        message = f"It looks like I don't have any training data on the {job_title} job at {company_name} company. If you want a more targeted interview please add more, otherwise, feel free to move onto a more generic interview experience."

    return render_template('upload_options.html', job_title=job_title, company_name=company_name, industry=industry, username=username, message=message)


@app.route('/', methods=['GET', 'POST'])
def index():
    username = request.args.get('username')
    if request.method == 'POST':
        job_title = request.form['job_title'].lower().strip()
        company_name = request.form['company_name'].lower().strip()
        industry = request.form['industry']
        username = request.form['username']  # Ensure username is taken from the form

        with app.app_context():
            db = next(get_db())
            training_data_exists = db.query(TrainingData).filter(
                func.lower(TrainingData.job_title) == job_title,
                func.lower(TrainingData.company_name) == company_name
            ).first() is not None

        if training_data_exists:
            message = f"It looks like I already have training data on the {job_title} job at {company_name} company. Feel free to add more or proceed to interview now."
        else:
            message = f"It looks like I don't have any training data on the {job_title} job at {company_name} company. If you want a more targeted interview please add more, otherwise, feel free to move onto a more generic interview experience."

        return redirect(url_for('upload_options', job_title=job_title, company_name=company_name, industry=industry, username=username))

    return render_template('index.html', username=username)
