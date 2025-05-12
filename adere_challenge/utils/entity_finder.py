"""Utility for finding entities from failed problems in APIs."""

import os
import re
import json
from colorama import Fore, Style

from adere_challenge.utils.logger import log, debug
from adere_challenge.data.cache import cache, add_to_cache

def review_failed_problems(api_client):
    """Review failed problems and identify entities with default value 0.
    
    Args:
        api_client: API client instance
    """
    failed_dir = 'failed_problems'
    not_found_file = 'entities_not_found.json'
    
    # Load existing not found entities if file exists
    not_found_entities = {}
    if os.path.exists(not_found_file):
        try:
            with open(not_found_file, 'r', encoding='utf-8') as f:
                not_found_entities = json.load(f)
        except (json.JSONDecodeError, IOError):
            log(f"{Fore.YELLOW}Error loading not found entities file. Creating a new one.{Style.RESET_ALL}")
            not_found_entities = {}
    
    if not os.path.exists(failed_dir):
        log(f"{Fore.RED}Directory '{failed_dir}' not found.{Style.RESET_ALL}")
        return
    
    log(f"{Fore.CYAN}Reviewing failed problems directory...{Style.RESET_ALL}")
    
    # Entities with value 0
    zero_entities = []
    
    # Process each failed problem file
    for filename in os.listdir(failed_dir):
        if not filename.endswith('.txt'):
            continue
        
        filepath = os.path.join(failed_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
            
            # Extract entities used
            entities_used_match = re.search(r'ENTITIES USED:(.*?)(?=\n\n|\nCALCULATION:)', content, re.DOTALL)
            
            if not entities_used_match:
                continue
                
            entities_used_text = entities_used_match.group(1).strip()
            
            # Parse entities that had value 0
            for line in entities_used_text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                # Match patterns like "entity.attribute = value"
                entity_match = re.match(r'([^.]+)\.([^ ]+)\s*=\s*(.+)', line)
                if entity_match:
                    entity, attribute, value = entity_match.groups()
                    entity = entity.strip()
                    value = value.strip()
                    
                    # Check if value is 0
                    if value == '0':
                        # Extract problem hash
                        hash_match = re.search(r'HASH:\s*([a-f0-9]+)', content)
                        problem_hash = hash_match.group(1) if hash_match else "unknown"
                        
                        # Add to list of zero entities
                        zero_entities.append({
                            'entity': entity,
                            'attribute': attribute,
                            'problem_hash': problem_hash
                        })
    
    if not zero_entities:
        log(f"{Fore.YELLOW}No entities with value 0 found in failed problems.{Style.RESET_ALL}")
        return
    
    # Display entities with value 0
    log(f"{Fore.GREEN}Found {len(zero_entities)} entities with value 0 in failed problems:{Style.RESET_ALL}")
    
    # Group entities by name for cleaner output
    entity_groups = {}
    for entity_info in zero_entities:
        entity_name = entity_info['entity']
        if entity_name not in entity_groups:
            entity_groups[entity_name] = []
        entity_groups[entity_name].append(entity_info)
    
    # List of newly not found entities
    newly_not_found = []
    # List of entities found and added to cache
    found_entities = []
    # List of entities that were tried but not found
    not_found_entities_list = []
    
    # Display grouped entities and try to find them in APIs
    for entity_name, entities in entity_groups.items():
        log(f"\n{Fore.CYAN}Entity: {entity_name}{Style.RESET_ALL}")
        
        # Check attributes with value 0
        attributes = [e['attribute'] for e in entities]
        attribute_str = ', '.join(attributes)
        log(f"  Attributes with value 0: {attribute_str}")
        
        # Problem hashes where this entity appears
        problem_hashes = [e['problem_hash'] for e in entities]
        unique_hashes = list(set(problem_hashes))
        log(f"  Found in {len(unique_hashes)} problems")
        
        # Check if entity is in our not found list with possible variations
        entity_found = False
        found_variation = None
        entity_type = None
        entity_data = None
        
        if entity_name in not_found_entities and not_found_entities[entity_name].get('tried_variations', []):
            log(f"  {Fore.YELLOW}Entity previously not found, trying stored variations...{Style.RESET_ALL}")
            variations = not_found_entities[entity_name].get('variations', [])
            if variations:
                for variation in variations:
                    log(f"  Trying variation: {variation}")
                    entity_type, entity_data = try_find_entity(api_client, variation, attributes)
                    if entity_type:
                        log(f"  {Fore.GREEN}Found with variation: {variation}{Style.RESET_ALL}")
                        # Add to cache
                        update_entity_cache(entity_type, entity_data, variation)
                        entity_found = True
                        found_variation = variation
                        break
        
        # If not found with variations, try the original
        if not entity_found:
            log(f"  Searching for entity in APIs...")
            entity_type, entity_data = try_find_entity(api_client, entity_name, attributes)
            if entity_type:
                # Add to cache (may already be in cache, but marked as found)
                update_entity_cache(entity_type, entity_data, entity_name)
                entity_found = True
                found_variation = entity_name
        
        # If still not found, generate variations and try them
        if not entity_found:
            variations = generate_name_variations(entity_name)
            
            # Store the entity in not found list if not already there
            if entity_name not in not_found_entities:
                not_found_entities[entity_name] = {
                    'attributes': attributes,
                    'tried_variations': True,
                    'variations': []
                }
            
            # Try each variation
            for variation in variations:
                log(f"  Trying variation: {variation}")
                entity_type, entity_data = try_find_entity(api_client, variation, attributes)
                if entity_type:
                    # Store successful variation
                    if variation not in not_found_entities[entity_name]['variations']:
                        not_found_entities[entity_name]['variations'].append(variation)
                    log(f"  {Fore.GREEN}Found with variation: {variation}{Style.RESET_ALL}")
                    # Add to cache
                    update_entity_cache(entity_type, entity_data, variation)
                    entity_found = True
                    found_variation = variation
                    break
        
        # If found, add to found list to remove from not_found_entities later
        if entity_found and entity_type and entity_data:
            found_entities.append({
                'original_name': entity_name,
                'found_as': found_variation,
                'type': entity_type
            })
            log(f"  {Fore.GREEN}Will remove '{entity_name}' from not found entities list{Style.RESET_ALL}")
        # If still not found after all attempts
        else:
            log(f"  {Fore.RED}Entity not found in any API{Style.RESET_ALL}")
            newly_not_found.append(entity_name)
            not_found_entities_list.append({
                'original_name': entity_name
            })
            
            # Ensure it's in our not found list
            if entity_name not in not_found_entities:
                not_found_entities[entity_name] = {
                    'attributes': attributes,
                    'tried_variations': True,
                    'variations': []
                }
    
    # Remove found entities from not_found_entities
    for entity in found_entities:
        original_name = entity['original_name']
        if original_name in not_found_entities:
            del not_found_entities[original_name]
            log(f"{Fore.GREEN}Removed {original_name} from not found entities list{Style.RESET_ALL}")
    
    # Save the updated not found entities list
    try:
        with open(not_found_file, 'w', encoding='utf-8') as f:
            json.dump(not_found_entities, f, indent=2)
        log(f"\n{Fore.GREEN}Updated not found entities file: {not_found_file}{Style.RESET_ALL}")
    except IOError:
        log(f"\n{Fore.RED}Error saving not found entities file{Style.RESET_ALL}")
    
    # Report on entities not found
    if newly_not_found:
        log(f"\n{Fore.YELLOW}Entities not found after all attempts: {', '.join(newly_not_found)}{Style.RESET_ALL}")
    else:
        log(f"\n{Fore.GREEN}All entities found in APIs{Style.RESET_ALL}")
    
    # Report on entities found and added to cache
    if found_entities:
        log(f"\n{Fore.GREEN}Found and added to cache: {len(found_entities)} entities{Style.RESET_ALL}")
        for entity in found_entities:
            log(f"  - {entity['original_name']} (as {entity['found_as']})")
    
    # Report on entities not found
    if not_found_entities_list:
        log(f"\n{Fore.RED}Not found in any API: {len(not_found_entities_list)} entities{Style.RESET_ALL}")
        for entity in not_found_entities_list:
            log(f"  - {entity['original_name']}")


def try_find_entity(api_client, entity_name, attributes):
    """Try to find an entity in the APIs.
    
    Args:
        api_client: API client instance
        entity_name: Name of the entity to find
        attributes: List of attributes to look for
        
    Returns:
        tuple: (entity_type, entity_data) if found, (None, None) otherwise
    """
    # First check if entity is already in our cache
    entity_lower = entity_name.lower()
    
    # Check Pokemon cache
    if entity_lower in cache['pokemon']:
        pokemon_data = cache['pokemon'][entity_lower]
        log(f"  {Fore.GREEN}Found in Pokemon cache: {pokemon_data['name']}{Style.RESET_ALL}")
        
        for attribute in attributes:
            # Display the attribute from cache
            if attribute == 'height':
                log(f"    {attribute}: {pokemon_data.get('height', 'N/A')}")
            elif attribute == 'base_experience':
                log(f"    {attribute}: {pokemon_data.get('base_experience', 'N/A')}")
            elif attribute == 'weight':
                log(f"    {attribute}: {pokemon_data.get('weight', 'N/A')}")
            else:
                log(f"    {attribute}: Value not found in Pokemon data")
        
        return ('pokemon', pokemon_data)
    
    # Check Star Wars character cache
    for char_name, char_data in cache['swapi_characters'].items():
        if entity_lower in char_name or char_name in entity_lower:
            log(f"  {Fore.GREEN}Found in Star Wars character cache: {char_data['name']}{Style.RESET_ALL}")
            
            for attribute in attributes:
                # Display the attribute from cache
                if attribute in ['mass', 'height']:
                    log(f"    {attribute}: {char_data.get(attribute, 'N/A')}")
                else:
                    log(f"    {attribute}: Value not found in character data")
            
            return ('swapi_character', char_data)
    
    # Check Star Wars planet cache
    for planet_name, planet_data in cache['swapi_planets'].items():
        if entity_lower in planet_name or planet_name in entity_lower:
            log(f"  {Fore.GREEN}Found in Star Wars planet cache: {planet_data['name']}{Style.RESET_ALL}")
            
            for attribute in attributes:
                # Display the attribute from cache
                if attribute == 'diameter':
                    log(f"    {attribute}: {planet_data.get('diameter', 'N/A')}")
                elif attribute == 'rotation_period':
                    log(f"    {attribute}: {planet_data.get('rotation_period', 'N/A')}")
                else:
                    log(f"    {attribute}: Value not found in planet data")
            
            return ('swapi_planet', planet_data)
    
    # If not in cache, try Pokemon API
    pokemon_response = api_client.get_pokemon(entity_name.lower())
    if pokemon_response.status_code == 200:
        pokemon_data = pokemon_response.json()
        log(f"  {Fore.GREEN}Found in Pokemon API: {pokemon_data['name']}{Style.RESET_ALL}")
        
        for attribute in attributes:
            # Try to find the attribute in the Pokemon data
            if attribute == 'height':
                log(f"    {attribute}: {pokemon_data.get('height', 'N/A')}")
            elif attribute == 'base_experience':
                log(f"    {attribute}: {pokemon_data.get('base_experience', 'N/A')}")
            elif attribute == 'weight':
                log(f"    {attribute}: {pokemon_data.get('weight', 'N/A')}")
            else:
                log(f"    {attribute}: Value not found in Pokemon API")
        
        return ('pokemon', pokemon_data)
    
    # Try Star Wars Character API
    swapi_char_response = api_client.get_swapi_character(entity_name.lower())
    if swapi_char_response.status_code == 200:
        swapi_data = swapi_char_response.json()
        if swapi_data['results']:
            character_data = swapi_data['results'][0]
            log(f"  {Fore.GREEN}Found in Star Wars API (character): {character_data['name']}{Style.RESET_ALL}")
            
            for attribute in attributes:
                # Try to find the attribute in the character data
                if attribute in ['mass', 'height']:
                    log(f"    {attribute}: {character_data.get(attribute, 'N/A')}")
                else:
                    log(f"    {attribute}: Value not found in Star Wars API")
            
            return ('swapi_character', character_data)
    
    # Try Star Wars Planet API
    swapi_planet_response = api_client.get_swapi_planet(entity_name.lower())
    if swapi_planet_response.status_code == 200:
        swapi_data = swapi_planet_response.json()
        if swapi_data['results']:
            planet_data = swapi_data['results'][0]
            log(f"  {Fore.GREEN}Found in Star Wars API (planet): {planet_data['name']}{Style.RESET_ALL}")
            
            for attribute in attributes:
                # Try to find the attribute in the planet data
                if attribute == 'diameter':
                    log(f"    {attribute}: {planet_data.get('diameter', 'N/A')}")
                elif attribute == 'rotation_period':
                    log(f"    {attribute}: {planet_data.get('rotation_period', 'N/A')}")
                else:
                    log(f"    {attribute}: Value not found in Star Wars API")
            
            return ('swapi_planet', planet_data)
    
    # Entity not found in any API or cache
    return (None, None)


def update_entity_cache(entity_type, entity_data, entity_name):
    """Add an entity to the cache.
    
    Args:
        entity_type: Type of entity ('pokemon', 'swapi_character', or 'swapi_planet')
        entity_data: Entity data from API
        entity_name: Name used to find the entity
        
    Returns:
        bool: True always (entity is considered found even if already in cache)
    """
    if entity_type == 'pokemon':
        cache_key = entity_name.lower()
        if cache_key not in cache['pokemon']:
            cache['pokemon'][cache_key] = entity_data
            log(f"  {Fore.GREEN}Added to Pokemon cache: {cache_key}{Style.RESET_ALL}")
            add_to_cache('pokemon', cache_key, entity_data)
        else:
            log(f"  {Fore.YELLOW}Already in Pokemon cache: {cache_key}{Style.RESET_ALL}")
    
    elif entity_type == 'swapi_character':
        character_name = entity_data['name'].lower()
        if character_name not in cache['swapi_characters']:
            cache['swapi_characters'][character_name] = entity_data
            log(f"  {Fore.GREEN}Added to Star Wars character cache: {character_name}{Style.RESET_ALL}")
            add_to_cache('swapi_characters', character_name, entity_data)
        else:
            log(f"  {Fore.YELLOW}Already in Star Wars character cache: {character_name}{Style.RESET_ALL}")
    
    elif entity_type == 'swapi_planet':
        planet_name = entity_data['name'].lower()
        if planet_name not in cache['swapi_planets']:
            cache['swapi_planets'][planet_name] = entity_data
            log(f"  {Fore.GREEN}Added to Star Wars planet cache: {planet_name}{Style.RESET_ALL}")
            add_to_cache('swapi_planets', planet_name, entity_data)
        else:
            log(f"  {Fore.YELLOW}Already in Star Wars planet cache: {planet_name}{Style.RESET_ALL}")
    
    # Always return True, as the entity is considered found even if already in cache
    return True


def generate_name_variations(name):
    """Generate variations of an entity name to try.
    
    Args:
        name: Original entity name
        
    Returns:
        list: List of name variations to try
    """
    variations = []
    
    # Common variations
    if " " in name:
        # Try without spaces
        variations.append(name.replace(" ", ""))
        
        # Try with dashes instead of spaces
        variations.append(name.replace(" ", "-"))
        
        # Try reversing first and last name
        parts = name.split()
        if len(parts) == 2:
            variations.append(f"{parts[1]} {parts[0]}")
    
    # Try capitalizing each word
    variations.append(name.title())
    
    # Try all lowercase
    variations.append(name.lower())
    
    # Try removing trailing numbers or special chars
    clean_name = re.sub(r'[^a-zA-Z\s]', '', name).strip()
    if clean_name != name:
        variations.append(clean_name)
    
    # Common character-specific variations for Star Wars
    if "darth" in name.lower():
        variations.append(name.lower().replace("darth", "darth "))
        variations.append(name.lower().replace("darht", "darth"))
    
    if "c3po" in name.lower() or "r2d2" in name.lower():
        variations.append(name.lower().replace("c3po", "c-3po"))
        variations.append(name.lower().replace("r2d2", "r2-d2"))
    
    # Remove duplicates and the original name
    return list(set([v for v in variations if v.lower() != name.lower()])) 