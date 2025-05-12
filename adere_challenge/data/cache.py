"""Database cache for storing API responses."""

import os
import json
import sqlite3
import hashlib
import time
import re
from colorama import Fore, Style

from adere_challenge.utils.logger import log, debug
from adere_challenge.utils.constants import DB_FILE, LOGS_DIR

# In-memory cache for faster access during runtime
cache = {
    "pokemon": {},
    "swapi_characters": {},
    "swapi_planets": {}
}

# Map entity type keys to table names
ENTITY_TABLE_MAP = {
    "pokemon": "pokemon",
    "swapi_characters": "starwars_characters",
    "swapi_planets": "starwars_planets"
}

def initialize_db():
    """Initialize the SQLite database for caching."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create tables if they don't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS api_cache (
        url TEXT PRIMARY KEY,
        response TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create Pokemon table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pokemon (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE,
        data TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create Star Wars character table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS starwars_characters (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE,
        data TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create Star Wars planet table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS starwars_planets (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE,
        data TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create problem cache table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS problem_cache (
        problem_hash TEXT PRIMARY KEY,
        problem_text TEXT,
        formula TEXT,
        answer TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    
    debug(f"Database initialized at {DB_FILE}")
    
    # Create logs directory if it doesn't exist
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
        log(f"{Fore.BLUE}Created logs directory at {Fore.CYAN}{LOGS_DIR}{Style.RESET_ALL}")

def load_cache():
    """Load the cache from the SQLite database."""
    global cache
    
    if not os.path.exists(DB_FILE):
        log(f"{Fore.YELLOW}No cache database found. Starting with empty cache.{Style.RESET_ALL}")
        initialize_db()
        return
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # For debugging, show table info
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        debug(f"Database tables: {tables}")
        
        # Load Pokemon
        cursor.execute("SELECT name, data FROM pokemon")
        pokemon_count = 0
        for name, data_json in cursor.fetchall():
            cache["pokemon"][name] = json.loads(data_json)
            pokemon_count += 1
        debug(f"Loaded {pokemon_count} Pokemon from database")
        
        # Load Star Wars characters - fixed to match the table name
        cursor.execute("SELECT name, data FROM starwars_characters")
        character_count = 0
        for name, data_json in cursor.fetchall():
            cache["swapi_characters"][name] = json.loads(data_json)
            character_count += 1
        debug(f"Loaded {character_count} Star Wars characters from database")
        
        # Load Star Wars planets - fixed to match the table name
        cursor.execute("SELECT name, data FROM starwars_planets")
        planet_count = 0
        for name, data_json in cursor.fetchall():
            cache["swapi_planets"][name] = json.loads(data_json)
            planet_count += 1
        debug(f"Loaded {planet_count} Star Wars planets from database")
        
        # Count problem cache entries
        cursor.execute("SELECT COUNT(*) FROM problem_cache")
        problem_count = cursor.fetchone()[0]
        
        conn.close()
        
        debug(f"Cache loaded with {len(cache['pokemon'])} Pokémon, "
              f"{len(cache['swapi_characters'])} Star Wars characters, "
              f"{len(cache['swapi_planets'])} Star Wars planets, and "
              f"{problem_count} cached problems.")
              
    except Exception as e:
        log(f"{Fore.RED}Error loading cache: {e}{Style.RESET_ALL}")
        log(f"{Fore.YELLOW}Starting with empty cache.{Style.RESET_ALL}")
        initialize_db()

def add_to_cache(entity_type, name, data):
    """Add or update an entity in both the in-memory cache and SQLite database.
    
    Args:
        entity_type: Type of entity ('pokemon', 'swapi_characters', 'swapi_planets')
        name: Entity name
        data: Entity data
    """
    try:
        # Update in-memory cache
        cache[entity_type][name] = data
        
        # Get the corresponding table name
        table_name = ENTITY_TABLE_MAP.get(entity_type, entity_type)
        
        # Update database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Convert data to JSON string
        data_json = json.dumps(data)
        
        # Insert or replace
        cursor.execute(f"INSERT OR REPLACE INTO {table_name} (name, data) VALUES (?, ?)",
                     (name, data_json))
        
        conn.commit()
        conn.close()
        
        debug(f"Added/updated '{name}' in {entity_type} cache and {table_name} table")
        
    except Exception as e:
        log(f"{Fore.RED}Error adding to cache: {e}{Style.RESET_ALL}")

def get_problem_hash(problem_text):
    """Generate a hash for a problem text to use as a unique identifier.
    
    Args:
        problem_text: The problem text
        
    Returns:
        String hash of the problem
    """
    # Handle None problem text
    if problem_text is None:
        log(f"{Fore.RED}Cannot generate hash for None problem.{Style.RESET_ALL}")
        return "none_problem"  # Return a special hash for None problems
        
    # Remove extra whitespace and convert to lowercase for consistent hashing
    normalized_text = ' '.join(problem_text.lower().split())
    return hashlib.md5(normalized_text.encode('utf-8')).hexdigest()

def check_problem_cache(problem_text):
    """Check if a problem is in the cache.
    
    Args:
        problem_text: The problem text
        
    Returns:
        tuple: (is_cached, formula, answer)
    """
    # Handle None problem text
    if problem_text is None:
        log(f"{Fore.RED}Cannot check cache for None problem.{Style.RESET_ALL}")
        return False, None, None
        
    try:
        problem_hash = get_problem_hash(problem_text)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT formula, answer FROM problem_cache WHERE problem_hash = ?", 
            (problem_hash,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            formula, answer = result
            return True, formula, answer
        else:
            return False, None, None
            
    except Exception as e:
        log(f"{Fore.RED}Error checking problem cache: {e}{Style.RESET_ALL}")
        return False, None, None

def add_to_problem_cache(problem_text, formula, answer):
    """Add a problem and its solution to the cache.
    
    Args:
        problem_text: The problem text
        formula: The formula for solving the problem
        answer: The calculated answer
    """
    # Skip caching for None values
    if problem_text is None or formula is None or answer is None:
        log(f"{Fore.YELLOW}Skipping cache for problem with None values.{Style.RESET_ALL}")
        return
        
    try:
        problem_hash = get_problem_hash(problem_text)
        timestamp = int(time.time())
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT OR REPLACE INTO problem_cache (problem_hash, problem_text, formula, answer, timestamp) VALUES (?, ?, ?, ?, ?)",
            (problem_hash, problem_text, formula, answer, timestamp)
        )
        
        conn.commit()
        conn.close()
        
        log(f"{Fore.GREEN}Problem added to cache with hash {Fore.WHITE}{problem_hash[:8]}{Style.RESET_ALL}")
        
    except Exception as e:
        log(f"{Fore.RED}Error adding to problem cache: {e}{Style.RESET_ALL}")

def log_failed_problem(problem_text, formula, answer, response_data, entities_info=None, calculation=None):
    """Log a failed problem to a text file.
    
    Args:
        problem_text: Original problem text
        formula: Formula used to solve the problem
        answer: Calculated answer
        response_data: API response data
        entities_info: Information about entities used (optional)
        calculation: Information about calculation performed (optional)
    """
    try:
        # Generate a hash for the problem text
        problem_hash = get_problem_hash(problem_text)
        
        # Create a timestamp
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Create the log filename
        log_file = os.path.join(LOGS_DIR, f"{problem_hash}.txt")
        
        # Clean up potential issues in formula
        if formula:
            # Fix spaces between quoted entity names and attributes
            formula = re.sub(r'("([^"]+)")\s+\.([a-zA-Z_][a-zA-Z0-9_]*)', r'\1.\3', formula)
        
        # Make sure LOGS_DIR exists
        if not os.path.exists(LOGS_DIR):
            os.makedirs(LOGS_DIR)
            log(f"{Fore.YELLOW}Created logs directory: {Fore.WHITE}{LOGS_DIR}{Style.RESET_ALL}")
        
        # Write the log file
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"FAILED PROBLEM LOG - {timestamp}\n")
            f.write("="*80 + "\n\n")
            
            f.write("PROBLEM TEXT:\n")
            f.write(f"{problem_text}\n\n")
            
            f.write("FORMULA:\n")
            f.write(f"{formula}\n\n")
            
            if entities_info:
                f.write("ENTITIES USED:\n")
                f.write(f"{entities_info}\n\n")
            
            if calculation:
                f.write("CALCULATION:\n")
                f.write(f"{calculation}\n\n")
            
            f.write("SUBMITTED ANSWER:\n")
            f.write(f"{answer}\n\n")
            
            f.write("API RESPONSE:\n")
            f.write(f"{json.dumps(response_data, indent=2)}\n\n")
            
            f.write("HASH:\n")
            f.write(f"{problem_hash}\n")
        
        log(f"{Fore.YELLOW}Failed problem logged to {Fore.WHITE}{log_file}{Style.RESET_ALL}")
        
    except Exception as e:
        log(f"{Fore.RED}Error logging failed problem: {e}{Style.RESET_ALL}") 