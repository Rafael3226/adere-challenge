"""API client for making requests to the challenge endpoints."""

import requests
import json
import urllib3
from colorama import Fore, Style

from adere_challenge.api.endpoints import BASE_URL, SWAPI_URL, POKEAPI_URL
from adere_challenge.utils.logger import log, debug
from adere_challenge.solvers.ai_parser import extract_formula_with_ai

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
        debug(f"{Fore.BLUE}GET {url}: {response.status_code}{Style.RESET_ALL}")
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
        debug(f"{Fore.BLUE}POST {url}: {response.status_code}{Style.RESET_ALL}")
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
        debug(f"{Fore.BLUE}GET {url}: {response.status_code}{Style.RESET_ALL}")
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
        debug(f"{Fore.BLUE}GET {url}: {response.status_code}{Style.RESET_ALL}")
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
        debug(f"{Fore.BLUE}GET {url}: {response.status_code}{Style.RESET_ALL}")
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
            debug(f"{Fore.RED}Cannot parse None problem with AI.{Style.RESET_ALL}")
            return "0"  # Return a default formula that will evaluate to 0
        
        # Use our new AI parser function
        formula = extract_formula_with_ai(problem, self.token)
        
        # If we got a formula back, return it
        if formula:
            return formula
        
        # Otherwise, return a default formula
        debug(f"{Fore.RED}AI parsing failed. Using default formula.{Style.RESET_ALL}")
        return "0"  # Return a default formula that will evaluate to 0 