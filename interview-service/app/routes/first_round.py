from werkzeug.utils import secure_filename
from pydub import AudioSegment
import os
import io
import random
import csv
from openai import OpenAI
from flask import Blueprint, render_template, request, jsonify, current_app, session, redirect, url_for, send_from_directory, Response
from app.utils.first_round_utils import *
from app.utils.interview_history_utils import record_interview_history
from app.utils.unique_session_utils import ensure_unique_session_id
from app.models import JobDescriptions
from app.database import db_session
from sqlalchemy.exc import IntegrityError
import logging

logger = logging.getLogger(__name__)
logger.debug("Creating first_round blueprint")

first_round_bp = Blueprint('first_round', __name__)

@first_round_bp.route('/')
def first_round_view():
    username = request.args.get('username')
    user_id = request.args.get('user_id')
    interview_round = request.args.get('interview_round')
    job_title = request.args.get('job_title')
    company_name = request.args.get('company_name')
    company_industry = request.args.get('company_industry')
    session_id = request.args.get('session_id', None)

    if not session_id:
        session_id = ensure_unique_session_id(user_id)
        return redirect(url_for('first_round.first_round_view', username=username, user_id=user_id, interview_round=interview_round, job_title=job_title, company_name=company_name, company_industry=company_industry, session_id=session_id))

    initial_question = get_first_question(username, user_id)

    # Set the initial question time in the session
    session['question_time'] = '30:00'  # Assuming the timer starts at 30 minutes

    return render_template('first_round.html', username=username, user_id=user_id, interview_round=interview_round, job_title=job_title, company_name=company_name, company_industry=company_industry, session_id=session_id, initial_question=initial_question)

@first_round_bp.route('/submit_answer', methods=['POST'])
def submit_answer():
    session_id = request.form.get('session_id')
    user_id = request.form.get('user_id')
    username = get_user_by_id(user_id).username
    question = request.form.get('question')
    answer = request.form.get('answer_1')
    feedback = request.form.get('feedback', None)
    score = request.form.get('score', None)
    interview_round = request.form.get('interview_round')
    question_id = request.form.get('question_id', None)

    job_details = fetch_interview_data(user_id)

    # Retrieve the stored question time
    question_time = session.get('question_time')
    current_time = request.form.get('current_time')

    # Debugging statements
    print(f"Question Time: {question_time}")
    print(f"Current Time: {current_time}")

    if question_time and current_time:
        question_time_minutes, question_time_seconds = map(int, question_time.split(':'))
        current_time_minutes, current_time_seconds = map(int, current_time.split(':'))

        # Convert times to total seconds
        question_total_seconds = question_time_minutes * 60 + question_time_seconds
        current_total_seconds = current_time_minutes * 60 + current_time_seconds

        # Calculate the timer value
        timer_seconds = question_total_seconds - current_total_seconds
        timer_hours = timer_seconds // 3600
        timer_seconds %= 3600
        timer_minutes = timer_seconds // 60
        timer_seconds %= 60

        timer = f"{timer_hours:02}:{timer_minutes:02}:{timer_seconds:02}"
    else:
        timer = "00:00:00"

    # More debugging statements
    print(f"Calculated Timer: {timer}")

    if answer == 'skipped':
        feedback = 'skipped'
        score = None
    else:
        question_num = request.form.get('question_num', 1)
        if question_num == 'last':
            feedback_function = get_last_feedback
            score_function = get_last_score
        else:
            question_num = int(question_num)
            feedback_function = globals()[f"get_{num_to_ordinal(question_num)}_feedback"]
            score_function = globals()[f"get_{num_to_ordinal(question_num)}_score"]

        # Dynamically determine the arguments for the feedback function
        feedback_func_code = feedback_function.__code__
        feedback_func_varnames = feedback_func_code.co_varnames[:feedback_func_code.co_argcount]

        # Prepare arguments based on function requirements
        feedback_args = []
        for varname in feedback_func_varnames:
            if varname == 'answer':
                feedback_args.append(answer)
            elif varname == 'user_id':
                feedback_args.append(user_id)
            elif varname == 'question_id':
                feedback_args.append(question_id)

        feedback = feedback_function(*feedback_args) if feedback is None else feedback

        # Dynamically determine the arguments for the score function
        score_func_code = score_function.__code__
        score_func_varnames = score_func_code.co_varnames[:score_func_code.co_argcount]

        # Prepare arguments based on function requirements
        score_args = []
        for varname in score_func_varnames:
            if varname == 'answer':
                score_args.append(answer)
            elif varname == 'user_id':
                score_args.append(user_id)

        score = score_function(*score_args) if score is None else score

    try:
        record_interview_history(session_id, user_id, question, answer, score, feedback, timer, interview_round, job_details.job_title, job_details.job_level, job_details.company_name, job_details.company_industry, question_id or None)
    except IntegrityError as e:
        current_app.logger.error(f"Error recording interview history: {e}")
        return jsonify({'error': 'Failed to record interview history'}), 500

    # Update the most recent question and answer
    set_most_recent_question_answer(question, answer)

    if question_num == 'last':
        return jsonify({'message': 'Interview complete', 'summary': get_summary_message()}), 200

    next_question_num = int(request.form.get('question_num', 1)) + 1
    next_question_function = globals().get(f"get_{num_to_ordinal(next_question_num)}_question", None)
    if next_question_function:
        # Dynamically determine the arguments for the next question function
        func_code = next_question_function.__code__
        func_varnames = func_code.co_varnames[:func_code.co_argcount]

        # Prepare arguments based on function requirements
        next_question_args = []
        for varname in func_varnames:
            if varname == 'username':
                next_question_args.append(username)
            elif varname == 'user_id':
                next_question_args.append(user_id)

        next_question_data = next_question_function(*next_question_args)
        if isinstance(next_question_data, tuple):
            next_question, question_id = next_question_data
        else:
            next_question = next_question_data
            question_id = None

        # Store the current interview timer for the next question
        session['question_time'] = current_time
    else:
        return jsonify({'message': 'Interview complete', 'summary': get_summary_message()}), 200

    return jsonify({'question': next_question, 'question_num': next_question_num, 'question_id': question_id})


@first_round_bp.route('/skip_question', methods=['POST'])
def skip_question():
    session_id = request.form.get('session_id')
    user_id = request.form.get('user_id')
    question = request.form.get('question')
    interview_round = request.form.get('interview_round')
    question_id = request.form.get('question_id', None)

    job_details = fetch_interview_data(user_id)

    # Retrieve the stored question time
    question_time = session.get('question_time')
    current_time = request.form.get('current_time')

    # Debugging statements
    print(f"Question Time: {question_time}")
    print(f"Current Time: {current_time}")

    if question_time and current_time:
        question_time_minutes, question_time_seconds = map(int, question_time.split(':'))
        current_time_minutes, current_time_seconds = map(int, current_time.split(':'))

        # Convert times to total seconds
        question_total_seconds = question_time_minutes * 60 + question_time_seconds
        current_total_seconds = current_time_minutes * 60 + current_time_seconds

        # Calculate the timer value
        timer_seconds = question_total_seconds - current_total_seconds
        timer_hours = timer_seconds // 3600
        timer_seconds %= 3600
        timer_minutes = timer_seconds // 60
        timer_seconds %= 60

        timer = f"{timer_hours:02}:{timer_minutes:02}:{timer_seconds:02}"
    else:
        timer = "00:00:00"

    # More debugging statements
    print(f"Calculated Timer: {timer}")

    feedback = 'skipped'
    answer = 'skipped'
    score = None

    try:
        # Set question_id to None if it's an empty string
        if not question_id:
            question_id = None

        record_interview_history(session_id, user_id, question, answer, score, feedback, timer, interview_round, job_details.job_title, job_details.job_level, job_details.company_name, job_details.company_industry, question_id)
    except IntegrityError as e:
        current_app.logger.error(f"Error recording skipped question in interview history: {e}")
        return jsonify({'error': 'Failed to record skipped question'}), 500

    next_question_num = int(request.form.get('question_num', 1)) + 1
    next_question_function = globals().get(f"get_{num_to_ordinal(next_question_num)}_question", None)
    if next_question_function:
        next_question = next_question_function(get_user_by_id(user_id).username)
        # Store the current interview timer for the next question
        session['question_time'] = current_time
    else:
        return jsonify({'message': 'Interview complete'}), 200

    return jsonify({'question': next_question, 'question_num': next_question_num})

@first_round_bp.route('/end_interview', methods=['POST'])
def end_interview():
    session_id = request.form.get('session_id')
    user_id = request.form.get('user_id')
    question = request.form.get('question')
    interview_round = request.form.get('interview_round')
    question_id = request.form.get('question_id', None)

    job_details = fetch_interview_data(user_id)

    feedback = 'skipped'
    answer = 'skipped'
    score = None

    try:
        # Set question_id to None if it's an empty string
        if not question_id:
            question_id = None

        record_interview_history(session_id, user_id, question, answer, score, feedback, "00:00:00", interview_round, job_details.job_title, job_details.job_level, job_details.company_name, job_details.company_industry, question_id)
    except IntegrityError as e:
        current_app.logger.error(f"Error recording skipped question in interview history: {e}")
        return jsonify({'error': 'Failed to record skipped question'}), 500

    # Serve the last question
    next_question = get_last_question(get_user_by_id(user_id).username)
    return jsonify({'question': next_question, 'question_num': 'last'})

def num_to_ordinal(num):
    ordinals = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "last"]
    return ordinals[num - 1]

