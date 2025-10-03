"""
Embedding Service for Vector Operations
Handles semantic embeddings for policies, rejected clauses, and similarity search
REQ-VC-006: Semantic similarity for rejection blocklist
REQ-PD-001: Policy drift detection via embeddings
"""

from typing import List, Dict, Optional, Tuple
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from config.settings import settings


class EmbeddingService:
    """
    Service for generating and managing semantic embeddings
    Uses sentence-transformers for embedding generation
    Uses ChromaDB for vector storage and similarity search
    """

    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL
        self.embedding_model: Optional[SentenceTransformer] = None
        self.chroma_client: Optional[chromadb.Client] = None
        self.policies_collection = None
        self.rejections_collection = None

    def _load_model(self):
        """Lazy load the embedding model"""
        if not self.embedding_model:
            self.embedding_model = SentenceTransformer(self.model_name)

    def _init_chroma(self):
        """Initialize ChromaDB client and collections"""
        if not self.chroma_client:
            self.chroma_client = chromadb.Client(
                ChromaSettings(
                    persist_directory=settings.CHROMA_PERSIST_DIRECTORY,
                    anonymized_telemetry=False,
                )
            )

            # Get or create collections
            self.policies_collection = self.chroma_client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION_POLICIES,
                metadata={"description": "Policy embeddings for semantic search"},
            )

            self.rejections_collection = self.chroma_client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION_REJECTIONS,
                metadata={"description": "Rejected clause embeddings for blocklist"},
            )

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as list of floats
        """
        self._load_model()
        embedding = self.embedding_model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        self._load_model()
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def add_policy_embedding(
        self, policy_id: str, policy_text: str, metadata: Optional[Dict] = None
    ) -> bool:
        """
        Add policy embedding to vector database

        Args:
            policy_id: UUID of policy
            policy_text: Policy text to embed
            metadata: Optional metadata (category, version, etc.)

        Returns:
            True if successful
        """
        self._init_chroma()

        embedding = self.generate_embedding(policy_text)

        self.policies_collection.add(
            ids=[policy_id],
            embeddings=[embedding],
            documents=[policy_text],
            metadatas=[metadata or {}],
        )

        return True

    def search_similar_policies(
        self, query_text: str, n_results: int = 5, category: Optional[str] = None
    ) -> List[Dict]:
        """
        Find policies similar to query text

        Args:
            query_text: Text to search for
            n_results: Number of results to return
            category: Optional category filter

        Returns:
            List of similar policies with scores
        """
        self._init_chroma()

        query_embedding = self.generate_embedding(query_text)

        # Build where clause for filtering
        where = {"category": category} if category else None

        results = self.policies_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
        )

        # Format results
        similar_policies = []
        for i, policy_id in enumerate(results["ids"][0]):
            similar_policies.append(
                {
                    "policy_id": policy_id,
                    "policy_text": results["documents"][0][i],
                    "similarity_score": 1 - results["distances"][0][i],  # Convert distance to similarity
                    "metadata": results["metadatas"][0][i],
                }
            )

        return similar_policies

    def add_rejected_clause(
        self, rejection_id: str, clause_text: str, metadata: Optional[Dict] = None
    ) -> bool:
        """
        Add rejected clause to blocklist
        REQ-VC-006: Rejection blocklist for risk mitigation

        Args:
            rejection_id: UUID of rejection
            clause_text: Rejected clause text to embed
            metadata: Optional metadata (session_id, rationale, etc.)

        Returns:
            True if successful
        """
        self._init_chroma()

        embedding = self.generate_embedding(clause_text)

        self.rejections_collection.add(
            ids=[rejection_id],
            embeddings=[embedding],
            documents=[clause_text],
            metadatas=[metadata or {}],
        )

        return True

    def check_against_rejections(
        self, clause_text: str, threshold: Optional[float] = None
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Check if clause is similar to previously rejected clauses
        REQ-VC-006: Block reintroduction of rejected terms

        Args:
            clause_text: Clause text to check
            threshold: Similarity threshold (default from settings)

        Returns:
            Tuple of (is_blocked, rejection_details)
            - is_blocked: True if clause matches rejected clause
            - rejection_details: Dict with rejection info if blocked, else None
        """
        self._init_chroma()

        threshold = threshold or settings.REJECTION_SIMILARITY_THRESHOLD
        query_embedding = self.generate_embedding(clause_text)

        results = self.rejections_collection.query(
            query_embeddings=[query_embedding],
            n_results=1,
        )

        if not results["ids"][0]:
            return False, None

        # Check if top match exceeds threshold
        similarity_score = 1 - results["distances"][0][0]

        if similarity_score >= threshold:
            return True, {
                "rejection_id": results["ids"][0][0],
                "original_clause": results["documents"][0][0],
                "similarity_score": similarity_score,
                "metadata": results["metadatas"][0][0],
            }

        return False, None

    def calculate_policy_drift(
        self, old_policy_text: str, new_policy_text: str
    ) -> float:
        """
        Calculate semantic drift between policy versions
        REQ-PD-001: Policy drift detection

        Args:
            old_policy_text: Previous policy version
            new_policy_text: New policy version

        Returns:
            Drift score (cosine similarity, 0-1, higher is more similar)
        """
        self._load_model()

        embeddings = self.generate_embeddings_batch([old_policy_text, new_policy_text])

        # Calculate cosine similarity
        import numpy as np

        old_emb = np.array(embeddings[0])
        new_emb = np.array(embeddings[1])

        similarity = np.dot(old_emb, new_emb) / (
            np.linalg.norm(old_emb) * np.linalg.norm(new_emb)
        )

        return float(similarity)

    def remove_policy_embedding(self, policy_id: str) -> bool:
        """
        Remove policy from vector database

        Args:
            policy_id: UUID of policy to remove

        Returns:
            True if successful
        """
        self._init_chroma()

        try:
            self.policies_collection.delete(ids=[policy_id])
            return True
        except Exception:
            return False

    def remove_rejection(self, rejection_id: str) -> bool:
        """
        Remove rejection from blocklist

        Args:
            rejection_id: UUID of rejection to remove

        Returns:
            True if successful
        """
        self._init_chroma()

        try:
            self.rejections_collection.delete(ids=[rejection_id])
            return True
        except Exception:
            return False

    def get_collection_stats(self) -> Dict:
        """
        Get statistics about vector collections

        Returns:
            Dict with collection statistics
        """
        self._init_chroma()

        return {
            "policies": {
                "count": self.policies_collection.count(),
                "name": settings.CHROMA_COLLECTION_POLICIES,
            },
            "rejections": {
                "count": self.rejections_collection.count(),
                "name": settings.CHROMA_COLLECTION_REJECTIONS,
            },
            "embedding_model": self.model_name,
            "embedding_dimension": settings.EMBEDDING_DIMENSION,
        }


# Global embedding service instance
embedding_service = EmbeddingService()
