"""API client for making requests to the challenge endpoints."""

import requests
import json
import urllib3
from colorama import Fore, Style

from adere_challenge.api.endpoints import BASE_URL, SWAPI_URL, POKEAPI_URL
from adere_challenge.utils.logger import log

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class APIClient:
    """Client for making API requests."""
    
    def __init__(self, token):
        """Initialize the API client.
        
        Args:
            token: Authentication token
        """
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def get(self, endpoint, params=None, verify=False):
        """Make a GET request to the API.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            verify: Whether to verify SSL certificate
            
        Returns:
            Response object
        """
        url = f"{BASE_URL}{endpoint}"
        response = requests.get(url, headers=self.headers, params=params, verify=verify)
        log(f"{Fore.BLUE}GET {url}: {response.status_code}{Style.RESET_ALL}")
        return response
    
    def post(self, endpoint, data, verify=False):
        """Make a POST request to the API.
        
        Args:
            endpoint: API endpoint
            data: Request data
            verify: Whether to verify SSL certificate
            
        Returns:
            Response object
        """
        url = f"{BASE_URL}{endpoint}"
        response = requests.post(url, headers=self.headers, json=data, verify=verify)
        log(f"{Fore.BLUE}POST {url}: {response.status_code}{Style.RESET_ALL}")
        return response
    
    def get_pokemon(self, name, verify=False):
        """Get Pokemon data from PokeAPI.
        
        Args:
            name: Pokemon name
            verify: Whether to verify SSL certificate
            
        Returns:
            Response object
        """
        url = f"{POKEAPI_URL}/pokemon/{name}"
        response = requests.get(url, verify=verify)
        log(f"{Fore.BLUE}GET {url}: {response.status_code}{Style.RESET_ALL}")
        return response
    
    def get_swapi_character(self, name, verify=False):
        """Get Star Wars character data from SWAPI.
        
        Args:
            name: Character name
            verify: Whether to verify SSL certificate
            
        Returns:
            Response object
        """
        url = f"{SWAPI_URL}/people/?search={name}"
        response = requests.get(url, verify=verify)
        log(f"{Fore.BLUE}GET {url}: {response.status_code}{Style.RESET_ALL}")
        return response
    
    def get_swapi_planet(self, name, verify=False):
        """Get Star Wars planet data from SWAPI.
        
        Args:
            name: Planet name
            verify: Whether to verify SSL certificate
            
        Returns:
            Response object
        """
        url = f"{SWAPI_URL}/planets/?search={name}"
        response = requests.get(url, verify=verify)
        log(f"{Fore.BLUE}GET {url}: {response.status_code}{Style.RESET_ALL}")
        return response
        
    def parse_with_ai(self, problem):
        """Use AI to parse a problem.
        
        Args:
            problem: Problem text
            
        Returns:
            Formula from AI
        """
        # Handle None problem
        if problem is None:
            log(f"{Fore.RED}Cannot parse None problem with AI.{Style.RESET_ALL}")
            return "0"  # Return a default formula that will evaluate to 0
            
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
- For special Pokémon names with hyphens such as "Kommo-o", "Hakamo-o", "Ho-oh", etc., keep the hyphen in the name
- Always use double quotes for entity names, never single quotes
- Use proper operator precedence with parentheses when needed
- The formula should only contain entity.attribute references, numbers, and mathematical operators (+, -, *, /, **, etc.)
- Pay attention to context - sometimes the problem might refer to "Hutt" which should be translated to "jabba"
- Be precise - the formula should capture the exact mathematical relationship described in the problem"""
                },
                {"role": "user", "content": problem}
            ]
        }
        
        try:
            response = self.post("/chat_completion", data)
            if response.status_code == 200:
                ai_response = response.json()
                formula = ai_response["choices"][0]["message"]["content"].strip()
                # Clean up the formula - remove any markdown formatting or quotes
                formula = formula.strip('`')
                if formula.startswith('```') and formula.endswith('```'):
                    formula = formula[3:-3].strip()
                return formula
            else:
                log(f"{Fore.RED}Error with AI: {response.status_code} - {response.text}{Style.RESET_ALL}")
                return "0"  # Return a default formula that will evaluate to 0
        except Exception as e:
            log(f"{Fore.RED}Exception during AI parsing: {str(e)}{Style.RESET_ALL}")
            return "0"  # Return a default formula that will evaluate to 0 