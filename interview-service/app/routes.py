from flask import Blueprint, render_template, request, jsonify, current_app, session, redirect, url_for
from werkzeug.utils import secure_filename
from pydub import AudioSegment
import os
import random
from openai import OpenAI
from .models import JobDescriptionAnalysis, User, InterviewHistory, Questions
from .utils import (
    generate_session_id, intro_question, store_user_answer, get_intro_question_feedback,
    get_resume_question_1_feedback, get_resume_question_2_feedback, get_behavioral_question_1_feedback,
    get_resume_question_1, get_resume_question_2, store_question, get_score, db_session
)

main = Blueprint('main', __name__)

# Initialize the OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@main.route('/first_round')
def first_round():
    try:
        username = request.args.get('username')
        user_id = request.args.get('user_id')
        interview_round = request.args.get('interview_round')
        job_title = request.args.get('job_title')
        company_name = request.args.get('company_name')
        industry = request.args.get('industry')

        # Generate a session ID if not already provided in the URL
        session_id = request.args.get('session_id')
        if not session_id:
            session_id = generate_session_id()
            # Redirect to the same URL with the session_id included
            return redirect(url_for('main.first_round', username=username, user_id=user_id, interview_round=interview_round, job_title=job_title, company_name=company_name, industry=industry, session_id=session_id))

        initial_question = intro_question(user_id, session_id)

        return render_template('first_round.html', username=username, initial_question=initial_question, session_id=session_id)
    except Exception as e:
        # Log the error and return a user-friendly message
        current_app.logger.error(f"Error in first_round route: {e}")
        return jsonify({"error": "An error occurred while processing your request. Please try again later."}), 500

@main.route('/submit_answer', methods=['POST'])
def submit_answer():
    try:
        answer = request.form.get('answer_1')
        user_id = request.form.get('user_id')
        session_id = request.form.get('session_id')

        print(f"Submitting answer: {answer} for user_id: {user_id}, session_id: {session_id}")

        store_user_answer(answer, user_id, session_id)

        # Determine the current cycle and set the conditions for transitioning to the next questions
        current_cycle = db_session.query(InterviewHistory).filter_by(user_id=user_id, session_id=session_id).count()
        print(f"Current cycle: {current_cycle}")

        if current_cycle == 1:
            response = get_intro_question_feedback(user_id, session_id)
        elif current_cycle == 2:
            response = get_resume_question_1_feedback(user_id, session_id)
        elif current_cycle == 3:
            response = get_resume_question_2_feedback(user_id, session_id)
        elif current_cycle == 4:
            response = get_behavioral_question_1_feedback(user_id, session_id)
        else:
            response = get_intro_question_feedback(user_id, session_id)  # Default case or handle other conditions

        next_question = response['next_question_response']

        response['session_id'] = session_id
        response['next_question'] = next_question
        print(f"Next question: {next_question}")
        return jsonify(response)
    except Exception as e:
        current_app.logger.error(f"Error in submit_answer route: {e}")
        return jsonify({"error": "An error occurred while processing your request. Please try again later."}), 500



@main.route('/transcribe_audio', methods=['POST'])
def transcribe_audio():
    file_path = None
    wav_path = None  # Initialize wav_path here
    text = None  # Initialize text here
    try:
        print("Received audio file for transcription...")
        if 'audio' not in request.files:
            print("No audio file uploaded.")
            return jsonify({'error': 'No audio file uploaded'}), 400

        audio_file = request.files['audio']
        filename = secure_filename(audio_file.filename)
        file_path = os.path.join('/tmp', filename)
        print(f"Saving audio file to {file_path}...")
        audio_file.save(file_path)

        # Convert audio file to WAV format using pydub
        audio = AudioSegment.from_file(file_path)
        wav_path = os.path.join('/tmp', 'audio.wav')
        audio.export(wav_path, format='wav')
        print(f"Audio file converted to WAV format at {wav_path}")

        # Transcribe audio using OpenAI API
        print("Starting transcription with OpenAI Whisper API...")
        with open(wav_path, "rb") as audio_file:
            response = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
            print(f"Transcription API response: {response}")

            # Check the structure of the response to handle it properly
            if isinstance(response, dict) and "text" in response:
                text = response["text"]
                print(f"Transcription result: {text}")
            elif isinstance(response, str):
                text = response
                print(f"Transcription result: {text}")
            else:
                raise ValueError("Unexpected response format from transcription API")
    except Exception as e:
        print(f"Error during transcription: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        print("Removing temporary audio files...")
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        if wav_path and os.path.exists(wav_path):
            os.remove(wav_path)

        return jsonify({'transcription': text})
