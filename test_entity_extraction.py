"""Test script for entity extraction with spaces."""

from adere_challenge.solvers.expression import evaluate_expression

def test_entity_extraction():
    """Test entity extraction with spaces between quoted entities and attributes."""
    
    # Test formula with space between entity and attribute
    formula = '"stufful".height * "dorin".diameter + "owen lars".mass + "poggle" .height'
    
    # Mock entity data
    class MockApiClient:
        def get_pokemon(self, name, verify=False):
            return MockResponse({"name": "stufful", "height": 5, "weight": 70})
        
        def get_swapi_character(self, name, verify=False):
            if name == "owen lars":
                return MockResponse({"results": [{"name": "Owen Lars", "height": "178", "mass": "120"}]})
            elif name == "poggle":
                return MockResponse({"results": [{"name": "Poggle the Lesser", "height": "96", "mass": "80"}]})
            return MockResponse({"results": []})
            
        def get_swapi_planet(self, name, verify=False):
            if name == "dorin":
                return MockResponse({"results": [{"name": "Dorin", "diameter": "13400"}]})
            return MockResponse({"results": []})

    class MockResponse:
        def __init__(self, data, status_code=200):
            self.data = data
            self.status_code = status_code
            
        def json(self):
            return self.data
    
    print(f"Testing formula: {formula}")
    
    # Test the expression evaluation
    result, entities_log, calculation_log = evaluate_expression(formula, MockApiClient())
    
    print("\nEntities Log:")
    print(entities_log)
    
    print("\nCalculation Log:")
    print(calculation_log)
    
    print(f"\nFinal Result: {result}")
    
    # Check if the result is as expected
    expected = 5 * 13400 + 120 + 96
    print(f"Expected Result: {expected}")
    print(f"Test {'PASSED' if result == expected else 'FAILED'}")

if __name__ == "__main__":
    test_entity_extraction() 