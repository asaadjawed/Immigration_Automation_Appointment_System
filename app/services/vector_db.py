"""
Vector database service for storing and retrieving document embeddings.
Uses ChromaDB for vector storage and similarity search.
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Optional
import os
from app.config import settings
from sentence_transformers import SentenceTransformer


class VectorDBService:
    """Service for vector database operations."""
    
    def __init__(self):
        self.db_path = settings.VECTOR_DB_PATH
        self.embedding_model_name = settings.EMBEDDING_MODEL
        
        # Create directory if it doesn't exist
        os.makedirs(self.db_path, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.db_path,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="immigration_documents",
            metadata={"description": "Immigration office documents and guidelines"}
        )
        
        # Initialize embedding model
        print(f"Loading embedding model: {self.embedding_model_name}")
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        print("Embedding model loaded successfully")
    
    def add_document(self, text: str, metadata: Dict, document_id: Optional[str] = None) -> str:
        """
        Add a document to the vector database.
        
        Args:
            text: Document text to embed
            metadata: Document metadata (filename, type, etc.)
            document_id: Optional document ID (auto-generated if not provided)
            
        Returns:
            Document ID in vector database
        """
        if not document_id:
            import uuid
            document_id = str(uuid.uuid4())
        
        # Generate embedding
        embedding = self.embedding_model.encode(text).tolist()
        
        # Add to collection
        self.collection.add(
            ids=[document_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata]
        )
        
        return document_id
    
    def search_similar(self, query: str, n_results: int = 5, guideline_name: Optional[str] = None) -> List[Dict]:
        """
        Search for similar documents.
        
        Args:
            query: Search query text
            n_results: Number of results to return
            guideline_name: Optional - filter by specific guideline name (e.g., "residence_permit.txt")
            
        Returns:
            List of similar documents with scores
        """
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query).tolist()
        
        # Build where clause if filtering by guideline name
        # ChromaDB requires using operators like $and, $eq for filtering
        where_clause = None
        if guideline_name:
            where_clause = {
                "$and": [
                    {"type": {"$eq": "guideline"}},
                    {"name": {"$eq": guideline_name}}
                ]
            }
        
        # Search
        query_params = {
            "query_embeddings": [query_embedding],
            "n_results": n_results
        }
        
        if where_clause:
            query_params["where"] = where_clause
        
        results = self.collection.query(**query_params)
        
        # Format results
        similar_docs = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                similar_docs.append({
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if "distances" in results else None
                })
        
        return similar_docs
    
    def get_document(self, document_id: str) -> Optional[Dict]:
        """Get a document by ID."""
        results = self.collection.get(ids=[document_id])
        
        if results["ids"]:
            return {
                "id": results["ids"][0],
                "document": results["documents"][0],
                "metadata": results["metadatas"][0]
            }
        
        return None
    
    def delete_document(self, document_id: str):
        """Delete a document from the vector database."""
        self.collection.delete(ids=[document_id])
    
    def add_guidelines(self, guidelines_text: str, guideline_name: str):
        """
        Add guidelines to the vector database.
        This is used for RAG - comparing student documents with guidelines.
        
        Args:
            guidelines_text: Text content of guidelines
            guideline_name: Name/identifier of the guideline
        """
        metadata = {
            "type": "guideline",
            "name": guideline_name,
            "source": "immigration_office"
        }
        
        return self.add_document(guidelines_text, metadata)

