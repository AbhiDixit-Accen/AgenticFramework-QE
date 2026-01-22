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


EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o-mini"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
TOP_K = 20          # higher → more complete requirement coverage
REBUILD_DB = True   # MUST BE TRUE to pick up changes in overview.md


# -----------------------------
# STEP 1: LOAD REQUIREMENTS
# -----------------------------
def load_documents():
    documents = []

    for file in os.listdir(DATA_PATH):
        file_path = os.path.join(DATA_PATH, file)

        if file.endswith((".txt", ".md")):
            documents.extend(
                TextLoader(file_path).load()
            )

        elif file.endswith(".pdf"):
            documents.extend(
                PyPDFLoader(file_path).load()
            )

        elif file.endswith(".docx"):
            documents.extend(
                Docx2txtLoader(file_path).load()
            )

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
def synthesize_requirements(db, openai_api_key=None):
    """
    Produces a structured, reusable knowledge context
    from retrieved requirement chunks.
    """

    if openai_api_key:
        llm = ChatOpenAI(
            model=LLM_MODEL,
            temperature=0,
            api_key=openai_api_key
        )
    else:
        llm = ChatOpenAI(
            model=LLM_MODEL,
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

