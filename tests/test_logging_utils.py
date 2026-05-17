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


def test_configure_logging_adds_handler_when_root_has_none():
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    for handler in original_handlers:
        root.removeHandler(handler)

    try:
        configure_logging("DEBUG")
        assert root.level == logging.DEBUG
        assert len(root.handlers) == 1
        assert root.handlers[0].formatter is not None
    finally:
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        for handler in original_handlers:
            root.addHandler(handler)
        root.setLevel(original_level)


def test_configure_logging_invalid_level_falls_back_to_info():
    root = logging.getLogger()
    original_level = root.level

    try:
        configure_logging("not-a-level")
        assert root.level == logging.INFO
    finally:
        root.setLevel(original_level)


def test_get_logger_sets_valid_explicit_level():
    logger = get_logger("debug_logger", level="DEBUG")
    assert logger.level == logging.DEBUG


def test_get_logger_ignores_invalid_explicit_level():
    logger = get_logger("invalid_level_logger")
    before = logger.level

    assert get_logger("invalid_level_logger", level="invalid").level == before
