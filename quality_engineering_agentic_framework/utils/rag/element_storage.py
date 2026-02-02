"""
ELEMENT STORAGE SYSTEM - SEPARATE FROM RAG
------------------------------------------

This module handles storage and retrieval of captured web elements in a dedicated vector database.
COMPLETELY ISOLATED from the requirements RAG system.

Use Case: Store browser-captured elements for intelligent test script generation
"""

import os
import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime

from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

from quality_engineering_agentic_framework.utils.logger import get_logger

logger = get_logger(__name__)

# ============================================
# CONFIGURATION - SEPARATE FROM RAG
# ============================================

# Get directory containing this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# CRITICAL: Use separate directory from requirements RAG
ELEMENTS_DB_PATH = os.path.join(BASE_DIR, "elements_vectordb")
ELEMENTS_CACHE_PATH = os.path.join(BASE_DIR, "elements_cache.json")

# Use same embedding model for consistency
EMBEDDING_MODEL = "text-embedding-3-large"


class ElementStorage:
    """
    Manages storage and retrieval of captured web elements in a vector database.
    Completely separate from the requirements RAG system.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize element storage with separate vector DB.
        
        Args:
            api_key: Optional OpenAI API key. If not provided, uses environment variable.
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.embeddings = None
        self.vectorstore = None
        self._initialize_vectorstore()
    
    def _initialize_vectorstore(self):
        """Initialize or load the elements vector database."""
        try:
            if not self.api_key:
                logger.warning("No OpenAI API key found. Element storage will be session-only.")
                return
            
            self.embeddings = OpenAIEmbeddings(
                model=EMBEDDING_MODEL,
                openai_api_key=self.api_key
            )
            
            # Create or load the elements vector database
            if os.path.exists(ELEMENTS_DB_PATH):
                logger.info(f"Loading existing elements vector DB from {ELEMENTS_DB_PATH}")
                self.vectorstore = Chroma(
                    persist_directory=ELEMENTS_DB_PATH,
                    embedding_function=self.embeddings
                )
            else:
                logger.info(f"Creating new elements vector DB at {ELEMENTS_DB_PATH}")
                os.makedirs(ELEMENTS_DB_PATH, exist_ok=True)
                # Create with empty documents initially
                self.vectorstore = Chroma(
                    persist_directory=ELEMENTS_DB_PATH,
                    embedding_function=self.embeddings
                )
            
            logger.info("Element storage initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing element storage: {str(e)}")
            self.vectorstore = None
    
    def store_element(
        self,
        element_data: Dict[str, Any],
        selectors: List[Dict[str, Any]],
        session_id: str,
        page_url: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a captured element with its selectors in the vector database.
        
        Args:
            element_data: Element metadata (tag, id, classes, attributes, etc.)
            selectors: Generated selectors for different frameworks
            session_id: Inspection session ID
            page_url: URL of the page where element was captured
            metadata: Additional metadata (e.g., test_case_id, feature_name)
            
        Returns:
            Element ID
        """
        if not self.vectorstore:
            logger.warning("Element storage not initialized. Element not persisted.")
            return self._generate_element_id(element_data)
        
        try:
            # Create searchable text representation of the element
            element_description = self._create_element_description(element_data)
            
            # Generate unique ID
            element_id = self._generate_element_id(element_data)
            
            # Prepare metadata for storage
            storage_metadata = {
                "element_id": element_id,
                "session_id": session_id,
                "page_url": page_url,
                "tagName": element_data.get("tagName", ""),
                "element_id_attr": element_data.get("id", ""),
                "classList": json.dumps(element_data.get("classList", [])),
                "innerText": element_data.get("innerText", "")[:200],  # Truncate
                "timestamp": datetime.now().isoformat(),
                "selectors": json.dumps(selectors),
                "attributes": json.dumps(element_data.get("attributes", {})),
                "ariaInfo": json.dumps(element_data.get("ariaInfo", {}))
            }
            
            # Add custom metadata if provided
            if metadata:
                storage_metadata.update(metadata)
            
            # Create document for vector storage
            document = Document(
                page_content=element_description,
                metadata=storage_metadata
            )
            
            # Add to vector store
            self.vectorstore.add_documents([document])
            
            logger.info(f"Stored element {element_id} in vector DB")
            
            return element_id
            
        except Exception as e:
            logger.error(f"Error storing element: {str(e)}")
            return self._generate_element_id(element_data)
    
    def query_similar_elements(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query for similar elements based on semantic similarity.
        
        Args:
            query: Natural language query (e.g., "blue submit button")
            top_k: Number of results to return
            filter_metadata: Optional metadata filters (e.g., {"page_url": "..."})
            
        Returns:
            List of matching elements with their selectors
        """
        if not self.vectorstore:
            logger.warning("Element storage not initialized. Returning empty results.")
            return []
        
        try:
            # Search vector database
            results = self.vectorstore.similarity_search(
                query,
                k=top_k,
                filter=filter_metadata
            )
            
            # Format results
            elements = []
            for doc in results:
                element = {
                    "element_id": doc.metadata.get("element_id"),
                    "description": doc.page_content,
                    "tagName": doc.metadata.get("tagName"),
                    "page_url": doc.metadata.get("page_url"),
                    "selectors": json.loads(doc.metadata.get("selectors", "[]")),
                    "attributes": json.loads(doc.metadata.get("attributes", "{}")),
                    "innerText": doc.metadata.get("innerText"),
                    "timestamp": doc.metadata.get("timestamp")
                }
                elements.append(element)
            
            logger.info(f"Found {len(elements)} similar elements for query: {query}")
            return elements
            
        except Exception as e:
            logger.error(f"Error querying elements: {str(e)}")
            return []
    
    def get_session_elements(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all elements from a specific inspection session.
        
        Args:
            session_id: Inspection session ID
            
        Returns:
            List of all elements from the session
        """
        return self.query_similar_elements(
            query="*",  # Match all
            top_k=1000,  # Large number to get all
            filter_metadata={"session_id": session_id}
        )
    
    def get_elements_by_page(self, page_url: str, top_k: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve all elements captured from a specific page URL.
        
        Args:
            page_url: Page URL
            top_k: Maximum number of elements to return
            
        Returns:
            List of elements from the page
        """
        return self.query_similar_elements(
            query="*",
            top_k=top_k,
            filter_metadata={"page_url": page_url}
        )
    
    def find_element_by_description(
        self,
        description: str,
        framework: str = "playwright",
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find elements matching a natural language description and return framework-specific selectors.
        
        Args:
            description: Natural language description (e.g., "login button", "email input field")
            framework: Framework to get selectors for (playwright, selenium, cypress)
            top_k: Number of matches to return
            
        Returns:
            List of matching elements with framework-specific selectors
        """
        elements = self.query_similar_elements(description, top_k)
        
        # Filter selectors for requested framework
        for element in elements:
            framework_selectors = [
                s for s in element.get("selectors", [])
                if s.get("framework") == framework.lower()
            ]
            element["framework_selectors"] = framework_selectors
        
        return elements
    
    def _create_element_description(self, element_data: Dict[str, Any]) -> str:
        """
        Create a searchable text description of the element for vector embedding.
        
        Args:
            element_data: Element metadata
            
        Returns:
            Text description
        """
        parts = []
        
        # Tag name
        tag = element_data.get("tagName", "")
        if tag:
            parts.append(f"Element: {tag}")
        
        # ID
        elem_id = element_data.get("id", "")
        if elem_id:
            parts.append(f"ID: {elem_id}")
        
        # Classes
        classes = element_data.get("classList", [])
        if classes:
            parts.append(f"Classes: {' '.join(classes)}")
        
        # Attributes
        attributes = element_data.get("attributes", {})
        
        # Test attributes (high priority)
        for test_attr in ["data-testid", "data-test", "data-cy"]:
            if test_attr in attributes:
                parts.append(f"{test_attr}: {attributes[test_attr]}")
        
        # ARIA information
        aria_info = element_data.get("ariaInfo", {})
        if aria_info:
            role = aria_info.get("role")
            label = aria_info.get("label")
            if role:
                parts.append(f"Role: {role}")
            if label:
                parts.append(f"ARIA Label: {label}")
        
        # Name attribute
        if "name" in attributes:
            parts.append(f"Name: {attributes['name']}")
        
        # Placeholder
        if "placeholder" in attributes:
            parts.append(f"Placeholder: {attributes['placeholder']}")
        
        # Type (for inputs)
        if "type" in attributes:
            parts.append(f"Type: {attributes['type']}")
        
        # Inner text
        inner_text = element_data.get("innerText", "").strip()
        if inner_text and len(inner_text) < 100:
            parts.append(f"Text: {inner_text}")
        
        # Value
        value = element_data.get("value", "")
        if value:
            parts.append(f"Value: {value}")
        
        return " | ".join(parts)
    
    def _generate_element_id(self, element_data: Dict[str, Any]) -> str:
        """Generate unique ID for an element based on its attributes."""
        identifier = f"{element_data.get('tagName', '')}_{element_data.get('id', '')}_{element_data.get('xpath', '')}"
        return hashlib.md5(identifier.encode()).hexdigest()[:12]
    
    def clear_session(self, session_id: str) -> int:
        """
        Clear all elements from a specific session.
        
        Args:
            session_id: Session ID to clear
            
        Returns:
            Number of elements deleted
        """
        if not self.vectorstore:
            return 0
        
        try:
            # Note: Chroma doesn't support direct deletion by metadata filter
            # This is a limitation - would need to fetch IDs first, then delete
            logger.warning("Session clearing not fully supported by Chroma. Consider recreating DB.")
            return 0
        except Exception as e:
            logger.error(f"Error clearing session: {str(e)}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored elements.
        
        Returns:
            Dictionary with stats
        """
        if not self.vectorstore:
            return {"status": "not_initialized", "count": 0}
        
        try:
            # Get collection stats
            collection = self.vectorstore._collection
            count = collection.count()
            
            return {
                "status": "active",
                "total_elements": count,
                "db_path": ELEMENTS_DB_PATH
            }
        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
            return {"status": "error", "error": str(e)}


# ============================================
# CONVENIENCE FUNCTIONS
# ============================================

_storage_instance = None

def get_element_storage(api_key: Optional[str] = None) -> ElementStorage:
    """
    Get or create the global element storage instance.
    
    Args:
        api_key: Optional OpenAI API key
        
    Returns:
        ElementStorage instance
    """
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = ElementStorage(api_key)
    return _storage_instance


def store_captured_element(
    element_data: Dict[str, Any],
    selectors: List[Dict[str, Any]],
    session_id: str,
    page_url: str,
    api_key: Optional[str] = None
) -> str:
    """
    Convenience function to store a captured element.
    
    Args:
        element_data: Element metadata
        selectors: Generated selectors
        session_id: Session ID
        page_url: Page URL
        api_key: Optional API key
        
    Returns:
        Element ID
    """
    storage = get_element_storage(api_key)
    return storage.store_element(element_data, selectors, session_id, page_url)


def find_elements_for_test_generation(
    element_descriptions: List[str],
    framework: str = "playwright",
    api_key: Optional[str] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Find elements for test script generation based on descriptions.
    
    Args:
        element_descriptions: List of element descriptions from test cases
            e.g., ["login button", "email input", "submit button"]
        framework: Target framework (playwright, selenium, cypress)
        api_key: Optional API key
        
    Returns:
        Dictionary mapping descriptions to matching elements with selectors
    """
    storage = get_element_storage(api_key)
    
    results = {}
    for description in element_descriptions:
        matches = storage.find_element_by_description(
            description,
            framework=framework,
            top_k=3
        )
        results[description] = matches
    
    return results
