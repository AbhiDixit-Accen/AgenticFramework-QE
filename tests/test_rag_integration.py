
import asyncio
import os
import shutil
from unittest.mock import MagicMock, patch

from quality_engineering_agentic_framework.agents.requirement_interpreter import TestCaseGenerationAgent
# Import from where it is used/defined
import quality_engineering_agentic_framework.utils.rag.rag_system as rag_system

# Mock LLM Interface
class MockLLM:
    def __init__(self):
        self.config = {"api_key": "test_api_key_123"}

    async def generate_with_json_output(self, prompt, json_schema, system_message):
        print(f"\n[MockLLM] Received Prompt:\n{prompt[:300]}...") # Print start of prompt
        
        if 'Product/System Context' in prompt and 'This is a test synthesized requirement' in prompt:
            print("\n[VERIFIED]: Prompt contains the injected Product/System Context.")
        else:
            print("\n[FAILED]: Prompt MISSING injected context.")
        
        return {
            "test_cases": [
                {
                    "title": "Test Case 1",
                    "description": "Verified integration",
                    "preconditions": ["Given RAG is working"],
                    "actions": ["When prompt is generated"],
                    "expected_results": ["Then context is present"],
                    "test_data": {}
                }
            ]
        }

async def test_integration():
    print("Starting Integration Test for Requirement Interpreter RAG...")
    
    # 1. Mock the RAG system functions to avoid actual processing
    with patch("quality_engineering_agentic_framework.agents.requirement_interpreter.load_documents") as mock_load, \
         patch("quality_engineering_agentic_framework.agents.requirement_interpreter.split_documents") as mock_split, \
         patch("quality_engineering_agentic_framework.agents.requirement_interpreter.create_vector_db") as mock_db, \
         patch("quality_engineering_agentic_framework.agents.requirement_interpreter.synthesize_requirements") as mock_synth:
        
        # Setup mocks
        mock_load.return_value = []
        mock_split.return_value = []
        mock_db.return_value = MagicMock()
        mock_synth.return_value = "This is a test synthesized requirement containing product knowledge."
        
        # 2. Initialize Agent
        llm = MockLLM()
        agent = TestCaseGenerationAgent(llm, config={"output_format": "gherkin"})
        
        requirement_text = "The user should be able to login with email."
        
        print("\nRunning agent process...")
        result = await agent.process(requirement_text)
        print("\nAgent finished.")
        print(f"Result Count: {len(result)}")
        
        # 3. Verify API Key Passing
        mock_db.assert_called_with([], openai_api_key="test_api_key_123")
        mock_synth.assert_called_with(mock_db.return_value, openai_api_key="test_api_key_123")
        print("[VERIFIED]: API Key was passed to RAG system functions.")

if __name__ == "__main__":
    asyncio.run(test_integration())
