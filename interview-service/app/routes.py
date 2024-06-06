from flask import render_template, request, jsonify
import os
from .utils import (
    get_session_history, load_training_data, generate_next_question,
    get_resume_question_answer, get_career_experience_answer, extract_score,
    most_recent_question, user_responses, query_faiss_index, text_to_speech_file
)
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

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

            initial_question = f"Tell me about your professional experience and how it relates to this role at {company_name}"
            session_id = os.urandom(24).hex()
            session_history = get_session_history(session_id)
            session_history.add_message(AIMessage(content=initial_question))

            return render_template('start_interview.html', question=initial_question, session_id=session_id, job_title=job_title, company_name=company_name, industry=industry, username=username)

        if request.method == 'POST':
            job_title = request.form['job_title']
            company_name = request.form['company_name']
            industry = request.form['industry']
            username = request.form['username']
            session_id = request.form['session_id']
            user_response = request.form['answer_1']
            generate_audio = 'generate_audio' in request.form

            # Query FAISS index for career context
            career_context_query = f"Top features of {company_name}"
            career_context = query_faiss_index(career_context_query)

            if user_responses["resume_user_response"] is None:
                # First response (resume_user_response)
                results = get_resume_question_answer(session, username, job_title, company_name, industry, user_response, career_context)
            else:
                # Subsequent responses (career_user_responses)
                results = get_career_experience_answer(session, username, job_title, company_name, industry, user_response, career_context)

            session_history = get_session_history(session_id)
            session_history.add_message(AIMessage(content=results["analysis_response"] if results["analysis_response"] else ""))
            session_history.add_message(AIMessage(content=results["next_question"]))

            # Convert text to speech for next question response only if the box is checked
            next_question_audio_path = None
            if generate_audio:
                next_question_audio_path = text_to_speech_file(results["next_question"])

            print(f"Next question audio path: {next_question_audio_path}")

            return jsonify({
                'feedback_response': results["analysis_response"] if results["analysis_response"] else "",
                'score_response': results["score"] if results["score"] else "N/A",
                'next_question_response': results["next_question"],
                'next_question_audio': next_question_audio_path if next_question_audio_path else None
            })
