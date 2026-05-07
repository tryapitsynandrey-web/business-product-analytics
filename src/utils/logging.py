import logging
from typing import Optional

def configure_logging(level: str = "INFO") -> None:
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
        
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        
def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(name)
    if level is not None:
        numeric_level = getattr(logging, level.upper(), None)
        if isinstance(numeric_level, int):
            logger.setLevel(numeric_level)
    return logger
