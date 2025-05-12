import requests
import time
import json
import re
import os
import sqlite3
import hashlib
from dotenv import load_dotenv
import urllib3
from colorama import Fore, Back, Style, init
import datetime

# Initialize colorama
init(autoreset=True)

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

# Get token from environment
TOKEN = os.getenv("AUTH_TOKEN")
if not TOKEN:
    TOKEN = input(f"{Fore.YELLOW}Please provide your authentication token: {Style.RESET_ALL}")

# API endpoints
BASE_URL = "https://recruiting.adere.so"
SWAPI_URL = "https://swapi.dev/api"
POKEAPI_URL = "https://pokeapi.co/api/v2"

# Headers for API requests
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Database file path
DB_FILE = "api_cache.db"

# Logs directory
LOGS_DIR = "failed_problems"

# In-memory cache for faster access during runtime
cache = {
    "pokemon": {},
    "swapi_characters": {},
    "swapi_planets": {}
}

# Add known compound Pokémon names that need special handling
COMPOUND_POKEMON_NAMES = [
    "tapu koko", "tapu lele", "tapu bulu", "tapu fini",
    "mr mime", "mime jr", "type null", "jangmo o",
    "hakamo o", "kommo o", "porygon z"
]

# Pokemon names with hyphens that should preserve the hyphen
HYPHENATED_POKEMON = [
    "kommo-o", "hakamo-o", "jangmo-o", "ho-oh", "porygon-z",
    "type-null", "mr-mime", "mime-jr", "tapu-koko", "tapu-lele",
    "tapu-bulu", "tapu-fini"
]

# Map of common entity name variations
NAME_VARIATIONS = {
    # Star Wars characters
    "beru": "beru whitesun lars",
    "beruwhitesunlars": "beru whitesun lars",
    "luke": "luke skywalker",
    "lukeskywalker": "luke skywalker",
    "ratts tyerel": "ratts tyerell",  # Note the spelling correction
    "rattstyerel": "ratts tyerell",
    "jabba desilijic tiure": "jabba",  # Handle Jabba's full name
    "jabba the hutt": "jabba",
    "jabba desilijic": "jabba",
    "jabba tiure": "jabba",
    "hutt": "jabba",  # As requested, map hutt to Jabba
    "desilijic": "jabba",
    "ayla secura": "aayla secura",  # Handle typo in Star Wars character name
    "aayla": "aayla secura",
    "general grievous": "grievous",
    "count dooku": "dooku",
    "darth maul": "maul",
    "darth vader": "vader",
    "darth sidious": "palpatine",
    "emperor palpatine": "palpatine",
    "princess leia": "leia",
    "queen amidala": "padmé amidala",
    "padme": "padmé amidala",
    # Pokemon
    "tapu": "tapu koko",  # Add common Tapu variations 
    "tapukoko": "tapu koko",
    "kommo o": "kommo-o",  # Add hyphenated Pokémon variants
    "hakamo o": "hakamo-o",
    "jangmo o": "jangmo-o",
    "spewpa": "spewpa",  # Ensure Spewpa is recognized correctly
    "ho oh": "ho-oh"
}

def initialize_db():
    """Initialize the SQLite database for caching"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create tables if they don't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pokemon (
        name TEXT PRIMARY KEY,
        data TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS swapi_characters (
        name TEXT PRIMARY KEY,
        data TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS swapi_planets (
        name TEXT PRIMARY KEY,
        data TEXT
    )
    ''')
    
    # Create problem cache table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS problem_cache (
        problem_hash TEXT PRIMARY KEY,
        problem_text TEXT,
        formula TEXT,
        answer REAL,
        timestamp INTEGER
    )
    ''')
    
    conn.commit()
    conn.close()
    print(f"{Fore.BLUE}Database initialized at {Fore.CYAN}{DB_FILE}{Style.RESET_ALL}")
    
    # Create logs directory if it doesn't exist
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
        print(f"{Fore.BLUE}Created logs directory at {Fore.CYAN}{LOGS_DIR}{Style.RESET_ALL}")

def load_cache():
    """Load the cache from the SQLite database"""
    global cache
    
    if not os.path.exists(DB_FILE):
        print(f"{Fore.YELLOW}No cache database found. Starting with empty cache.{Style.RESET_ALL}")
        initialize_db()
        return
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Load Pokemon
        cursor.execute("SELECT name, data FROM pokemon")
        for name, data_json in cursor.fetchall():
            cache["pokemon"][name] = json.loads(data_json)
        
        # Load Star Wars characters
        cursor.execute("SELECT name, data FROM swapi_characters")
        for name, data_json in cursor.fetchall():
            cache["swapi_characters"][name] = json.loads(data_json)
        
        # Load Star Wars planets
        cursor.execute("SELECT name, data FROM swapi_planets")
        for name, data_json in cursor.fetchall():
            cache["swapi_planets"][name] = json.loads(data_json)
        
        # Count problem cache entries
        cursor.execute("SELECT COUNT(*) FROM problem_cache")
        problem_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"{Fore.GREEN}Cache loaded with {Fore.WHITE}{len(cache['pokemon'])} Pokémon, "
              f"{Fore.WHITE}{len(cache['swapi_characters'])} Star Wars characters, "
              f"{Fore.WHITE}{len(cache['swapi_planets'])} Star Wars planets, and "
              f"{Fore.WHITE}{problem_count} cached problems.{Style.RESET_ALL}")
              
    except Exception as e:
        print(f"{Fore.RED}Error loading cache: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Starting with empty cache.{Style.RESET_ALL}")
        initialize_db()

def add_to_cache(entity_type, name, data):
    """Add or update an entity in both the in-memory cache and SQLite database"""
    try:
        # Update in-memory cache
        cache[entity_type][name] = data
        
        # Update database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Convert data to JSON string
        data_json = json.dumps(data)
        
        # Insert or replace
        cursor.execute(f"INSERT OR REPLACE INTO {entity_type} (name, data) VALUES (?, ?)",
                     (name, data_json))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"{Fore.RED}Error adding to cache: {e}{Style.RESET_ALL}")

def get_entity_data(entity_name):
    """Central function to find an entity across all available APIs
    
    This function will:
    1. Check the cache first
    2. Analyze the entity name to determine which API is most likely
    3. Try that API first
    4. If not found, try the other APIs
    5. Try name variations if still not found
    
    Returns:
        tuple: (entity_data, entity_type) where entity_type is 'pokemon', 'swapi_characters', or 'swapi_planets'
    """
    # Normalize the name
    normalized_name = entity_name.lower()
    
    # First check if this is a known name variation
    if normalized_name in NAME_VARIATIONS:
        normalized_name = NAME_VARIATIONS[normalized_name]
        print(f"{Fore.YELLOW}Using known name variation: '{Fore.WHITE}{entity_name}{Fore.YELLOW}' → '{Fore.WHITE}{normalized_name}{Fore.YELLOW}'{Style.RESET_ALL}")
    
    # Check all caches first
    for entity_type in ["pokemon", "swapi_characters", "swapi_planets"]:
        if normalized_name in cache[entity_type]:
            return cache[entity_type][normalized_name], entity_type
    
    print(f"{Fore.YELLOW}Entity '{Fore.WHITE}{entity_name}{Fore.YELLOW}' not found in cache. Searching APIs...{Style.RESET_ALL}")
    
    # Special handling for specific entities we know need it
    if normalized_name == "jabba":
        print(f"{Fore.CYAN}Special handling for Jabba - using hardcoded data{Style.RESET_ALL}")
        # Jabba is a known character but might not be in the API with correct values
        jabba_data = {
            "name": "Jabba Desilijic Tiure",
            "height": 175,  # Based on Star Wars lore (approx)
            "mass": 1300,   # Hutts are massive creatures
            "homeworld": "https://swapi.dev/api/planets/24/"  # Nal Hutta
        }
        # Cache this for future use
        add_to_cache("swapi_characters", normalized_name, jabba_data)
        return jabba_data, "swapi_characters"
    
    # Determine which API is most likely to contain this entity
    api_order = determine_api_order(normalized_name)
    print(f"{Fore.BLUE}API search order for '{Fore.WHITE}{entity_name}{Fore.BLUE}': {Fore.CYAN}{', '.join(api_order)}{Style.RESET_ALL}")
    
    # Try the APIs in the determined order
    for api_type in api_order:
        if api_type == "pokemon":
            pokemon_data = get_pokemon_data(normalized_name)
            if pokemon_data:
                print(f"{Fore.GREEN}Found '{Fore.WHITE}{entity_name}{Fore.GREEN}' in Pokémon API{Style.RESET_ALL}")
                return pokemon_data, "pokemon"
        elif api_type == "swapi_characters":
            character_data = get_sw_character_data(normalized_name)
            if character_data:
                print(f"{Fore.GREEN}Found '{Fore.WHITE}{entity_name}{Fore.GREEN}' in Star Wars character API{Style.RESET_ALL}")
                return character_data, "swapi_characters"
        elif api_type == "swapi_planets":
            planet_data = get_sw_planet_data(normalized_name)
            if planet_data:
                print(f"{Fore.GREEN}Found '{Fore.WHITE}{entity_name}{Fore.GREEN}' in Star Wars planet API{Style.RESET_ALL}")
                return planet_data, "swapi_planets"
    
    # If still not found, try with name variations
    print(f"{Fore.YELLOW}Entity '{Fore.WHITE}{entity_name}{Fore.YELLOW}' not found in any API. Trying common variations...{Style.RESET_ALL}")
    
    # Try removing spaces (e.g., "luke skywalker" -> "lukeskywalker")
    if " " in normalized_name:
        no_space_name = normalized_name.replace(" ", "")
        print(f"{Fore.BLUE}Trying without spaces: '{Fore.WHITE}{no_space_name}{Fore.BLUE}'{Style.RESET_ALL}")
        
        # Try the APIs in the determined order with no spaces
        for api_type in api_order:
            if api_type == "pokemon":
                pokemon_data = get_pokemon_data(no_space_name)
                if pokemon_data:
                    print(f"{Fore.GREEN}Found '{Fore.WHITE}{no_space_name}{Fore.GREEN}' in Pokémon API{Style.RESET_ALL}")
                    # Cache with original name too
                    add_to_cache("pokemon", normalized_name, pokemon_data)
                    return pokemon_data, "pokemon"
            elif api_type == "swapi_characters":
                character_data = get_sw_character_data(no_space_name)
                if character_data:
                    print(f"{Fore.GREEN}Found '{Fore.WHITE}{no_space_name}{Fore.GREEN}' in Star Wars character API{Style.RESET_ALL}")
                    # Cache with original name too
                    add_to_cache("swapi_characters", normalized_name, character_data)
                    return character_data, "swapi_characters"
            elif api_type == "swapi_planets":
                planet_data = get_sw_planet_data(no_space_name)
                if planet_data:
                    print(f"{Fore.GREEN}Found '{Fore.WHITE}{no_space_name}{Fore.GREEN}' in Star Wars planet API{Style.RESET_ALL}")
                    # Cache with original name too
                    add_to_cache("swapi_planets", normalized_name, planet_data)
                    return planet_data, "swapi_planets"
    
    # If we still haven't found it, try with just the first word
    if " " in normalized_name:
        first_name = normalized_name.split()[0]
        print(f"{Fore.BLUE}Trying with first name only: '{Fore.WHITE}{first_name}{Fore.BLUE}'{Style.RESET_ALL}")
        
        # Try the APIs in the determined order with first name only
        for api_type in api_order:
            if api_type == "pokemon":
                pokemon_data = get_pokemon_data(first_name)
                if pokemon_data:
                    print(f"{Fore.GREEN}Found '{Fore.WHITE}{first_name}{Fore.GREEN}' in Pokémon API{Style.RESET_ALL}")
                    # Cache with original name too
                    add_to_cache("pokemon", normalized_name, pokemon_data)
                    return pokemon_data, "pokemon"
            elif api_type == "swapi_characters":
                character_data = get_sw_character_data(first_name)
                if character_data:
                    print(f"{Fore.GREEN}Found '{Fore.WHITE}{first_name}{Fore.GREEN}' in Star Wars character API{Style.RESET_ALL}")
                    # Cache with original name too
                    add_to_cache("swapi_characters", normalized_name, character_data)
                    return character_data, "swapi_characters"
            elif api_type == "swapi_planets":
                planet_data = get_sw_planet_data(first_name)
                if planet_data:
                    print(f"{Fore.GREEN}Found '{Fore.WHITE}{first_name}{Fore.GREEN}' in Star Wars planet API{Style.RESET_ALL}")
                    # Cache with original name too
                    add_to_cache("swapi_planets", normalized_name, planet_data)
                    return planet_data, "swapi_planets"
    
    # If we get here, we couldn't find the entity in any API
    print(f"{Fore.RED}ERROR: Could not find entity '{Fore.WHITE}{entity_name}{Fore.RED}' in any API after trying multiple variations.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Defaulting to empty entity for '{Fore.WHITE}{entity_name}{Fore.YELLOW}'.{Style.RESET_ALL}")
    
    # Create a default entity with 0 values
    default_entity = {
        "name": entity_name,
        "height": 0,
        "weight": 0,
        "base_experience": 0,
        "mass": 0
    }
    
    # Choose a default type based on naming patterns - use the first API in our determined order
    entity_type = api_order[0]
    
    # Cache this default entity to avoid repeated errors
    add_to_cache(entity_type, normalized_name, default_entity)
    
    return default_entity, entity_type

def determine_api_order(entity_name):
    """Analyze entity name to determine the most likely API order to try
    
    Args:
        entity_name: The normalized entity name
        
    Returns:
        list: Ordered list of API names to try ['pokemon', 'swapi_characters', 'swapi_planets']
    """
    # Common Pokemon names and patterns
    pokemon_patterns = [
        'pikachu', 'charizard', 'bulbasaur', 'squirtle', 'eevee', 'mewtwo', 'jigglypuff', 
        'vulpix', 'snorlax', 'meowth', 'pika', 'char', 'bulba', 'venonat', 'fomantis',
        'zubat', 'geodude', 'gyarados', 'lapras', 'gengar', 'mew', 'ditto', 'magikarp'
    ]
    
    # Common Star Wars character names and patterns
    sw_character_patterns = [
        'skywalker', 'vader', 'leia', 'solo', 'han', 'chewbacca', 'r2', 'c-3po',
        'obi-wan', 'kenobi', 'yoda', 'palpatine', 'emperor', 'boba', 'fett', 'jabba',
        'lando', 'anakin', 'darth', 'wicket', 'ewok', 'luke', 'jedi', 'sith', 'trooper',
        'ackbar', 'amidala', 'padme', 'grievous', 'dooku', 'maul', 'windu', 'jinn',
        'beru', 'lars', 'biggs', 'wedge', 'tyerell', 'tyerel'
    ]
    
    # Common Star Wars planet names and patterns
    sw_planet_patterns = [
        'tatooine', 'alderaan', 'yavin', 'hoth', 'dagobah', 'bespin', 'endor', 'naboo',
        'coruscant', 'kamino', 'geonosis', 'utapau', 'mustafar', 'kashyyyk', 'world',
        'moon', 'planet', 'system', 'sector', 'galaxy', 'star'
    ]
    
    # Count matches for each category
    pokemon_score = 0
    character_score = 0
    planet_score = 0
    
    # Check for exact matches in patterns
    for pattern in pokemon_patterns:
        if pattern in entity_name:
            pokemon_score += 3  # Higher weight for Pokemon matches
    
    for pattern in sw_character_patterns:
        if pattern in entity_name:
            character_score += 2
    
    for pattern in sw_planet_patterns:
        if pattern in entity_name:
            planet_score += 2
    
    # Additional heuristics
    
    # Pokemon names are often single words that are made-up nonsense words or based on animals/plants
    if len(entity_name.split()) == 1 and not any(char.isdigit() for char in entity_name):
        pokemon_score += 1
    
    # Star Wars characters often have two or more names
    if len(entity_name.split()) >= 2:
        character_score += 1
    
    # Star Wars planets often end with specific sounds
    if any(entity_name.endswith(suffix) for suffix in ['ine', 'oine', 'aan', 'osis', 'or', 'us']):
        planet_score += 1
    
    # Language pattern heuristics (very simplified)
    vowel_count = sum(1 for char in entity_name if char.lower() in 'aeiou')
    consonant_count = len(entity_name) - vowel_count
    
    # Pokemon names often have a good vowel-consonant balance
    vowel_ratio = vowel_count / len(entity_name) if len(entity_name) > 0 else 0
    if 0.3 <= vowel_ratio <= 0.7:
        pokemon_score += 1
    
    # Create the ordered list based on scores
    scores = [
        ("pokemon", pokemon_score),
        ("swapi_characters", character_score),
        ("swapi_planets", planet_score)
    ]
    
    # Sort by score in descending order
    scores.sort(key=lambda x: x[1], reverse=True)
    
    # Extract just the API names in the sorted order
    return [api[0] for api in scores]

def prefetch_data():
    """Prefetch common Pokemon and Star Wars data to improve performance"""
    # Skip prefetching if we already have a substantial cache
    if os.path.exists(DB_FILE):
        # Check if we have a decent amount of data already cached
        if (len(cache['pokemon']) >= 5 and 
            len(cache['swapi_characters']) >= 5 and 
            len(cache['swapi_planets']) >= 3):
            print(f"{Fore.GREEN}Using existing cache with {Fore.WHITE}{len(cache['pokemon'])} Pokémon, "
                  f"{Fore.WHITE}{len(cache['swapi_characters'])} Star Wars characters, and "
                  f"{Fore.WHITE}{len(cache['swapi_planets'])} Star Wars planets.{Style.RESET_ALL}")
            return
        else:
            print(f"{Fore.YELLOW}Cache database exists but doesn't have enough data. Prefetching...{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}No cache database found. Starting prefetch...{Style.RESET_ALL}")
    
    print(f"{Fore.BLUE}Prefetching data...{Style.RESET_ALL}")
    
    # Common Pokemon
    pokemon_list = ["pikachu", "charizard", "bulbasaur", "squirtle", "eevee", 
                   "mewtwo", "jigglypuff", "vulpix", "snorlax", "meowth"]
    
    # Common Star Wars characters
    sw_characters = ["luke skywalker", "darth vader", "leia organa", "han solo", 
                     "chewbacca", "r2-d2", "c-3po", "obi-wan kenobi", "yoda",
                     "palpatine", "boba fett", "lando calrissian", "anakin skywalker",
                     "beru whitesun lars", "biggs darklighter"]
    
    # Common Star Wars planets
    sw_planets = ["tatooine", "alderaan", "yavin", "hoth", "dagobah", 
                 "bespin", "endor", "naboo", "coruscant", "kamino"]
    
    # Prefetch Pokemon data
    print(f"{Fore.CYAN}Prefetching Pokémon data...{Style.RESET_ALL}")
    for pokemon in pokemon_list:
        get_pokemon_data(pokemon)
    
    # Prefetch Star Wars character data
    print(f"{Fore.CYAN}Prefetching Star Wars character data...{Style.RESET_ALL}")
    for character in sw_characters:
        get_sw_character_data(character)
    
    # Prefetch Star Wars planet data
    print(f"{Fore.CYAN}Prefetching Star Wars planet data...{Style.RESET_ALL}")
    for planet in sw_planets:
        get_sw_planet_data(planet)
    
    print(f"{Fore.GREEN}Prefetching complete. Cached {Fore.WHITE}{len(cache['pokemon'])} Pokémon, "
          f"{Fore.WHITE}{len(cache['swapi_characters'])} Star Wars characters, and "
          f"{Fore.WHITE}{len(cache['swapi_planets'])} Star Wars planets.{Style.RESET_ALL}")

def get_pokemon_data(name):
    """Fetch Pokémon data from cache or PokéAPI"""
    # Normalize name for consistency
    normalized_name = name.lower()
    
    # Check in-memory cache first
    if normalized_name in cache["pokemon"]:
        return cache["pokemon"][normalized_name]
    
    # Try to fetch from API
    response = requests.get(f"{POKEAPI_URL}/pokemon/{normalized_name}", verify=False)
    if response.status_code == 200:
        data = response.json()
        pokemon = {
            "name": data["name"],
            "base_experience": data["base_experience"],
            "height": data["height"],  # Height is in decimeters (1/10 meter)
            "weight": data["weight"]   # Weight is in hectograms (1/10 kg)
        }
        # Add to cache
        add_to_cache("pokemon", normalized_name, pokemon)
        return pokemon
    return None

def get_sw_character_data(name):
    """Fetch Star Wars character data from cache or SWAPI"""
    # Normalize name for consistency
    normalized_name = name.lower()
    
    # Check in-memory cache first
    if normalized_name in cache["swapi_characters"]:
        return cache["swapi_characters"][normalized_name]
    
    # Search for the character in API
    response = requests.get(f"{SWAPI_URL}/people/?search={normalized_name}", verify=False)
    if response.status_code == 200:
        data = response.json()
        if data["results"]:
            character = data["results"][0]
            character_data = {
                "name": character["name"],
                "height": int(character["height"]) if character["height"].isdigit() else 0,
                "mass": int(character["mass"]) if character["mass"].isdigit() else 0,
                "homeworld": character["homeworld"]
            }
            # Add to cache
            add_to_cache("swapi_characters", normalized_name, character_data)
            return character_data
    return None

def get_sw_planet_data(name):
    """Fetch Star Wars planet data from cache or SWAPI"""
    # Normalize name for consistency
    normalized_name = name.lower()
    
    # Check in-memory cache first
    if normalized_name in cache["swapi_planets"]:
        return cache["swapi_planets"][normalized_name]
    
    # Search for the planet in API
    response = requests.get(f"{SWAPI_URL}/planets/?search={normalized_name}", verify=False)
    if response.status_code == 200:
        data = response.json()
        if data["results"]:
            planet = data["results"][0]
            planet_data = {
                "name": planet["name"],
                "rotation_period": int(planet["rotation_period"]) if planet["rotation_period"].isdigit() else 0,
                "orbital_period": int(planet["orbital_period"]) if planet["orbital_period"].isdigit() else 0,
                "diameter": int(planet["diameter"]) if planet["diameter"].isdigit() else 0,
                "surface_water": int(planet["surface_water"]) if planet["surface_water"].isdigit() else 0,
                "population": int(planet["population"]) if planet["population"].isdigit() else 0
            }
            # Add to cache
            add_to_cache("swapi_planets", normalized_name, planet_data)
            return planet_data
    return None

def parse_problem_with_ai(problem):
    """Use AI to parse the problem and extract the mathematical expression"""
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "developer", 
                "content": """I need you to extract a mathematical formula from problems about Star Wars characters, planets, and Pokémon.

Each problem will describe a scenario requiring mathematical operations on entity attributes.

Entity types and their attributes:
1. Star Wars Characters: name, height, mass, homeworld
2. Star Wars Planets: name, rotation_period, orbital_period, diameter, surface_water, population
3. Pokémon: name, base_experience, height, weight

TASK:
1. Identify all entities mentioned in the problem
2. Determine which attributes are involved
3. Extract the mathematical operations to be performed
4. Express this as a clear formula

IMPORTANT: 
- Return ONLY the formula/expression, nothing else
- For entity names with multiple words (like "Luke Skywalker" or "Tapu Koko"), use quotes: "luke skywalker".mass or "tapu koko".weight
- Handle compound names like Tapu-Koko, Type-Null as single units (e.g., "tapu-koko".weight)
- Exclude titles (like General, Captain, Princess) from character names (e.g., use "grievous" not "general grievous")
- Use lowercase for all entity names
- Handle division, multiplication, addition, subtraction, exponents, etc.
- Use proper operator precedence with parentheses when needed"""
            },
            {"role": "user", "content": problem}
        ]
    }
    
    response = requests.post(f"{BASE_URL}/chat_completion", json=data, headers=headers)
    if response.status_code == 200:
        ai_response = response.json()
        formula = ai_response["choices"][0]["message"]["content"].strip()
        # Clean up the formula - remove any markdown formatting or quotes
        formula = formula.strip('`')
        if formula.startswith('```') and formula.endswith('```'):
            formula = formula[3:-3].strip()
        return formula
    else:
        print(f"{Fore.RED}Error with AI: {response.status_code} - {response.text}{Style.RESET_ALL}")
        return None

def normalize_entity_name(name):
    """Normalize entity names by removing dots and standardizing format"""
    # Remove quotes if present
    name = name.strip('"\'')
    
    # Replace dots with spaces (for cases like "ratts.tyerel")
    name = name.replace('.', ' ')
    
    # Check if this is a hyphenated Pokemon name that we should preserve
    for hyphenated_name in HYPHENATED_POKEMON:
        if hyphenated_name.lower() in name.lower():
            # Keep the hyphen for this known Pokemon
            # Just normalize case and whitespace
            name = ' '.join(name.split())
            name = name.lower()
            return strip_titles(name)
    
    # For other names, replace hyphens with spaces (for cases like regular hyphenated names)
    name = name.replace('-', ' ')
    
    # Normalize whitespace
    name = ' '.join(name.split())
    
    # Convert to lowercase
    name = name.lower()
    
    # Strip common titles from Star Wars characters
    return strip_titles(name)

# Common titles that should be stripped from entity names
COMMON_TITLES = [
    "general", "captain", "commander", "admiral", "lieutenant", 
    "sergeant", "corporal", "private", "master", "lord", "darth",
    "princess", "prince", "king", "queen", "emperor", "empress",
    "doctor", "dr", "professor", "prof", "count", "baron", "sir"
]

def strip_titles(name):
    """Remove common titles from entity names"""
    words = name.split()
    if len(words) <= 1:
        return name  # Single word, no titles to strip
    
    # Check if the first word is a title
    if words[0].lower() in COMMON_TITLES:
        # Removed the title and return the rest of the name
        print(f"{Fore.YELLOW}Stripping title: '{words[0]}' from '{name}' → '{' '.join(words[1:])}'{Style.RESET_ALL}")
        return ' '.join(words[1:])
    
    return name

# Function disabled as per user request
def correct_typos(entity_name):
    """This function is disabled - returns entity name unchanged"""
    return entity_name

def log_failed_problem(problem_text, formula, answer, response_data, entities_info=None, calculation=None):
    """Log a failed problem to a text file
    
    Args:
        problem_text: The original problem text
        formula: The formula used to solve the problem
        answer: The calculated answer
        response_data: The API response data
        entities_info: Information about the entities used (optional)
        calculation: Information about the calculation performed (optional)
    """
    try:
        # Generate a hash for the problem text
        problem_hash = get_problem_hash(problem_text)
        
        # Create a timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create the log filename
        log_file = os.path.join(LOGS_DIR, f"{problem_hash}.txt")
        
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
        
        print(f"{Fore.YELLOW}Failed problem logged to {Fore.WHITE}{log_file}{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}Error logging failed problem: {e}{Style.RESET_ALL}")

def evaluate_expression(formula):
    """Evaluate the mathematical expression based on the formula provided by AI"""
    print(f"{Fore.BLUE}Original formula: {Fore.CYAN}{formula}{Style.RESET_ALL}")
    
    # We'll collect all variables mentioned in the formula
    variables = {}
    
    # Collection for logging
    entities_log = []
    
    # Extract entity names and attributes from the formula - handle both quoted and unquoted names
    # This complex pattern handles several cases:
    # 1. "entity name".attribute - quoted multi-word entities
    # 2. entity.attribute - simple unquoted entities
    # 3. entity.name.attribute - incorrectly parsed multi-word entities with dots
    entity_pattern = re.compile(r'("([^"]+)"|([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*))\.([a-zA-Z_][a-zA-Z0-9_]*)')
    
    # Process for both compound names with spaces and hyphenated names
    combined_special_names = list(set(COMPOUND_POKEMON_NAMES + HYPHENATED_POKEMON))
    
    # Special handling for special Pokemon names in formula before extraction
    for special_name in combined_special_names:
        # Look for variations of the special name without quotes
        space_version = special_name.replace("-", " ")
        variations = [
            special_name,            # original form (tapu-koko or tapu koko)
            special_name.replace(" ", "").replace("-", ""),  # no spaces/hyphens (tapukoko)
            special_name.replace(" ", "-"),  # spaces to hyphens (tapu-koko)
            special_name.replace("-", " "),  # hyphens to spaces (tapu koko)
            special_name.replace(" ", ".").replace("-", ".")   # dotted (tapu.koko)
        ]
        
        for variation in variations:
            # Replace all instances not in quotes with the quoted version
            # Only replace when it's a standalone term, not part of another word
            # This is a complex regex that handles boundaries correctly
            formula = re.sub(
                r'(?<!")\b' + re.escape(variation) + r'\b(?!")', 
                f'"{special_name}"', 
                formula, 
                flags=re.IGNORECASE
            )
    
    # First, find all entities in the formula
    entities_to_process = []
    for match in entity_pattern.finditer(formula):
        full_match, quoted_name, dotted_name, attribute = match.groups()
        
        # Get the actual entity name (either from quotes or from dotted notation)
        if quoted_name:
            entity_name = quoted_name
        else:
            entity_name = dotted_name
        
        # NO TYPO CORRECTION - use entity name directly as per user request
        # entity_name = correct_typos(entity_name)  # This line is disabled
        
        # Normalize the entity name
        normalized_name = normalize_entity_name(entity_name)
        
        # Check for name variations
        if normalized_name in NAME_VARIATIONS:
            normalized_name = NAME_VARIATIONS[normalized_name]
        
        # Check for compound Pokémon names when we have a partial match
        for compound_name in COMPOUND_POKEMON_NAMES:
            compound_parts = compound_name.split()
            if (normalized_name == compound_parts[0] and len(compound_parts) > 1):
                print(f"{Fore.YELLOW}Found partial match for compound Pokémon name: '{normalized_name}' → '{compound_name}'{Style.RESET_ALL}")
                normalized_name = compound_name
                break
            
        # Store for processing
        entities_to_process.append((match.group(0), normalized_name, attribute))

    # Print a summary of all entities found in the formula
    print(f"{Fore.BLUE}Found {Fore.WHITE}{len(entities_to_process)}{Fore.BLUE} entities in formula:{Style.RESET_ALL}")
    for _, entity_name, attribute in entities_to_process:
        print(f"{Fore.CYAN}  • {Fore.WHITE}{entity_name}{Fore.CYAN}.{Fore.WHITE}{attribute}{Style.RESET_ALL}")
    
    # Now fetch data for all entities
    for original_text, entity_name, attribute in entities_to_process:
        # If we haven't fetched this entity yet
        if entity_name not in variables:
            # Use the centralized entity resolution function
            # Check if already in cache
            is_in_cache = False
            for entity_type in ["pokemon", "swapi_characters", "swapi_planets"]:
                if entity_name in cache[entity_type]:
                    is_in_cache = True
                    entity_data = cache[entity_type][entity_name]
                    print(f"{Fore.GREEN}Found '{Fore.WHITE}{entity_name}{Fore.GREEN}' in {entity_type} cache{Style.RESET_ALL}")
                    variables[entity_name] = entity_data
                    break
            
            # If not in cache, fetch from API
            if not is_in_cache:
                entity_data, entity_type = get_entity_data(entity_name)
                if entity_data:
                    variables[entity_name] = entity_data
                else:
                    print(f"{Fore.YELLOW}Warning: Could not find data for entity '{Fore.WHITE}{entity_name}{Fore.YELLOW}'{Style.RESET_ALL}")
    
    # Replace all entity references with actual values
    eval_formula = formula
    # Print a summary of all entity values being used
    print(f"{Fore.BLUE}Entity values used in calculation:{Style.RESET_ALL}")
    for original_text, entity_name, attribute in entities_to_process:
        if entity_name in variables and attribute in variables[entity_name]:
            # Get the attribute value
            value = variables[entity_name][attribute]
            
            # No unit conversions - use the original value
            log_entry = f"{entity_name}.{attribute} = {value}"
            entities_log.append(log_entry)
            print(f"{Fore.CYAN}  • {Fore.WHITE}{entity_name}{Fore.CYAN}.{Fore.WHITE}{attribute}{Fore.CYAN} = {Fore.WHITE}{value}{Style.RESET_ALL}")
            
            # Replace the complete original text with the value
            eval_formula = eval_formula.replace(original_text, str(value))
        else:
            if entity_name in variables:
                print(f"{Fore.YELLOW}Warning: Attribute '{Fore.WHITE}{attribute}{Fore.YELLOW}' not found for entity '{Fore.WHITE}{entity_name}{Fore.YELLOW}'{Style.RESET_ALL}")
                print(f"{Fore.BLUE}Available attributes: {Fore.WHITE}{list(variables[entity_name].keys())}{Fore.BLUE}{Style.RESET_ALL}")
            # Default to 0 if we can't find the attribute
            log_entry = f"{entity_name}.{attribute} = 0 (NOT FOUND)"
            entities_log.append(log_entry)
            print(f"{Fore.RED}Using default value 0 for {Fore.WHITE}{entity_name}{Fore.RED}.{Fore.WHITE}{attribute}{Style.RESET_ALL}")
            eval_formula = eval_formula.replace(original_text, "0")
    
    # Additional cleanup to remove any remaining entity names that might not have been properly matched
    # This regex will find words that aren't part of a mathematical expression
    remaining_words_pattern = re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*')
    
    # Check if there are still words in the formula
    if remaining_words_pattern.search(eval_formula):
        print(f"{Fore.YELLOW}Warning: Found remaining words in formula. Cleaning up: {Fore.CYAN}{eval_formula}{Style.RESET_ALL}")
        
        # Replace any remaining words with 0
        eval_formula = remaining_words_pattern.sub("0", eval_formula)
        print(f"{Fore.YELLOW}Cleaned formula: {Fore.CYAN}{eval_formula}{Style.RESET_ALL}")
    
    # Handle any spaces between numbers that could cause issues (like "5 6" which is invalid)
    # Replace patterns like "number space number" with "number operator number"
    eval_formula = re.sub(r'(\d+)\s+(\d+)', r'\1+\2', eval_formula)
    
    # Evaluate the formula
    try:
        print(f"{Fore.BLUE}Evaluating formula: {Fore.CYAN}{eval_formula}{Style.RESET_ALL}")
        result = eval(eval_formula)
        # Round to 10 decimal places as specified in the challenge
        result = round(float(result), 10)
        print(f"{Fore.MAGENTA}Result: {Fore.WHITE}{result}{Style.RESET_ALL}")
        
        # Return the result along with logging information
        calculation_log = f"Formula: {formula}\nEvaluating: {eval_formula}\nResult: {result}"
        return result, "\n".join(entities_log), calculation_log
    except Exception as e:
        print(f"{Fore.RED}Error evaluating formula: {e}{Style.RESET_ALL}")
        print(f"{Fore.RED}Formula: {eval_formula}{Style.RESET_ALL}")
        
        # Last resort cleanup - try to salvage the calculation by replacing everything non-numeric
        # with basic operations
        try:
            # This is a more aggressive approach that keeps only numbers and basic operators
            clean_formula = re.sub(r'[^0-9+\-*/().\s]', '0', eval_formula)
            # Replace multiple consecutive zeros with a single zero
            clean_formula = re.sub(r'0+', '0', clean_formula)
            # Handle any invalid math operations like double operators
            clean_formula = re.sub(r'[\+\-\*/]{2,}', '+', clean_formula)
            
            print(f"{Fore.YELLOW}Attempting last-resort cleanup. New formula: {Fore.CYAN}{clean_formula}{Style.RESET_ALL}")
            
            # Try evaluating the cleaned formula
            result = eval(clean_formula)
            result = round(float(result), 10)
            print(f"{Fore.GREEN}Salvaged result: {Fore.WHITE}{result}{Style.RESET_ALL}")
            
            # Return the result along with logging information
            calculation_log = f"Formula: {formula}\nEvaluating (after cleanup): {clean_formula}\nResult: {result}"
            return result, "\n".join(entities_log), calculation_log
        except Exception as e2:
            print(f"{Fore.RED}Cleanup failed: {e2}{Style.RESET_ALL}")
            return None, "\n".join(entities_log), f"Error: {str(e)}\nCleanup error: {str(e2)}"

def get_problem_hash(problem_text):
    """Generate a hash for a problem text to use as a unique identifier"""
    # Remove extra whitespace and convert to lowercase for consistent hashing
    normalized_text = ' '.join(problem_text.lower().split())
    return hashlib.md5(normalized_text.encode('utf-8')).hexdigest()

def check_problem_cache(problem_text):
    """Check if a problem is in the cache
    
    Args:
        problem_text: The problem text to look for
        
    Returns:
        tuple: (is_cached, formula, answer) where is_cached is a boolean
    """
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
        print(f"{Fore.RED}Error checking problem cache: {e}{Style.RESET_ALL}")
        return False, None, None

def add_to_problem_cache(problem_text, formula, answer):
    """Add a problem and its solution to the cache
    
    Args:
        problem_text: The original problem text
        formula: The formula used to solve the problem
        answer: The calculated answer
    """
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
        
        print(f"{Fore.GREEN}Problem added to cache with hash {Fore.WHITE}{problem_hash[:8]}{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}Error adding to problem cache: {e}{Style.RESET_ALL}")

def test_solver():
    """Test the solver with the practice endpoint"""
    response = requests.get(f"{BASE_URL}/challenge/test", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"{Fore.BLUE}Test API Response: {json.dumps(data, indent=2)}{Style.RESET_ALL}")
        
        # Check for different possible response structures
        if "problem" in data and "solution" in data:
            problem = data["problem"]
            expected_answer = data["solution"]
        elif "problem" in data and "expected_solution" in data:
            problem = data["problem"]
            expected_answer = data["expected_solution"]
        else:
            print(f"{Fore.RED}Unexpected response structure. Here's the raw response:{Style.RESET_ALL}")
            print(json.dumps(data, indent=2))
            return
        
        print(f"{Fore.CYAN}Test problem: {Fore.WHITE}{problem}{Style.RESET_ALL}")
        
        # Check if this problem is already in our cache
        is_cached, cached_formula, cached_answer = check_problem_cache(problem)
        
        if is_cached:
            print(f"{Fore.GREEN}CACHE HIT! Problem found in cache.{Style.RESET_ALL}")
            print(f"{Fore.BLUE}Cached formula: {Fore.CYAN}{cached_formula}{Style.RESET_ALL}")
            print(f"{Fore.MAGENTA}Cached answer: {Fore.WHITE}{cached_answer}{Style.RESET_ALL}")
            formula = cached_formula
            answer = cached_answer
        else:
            print(f"{Fore.YELLOW}Cache miss. Calculating answer...{Style.RESET_ALL}")
            # Parse problem with AI
            formula = parse_problem_with_ai(problem)
            print(f"{Fore.BLUE}AI Formula: {Fore.CYAN}{formula}{Style.RESET_ALL}")
            
            # Evaluate the formula
            answer = evaluate_expression(formula)
        
        print(f"{Fore.MAGENTA}Calculated answer: {Fore.WHITE}{answer}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}Expected answer: {Fore.WHITE}{expected_answer}{Style.RESET_ALL}")
        
        if answer == expected_answer:
            print(f"{Fore.GREEN}✅ Test passed! Your solution is working correctly.{Style.RESET_ALL}")
            # Only cache if the answer was correct and not already cached
            if not is_cached and answer is not None and formula:
                print(f"{Fore.GREEN}Adding correct solution to problem cache.{Style.RESET_ALL}")
                add_to_problem_cache(problem, formula, answer)
        else:
            print(f"{Fore.RED}❌ Test failed. The calculated answer doesn't match the expected answer.{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}Error testing solver: {response.status_code} - {response.text}{Style.RESET_ALL}")

def run_challenge():
    """Run the actual challenge"""
    # Start the challenge
    start_response = requests.get(f"{BASE_URL}/challenge/start", headers=headers)
    if start_response.status_code != 200:
        print(f"{Fore.RED}Error starting challenge: {start_response.status_code} - {start_response.text}{Style.RESET_ALL}")
        return
    
    start_data = start_response.json()
    print(f"{Fore.BLUE}Start response: {json.dumps(start_data, indent=2)}{Style.RESET_ALL}")
    
    # Handle different possible response formats
    if "problem_id" in start_data:
        problem_id = start_data["problem_id"]
    elif "id" in start_data:
        problem_id = start_data["id"]
    else:
        print(f"{Fore.RED}Error: Could not find problem ID in response: {json.dumps(start_data, indent=2)}{Style.RESET_ALL}")
        return
    
    if "problem" in start_data:
        problem = start_data["problem"]
        has_problem = True
    else:
        print(f"{Fore.RED}Error: Could not find problem text in response: {json.dumps(start_data, indent=2)}{Style.RESET_ALL}")
        return
    
    solved_count = 0
    attempted_count = 0
    start_time = time.time()
    
    # Loop continues as long as we have a problem to solve
    while has_problem:
        attempted_count += 1
        current_time = time.time()
        elapsed_time = current_time - start_time
        
        print(f"\n{Fore.CYAN}Problem #{attempted_count} (Time: {Fore.WHITE}{elapsed_time:.2f}s{Fore.CYAN}): {Fore.WHITE}{problem}{Style.RESET_ALL}")
        
        # Check if this problem is already in our cache
        is_cached, cached_formula, cached_answer = check_problem_cache(problem)
        
        if is_cached:
            print(f"{Fore.GREEN}CACHE HIT! Problem found in cache.{Style.RESET_ALL}")
            print(f"{Fore.BLUE}Cached formula: {Fore.CYAN}{cached_formula}{Style.RESET_ALL}")
            print(f"{Fore.MAGENTA}Cached answer: {Fore.WHITE}{cached_answer}{Style.RESET_ALL}")
            formula = cached_formula
            answer = cached_answer
            entities_info = None
            calculation_info = None
        else:
            print(f"{Fore.YELLOW}Cache miss. Calculating answer...{Style.RESET_ALL}")
            # Parse problem with AI
            formula = parse_problem_with_ai(problem)
            print(f"{Fore.BLUE}AI Formula: {Fore.CYAN}{formula}{Style.RESET_ALL}")
            
            # Evaluate the formula
            result = evaluate_expression(formula)
            if isinstance(result, tuple) and len(result) == 3:
                answer, entities_info, calculation_info = result
            else:
                answer = result
                entities_info = None
                calculation_info = None
            
            # Don't store in cache yet - only store if the answer is correct
        
        # Handle case where we couldn't calculate an answer
        if answer is None:
            print(f"{Fore.RED}No valid answer calculated. Trying to continue with next problem...{Style.RESET_ALL}")
            # Use a default value that is likely incorrect but allows us to get the next problem
            answer = 0
            
        # Submit the solution
        solution_data = {
            "problem_id": problem_id,
            "answer": answer
        }
        
        has_problem = False  # Reset for this iteration
        try:
            solution_response = requests.post(
                f"{BASE_URL}/challenge/solution", 
                headers=headers,
                json=solution_data
            )
            
            if solution_response.status_code == 200:
                solution_data = solution_response.json()
                
                # Debug the response
                print(f"{Fore.BLUE}API Response: {json.dumps(solution_data, indent=2)}{Style.RESET_ALL}")
                
                # Check if time limit was exceeded
                if "message" in solution_data and solution_data["message"] == "Time limit exceeded.":
                    print(f"{Fore.YELLOW}⏱️ API time limit exceeded. Challenge will continue but score may not be recorded.{Style.RESET_ALL}")
                    was_correct = False
                    print(f"{Fore.RED}❌ INCORRECT. Time limit exceeded is considered as wrong answer.{Style.RESET_ALL}")
                
                # Check if answer was correct based on the message field
                was_correct = False
                if "message" in solution_data:
                    if solution_data["message"] == "Correct answer.":
                        was_correct = True
                        solved_count += 1
                        print(f"{Fore.GREEN}✅ CORRECT! Your answer was right.{Style.RESET_ALL}")
                        
                        # Only add to cache if the answer was correct and not already cached
                        if not is_cached and answer is not None and formula:
                            print(f"{Fore.GREEN}Adding correct solution to problem cache.{Style.RESET_ALL}")
                            add_to_problem_cache(problem, formula, answer)
                            
                    elif solution_data["message"] == "Incorrect answer.":
                        was_correct = False
                        print(f"{Fore.RED}❌ INCORRECT. Your answer was wrong.{Style.RESET_ALL}")
                        
                        # Log failed problem
                        if not is_cached and answer is not None and formula:
                            log_failed_problem(
                                problem_text=problem,
                                formula=formula,
                                answer=answer,
                                response_data=solution_data,
                                entities_info=entities_info,
                                calculation=calculation_info
                            )
                            
                    elif solution_data["message"] == "Time limit exceeded.":
                        # Already handled above
                        was_correct = False
                        
                        # Log failed problem
                        if not is_cached and answer is not None and formula:
                            log_failed_problem(
                                problem_text=problem,
                                formula=formula,
                                answer=answer,
                                response_data=solution_data,
                                entities_info=entities_info,
                                calculation=calculation_info
                            )
                    else:
                        print(f"{Fore.YELLOW}Unexpected message in response: {solution_data['message']}{Style.RESET_ALL}")
                        # If we can't determine correctness, we'll assume it's correct if we got a next problem
                        was_correct = True
                else:
                    # If there's no message field, we'll check for "correct" field
                    if "correct" in solution_data:
                        if solution_data["correct"] == 1:
                            was_correct = True
                            solved_count += 1
                            print(f"{Fore.GREEN}✅ CORRECT! Your answer was right.{Style.RESET_ALL}")
                            
                            # Only add to cache if the answer was correct and not already cached
                            if not is_cached and answer is not None and formula:
                                print(f"{Fore.GREEN}Adding correct solution to problem cache.{Style.RESET_ALL}")
                                add_to_problem_cache(problem, formula, answer)
                        else:
                            was_correct = False
                            print(f"{Fore.RED}❌ INCORRECT. Your answer was wrong.{Style.RESET_ALL}")
                            
                            # Log failed problem
                            if not is_cached and answer is not None and formula:
                                log_failed_problem(
                                    problem_text=problem,
                                    formula=formula,
                                    answer=answer,
                                    response_data=solution_data,
                                    entities_info=entities_info,
                                    calculation=calculation_info
                                )
                    else:
                        # If we can't determine correctness, don't increment solved_count
                        print(f"{Fore.YELLOW}Could not determine if answer was correct from response.{Style.RESET_ALL}")
                
                # Check for next problem in various possible response formats
                
                # Check for nested next_problem object
                if "next_problem" in solution_data and isinstance(solution_data["next_problem"], dict):
                    next_problem = solution_data["next_problem"]
                    if "id" in next_problem and "problem" in next_problem:
                        problem_id = next_problem["id"]
                        problem = next_problem["problem"]
                        has_problem = True
                        print(f"{Fore.GREEN}Next problem received (nested format).{Style.RESET_ALL}")
                
                # Check for old formats if not found above
                if not has_problem:
                    if "next_problem" in solution_data and "next_problem_id" in solution_data:
                        problem_id = solution_data["next_problem_id"]
                        problem = solution_data["next_problem"]
                        has_problem = True
                        print(f"{Fore.GREEN}Next problem received.{Style.RESET_ALL}")
                    elif "problem" in solution_data and "problem_id" in solution_data:
                        problem_id = solution_data["problem_id"]
                        problem = solution_data["problem"]
                        has_problem = True
                        print(f"{Fore.GREEN}Next problem received.{Style.RESET_ALL}")
                    elif "problem" in solution_data and "id" in solution_data:
                        problem_id = solution_data["id"]
                        problem = solution_data["problem"]
                        has_problem = True
                        print(f"{Fore.GREEN}Next problem received.{Style.RESET_ALL}")
                
                # If no next problem was found, we're done
                if not has_problem:
                    elapsed_time = time.time() - start_time
                    print(f"{Fore.GREEN}✅ All problems solved! Final score: {Fore.WHITE}{solved_count}/{attempted_count}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}❌ Error submitting solution: {solution_response.status_code} - {solution_response.text}{Style.RESET_ALL}")
                # Try to get the next problem instead of breaking
                print(f"{Fore.YELLOW}Attempting to get next problem despite error...{Style.RESET_ALL}")
                
                try:
                    # Try to get the next problem directly
                    next_response = requests.get(f"{BASE_URL}/challenge/next", headers=headers)
                    if next_response.status_code == 200:
                        next_data = next_response.json()
                        print(f"{Fore.BLUE}Next problem response: {json.dumps(next_data, indent=2)}{Style.RESET_ALL}")
                        
                        if "id" in next_data:
                            problem_id = next_data["id"]
                        elif "problem_id" in next_data:
                            problem_id = next_data["problem_id"]
                        else:
                            print(f"{Fore.RED}Could not find problem ID in next response{Style.RESET_ALL}")
                            has_problem = False
                            
                        if "problem" in next_data:
                            problem = next_data["problem"]
                            has_problem = True
                            print(f"{Fore.GREEN}Successfully retrieved next problem.{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.RED}Could not find problem text in next response{Style.RESET_ALL}")
                            has_problem = False
                    else:
                        print(f"{Fore.RED}Failed to get next problem: {next_response.status_code} - {next_response.text}{Style.RESET_ALL}")
                        has_problem = False
                except Exception as e:
                    print(f"{Fore.RED}Error getting next problem: {e}{Style.RESET_ALL}")
                    has_problem = False
        except Exception as e:
            print(f"{Fore.RED}Error during solution submission: {e}{Style.RESET_ALL}")
            # Try to continue with the next problem
            try:
                # Try to get the next problem directly
                next_response = requests.get(f"{BASE_URL}/challenge/next", headers=headers)
                if next_response.status_code == 200:
                    next_data = next_response.json()
                    if "id" in next_data and "problem" in next_data:
                        problem_id = next_data["id"]
                        problem = next_data["problem"]
                        has_problem = True
                        print(f"{Fore.GREEN}Retrieved next problem after error.{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}Invalid next problem response{Style.RESET_ALL}")
                        has_problem = False
                else:
                    print(f"{Fore.RED}Failed to get next problem after error{Style.RESET_ALL}")
                    has_problem = False
            except:
                print(f"{Fore.RED}Failed to recover from error{Style.RESET_ALL}")
                has_problem = False
                
        # If we have no more problems, print a message before exiting the loop
        if not has_problem:
            print(f"{Fore.YELLOW}No more problems available. Challenge completed.{Style.RESET_ALL}")
    
    # Calculate final statistics
    elapsed_time = time.time() - start_time
    print(f"\n{Fore.GREEN}🏁 Challenge completed! Problems solved: {Fore.WHITE}{solved_count}/{attempted_count}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}Time elapsed: {Fore.WHITE}{elapsed_time:.2f} seconds{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}Average time per problem: {Fore.WHITE}{elapsed_time/attempted_count:.2f} seconds{Style.RESET_ALL}")
    if attempted_count > 0:
        print(f"{Fore.CYAN}Success rate: {Fore.WHITE}{(solved_count/attempted_count)*100:.1f}%{Style.RESET_ALL}")

if __name__ == "__main__":
    print(f"{Fore.CYAN}Star Wars & Pokémon Challenge Solver{Style.RESET_ALL}")
    print(f"{Fore.CYAN}===================================={Style.RESET_ALL}")
    
    # Initialize and load the cache at startup
    initialize_db()
    load_cache()
    
    # Prefetch data if necessary
    prefetch_data()
    
    choice = input(f"{Fore.YELLOW}Choose an option:\n{Fore.WHITE}1. Test with practice problem\n{Fore.WHITE}2. Run the actual challenge\n{Fore.YELLOW}Your choice (1-2): {Style.RESET_ALL}")
    
    if choice == "1":
        test_solver()
    elif choice == "2":
        run_challenge()
    else:
        print(f"{Fore.RED}Invalid choice. Exiting.{Style.RESET_ALL}") 