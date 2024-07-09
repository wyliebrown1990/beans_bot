from flask import Blueprint, render_template, request, jsonify, current_app, session, redirect, url_for
from ..utils import generate_session_id
import logging

logger = logging.getLogger(__name__)
logger.debug("Creating second_round blueprint")

second_round_bp = Blueprint('second_round', __name__)

@second_round_bp.route('/')
def second_round():
    try:
        logger.debug("second_round route called")
        username = request.args.get('username')
        user_id = request.args.get('user_id')
        interview_round = request.args.get('interview_round')
        session_id = request.args.get('session_id')

        session.pop('last_question', None)

        if not session_id:
            session_id = generate_session_id()
            return redirect(url_for('second_round.second_round', username=username, user_id=user_id, interview_round=interview_round, session_id=session_id))

        initial_question = second_round_question(user_id, session_id)

        return render_template('second_round.html', username=username, initial_question=initial_question, session_id=session_id)
    except Exception as e:
        current_app.logger.error(f"Error in second_round route: {e}")
        return jsonify({"error": "An error occurred while processing your request. Please try again later."}), 500

# Ensure other routes are updated to use 'second_round_bp'
