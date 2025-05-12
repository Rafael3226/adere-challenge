"""Star Wars data fetching and processing."""

from colorama import Fore, Style

from adere_challenge.utils.logger import log
from adere_challenge.data.cache import add_to_cache, cache

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
    
    # Check in-memory cache first
    if normalized_name in cache["swapi_characters"]:
        return cache["swapi_characters"][normalized_name]
    
    # Search for the character in API
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
            # Add to cache
            add_to_cache("swapi_characters", normalized_name, character_data)
            return character_data
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
    
    # Check in-memory cache first
    if normalized_name in cache["swapi_planets"]:
        return cache["swapi_planets"][normalized_name]
    
    # Search for the planet in API
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
            # Add to cache
            add_to_cache("swapi_planets", normalized_name, planet_data)
            return planet_data
    return None

def prefetch_starwars(api_client):
    """Prefetch common Star Wars data to improve performance.
    
    Args:
        api_client: API client instance
    """
    # Common Star Wars characters
    sw_characters = ["luke skywalker", "darth vader", "leia organa", "han solo", 
                     "chewbacca", "r2-d2", "c-3po", "obi-wan kenobi", "yoda",
                     "palpatine", "boba fett", "lando calrissian", "anakin skywalker",
                     "beru whitesun lars", "biggs darklighter", "owen lars", 
                     "jyn erso", "finn", "rey", "poe dameron", "kylo ren", 
                     "mace windu", "padmé amidala", "qui-gon jinn", "jar jar binks",
                     "dooku", "grievous", "jabba", "maul", "wedge antilles",
                     "jango fett", "wicket systri warrick", "greedo", "lama su", 
                     "mon mothma", "ackbar"]
    
    # Common Star Wars planets
    sw_planets = ["tatooine", "alderaan", "yavin", "hoth", "dagobah", 
                 "bespin", "endor", "naboo", "coruscant", "kamino",
                 "geonosis", "utapau", "mustafar", "kashyyyk", "polis massa",
                 "mygeeto", "felucia", "cato neimoidia", "saleucami", "jakku",
                 "dantooine", "ord mantell", "nal hutta", "tund", "hosnian prime"]
    
    # Prefetch Star Wars character data
    log(f"{Fore.CYAN}Prefetching Star Wars character data...{Style.RESET_ALL}")
    for character in sw_characters:
        get_sw_character_data(api_client, character)
    
    # Prefetch Star Wars planet data
    log(f"{Fore.CYAN}Prefetching Star Wars planet data...{Style.RESET_ALL}")
    for planet in sw_planets:
        get_sw_planet_data(api_client, planet) 