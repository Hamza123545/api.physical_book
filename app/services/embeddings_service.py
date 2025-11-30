"""
Embeddings service for managing vector operations with Qdrant
Supports both FastEmbed (local, free) and OpenAI embeddings
Handles collection creation, vector ingestion, and similarity search
"""
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.config import (
    get_qdrant_client,
    get_openai_client,
    QDRANT_COLLECTION_NAME,
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL,
    TOP_K_CHUNKS,
    SIMILARITY_THRESHOLD,
    USE_FASTEMBED
)
from app.utils.logger import setup_logger, log_external_api_call
import time

logger = setup_logger(__name__)

# Initialize FastEmbed if enabled
fastembed_model = None
if USE_FASTEMBED:
    try:
        from fastembed import TextEmbedding
        fastembed_model = TextEmbedding(model_name=EMBEDDING_MODEL)
        logger.info(f"FastEmbed initialized with model: {EMBEDDING_MODEL}")
    except Exception as e:
        logger.error(f"Failed to initialize FastEmbed: {e}")
        logger.warning("Falling back to OpenAI embeddings")
        USE_FASTEMBED = False


def create_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Create embeddings for a batch of texts using FastEmbed or OpenAI

    Args:
        texts: List of text strings to embed

    Returns:
        List of embedding vectors
    """
    try:
        start_time = time.time()

        if USE_FASTEMBED and fastembed_model:
            # Use FastEmbed for local, free embeddings
            embeddings_generator = fastembed_model.embed(texts)
            embeddings = [list(embedding) for embedding in embeddings_generator]

            duration_ms = (time.time() - start_time) * 1000
            log_external_api_call(
                logger,
                service="FastEmbed",
                operation="create_embeddings",
                duration_ms=duration_ms,
                success=True,
                batch_size=len(texts),
                model=EMBEDDING_MODEL
            )

            logger.info(f"Created {len(embeddings)} embeddings with FastEmbed in {duration_ms:.2f}ms (FREE)")
            return embeddings

        else:
            # Use OpenAI embeddings API
            client = get_openai_client()

            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts
            )

            embeddings = [item.embedding for item in response.data]

            duration_ms = (time.time() - start_time) * 1000
            log_external_api_call(
                logger,
                service="OpenAI",
                operation="create_embeddings",
                duration_ms=duration_ms,
                success=True,
                batch_size=len(texts),
                model=EMBEDDING_MODEL
            )

            logger.info(f"Created {len(embeddings)} embeddings with OpenAI in {duration_ms:.2f}ms")
            return embeddings

    except Exception as e:
        service = "FastEmbed" if USE_FASTEMBED else "OpenAI"
        logger.error(f"Failed to create embeddings with {service}: {e}")
        log_external_api_call(
            logger,
            service=service,
            operation="create_embeddings",
            success=False,
            error=str(e)
        )
        return []


def create_qdrant_collection(force_recreate: bool = False) -> bool:
    """
    Create or verify Qdrant collection for Physical AI textbook embeddings
    
    Args:
        force_recreate: If True, delete and recreate collection
    
    Returns:
        bool: True if collection is ready, False otherwise
    """
    try:
        client = get_qdrant_client()
        start_time = time.time()
        
        # Check if collection exists
        collections = client.get_collections().collections
        collection_exists = any(col.name == QDRANT_COLLECTION_NAME for col in collections)
        
        if collection_exists:
            if force_recreate:
                logger.info(f"Deleting existing collection: {QDRANT_COLLECTION_NAME}")
                client.delete_collection(collection_name=QDRANT_COLLECTION_NAME)
                collection_exists = False
            else:
                logger.info(f"Collection '{QDRANT_COLLECTION_NAME}' already exists")
                duration_ms = (time.time() - start_time) * 1000
                log_external_api_call(
                    logger,
                    service="Qdrant",
                    operation="verify_collection",
                    duration_ms=duration_ms,
                    success=True
                )
                return True
        
        # Create collection if it doesn't exist
        if not collection_exists:
            logger.info(f"Creating Qdrant collection: {QDRANT_COLLECTION_NAME}")
            client.create_collection(
                collection_name=QDRANT_COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIMENSION,
                    distance=Distance.COSINE
                )
            )
            
            duration_ms = (time.time() - start_time) * 1000
            log_external_api_call(
                logger,
                service="Qdrant",
                operation="create_collection",
                duration_ms=duration_ms,
                success=True,
                collection=QDRANT_COLLECTION_NAME,
                dimension=EMBEDDING_DIMENSION
            )
            logger.info(f"Collection created successfully with {EMBEDDING_DIMENSION}-dim vectors, cosine distance")
        
        return True
    
    except Exception as e:
        logger.error(f"Failed to create Qdrant collection: {e}")
        log_external_api_call(
            logger,
            service="Qdrant",
            operation="create_collection",
            success=False,
            error=str(e)
        )
        return False


def upsert_vectors(
    vectors: List[List[float]],
    payloads: List[Dict[str, Any]],
    ids: Optional[List[str]] = None
) -> int:
    """
    Insert or update vectors in Qdrant collection
    
    Args:
        vectors: List of embedding vectors
        payloads: List of metadata payloads (chapter, lesson, content, etc.)
        ids: Optional list of IDs (generated if not provided)
    
    Returns:
        int: Number of vectors uploaded
    """
    try:
        client = get_qdrant_client()
        start_time = time.time()
        
        # Generate IDs if not provided (use integers for Qdrant)
        if ids is None:
            ids = list(range(len(vectors)))
        
        # Create PointStruct objects
        points = [
            PointStruct(id=id_val, vector=vector, payload=payload)
            for id_val, vector, payload in zip(ids, vectors, payloads)
        ]
        
        # Upsert points in batches
        batch_size = 100
        total_uploaded = 0
        
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            client.upsert(
                collection_name=QDRANT_COLLECTION_NAME,
                points=batch
            )
            total_uploaded += len(batch)
            logger.info(f"Uploaded batch {i // batch_size + 1}: {len(batch)} vectors")
        
        duration_ms = (time.time() - start_time) * 1000
        log_external_api_call(
            logger,
            service="Qdrant",
            operation="upsert_vectors",
            duration_ms=duration_ms,
            success=True,
            vectors_count=total_uploaded
        )
        
        return total_uploaded
    
    except Exception as e:
        logger.error(f"Failed to upsert vectors: {e}")
        log_external_api_call(
            logger,
            service="Qdrant",
            operation="upsert_vectors",
            success=False,
            error=str(e)
        )
        return 0


def search_similar_chunks(
    query_vector: List[float],
    top_k: int = TOP_K_CHUNKS,
    score_threshold: float = SIMILARITY_THRESHOLD
) -> List[Dict[str, Any]]:
    """
    Search for similar chunks using vector similarity
    
    Args:
        query_vector: Query embedding vector
        top_k: Number of results to return
        score_threshold: Minimum similarity score (0-1)
    
    Returns:
        List of dicts with payload and score
    """
    try:
        client = get_qdrant_client()
        start_time = time.time()

        # Use query_points for newer Qdrant client API
        from qdrant_client.models import QueryRequest
        results = client.query_points(
            collection_name=QDRANT_COLLECTION_NAME,
            query=query_vector,
            limit=top_k,
            score_threshold=score_threshold
        ).points
        
        duration_ms = (time.time() - start_time) * 1000
        log_external_api_call(
            logger,
            service="Qdrant",
            operation="search",
            duration_ms=duration_ms,
            success=True,
            results_count=len(results)
        )
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "payload": result.payload,
                "score": result.score
            })
        
        return formatted_results
    
    except Exception as e:
        logger.error(f"Failed to search vectors: {e}")
        log_external_api_call(
            logger,
            service="Qdrant",
            operation="search",
            success=False,
            error=str(e)
        )
        return []


def get_collection_info() -> Optional[Dict[str, Any]]:
    """
    Get information about the Qdrant collection
    
    Returns:
        Dict with collection stats or None if error
    """
    try:
        client = get_qdrant_client()
        collection_info = client.get_collection(collection_name=QDRANT_COLLECTION_NAME)

        # Access the nested structure correctly
        return {
            "name": QDRANT_COLLECTION_NAME,
            "points_count": collection_info.points_count,
            "vectors_count": collection_info.points_count,  # Same as points_count in newer versions
            "status": str(collection_info.status),
            "config": {
                "params": str(collection_info.config.params) if hasattr(collection_info.config, 'params') else None
            }
        }

    except Exception as e:
        logger.error(f"Failed to get collection info: {e}")
        return None
