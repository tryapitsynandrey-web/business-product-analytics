import logging
from utils.logging import configure_logging, get_logger

def test_logger_creation():
    logger = get_logger("test_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"

def test_no_duplicate_handlers():
    configure_logging()
    handlers_before = len(logging.getLogger().handlers)
    configure_logging()
    handlers_after = len(logging.getLogger().handlers)
    assert handlers_before == handlers_after
