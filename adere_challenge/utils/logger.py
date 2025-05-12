"""Simple logger for the application."""

from colorama import init

# Initialize colorama
init(autoreset=True)

def log(message):
    """Print a log message to the console.
    
    Args:
        message: The message to log
    """
    print(message) 