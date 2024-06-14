from flask import render_template, request, jsonify, Response, make_response, session as flask_session  # Use flask_session for Flask session
import csv
import os
import logging
from io import StringIO
from werkzeug.utils import secure_filename
from pydub import AudioSegment
from openai import OpenAI
from .utils import (
   get_session_history, generate_question_2, generate_question_3, generate_question_4,  # Import dynamically named functions
   get_answer_1, get_answer_2, get_answer_3, # Import dynamically named functions
   extract_score, most_recent_question, user_responses, users_training_data, text_to_speech_file,
   setup_database, fetch_interview_data
)
from .resume_utils import get_user_resume_data  # Correct import statement
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.models import TrainingData, InterviewAnswer, User, VideoRecordingLog

# Initialize the OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Ensure you have the session setup globally in the routes file
engine, sqlalchemy_session = setup_database(os.getenv("DATABASE_URL"))

def setup_routes(app_instance, session_instance):
   global sqlalchemy_session
   sqlalchemy_session = session_instance

   @app_instance.route('/start_interview', methods=['GET', 'POST'])
   def start_interview():
       try:
           if request.method == 'GET':
               job_title = request.args.get('job_title').strip().lower()
               company_name = request.args.get('company_name').strip().lower()
               industry = request.args.get('industry').strip().lower()
               username = request.args.get('username').strip().lower()
               user_id = request.args.get('user_id').strip()

               initial_question = f"Tell me about yourself. What relevant professional experience have you had and what skillsets have you learned that make you uniquely qualified to succeed at {company_name}?"
               session_id = os.urandom(24).hex()  # Generate a new session ID
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
               voice_id = request.form.get('voice', 'WBPMIeOib7vXJnT2Iibp')  # Default to Knightley if no voice is selected

               logging.debug(f"Job Title: {job_title}, Company Name: {company_name}, Industry: {industry}, Username: {username}, Session ID: {session_id}, User Response: {user_response}, User ID: {user_id}, Generate Audio: {generate_audio}, Voice ID: {voice_id}")

               # Load user training data
               training_data = users_training_data(sqlalchemy_session, user_id, job_title, company_name)
               logging.debug(f"Training Data: {training_data}")

               if not training_data:
                   return jsonify({'error': 'No training data found for the given parameters'}), 400

               file_summary = training_data.get("file_summary", "")

               # Initialize or update user responses in the Flask session
               if 'user_responses' not in flask_session:
                   flask_session['user_responses'] = []

               logging.debug(f"Initial Flask Session User Responses: {flask_session['user_responses']}")

               # Determine the response number
               response_number = len(flask_session['user_responses']) + 1
               logging.debug(f"Response Number: {response_number}")

               # Dynamically call the correct answer function
               answer_function_name = f"get_answer_{response_number}"
               logging.debug(f"Answer Function Name: {answer_function_name}")
               answer_function = globals().get(answer_function_name)
               logging.debug(f"Answer Function: {answer_function}")

               if answer_function:
                   print(f"Calling {answer_function_name}")  # Add print statement
                   results = answer_function(sqlalchemy_session, username, job_title, company_name, industry, user_response, file_summary, session_id)
                   flask_session['user_responses'].append(user_response)
               else:
                   logging.error(f"No function defined for response number {response_number}")
                   return jsonify({'error': f'No function defined for response number {response_number}'}), 500

               # Save the updated Flask session
               flask_session.modified = True

               session_history = get_session_history(session_id)
               session_history.add_message(AIMessage(content=results.get("analysis_response", "No analysis response")))
               session_history.add_message(AIMessage(content=results.get("next_question", "No next question")))

               # Convert text to speech for next question response only if the box is checked
               next_question_audio_path = None
               if generate_audio:
                   next_question_audio_path = text_to_speech_file(results["next_question"], voice_id)

               return jsonify({
                   'feedback_response': results.get("analysis_response", "No analysis response"),
                   'score_response': results.get("score", "N/A"),
                   'next_question_response': results.get("next_question", "No next question"),
                   'next_question_audio': next_question_audio_path if next_question_audio_path else None
               })
       except Exception as e:
           logging.error(f"Error in start_interview: {e}", exc_info=True)
           return jsonify({'error': str(e)}), 500

   @app_instance.route('/transcribe_audio', methods=['POST'])
   def transcribe_audio():
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
           os.remove(file_path)
           os.remove(wav_path)

       return jsonify({'transcription': text})

   @app_instance.route('/get_user_training_data', methods=['GET'])
   def get_user_training_data():
       try:
           user_id = current_user.id  # Assuming you have a way to get the current user's ID
           job_title = request.args.get('job_title')
           company_name = request.args.get('company_name')
           data = users_training_data(sqlalchemy_session, user_id, job_title, company_name)
           return jsonify(data)
       except Exception as e:
           logging.error(f"Error in get_user_training_data: {e}", exc_info=True)
           return jsonify({'error': str(e)}), 500

   @app_instance.route('/download_transcript/<session_id>')
   def download_transcript(session_id):
       try:
           # Fetch interview data from the database
           interview_data = fetch_interview_data(sqlalchemy_session, session_id)  # Pass the session first, then session_id

           # Create CSV data
           si = StringIO()
           cw = csv.writer(si)
           cw.writerow(['Question', 'Answer', 'Feedback', 'Score'])
           for item in interview_data:
               cw.writerow([item.question, item.answer, item.critique, item.score])

           output = make_response(si.getvalue())
           output.headers["Content-Disposition"] = "attachment; filename=interview_transcript.csv"
           output.headers["Content-type"] = "text/csv"
           return output
       except Exception as e:
           logging.error(f"Error in download_transcript: {e}", exc_info=True)
           return jsonify({'error': str(e)}), 500

   @app_instance.route('/clear_session', methods=['POST'])
   def clear_session():
       flask_session.clear()
       return jsonify({'status': 'session cleared'}), 200

   @app_instance.route('/save_video', methods=['POST'])
   def save_video():
       try:
           print("Received video file for saving...")
           if 'video' not in request.files:
               print("No video file uploaded.")
               return jsonify({'error': 'No video file uploaded'}), 400

           video_file = request.files['video']
           session_id = request.form['session_id']
           user_id = request.form['user_id']
           job_role = request.form['job_title']  # Change job_title to job_role
           company_name = request.form['company_name']

           filename = secure_filename(video_file.filename)
           file_path = os.path.join('/tmp', filename)
           print(f"Saving video file to {file_path}...")
           video_file.save(file_path)

           with open(file_path, "rb") as video:
               video_data = video.read()

           new_video_recording = VideoRecordingLog(
               user_id=user_id,
               job_role=job_role,  # Change job_title to job_role
               company_name=company_name,
               session_id=session_id,
               video_data=video_data
           )
           sqlalchemy_session.add(new_video_recording)
           sqlalchemy_session.commit()
           print(f"Video recording saved to database for session_id: {session_id}, user_id: {user_id}, job_role: {job_role}, company_name: {company_name}")

           os.remove(file_path)
           return jsonify({'message': 'Video saved successfully'})
       except Exception as e:
               print(f"Error saving video: {e}")
               return jsonify({'error': str(e)}), 500
