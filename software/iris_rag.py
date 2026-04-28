"""
iris_rag.py — Lightweight RAG module for Echo IRIS
ECE 202 | Colorado State University | Spring 2026

Uses nomic-embed-text via Ollama for embeddings.
No ChromaDB or heavy dependencies — just numpy cosine similarity.
Knowledge base is loaded from iris_knowledge.md at startup.

Usage:
    from iris_rag import IRISRag
    rag = IRISRag()
    rag.load()
    answer, confidence = rag.query("what hardware does iris use?")
"""

import os
import json
import math
import requests

# --- CONFIGURATION ---
HOME = os.path.expanduser("~")
KNOWLEDGE_FILE  = os.path.join(HOME, "echo-iris", "software", "iris_knowledge.md")
CACHE_FILE      = os.path.join(HOME, "iris_rag_cache.json")
EMBED_MODEL     = "nomic-embed-text:v1.5"
OLLAMA_URL      = "http://localhost:11434"
EMBED_URL       = f"{OLLAMA_URL}/api/embeddings"
CHAT_URL        = f"{OLLAMA_URL}/api/chat"
LLM_MODEL       = "qwen3:0.6b"
TOP_K           = 2        # Number of chunks to retrieve
MIN_CONFIDENCE  = 0.45     # Cosine similarity threshold to attempt an answer
MAX_TOKENS      = 80       # Keep responses short for voice output
EMBED_TIMEOUT   = 10
LLM_TIMEOUT     = 60


# ============================================================
#  EMBEDDING HELPERS
# ============================================================

def _embed(text: str) -> list[float] | None:
    """Get embedding vector for a piece of text via Ollama."""
    try:
        r = requests.post(
            EMBED_URL,
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=EMBED_TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get("embedding")
    except Exception as e:
        print(f"[RAG] Embed error: {e}")
        return None


def _cosine(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ============================================================
#  KNOWLEDGE BASE LOADER
# ============================================================

def _load_chunks(filepath: str) -> list[str]:
    """
    Load and split iris_knowledge.md into chunks.
    Chunks are separated by '---' lines.
    """
    if not os.path.exists(filepath):
        print(f"[RAG] Knowledge file not found: {filepath}")
        return []

    with open(filepath, "r") as f:
        raw = f.read()

    chunks = []
    for block in raw.split("---"):
        block = block.strip()
        # Remove markdown headers and blank lines, keep content
        lines = [l.strip() for l in block.splitlines() if l.strip() and not l.startswith("#")]
        if lines:
            chunks.append(" ".join(lines))

    print(f"[RAG] Loaded {len(chunks)} knowledge chunks from {filepath}")
    return chunks


# ============================================================
#  MAIN RAG CLASS
# ============================================================

class IRISRag:
    def __init__(self):
        self.chunks: list[str] = []
        self.vectors: list[list[float]] = []
        self.loaded = False

    def load(self, force_rebuild: bool = False):
        """
        Load knowledge base and build embedding index.
        Uses a JSON cache to avoid re-embedding on every startup.
        Set force_rebuild=True to regenerate the cache.
        """
        self.chunks = _load_chunks(KNOWLEDGE_FILE)
        if not self.chunks:
            print("[RAG] No chunks loaded. RAG disabled.")
            return

        # Try loading from cache first
        if not force_rebuild and os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r") as f:
                    cache = json.load(f)
                if cache.get("chunks") == self.chunks:
                    self.vectors = cache["vectors"]
                    self.loaded = True
                    print(f"[RAG] Loaded {len(self.vectors)} embeddings from cache.")
                    return
                else:
                    print("[RAG] Knowledge base changed, rebuilding embeddings...")
            except Exception:
                print("[RAG] Cache read failed, rebuilding...")

        # Build embeddings
        print("[RAG] Building embedding index (this takes ~10-20 seconds)...")
        self.vectors = []
        for i, chunk in enumerate(self.chunks):
            vec = _embed(f"search_document: {chunk}")
            if vec:
                self.vectors.append(vec)
            else:
                # Placeholder zero vector on failure
                self.vectors.append([0.0] * 768)
            print(f"[RAG]   Embedded chunk {i+1}/{len(self.chunks)}")

        # Save cache
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump({"chunks": self.chunks, "vectors": self.vectors}, f)
            print("[RAG] Embedding cache saved.")
        except Exception as e:
            print(f"[RAG] Cache save failed: {e}")

        self.loaded = True
        print("[RAG] Ready.")

    def retrieve(self, query: str) -> tuple[list[str], float]:
        """
        Find the top-K most relevant chunks for a query.
        Returns (list of chunk strings, best similarity score).
        """
        if not self.loaded or not self.vectors:
            return [], 0.0

        query_vec = _embed(f"search_query: {query}")
        if not query_vec:
            return [], 0.0

        scores = [_cosine(query_vec, v) for v in self.vectors]
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:TOP_K]
        top_chunks = [self.chunks[i] for i in top_indices]
        best_score = scores[top_indices[0]]

        return top_chunks, best_score

    def query(self, user_text: str) -> tuple[str | None, float]:
        """
        Full RAG pipeline: retrieve relevant chunks, then ask the LLM.
        Returns (answer string or None, confidence score).
        Returns None if confidence is below MIN_CONFIDENCE threshold.
        """
        if not self.loaded:
            return None, 0.0

        chunks, confidence = self.retrieve(user_text)

        if confidence < MIN_CONFIDENCE:
            print(f"[RAG] Low confidence ({confidence:.2f}) - skipping LLM.")
            return None, confidence

        print(f"[RAG] Confidence: {confidence:.2f} - querying LLM with {len(chunks)} chunks.")

        context = "\n\n".join(chunks)
        prompt = (
 	   f"/no_think "
 	   f"You are IRIS, an AI-powered mini-Jeep. Answer in first person as IRIS. "
 	   f"Use ONLY the context below. Reply in 1-2 full sentences. "
 	   f"Start your answer directly, no preamble.\n\n"
 	   f"Context:\n{context}\n\n"
 	   f"Question: {user_text}\n"
 	   f"IRIS says:"
)
        try:
            response = requests.post(
                CHAT_URL,
                json={
                    "model": LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
	            "think": False,
                    "options": {
                        "num_predict": MAX_TOKENS,
                        "num_thread": 2,
                        "temperature": 0.3,
                        "top_p": 0.9,
                    },
                },
                timeout=LLM_TIMEOUT,
            )
            response.raise_for_status()
            answer = response.json().get("message", {}).get("content", "").strip()
            # Clean any leftover thinking tags from qwen
            if "<think>" in answer:
                answer = answer.split("</think>")[-1].strip()
            answer = answer.replace("*", "").replace("#", "").strip()
            return answer, confidence

        except requests.exceptions.Timeout:
            print("[RAG] LLM timeout.")
            return None, confidence
        except Exception as e:
            print(f"[RAG] LLM error: {e}")
            return None, confidence


# ============================================================
#  QUICK TEST (run directly to verify setup)
# ============================================================

if __name__ == "__main__":
    print("=== IRIS RAG Test ===")
    rag = IRISRag()
    rag.load()

    test_questions = [
        "who built iris?",
        "what camera does iris use?",
        "what is the power system?",
        "what programming language is used?",
        "when is demo day?",
    ]

    for q in test_questions:
        print(f"\nQ: {q}")
        answer, conf = rag.query(q)
        if answer:
            print(f"A ({conf:.2f}): {answer}")
        else:
            print(f"  (no answer, confidence too low: {conf:.2f})")
