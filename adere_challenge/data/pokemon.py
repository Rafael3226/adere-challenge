"""Pokemon data fetching and processing."""

from colorama import Fore, Style

from adere_challenge.utils.logger import log, debug
from adere_challenge.data.cache import add_to_cache, cache
from adere_challenge.utils.constants import NAME_VARIATIONS

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
    
    # Check in-memory cache first with the given name
    if normalized_name in cache["pokemon"]:
        debug(f"{Fore.GREEN}Direct cache hit for Pokémon: '{Fore.WHITE}{normalized_name}{Fore.GREEN}'{Style.RESET_ALL}")
        return cache["pokemon"][normalized_name]
    
    # Check name variations in cache
    canonical_name = NAME_VARIATIONS.get(normalized_name, normalized_name)
    if canonical_name != normalized_name and canonical_name in cache["pokemon"]:
        debug(f"{Fore.GREEN}Variation cache hit for Pokémon: '{Fore.WHITE}{normalized_name}{Fore.GREEN}' → '{Fore.WHITE}{canonical_name}{Fore.GREEN}'{Style.RESET_ALL}")
        # Cache under the original name too
        pokemon_data = cache["pokemon"][canonical_name]
        add_to_cache("pokemon", normalized_name, pokemon_data)
        return pokemon_data
    
    # Check all variations that map to this canonical name
    for variation, canonical in NAME_VARIATIONS.items():
        if canonical == canonical_name and variation in cache["pokemon"]:
            debug(f"{Fore.GREEN}Reverse variation cache hit for Pokémon: '{Fore.WHITE}{normalized_name}{Fore.GREEN}' through variation '{Fore.WHITE}{variation}{Fore.GREEN}'{Style.RESET_ALL}")
            pokemon_data = cache["pokemon"][variation]
            # Cache under the requested name too
            add_to_cache("pokemon", normalized_name, pokemon_data)
            return pokemon_data
    
    # Not in cache, try to fetch from API
    debug(f"{Fore.YELLOW}Pokémon '{Fore.WHITE}{normalized_name}{Fore.YELLOW}' not found in cache. Querying PokéAPI...{Style.RESET_ALL}")
    response = api_client.get_pokemon(normalized_name)
    if response.status_code == 200:
        data = response.json()
        pokemon = {
            "name": data["name"],
            "base_experience": data["base_experience"],
            "height": data["height"],  # Height is in decimeters (1/10 meter)
            "weight": data["weight"]   # Weight is in hectograms (1/10 kg)
        }
        # Add to cache under both the requested name and canonical name
        add_to_cache("pokemon", normalized_name, pokemon)
        if canonical_name != normalized_name:
            add_to_cache("pokemon", canonical_name, pokemon)
        return pokemon
    debug(f"{Fore.RED}Pokémon '{Fore.WHITE}{normalized_name}{Fore.RED}' not found in PokéAPI.{Style.RESET_ALL}")
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
                   "ho-oh", "tapu-koko", "tapu-lele", "tapu-bulu", "tapu-fini",
                   "stufful"]
    
    debug(f"{Fore.CYAN}Prefetching Pokémon data...{Style.RESET_ALL}")
    for pokemon in pokemon_list:
        get_pokemon_data(api_client, pokemon) 