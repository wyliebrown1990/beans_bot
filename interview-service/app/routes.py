from flask import Blueprint, render_template, request, jsonify, current_app, session, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from pydub import AudioSegment
import os
import random
from openai import OpenAI
from .models import JobDescriptionAnalysis, User, InterviewHistory, Questions
from .utils import (
    generate_session_id, intro_question, store_user_answer, get_intro_question_feedback,
    get_resume_question_1_feedback, get_resume_question_2_feedback, get_resume_question_3_feedback,
    get_resume_question_4_feedback, get_behavioral_question_1_feedback, get_behavioral_question_2_feedback,
    get_situational_question_1_feedback, get_personality_question_1_feedback, get_motivational_question_1_feedback,
    get_competency_question_1_feedback, get_ethical_question_1_feedback, get_last_question_feedback, get_personality_question_1, get_behavioral_question_1, get_behavioral_question_2,
    get_situational_question_1, get_resume_question_1, get_resume_question_2, get_resume_question_3, get_resume_question_4,
    get_motivational_question_1, get_ethical_question_1, get_last_question, store_question, get_intro_score, get_score, fill_in_skipped_answers, generate_final_message, text_to_speech_file, db_session
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

        # Clear the last question flag
        session.pop('last_question', None)

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
        generate_audio = request.form.get('generate_audio') == 'true'
        voice_id = request.form.get('voice')

        print(f"Submitting answer: {answer} for user_id: {user_id}, session_id: {session_id}")

        store_user_answer(answer, user_id, session_id)

        # Determine the current cycle and set the conditions for transitioning to the next questions
        current_cycle = db_session.query(InterviewHistory).filter_by(user_id=user_id, session_id=session_id).count()
        print(f"Current cycle: {current_cycle}")

        if 'last_question' in session:
            print("Handling last question feedback")
            response = get_last_question_feedback(user_id, session_id)
            if 'error' in response:
                print(f"Error in last question feedback: {response['error']}")
                return jsonify(response)
            # Generate the final message
            final_message = generate_final_message(user_id, session_id)
            print(f"Generated final message: {final_message}")
            response['final_message'] = final_message

            current_app.logger.debug(f"Server response: {response}")

            return jsonify(response)

        if current_cycle == 1:
            response = get_intro_question_feedback(user_id, session_id)
        elif current_cycle == 2:
            response = get_resume_question_1_feedback(user_id, session_id)
        elif current_cycle == 3:
            response = get_resume_question_2_feedback(user_id, session_id)
        elif current_cycle == 4:
            response = get_resume_question_3_feedback(user_id, session_id)
        elif current_cycle == 5:
            response = get_resume_question_4_feedback(user_id, session_id)
        elif current_cycle == 6:
            response = get_behavioral_question_1_feedback(user_id, session_id)
        elif current_cycle == 7:
            response = get_behavioral_question_2_feedback(user_id, session_id)
        elif current_cycle == 8:
            response = get_situational_question_1_feedback(user_id, session_id)
        elif current_cycle == 9:
            response = get_personality_question_1_feedback(user_id, session_id)
        elif current_cycle == 10:
            response = get_motivational_question_1_feedback(user_id, session_id)
        elif current_cycle == 11:
            response = get_competency_question_1_feedback(user_id, session_id)
        elif current_cycle == 12:
            response = get_ethical_question_1_feedback(user_id, session_id)
        else:
            response = get_intro_question_feedback(user_id, session_id)  # Default case or handle other conditions

        # Set the session flag to indicate the last question was asked
        if current_cycle >= 12:
            session['last_question'] = True

        print(f"Response: {response}")

        next_question = response.get('next_question_response', 'No next question found')
        response_message = response.get('response_message', '')

        # Convert text to speech for the next question response only if the box is checked
        next_question_audio_path = None
        if generate_audio and next_question:
            print("Generating audio for the next question...")
            next_question_audio_path = text_to_speech_file(next_question, voice_id, current_app)
            if next_question_audio_path:
                print(f"Generated audio file path: {next_question_audio_path}")
                next_question_audio_url = url_for('main.uploaded_file', filename=os.path.basename(next_question_audio_path))
                response['next_question_audio'] = next_question_audio_url
            else:
                print("Failed to generate audio file.")
                response['next_question_audio'] = None

        response['session_id'] = session_id
        response['next_question'] = next_question
        response['response_message'] = response_message

        print(f"Next question: {next_question}")
        print(f"Next question audio: {response['next_question_audio']}")

        current_app.logger.debug(f"Server response: {response}")

        return jsonify(response)
    except Exception as e:
        current_app.logger.error(f"Error in submit_answer route: {e}")
        print(f"Error in submit_answer route: {e}")
        return jsonify({"error": "An error occurred while processing your request. Please try again later."}), 500

@main.route('/audio_files/<filename>')
def uploaded_file(filename):
    return send_from_directory(os.path.join(current_app.root_path, 'audio_files'), filename)

@main.route('/get_last_question', methods=['GET'])
def get_last_question_route():
    try:
        user_id = request.args.get('user_id')
        session_id = request.args.get('session_id')
        if not user_id or not session_id:
            raise ValueError("user_id or session_id missing from request")
        print(f"Getting last question for user_id: {user_id}, session_id: {session_id}")
        question = get_last_question(user_id, session_id)
        session['last_question'] = True  # Set the session flag
        print(f"Generated last question: {question}")
        return jsonify({"next_question_response": question})
    except Exception as e:
        current_app.logger.error(f"Error in get_last_question route: {e}")
        print(f"Error in get_last_question route: {e}")
        return jsonify({"error": "An error occurred while processing your request. Please try again later."}), 500



@main.route('/wrap_up_early', methods=['POST'])
def wrap_up_early():
    try:
        user_id = request.form.get('user_id')
        session_id = request.form.get('session_id')

        print(f"Wrap up early triggered for user_id: {user_id}, session_id: {session_id}")

        # Fill in skipped answers and generate the last question
        fill_in_skipped_answers(session_id)
        last_question = get_last_question(user_id, session_id)
        session['last_question'] = True

        print(f"Last question generated: {last_question}")

        return jsonify({"next_question_response": last_question})
    except Exception as e:
        current_app.logger.error(f"Error in wrap_up_early route: {e}")
        print(f"Error in wrap_up_early route: {e}")
        return jsonify({"error": "An error occurred while processing your request. Please try again later."}), 500


@main.route('/send_final_message', methods=['GET'])
def send_final_message():
   try:
       user_id = request.args.get('user_id')
       session_id = request.args.get('session_id')

       if not user_id or not session_id:
           raise ValueError("user_id or session_id missing from request")

       response_message = generate_final_message(user_id, session_id)
       print(f"Final message generated: {response_message}")

       return jsonify({"final_message": response_message})
   except Exception as e:
       current_app.logger.error(f"Error in send_final_message route: {e}")
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
