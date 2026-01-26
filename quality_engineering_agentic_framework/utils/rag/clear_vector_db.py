"""
Script to delete the vector database and all related cache files.

This script removes:
1. The entire vector database directory
2. Any Chroma-related cache files
3. __pycache__ directories in the RAG module

Usage:
    python tests/clear_vector_db.py
"""

import os
import shutil
import sys

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from quality_engineering_agentic_framework.utils.rag.rag_system import DB_PATH, DATA_PATH


def clear_vector_db():
    """Delete the vector database and all related cache."""
    print("=" * 60)
    print("Vector Database Cleanup Script")
    print("=" * 60)
    
    # 1. Remove vector database directory
    if os.path.exists(DB_PATH):
        print(f"\n[1/3] Removing vector database at: {DB_PATH}")
        try:
            shutil.rmtree(DB_PATH)
            print("✓ Vector database deleted successfully")
        except Exception as e:
            print(f"✗ Failed to delete vector database: {e}")
    else:
        print(f"\n[1/3] Vector database not found at: {DB_PATH}")
        print("✓ Nothing to delete")
    
    # 2. Remove __pycache__ in RAG module
    rag_dir = os.path.dirname(DB_PATH)
    pycache_dir = os.path.join(rag_dir, "__pycache__")
    if os.path.exists(pycache_dir):
        print(f"\n[2/3] Removing Python cache at: {pycache_dir}")
        try:
            shutil.rmtree(pycache_dir)
            print("✓ Python cache deleted successfully")
        except Exception as e:
            print(f"✗ Failed to delete Python cache: {e}")
    else:
        print(f"\n[2/3] Python cache not found")
        print("✓ Nothing to delete")
    
    # 3. Remove any .chroma files or directories in the RAG module
    print(f"\n[3/3] Scanning for Chroma-related files in: {rag_dir}")
    chroma_files_found = False
    for item in os.listdir(rag_dir):
        if ".chroma" in item.lower() or item.startswith("chroma"):
            item_path = os.path.join(rag_dir, item)
            chroma_files_found = True
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
                print(f"✓ Deleted: {item}")
            except Exception as e:
                print(f"✗ Failed to delete {item}: {e}")
    
    if not chroma_files_found:
        print("✓ No Chroma-related files found")
    
    # Summary
    print("\n" + "=" * 60)
    print("Cleanup Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Restart your backend server")
    print("2. Generate test cases - the vector DB will be rebuilt automatically")
    print("=" * 60)


if __name__ == "__main__":
    # Confirm before deletion
    print("\nThis will delete:")
    print(f"  - Vector database: {DB_PATH}")
    print(f"  - Related cache files")
    print("\nRequirement documents will NOT be deleted.")
    
    response = input("\nProceed with deletion? (yes/no): ").strip().lower()
    
    if response in ["yes", "y"]:
        clear_vector_db()
    else:
        print("\nCancelled. No files were deleted.")
