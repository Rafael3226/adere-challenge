# Adere Challenge Solver

A modular solver for the Adere coding challenge involving Star Wars characters and Pokémon.

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/adere-challenge.git
cd adere-challenge

# Install the package in development mode
pip install -e .
```

## Configuration

Create a `.env` file in the root directory with your authentication token:

```
AUTH_TOKEN=your_token_here
```

## Usage

Run the challenge solver:

```bash
# Run with test problem
adere --test

# Run the actual challenge
adere

# Skip prefetching data (faster startup, but might be slower for first queries)
adere --no-prefetch
```

Or use with explicit token:

```bash
adere --token your_token_here
```

## Project Structure

```
adere-challenge/
├── adere_challenge/           # Main package
│   ├── __init__.py
│   ├── cli.py                 # CLI entry point
│   ├── api/                   # API client functionality
│   │   ├── __init__.py
│   │   ├── client.py          # API client
│   │   └── endpoints.py       # API endpoints
│   ├── data/                  # Data management
│   │   ├── __init__.py
│   │   ├── cache.py           # Database cache
│   │   ├── pokemon.py         # Pokemon API interactions
│   │   └── starwars.py        # Star Wars API interactions
│   ├── solvers/               # Problem solvers
│   │   ├── __init__.py
│   │   ├── entities.py        # Entity name handling
│   │   └── expression.py      # Expression evaluation
│   ├── challenge/             # Challenge runner
│   │   ├── __init__.py
│   │   └── runner.py          # Challenge execution
│   └── utils/                 # Utilities
│       ├── __init__.py
│       ├── constants.py       # Common constants
│       └── logger.py          # Logging utility
├── failed_problems/           # Logs for failed problems
├── setup.py                   # Package setup
├── requirements.txt           # Dependencies
└── .env                       # Environment variables
```

## Features

- Caching of API responses to avoid redundant requests
- Smart entity name resolution across different APIs
- Problem parsing using AI
- Mathematical expression evaluation
- Detailed logging and error handling
- Command-line interface

## Overview

The challenge requires solving mathematical problems involving attributes of:
- Star Wars characters
- Star Wars planets
- Pokémon

The script uses GPT to parse the problem statements, fetches data from the relevant APIs, performs calculations, and submits answers.

## Setup

1. Install dependencies:
```
pip install requests python-dotenv colorama
```

2. Create a `.env` file in the same directory with your authentication token:
```
AUTH_TOKEN=your_token_here
```
Replace `your_token_here` with the token you received from Adere.so after registration.

## Usage

Run the script:
```
python main.py
```

You'll be presented with two options:
1. Test with a practice problem - to verify your solution works
2. Run the actual challenge - to solve as many problems as possible

Before executing any option, the script will:
1. Initialize or connect to the SQLite database (`api_cache.db`)
2. Load any previously cached data into memory
3. If a sufficiently populated database exists, skip prefetching to save time
4. Otherwise, automatically prefetch and cache data for common entities
5. Store newly encountered entities in the database during execution

The SQLite database provides a robust and persistent cache that survives between runs, allowing the script to start instantly on subsequent executions.

## Features

### Problem Caching

The script stores verified correct problem solutions:
- Each problem text is hashed to create a unique identifier
- Only correct answers are stored in the cache (verified by the API)
- The formula, answer, and timestamp are saved to the SQLite database
- When a problem is encountered again, the cached answer is used immediately
- This eliminates the need to recalculate solutions for repeat problems
- Dramatically improves performance when the challenge repeats questions

This complete caching solution saves time on both API calls and AI processing for problems that have been solved before.

### Intelligent API Selection

The script uses a sophisticated algorithm to determine which API is most likely to contain an entity:
- Analyzes entity names for patterns specific to each universe
- Assigns scores based on name characteristics and linguistic patterns
- Creates a custom API search order for each entity
- Displays the search order in the console output
- Reduces unnecessary API calls by trying the most likely source first

This targeted approach significantly improves entity resolution speed and accuracy by minimizing failed API requests.

### Enhanced Entity Resolution

The script includes several mechanisms to improve entity matching:
- Preserves hyphens in special Pokémon names (e.g., "kommo-o")
- Handles compound names like "Tapu Koko" appropriately
- Uses a comprehensive name variation dictionary to map alternate forms to canonical names
- Special handling for characters like Jabba with hardcoded data when needed
- Removes titles from character names (General, Princess, etc.)
- Displays detailed information about entity resolution and values used in calculations

### No Time Limit Constraint

Unlike earlier versions, the script now continues running until all problems are solved:
- No artificial time limit constraints
- Processes all available problems from the challenge
- Continues even after the API's time limit message
- Tracks which problems were solved correctly and provides accurate statistics

### Colorized CLI

The script uses colorama for a visually appealing and easy-to-read color-coded CLI:
- ✅ Green for success messages and correct answers
- ❌ Red for errors and failures
- 🟡 Yellow for warnings and important alerts
- 🔵 Blue for information and status updates
- 🟣 Magenta for results and calculated values
- 🔆 Cyan for headings and problem statements
- ⚪ White for highlighted values and data

Colors make it easy to scan the output quickly and identify important information at a glance.

## How It Works

1. The script initializes and connects to the SQLite database
2. Loads existing cached data into memory for fast access
3. If the cache is insufficient, prefetches common entities
4. Retrieves a problem from the Adere.so API
5. Checks if the problem exists in the problem cache
   - If found, uses the cached formula and answer
   - If not found, proceeds with formula generation and calculation
6. For new problems, uses GPT-4o-mini to translate the problem into a mathematical expression
7. For each entity in the expression:
   - First checks the in-memory cache for the entity
   - If not found, uses the enhanced entity resolution system to:
     - Analyze the entity name to determine the most likely API source
     - Try APIs in order of decreasing likelihood
     - Try common name variations (removing spaces, first name only)
     - Create and cache a fallback entity if all lookups fail
8. Evaluates the expression with the retrieved data
9. Submits the answer and waits for confirmation
10. If the answer is correct, caches the problem, formula, and answer for future use
11. Receives the next problem and repeats until no more problems are available
12. Displays comprehensive statistics upon completion

## Recent Improvements

- Only caches problems with verified correct answers
- Treats "Time limit exceeded" responses as incorrect answers
- Preserves hyphens in special Pokémon names (e.g., "kommo-o", "hakamo-o")
- Special case handling for "Jabba" with accurate mass data
- Enhanced entity mapping for commonly misspelled or alternate character names
- Improved logging that shows all entity values used in calculations
- Enhanced accuracy tracking by checking the "message" field in responses

## Performance Optimization

- Uses SQLite for persistent, structured storage of entity data and solved problems
- Maintains a dual-layer cache system (in-memory + database)
- Caches complete problems with their formulas and answers
- Uses MD5 hashing for fast problem lookups
- Implements intelligent API selection based on entity name analysis
- Uses a scoring system with weighted patterns and linguistic heuristics
- Handles unknown entities gracefully with fallback mechanisms
- Strips titles from entity names to improve matching
- Tries multiple name variations to maximize entity matches
- Skips prefetching entirely when sufficient entities are already cached
- Uses efficient SQL queries with primary key lookups for fast data retrieval
- Automatically stores all encountered entities for future use
- Features a color-coded CLI for improved readability and user experience

The combination of comprehensive caching, intelligent API selection, and enhanced entity resolution ensures maximum performance while minimizing unnecessary calculations and API calls.

Good luck with the challenge! 