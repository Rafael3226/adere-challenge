import requests
import time
import json
import re
import os
import sqlite3
from dotenv import load_dotenv
import urllib3
from colorama import Fore, Back, Style, init

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

# In-memory cache for faster access during runtime
cache = {
    "pokemon": {},
    "swapi_characters": {},
    "swapi_planets": {}
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
    
    conn.commit()
    conn.close()
    print(f"{Fore.BLUE}Database initialized at {Fore.CYAN}{DB_FILE}{Style.RESET_ALL}")

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
        
        conn.close()
        
        print(f"{Fore.GREEN}Cache loaded with {Fore.WHITE}{len(cache['pokemon'])} Pokémon, "
              f"{Fore.WHITE}{len(cache['swapi_characters'])} Star Wars characters, and "
              f"{Fore.WHITE}{len(cache['swapi_planets'])} Star Wars planets.{Style.RESET_ALL}")
              
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
    
    # Check all caches first
    for entity_type in ["pokemon", "swapi_characters", "swapi_planets"]:
        if normalized_name in cache[entity_type]:
            return cache[entity_type][normalized_name], entity_type
    
    print(f"{Fore.YELLOW}Entity '{Fore.WHITE}{entity_name}{Fore.YELLOW}' not found in cache. Searching APIs...{Style.RESET_ALL}")
    
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
            "height": data["height"],
            "weight": data["weight"]
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
- For entity names with multiple words (like "Luke Skywalker"), use quotes: "luke skywalker".mass
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
        print(f"Error with AI: {response.status_code} - {response.text}")
        return None

def normalize_entity_name(name):
    """Normalize entity names by removing dots and standardizing format"""
    # Remove quotes if present
    name = name.strip('"\'')
    # Replace dots with spaces (for cases like "ratts.tyerel")
    name = name.replace('.', ' ')
    # Normalize whitespace
    name = ' '.join(name.split())
    return name.lower()

def evaluate_expression(formula):
    """Evaluate the mathematical expression based on the formula provided by AI"""
    print(f"{Fore.BLUE}Original formula: {Fore.CYAN}{formula}{Style.RESET_ALL}")
    
    # We'll collect all variables mentioned in the formula
    variables = {}
    
    # Extract entity names and attributes from the formula - handle both quoted and unquoted names
    # This complex pattern handles several cases:
    # 1. "entity name".attribute - quoted multi-word entities
    # 2. entity.attribute - simple unquoted entities
    # 3. entity.name.attribute - incorrectly parsed multi-word entities with dots
    entity_pattern = re.compile(r'("([^"]+)"|([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*))\.([a-zA-Z_][a-zA-Z0-9_]*)')
    
    # Map of common entity name variations
    name_variations = {
        "beru": "beru whitesun lars",
        "beruwhitesunlars": "beru whitesun lars",
        "luke": "luke skywalker",
        "lukeskywalker": "luke skywalker",
        "ratts tyerel": "ratts tyerell",  # Note the spelling correction
        "rattstyerel": "ratts tyerell"
    }
    
    # First, find all entities in the formula
    entities_to_process = []
    for match in entity_pattern.finditer(formula):
        full_match, quoted_name, dotted_name, attribute = match.groups()
        
        # Get the actual entity name (either from quotes or from dotted notation)
        if quoted_name:
            entity_name = quoted_name
        else:
            entity_name = dotted_name
        
        # Normalize the entity name
        normalized_name = normalize_entity_name(entity_name)
        
        # Check for name variations
        if normalized_name in name_variations:
            normalized_name = name_variations[normalized_name]
            
        # Store for processing
        entities_to_process.append((match.group(0), normalized_name, attribute))
    
    # Now fetch data for all entities
    for original_text, entity_name, attribute in entities_to_process:
        # If we haven't fetched this entity yet
        if entity_name not in variables:
            # Use the centralized entity resolution function
            entity_data, _ = get_entity_data(entity_name)
            if entity_data:
                variables[entity_name] = entity_data
            else:
                print(f"{Fore.YELLOW}Warning: Could not find data for entity '{Fore.WHITE}{entity_name}{Fore.YELLOW}'{Style.RESET_ALL}")
    
    # Replace all entity references with actual values
    eval_formula = formula
    for original_text, entity_name, attribute in entities_to_process:
        if entity_name in variables and attribute in variables[entity_name]:
            value = variables[entity_name][attribute]
            # Replace the complete original text with the value
            eval_formula = eval_formula.replace(original_text, str(value))
        else:
            if entity_name in variables:
                print(f"{Fore.YELLOW}Warning: Attribute '{Fore.WHITE}{attribute}{Fore.YELLOW}' not found for entity '{Fore.WHITE}{entity_name}{Fore.YELLOW}'{Style.RESET_ALL}")
                print(f"{Fore.BLUE}Available attributes: {Fore.WHITE}{list(variables[entity_name].keys())}{Fore.BLUE}{Style.RESET_ALL}")
            # Default to 0 if we can't find the attribute
            eval_formula = eval_formula.replace(original_text, "0")
    
    # Evaluate the formula
    try:
        print(f"{Fore.BLUE}Evaluating formula: {Fore.CYAN}{eval_formula}{Style.RESET_ALL}")
        result = eval(eval_formula)
        # Round to 10 decimal places as specified in the challenge
        result = round(float(result), 10)
        print(f"{Fore.MAGENTA}Result: {Fore.WHITE}{result}{Style.RESET_ALL}")
        return result
    except Exception as e:
        print(f"{Fore.RED}Error evaluating formula: {e}{Style.RESET_ALL}")
        print(f"{Fore.RED}Formula: {eval_formula}{Style.RESET_ALL}")
        return None

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
        
        # Parse problem with AI
        formula = parse_problem_with_ai(problem)
        print(f"{Fore.BLUE}AI Formula: {Fore.CYAN}{formula}{Style.RESET_ALL}")
        
        # Evaluate the formula
        answer = evaluate_expression(formula)
        print(f"{Fore.MAGENTA}Calculated answer: {Fore.WHITE}{answer}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}Expected answer: {Fore.WHITE}{expected_answer}{Style.RESET_ALL}")
        
        if answer == expected_answer:
            print(f"{Fore.GREEN}✅ Test passed! Your solution is working correctly.{Style.RESET_ALL}")
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
    problem_id = start_data["problem_id"]
    problem = start_data["problem"]
    
    solved_count = 0
    start_time = time.time()
    end_time = start_time + 180  # 3 minutes
    
    while time.time() < end_time:
        print(f"\n{Fore.CYAN}Problem #{solved_count + 1}: {Fore.WHITE}{problem}{Style.RESET_ALL}")
        
        # Parse problem with AI
        formula = parse_problem_with_ai(problem)
        print(f"{Fore.BLUE}AI Formula: {Fore.CYAN}{formula}{Style.RESET_ALL}")
        
        # Evaluate the formula
        answer = evaluate_expression(formula)
        print(f"{Fore.MAGENTA}Answer: {Fore.WHITE}{answer}{Style.RESET_ALL}")
        
        # Submit the solution
        solution_data = {
            "problem_id": problem_id,
            "answer": answer
        }
        
        solution_response = requests.post(
            f"{BASE_URL}/challenge/solution", 
            headers=headers,
            json=solution_data
        )
        
        if solution_response.status_code == 200:
            solution_data = solution_response.json()
            solved_count += 1
            
            # Debug the response
            print(f"{Fore.BLUE}API Response: {json.dumps(solution_data, indent=2)}{Style.RESET_ALL}")
            
            # Check for next problem in various possible response formats
            if "next_problem" in solution_data and "next_problem_id" in solution_data:
                problem_id = solution_data["next_problem_id"]
                problem = solution_data["next_problem"]
                print(f"{Fore.GREEN}✅ Correct! Next problem received.{Style.RESET_ALL}")
            elif "problem" in solution_data and "problem_id" in solution_data:
                problem_id = solution_data["problem_id"]
                problem = solution_data["problem"]
                print(f"{Fore.GREEN}✅ Correct! Next problem received.{Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}✅ All problems solved! Final score: {Fore.WHITE}{solved_count}{Style.RESET_ALL}")
                break
        else:
            print(f"{Fore.RED}❌ Error submitting solution: {solution_response.status_code} - {solution_response.text}{Style.RESET_ALL}")
            break
        
        # Check if we're out of time
        if time.time() >= end_time:
            print(f"{Fore.YELLOW}⏱️ Time's up! Problems solved: {Fore.WHITE}{solved_count}{Style.RESET_ALL}")
            break
    
    print(f"\n{Fore.GREEN}🏁 Challenge completed! Problems solved: {Fore.WHITE}{solved_count}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}Time elapsed: {Fore.WHITE}{time.time() - start_time:.2f} seconds{Style.RESET_ALL}")

if __name__ == "__main__":
    print(f"{Fore.CYAN}Star Wars & Pokémon Challenge Solver{Style.RESET_ALL}")
    print(f"{Fore.CYAN}===================================={Style.RESET_ALL}")
    
    # Initialize and load the cache at startup
    initialize_db()
    load_cache()
    
    # Prefetch data if necessary
    prefetch_data()
    
    choice = input(f"{Fore.YELLOW}Choose an option:\n{Fore.WHITE}1. Test with practice problem\n{Fore.WHITE}2. Run the actual challenge\n{Fore.YELLOW}Your choice (1 or 2): {Style.RESET_ALL}")
    
    if choice == "1":
        test_solver()
    elif choice == "2":
        run_challenge()
    else:
        print(f"{Fore.RED}Invalid choice. Exiting.{Style.RESET_ALL}") 