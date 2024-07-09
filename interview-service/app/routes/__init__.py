import logging

logger = logging.getLogger(__name__)
logger.debug("Importing blueprints in routes/__init__.py")

from .first_round import first_round_bp
from .second_round import second_round_bp
from .third_round import third_round_bp

logger.debug("Blueprints imported successfully")

__all__ = ['first_round_bp', 'second_round_bp', 'third_round_bp']