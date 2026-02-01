import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath("."))

from quality_engineering_agentic_framework.utils.rag.rag_system import (
    load_documents, split_documents, create_vector_db, 
    synthesize_requirements_for_query
)

# Ensure API Key is set for expansion
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("WARNING: OPENAI_API_KEY not found in environment. Test might fail.")

# Load and Index
selected = ["EngagePortalFunctionalRequirem.txt", "Visual.docx"]
docs = load_documents(file_list=selected)
chunks = split_documents(docs)
db = create_vector_db(chunks, openai_api_key=api_key)

# Test Synthesis with expansion
query = "user login and authentication"
print(f"\n[TEST] Querying for: \"{query}\"")
result = synthesize_requirements_for_query(db, query, openai_api_key=api_key)

print("\n===== SYNTHESIZED RESULT =====\n")
print(result)
