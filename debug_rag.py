import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath("."))

from quality_engineering_agentic_framework.utils.rag.rag_system import DATA_PATH, load_documents

print(f"DEBUG: DATA_PATH is {DATA_PATH}")
print(f"DEBUG: DATA_PATH exists: {os.path.exists(DATA_PATH)}")
if os.path.exists(DATA_PATH):
    print(f"DEBUG: Contents of DATA_PATH: {os.listdir(DATA_PATH)}")

# Test loading with specific filenames
selected = ["EngagePortalFunctionalRequirem.txt", "Visual.docx"]
docs = load_documents(file_list=selected)
print(f"DEBUG: Loaded {len(docs)} documents for {selected}")

# Test loading all
docs_all = load_documents()
print(f"DEBUG: Loaded {len(docs_all)} documents when loading all")
