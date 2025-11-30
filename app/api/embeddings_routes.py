"""
API routes for embeddings ingestion
Handles batch processing of textbook content into Qdrant
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.models.schemas import EmbeddingIngestRequest, EmbeddingIngestResponse
from app.services.embeddings_service import (
    create_qdrant_collection,
    create_embeddings_batch,
    upsert_vectors
)
from app.utils.markdown_processor import (
    find_all_lesson_files,
    process_document_to_chunks
)
from app.utils.logger import setup_logger
import time
import os

router = APIRouter()
logger = setup_logger(__name__)
limiter = Limiter(key_func=get_remote_address)


@router.post("/ingest", response_model=EmbeddingIngestResponse)
@limiter.limit("1/hour")  # Limit ingestion to once per hour
async def ingest_embeddings(http_request: Request, request: EmbeddingIngestRequest):
    """
    Ingest all textbook lessons into Qdrant vector database
    
    This endpoint:
    1. Finds all lesson files in book-source/docs/
    2. Chunks each lesson (512 tokens, 100 overlap)
    3. Creates embeddings using OpenAI
    4. Stores vectors in Qdrant with metadata
    
    Rate limited to 1/hour to prevent accidental re-ingestion
    """
    start_time = time.time()
    
    try:
        # Step 1: Create or verify Qdrant collection
        logger.info("Step 1: Creating/verifying Qdrant collection...")
        collection_ready = create_qdrant_collection(force_recreate=request.force_reindex)
        
        if not collection_ready:
            raise HTTPException(
                status_code=500,
                detail="Failed to create Qdrant collection"
            )
        
        # Step 2: Find all lesson files
        logger.info("Step 2: Finding lesson files...")
        docs_dir = os.path.join(os.getcwd(), "..", "book-source", "docs")
        
        # Check if docs directory exists
        if not os.path.exists(docs_dir):
            # Try alternative path
            docs_dir = os.path.join(os.getcwd(), "book-source", "docs")
        
        if not os.path.exists(docs_dir):
            raise HTTPException(
                status_code=404,
                detail=f"Documentation directory not found: {docs_dir}"
            )
        
        lesson_files = find_all_lesson_files(docs_dir)
        
        if not lesson_files:
            return EmbeddingIngestResponse(
                success=True,
                message="No lesson files found to process",
                chunks_processed=0,
                vectors_created=0,
                duration_seconds=time.time() - start_time
            )
        
        logger.info(f"Found {len(lesson_files)} lesson files")
        
        # Step 3: Process all documents into chunks
        logger.info("Step 3: Processing documents into chunks...")
        all_chunks = []
        
        for file_path in lesson_files:
            try:
                chunks = process_document_to_chunks(file_path)
                all_chunks.extend(chunks)
                logger.info(f"Processed {file_path}: {len(chunks)} chunks")
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                continue
        
        if not all_chunks:
            return EmbeddingIngestResponse(
                success=True,
                message="No valid chunks extracted from lessons",
                chunks_processed=0,
                vectors_created=0,
                duration_seconds=time.time() - start_time
            )
        
        logger.info(f"Total chunks created: {len(all_chunks)}")
        
        # Step 4: Create embeddings in batches
        logger.info("Step 4: Creating embeddings with OpenAI...")
        batch_size = 100  # OpenAI allows up to 2048 inputs per request
        all_vectors = []
        
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i:i + batch_size]
            texts = [chunk['content'] for chunk in batch]
            
            embeddings = create_embeddings_batch(texts)
            
            if not embeddings:
                logger.error(f"Failed to create embeddings for batch {i // batch_size + 1}")
                continue
            
            all_vectors.extend(embeddings)
            logger.info(f"Created embeddings for batch {i // batch_size + 1}/{(len(all_chunks) + batch_size - 1) // batch_size}")
        
        if not all_vectors:
            raise HTTPException(
                status_code=500,
                detail="Failed to create any embeddings"
            )
        
        # Step 5: Prepare payloads and upsert to Qdrant
        logger.info("Step 5: Upserting vectors to Qdrant...")
        payloads = []
        
        for chunk in all_chunks:
            payload = {
                'chapter': chunk['chapter'],
                'lesson': chunk['lesson'],
                'section_title': chunk['section_title'],
                'content': chunk['content'],
                'file_path': chunk['file_path'],
                'chunk_index': chunk['chunk_index'],
                'cefr_level': chunk['cefr_level']
            }
            payloads.append(payload)
        
        vectors_uploaded = upsert_vectors(
            vectors=all_vectors,
            payloads=payloads
        )
        
        duration_seconds = time.time() - start_time
        
        logger.info(f"Ingestion complete: {vectors_uploaded} vectors in {duration_seconds:.2f}s")
        
        return EmbeddingIngestResponse(
            success=True,
            message=f"Successfully ingested {len(lesson_files)} lessons into Qdrant",
            chunks_processed=len(all_chunks),
            vectors_created=vectors_uploaded,
            duration_seconds=duration_seconds
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}"
        )


@router.get("/status")
async def get_ingestion_status():
    """
    Get current status of the embeddings collection
    """
    try:
        from app.services.embeddings_service import get_collection_info
        
        info = get_collection_info()
        
        if info is None:
            return {
                "status": "not_initialized",
                "message": "Collection does not exist yet. Run /ingest to create it."
            }
        
        return {
            "status": "ready",
            "collection": info
        }
    
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status: {str(e)}"
        )
