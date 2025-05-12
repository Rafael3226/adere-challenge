"""Command-line interface for Adere Challenge."""

import os
import argparse
from dotenv import load_dotenv
from colorama import Fore, Style, init

from adere_challenge.api.client import APIClient
from adere_challenge.data.cache import initialize_db, load_cache
from adere_challenge.data.pokemon import prefetch_pokemon
from adere_challenge.data.starwars import prefetch_starwars
from adere_challenge.solvers.expression import evaluate_expression
from adere_challenge.challenge.runner import ChallengeRunner
from adere_challenge.utils.logger import log

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
    return parser

def main():
    """Main entry point for the CLI application."""
    # Parse command-line arguments
    parser = create_parser()
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Get token from environment or command-line
    token = args.token or os.getenv("AUTH_TOKEN")
    if not token:
        token = input(f"{Fore.YELLOW}Please provide your authentication token: {Style.RESET_ALL}")
    
    # Initialize the API client
    api_client = APIClient(token)
    
    # Print the banner
    print(f"{Fore.CYAN}Star Wars & Pokémon Challenge Solver{Style.RESET_ALL}")
    print(f"{Fore.CYAN}===================================={Style.RESET_ALL}")
    
    # Initialize and load the cache at startup
    initialize_db()
    load_cache()
    
    # Prefetch data if necessary
    if not args.no_prefetch:
        prefetch_pokemon(api_client)
        prefetch_starwars(api_client)
    
    # Create the challenge runner
    runner = ChallengeRunner(
        api_client, 
        lambda problem: api_client.parse_with_ai(problem),
        evaluate_expression
    )
    
    # Run test or actual challenge
    if args.test:
        runner.test()
    else:
        # Ask for confirmation before running the actual challenge
        choice = input(f"{Fore.YELLOW}Run the actual challenge? (y/n): {Style.RESET_ALL}")
        if choice.lower() == 'y':
            runner.run()
        else:
            log(f"{Fore.RED}Challenge aborted.{Style.RESET_ALL}")

if __name__ == "__main__":
    main() 