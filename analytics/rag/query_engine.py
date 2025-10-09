"""
Vector Store Query Engine

Simple SQLite-based vector store for analytics insights.
"""
import sqlite3
from pathlib import Path
import json


class VectorStore:
    """SQLite-backed vector store for semantic search."""
    
    def __init__(self, db_path: Path):
        """
        Initialize vector store.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self._ensure_schema()
    
    def _ensure_schema(self):
        """Create vector store schema if needed."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS vectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                metadata TEXT,
                embedding BLOB
            )
        """)
        self.conn.commit()
    
    def search(self, embedder, query: str, k: int = 6) -> list[dict]:
        """
        Search for similar documents.
        
        Args:
            embedder: Embedding model instance
            query: Search query text
            k: Number of results to return
            
        Returns:
            List of matching documents with scores
        """
        # Get query embedding
        query_vec = embedder.encode(query)
        
        # Fetch all vectors (simple implementation - could optimize with indexing)
        cursor = self.conn.execute("SELECT id, text, metadata FROM vectors")
        results = []
        
        for row_id, text, metadata in cursor.fetchall():
            # Simple cosine similarity (stub - implement proper similarity)
            score = 0.5  # Placeholder score
            results.append({
                "id": row_id,
                "text": text,
                "metadata": json.loads(metadata) if metadata else {},
                "score": score
            })
        
        # Return top k
        return sorted(results, key=lambda x: x["score"], reverse=True)[:k]
    
    def add(self, text: str, metadata: dict = None):
        """Add document to vector store."""
        self.conn.execute(
            "INSERT INTO vectors (text, metadata) VALUES (?, ?)",
            (text, json.dumps(metadata) if metadata else None)
        )
        self.conn.commit()
