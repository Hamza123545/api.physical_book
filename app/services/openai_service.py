"""
OpenAI service for embeddings (still uses OpenAI client)
Chat completions now handled by agent_service.py using OpenAI Agents SDK
"""
from typing import List, Optional
from app.config import get_openai_client, EMBEDDING_MODEL
from app.utils.logger import setup_logger, log_external_api_call
import time

logger = setup_logger(__name__)


def create_embeddings(texts: List[str]) -> Optional[List[List[float]]]:
    """
    Create embeddings using OpenAI (for vector search)
    
    Args:
        texts: List of text strings to embed
    
    Returns:
        List of embedding vectors or None if failed
    """
    try:
        client = get_openai_client()
        start_time = time.time()
        
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts
        )
        
        duration_ms = (time.time() - start_time) * 1000
        
        embeddings = [item.embedding for item in response.data]
        
        log_external_api_call(
            logger,
            service="OpenAI",
            operation="embeddings",
            duration_ms=duration_ms,
            success=True,
            model=EMBEDDING_MODEL,
            tokens_used=response.usage.total_tokens if hasattr(response, 'usage') else 0
        )
        
        logger.info(f"Created {len(embeddings)} embeddings: {duration_ms:.2f}ms")
        
        return embeddings
    
    except Exception as e:
        logger.error(f"Failed to create embeddings: {e}")
        log_external_api_call(
            logger,
            service="OpenAI",
            operation="embeddings",
            success=False,
            error=str(e)
        )
        return None
