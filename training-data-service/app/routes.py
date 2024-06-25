import os
import threading
import logging
from flask import render_template, request, redirect, url_for, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
from app.database import get_db
from app.models import JobDescriptionAnalysis, ProcessStatus, User
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

            with app.app_context():
                db_session = next(get_db())
                user_data_count = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).count()

                if user_data_count > 0:
                    return jsonify({'error': 'A job listing is already stored. If you would like to add another then please delete the existing job listing first.'}), 400

            files = request.files.getlist('files')
            if not files:
                raise ValueError("No files part")

            for file in files:
                filename = secure_filename(file.filename)
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
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
                    logging.debug(f"Skipping unsupported file type: {filename}")

            return jsonify({'pending': 'File processing started'}), 202
        except Exception as e:
            logging.error(f"Exception in file_upload: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/raw_text_submission', methods=['POST'])
    def raw_text_submission():
        try:
            user_id = request.form.get('user_id')
            raw_text = request.form.get('raw_text')

            with app.app_context():
                db_session = next(get_db())
                user_data_count = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).count()

                if user_data_count > 0:
                    return jsonify({'error': 'A job listing is already stored. If you would like to add another then please delete the existing job listing first.'}), 400

            threading.Thread(target=process_text, args=(current_app._get_current_object(), raw_text, user_id)).start()
            return jsonify({'pending': 'Raw text submission started successfully'}), 202
        except Exception as e:
            logging.error(f"Exception in raw_text_submission: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/job-description-analysis/delete', methods=['DELETE'])
    def delete_selected_files():
        try:
            data = request.json
            ids = data.get('ids', [])

            if not ids or 'undefined' in ids:
                raise ValueError("Invalid ID value(s)")

            with app.app_context():
                db_session = next(get_db())
                db_session.query(JobDescriptionAnalysis).filter(JobDescriptionAnalysis.id.in_(ids)).delete(synchronize_session=False)
                db_session.commit()
            return jsonify({'success': True})
        except Exception as e:
            logging.error(f"Failed to delete selected files: {str(e)}")
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

    @app.route('/api/job-description-analysis/<int:user_id>', methods=['GET'])
    def get_job_description(user_id):
        try:
            with app.app_context():
                db_session = next(get_db())
                job_descriptions = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).all()
                logging.debug(f"Job descriptions fetched for user {user_id}: {job_descriptions}")
                response_data = [{
                    'id': job_description.id,  # Include the id field
                    'job_title': job_description.job_title,
                    'job_level': job_description.job_level,
                    'job_location': job_description.job_location,
                    'job_type': job_description.job_type,
                    'job_salary': job_description.job_salary,
                    'job_responsibilities': job_description.job_responsibilities,
                    'personal_qualifications': job_description.personal_qualifications,
                    'company_name': job_description.company_name,
                    'company_size': job_description.company_size,
                    'company_industry': job_description.company_industry,
                    'company_mission_and_values': job_description.company_mission_and_values,
                    'education_background': job_description.education_background,
                    'required_professional_experiences': job_description.required_professional_experiences,
                    'nice_to_have_experiences': job_description.nice_to_have_experiences,
                    'required_skill_sets': job_description.required_skill_sets
                } for job_description in job_descriptions]
                logging.debug(f"Response data for user {user_id}: {response_data}")
                return jsonify(response_data)
        except Exception as e:
            logging.error(f"Failed to fetch job description for user {user_id}: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/job-description-details/<int:user_id>', methods=['GET'])
    def get_job_description_details(user_id):
        try:
            with app.app_context():
                db_session = next(get_db())
                job_descriptions = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).all()
                
                response_data = {
                    'job_titles': list(set([jd.job_title for jd in job_descriptions])),
                    'company_names': list(set([jd.company_name for jd in job_descriptions])),
                    'industries': list(set([jd.company_industry for jd in job_descriptions])),
                }
                
                return jsonify(response_data)
        except Exception as e:
            logging.error(f"Failed to fetch job description details for user {user_id}: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/job-description-analysis/<int:user_id>', methods=['PUT'])
    def update_job_description(user_id):
        try:
            data = request.json
            logging.debug(f"Data received for update: {data}")

            with app.app_context():
                db_session = next(get_db())
                job_description = db_session.query(JobDescriptionAnalysis).filter_by(user_id=user_id).first()

                if not job_description:
                    return jsonify({'error': 'Job description not found'}), 404

                job_description.job_title = data.get('job_title', job_description.job_title)
                job_description.job_level = data.get('job_level', job_description.job_level)
                job_description.job_location = data.get('job_location', job_description.job_location)
                job_description.job_type = data.get('job_type', job_description.job_type)
                job_description.job_salary = data.get('job_salary', job_description.job_salary)
                job_description.job_responsibilities = data.get('job_responsibilities', job_description.job_responsibilities)
                job_description.personal_qualifications = data.get('personal_qualifications', job_description.personal_qualifications)
                job_description.company_name = data.get('company_name', job_description.company_name)
                job_description.company_size = data.get('company_size', job_description.company_size)
                job_description.company_industry = data.get('company_industry', job_description.company_industry)
                job_description.company_mission_and_values = data.get('company_mission_and_values', job_description.company_mission_and_values)
                job_description.education_background = data.get('education_background', job_description.education_background)
                job_description.required_professional_experiences = data.get('required_professional_experiences', job_description.required_professional_experiences)
                job_description.nice_to_have_experiences = data.get('nice_to_have_experiences', job_description.nice_to_have_experiences)
                job_description.required_skill_sets = data.get('required_skill_sets', job_description.required_skill_sets)

                db_session.commit()

            return jsonify({'success': True}), 200
        except Exception as e:
            logging.error(f"Failed to update job description: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/edit_job_listing.html')
    def edit_job_listing():
        username = request.args.get('username')
        user_id = request.args.get('user_id')

        if not username or not user_id:
            return "Missing username or user_id parameters", 400

        return render_template('edit_job_listing.html', username=username, user_id=user_id)

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

    @app.route('/api/user/<int:user_id>', methods=['GET'])
    def get_user(user_id):
        try:
            with app.app_context():
                db_session = next(get_db())
                user = db_session.query(User).filter_by(id=user_id).first()

                if not user:
                    return jsonify({'error': 'User not found'}), 404

                user_data = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'resume_text_full': user.resume_text_full,
                    'key_technical_skills': user.key_technical_skills,
                    'key_soft_skills': user.key_soft_skills,
                    'most_recent_job_title': user.most_recent_job_title,
                    'second_most_recent_job_title': user.second_most_recent_job_title,
                    'most_recent_job_title_summary': user.most_recent_job_title_summary,
                    'second_most_recent_job_title_summary': user.second_most_recent_job_title_summary,
                    'top_listed_skill_keyword': user.top_listed_skill_keyword,
                    'second_most_top_listed_skill_keyword': user.second_most_top_listed_skill_keyword,
                    'third_most_top_listed_skill_keyword': user.third_most_top_listed_skill_keyword,
                    'fourth_most_top_listed_skill_keyword': user.fourth_most_top_listed_skill_keyword,
                    'educational_background': user.educational_background,
                    'certifications_and_awards': user.certifications_and_awards,
                    'most_recent_successful_project': user.most_recent_successful_project,
                    'areas_for_improvement': user.areas_for_improvement,
                    'questions_about_experience': user.questions_about_experience,
                    'resume_length': user.resume_length,
                    'top_challenge': user.top_challenge,
                    'created_at': user.created_at
                }

                return jsonify(user_data)
        except Exception as e:
            logging.error(f"Failed to fetch user data for user {user_id}: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/edit_resume.html')
    def edit_resume():
        username = request.args.get('username')
        user_id = request.args.get('user_id')

        if not username or not user_id:
            return "Missing username or user_id parameters", 400

        return render_template('edit_resume.html', username=username, user_id=user_id)

    @app.route('/api/resume-data/<int:user_id>', methods=['GET'])
    def get_resume_data(user_id):
        try:
            with app.app_context():
                db_session = next(get_db())
                user = db_session.query(User).filter_by(id=user_id).first()
                if not user:
                    return jsonify({'error': 'User not found'}), 404

                response_data = {
                    'key_technical_skills': user.key_technical_skills,
                    'key_soft_skills': user.key_soft_skills,
                    'most_recent_job_title': user.most_recent_job_title,
                    'second_most_recent_job_title': user.second_most_recent_job_title,
                    'most_recent_job_title_summary': user.most_recent_job_title_summary,
                    'second_most_recent_job_title_summary': user.second_most_recent_job_title_summary,
                    'top_listed_skill_keyword': user.top_listed_skill_keyword,
                    'second_most_top_listed_skill_keyword': user.second_most_top_listed_skill_keyword,
                    'third_most_top_listed_skill_keyword': user.third_most_top_listed_skill_keyword,
                    'fourth_most_top_listed_skill_keyword': user.fourth_most_top_listed_skill_keyword,
                    'educational_background': user.educational_background,
                    'certifications_and_awards': user.certifications_and_awards,
                    'most_recent_successful_project': user.most_recent_successful_project,
                    'areas_for_improvement': user.areas_for_improvement,
                    'questions_about_experience': user.questions_about_experience,
                    'resume_length': user.resume_length,
                    'top_challenge': user.top_challenge
                }

                return jsonify(response_data)
        except Exception as e:
            logging.error(f"Failed to fetch resume data for user {user_id}: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/resume-data/<int:user_id>', methods=['PUT'])
    def update_resume_data(user_id):
        try:
            data = request.json

            with app.app_context():
                db_session = next(get_db())
                user = db_session.query(User).filter_by(id=user_id).first()

                if not user:
                    return jsonify({'error': 'User not found'}), 404

                user.key_technical_skills = data.get('key_technical_skills', user.key_technical_skills)
                user.key_soft_skills = data.get('key_soft_skills', user.key_soft_skills)
                user.most_recent_job_title = data.get('most_recent_job_title', user.most_recent_job_title)
                user.second_most_recent_job_title = data.get('second_most_recent_job_title', user.second_most_recent_job_title)
                user.most_recent_job_title_summary = data.get('most_recent_job_title_summary', user.most_recent_job_title_summary)
                user.second_most_recent_job_title_summary = data.get('second_most_recent_job_title_summary', user.second_most_recent_job_title_summary)
                user.top_listed_skill_keyword = data.get('top_listed_skill_keyword', user.top_listed_skill_keyword)
                user.second_most_top_listed_skill_keyword = data.get('second_most_top_listed_skill_keyword', user.second_most_top_listed_skill_keyword)
                user.third_most_top_listed_skill_keyword = data.get('third_most_top_listed_skill_keyword', user.third_most_top_listed_skill_keyword)
                user.fourth_most_top_listed_skill_keyword = data.get('fourth_most_top_listed_skill_keyword', user.fourth_most_top_listed_skill_keyword)
                user.educational_background = data.get('educational_background', user.educational_background)
                user.certifications_and_awards = data.get('certifications_and_awards', user.certifications_and_awards)
                user.most_recent_successful_project = data.get('most_recent_successful_project', user.most_recent_successful_project)
                user.areas_for_improvement = data.get('areas_for_improvement', user.areas_for_improvement)
                user.questions_about_experience = data.get('questions_about_experience', user.questions_about_experience)
                user.resume_length = data.get('resume_length', user.resume_length)
                user.top_challenge = data.get('top_challenge', user.top_challenge)

                db_session.commit()

            return jsonify({'success': True}), 200
        except Exception as e:
            logging.error(f"Failed to update resume data: {str(e)}")
            return jsonify({'error': str(e)}), 500