from flask import Blueprint, render_template, request, jsonify, current_app, session, redirect, url_for
from ..utils import generate_session_id
import logging

logger = logging.getLogger(__name__)
logger.debug("Creating third_round blueprint")

third_round_bp = Blueprint('third_round', __name__)

@third_round_bp.route('/')
def third_round():
    try:
        logger.debug("third_round route called")
        username = request.args.get('username')
        user_id = request.args.get('user_id')
        interview_round = request.args.get('interview_round')
        session_id = request.args.get('session_id')

        session.pop('last_question', None)

        if not session_id:
            session_id = generate_session_id()
            return redirect(url_for('third_round.third_round', username=username, user_id=user_id, interview_round=interview_round, session_id=session_id))

        initial_question = third_round_question(user_id, session_id)

        return render_template('third_round.html', username=username, initial_question=initial_question, session_id=session_id)
    except Exception as e:
        current_app.logger.error(f"Error in third_round route: {e}")
        return jsonify({"error": "An error occurred while processing your request. Please try again later."}), 500

# Ensure other routes are updated to use 'third_round_bp'
