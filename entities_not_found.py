"""
Script to extract entities not found and checkofailed_problems from the failed_problems directory.
This generates a report of entities that could not be found during problem solving
and analyzes the patterns in failed problems.
"""

import os
import re
import json
from collections import defaultdict

# Dictionary to store entities with mismatched or incorrect values
entities_mismatched = []
# List to store failed problems
checkofailed_problems = []

def extract_failed_problems():
    """Extract failed problems from the failed_problems directory."""
    # Path to the failed_problems directory
    failed_dir = 'failed_problems'
    
    # Check if directory exists
    if not os.path.exists(failed_dir):
        print(f"Directory '{failed_dir}' not found.")
        return
    
    # Go through each file in the failed_problems directory
    for filename in os.listdir(failed_dir):
        if not filename.endswith('.txt'):
            continue
        
        filepath = os.path.join(failed_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
            
            # Only process files that contain test failures
            if "Test failed" not in content and "FAILED PROBLEM LOG" not in content:
                continue
                
            # Extract problem hash if available
            hash_match = re.search(r'HASH:\s*([a-f0-9]+)', content)
            problem_hash = hash_match.group(1) if hash_match else "unknown"
            
            # Extract problem text
            problem_match = re.search(r'PROBLEM TEXT:\s*(.*?)(?=\n\n|\nFORMULA)', content, re.DOTALL)
            problem_text = problem_match.group(1).strip() if problem_match else "Unknown problem"
            
            # Extract formula
            formula_match = re.search(r'FORMULA:\s*(.*?)(?=\n\n|\nENTITIES)', content)
            formula = formula_match.group(1).strip() if formula_match else ""
            
            # Extract entities used
            entities_used_match = re.search(r'ENTITIES USED:(.*?)(?=\n\n|\nCALCULATION:)', content, re.DOTALL)
            entities_used_text = entities_used_match.group(1).strip() if entities_used_match else ""
            
            # Parse entities that were used
            used_entities = {}
            if entities_used_text:
                for line in entities_used_text.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Match patterns like "entity.attribute = value"
                    entity_match = re.match(r'([^.]+)\.([^ ]+)\s*=\s*(.+)', line)
                    if entity_match:
                        entity, attribute, value = entity_match.groups()
                        entity = entity.strip()
                        used_entities[(entity, attribute)] = value
            
            # Extract expected and calculated answers
            expected_match = re.search(r'"expected_answer":\s*([^,\n}]+)', content)
            calculated_match = re.search(r'"calculated_answer":\s*([^,\n}]+)', content)
            
            expected = expected_match.group(1) if expected_match else "Unknown"
            calculated = calculated_match.group(1) if calculated_match else "Unknown"
            
            # Extract analysis if available
            analysis_match = re.search(r'ANALYSIS:(.*?)(?=\n\n|$)', content, re.DOTALL)
            analysis = analysis_match.group(1).strip() if analysis_match else ""
            
            # Check if there's any indication of entity mismatches in the analysis
            mismatched_entities = []
            if analysis:
                # Look for lines that mention entities possibly having incorrect values
                entity_lines = re.findall(r'([a-zA-Z0-9_\- ]+)\'s ([a-zA-Z_]+) should (potentially be|be) ([0-9.]+) rather than ([0-9.]+)', analysis)
                for entity, attribute, _, correct_value, wrong_value in entity_lines:
                    mismatched_entities.append({
                        'entity': entity.strip(),
                        'attribute': attribute.strip(),
                        'expected_value': correct_value,
                        'actual_value': wrong_value,
                        'problem_hash': problem_hash
                    })
                    
                    # Add to global list
                    entities_mismatched.append({
                        'entity': entity.strip(),
                        'attribute': attribute.strip(),
                        'expected_value': correct_value,
                        'actual_value': wrong_value,
                        'problem_hash': problem_hash
                    })
                
                # If no entity lines were found with the pattern above, look for specific mentions
                if not mismatched_entities and "indicates" in analysis and "should" in analysis:
                    # Try a more generic pattern
                    generic_match = re.search(r'indicates\s+([a-zA-Z0-9_\- ]+)\'s\s+([a-zA-Z_]+)\s+should\s+.*?\s+([0-9.]+)\s+', analysis)
                    if generic_match:
                        entity, attribute, value = generic_match.groups()
                        for (e, a), v in used_entities.items():
                            if e.lower() == entity.lower() and a.lower() == attribute.lower():
                                mismatched_entities.append({
                                    'entity': entity.strip(),
                                    'attribute': attribute.strip(),
                                    'expected_value': value,
                                    'actual_value': v,
                                    'problem_hash': problem_hash
                                })
                                
                                # Add to global list
                                entities_mismatched.append({
                                    'entity': entity.strip(),
                                    'attribute': attribute.strip(),
                                    'expected_value': value,
                                    'actual_value': v,
                                    'problem_hash': problem_hash
                                })
            
            # Add to the list of failed problems
            checkofailed_problems.append({
                'hash': problem_hash,
                'problem_text': problem_text,
                'formula': formula,
                'expected_answer': expected,
                'calculated_answer': calculated,
                'used_entities': used_entities,
                'mismatched_entities': mismatched_entities,
                'analysis': analysis
            })

def generate_report():
    """Generate a report of entities not found and failed problems."""
    print("===== CHECKOFAILED PROBLEMS =====")
    if not checkofailed_problems:
        print("No failed problems found.")
    else:
        print(f"Found {len(checkofailed_problems)} failed problems.")
        for i, problem in enumerate(checkofailed_problems, 1):
            print(f"\n{i}. Problem Hash: {problem['hash']}")
            # Truncate formula to 70 characters if longer
            formula = problem['formula']
            if len(formula) > 70:
                formula = formula[:67] + "..."
            print(f"   Formula: {formula}")
            print(f"   Expected Answer: {problem['expected_answer']}")
            print(f"   Calculated Answer: {problem['calculated_answer']}")
            
            if problem['mismatched_entities']:
                print("   Mismatched Entities:")
                for entity_info in problem['mismatched_entities']:
                    print(f"     - {entity_info['entity']}.{entity_info['attribute']}: "
                          f"Expected {entity_info['expected_value']} but got {entity_info['actual_value']}")
            
            # Print brief analysis if available and no mismatches found
            if not problem['mismatched_entities'] and problem['analysis']:
                print("   Analysis Summary:")
                # Extract first two sentences of analysis
                sentences = re.split(r'(?<=[.!?])\s+', problem['analysis'].strip())
                summary = ' '.join(sentences[:2]) if len(sentences) > 1 else problem['analysis']
                # Truncate to 100 characters if longer
                if len(summary) > 100:
                    summary = summary[:97] + "..."
                print(f"     {summary}")
    
    print("\n\n===== ENTITIES WITH MISMATCHED VALUES =====")
    if not entities_mismatched:
        print("No entities with mismatched values found.")
    else:
        # Group by entity and attribute
        entity_groups = defaultdict(list)
        for entity_info in entities_mismatched:
            key = (entity_info['entity'], entity_info['attribute'])
            entity_groups[key].append(entity_info)
        
        # Print summary grouped by entity and attribute
        for (entity, attribute), infos in sorted(entity_groups.items()):
            print(f"\nEntity: {entity}.{attribute}")
            print(f"Found in {len(infos)} problems")
            
            # If there are multiple expected values, show them all
            expected_values = set(info['expected_value'] for info in infos)
            actual_values = set(info['actual_value'] for info in infos)
            
            if len(expected_values) == 1 and len(actual_values) == 1:
                print(f"  Should be: {list(expected_values)[0]} instead of {list(actual_values)[0]}")
            else:
                print("  Value mismatches:")
                for info in infos:
                    print(f"  - Problem {info['problem_hash']}: "
                          f"Should be {info['expected_value']} instead of {info['actual_value']}")

if __name__ == "__main__":
    extract_failed_problems()
    generate_report() 