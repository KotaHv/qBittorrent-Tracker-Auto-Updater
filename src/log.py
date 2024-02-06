import sys
from loguru import logger
from config import settings


def setup_logger():
    logger.remove()
    logger.add(sys.stderr, level=settings.log_level)
