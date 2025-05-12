"""Expression evaluation logic."""

import re
from colorama import Fore, Style

from adere_challenge.utils.logger import log
from adere_challenge.utils.constants import COMPOUND_POKEMON_NAMES, HYPHENATED_POKEMON, NAME_VARIATIONS
from adere_challenge.solvers.entities import normalize_entity_name, get_entity_data

def evaluate_expression(formula, api_client=None):
    """Evaluate a mathematical expression.
    
    Args:
        formula: Formula string to evaluate
        api_client: API client instance (optional)
        
    Returns:
        tuple: (result, entities_log, calculation_log)
    """
    # Handle None or empty formula
    if formula is None or not formula.strip():
        log(f"{Fore.RED}Cannot evaluate None or empty formula.{Style.RESET_ALL}")
        return 0, "No formula to evaluate", "Error: No formula provided"
        
    log(f"{Fore.BLUE}Original formula: {Fore.CYAN}{formula}{Style.RESET_ALL}")
    
    # Pre-process formula to clean up spaces between quoted entities and attributes
    # Fix cases like "entity" .attribute -> "entity".attribute
    formula = re.sub(r'("([^"]+)")\s+\.([a-zA-Z_][a-zA-Z0-9_]*)', r'\1.\3', formula)
    log(f"{Fore.BLUE}Preprocessed formula: {Fore.CYAN}{formula}{Style.RESET_ALL}")
    
    # We'll collect all variables mentioned in the formula
    variables = {}
    
    # Collection for logging
    entities_log = []
    
    # Extract entity names and attributes from the formula - handle both quoted and unquoted names
    # This complex pattern handles several cases:
    # 1. "entity name".attribute - quoted multi-word entities
    # 2. entity.attribute - simple unquoted entities
    # 3. entity.name.attribute - incorrectly parsed multi-word entities with dots
    entity_pattern = re.compile(r'("([^"]+)"|([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*))\.([a-zA-Z_][a-zA-Z0-9_]*)')
    
    # Process for both compound names with spaces and hyphenated names
    combined_special_names = list(set(COMPOUND_POKEMON_NAMES + HYPHENATED_POKEMON))
    
    # Special handling for special Pokemon names in formula before extraction
    for special_name in combined_special_names:
        # Look for variations of the special name without quotes
        space_version = special_name.replace("-", " ")
        variations = [
            special_name,            # original form (tapu-koko or tapu koko)
            special_name.replace(" ", "").replace("-", ""),  # no spaces/hyphens (tapukoko)
            special_name.replace(" ", "-"),  # spaces to hyphens (tapu-koko)
            special_name.replace("-", " "),  # hyphens to spaces (tapu koko)
            special_name.replace(" ", ".").replace("-", ".")   # dotted (tapu.koko)
        ]
        
        for variation in variations:
            # Replace all instances not in quotes with the quoted version
            # Only replace when it's a standalone term, not part of another word
            # This is a complex regex that handles boundaries correctly
            formula = re.sub(
                r'(?<!")\b' + re.escape(variation) + r'\b(?!")', 
                f'"{special_name}"', 
                formula, 
                flags=re.IGNORECASE
            )
    
    # First, find all entities in the formula
    entities_to_process = []
    for match in entity_pattern.finditer(formula):
        full_match, quoted_name, dotted_name, attribute = match.groups()
        
        # Get the actual entity name (either from quotes or from dotted notation)
        if quoted_name:
            entity_name = quoted_name
        else:
            entity_name = dotted_name
        
        # Normalize the entity name
        normalized_name = normalize_entity_name(entity_name)
        
        # Check for name variations
        if normalized_name in NAME_VARIATIONS:
            normalized_name = NAME_VARIATIONS[normalized_name]
            
        # Check for compound Pokémon names when we have a partial match
        for compound_name in COMPOUND_POKEMON_NAMES:
            compound_parts = compound_name.split()
            if (normalized_name == compound_parts[0] and len(compound_parts) > 1):
                log(f"{Fore.YELLOW}Found partial match for compound Pokémon name: '{normalized_name}' → '{compound_name}'{Style.RESET_ALL}")
                normalized_name = compound_name
                break
        
        # Store for processing
        entities_to_process.append((match.group(0), normalized_name, attribute))

    # Print a summary of all entities found in the formula
    log(f"{Fore.BLUE}Found {Fore.WHITE}{len(entities_to_process)}{Fore.BLUE} entities in formula:{Style.RESET_ALL}")
    for _, entity_name, attribute in entities_to_process:
        log(f"{Fore.CYAN}  • {Fore.WHITE}{entity_name}{Fore.CYAN}.{Fore.WHITE}{attribute}{Style.RESET_ALL}")
    
    # Now fetch data for all entities
    for original_text, entity_name, attribute in entities_to_process:
        # If we haven't fetched this entity yet
        if entity_name not in variables:
            # Use the centralized entity resolution function
            entity_data, entity_type = get_entity_data(entity_name, api_client)
            variables[entity_name] = entity_data
    
    # Replace all entity references with actual values
    eval_formula = formula
    # Print a summary of all entity values being used
    log(f"{Fore.BLUE}Entity values used in calculation:{Style.RESET_ALL}")
    for original_text, entity_name, attribute in entities_to_process:
        if entity_name in variables and attribute in variables[entity_name]:
            # Get the attribute value
            value = variables[entity_name][attribute]
            
            # No unit conversions - use the original value
            log_entry = f"{entity_name}.{attribute} = {value}"
            entities_log.append(log_entry)
            log(f"{Fore.CYAN}  • {Fore.WHITE}{entity_name}{Fore.CYAN}.{Fore.WHITE}{attribute}{Fore.CYAN} = {Fore.WHITE}{value}{Style.RESET_ALL}")
            
            # Replace the complete original text with the value
            eval_formula = eval_formula.replace(original_text, str(value))
        else:
            if entity_name in variables:
                log(f"{Fore.YELLOW}Warning: Attribute '{Fore.WHITE}{attribute}{Fore.YELLOW}' not found for entity '{Fore.WHITE}{entity_name}{Fore.YELLOW}'{Style.RESET_ALL}")
                log(f"{Fore.BLUE}Available attributes: {Fore.WHITE}{list(variables[entity_name].keys())}{Fore.BLUE}{Style.RESET_ALL}")
            # Default to 0 if we can't find the attribute
            log_entry = f"{entity_name}.{attribute} = 0 (NOT FOUND)"
            entities_log.append(log_entry)
            log(f"{Fore.RED}Using default value 0 for {Fore.WHITE}{entity_name}{Fore.RED}.{Fore.WHITE}{attribute}{Style.RESET_ALL}")
            eval_formula = eval_formula.replace(original_text, "0")
    
    # Additional cleanup to remove any remaining entity names that might not have been properly matched
    # This regex will find words that aren't part of a mathematical expression
    remaining_words_pattern = re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*')
    
    # Check if there are still words in the formula
    if remaining_words_pattern.search(eval_formula):
        log(f"{Fore.YELLOW}Warning: Found remaining words in formula. Cleaning up: {Fore.CYAN}{eval_formula}{Style.RESET_ALL}")
        
        # Replace any remaining words with 0
        eval_formula = remaining_words_pattern.sub("0", eval_formula)
        log(f"{Fore.YELLOW}Cleaned formula: {Fore.CYAN}{eval_formula}{Style.RESET_ALL}")
    
    # Handle any spaces between numbers that could cause issues (like "5 6" which is invalid)
    # Replace patterns like "number space number" with "number operator number"
    eval_formula = re.sub(r'(\d+)\s+(\d+)', r'\1+\2', eval_formula)
    
    # Evaluate the formula
    try:
        log(f"{Fore.BLUE}Evaluating formula: {Fore.CYAN}{eval_formula}{Style.RESET_ALL}")
        result = eval(eval_formula)
        # Round to 10 decimal places as specified in the challenge and ensure it's not in scientific notation
        result = float(f"{float(result):.10f}")
        log(f"{Fore.MAGENTA}Result: {Fore.WHITE}{result}{Style.RESET_ALL}")
        
        # Return the result along with logging information
        calculation_log = f"Formula: {formula}\nEvaluating: {eval_formula}\nResult: {result:.10f}"
        return result, "\n".join(entities_log), calculation_log
    except Exception as e:
        log(f"{Fore.RED}Error evaluating formula: {e}{Style.RESET_ALL}")
        log(f"{Fore.RED}Formula: {eval_formula}{Style.RESET_ALL}")
        
        # Last resort cleanup - try to salvage the calculation by replacing everything non-numeric
        # with basic operations
        try:
            # This is a more aggressive approach that keeps only numbers and basic operators
            clean_formula = re.sub(r'[^0-9+\-*/().\s]', '0', eval_formula)
            # Replace multiple consecutive zeros with a single zero
            clean_formula = re.sub(r'0+', '0', clean_formula)
            # Handle any invalid math operations like double operators
            clean_formula = re.sub(r'[\+\-\*/]{2,}', '+', clean_formula)
            
            log(f"{Fore.YELLOW}Attempting last-resort cleanup. New formula: {Fore.CYAN}{clean_formula}{Style.RESET_ALL}")
            
            # Try evaluating the cleaned formula
            result = eval(clean_formula)
            # Format with 10 decimal places without scientific notation
            result = float(f"{float(result):.10f}")
            log(f"{Fore.GREEN}Salvaged result: {Fore.WHITE}{result}{Style.RESET_ALL}")
            
            # Return the result along with logging information
            calculation_log = f"Formula: {formula}\nEvaluating (after cleanup): {clean_formula}\nResult: {result:.10f}"
            return result, "\n".join(entities_log), calculation_log
        except Exception as e2:
            log(f"{Fore.RED}Cleanup failed: {e2}{Style.RESET_ALL}")
            return None, "\n".join(entities_log), f"Error: {str(e)}\nCleanup error: {str(e2)}" 