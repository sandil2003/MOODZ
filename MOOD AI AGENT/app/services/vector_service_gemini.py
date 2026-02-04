from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
from pinecone import Pinecone, ServerlessSpec
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from config import settings


class VectorServiceGemini:
    """
    Pinecone vector database service with Google Gemini embeddings.
    
    Handles embedding generation and similarity search for mood data,
    user facts, and conversation context using Gemini-based embeddings.
    
    Metadata structure:
    - user_id: string - Unique identifier for the user
    - timestamp: datetime - When this entry was created
    - data_type: string - "text", "music", "journal", "mood_checkin"
    - mood_label: string - Optional: "happy", "sad", "angry", "neutral"
    - source: string - "typing", "voice", "music_analysis", "journal"
    - context_id: string - Optional: group multiple vectors under one context/session
    - additional_info: dict - Any other custom info (song genre, emotion intensity, etc.)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        environment: Optional[str] = None,
        index_name: Optional[str] = None,
        embedding_dimension: int = 768 # Default for Gemini text-embedding-004
    ):
        """
        Initialize Pinecone vector service with Gemini embeddings.
        
        Args:
            api_key: Pinecone API key (defaults to settings)
            environment: Pinecone environment (defaults to settings)
            index_name: Pinecone index name (defaults to settings)
            embedding_dimension: Embedding dimension (768 for Gemini)
        """
        self.api_key = api_key or settings.pinecone_api_key
        # Environment is not strictly needed for the new Pinecone SDK but stored for compatibility
        self.environment = environment or settings.pinecone_environment
        self.index_name = index_name or f"{settings.pinecone_index_name}-gemini"
        self.embedding_dimension = embedding_dimension
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=self.api_key)
        
        # Initialize Gemini embeddings
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=settings.gemini_api_key
        )
        
        # Initialize or get index
        self._initialize_index()
    
    def _initialize_index(self):
        """Initialize or connect to Pinecone index."""
        try:
            # Check if index exists
            existing_indexes = self.pc.list_indexes()
            index_names = [idx.name for idx in existing_indexes]
            
            if self.index_name not in index_names:
                print(f"Creating new Gemini-compatible index: {self.index_name}")
                # Create index with configured dimensions
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.embedding_dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                print(f"✓ Index '{self.index_name}' created with {self.embedding_dimension} dimensions")
            else:
                print(f"✓ Connected to existing index: {self.index_name}")
            
            # Get index
            self.index = self.pc.Index(self.index_name)
            
        except Exception as e:
            print(f"Error initializing Pinecone index: {e}")
            # Don't raise, allow graceful degradation if possible
    
    async def add_text(
        self,
        user_id: UUID,
        text: str,
        data_type: str,
        source: str,
        mood_label: Optional[str] = None,
        context_id: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add text to vector database with Gemini embeddings."""
        try:
            # Generate embedding
            embedding = await self.embeddings.aembed_query(text)
            
            # Generate unique ID
            doc_id = f"{user_id}_{datetime.utcnow().timestamp()}"
            
            # Prepare metadata
            metadata = {
                "user_id": str(user_id),
                "timestamp": datetime.utcnow().isoformat(),
                "data_type": data_type,
                "source": source,
                "text": text
            }
            
            if mood_label: metadata["mood_label"] = mood_label
            if context_id: metadata["context_id"] = context_id
            if additional_info:
                import json
                metadata["additional_info"] = json.dumps(additional_info)
            
            self.index.upsert(vectors=[(doc_id, embedding, metadata)])
            return doc_id
        except Exception as e:
            print(f"Error adding text to Gemini vector store: {e}")
            raise

    async def similarity_search(
        self,
        query: str,
        user_id: Optional[UUID] = None,
        data_type: Optional[str] = None,
        mood_label: Optional[str] = None,
        k: int = 5,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Perform similarity search on vector database."""
        try:
            query_embedding = await self.embeddings.aembed_query(query)
            
            filter_dict = {}
            if user_id: filter_dict["user_id"] = {"$eq": str(user_id)}
            if data_type: filter_dict["data_type"] = {"$eq": data_type}
            if mood_label: filter_dict["mood_label"] = {"$eq": mood_label}
            
            results = self.index.query(
                vector=query_embedding,
                top_k=k,
                filter=filter_dict if filter_dict else None,
                include_metadata=True
            )
            
            formatted_results = []
            for match in results.matches:
                if score_threshold and match.score < score_threshold:
                    continue
                
                metadata = dict(match.metadata)
                if "additional_info" in metadata and isinstance(metadata["additional_info"], str):
                    import json
                    try: metadata["additional_info"] = json.loads(metadata["additional_info"])
                    except: pass
                
                formatted_results.append({
                    "id": match.id,
                    "text": match.metadata.get("text", ""),
                    "score": float(match.score),
                    "metadata": metadata
                })
            return formatted_results
        except Exception as e:
            print(f"Error performing similarity search (Gemini): {e}")
            return []

    async def get_user_context(self, user_id: UUID, query: str, k: int = 10) -> str:
        """Get relevant user context for a query."""
        results = await self.similarity_search(query=query, user_id=user_id, k=k)
        if not results: return "No relevant context found."
        
        context_parts = ["Relevant user context (Gemini):"]
        for i, result in enumerate(results, 1):
            m = result["metadata"]
            context_parts.append(f"\n{i}. [{m.get('data_type', 'unknown')}] {result['text'][:200]}...")
        return "\n".join(context_parts)


# Global vector service instance for Gemini
_vector_service_gemini: Optional[VectorServiceGemini] = None

def get_vector_service_gemini(embedding_dimension: int = 768) -> VectorServiceGemini:
    global _vector_service_gemini
    if _vector_service_gemini is None:
        _vector_service_gemini = VectorServiceGemini(embedding_dimension=embedding_dimension)
    return _vector_service_gemini
