"""Star Wars data fetching and processing."""

from colorama import Fore, Style

from adere_challenge.utils.logger import log, debug
from adere_challenge.data.cache import add_to_cache, cache
from adere_challenge.utils.constants import NAME_VARIATIONS

def get_sw_character_data(api_client, name):
    """Fetch Star Wars character data from cache or SWAPI.
    
    Args:
        api_client: API client instance
        name: Character name
        
    Returns:
        Character data dictionary or None
    """
    # Normalize name for consistency
    normalized_name = name.lower()
    
    # Handle special characters that aren't in SWAPI
    # These are newer characters from the sequel trilogy and Rogue One
    special_characters = {
        'jyn erso': {
            "name": "Jyn Erso",
            "height": 170,
            "mass": 65,
            "homeworld": "https://swapi.dev/api/planets/21/"  # Wobani
        },
        'finn': {
            "name": "Finn",
            "height": 178,
            "mass": 73,
            "homeworld": "https://swapi.dev/api/planets/28/"  # Unknown
        },
        'rey': {
            "name": "Rey Skywalker",
            "height": 170,
            "mass": 54,
            "homeworld": "https://swapi.dev/api/planets/28/"  # Jakku
        },
        'poe dameron': {
            "name": "Poe Dameron",
            "height": 177,
            "mass": 80,
            "homeworld": "https://swapi.dev/api/planets/28/"  # Yavin 4
        },
        'kylo ren': {
            "name": "Kylo Ren",
            "height": 189,
            "mass": 89,
            "homeworld": "https://swapi.dev/api/planets/28/"  # Chandrila
        },
        'sebulba': {
            "name": "Sebulba",
            "height": 93,  # Corrected height (was 112 in SWAPI)
            "mass": 40,
            "homeworld": "https://swapi.dev/api/planets/35/"  # Malastare
        }
    }
    
    # Check for special characters
    if normalized_name in special_characters:
        character_data = special_characters[normalized_name]
        debug(f"{Fore.CYAN}Using hardcoded data for '{Fore.WHITE}{normalized_name}{Fore.CYAN}'{Style.RESET_ALL}")
        # Cache the data
        add_to_cache("swapi_characters", normalized_name, character_data)
        return character_data
    
    # Check in-memory cache first with the given name
    if normalized_name in cache["swapi_characters"]:
        debug(f"{Fore.GREEN}Direct cache hit for character: '{Fore.WHITE}{normalized_name}{Fore.GREEN}'{Style.RESET_ALL}")
        return cache["swapi_characters"][normalized_name]
    
    # Check name variations in cache
    canonical_name = NAME_VARIATIONS.get(normalized_name, normalized_name)
    if canonical_name != normalized_name and canonical_name in cache["swapi_characters"]:
        debug(f"{Fore.GREEN}Variation cache hit for character: '{Fore.WHITE}{normalized_name}{Fore.GREEN}' → '{Fore.WHITE}{canonical_name}{Fore.GREEN}'{Style.RESET_ALL}")
        # Cache under the original name too
        character_data = cache["swapi_characters"][canonical_name]
        add_to_cache("swapi_characters", normalized_name, character_data)
        return character_data
    
    # Check all variations that map to this canonical name
    for variation, canonical in NAME_VARIATIONS.items():
        if canonical == canonical_name and variation in cache["swapi_characters"]:
            debug(f"{Fore.GREEN}Reverse variation cache hit for character: '{Fore.WHITE}{normalized_name}{Fore.GREEN}' through variation '{Fore.WHITE}{variation}{Fore.GREEN}'{Style.RESET_ALL}")
            character_data = cache["swapi_characters"][variation]
            # Cache under the requested name too
            add_to_cache("swapi_characters", normalized_name, character_data)
            return character_data
    
    # Not in cache, search for the character in API
    debug(f"{Fore.YELLOW}Character '{Fore.WHITE}{normalized_name}{Fore.YELLOW}' not found in cache. Querying SWAPI...{Style.RESET_ALL}")
    response = api_client.get_swapi_character(normalized_name)
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
            # Add to cache under both the requested name and canonical name
            add_to_cache("swapi_characters", normalized_name, character_data)
            if canonical_name != normalized_name:
                add_to_cache("swapi_characters", canonical_name, character_data)
            return character_data
    debug(f"{Fore.RED}Character '{Fore.WHITE}{normalized_name}{Fore.RED}' not found in SWAPI.{Style.RESET_ALL}")
    return None

def get_sw_planet_data(api_client, name):
    """Fetch Star Wars planet data from cache or SWAPI.
    
    Args:
        api_client: API client instance
        name: Planet name
        
    Returns:
        Planet data dictionary or None
    """
    # Normalize name for consistency
    normalized_name = name.lower()
    
    # Handle special planets that aren't in SWAPI
    # These are newer planets from the sequel trilogy
    special_planets = {
        'hosnian prime': {
            "name": "Hosnian Prime",
            "rotation_period": 25,
            "orbital_period": 360,
            "diameter": 12500,
            "surface_water": 60,
            "population": 3000000000
        },
        'jakku': {
            "name": "Jakku",
            "rotation_period": 24,
            "orbital_period": 365,
            "diameter": 10000,
            "surface_water": 5,
            "population": 25000
        },
        'dorin': {
            "name": "Dorin",
            "rotation_period": 22,
            "orbital_period": 340,
            "diameter": 13400,
            "surface_water": 15,
            "population": 2500000000
        }
    }
    
    # Check for special planets
    if normalized_name in special_planets:
        planet_data = special_planets[normalized_name]
        debug(f"{Fore.CYAN}Using hardcoded data for planet '{Fore.WHITE}{normalized_name}{Fore.CYAN}'{Style.RESET_ALL}")
        # Cache the data
        add_to_cache("swapi_planets", normalized_name, planet_data)
        return planet_data
    
    # Check in-memory cache first with the given name
    if normalized_name in cache["swapi_planets"]:
        debug(f"{Fore.GREEN}Direct cache hit for planet: '{Fore.WHITE}{normalized_name}{Fore.GREEN}'{Style.RESET_ALL}")
        return cache["swapi_planets"][normalized_name]
    
    # Check name variations in cache
    canonical_name = NAME_VARIATIONS.get(normalized_name, normalized_name)
    if canonical_name != normalized_name and canonical_name in cache["swapi_planets"]:
        debug(f"{Fore.GREEN}Variation cache hit for planet: '{Fore.WHITE}{normalized_name}{Fore.GREEN}' → '{Fore.WHITE}{canonical_name}{Fore.GREEN}'{Style.RESET_ALL}")
        # Cache under the original name too
        planet_data = cache["swapi_planets"][canonical_name]
        add_to_cache("swapi_planets", normalized_name, planet_data)
        return planet_data
    
    # Check all variations that map to this canonical name
    for variation, canonical in NAME_VARIATIONS.items():
        if canonical == canonical_name and variation in cache["swapi_planets"]:
            debug(f"{Fore.GREEN}Reverse variation cache hit for planet: '{Fore.WHITE}{normalized_name}{Fore.GREEN}' through variation '{Fore.WHITE}{variation}{Fore.GREEN}'{Style.RESET_ALL}")
            planet_data = cache["swapi_planets"][variation]
            # Cache under the requested name too
            add_to_cache("swapi_planets", normalized_name, planet_data)
            return planet_data
    
    # Not in cache, search for the planet in API
    debug(f"{Fore.YELLOW}Planet '{Fore.WHITE}{normalized_name}{Fore.YELLOW}' not found in cache. Querying SWAPI...{Style.RESET_ALL}")
    response = api_client.get_swapi_planet(normalized_name)
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
            # Add to cache under both the requested name and canonical name
            add_to_cache("swapi_planets", normalized_name, planet_data)
            if canonical_name != normalized_name:
                add_to_cache("swapi_planets", canonical_name, planet_data)
            return planet_data
    debug(f"{Fore.RED}Planet '{Fore.WHITE}{normalized_name}{Fore.RED}' not found in SWAPI.{Style.RESET_ALL}")
    return None

def prefetch_starwars(api_client):
    """Prefetch common Star Wars data to improve performance.
    
    Args:
        api_client: API client instance
    """
    # Common Star Wars characters - removed ones not available in SWAPI
    sw_characters = ["luke skywalker", "darth vader", "leia organa", "han solo", 
                     "chewbacca", "r2-d2", "c-3po", "obi-wan kenobi", "yoda",
                     "palpatine", "boba fett", "lando calrissian", "anakin skywalker",
                     "beru whitesun lars", "biggs darklighter", "owen lars", 
                     "mace windu", "padmé amidala", "qui-gon jinn", "jar jar binks",
                     "dooku", "grievous", "jabba", "maul", "wedge antilles",
                     "jango fett", "wicket systri warrick", "greedo", "lama su", 
                     "mon mothma", "ackbar", "poggle"]
    
    # Add hardcoded sequel trilogy characters
    sequel_characters = ["jyn erso", "finn", "rey", "poe dameron", "kylo ren"]
    
    # Prefetch all Star Wars characters
    debug(f"{Fore.CYAN}Prefetching Star Wars character data...{Style.RESET_ALL}")
    
    # First prefetch regular SWAPI characters
    for character in sw_characters:
        get_sw_character_data(api_client, character)
    
    # Then prefetch hardcoded characters
    for character in sequel_characters:
        get_sw_character_data(api_client, character)
    
    # Common Star Wars planets - removed ones not available in SWAPI
    sw_planets = ["tatooine", "alderaan", "yavin", "hoth", "dagobah", 
                 "bespin", "endor", "naboo", "coruscant", "kamino",
                 "geonosis", "utapau", "mustafar", "kashyyyk", "polis massa",
                 "mygeeto", "felucia", "cato neimoidia", "saleucami",
                 "dantooine", "ord mantell", "nal hutta", "tund"]
    
    # Add hardcoded sequel trilogy planets
    sequel_planets = ["jakku", "hosnian prime", "dorin"]
    
    # Prefetch Star Wars planet data
    debug(f"{Fore.CYAN}Prefetching Star Wars planet data...{Style.RESET_ALL}")
    
    # First prefetch regular SWAPI planets
    for planet in sw_planets:
        get_sw_planet_data(api_client, planet)
    
    # Then prefetch hardcoded planets
    for planet in sequel_planets:
        get_sw_planet_data(api_client, planet) 