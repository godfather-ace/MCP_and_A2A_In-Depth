"""
Pinecone MCP Server (Python)
Exposes Pinecone vector DB operations as MCP tools + sample prompts,
with OpenAI handling text embeddings automatically.

Tools:
    - list_indexes        : list all Pinecone indexes
    - upsert_texts        : embed texts via OpenAI then upsert into Pinecone
    - upsert_vectors      : upsert raw pre-computed vectors
    - query_by_text       : embed a query text then semantic-search Pinecone
    - query_by_vector     : semantic-search using a raw vector
    - delete_vectors      : delete vectors by ID

Prompts:
    - store_documents     : guided prompt to ingest a list of documents
    - semantic_search     : guided prompt for a natural-language search
    - rag_answer          : retrieve context from Pinecone then answer a question
    - manage_index        : guided prompt for index inspection / cleanup
"""

import json
import os
import sys
from typing import Any
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from openai import OpenAI
from pinecone import Pinecone

load_dotenv()

# ── Validate env vars ────────────────────────────────────────────────────────
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
OPENAI_API_KEY   = os.environ.get("OPENAI_API_KEY")

if not PINECONE_API_KEY:
    print("ERROR: PINECONE_API_KEY environment variable is required", file=sys.stderr)
    sys.exit(1)

if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY environment variable is required", file=sys.stderr)
    sys.exit(1)

# ── Clients ──────────────────────────────────────────────────────────────────
pinecone = Pinecone(api_key=PINECONE_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

EMBED_MODEL = "text-embedding-3-small"   # 1536-dim; change to text-embedding-3-large if needed

# ── MCP server ───────────────────────────────────────────────────────────────
mcp = FastMCP("pinecone-mcp")

# ── Helper: get embeddings from OpenAI ───────────────────────────────────────
def embed_texts(texts: list[str]) -> list[list[float]]:
    """Return a list of embedding vectors for the given texts."""
    response = openai_client.embeddings.create(
        model=EMBED_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


# ════════════════════════════════════════════════════════════════════════════
# Tool: list_indexes
# ════════════════════════════════════════════════════════════════════════════
@mcp.tool()
def list_indexes() -> str:
    """List all Pinecone indexes in your project."""
    result = pinecone.list_indexes()
    indexes = [idx.name for idx in result]
    return json.dumps(indexes, indent=2)


# ════════════════════════════════════════════════════════════════════════════
# Tool: upsert_texts
# ════════════════════════════════════════════════════════════════════════════
@mcp.tool()
def upsert_texts(
    index_name: str,
    records: list[dict[str, Any]],
    namespace: str = "",
) -> str:
    """
    Embed text strings via OpenAI and upsert them into a Pinecone index.

    Each record must have:
        - id       (str)  : unique vector ID
        - text     (str)  : text to embed
        - metadata (dict) : optional extra metadata stored alongside the vector

    Args:
        index_name: Name of the Pinecone index.
        records:    List of records with 'id', 'text', and optional 'metadata'.
        namespace:  Pinecone namespace (default: "").
    """
    if not records:
        return json.dumps({"error": "records list is empty"})

    texts = [r["text"] for r in records]
    embeddings = embed_texts(texts)

    vectors = []
    for record, embedding in zip(records, embeddings):
        meta = record.get("metadata", {})
        meta["text"] = record["text"]          # store original text for retrieval
        vectors.append({
            "id":       record["id"],
            "values":   embedding,
            "metadata": meta,
        })

    index = pinecone.Index(index_name)
    index.upsert(vectors=vectors, namespace=namespace)

    return json.dumps({
        "upserted_count": len(vectors),
        "model_used":     EMBED_MODEL,
        "index":          index_name,
        "namespace":      namespace,
    }, indent=2)


# ════════════════════════════════════════════════════════════════════════════
# Tool: upsert_vectors
# ════════════════════════════════════════════════════════════════════════════
@mcp.tool()
def upsert_vectors(
    index_name: str,
    vectors: list[dict[str, Any]],
    namespace: str = "",
) -> str:
    """
    Upsert pre-computed vectors directly into a Pinecone index (no embedding step).

    Each vector dict must have:
        - id       (str)          : unique vector ID
        - values   (list[float])  : embedding values
        - metadata (dict)         : optional metadata

    Args:
        index_name: Name of the Pinecone index.
        vectors:    List of vector dicts.
        namespace:  Pinecone namespace (default: "").
    """
    if not vectors:
        return json.dumps({"error": "vectors list is empty"})

    index = pinecone.Index(index_name)
    index.upsert(vectors=vectors, namespace=namespace)

    return json.dumps({
        "upserted_count": len(vectors),
        "index":          index_name,
        "namespace":      namespace,
    }, indent=2)


# ════════════════════════════════════════════════════════════════════════════
# Tool: query_by_text
# ════════════════════════════════════════════════════════════════════════════
@mcp.tool()
def query_by_text(
    index_name: str,
    query_text: str,
    top_k: int = 5,
    namespace: str = "",
    include_metadata: bool = True,
    include_values: bool = False,
    filter: dict[str, Any] | None = None,
) -> str:
    """
    Embed a query string via OpenAI and run a semantic search on Pinecone.

    Args:
        index_name:       Name of the Pinecone index.
        query_text:       Natural-language query to embed and search.
        top_k:            Number of nearest neighbours to return (default: 5).
        namespace:        Pinecone namespace (default: "").
        include_metadata: Include metadata in results (default: True).
        include_values:   Include vector values in results (default: False).
        filter:           Pinecone metadata filter dict (optional).
    """
    (query_vector,) = embed_texts([query_text])

    index = pinecone.Index(index_name)
    query_kwargs: dict[str, Any] = {
        "vector":           query_vector,
        "top_k":            top_k,
        "namespace":        namespace,
        "include_metadata": include_metadata,
        "include_values":   include_values,
    }
    if filter:
        query_kwargs["filter"] = filter

    results = index.query(**query_kwargs)

    matches = [
        {
            "id":       m["id"],
            "score":    m["score"],
            "metadata": m.get("metadata", {}),
            **({"values": m["values"]} if include_values else {}),
        }
        for m in results.get("matches", [])
    ]

    return json.dumps({
        "query":       query_text,
        "model_used":  EMBED_MODEL,
        "top_k":       top_k,
        "matches":     matches,
    }, indent=2)


# ════════════════════════════════════════════════════════════════════════════
# Tool: query_by_vector
# ════════════════════════════════════════════════════════════════════════════
@mcp.tool()
def query_by_vector(
    index_name: str,
    vector: list[float],
    top_k: int = 5,
    namespace: str = "",
    include_metadata: bool = True,
    include_values: bool = False,
    filter: dict[str, Any] | None = None,
) -> str:
    """
    Run a nearest-neighbour search on Pinecone using a raw pre-computed vector.

    Args:
        index_name:       Name of the Pinecone index.
        vector:           Query vector (must match index dimension).
        top_k:            Number of results to return (default: 5).
        namespace:        Pinecone namespace (default: "").
        include_metadata: Include metadata in results (default: True).
        include_values:   Include vector values in results (default: False).
        filter:           Pinecone metadata filter dict (optional).
    """
    index = pinecone.Index(index_name)
    query_kwargs: dict[str, Any] = {
        "vector":           vector,
        "top_k":            top_k,
        "namespace":        namespace,
        "include_metadata": include_metadata,
        "include_values":   include_values,
    }
    if filter:
        query_kwargs["filter"] = filter

    results = index.query(**query_kwargs)

    matches = [
        {
            "id":       m["id"],
            "score":    m["score"],
            "metadata": m.get("metadata", {}),
            **({"values": m["values"]} if include_values else {}),
        }
        for m in results.get("matches", [])
    ]

    return json.dumps({"top_k": top_k, "matches": matches}, indent=2)


# ════════════════════════════════════════════════════════════════════════════
# Tool: delete_vectors
# ════════════════════════════════════════════════════════════════════════════
@mcp.tool()
def delete_vectors(
    index_name: str,
    ids: list[str],
    namespace: str = "",
) -> str:
    """
    Delete vectors from a Pinecone index by their IDs.

    Args:
        index_name: Name of the Pinecone index.
        ids:        List of vector IDs to delete.
        namespace:  Pinecone namespace (default: "").
    """
    if not ids:
        return json.dumps({"error": "ids list is empty"})

    index = pinecone.Index(index_name)
    index.delete(ids=ids, namespace=namespace)

    return json.dumps({
        "deleted":    ids,
        "index":      index_name,
        "namespace":  namespace,
    }, indent=2)


# ════════════════════════════════════════════════════════════════════════════
# Prompt: store_documents
# ════════════════════════════════════════════════════════════════════════════
@mcp.prompt()
def store_documents(
    index_name: str,
    documents: str,
    namespace: str = "",
) -> str:
    """
    Guided prompt to embed and store a batch of documents into Pinecone.

    Args:
        index_name: Target Pinecone index name.
        documents:  Newline-separated list of texts to store, each prefixed
                    with an ID, e.g.  "doc-1: The quick brown fox..."
        namespace:  Optional Pinecone namespace (default: "").
    """
    return f"""You are a helpful assistant that stores documents in a Pinecone vector database.

The user wants to store the following documents into the Pinecone index **"{index_name}"**
(namespace: "{namespace or 'default'}"):

---
{documents}
---

Follow these steps:
1. Parse each line as "id: text". If no "id:" prefix is present, auto-generate IDs like "doc-1", "doc-2", ...
2. Call the `upsert_texts` tool with:
    - index_name = "{index_name}"
    - namespace  = "{namespace}"
    - records    = the parsed list of {{ "id": ..., "text": ... }} objects
3. Report back how many documents were successfully stored and confirm their IDs.

Start now."""


# ════════════════════════════════════════════════════════════════════════════
# Prompt: semantic_search
# ════════════════════════════════════════════════════════════════════════════
@mcp.prompt()
def semantic_search(
    index_name: str,
    query: str,
    top_k: int = 5,
    namespace: str = "",
) -> str:
    """
    Guided prompt to run a natural-language semantic search against Pinecone.

    Args:
        index_name: Pinecone index to search.
        query:      The natural-language question or phrase to search for.
        top_k:      Number of results to return (default: 5).
        namespace:  Optional Pinecone namespace (default: "").
    """
    return f"""You are a helpful search assistant powered by Pinecone vector search and OpenAI embeddings.

The user wants to search for:
> "{query}"

Search the Pinecone index **"{index_name}"** (namespace: "{namespace or 'default'}") and return the top {top_k} results.

Steps:
1. Call the `query_by_text` tool with:
    - index_name  = "{index_name}"
    - query_text  = "{query}"
    - top_k       = {top_k}
    - namespace   = "{namespace}"
    - include_metadata = true
2. Present the results in a clean, readable format:
    - For each match show: rank, similarity score (%), and the stored text / metadata.
3. Briefly summarise what the top results are about in 1–2 sentences.

Start now."""


# ════════════════════════════════════════════════════════════════════════════
# Prompt: rag_answer
# ════════════════════════════════════════════════════════════════════════════
@mcp.prompt()
def rag_answer(
    index_name: str,
    question: str,
    top_k: int = 3,
    namespace: str = "",
) -> str:
    """
    Retrieval-Augmented Generation prompt: fetch relevant context from Pinecone,
    then use OpenAI to answer the user's question grounded in that context.

    Args:
        index_name: Pinecone index that holds your knowledge base.
        question:   The question the user wants answered.
        top_k:      Number of context chunks to retrieve (default: 3).
        namespace:  Optional Pinecone namespace (default: "").
    """
    return f"""You are a RAG (Retrieval-Augmented Generation) assistant.
Your job is to answer the user's question using ONLY context retrieved from Pinecone.

**Question:** {question}

**Steps:**
1. Call `query_by_text` with:
    - index_name  = "{index_name}"
    - query_text  = "{question}"
    - top_k       = {top_k}
    - namespace   = "{namespace}"
    - include_metadata = true
2. Collect the returned chunks (the "text" field in each match's metadata).
3. Answer the question using ONLY the retrieved context. Do not use outside knowledge.
4. Format your response as:

   **Answer:**
    <your answer here, grounded in the context>

   **Sources used:**
    - [id]: <short excerpt from the chunk>
    - ...

5. If none of the retrieved chunks contain enough information to answer,
    say: "I could not find a confident answer in the knowledge base."

Start now."""


# ════════════════════════════════════════════════════════════════════════════
# Prompt: manage_index
# ════════════════════════════════════════════════════════════════════════════
@mcp.prompt()
def manage_index(action: str = "inspect") -> str:
    """
    Guided prompt for Pinecone index management tasks: inspect, clean up, or delete vectors.

    Args:
        action: One of "inspect" (list indexes), "cleanup" (delete specific vectors),
                or "audit" (list indexes and report stats). Default: "inspect".
    """
    action = action.lower().strip()

    if action == "cleanup":
        return """You are a Pinecone database administrator assistant.

The user wants to clean up vectors from a Pinecone index.

Steps:
1. Call `list_indexes` to show all available indexes.
2. Ask the user which index and which vector IDs (or namespace) to clean up.
3. Once confirmed, call `delete_vectors` with the specified index_name and ids.
4. Confirm how many vectors were deleted and from which index/namespace.

⚠️  Always confirm with the user before deleting — deletions are irreversible.

Start by listing the available indexes."""

    elif action == "audit":
        return """You are a Pinecone database auditing assistant.

The user wants an audit of their Pinecone project.

Steps:
1. Call `list_indexes` and display all index names.
2. For each index, summarise what you know (name, any metadata available).
3. Suggest next actions the user might want to take:
    - Query an index to see what's stored
    - Delete stale vectors
    - Upsert new documents

Present the audit in a clean table or bullet list.

Start by listing all indexes now."""

    else:  # default: inspect
        return """You are a Pinecone assistant helping the user explore their vector database.

Steps:
1. Call `list_indexes` to retrieve all Pinecone indexes in the project.
2. Display the index names in a numbered list.
3. Ask the user which index they'd like to work with and what they'd like to do:
    - Search (semantic query)
    - Add documents
    - Delete vectors
    - Audit the index

Wait for their choice before proceeding.

Start by listing the indexes now."""


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="stdio")
