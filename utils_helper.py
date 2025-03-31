"""
Helper file to resolve circular imports by re-exporting functions from app.py
"""

# This file will be imported by app.py to resolve the circular import issue
# The actual implementation is in app.py

# Function declarations that will be imported by app.py
def process_company_documents(*args, **kwargs):
    """
    Proxy function for process_company_documents in app.py
    This is a placeholder to avoid circular imports.
    The actual implementation is in app.py
    """
    # This will never be called, since app.py defines its own version
    pass

def initialize_claude(*args, **kwargs):
    """
    Proxy function for initialize_claude in app.py
    This is a placeholder to avoid circular imports.
    The actual implementation is in app.py
    """
    # This will never be called, since app.py defines its own version
    pass 