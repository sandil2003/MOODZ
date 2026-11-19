"""Pinecone vector database service with dynamic provider embedding support (Gemini & OpenAI)."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from uuid import UUID
from pinecone import Pinecone, ServerlessSpec

from config import settings
from app.core.pii_scrubber import PIIScrubber

logger = logging.getLogger(__name__)


class GeminiEmbeddingsWrapper:
    """Wrapper around google.generativeai supporting dimensionality control for Pinecone."""

    def __init__(self, model: str = "models/gemini-embedding-001", dimension: int = 768, api_key: Optional[str] = None):
        import google.generativeai as genai
        self.model = model
        self.dimension = dimension
        if api_key:
            genai.configure(api_key=api_key)
        self._genai = genai

    def embed_query(self, text: str) -> List[float]:
        res = self._genai.embed_content(
            model=self.model,
            content=text,
            output_dimensionality=self.dimension
        )
        return res["embedding"]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        res = self._genai.embed_content(
            model=self.model,
            content=texts,
            output_dimensionality=self.dimension
        )
        return res["embedding"]

    async def aembed_query(self, text: str) -> List[float]:
        return await asyncio.to_thread(self.embed_query, text)

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        return await asyncio.to_thread(self.embed_documents, texts)


class VectorService:
    """Pinecone vector database service supporting long-term episodic memory search."""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        environment: Optional[str] = None,
        index_name: Optional[str] = None,
        embedding_dimension: Optional[int] = None
    ):
        self.provider = provider or ("gemini" if settings.gemini_api_key else "openai")

        if self.provider == "gemini":
            default_dimension = 768
            default_index = f"{settings.pinecone_index_name}-gemini"
        else:
            default_dimension = 1536
            default_index = settings.pinecone_index_name

        self.embedding_dimension = embedding_dimension or default_dimension
        self.index_name = index_name or default_index
        self.api_key = api_key or settings.pinecone_api_key
        self.environment = environment or settings.pinecone_environment

        self.pc = Pinecone(api_key=self.api_key)

        if self.provider == "gemini":
            self.embeddings = GeminiEmbeddingsWrapper(
                model="models/gemini-embedding-001",
                dimension=self.embedding_dimension,
                api_key=settings.gemini_api_key
            )
        else:
            from langchain_openai import OpenAIEmbeddings
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                dimensions=self.embedding_dimension,
                openai_api_key=settings.openai_api_key
            )

        self._initialize_index()

    def _initialize_index(self) -> None:
        """Connect to or create the serverless Pinecone index."""
        try:
            existing_indexes = self.pc.list_indexes()
            index_names = [idx.name for idx in existing_indexes]
            if self.index_name not in index_names:
                logger.info(f"Creating new {self.provider}-compatible Pinecone index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.embedding_dimension,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1")
                )
            self.index = self.pc.Index(self.index_name)
        except Exception as e:
            logger.error(f"Error initializing Pinecone index for provider {self.provider}: {e}")

    async def add_text(
        self,
        user_id: Union[str, UUID],
        text: str,
        data_type: str,
        source: str,
        mood_label: Optional[str] = None,
        context_id: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """Scrub PII, compute dense embedding, and upsert vector with metadata into Pinecone."""
        try:
            clean_text = PIIScrubber.scrub_text(text)
            embedding = await self.embeddings.aembed_query(clean_text)
            now = datetime.now(timezone.utc)
            doc_id = f"{user_id}_{now.timestamp()}"

            metadata = {
                "user_id": str(user_id),
                "timestamp": now.isoformat(),
                "data_type": data_type,
                "source": source,
                "text": clean_text
            }
            if mood_label:
                metadata["mood_label"] = mood_label
            if context_id:
                metadata["context_id"] = context_id
            if additional_info:
                metadata["additional_info"] = json.dumps(additional_info)

            self.index.upsert(vectors=[(doc_id, embedding, metadata)])
            return doc_id
        except Exception as e:
            logger.error(f"Error adding text to vector store ({self.provider}): {e}")
            raise

    async def similarity_search(
        self,
        query: str,
        user_id: Optional[Union[str, UUID]] = None,
        data_type: Optional[str] = None,
        mood_label: Optional[str] = None,
        k: int = 5,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Query Pinecone for semantic matches filtered by user or metadata tags."""
        try:
            query_embedding = await self.embeddings.aembed_query(query)
            filter_dict: Dict[str, Any] = {}
            if user_id:
                filter_dict["user_id"] = {"$eq": str(user_id)}
            if data_type:
                filter_dict["data_type"] = {"$eq": data_type}
            if mood_label:
                filter_dict["mood_label"] = {"$eq": mood_label}

            results = self.index.query(
                vector=query_embedding,
                top_k=k,
                filter=filter_dict if filter_dict else None,
                include_metadata=True
            )

            formatted: List[Dict[str, Any]] = []
            for match in results.matches:
                if score_threshold and match.score < score_threshold:
                    continue
                metadata = dict(match.metadata or {})
                if "additional_info" in metadata and isinstance(metadata["additional_info"], str):
                    try:
                        metadata["additional_info"] = json.loads(metadata["additional_info"])
                    except Exception:
                        pass
                formatted.append({
                    "id": match.id,
                    "text": metadata.get("text", ""),
                    "score": float(match.score),
                    "metadata": metadata
                })
            return formatted
        except Exception as e:
            logger.error(f"Error performing similarity search ({self.provider}): {e}")
            return []

    async def get_user_context(self, user_id: Union[str, UUID], query: str, k: int = 10) -> str:
        """Formatted plain-text summary of past experiences for LLM prompt augmentation."""
        try:
            results = await self.similarity_search(query=query, user_id=user_id, k=k)
            if not results:
                return "No relevant context found."
            parts = [f"Relevant user context ({self.provider.capitalize()}):"]
            for i, result in enumerate(results, 1):
                meta = result["metadata"]
                data_type = meta.get("data_type", "unknown")
                mood = meta.get("mood_label", "N/A")
                timestamp = meta.get("timestamp", "")
                parts.append(f"\n{i}. [{data_type}] (mood: {mood}, relevance: {result['score']:.2f})")
                parts.append(f"   {result['text'][:200]}...")
                parts.append(f"   Time: {timestamp}")
            return "\n".join(parts)
        except Exception as e:
            logger.error(f"Error getting user context ({self.provider}): {e}")
            return "Error retrieving context."

    async def find_similar_moods(self, user_id: Union[str, UUID], current_mood: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve check-ins sharing similar emotional expressions."""
        return await self.similarity_search(query=current_mood, user_id=user_id, data_type="mood_checkin", k=k)

    async def delete_user_data(self, user_id: Union[str, UUID]) -> bool:
        """Purge all vector embeddings associated with a user."""
        try:
            self.index.delete(filter={"user_id": str(user_id)})
            return True
        except Exception as e:
            logger.error(f"Error deleting user data ({self.provider}): {e}")
            return False

    async def get_index_stats(self) -> Dict[str, Any]:
        """Describe index vector count and dimensional stats."""
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "namespaces": stats.namespaces
            }
        except Exception as e:
            logger.error(f"Error getting index stats ({self.provider}): {e}")
            return {}


_vector_service_instances: Dict[str, VectorService] = {}


def get_vector_service(provider: Optional[str] = None, embedding_dimension: Optional[int] = None) -> VectorService:
    """Retrieve or create singleton VectorService for a specific provider."""
    global _vector_service_instances
    selected_provider = provider or ("gemini" if settings.gemini_api_key else "openai")
    cache_key = f"{selected_provider}_{embedding_dimension or 'default'}"
    if cache_key not in _vector_service_instances:
        _vector_service_instances[cache_key] = VectorService(
            provider=selected_provider,
            embedding_dimension=embedding_dimension
        )
    return _vector_service_instances[cache_key]


VectorServiceGemini = VectorService


def get_vector_service_gemini(embedding_dimension: int = 768) -> VectorService:
    """Convenience getter for the Gemini-backed Pinecone service."""
    return get_vector_service(provider="gemini", embedding_dimension=embedding_dimension)
