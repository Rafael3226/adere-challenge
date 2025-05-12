"""Command-line interface for Adere Challenge."""

import os
import argparse
from dotenv import load_dotenv
from colorama import Fore, Style, init

from adere_challenge.api.client import APIClient
from adere_challenge.data.cache import initialize_db, load_cache, cache
from adere_challenge.data.pokemon import prefetch_pokemon
from adere_challenge.data.starwars import prefetch_starwars
from adere_challenge.solvers.expression import evaluate_expression
from adere_challenge.challenge.runner import ChallengeRunner
from adere_challenge.utils.logger import log, set_debug_mode, debug

# Initialize colorama
init(autoreset=True)

def create_parser():
    """Create command-line argument parser.
    
    Returns:
        ArgumentParser: Argument parser instance
    """
    parser = argparse.ArgumentParser(description="Adere Challenge - Star Wars & Pokémon")
    parser.add_argument("--test", action="store_true", help="Run with test problem")
    parser.add_argument("--token", type=str, help="Authentication token")
    parser.add_argument("--no-prefetch", action="store_true", help="Skip prefetching of common entities")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--reset-cache", action="store_true", help="Reset the cache before starting")
    return parser

def main():
    """Main entry point for the CLI application."""
    # Parse command-line arguments
    parser = create_parser()
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Set debug mode in logger
    set_debug_mode(args.debug)
    
    # Get token from environment or command-line
    token = args.token or os.getenv("AUTH_TOKEN")
    if not token:
        token = input(f"{Fore.YELLOW}Please provide your authentication token: {Style.RESET_ALL}")
    
    # Initialize the API client
    api_client = APIClient(token)
    
    # Print the banner
    print(f"{Fore.CYAN}Star Wars & Pokémon Challenge Solver{Style.RESET_ALL}")
    print(f"{Fore.CYAN}===================================={Style.RESET_ALL}")
    
    if args.debug:
        debug(f"{Fore.YELLOW}Debug mode enabled{Style.RESET_ALL}")
        
    def setup_environment():
        """Initialize database and prefetch data."""
        # Reset cache if requested
        if args.reset_cache:
            log(f"{Fore.YELLOW}Resetting cache as requested{Style.RESET_ALL}")
            if os.path.exists("api_cache.db"):
                os.remove("api_cache.db")
                log(f"{Fore.GREEN}Cache database deleted{Style.RESET_ALL}")
        
        # Initialize database
        initialize_db()
        
        # Load cache from database
        load_cache()
        
        # Log cache stats before prefetching
        debug(f"Cache before prefetching: {len(cache['pokemon'])} Pokémon, "
              f"{len(cache['swapi_characters'])} Star Wars characters, "
              f"{len(cache['swapi_planets'])} Star Wars planets")
        
        # Prefetch data if necessary
        if not args.no_prefetch:
            prefetch_pokemon(api_client)
            prefetch_starwars(api_client)
            
            # Log cache stats after prefetching
            debug(f"Cache after prefetching: {len(cache['pokemon'])} Pokémon, "
                  f"{len(cache['swapi_characters'])} Star Wars characters, "
                  f"{len(cache['swapi_planets'])} Star Wars planets")
        
        return ChallengeRunner(
            api_client, 
            lambda problem: api_client.parse_with_ai(problem),
            evaluate_expression
        )
    
    # Run test or actual challenge
    if args.test:
        runner = setup_environment()
        runner.test()
    else:
        # Ask for confirmation before running the actual challenge
        choice = input(f"{Fore.YELLOW}Run the actual challenge? (y/n): {Style.RESET_ALL}")
        if choice.lower() == 'y':
            runner = setup_environment()
            runner.run()
        else:
            log(f"{Fore.RED}Challenge aborted.{Style.RESET_ALL}")

if __name__ == "__main__":
    main() 