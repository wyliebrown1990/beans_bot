import os
import threading
import logging
from flask import render_template, request, redirect, url_for, jsonify, current_app
from werkzeug.utils import secure_filename
from app.database import get_db
from app.models import JobDescriptionAnalysis, ProcessStatus
from app.utils import process_file, process_text, cleanup_uploads_folder, update_process_status
from sqlalchemy import func
import fitz  # PyMuPDF for PDF processing
import docx

logging.basicConfig(level=logging.DEBUG)

def extract_text_from_pdf(file_path):
    text = ""
    doc = fitz.open(file_path)
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text += page.get_text()
    return text

def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

def setup_routes(app, db_session):

    @app.route('/file_upload', methods=['POST'])
    def file_upload():
        try:
            user_id = request.form.get('user_id')
            if not user_id:
                raise ValueError("Missing user_id")

            files = request.files.getlist('files')
            if not files:
                raise ValueError("No files part")

            for file in files:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

                if filename.endswith('.txt'):
                    with open(file_path, 'r') as f:
                        file_content = f.read()
                    threading.Thread(target=process_text, args=(current_app._get_current_object(), file_content, user_id)).start()
                elif filename.endswith('.pdf'):
                    file_content = extract_text_from_pdf(file_path)
                    threading.Thread(target=process_text, args=(current_app._get_current_object(), file_content, user_id)).start()
                elif filename.endswith('.docx'):
                    file_content = extract_text_from_docx(file_path)
                    threading.Thread(target=process_text, args=(current_app._get_current_object(), file_content, user_id)).start()
                else:
                    print(f"DEBUG: Skipping unsupported file type: {filename}")

            return jsonify({'pending': 'File processing started'}), 202
        except Exception as e:
            print(f"ERROR: Exception in file_upload - {str(e)}")
            return jsonify({'error': str(e)}), 500


    @app.route('/raw_text_submission', methods=['POST'])
    def raw_text_submission():
        try:
            user_id = request.form['user_id']
            raw_text = request.form['raw_text']

            with app.app_context():
                db = next(get_db())
                user_data_count = db.query(JobDescriptionAnalysis).filter_by(user_id=user_id).count()

                if user_data_count >= 5:
                    return jsonify({'error': 'You have reached the limit of 5 uploads. Please delete some files before uploading more.'}), 400

            threading.Thread(target=process_text, args=(current_app._get_current_object(), raw_text, user_id)).start()
            return jsonify({'pending': 'Raw text submission started successfully'}), 202
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/job-description-analysis/delete', methods=['DELETE'])
    def delete_selected_files():
        try:
            data = request.json
            ids = data.get('ids', [])

            with app.app_context():
                db_session = next(get_db())
                db_session.query(JobDescriptionAnalysis).filter(JobDescriptionAnalysis.id.in_(ids)).delete(synchronize_session=False)
                db_session.commit()
            return jsonify({'success': True})
        except Exception as e:
            logging.error(f"Failed to delete selected files: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/job-description-analysis/delete-all/<int:user_id>', methods=['DELETE'])
    def delete_all_files(user_id):
        try:
            with app.app_context():
                db_session = next(get_db())
                db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).delete(synchronize_session=False)
                db_session.commit()
            return jsonify({'success': True})
        except Exception as e:
            logging.error(f"Failed to delete all files for user {user_id}: {str(e)}")
            return jsonify({'error': str(e)}), 500
        
    @app.route('/', methods=['GET', 'POST'])
    def index():
        username = request.args.get('username')
        user_id = request.args.get('user_id')

        if not username or not user_id:
            return "Missing username or user_id parameters", 400

        if request.method == 'POST':
            job_title = request.form['job_title'].lower().strip()
            company_name = request.form['company_name'].lower().strip()
            industry = request.form['industry']
            username = request.form['username']
            user_id = request.form['user_id']

            with app.app_context():
                db = next(get_db())
                analysis_data_exists = db.query(JobDescriptionAnalysis).filter(
                    func.lower(JobDescriptionAnalysis.job_title) == job_title,
                    func.lower(JobDescriptionAnalysis.company_name) == company_name
                ).first() is not None

            if analysis_data_exists:
                message = f"It looks like I already have analysis data on the {job_title} job at {company_name} company. Feel free to add more or proceed to interview now."
            else:
                message = f"It looks like I don't have any analysis data on the {job_title} job at {company_name} company. If you want a more targeted interview please add more, otherwise, feel free to move onto a more generic interview experience."

            return render_template('index.html', username=username, user_id=user_id, message=message)

        return render_template('index.html', username=username, user_id=user_id)

    @app.route('/api/job-description/<int:user_id>', methods=['GET'])
    def get_job_description(user_id):
        try:
            with app.app_context():
                db_session = next(get_db())
                job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()
                if job_description:
                    response_data = {
                        'job_title': job_description.job_title,
                        'company_name': job_description.company_name,
                        'industry': job_description.company_industry
                    }
                else:
                    response_data = {
                        'job_title': '',
                        'company_name': '',
                        'industry': ''
                    }
                return jsonify(response_data)
        except Exception as e:
            logging.error(f"Failed to fetch job description for user {user_id}: {str(e)}")
            return jsonify({'error': str(e)}), 500
        
    @app.route('/update_status', methods=['POST'])
    def update_status():
        try:
            data = request.get_json()
            user_id = data.get('user_id')
            status = data.get('status')

            if not user_id or not status:
                raise ValueError("Missing user_id or status")

            # Logic to update status in the database
            print(f"Updated status for user_id: {user_id} to {status}")

            return jsonify({'success': True}), 200
        except Exception as e:
            print(f"ERROR: Exception in update_status - {str(e)}")
            return jsonify({'error': str(e)}), 500
