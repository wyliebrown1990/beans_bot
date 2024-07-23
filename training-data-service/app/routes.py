import os
import threading
import logging
from flask import render_template, request, redirect, url_for, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
from app.database import get_db
from app.models import JobDescriptions, Users, Questions, Resumes
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
                user_data_count = db_session.query(JobDescriptions).filter_by(user_id=user_id).count()

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
                user_data_count = db_session.query(JobDescriptions).filter_by(user_id=user_id).count()

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
                db_session.query(JobDescriptions).filter(JobDescriptions.id.in_(ids)).delete(synchronize_session=False)
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
                job_descriptions = db_session.query(JobDescriptions).filter_by(user_id=user_id).all()
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
                    'Required_technical_skills': job_description.Required_technical_skills,
                    'Required_soft_skills': job_description.Required_soft_skills,
                    'company_name': job_description.company_name,
                    'company_size': job_description.company_size,
                    'company_industry': job_description.company_industry,
                    'company_mission_and_values': job_description.company_mission_and_values,
                    'education_background': job_description.education_background,
                    'required_professional_experiences': job_description.required_professional_experiences,
                    'nice_to_have_experiences': job_description.nice_to_have_experiences,
                    'required_skill_sets': job_description.required_skill_sets,
                    'keywords_analysis': job_description.keywords_analysis
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
                job_descriptions = db_session.query(JobDescriptions).filter_by(user_id=user_id).all()

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
                job_description = db_session.query(JobDescriptions).filter_by(user_id=user_id).first()

                if not job_description:
                    return jsonify({'error': 'Job description not found'}), 404

                job_description.job_title = data.get('job_title', job_description.job_title)
                job_description.job_level = data.get('job_level', job_description.job_level)
                job_description.job_location = data.get('job_location', job_description.job_location)
                job_description.job_type = data.get('job_type', job_description.job_type)
                job_description.job_salary = data.get('job_salary', job_description.job_salary)
                job_description.job_responsibilities = data.get('job_responsibilities', job_description.job_responsibilities)
                job_description.personal_qualifications = data.get('personal_qualifications', job_description.personal_qualifications)
                job_description.Required_technical_skills = data.get('Required_technical_skills', job_description.Required_technical_skills)
                job_description.Required_soft_skills = data.get('Required_soft_skills', job_description.Required_soft_skills)
                job_description.company_name = data.get('company_name', job_description.company_name)
                job_description.company_size = data.get('company_size', job_description.company_size)
                job_description.company_industry = data.get('company_industry', job_description.company_industry)
                job_description.company_mission_and_values = data.get('company_mission_and_values', job_description.company_mission_and_values)
                job_description.education_background = data.get('education_background', job_description.education_background)
                job_description.required_professional_experiences = data.get('required_professional_experiences', job_description.required_professional_experiences)
                job_description.nice_to_have_experiences = data.get('nice_to_have_experiences', job_description.nice_to_have_experiences)
                job_description.required_skill_sets = data.get('required_skill_sets', job_description.required_skill_sets)
                job_description.keywords_analysis = data.get('keywords_analysis', job_description.keywords_analysis)

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
                    'location_input': user.location_input,
                    'job_situation': user.job_situation,
                    'created_at': user.account_created_at,
                    'resumes': [resume.to_dict() for resume in user.resumes]  # Serialize resumes
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
                resume = db_session.query(Resumes).filter_by(user_id=user_id).first()
                if not resume:
                    return jsonify({'error': 'Resume not found'}), 404

                response_data = {
                    'id': resume.id,
                    'user_id': resume.user_id,
                    'created_at': resume.created_at,
                    'username': resume.username,
                    'email': resume.email,
                    'file_uploaded': resume.file_uploaded,
                    'header_text': resume.header_text,
                    'top_section_summary': resume.top_section_summary,
                    'top_section_list_of_achievements': resume.top_section_list_of_achievements,
                    'education': resume.education,
                    'bottom_section_list_of_achievements': resume.bottom_section_list_of_achievements,
                    'achievements_and_awards': resume.achievements_and_awards,
                    'job_title_1': resume.job_title_1,
                    'job_title_1_start_date': resume.job_title_1_start_date,
                    'job_title_1_end_date': resume.job_title_1_end_date,
                    'job_title_1_length': resume.job_title_1_length,
                    'job_title_1_location': resume.job_title_1_location,
                    'job_title_1_description': resume.job_title_1_description,
                    'job_title_2': resume.job_title_2,
                    'job_title_2_start_date': resume.job_title_2_start_date,
                    'job_title_2_end_date': resume.job_title_2_end_date,
                    'job_title_2_length': resume.job_title_2_length,
                    'job_title_2_location': resume.job_title_2_location,
                    'job_title_2_description': resume.job_title_2_description,
                    'job_title_3': resume.job_title_3,
                    'job_title_3_start_date': resume.job_title_3_start_date,
                    'job_title_3_end_date': resume.job_title_3_end_date,
                    'job_title_3_length': resume.job_title_3_length,
                    'job_title_3_location': resume.job_title_3_location,
                    'job_title_3_description': resume.job_title_3_description,
                    'job_title_4': resume.job_title_4,
                    'job_title_4_start_date': resume.job_title_4_start_date,
                    'job_title_4_end_date': resume.job_title_4_end_date,
                    'job_title_4_length': resume.job_title_4_length,
                    'job_title_4_location': resume.job_title_4_location,
                    'job_title_4_description': resume.job_title_4_description,
                    'job_title_5': resume.job_title_5,
                    'job_title_5_start_date': resume.job_title_5_start_date,
                    'job_title_5_end_date': resume.job_title_5_end_date,
                    'job_title_5_length': resume.job_title_5_length,
                    'job_title_5_location': resume.job_title_5_location,
                    'job_title_5_description': resume.job_title_5_description,
                    'job_title_6': resume.job_title_6,
                    'job_title_6_start_date': resume.job_title_6_start_date,
                    'job_title_6_end_date': resume.job_title_6_end_date,
                    'job_title_6_length': resume.job_title_6_length,
                    'job_title_6_location': resume.job_title_6_location,
                    'job_title_6_description': resume.job_title_6_description,
                    'key_technical_skills': resume.key_technical_skills,
                    'key_soft_skills': resume.key_soft_skills,
                    'top_listed_skill_keyword': resume.top_listed_skill_keyword,
                    'second_most_top_listed_skill_keyword': resume.second_most_top_listed_skill_keyword,
                    'third_most_top_listed_skill_keyword': resume.third_most_top_listed_skill_keyword,
                    'fourth_most_top_listed_skill_keyword': resume.fourth_most_top_listed_skill_keyword,
                    'certifications_and_awards': resume.certifications_and_awards,
                    'most_recent_successful_project': resume.most_recent_successful_project,
                    'areas_for_improvement': resume.areas_for_improvement,
                    'questions_about_experience': resume.questions_about_experience,
                    'resume_length': resume.resume_length,
                    'top_challenge': resume.top_challenge
                }

                return jsonify(response_data), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500



    @app.route('/api/resume-data/<int:user_id>', methods=['PUT'])
    def update_resume_data(user_id):
        try:
            data = request.json

            with app.app_context():
                db_session = next(get_db())
                resume = db_session.query(Resumes).filter_by(user_id=user_id).first()

                if not resume:
                    return jsonify({'error': 'Resume not found'}), 404

                resume.header_text = data.get('header_text', resume.header_text)
                resume.top_section_summary = data.get('top_section_summary', resume.top_section_summary)
                resume.top_section_list_of_achievements = data.get('top_section_list_of_achievements', resume.top_section_list_of_achievements)
                resume.education = data.get('education', resume.education)
                resume.bottom_section_list_of_achievements = data.get('bottom_section_list_of_achievements', resume.bottom_section_list_of_achievements)
                resume.achievements_and_awards = data.get('achievements_and_awards', resume.achievements_and_awards)
                resume.job_title_1 = data.get('job_title_1', resume.job_title_1)
                resume.job_title_1_start_date = data.get('job_title_1_start_date', resume.job_title_1_start_date)
                resume.job_title_1_end_date = data.get('job_title_1_end_date', resume.job_title_1_end_date)
                resume.job_title_1_length = data.get('job_title_1_length', resume.job_title_1_length)
                resume.job_title_1_location = data.get('job_title_1_location', resume.job_title_1_location)
                resume.job_title_1_description = data.get('job_title_1_description', resume.job_title_1_description)
                resume.job_title_2 = data.get('job_title_2', resume.job_title_2)
                resume.job_title_2_start_date = data.get('job_title_2_start_date', resume.job_title_2_start_date)
                resume.job_title_2_end_date = data.get('job_title_2_end_date', resume.job_title_2_end_date)
                resume.job_title_2_length = data.get('job_title_2_length', resume.job_title_2_length)
                resume.job_title_2_location = data.get('job_title_2_location', resume.job_title_2_location)
                resume.job_title_2_description = data.get('job_title_2_description', resume.job_title_2_description)
                resume.job_title_3 = data.get('job_title_3', resume.job_title_3)
                resume.job_title_3_start_date = data.get('job_title_3_start_date', resume.job_title_3_start_date)
                resume.job_title_3_end_date = data.get('job_title_3_end_date', resume.job_title_3_end_date)
                resume.job_title_3_length = data.get('job_title_3_length', resume.job_title_3_length)
                resume.job_title_3_location = data.get('job_title_3_location', resume.job_title_3_location)
                resume.job_title_3_description = data.get('job_title_3_description', resume.job_title_3_description)
                resume.job_title_4 = data.get('job_title_4', resume.job_title_4)
                resume.job_title_4_start_date = data.get('job_title_4_start_date', resume.job_title_4_start_date)
                resume.job_title_4_end_date = data.get('job_title_4_end_date', resume.job_title_4_end_date)
                resume.job_title_4_length = data.get('job_title_4_length', resume.job_title_4_length)
                resume.job_title_4_location = data.get('job_title_4_location', resume.job_title_4_location)
                resume.job_title_4_description = data.get('job_title_4_description', resume.job_title_4_description)
                resume.job_title_5 = data.get('job_title_5', resume.job_title_5)
                resume.job_title_5_start_date = data.get('job_title_5_start_date', resume.job_title_5_start_date)
                resume.job_title_5_end_date = data.get('job_title_5_end_date', resume.job_title_5_end_date)
                resume.job_title_5_length = data.get('job_title_5_length', resume.job_title_5_length)
                resume.job_title_5_location = data.get('job_title_5_location', resume.job_title_5_location)
                resume.job_title_5_description = data.get('job_title_5_description', resume.job_title_5_description)
                resume.job_title_6 = data.get('job_title_6', resume.job_title_6)
                resume.job_title_6_start_date = data.get('job_title_6_start_date', resume.job_title_6_start_date)
                resume.job_title_6_end_date = data.get('job_title_6_end_date', resume.job_title_6_end_date)
                resume.job_title_6_length = data.get('job_title_6_length', resume.job_title_6_length)
                resume.job_title_6_location = data.get('job_title_6_location', resume.job_title_6_location)
                resume.job_title_6_description = data.get('job_title_6_description', resume.job_title_6_description)
                resume.key_technical_skills = data.get('key_technical_skills', resume.key_technical_skills)
                resume.key_soft_skills = data.get('key_soft_skills', resume.key_soft_skills)
                resume.top_listed_skill_keyword = data.get('top_listed_skill_keyword', resume.top_listed_skill_keyword)
                resume.second_most_top_listed_skill_keyword = data.get('second_most_top_listed_skill_keyword', resume.second_most_top_listed_skill_keyword)
                resume.third_most_top_listed_skill_keyword = data.get('third_most_top_listed_skill_keyword', resume.third_most_top_listed_skill_keyword)
                resume.fourth_most_top_listed_skill_keyword = data.get('fourth_most_top_listed_skill_keyword', resume.fourth_most_top_listed_skill_keyword)
                resume.certifications_and_awards = data.get('certifications_and_awards', resume.certifications_and_awards)
                resume.most_recent_successful_project = data.get('most_recent_successful_project', resume.most_recent_successful_project)
                resume.areas_for_improvement = data.get('areas_for_improvement', resume.areas_for_improvement)
                resume.questions_about_experience = data.get('questions_about_experience', resume.questions_about_experience)
                resume.resume_length = data.get('resume_length', resume.resume_length)
                resume.top_challenge = data.get('top_challenge', resume.top_challenge)

                db_session.commit()

            return jsonify({'success': True}), 200
        except Exception as e:
            logging.error(f"Failed to update resume data: {str(e)}")
            return jsonify({'error': str(e)}), 500

        
    @app.route('/api/questions', methods=['POST'])
    def create_question():
        data = request.json
        with app.app_context():
            db_session = next(get_db())
            new_question = Questions(**data)
            db_session.add(new_question)
            db_session.commit()
            return jsonify({'id': new_question.id, 'message': 'Question created successfully'}), 201

    @app.route('/api/questions', methods=['GET'])
    def get_questions():
        filters = request.args.to_dict()
        with app.app_context():
            db_session = next(get_db())
            query = db_session.query(Questions)
            for key, value in filters.items():
                if hasattr(Questions, key):
                    query = query.filter(getattr(Questions, key) == value)
            questions = query.all()
            return jsonify([q.to_dict() for q in questions])
    
    @app.route('/question_data.html')
    def question_data():
        username = request.args.get('username')
        user_id = request.args.get('user_id')
        return render_template('question_data.html', username=username, user_id=user_id)

    @app.route('/api/questions/<int:question_id>', methods=['PUT'])
    def update_question_route(question_id):
        data = request.json
        with app.app_context():
            db_session = next(get_db())
            updated_question = db_session.query(Questions).filter_by(id=question_id).first()
            if updated_question:
                for key, value in data.items():
                    setattr(updated_question, key, value)
                db_session.commit()
                return jsonify({'message': 'Question updated successfully'}), 200
            return jsonify({'error': 'Question not found'}), 404

    @app.route('/api/questions/<int:question_id>', methods=['DELETE'])
    def delete_question_route(question_id):
        with app.app_context():
            db_session = next(get_db())
            question = db_session.query(Questions).filter_by(id=question_id).first()
            if question:
                db_session.delete(question)
                db_session.commit()
                return jsonify({'message': 'Question deleted successfully'}), 200
            return jsonify({'error': 'Question not found'}), 404
    
    @app.route('/save_interview_history', methods=['POST'])
    def save_interview_history():
        with app.app_context():
            db_session = next(get_db())
            new_history = InterviewHistory(
                session_id=request.json['session_id'],
                user_id=request.json['user_id'],
                # ... other fields ...
            )
            db_session.add(new_history)
            db_session.commit()
        return jsonify({'status': 'success'})
    
    @app.route('/api/interview-history/sessions/<int:user_id>', methods=['GET'])
    def get_interview_sessions(user_id):
        try:
            with app.app_context():
                db_session = next(get_db())
                sessions = db_session.query(
                    InterviewHistory.session_id,
                    func.min(InterviewHistory.created_at).label('date')
                ).filter_by(user_id=user_id).group_by(InterviewHistory.session_id).all()
                
                return jsonify([
                    {'session_id': session.session_id, 'date': session.date.isoformat()}
                    for session in sessions
                ])
        except Exception as e:
            logging.error(f"Error fetching interview sessions: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/interview-history/<int:user_id>/<int:session_id>', methods=['GET'])
    def get_interview_history(user_id, session_id):
        try:
            with app.app_context():
                db_session = next(get_db())
                summary = db_session.query(InterviewHistory).filter_by(
                    user_id=user_id, session_id=session_id
                ).first()
                
                transcript = db_session.query(
                    InterviewHistory.question,
                    InterviewHistory.answer,
                    InterviewHistory.feedback,
                    InterviewHistory.score,
                    InterviewHistory.created_at
                ).filter_by(user_id=user_id, session_id=session_id).order_by(
                    InterviewHistory.created_at, InterviewHistory.id
                ).all()
                
                return jsonify({
                    'summary': {
                        'top_score': summary.session_top_score,
                        'lowest_score': summary.session_low_score,
                        'average_score': summary.session_score_average,
                        'next_steps': summary.session_summary_next_steps
                    },
                    'transcript': [
                        {
                            'question': item.question,
                            'answer': item.answer,
                            'feedback': item.feedback,
                            'score': item.score
                        } for item in transcript
                    ]
                })
        except Exception as e:
            logging.error(f"Error fetching interview history: {str(e)}")
            return jsonify({'error': str(e)}), 500
        
    @app.route('/interview_history.html')
    def interview_history():
        username = request.args.get('username')
        user_id = request.args.get('user_id')

        if not username or not user_id:
            return "Missing username or user_id parameters", 400

        return render_template('interview_history.html', username=username, user_id=user_id)
