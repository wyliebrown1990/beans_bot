from flask import render_template, request, jsonify
import os
import logging
from werkzeug.utils import secure_filename
from pydub import AudioSegment
from openai import OpenAI
from .utils import (
    get_session_history, generate_next_question,
    get_resume_question_answer, get_career_experience_answer, extract_score,
    most_recent_question, user_responses, users_training_data, text_to_speech_file,
    setup_database
)
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Initialize the OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Ensure you have the session setup globally in the routes file
engine, session = setup_database(os.getenv("DATABASE_URL"))

def setup_routes(app_instance, session_instance):
    global session
    session = session_instance

    @app_instance.route('/start_interview', methods=['GET', 'POST'])
    def start_interview():
        if request.method == 'GET':
            job_title = request.args.get('job_title').strip().lower()
            company_name = request.args.get('company_name').strip().lower()
            industry = request.args.get('industry').strip().lower()
            username = request.args.get('username').strip().lower()
            user_id = request.args.get('user_id').strip()

            initial_question = f"Tell me about yourself. What relevant professional experience have you had and what skillsets have you learned that make you uniquely qualified to succeed at {company_name}?"
            session_id = os.urandom(24).hex()
            session_history = get_session_history(session_id)
            session_history.add_message(AIMessage(content=initial_question))

            return render_template('start_interview.html', question=initial_question, session_id=session_id, job_title=job_title, company_name=company_name, industry=industry, username=username, user_id=user_id)

        if request.method == 'POST':
            job_title = request.form['job_title']
            company_name = request.form['company_name']
            industry = request.form['industry']
            username = request.form['username']
            session_id = request.form['session_id']
            user_response = request.form['answer_1']
            user_id = request.form['user_id']
            generate_audio = 'generate_audio' in request.form
            voice_id = request.form.get('voice', 'xU744AaoW3SYWVj6TN6H')  # Default to Knightley if no voice is selected

            # Load user training data
            training_data = users_training_data(session, user_id, job_title, company_name)
            print("Type of training_data:", type(training_data))
            print("Contents of training_data:", training_data)

            if not training_data:
                return jsonify({'error': 'No training data found for the given parameters'}), 400

            file_summary = training_data.get("file_summary", "")
            print("file_summary:", file_summary)
            
            if user_responses["resume_user_response"] is None:
                # First response (resume_user_response)
                results = get_resume_question_answer(session, username, job_title, company_name, industry, user_response, file_summary)
            else:
                # Subsequent responses (career_user_responses)
                results = get_career_experience_answer(session, username, job_title, company_name, industry, user_response, file_summary)

            session_history = get_session_history(session_id)
            session_history.add_message(AIMessage(content=results["analysis_response"] if results["analysis_response"] else ""))
            session_history.add_message(AIMessage(content=results["next_question"]))

            # Convert text to speech for next question response only if the box is checked
            next_question_audio_path = None
            if generate_audio:
                next_question_audio_path = text_to_speech_file(results["next_question"], voice_id)

            print(f"Next question audio path: {next_question_audio_path}")

            return jsonify({
                'feedback_response': results["analysis_response"] if results["analysis_response"] else "",
                'score_response': results["score"] if results["score"] else "N/A",
                'next_question_response': results["next_question"],
                'next_question_audio': next_question_audio_path if next_question_audio_path else None
            })

    @app_instance.route('/transcribe_audio', methods=['POST'])
    def transcribe_audio():
        print("Received audio file for transcription...")
        if 'audio' not in request.files:
            print("No audio file uploaded.")
            return jsonify({'error': 'No audio file uploaded'}), 400

        audio_file = request.files['audio']
        filename = secure_filename(audio_file.filename)
        file_path = os.path.join('/tmp', filename)
        print(f"Saving audio file to {file_path}...")
        audio_file.save(file_path)

        try:
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
            os.remove(file_path)
            os.remove(wav_path)

        return jsonify({'transcription': text})

    @app_instance.route('/get_user_training_data', methods=['GET'])
    def get_user_training_data():
        user_id = current_user.id  # Assuming you have a way to get the current user's ID
        job_title = request.args.get('job_title')
        company_name = request.args.get('company_name')
        data = users_training_data(session, user_id, job_title, company_name)
        return jsonify(data)
