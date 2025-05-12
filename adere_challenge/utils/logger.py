"""Simple logger for the application."""

from colorama import init, Fore

# Initialize colorama
init(autoreset=True)

# Global debug flag
_DEBUG = False

def set_debug_mode(enabled):
    """Set the debug mode.
    
    Args:
        enabled (bool): Whether debug mode is enabled
    """
    global _DEBUG
    _DEBUG = enabled

def is_debug_enabled():
    """Check if debug mode is enabled.
    
    Returns:
        bool: True if debug mode is enabled, False otherwise
    """
    return _DEBUG

def log(message, debug=False):
    """Print a log message to the console.
    
    Args:
        message: The message to log
        debug (bool): Whether this is a debug message
    """
    # Skip debug messages if debug mode is not enabled
    if debug and not _DEBUG:
        return
    
    # Prefix debug messages with DEBUG tag
    if debug:
        print(f"{Fore.MAGENTA}[DEBUG]{Fore.RESET} {message}")
    else:
        print(message)

def debug(message):
    """Print a debug message to the console if debug mode is enabled.
    
    Args:
        message: The debug message to log
    """
    log(message, debug=True) 