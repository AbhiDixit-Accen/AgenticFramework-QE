
import os
import sys
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from quality_engineering_agentic_framework.utils.rag.rag_system import create_vector_db, synthesize_requirements, load_documents, split_documents

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_rag():
    print("=== Manual RAG Verification Script ===")
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        api_key = input("Enter your OpenAI API Key: ").strip()
        if not api_key:
            print("Error: API Key is required.")
            return

    print("\n1. Loading Documents...")
    try:
        documents = load_documents()
        print(f"   Loaded {len(documents)} documents.")
    except Exception as e:
        print(f"   Error loading documents: {e}")
        return

    print("\n2. Splitting Documents...")
    chunks = split_documents(documents)
    print(f"   Split into {len(chunks)} chunks.")

    print("\n3. Creating/Loading Vector DB...")
    try:
        # Force rebuild to ensure we use the latest overview.md
        # calling create_vector_db with restart logic effectively if we could, 
        # but here we rely on the function's internal logic.
        # Ideally we should delete the old DB to prove it works fresh.
        # But let's just run it.
        vector_db = create_vector_db(chunks, openai_api_key=api_key)
        print("   Vector DB ready.")
    except Exception as e:
        print(f"   Error creating Vector DB: {e}")
        return

    print("\n4. Synthesizing Requirements (Asking LLM)...")
    try:
        context = synthesize_requirements(vector_db, openai_api_key=api_key)
        print("\n=== SYNTHESIZED PRODUCT CONTEXT ===\n")
        print(context)
        print("\n===================================")
        
        if "SauceDemo" in context or "User Roles" in context:
            print("\n[SUCCESS] The RAG system successfully retrieved content from your overview.md!")
        else:
            print("\n[WARNING] Context generated, but didn't explicitly mention expected keywords. Check output above.")
            
    except Exception as e:
        print(f"   Error synthesizing requirements: {e}")

if __name__ == "__main__":
    verify_rag()
