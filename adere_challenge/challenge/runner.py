"""Challenge runner for solving problems."""

import time
import json
from colorama import Fore, Style

from adere_challenge.utils.logger import log, debug
from adere_challenge.data.cache import check_problem_cache, add_to_problem_cache, log_failed_problem

class ChallengeRunner:
    """Runner for the Adere Challenge."""
    
    def __init__(self, api_client, parser_fn, evaluator_fn):
        """Initialize the challenge runner.
        
        Args:
            api_client: API client instance
            parser_fn: Function to parse problems into formulas
            evaluator_fn: Function to evaluate formulas
        """
        self.api_client = api_client
        self.parse_problem = parser_fn
        self.evaluate_expression = evaluator_fn
    
    def test(self):
        """Test the solver with the practice endpoint."""
        response = self.api_client.get("/challenge/test")
        if response.status_code != 200:
            log(f"{Fore.RED}Error getting test problem: {response.status_code} - {response.text}{Style.RESET_ALL}")
            return
        
        try:
            data = response.json()
            problem = data.get("problem")
            expected_answer = data.get("answer")
            
            if not problem:
                log(f"{Fore.RED}No problem in test response{Style.RESET_ALL}")
                return
                
            log(f"{Fore.CYAN}Test problem: {Fore.WHITE}{problem}{Style.RESET_ALL}")
            
            # Parse the problem using AI
            formula = self.parse_problem(problem)
            
            # Evaluate the formula
            answer, entities_info, calculation_info = self.evaluate_expression(formula, self.api_client)
            
            log(f"{Fore.BLUE}Calculated answer: {Fore.WHITE}{answer}{Style.RESET_ALL}")
            if expected_answer is not None:
                log(f"{Fore.BLUE}Expected answer: {Fore.WHITE}{expected_answer}{Style.RESET_ALL}")
                
                # Check if our answer matches the expected answer
                if abs(answer - expected_answer) < 1e-6:  # Allow for small floating-point differences
                    log(f"{Fore.GREEN}✅ Test passed. The calculated answer matches the expected answer.{Style.RESET_ALL}")
                else:
                    log(f"{Fore.RED}❌ Test failed. The calculated answer doesn't match the expected answer.{Style.RESET_ALL}")
                    
                    # Log the failed test to the failed_problems directory
                    # Create a mock response data structure similar to what the challenge endpoint would return
                    mock_response = {
                        "message": "Test failed. The calculated answer doesn't match the expected answer.",
                        "problem": problem,
                        "expected_answer": expected_answer,
                        "calculated_answer": answer
                    }
                    
                    log_failed_problem(
                        problem_text=problem,
                        formula=formula,
                        answer=answer,
                        response_data=mock_response,
                        entities_info=entities_info,
                        calculation=calculation_info
                    )
                    
                    log(f"{Fore.YELLOW}Failed test problem has been logged to the failed_problems directory.{Style.RESET_ALL}")
            else:
                log(f"{Fore.YELLOW}No expected answer in test response. Cannot verify correctness.{Style.RESET_ALL}")
                
        except Exception as e:
            log(f"{Fore.RED}Error testing solver: {str(e)}{Style.RESET_ALL}")
    
    def run(self):
        """Run the actual challenge."""
        # Start the challenge
        start_response = self.api_client.get("/challenge/start")
        if start_response.status_code != 200:
            log(f"{Fore.RED}Error starting challenge: {start_response.status_code} - {start_response.text}{Style.RESET_ALL}")
            return
        
        start_data = start_response.json()
        debug(f"{Fore.BLUE}Start response: {json.dumps(start_data, indent=2)}{Style.RESET_ALL}")
        
        # Handle different possible response formats
        if "problem_id" in start_data:
            problem_id = start_data["problem_id"]
        elif "id" in start_data:
            problem_id = start_data["id"]
        else:
            log(f"{Fore.RED}Error: Could not find problem ID in response: {json.dumps(start_data, indent=2)}{Style.RESET_ALL}")
            return
        
        if "problem" in start_data:
            problem = start_data["problem"]
            has_problem = True
        else:
            log(f"{Fore.RED}Error: Could not find problem text in response: {json.dumps(start_data, indent=2)}{Style.RESET_ALL}")
            return
        
        solved_count = 0
        attempted_count = 0
        start_time = time.time()
        
        # Loop continues as long as we have a problem to solve
        while has_problem:
            attempted_count += 1
            current_time = time.time()
            elapsed_time = current_time - start_time
            
            # Check if we have a valid problem
            if problem is None:
                log(f"{Fore.RED}Received null problem. Ending challenge.{Style.RESET_ALL}")
                has_problem = False
                break
            
            log(f"\n{Fore.CYAN}Problem #{attempted_count} (Time: {Fore.WHITE}{elapsed_time:.2f}s{Fore.CYAN}): {Fore.WHITE}{problem}{Style.RESET_ALL}")
            
            # Check if this problem is already in our cache
            try:
                is_cached, cached_formula, cached_answer = check_problem_cache(problem)
            except Exception as e:
                debug(f"{Fore.RED}Error checking cache: {str(e)}{Style.RESET_ALL}")
                is_cached = False
                cached_formula = None
                cached_answer = None
            
            if is_cached:
                debug(f"{Fore.GREEN}CACHE HIT! Problem found in cache.{Style.RESET_ALL}")
                debug(f"{Fore.BLUE}Cached formula: {Fore.CYAN}{cached_formula}{Style.RESET_ALL}")
                debug(f"{Fore.MAGENTA}Cached answer: {Fore.WHITE}{cached_answer}{Style.RESET_ALL}")
                formula = cached_formula
                answer = cached_answer
                entities_info = None
                calculation_info = None
            else:
                debug(f"{Fore.YELLOW}Cache miss. Calculating answer...{Style.RESET_ALL}")
                # Parse problem with AI
                try:
                    formula = self.parse_problem(problem)
                    debug(f"{Fore.BLUE}AI Formula: {Fore.CYAN}{formula}{Style.RESET_ALL}")
                except Exception as e:
                    debug(f"{Fore.RED}Error parsing problem: {str(e)}{Style.RESET_ALL}")
                    formula = None
                
                # Evaluate the formula if we have one
                if formula is not None:
                    try:
                        result = self.evaluate_expression(formula, self.api_client)
                        if isinstance(result, tuple) and len(result) == 3:
                            answer, entities_info, calculation_info = result
                        else:
                            answer = result
                            entities_info = None
                            calculation_info = None
                    except Exception as e:
                        debug(f"{Fore.RED}Error evaluating formula: {str(e)}{Style.RESET_ALL}")
                        answer = 0
                        entities_info = None
                        calculation_info = None
                else:
                    debug(f"{Fore.RED}No formula available. Using default answer 0.{Style.RESET_ALL}")
                    answer = 0
                    entities_info = None
                    calculation_info = None
            
            # Handle case where we couldn't calculate an answer
            if answer is None:
                debug(f"{Fore.RED}No valid answer calculated. Using default answer 0.{Style.RESET_ALL}")
                # Use a default value that is likely incorrect but allows us to get the next problem
                answer = 0
                
            # Submit the solution
            solution_data = {
                "problem_id": problem_id,
                "answer": answer
            }
            
            has_problem = False  # Reset for this iteration
            try:
                solution_response = self.api_client.post("/challenge/solution", solution_data)
                
                if solution_response.status_code == 200:
                    solution_data = solution_response.json()
                    
                    # Debug the response
                    debug(f"{Fore.BLUE}API Response: {json.dumps(solution_data, indent=2)}{Style.RESET_ALL}")
                    
                    # Check if time limit was exceeded
                    if "message" in solution_data and solution_data["message"] == "Time limit exceeded.":
                        log(f"{Fore.YELLOW}⏱️ API time limit exceeded. Challenge will continue but score may not be recorded.{Style.RESET_ALL}")
                        was_correct = False
                        log(f"{Fore.RED}❌ INCORRECT. Time limit exceeded is considered as wrong answer.{Style.RESET_ALL}")
                    
                    # Check if answer was correct based on the message field
                    was_correct = False
                    if "message" in solution_data:
                        if solution_data["message"] == "Correct answer.":
                            was_correct = True
                            solved_count += 1
                            log(f"{Fore.GREEN}✅ CORRECT! Your answer was right.{Style.RESET_ALL}")
                            
                            # Only add to cache if the answer was correct and not already cached
                            if not is_cached and answer is not None and formula:
                                debug(f"{Fore.GREEN}Adding correct solution to problem cache.{Style.RESET_ALL}")
                                add_to_problem_cache(problem, formula, answer)
                                
                        elif solution_data["message"] == "Incorrect answer.":
                            was_correct = False
                            log(f"{Fore.RED}❌ INCORRECT. Your answer was wrong.{Style.RESET_ALL}")
                            
                            # Log failed problem
                            if not is_cached and answer is not None and formula:
                                debug("Logging failed problem for analysis")
                                log_failed_problem(
                                    problem_text=problem,
                                    formula=formula,
                                    answer=answer,
                                    response_data=solution_data,
                                    entities_info=entities_info,
                                    calculation=calculation_info
                                )
                    
                    # Check if there's a next problem
                    if "next_problem" in solution_data:
                        next_problem_data = solution_data["next_problem"]
                        
                        # Check if we have a null next problem
                        if next_problem_data is None:
                            log(f"{Fore.YELLOW}No more problems available. Challenge completed.{Style.RESET_ALL}")
                            break
                        
                        if isinstance(next_problem_data, dict):
                            # Handle the case where next_problem is a dictionary with problem and ID
                            if "problem" in next_problem_data:
                                problem = next_problem_data["problem"]
                                has_problem = True
                            
                            if "problem_id" in next_problem_data:
                                problem_id = next_problem_data["problem_id"]
                            elif "id" in next_problem_data:
                                problem_id = next_problem_data["id"]
                        else:
                            # Handle the case where next_problem is just the problem text
                            problem = next_problem_data
                            if problem is not None:
                                has_problem = True
                    
                    # Check if there's a problem_id for the next problem
                    if "next_problem_id" in solution_data:
                        problem_id = solution_data["next_problem_id"]
                    
                    # Check for completion
                    if "completed" in solution_data and solution_data["completed"]:
                        log(f"{Fore.GREEN}🎉 Challenge completed!{Style.RESET_ALL}")
                        has_problem = False
                        
                        # Display score if available
                        if "score" in solution_data:
                            score = solution_data["score"]
                            log(f"{Fore.GREEN}Your score: {Fore.WHITE}{score}{Style.RESET_ALL}")
                            
                        # Display any final message
                        if "message" in solution_data:
                            log(f"{Fore.CYAN}Final message: {Fore.WHITE}{solution_data['message']}{Style.RESET_ALL}")
                            
                        break
                else:
                    log(f"{Fore.RED}Error submitting solution: {solution_response.status_code} - {solution_response.text}{Style.RESET_ALL}")
                    # Try to continue if possible
            except Exception as e:
                log(f"{Fore.RED}Exception during solution submission: {str(e)}{Style.RESET_ALL}")
                break
        
        # Challenge completed or error occurred
        end_time = time.time()
        total_time = end_time - start_time
        log(f"\n{Fore.GREEN}Challenge Summary:{Style.RESET_ALL}")
        log(f"{Fore.CYAN}Total problems attempted: {Fore.WHITE}{attempted_count}{Style.RESET_ALL}")
        log(f"{Fore.CYAN}Total problems solved: {Fore.WHITE}{solved_count}{Style.RESET_ALL}")
        log(f"{Fore.CYAN}Success rate: {Fore.WHITE}{(solved_count/attempted_count)*100 if attempted_count > 0 else 0:.2f}%{Style.RESET_ALL}")
        log(f"{Fore.CYAN}Total time: {Fore.WHITE}{total_time:.2f} seconds{Style.RESET_ALL}") 