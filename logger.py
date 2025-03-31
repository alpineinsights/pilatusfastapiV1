import logging

# Create a logger instance that will be imported by other modules
logger = logging.getLogger("financial_insights")
logger.setLevel(logging.INFO)

# This logger will be configured by the setup_logging function in logging_config.py
# We just create the instance here to avoid circular imports 