"""
Text embedding utilities for semantic search.

This module provides text embedding functionality for RAG search.
Currently uses a fallback implementation for development.
Can be replaced with OpenAI, Ollama, or other embedding providers.
"""

from typing import List


def embed_query(text: str) -> List[float]:
    """
    Convert text to an embedding vector for semantic search.

    Current implementation: Deterministic random fallback for development.
    TODO: Replace with real embeddings (OpenAI, BGE, Sentence-Transformers, etc.)

    Args:
        text: Query text to embed

    Returns:
        List of floats representing the embedding vector (128-dimensional)
    """
    # Fallback: tiny fixed vector to avoid runtime failure in dev
    # Uses deterministic seeding so same text always gets same vector
    import random

    # Create deterministic seed from text hash
    seed = hash(text) & 0xFFFFFFFF  # Ensure positive 32-bit integer
    random.seed(seed)

    # Generate 128-dimensional vector
    # This maintains consistency: same input = same output
    return [random.random() for _ in range(128)]


def embed_batch(texts: List[str]) -> List[List[float]]:
    """
    Embed multiple texts at once (more efficient for batch operations).

    Args:
        texts: List of texts to embed

    Returns:
        List of embedding vectors
    """
    return [embed_query(text) for text in texts]


# Future implementation example (commented out):
#
# from openai import OpenAI
# client = OpenAI()
#
# def embed_query(text: str) -> List[float]:
#     response = client.embeddings.create(
#         model="text-embedding-3-small",
#         input=text
#     )
#     return response.data[0].embedding
#
# Or with Ollama:
#
# import ollama
#
# def embed_query(text: str) -> List[float]:
#     response = ollama.embeddings(
#         model='nomic-embed-text',
#         prompt=text
#     )
#     return response['embedding']
