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
REBUILD_DB = True   # MUST BE TRUE to pick up changes in overview.md


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
    if file_list:
        files_to_load = [f for f in file_list if os.path.isfile(os.path.join(DATA_PATH, f))]
        print(f"[RAG] Loading {len(files_to_load)} selected documents: {files_to_load}")
    else:
        files_to_load = [f for f in os.listdir(DATA_PATH) if os.path.isfile(os.path.join(DATA_PATH, f))]
        print(f"[RAG] Loading all {len(files_to_load)} documents from {DATA_PATH}")

    for file in files_to_load:
        file_path = os.path.join(DATA_PATH, file)

        try:
            if file.endswith((".txt", ".md")):
                documents.extend(
                    TextLoader(file_path).load()
                )

            elif file.endswith(".pdf"):
                try:
                    documents.extend(
                        PyPDFLoader(file_path).load()
                    )
                except ImportError as e:
                    print(f"[RAG] Warning: Skipping PDF file {file} - pypdf not available: {e}")
                    continue

            elif file.endswith(".docx"):
                documents.extend(
                    Docx2txtLoader(file_path).load()
                )
        except Exception as e:
            print(f"[RAG] Warning: Failed to load {file}: {e}")
            continue

    print(f"Loaded {len(documents)} documents")
    return documents


# -----------------------------
# STEP 2: SPLIT INTO CHUNKS
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
def create_vector_db(chunks, openai_api_key=None):
    if openai_api_key:
        embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, openai_api_key=openai_api_key)
    else:
        embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

    if os.path.exists(DB_PATH) and not REBUILD_DB:
        print("Loading existing vector database...")
        db = Chroma(
            persist_directory=DB_PATH,
            embedding_function=embeddings
        )
    else:
        if REBUILD_DB and os.path.exists(DB_PATH):
            print(f"Clearing existing vector database at {DB_PATH} for strict filtering...")
            import shutil
            try:
                shutil.rmtree(DB_PATH)
            except Exception as e:
                print(f"Warning: Failed to clear database directory: {e}")
                
        print("Creating new vector database...")
        db = Chroma.from_documents(
            chunks,
            embeddings,
            persist_directory=DB_PATH
        )
        db.persist()

    return db


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


def synthesize_requirements_for_query(db, query: str, openai_api_key=None, model=None, top_k=10):
    """
    Retrieves and synthesizes requirements relevant to a specific user query.
    Uses semantic search to find the most relevant chunks.
    
    Args:
        db: Vector database instance
        query: User's requirement query (e.g., "test performance")
        openai_api_key: Optional OpenAI API key
        model: Optional LLM model name
        top_k: Number of relevant chunks to retrieve
    
    Returns:
        Synthesized context relevant to the query
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

    # Perform semantic search to get relevant chunks
    relevant_docs = db.similarity_search(query, k=top_k)
    
    if not relevant_docs:
        return "No relevant documentation found for your query."
    
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

Retrieved Context:
{context}

Comprehensive Requirements Related to "{query}":
""",
        input_variables=["query", "context"],
    )

    response = llm.invoke(prompt.format(query=query, context=context))

    return response.content


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

