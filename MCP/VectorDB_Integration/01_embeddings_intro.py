"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Understanding Embeddings
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Goal      : Build intuition for embeddings and similarity

Concepts covered:
    • What are embedding vectors?
    • Generating embeddings (OpenAI or local)
    • Cosine similarity by hand
    • Visualizing semantic relationships

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import json
import math
import time
from typing import List
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────
# SECTION 1: What is an embedding?
# ─────────────────────────────────────────────────────────────
print("""
╔════════════════════════════════════════════════════════════╗
║  SECTION 1: What Is an Embedding?                         ║
╚════════════════════════════════════════════════════════════╝

An embedding is a list of floating-point numbers (a vector) that
represents the *meaning* of text in a high-dimensional space.

Example (extremely simplified 3D):
    "cat"  → [0.9, 0.1, 0.2]   (animal-like, fluffy, small)
    "dog"  → [0.85, 0.15, 0.3] (animal-like, fluffy, medium)
    "car"  → [0.0, 0.9, 0.0]   (machine-like, metal, fast)

Real models use 384 to 3072 dimensions to capture nuanced semantics.
The key insight: similar *meanings* produce similar vectors.
""")

input("Press ENTER to continue to Section 2...")


# ─────────────────────────────────────────────────────────────
# SECTION 2: Cosine Similarity (from scratch)
# ─────────────────────────────────────────────────────────────
print("""
╔════════════════════════════════════════════════════════════╗
║  SECTION 2: Cosine Similarity from Scratch                ║
╚════════════════════════════════════════════════════════════╝
""")

def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Compute cosine similarity between two vectors.
    
    Formula:  cos(θ) = (A · B) / (|A| × |B|)
    
    Returns:
        1.0  → identical direction (same meaning)
        0.0  → perpendicular (unrelated)
        -1.0  → opposite direction (antonyms)
    """
    # ── YOUR TASK ──────────────────────────────────────────────
    # Implement cosine similarity using only Python built-ins.
    # Steps:
    #   1. Compute dot product:  sum of (a_i * b_i)
    #   2. Compute magnitude of A: sqrt(sum of a_i^2)
    #   3. Compute magnitude of B: sqrt(sum of b_i^2)
    #   4. Return dot_product / (mag_a * mag_b)
    #
    # HINT: Use math.sqrt() for the square root.
    # ──────────────────────────────────────────────────────────
    
    # TODO: Replace this placeholder with your implementation
    raise NotImplementedError("Implement cosine_similarity!")

    # Uncomment below to test your logic step-by-step:
    # dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    # mag_a = math.sqrt(sum(a**2 for a in vec_a))
    # mag_b = math.sqrt(sum(b**2 for b in vec_b))
    # if mag_a == 0 or mag_b == 0:
    #     return 0.0
    # return dot_product / (mag_a * mag_b)


# Test vectors (simplified concept space)
test_pairs = [
    ("cat",        [0.90, 0.10, 0.20, 0.05]),
    ("dog",        [0.85, 0.15, 0.25, 0.08]),
    ("car",        [0.02, 0.90, 0.05, 0.80]),
    ("vector DB",  [0.10, 0.20, 0.95, 0.30]),
    ("database",   [0.05, 0.25, 0.85, 0.40]),
]

print("Testing cosine_similarity with toy vectors:\n")
print(f"{'Pair':<35} {'Similarity':>10}  {'Interpretation'}")
print("-" * 70)

try:
    for i, (name_a, vec_a) in enumerate(test_pairs):
        for name_b, vec_b in test_pairs[i+1:]:
            sim = cosine_similarity(vec_a, vec_b)
            if sim > 0.9:
                interp = "🟢 Very similar"
            elif sim > 0.7:
                interp = "🟡 Somewhat similar"
            elif sim > 0.3:
                interp = "🟠 Loosely related"
            else:
                interp = "🔴 Unrelated"
            print(f"  {name_a!r:15} vs {name_b!r:15} {sim:>8.4f}  {interp}")

    print("\n✅ cosine_similarity works! Notice that 'cat'/'dog' score")
    print("   higher than 'cat'/'car', even though vectors are made up.")
except NotImplementedError:
    print("⚠️  NotImplementedError: implement cosine_similarity() above first!")
    print("\nExpected outputs (approximately):")
    print("  'cat' vs 'dog'       → ~0.998 (very similar animals)")
    print("  'cat' vs 'car'       → ~0.240 (unrelated)")
    print("  'vector DB' vs 'database' → ~0.978 (related concepts)")

input("\nPress ENTER to continue to Section 3...")


# ─────────────────────────────────────────────────────────────
# SECTION 3: Real Embeddings
# ─────────────────────────────────────────────────────────────
print("""
╔════════════════════════════════════════════════════════════╗
║  SECTION 3: Generating Real Embeddings                    ║
╚════════════════════════════════════════════════════════════╝
""")

def get_embedding_function():
    """
    Returns an embedding function based on available API keys.
    Prefers OpenAI; falls back to local sentence-transformers.
    
    Returns:
        tuple: (embed_fn, model_name, dimensions)
        where embed_fn(texts: List[str]) -> List[List[float]]
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    use_local = os.getenv("USE_LOCAL_EMBEDDINGS", "false").lower() == "true"

    if openai_key and not use_local:
        from openai import OpenAI
        client = OpenAI(api_key=openai_key)
        model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

        def openai_embed(texts: List[str]) -> List[List[float]]:
            response = client.embeddings.create(input=texts, model=model)
            return [item.embedding for item in response.data]

        dims = 1536 if "3-small" in model else 3072
        print(f"Using OpenAI model: {model} ({dims} dimensions)")
        return openai_embed, model, dims

    else:
        from sentence_transformers import SentenceTransformer
        model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        print(f"Loading local model: {model_name} (first run downloads ~90MB)...")
        model = SentenceTransformer(model_name)

        def local_embed(texts: List[str]) -> List[List[float]]:
            embeddings = model.encode(texts, normalize_embeddings=True)
            return embeddings.tolist()

        dims = model.get_sentence_embedding_dimension()
        print(f"Model loaded: {model_name} ({dims} dimensions)")
        return local_embed, model_name, dims


# Sample sentences to embed
sentences = [
    "Vector databases store high-dimensional embeddings",
    "Pinecone is a managed vector database service",
    "Semantic search finds conceptually similar documents",
    "The quick brown fox jumps over the lazy dog",
    "Machine learning models process numerical data",
    "RAG combines retrieval with language generation",
]

print("Sample sentences:\n")
for i, s in enumerate(sentences, 1):
    print(f"  {i}. {s}")

print("\nGenerating embeddings...\n")

try:
    embed_fn, model_name, dims = get_embedding_function()
    
    start = time.time()
    embeddings = embed_fn(sentences)
    elapsed = time.time() - start
    
    print(f"✅ Generated {len(embeddings)} embeddings")
    print(f"   Dimensions: {len(embeddings[0])}")
    print(f"   Time: {elapsed:.2f}s")
    print(f"\nFirst embedding (first 8 values):")
    print(f"  {embeddings[0][:8]}")
    print(f"  ... [{len(embeddings[0])} total dimensions]")

    # ── YOUR TASK ─────────────────────────────────────────────
    # Using your cosine_similarity function from Section 2,
    # find the TWO most similar pairs among the 6 sentences.
    #
    # HINT: Loop through all pairs (i, j) where i < j
    #       and track the highest similarity scores.
    # ─────────────────────────────────────────────────────────
    print("\n--- Pairwise Similarity Matrix ---\n")
    print(f"{'':>5}", end="")
    for i in range(len(sentences)):
        print(f"  [{i+1}]  ", end="")
    print()
    
    # TODO: Compute and print pairwise similarities
    # Expected: sentences about vector DBs should cluster together
    # "quick brown fox" should be most different from all others
    
    # Reference solution (uncomment to check your work):
    # similarities = []
    # for i, (s1, e1) in enumerate(zip(sentences, embeddings)):
    #     row = []
    #     for j, (s2, e2) in enumerate(zip(sentences, embeddings)):
    #         sim = cosine_similarity(e1, e2)
    #         row.append(sim)
    #     print(f"[{i+1}]", " ".join(f"{s:6.3f}" for s in row))
    #     similarities.extend([(sim, i, j) for j, sim in enumerate(row) if j > i])
    # 
    # similarities.sort(reverse=True)
    # print("\nTop 3 most similar pairs:")
    # for sim, i, j in similarities[:3]:
    #     print(f"  {sim:.4f} — [{i+1}] vs [{j+1}]")
    #     print(f"    '{sentences[i][:50]}'")
    #     print(f"    '{sentences[j][:50]}'")

except Exception as e:
    print(f"❌ Error: {e}")
    print("\nMake sure OPENAI_API_KEY or USE_LOCAL_EMBEDDINGS=true is set in .env")

input("\nPress ENTER to continue to Section 4...")


# ─────────────────────────────────────────────────────────────
# SECTION 4: Embedding Documents from Corpus
# ─────────────────────────────────────────────────────────────
print("""
╔════════════════════════════════════════════════════════════╗
║  SECTION 4: Embedding the Workshop Corpus                 ║
╚════════════════════════════════════════════════════════════╝
""")

data_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_docs.json")

with open(data_path) as f:
    docs = json.load(f)

print(f"Loaded {len(docs)} documents from sample_docs.json\n")
print("Sample document:")
print(json.dumps(docs[0], indent=2))

print("\n" + "─" * 60)
print("What we need to embed for vector search:")
print("""
    Option A: Embed title only
        + Fast and cheap
        - Misses body content

    Option B: Embed content only
        + Captures full meaning
        - May miss structured metadata

    Option C: Embed title + content (concatenated)  ← We'll use this
        + Best recall
        - Slightly more tokens

    Option D: Separate embeddings per field
        + Flexible queries
        - More complex, more storage
""")

# ── YOUR TASK ──────────────────────────────────────────────────
# Write a function that prepares text for embedding by combining
# the document's title and content fields.
#
# Requirements:
#   - Format: "Title: {title}\n\nContent: {content}"
#   - Strip leading/trailing whitespace from each field
#   - Handle missing fields gracefully (default to "")
# ──────────────────────────────────────────────────────────────

def prepare_text_for_embedding(doc: dict) -> str:
    """
    Combine document fields into a single string for embedding.
    
    Args:
        doc: Document dict with 'title' and 'content' keys
        
    Returns:
        str: Combined text ready for embedding
    """
    # TODO: Implement this function
    raise NotImplementedError("Implement prepare_text_for_embedding!")

    # HINT:
    # title = doc.get("title", "").strip()
    # content = doc.get("content", "").strip()
    # return f"Title: {title}\n\nContent: {content}"


print("\nTesting prepare_text_for_embedding:")
try:
    result = prepare_text_for_embedding(docs[0])
    print(f"\n{result}\n")
    print("✅ Text preparation works!")
    
    print("\nBatch embedding all documents (this may take a moment)...")
    try:
        embed_fn, _, _ = get_embedding_function()
        texts = [prepare_text_for_embedding(doc) for doc in docs]
        all_embeddings = embed_fn(texts)
        
        print(f"✅ Embedded {len(all_embeddings)} documents")
        
        # Save to a JSON cache so Exercise 02 can reuse them
        cache_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "embeddings_cache.json"
        )
        with open(cache_path, "w") as f:
            json.dump({
                "model": os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
                "embeddings": {
                    docs[i]["id"]: all_embeddings[i]
                    for i in range(len(docs))
                }
            }, f)
        print(f"📦 Embeddings cached to data/embeddings_cache.json")
        
    except Exception as e:
        print(f"⚠️  Embedding failed: {e}")
        print("    (This is OK — Exercise 02 will generate embeddings on-the-fly)")

except NotImplementedError:
    print("⚠️  Implement prepare_text_for_embedding() first!")

print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Exercise Complete!

Key Takeaways:
    • Embeddings are dense vectors capturing semantic meaning
    • Cosine similarity measures directional alignment, not magnitude
    • Real models produce 384 to 3072 dimensional vectors
    • Text preparation (what you embed) significantly affects quality

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
