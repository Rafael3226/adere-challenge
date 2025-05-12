# Star Wars & Pokémon Challenge Solver

This script automates the Adere.so programming challenge involving Star Wars and Pokémon data.

## Overview

The challenge requires solving mathematical problems involving attributes of:
- Star Wars characters
- Star Wars planets
- Pokémon

The script uses GPT to parse the problem statements, fetches data from the relevant APIs, performs calculations, and submits answers—all within a 3-minute time limit.

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
2. Run the actual challenge - to solve as many problems as possible in 3 minutes

Before executing either option, the script will:
1. Initialize or connect to the SQLite database (`api_cache.db`)
2. Load any previously cached data into memory
3. If a sufficiently populated database exists, skip prefetching to save time
4. Otherwise, automatically prefetch and cache data for common entities
5. Store newly encountered entities in the database during execution

The SQLite database provides a robust and persistent cache that survives between runs, allowing the script to start instantly on subsequent executions.

## Features

### Intelligent API Selection

The script now uses a sophisticated algorithm to determine which API is most likely to contain an entity:
- Analyzes entity names for patterns specific to each universe
- Assigns scores based on name characteristics and linguistic patterns
- Creates a custom API search order for each entity
- Displays the search order in the console output
- Reduces unnecessary API calls by trying the most likely source first

This targeted approach significantly improves entity resolution speed and accuracy by minimizing failed API requests.

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
5. Uses GPT-4o-mini to translate the problem into a mathematical expression
6. For each entity in the expression:
   - First checks the in-memory cache for the entity
   - If not found, uses the enhanced entity resolution system to:
     - Analyze the entity name to determine the most likely API source
     - Try APIs in order of decreasing likelihood
     - Try common name variations (removing spaces, first name only)
     - Create and cache a fallback entity if all lookups fail
7. Evaluates the expression with the retrieved data
8. Submits the answer and receives the next problem
9. Repeats until the 3-minute limit is reached

## Performance Optimization

- Uses SQLite for persistent, structured storage of entity data
- Maintains a dual-layer cache system (in-memory + database)
- Implements intelligent API selection based on entity name analysis
- Uses a scoring system with weighted patterns and linguistic heuristics
- Handles unknown entities gracefully with fallback mechanisms
- Tries multiple name variations to maximize entity matches
- Skips prefetching entirely when sufficient entities are already cached
- Uses efficient SQL queries with primary key lookups for fast data retrieval
- Automatically stores all encountered entities for future use
- Features a color-coded CLI for improved readability and user experience

The combination of intelligent API selection and enhanced entity resolution ensures maximum success in solving problems while minimizing unnecessary API calls.

Good luck with the challenge! 