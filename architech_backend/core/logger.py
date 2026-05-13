import logging
import sys

def setup_logger(name: str) -> logging.Logger:
    """
    Sets up an enterprise-grade logger for the given module name.
    """
    logger = logging.getLogger(name)
    
    # Only configure if the logger doesn't already have handlers
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Create console handler with standard formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Standard format: [Time] [Level] [LoggerName] - Message
        formatter = logging.Formatter(
            '%(asctime)s - [%(levelname)s] - %(name)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        
    return logger
