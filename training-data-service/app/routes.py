import os
import threading
import logging
from flask import render_template, request, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from app import app
from app.database import get_db
from app.models import TrainingData, ProcessStatus
from app.utils import (
    load_training_data, generate_summary, store_training_data,
    process_raw_text, process_file, cleanup_uploads_folder,
    get_video_urls_from_channel, sanitize_filename, download_and_transcribe,
    transcribe_videos, process_youtube_urls, update_process_status
)
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
    user_id = request.form['user_id']
    channel_id = request.form['channel_id']
    num_videos = int(request.form['num_videos'])

    with app.app_context():
        db = next(get_db())
        user_data_count = db.query(TrainingData).filter_by(user_id=user_id).count()
        
        if user_data_count >= 5:
            return jsonify({'error': 'You have reached the limit of 5 uploads. Please delete some files before uploading more.'}), 400

    threading.Thread(target=transcribe_videos, args=(channel_id, num_videos, job_title.lower().strip(), company_name.lower().strip(), username, user_id)).start()
    return jsonify({'success': 'Transcription started successfully'}), 200


@app.route('/youtube_urls_transcription', methods=['POST'])
def youtube_urls_transcription():
    job_title = request.form['job_title']
    company_name = request.form['company_name']
    industry = request.form['industry']
    username = request.form['username']
    user_id = request.form['user_id']
    youtube_urls = request.form['youtube_urls'].strip().split('\n')
    youtube_urls = [url.strip() for url in youtube_urls if url.strip()]

    with app.app_context():
        db = next(get_db())
        user_data_count = db.query(TrainingData).filter_by(user_id=user_id).count()
        
        if user_data_count >= 5:
            return jsonify({'error': 'You have reached the limit of 5 uploads. Please delete some files before uploading more.'}), 400

    threading.Thread(target=process_youtube_urls, args=(youtube_urls, job_title, company_name, username, user_id)).start()
    return jsonify({'success': 'YouTube URLs transcription started successfully'}), 200



@app.route('/file_upload', methods=['POST'])
def file_upload():
    job_title = request.form['job_title']
    company_name = request.form['company_name']
    industry = request.form['industry']
    username = request.form['username']
    user_id = request.form['user_id']

    print(f"DEBUG: file_upload - Received data: job_title={job_title}, company_name={company_name}, industry={industry}, username={username}, user_id={user_id}")

    with app.app_context():
        db = next(get_db())
        user_data_count = db.query(TrainingData).filter_by(user_id=user_id).count()

        if user_data_count >= 5:
            return jsonify({'error': 'You have reached the limit of 5 uploads. Please delete some files before uploading more.'}), 400

    files = request.files.getlist('files')

    for file in files:
        if file and file.filename.endswith('.txt'):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            threading.Thread(target=process_file, args=(file_path, job_title, company_name, username, user_id)).start()

    return jsonify({'success': 'Files uploaded successfully'}), 200


@app.route('/raw_text_submission', methods=['POST'])
def raw_text_submission():
    job_title = request.form['job_title']
    company_name = request.form['company_name']
    industry = request.form['industry']
    username = request.form['username']
    user_id = request.form['user_id']
    raw_text = request.form['raw_text']

    with app.app_context():
        db = next(get_db())
        user_data_count = db.query(TrainingData).filter_by(user_id=user_id).count()
        
        if user_data_count >= 5:
            return jsonify({'error': 'You have reached the limit of 5 uploads. Please delete some files before uploading more.'}), 400

    threading.Thread(target=process_raw_text, args=(job_title, company_name, raw_text, username, user_id)).start()
    return jsonify({'success': 'Raw text submission started successfully'}), 200


@app.route('/progress')
def progress():
    job_title = request.args.get('job_title')
    company_name = request.args.get('company_name')
    industry = request.args.get('industry')
    username = request.args.get('username')
    user_id = request.args.get('user_id')
    
    print(f"DEBUG: progress - Received query params: job_title={job_title}, company_name={company_name}, industry={industry}, username={username}, user_id={user_id}")

    return render_template('progress.html', job_title=job_title, company_name=company_name, industry=industry, username=username, user_id=user_id)


@app.route('/upload_options', methods=['GET'])
def upload_options():
    job_title = request.args.get('job_title').lower().strip()
    company_name = request.args.get('company_name').lower().strip()
    industry = request.args.get('industry')
    username = request.args.get('username')
    user_id = request.args.get('user_id')

    print(f"DEBUG: upload_options - Received query params: job_title={job_title}, company_name={company_name}, industry={industry}, username={username}, user_id={user_id}")

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

    return render_template('upload_options.html', job_title=job_title, company_name=company_name, industry=industry, username=username, user_id=user_id, message=message)

@app.route('/api/training-data/<int:user_id>', methods=['GET'])
def get_training_data(user_id):
    print(f"Route /api/training-data/{user_id} hit")
    try:
        with app.app_context():
            db_session = next(get_db())
            print(f"DB session established for user ID: {user_id}")
            training_data = db_session.query(TrainingData).filter_by(user_id=user_id).all()
            print(f"Training data fetched: {training_data}")
            response_data = [
                {
                    'id': data.id,
                    'processed_files': data.processed_files
                } for data in training_data
            ]
            print(f"Response data: {response_data}")
            return jsonify(response_data)
    except Exception as e:
        logging.error(f"Failed to fetch training data for user {user_id}: {str(e)}")
        print(f"Exception occurred: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/training-data/delete', methods=['DELETE'])
def delete_selected_files():
    try:
        data = request.json
        ids = data.get('ids', [])
        print(f"Deleting files with IDs: {ids}")

        with app.app_context():
            db_session = next(get_db())
            db_session.query(TrainingData).filter(TrainingData.id.in_(ids)).delete(synchronize_session=False)
            db_session.commit()
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Failed to delete selected files: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/training-data/delete-all/<int:user_id>', methods=['DELETE'])
def delete_all_files(user_id):
    try:
        print(f"Deleting all files for user ID: {user_id}")

        with app.app_context():
            db_session = next(get_db())
            db_session.query(TrainingData).filter_by(user_id=user_id).delete(synchronize_session=False)
            db_session.commit()
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Failed to delete all files for user {user_id}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/', methods=['GET', 'POST'])
def index():
   username = request.args.get('username')
   user_id = request.args.get('user_id')
   if request.method == 'POST':
       job_title = request.form['job_title'].lower().strip()
       company_name = request.form['company_name'].lower().strip()
       industry = request.form['industry']
       username = request.form['username']
       user_id = request.form['user_id']

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

       return redirect(url_for('upload_options', job_title=job_title, company_name=company_name, industry=industry, username=username, user_id=user_id))

   return render_template('index.html', username=username, user_id=user_id)