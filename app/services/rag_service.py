"""
RAG (Retrieval-Augmented Generation) service
Orchestrates vector search, context retrieval, and OpenAI Agents SDK response generation
"""
from typing import List, Dict, Any, Optional, Tuple
from app.services.embeddings_service import create_embeddings_batch, search_similar_chunks
from app.services.agent_service import create_rag_completion_with_agent, create_selected_text_completion_with_agent
from app.models.schemas import SourceCitation
from app.utils.logger import setup_logger
import time

logger = setup_logger(__name__)


def extract_source_citations(retrieved_chunks: List[Dict[str, Any]]) -> List[SourceCitation]:
    """
    Extract source citations from retrieved chunks
    
    Args:
        retrieved_chunks: List of chunks with payload and score
    
    Returns:
        List of SourceCitation objects
    """
    citations = []
    
    for chunk in retrieved_chunks:
        payload = chunk.get('payload', {})
        score = chunk.get('score', 0.0)
        
        citation = SourceCitation(
            chapter=payload.get('chapter', 'unknown'),
            lesson=payload.get('lesson', 'unknown'),
            section_title=payload.get('section_title', 'Unknown Section'),
            file_path=payload.get('file_path', ''),
            similarity_score=score
        )
        citations.append(citation)
    
    return citations


async def generate_rag_response(
    user_question: str,
    session_id: str,
    chat_history: Optional[List[Dict[str, str]]] = None
) -> Tuple[Optional[str], List[SourceCitation]]:
    """
    Generate a RAG-enhanced response to user's question

    Process:
    1. Create embedding for user question
    2. Search for similar chunks in Qdrant
    3. Generate response using GPT-4 with context
    4. Extract source citations

    Args:
        user_question: User's question
        session_id: Session identifier for logging
        chat_history: Optional previous messages

    Returns:
        Tuple of (response_text, source_citations)
    """
    start_time = time.time()

    try:
        # Step 1: Create embedding for user question
        logger.info(f"[{session_id}] Creating embedding for question")
        
        question_embeddings = create_embeddings_batch([user_question])
        
        if not question_embeddings:
            logger.error(f"[{session_id}] Failed to create question embedding")
            return None, []
        
        question_vector = question_embeddings[0]
        
        # Step 2: Search for similar chunks
        logger.info(f"[{session_id}] Searching for relevant content")
        
        retrieved_chunks = search_similar_chunks(
            query_vector=question_vector,
            top_k=5,
            score_threshold=0.7
        )
        
        if not retrieved_chunks:
            logger.warning(f"[{session_id}] No relevant content found")
            return "I couldn't find relevant information in the textbook to answer your question. Could you rephrase or ask something else?", []
        
        logger.info(f"[{session_id}] Found {len(retrieved_chunks)} relevant chunks")
        
        # Step 3: Extract citations
        citations = extract_source_citations(retrieved_chunks)
        
        # Step 4: Generate response using OpenAI Agents SDK
        logger.info(f"[{session_id}] Generating response with OpenAI Agents SDK")

        response_text = await create_rag_completion_with_agent(
            user_question=user_question,
            retrieved_chunks=retrieved_chunks,
            chat_history=chat_history
        )
        
        if not response_text:
            logger.error(f"[{session_id}] Failed to generate response")
            return "I'm having trouble generating a response right now. Please try again.", citations
        
        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"[{session_id}] RAG response generated in {duration_ms:.2f}ms")
        
        return response_text, citations
    
    except Exception as e:
        logger.error(f"[{session_id}] RAG generation failed: {e}")
        return "An error occurred while processing your question. Please try again.", []


async def generate_selected_text_response(
    user_question: str,
    selected_text: str,
    session_id: str
) -> Tuple[Optional[str], List[SourceCitation]]:
    """
    Generate response for a question about selected text
    
    Args:
        user_question: User's question about the selected text
        selected_text: Text selected by user
        session_id: Session identifier
    
    Returns:
        Tuple of (response_text, source_citations)
    """
    start_time = time.time()
    
    try:
        # Create embedding for selected text to find context
        logger.info(f"[{session_id}] Creating embedding for selected text")
        
        text_embeddings = create_embeddings_batch([selected_text])
        
        if not text_embeddings:
            logger.error(f"[{session_id}] Failed to create text embedding")
            return None, []
        
        text_vector = text_embeddings[0]
        
        # Search for similar chunks (to find source context)
        retrieved_chunks = search_similar_chunks(
            query_vector=text_vector,
            top_k=3,
            score_threshold=0.8
        )
        
        # Extract citations
        citations = extract_source_citations(retrieved_chunks)
        
        # Generate response using OpenAI Agents SDK (await async function)
        logger.info(f"[{session_id}] Generating selected text response with OpenAI Agents SDK")
        
        response_text = await create_selected_text_completion_with_agent(
            user_question=user_question,
            selected_text=selected_text
        )
        
        if not response_text:
            logger.error(f"[{session_id}] Failed to generate selected text response")
            return "I'm having trouble answering that. Please try again.", citations
        
        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"[{session_id}] Selected text response generated in {duration_ms:.2f}ms")
        
        return response_text, citations
    
    except Exception as e:
        logger.error(f"[{session_id}] Selected text response failed: {e}")
        return "An error occurred. Please try again.", []
