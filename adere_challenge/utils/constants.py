"""Constants used throughout the application."""

import os

# Database file path
DB_FILE = "api_cache.db"

# Logs directory
LOGS_DIR = "failed_problems"

# Add known compound Pokémon names that need special handling
COMPOUND_POKEMON_NAMES = [
    "tapu koko", "tapu lele", "tapu bulu", "tapu fini",
    "mr mime", "mime jr", "type null", "jangmo o",
    "hakamo o", "kommo o", "porygon z"
]

# Pokemon names with hyphens that should preserve the hyphen
HYPHENATED_POKEMON = [
    "kommo-o", "hakamo-o", "jangmo-o", "ho-oh", "porygon-z",
    "type-null", "mr-mime", "mime-jr", "tapu-koko", "tapu-lele",
    "tapu-bulu", "tapu-fini"
]

# Map of common entity name variations
NAME_VARIATIONS = {
    # Star Wars characters
    "beru": "beru whitesun lars",
    "beruwhitesunlars": "beru whitesun lars",
    "luke": "luke skywalker",
    "lukeskywalker": "luke skywalker",
    "ratts tyerel": "ratts tyerell",  # Note the spelling correction
    "rattstyerel": "ratts tyerell",
    "jabba desilijic tiure": "jabba",  # Handle Jabba's full name
    "jabba the hutt": "jabba",
    "jabba desilijic": "jabba",
    "jabba tiure": "jabba",
    "hutt": "jabba",  # As requested, map hutt to Jabba
    "desilijic": "jabba",
    "ayla secura": "aayla secura",  # Handle typo in Star Wars character name
    "aayla": "aayla secura",
    "general grievous": "grievous",
    "count dooku": "dooku",
    "darth maul": "maul",
    "darth vader": "vader",
    "darth sidious": "palpatine",
    "emperor palpatine": "palpatine",
    "princess leia": "leia",
    "queen amidala": "padmé amidala",
    "padme": "padmé amidala",
    # Pokemon
    "tapu": "tapu koko",  # Add common Tapu variations 
    "tapukoko": "tapu koko",
    "kommo o": "kommo-o",  # Add hyphenated Pokémon variants
    "hakamo o": "hakamo-o",
    "jangmo o": "jangmo-o",
    "spewpa": "spewpa",  # Ensure Spewpa is recognized correctly
    "ho oh": "ho-oh"
}

# Common titles that should be stripped from entity names
COMMON_TITLES = [
    "general", "captain", "commander", "admiral", "lieutenant", 
    "sergeant", "corporal", "private", "master", "lord", "darth",
    "princess", "prince", "king", "queen", "emperor", "empress",
    "doctor", "dr", "professor", "prof", "count", "baron", "sir"
] 