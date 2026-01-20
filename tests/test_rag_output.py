"""
Quick test to verify RAG integration is working.
This bypasses the UI and directly tests the agent.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from quality_engineering_agentic_framework.agents.requirement_interpreter import TestCaseGenerationAgent
from quality_engineering_agentic_framework.llm.openai_llm import OpenAILLM

def test_rag_integration():
    """Test that RAG context is being used in test case generation."""
    
    # Get API key from environment
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        api_key = input("Enter your OpenAI API key: ")
    
    # Create LLM
    llm_config = {
        "provider": "openai",
        "model": "gpt-3.5-turbo",
        "api_key": api_key,
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    llm = OpenAILLM(llm_config)
    
    # Create agent
    agent_config = {}
    agent = TestCaseGenerationAgent(llm, agent_config)
    
    # Test with a simple requirement
    requirement = "Test the login functionality"
    
    print("\n" + "="*60)
    print("TESTING RAG INTEGRATION")
    print("="*60)
    print(f"\nRequirement: {requirement}")
    print("\nGenerating test cases...\n")
    
    # Generate test cases
    import asyncio
    test_cases = asyncio.run(agent.process(requirement))
    
    print("\n" + "="*60)
    print("GENERATED TEST CASES")
    print("="*60)
    
    # Display test cases
    for i, tc in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i} ---")
        print(f"Title: {tc.get('title', 'N/A')}")
        print(f"Description: {tc.get('description', 'N/A')}")
        if tc.get('preconditions'):
            print(f"Preconditions: {tc['preconditions']}")
        if tc.get('actions'):
            print(f"Actions: {tc['actions']}")
        if tc.get('test_data'):
            print(f"Test Data: {tc['test_data']}")
    
    # Check for RAG-specific keywords
    print("\n" + "="*60)
    print("RAG VERIFICATION")
    print("="*60)
    
    rag_keywords = [
        "prabhakaranSankar",
        "SauceDemo", 
        "saucedemo.com",
        "product catalog",
        "shopping cart"
    ]
    
    # Convert test cases to string for searching
    test_cases_str = str(test_cases).lower()
    
    found_keywords = []
    for keyword in rag_keywords:
        if keyword.lower() in test_cases_str:
            found_keywords.append(keyword)
    
    if found_keywords:
        print(f"\n✅ RAG IS WORKING!")
        print(f"Found RAG-specific keywords: {', '.join(found_keywords)}")
    else:
        print(f"\n❌ RAG NOT DETECTED")
        print(f"No product-specific keywords found in output.")
        print(f"Expected to find: {', '.join(rag_keywords)}")
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    test_rag_integration()
