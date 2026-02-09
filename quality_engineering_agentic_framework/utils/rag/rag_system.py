"""
LOCAL RAG SYSTEM FOR REQUIREMENT SYNTHESIS (OPENAI VERSION)
----------------------------------------------------------

This script:
1. Ingests requirement documents
2. Indexes them using OpenAI embeddings
3. Stores them in a local Chroma vector database
4. Synthesizes ALL requirements into a structured knowledge context
5. Outputs reusable context for downstream prompts
"""

import os
from langchain_community.document_loaders import TextLoader, PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import PromptTemplate


# -----------------------------
# CONFIGURATION
# -----------------------------


# Get directory containing this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "requirements")
DB_PATH = os.path.join(BASE_DIR, "vectordb")


EMBEDDING_MODEL = "text-embedding-3-large"
LLM_MODEL = "gpt-4o-mini"  # Default model, can be overridden by frontend

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
TOP_K = 20          # higher → more complete requirement coverage
CACHE_PATH = os.path.join(BASE_DIR, "fingerprint_cache.json")


# -----------------------------
# STEP 0: SMART CACHING
# -----------------------------
def get_selection_fingerprint(file_list=None):
    """
    Creates a unique hash based on the filenames and their 
    last modification times to detect changes.
    """
    import hashlib
    import json
    
    if file_list is None:
        file_list = [f for f in os.listdir(DATA_PATH) if os.path.isfile(os.path.join(DATA_PATH, f))]
    
    # Sort for consistency
    file_list.sort()
    
    state = {}
    for f in file_list:
        p = os.path.join(DATA_PATH, f)
        if os.path.exists(p):
            state[f] = os.path.getmtime(p)
            
    # Serialize and hash the state
    state_str = json.dumps(state, sort_keys=True)
    return hashlib.md5(state_str.encode()).hexdigest()


# -----------------------------
# STEP 1: LOAD REQUIREMENTS
# -----------------------------
def load_documents(file_list=None):
    """
    Load documents from the data directory.
    
    Args:
        file_list: Optional list of specific filenames to load. If None, loads all files.
    
    Returns:
        List of loaded documents
    """
    documents = []

    # Get list of files to process
    if file_list is not None:
        files_to_load = [f for f in file_list if os.path.isfile(os.path.join(DATA_PATH, f))]
        print(f"[RAG] Loading {len(files_to_load)} selected documents: {files_to_load}")
    else:
        files_to_load = [f for f in os.listdir(DATA_PATH) if os.path.isfile(os.path.join(DATA_PATH, f))]
        print(f"[RAG] Loading all {len(files_to_load)} documents from {DATA_PATH}")

    for file in files_to_load:
        file_path = os.path.join(DATA_PATH, file)
        
        # Extract metadata
        file_stat = os.stat(file_path)
        metadata = {
            "source": file,
            "file_type": file.split('.')[-1] if '.' in file else "unknown",
            "modified_time": file_stat.st_mtime,
            "layer": "raw_chunk" # Default layer
        }

        try:
            loaded_docs = []
            if file.endswith((".txt", ".md")):
                try:
                    loaded_docs = TextLoader(file_path, encoding="utf-8").load()
                except Exception:
                    loaded_docs = TextLoader(file_path, encoding="cp1252", errors="ignore").load()

            elif file.endswith(".pdf"):
                try:
                    loaded_docs = PyPDFLoader(file_path).load()
                except ImportError as e:
                    print(f"[RAG] Warning: Skipping PDF file {file} - pypdf not available: {e}")
                    continue

            elif file.endswith(".docx"):
                loaded_docs = Docx2txtLoader(file_path).load()
            
            # Inject metadata into each page/segment of the loaded document
            for d in loaded_docs:
                d.metadata.update(metadata)
            
            documents.extend(loaded_docs)
            
        except Exception as e:
            print(f"[RAG] Warning: Failed to load {file}: {e}")
            continue

    print(f"Loaded {len(documents)} document segments with metadata")
    return documents


# -----------------------------
# STEP 2: SUMMARIZE DOCUMENTS (LAYERED INDEXING)
# -----------------------------
def summarize_document(doc_content, source_name, openai_api_key=None, model=None):
    """
    Generates a high-level summary of a single document and 
    classifies it as 'spec' or 'narrative'.
    """
    llm_model = model if model else LLM_MODEL
    if openai_api_key:
        llm = ChatOpenAI(model=llm_model, temperature=0, api_key=openai_api_key)
    else:
        llm = ChatOpenAI(model=llm_model, temperature=0)

    prompt = PromptTemplate(
        template="""
        Analyze the following requirement document and:
        1. Classify it as either 'Authoritative Spec' (if it contains technical details, API endpoints, error codes, or exact business rules) or 'Narrative' (if it is a high-level overview, user story description, or general context).
        2. Generate a concise but comprehensive summary.
        
        Document Content Start:
        {content}
        Document Content End
        
        Provide the output in the following format:
        TYPE: [Authoritative Spec / Narrative]
        SUMMARY: [Your summary here]
        """,
        input_variables=["content"],
    )

    # Truncate content if too long
    truncated_content = doc_content[:15000]
    response = llm.invoke(prompt.format(content=truncated_content))
    
    # Simple parser for the structured response
    resp_text = response.content
    doc_type = "narrative"
    if "TYPE: Authoritative Spec" in resp_text:
        doc_type = "spec"
    
    summary = resp_text.split("SUMMARY:")[-1].strip() if "SUMMARY:" in resp_text else resp_text
    
    return summary, doc_type


# -----------------------------
# STEP 3: SPLIT INTO CHUNKS
# -----------------------------
def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )

    chunks = splitter.split_documents(documents)
    print(f"Split into {len(chunks)} chunks")
    return chunks


# -----------------------------
# STEP 3: CREATE / LOAD VECTOR DB
# -----------------------------
def create_vector_db(chunks, openai_api_key=None, fingerprint=None):
    import traceback
    import shutil
    import time
    from datetime import datetime

    try:
        if openai_api_key:
            embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, openai_api_key=openai_api_key)
        else:
            embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

        # Check if we can reuse the database
        reuse_db = False
        stored_db_path = None
        if os.path.exists(CACHE_PATH):
            try:
                import json
                with open(CACHE_PATH, 'r') as f:
                    cached_data = json.load(f)
                    cached_fp = cached_data.get("fingerprint")
                    if cached_fp == fingerprint:
                        stored_db_path = cached_data.get("db_path")
                        if stored_db_path and os.path.exists(stored_db_path):
                            reuse_db = True
                            print(f"[RAG] SUCCESS: Fingerprint {fingerprint} matches. Reusing existing DB at {stored_db_path}")
            except Exception as e:
                print(f"[RAG] CACHE READ ERROR: {e}. Rebuilding...")

        if reuse_db and stored_db_path:
            try:
                db = Chroma(
                    persist_directory=stored_db_path,
                    embedding_function=embeddings
                )
                # VALIDATION: Check if DB is actually usable and not empty
                db_data = db.get()
                if not db_data or not db_data.get('ids'):
                    print(f"[RAG] WARNING: Cached DB at {stored_db_path} is EMPTY. Forcing rebuild.")
                    reuse_db = False
                else:
                    print(f"[RAG] SUCCESS: Verified cached DB at {stored_db_path} contains {len(db_data['ids'])} segments.")
                    return db
            except Exception as e:
                print(f"[RAG] FAILED to load/validate cached DB at {stored_db_path}: {e}. Falling back to rebuild.")
                # CRITICAL: If chunks is None, we CANNOT rebuild. We must raise so the agent re-ingests.
                if chunks is None:
                    raise ValueError(f"Cache load failed and no chunks provided for re-indexing: {e}")

        # REBUILD PATH: Always use a unique folder to avoid locks/conflicts
        if chunks is None:
             raise ValueError("create_vector_db called with chunks=None but no matching cache found.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_db_path = os.path.join(BASE_DIR, f"vectordb_{timestamp}")
        
        print(f"[RAG] Rebuilding: Creating fresh database at {new_db_path}")
        
        try:
            os.makedirs(new_db_path, exist_ok=True)
            print(f"[RAG] Starting indexing: Creating DB at {new_db_path}")
            
            chunk_count = len(chunks) if chunks else 0
            print(f"[RAG] Indexing {chunk_count} chunks/summaries")
            
            if chunk_count == 0:
                print("[RAG] ERROR: No chunks provided for indexing!")
                # Create an empty DB anyway to avoid returning None, but this is a fail state
                db = Chroma(persist_directory=new_db_path, embedding_function=embeddings)
            else:
                db = Chroma.from_documents(
                    documents=chunks,
                    embedding=embeddings,
                    persist_directory=new_db_path
                )
            
            # Ensure persistence
            try:
                db.persist()
                print(f"[RAG] Database persisted to {new_db_path}")
            except AttributeError:
                pass
            
            # Save the new fingerprint and THE PATH we ended up using
            if fingerprint:
                try:
                    import json
                    with open(CACHE_PATH, 'w') as f:
                        json.dump({
                            "fingerprint": fingerprint,
                            "db_path": new_db_path
                        }, f)
                    print(f"[RAG] SUCCESS: Saved cache link: {fingerprint} -> {new_db_path}")
                except Exception as e:
                    print(f"Warning: Failed to save fingerprint to {CACHE_PATH}: {e}")

            # CLEANUP: Try to remove old vectordb folders that are no longer referenced
            try:
                current_abs = os.path.abspath(new_db_path)
                for item in os.listdir(BASE_DIR):
                    item_path = os.path.join(BASE_DIR, item)
                    if os.path.isdir(item_path) and (item.startswith("vectordb_") or item == "vectordb"):
                        if os.path.abspath(item_path) != current_abs:
                            try:
                                shutil.rmtree(item_path)
                                print(f"[RAG Cleanup] Removed old index: {item}")
                            except:
                                pass # Keep silent on locks during cleanup
            except Exception as cleanup_e:
                print(f"Warning: Cleanup failed: {cleanup_e}")

            return db
            
        except Exception as e:
            print(f"[RAG] CRITICAL ERROR during DB creation at {new_db_path}: {e}")
            traceback.print_exc()
            raise e

    except Exception as top_e:
        print(f"[RAG] TOP-LEVEL create_vector_db ERROR: {top_e}")
        traceback.print_exc()
        raise top_e


# -----------------------------
# STEP 4: SYNTHESIZE REQUIREMENTS
# -----------------------------
def synthesize_requirements(db, openai_api_key=None, model=None):
    """
    Produces a structured, reusable knowledge context
    from retrieved requirement chunks.
    """
    
    # Use provided model or fall back to default
    llm_model = model if model else LLM_MODEL

    if openai_api_key:
        llm = ChatOpenAI(
            model=llm_model,
            temperature=0,
            api_key=openai_api_key
        )
    else:
        llm = ChatOpenAI(
            model=llm_model,
            temperature=0
        )

    # For synthesis, we want the FULL context from all indexed documents.
    all_docs = db.get()
    context = "\n\n".join(all_docs['documents'])

    prompt = PromptTemplate(
        template="""
You are a senior requirements analyst.

Using the retrieved context below, synthesize a comprehensive, structured representation of the system requirements.

CRITICAL INSTRUCTIONS:
- IDENTIFY ALL MODULES: If the context covers multiple areas (e.g., UI Overview and Technical API), ensure BOTH are represented.
- PRESERVE SPECIFICS: Do not omit specific names, error messages, usernames, endpoint URLs, or header names.
- NO HALLUCINATION: Use only the provided context. If a detail is missing, do not invent it.
- STRUCTURED OUTPUT: Use the following format:

SYSTEM IDENTITIES & OVERVIEW
(List product names and high-level purpose)

FUNCTIONAL REQUIREMENTS
(Grouped by feature or component. Include specific business logic.)

TECHNICAL SPECIFICATIONS & API DETAILS
(List endpoints, headers, and request/response structures found in the context)

NON-FUNCTIONAL REQUIREMENTS
(Performance, Security, etc.)

CONSTRAINTS & ASSUMPTIONS

Context:
{context}

Comprehensive Requirements Synthesis:
""",
        input_variables=["context"],
    )

    response = llm.invoke(prompt.format(context=context))

    return response.content


def generate_multi_queries(query: str, openai_api_key=None, model=None):
    """
    Generates multiple variations of the user's query to improve retrieval coverage.
    """
    llm_model = model if model else LLM_MODEL
    
    if openai_api_key:
        llm = ChatOpenAI(model=llm_model, temperature=0, api_key=openai_api_key)
    else:
        llm = ChatOpenAI(model=llm_model, temperature=0)

    prompt = PromptTemplate(
        template="""
        You are an AI language model assistant. Your task is to generate five 
        different versions of the given user query to retrieve relevant documents from a vector 
        database. By generating multiple perspectives on the user query, your goal is to help
        the user overcome some of the limitations of the distance-based similarity search. 
        
        Provide these alternative queries separated by newlines.
        Original query: {query}
        """,
        input_variables=["query"],
    )

    response = llm.invoke(prompt.format(query=query))
    # Split by newlines and filter out empty lines or numbers
    queries = [q.strip() for q in response.content.split("\n") if q.strip()]
    # Ensure at least the original query is included
    if query not in queries:
        queries.append(query)
    
    print(f"[RAG] Generated {len(queries)} query variations for broader search")
    return queries


def synthesize_requirements_for_query(db, query: str, openai_api_key=None, model=None, top_k=10):
    """
    Retrieves and synthesizes requirements relevant to a specific user query.
    Uses semantic search to find the most relevant chunks.
    """
    import traceback
    try:
        # Use provided model or fall back to default
        llm_model = model if model else LLM_MODEL

        if openai_api_key:
            llm = ChatOpenAI(
                model=llm_model,
                temperature=0,
                api_key=openai_api_key
            )
        else:
            llm = ChatOpenAI(
                model=llm_model,
                temperature=0
            )

        # Multi-Query Retrieval Logic
        print(f"[RAG] Expanding query: \"{query}\"")
        multi_queries = generate_multi_queries(query, openai_api_key=openai_api_key, model=llm_model)
        
        all_relevant_docs = []
        seen_ids = set()
        
        total_retrieved = 0
        for q in multi_queries:
            # Perform semantic search for each query variation
            try:
                docs = db.similarity_search(q, k=5)  # Get top 5 per variation
                total_retrieved += len(docs)
                for doc in docs:
                    # Deduplicate by content hash
                    content_hash = hash(doc.page_content)
                    if content_hash not in seen_ids:
                        all_relevant_docs.append(doc)
                        seen_ids.add(content_hash)
            except Exception as search_e:
                print(f"[RAG] Search error for variation \"{q}\": {search_e}")
                traceback.print_exc()
        
        print(f"[RAG] Total retrieved chunks: {total_retrieved}. Unique relevant chunks: {len(all_relevant_docs)}")

        # Sort or limit to top_k if needed, but here we take the aggregated set
        relevant_docs = all_relevant_docs[:top_k]
        
        if not relevant_docs:
            print("[RAG] WARNING: No relevant documentation found in the vector database.")
            # DIAGNOSTIC: Check if DB is actually empty
            db_size = 0
            try:
                all_data = db.get()
                db_size = len(all_data.get('ids', []))
            except:
                pass
                
            return f"No relevant documentation found for your query. (Retrieved 0 matches from {db_size} indexed segments in the Knowledge Hub)"
        
        # Combine the relevant chunks
        context = "\n\n".join([doc.page_content for doc in relevant_docs])

        prompt = PromptTemplate(
            template="""
You are a senior requirements analyst.

The user wants to test: "{query}"

Using the retrieved context below, synthesize a comprehensive representation of ALL requirements and information related to this topic.

CRITICAL INSTRUCTIONS:
- COMPREHENSIVE COVERAGE: Include ALL information related to the user's input, even tangentially related details.
- PRESERVE SPECIFICS: Do not omit specific names, error messages, usernames, endpoint URLs, or header names.
- NO HALLUCINATION: Use only the provided context. If a detail is missing, do not invent it.
- STRUCTURED OUTPUT: Organize the information clearly with appropriate headings.
- SUPPORT TEST CREATION: Include all details that would help create thorough test cases.
- MACHINE READABLE TRACE: At the very end of your response, provide a JSON block enclosed in ```json ... ``` that maps each requirement to its source document and specifies if it is an 'Authoritative Spec' or 'Narrative'.

Retrieved Context:
{context}

Comprehensive Requirements Related to "{query}":
""",
            input_variables=["query", "context"],
        )

        response = llm.invoke(prompt.format(query=query, context=context))
        return response.content

    except Exception as e:
        print(f"[RAG] Critical error in synthesize_requirements_for_query: {e}")
        traceback.print_exc()
        return f"Error retrieving relevant context: {e}"


# -----------------------------
# MAIN PIPELINE
# -----------------------------
if __name__ == "__main__":
    documents = load_documents()
    chunks = split_documents(documents)
    vector_db = create_vector_db(chunks)

    structured_requirements = synthesize_requirements(vector_db)

    print("\n===== SYNTHESIZED REQUIREMENTS CONTEXT =====\n")
    print(structured_requirements)

