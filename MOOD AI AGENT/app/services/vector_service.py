from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from config import settings


class VectorService:
    """
    Pinecone vector database service with LangChain OpenAI embeddings.
    
    Handles embedding generation and similarity search for mood data,
    user facts, and conversation context.
    
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
        embedding_dimension: int = 1536 # Match your Pinecone index dimension
    ):
        """
        Initialize Pinecone vector service.
        
        Args:
            api_key: Pinecone API key (defaults to settings)
            environment: Pinecone environment (defaults to settings)
            index_name: Pinecone index name (defaults to settings)
            embedding_dimension: Embedding dimension (512 or 1536)
        """
        self.api_key = api_key or settings.pinecone_api_key
        self.environment = environment or settings.pinecone_environment
        self.index_name = index_name or settings.pinecone_index_name
        self.embedding_dimension = embedding_dimension
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=self.api_key)
        
        # Initialize OpenAI embeddings with configurable dimensions
        # text-embedding-3-small supports dimensions parameter
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            dimensions=self.embedding_dimension,  # Set to match Pinecone index
            openai_api_key=settings.openai_api_key
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
                print(f"Creating new index: {self.index_name}")
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
            raise
    
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
        """
        Add text to vector database with embeddings.
        
        Args:
            user_id: User UUID
            text: Text content to embed
            data_type: Type of data ("text", "music", "journal", "mood_checkin")
            source: Source of data ("typing", "voice", "music_analysis", "journal")
            mood_label: Optional mood label ("happy", "sad", "angry", "neutral")
            context_id: Optional context/session ID
            additional_info: Optional additional metadata
            
        Returns:
            str: Document ID
        """
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
                "text": text  # Store original text in metadata
            }
            
            # Add optional fields
            if mood_label:
                metadata["mood_label"] = mood_label
            if context_id:
                metadata["context_id"] = context_id
            if additional_info:
                # Convert dict to JSON string for Pinecone compatibility
                import json
                metadata["additional_info"] = json.dumps(additional_info)
            
            # Upsert to Pinecone
            self.index.upsert(
                vectors=[(doc_id, embedding, metadata)],
                namespace=""
            )
            
            return doc_id
            
        except Exception as e:
            print(f"Error adding text to vector store: {e}")
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
        """
        Perform similarity search on vector database.
        
        Args:
            query: Search query text
            user_id: Optional filter by user ID
            data_type: Optional filter by data type
            mood_label: Optional filter by mood label
            k: Number of results to return
            score_threshold: Optional minimum similarity score (0-1)
            
        Returns:
            List[Dict]: List of matching documents with scores
        """
        try:
            # Generate query embedding
            query_embedding = await self.embeddings.aembed_query(query)
            
            # Build filter
            filter_dict = {}
            if user_id:
                filter_dict["user_id"] = {"$eq": str(user_id)}
            if data_type:
                filter_dict["data_type"] = {"$eq": data_type}
            if mood_label:
                filter_dict["mood_label"] = {"$eq": mood_label}
            
            # Query Pinecone
            if filter_dict:
                results = self.index.query(
                    vector=query_embedding,
                    top_k=k,
                    filter=filter_dict,
                    include_metadata=True,
                    namespace=""
                )
            else:
                results = self.index.query(
                    vector=query_embedding,
                    top_k=k,
                    include_metadata=True,
                    namespace=""
                )
            
            # Format results
            formatted_results = []
            for match in results.matches:
                # Apply score threshold if specified
                if score_threshold and match.score < score_threshold:
                    continue
                
                # Parse additional_info if present
                metadata = dict(match.metadata)
                if "additional_info" in metadata and isinstance(metadata["additional_info"], str):
                    import json
                    try:
                        metadata["additional_info"] = json.loads(metadata["additional_info"])
                    except json.JSONDecodeError:
                        pass  # Keep as string if not valid JSON
                
                result = {
                    "id": match.id,
                    "text": match.metadata.get("text", ""),
                    "score": float(match.score),
                    "metadata": metadata
                }
                formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            print(f"Error performing similarity search: {e}")
            return []
    
    async def get_user_context(
        self,
        user_id: UUID,
        query: str,
        k: int = 10
    ) -> str:
        """
        Get relevant user context for a query.
        
        Args:
            user_id: User UUID
            query: Current user query/message
            k: Number of relevant items to retrieve
            
        Returns:
            str: Formatted context string
        """
        try:
            # Search for relevant user data
            results = await self.similarity_search(
                query=query,
                user_id=user_id,
                k=k
            )
            
            if not results:
                return "No relevant context found."
            
            # Format context
            context_parts = ["Relevant user context:"]
            
            for i, result in enumerate(results, 1):
                metadata = result["metadata"]
                text = result["text"]
                score = result["score"]
                
                data_type = metadata.get("data_type", "unknown")
                mood = metadata.get("mood_label", "N/A")
                timestamp = metadata.get("timestamp", "")
                
                context_parts.append(
                    f"\n{i}. [{data_type}] (mood: {mood}, relevance: {score:.2f})"
                )
                context_parts.append(f"   {text[:200]}...")
                context_parts.append(f"   Time: {timestamp}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            print(f"Error getting user context: {e}")
            return "Error retrieving context."
    
    async def find_similar_moods(
        self,
        user_id: UUID,
        current_mood: str,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar past mood entries.
        
        Args:
            user_id: User UUID
            current_mood: Current mood description
            k: Number of similar moods to find
            
        Returns:
            List[Dict]: Similar mood entries
        """
        return await self.similarity_search(
            query=current_mood,
            user_id=user_id,
            data_type="mood_checkin",
            k=k
        )
    
    async def delete_user_data(self, user_id: UUID) -> bool:
        """
        Delete all vectors for a specific user.
        
        Args:
            user_id: User UUID
            
        Returns:
            bool: True if successful
        """
        try:
            # Delete by filter
            self.index.delete(filter={"user_id": str(user_id)})
            return True
        except Exception as e:
            print(f"Error deleting user data: {e}")
            return False
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """
        Get Pinecone index statistics.
        
        Returns:
            Dict: Index statistics
        """
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "namespaces": stats.namespaces
            }
        except Exception as e:
            print(f"Error getting index stats: {e}")
            return {}


# Global vector service instance
_vector_service: Optional[VectorService] = None


def get_vector_service(embedding_dimension: int = 1536) -> VectorService:
    """
    Get or create the global vector service instance.
    
    Args:
        embedding_dimension: Embedding dimension (512 or 1536)
        Default is 1536 to match text-embedding-3-small
    
    Returns:
        VectorService: Vector service instance
    """
    global _vector_service
    
    if _vector_service is None:
        _vector_service = VectorService(embedding_dimension=embedding_dimension)
    
    return _vector_service
