"""AI-based formula extraction from problem statements."""

import json
import requests
from colorama import Fore, Style

from adere_challenge.utils.logger import log

# OpenAI proxy endpoint
OPENAI_ENDPOINT = "https://recruiting.adere.so/chat_completion"

def extract_formula_with_ai(problem_statement, auth_token=None):
    """
    Extract a mathematical formula from a problem statement using AI.
    
    Args:
        problem_statement: The problem statement to parse
        auth_token: Authentication token for the API
        
    Returns:
        str: The extracted formula
    """
    log(f"{Fore.BLUE}Extracting formula from problem: {Fore.CYAN}{problem_statement[:100]}...{Style.RESET_ALL}")
    
    # Create the detailed prompt for the AI
    system_message = """I need you to extract a mathematical formula from problems about Star Wars characters, planets, and Pokémon.

Each problem will describe a scenario requiring mathematical operations on entity attributes.

Entity types and their attributes:
1. Star Wars Characters: name, height, homeworld
2. Star Wars Planets: name, rotation_period, orbital_period, diameter, surface_water, population, mass
3. Pokémon: name, base_experience, height, weight

TASK:
1. Identify all entities mentioned in the problem
2. Determine which attributes are involved for each entity
3. Extract the mathematical operations to be performed
4. Express this as a clear formula

IMPORTANT: 
- Estructure for each vaule is: "entity".attribute
- usually when the  problem talk about mass is talking about the planet mass
- Return ONLY the formula/expression, nothing else
- For entity names with multiple words (like "Luke Skywalker" or "Tapu Koko"), use quotes: "luke skywalker".[attributes] or "tapu koko".[attributes]
- Handle compound names like Tapu-Koko, Type-Null as single units (e.g., "tapu-koko".[attributes])
- Exclude titles (like General, Captain, Princess) from character names (e.g., use "grievous" not "general grievous")
- Use lowercase for all entity names
- For special Pokémon names with hyphens such as "Kommo-o", "Hakamo-o", "Ho-oh", etc., keep the hyphen in the name
- Always use double quotes for entity names, never single quotes
- Use proper operator precedence with parentheses when needed
- The formula should only contain entity.attribute references, numbers, and mathematical operators (+, -, *, /, **, etc.)
- Be precise - the formula should capture the exact mathematical relationship described in the problem"""
    
    # Prepare request payload
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "developer", "content": system_message},
            {"role": "user", "content": problem_statement}
        ]
    }
    
    # Set up headers
    headers = {
        "Content-Type": "application/json"
    }
    
    # Add authorization if token is provided
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
    try:
        # Make the API call
        response = requests.post(
            OPENAI_ENDPOINT,
            headers=headers,
            data=json.dumps(payload)
        )
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse the response
        response_data = response.json()
        
        # Extract the formula from the response
        if "choices" in response_data and len(response_data["choices"]) > 0:
            formula = response_data["choices"][0]["message"]["content"].strip()
            
            # Clean up the formula - remove any markdown formatting or quotes
            formula = formula.strip('`')
            if formula.startswith('```') and formula.endswith('```'):
                formula = formula[3:-3].strip()
                
            log(f"{Fore.GREEN}Successfully extracted formula: {Fore.WHITE}{formula}{Style.RESET_ALL}")
            return formula
        else:
            log(f"{Fore.RED}No formula found in AI response: {response_data}{Style.RESET_ALL}")
            return None
            
    except requests.exceptions.RequestException as e:
        log(f"{Fore.RED}Error calling OpenAI API: {str(e)}{Style.RESET_ALL}")
        return None
    except json.JSONDecodeError as e:
        log(f"{Fore.RED}Error decoding API response: {str(e)}{Style.RESET_ALL}")
        return None
    except Exception as e:
        log(f"{Fore.RED}Unexpected error: {str(e)}{Style.RESET_ALL}")
        return None 