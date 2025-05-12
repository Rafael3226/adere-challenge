"""Pokemon data fetching and processing."""

from colorama import Fore, Style

from adere_challenge.utils.logger import log
from adere_challenge.data.cache import add_to_cache, cache

def get_pokemon_data(api_client, name):
    """Fetch Pokémon data from cache or PokéAPI.
    
    Args:
        api_client: API client instance
        name: Pokemon name
        
    Returns:
        Pokemon data dictionary or None
    """
    # Normalize name for consistency
    normalized_name = name.lower()
    
    # Check in-memory cache first
    if normalized_name in cache["pokemon"]:
        return cache["pokemon"][normalized_name]
    
    # Try to fetch from API
    response = api_client.get_pokemon(normalized_name)
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

def prefetch_pokemon(api_client):
    """Prefetch common Pokemon data to improve performance.
    
    Args:
        api_client: API client instance
    """
    # Common Pokemon
    pokemon_list = ["pikachu", "charizard", "bulbasaur", "squirtle", "eevee", 
                   "mewtwo", "jigglypuff", "vulpix", "snorlax", "meowth",
                   "arcanine", "gyarados", "dragonite", "gengar", "machamp",
                   "alakazam", "lapras", "magikarp", "ditto", "venusaur", 
                   "blastoise", "mew", "vaporeon", "flareon", "jolteon", 
                   "mr-mime", "kommo-o", "hakamo-o", "jangmo-o", "porygon-z", 
                   "ho-oh", "tapu-koko", "tapu-lele", "tapu-bulu", "tapu-fini"]
    
    log(f"{Fore.CYAN}Prefetching Pokémon data...{Style.RESET_ALL}")
    for pokemon in pokemon_list:
        get_pokemon_data(api_client, pokemon) 