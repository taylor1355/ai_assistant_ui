"""Logging configuration for the application."""
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

from ai_assistant_ui.paths import PROJECT_ROOT

def _generate_log_filename(base_dir):
    """Generate a unique log filename with timestamp."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    base_name = f'app_{timestamp}.log'
    file_path = os.path.join(base_dir, base_name)
    
    # Handle duplicate filenames by adding a suffix
    counter = 1
    while os.path.exists(file_path):
        base_name = f'app_{timestamp}_{counter}.log'
        file_path = os.path.join(base_dir, base_name)
        counter += 1
    
    return file_path

def setup_logging():
    """Set up logging configuration."""
    # Create logs directory in project root if it doesn't exist
    log_dir = os.path.join(PROJECT_ROOT, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate unique log filename with timestamp
    log_file = _generate_log_filename(log_dir)
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1024 * 1024,  # 1MB
        backupCount=5
    )
    
    # Set up formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)

    return log_file
