"""
API routes for chat interactions
Handles general chat, selected text queries, and history management
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from app.config import get_db
from app.models.schemas import (
    ChatRequest,
    SelectedTextChatRequest,
    ChatResponse,
    ChatHistoryResponse,
    ClearHistoryRequest,
    ClearHistoryResponse
)
from app.services.rag_service import generate_rag_response, generate_selected_text_response
from app.services.db_service import (
    get_or_create_session,
    save_message,
    get_session_history,
    clear_session_history
)
from app.utils.logger import setup_logger, log_api_request
from datetime import datetime

router = APIRouter()
logger = setup_logger(__name__)


@router.post("/", response_model=ChatResponse, summary="General chat query")
async def chat(http_request: Request, request: ChatRequest, db: Session = Depends(get_db)):
    """
    Answer general questions about the textbook using RAG
    
    Process:
    1. Retrieve relevant content from Qdrant
    2. Generate answer using GPT-4
    3. Save conversation to database
    4. Return answer with source citations
    """
    log_api_request(logger, "/api/chat", "POST", session_id=request.session_id)
    
    try:
        # Get or create session
        session = get_or_create_session(db, request.session_id)
        
        # Get chat history for context
        history = get_session_history(db, request.session_id, limit=10)
        chat_history = [
            {"role": msg.role, "content": msg.content}
            for msg in history
        ]
        
        # Save user message
        save_message(
            db=db,
            session_id=session.id,
            role="user",
            content=request.message
        )
        
        # Generate RAG response
        response_text, citations = await generate_rag_response(
            user_question=request.message,
            session_id=str(session.id),
            chat_history=chat_history
        )
        
        if response_text is None:
            # Fallback for OpenAI API failures
            response_text = "I'm having trouble answering that question right now. Please try again in a moment."
            citations = []
        
        # Save assistant response
        save_message(
            db=db,
            session_id=session.id,
            role="assistant",
            content=response_text,
            retrieved_chunks=[
                {
                    "chapter": c.chapter,
                    "lesson": c.lesson,
                    "section": c.section_title,
                    "score": c.similarity_score
                }
                for c in citations
            ]
        )
        
        return ChatResponse(
            session_id=str(session.id),
            message=response_text,
            sources=citations,
            timestamp=datetime.utcnow()
        )
    
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        
        # Return graceful error response
        return ChatResponse(
            session_id=request.session_id,
            message="I encountered an error while processing your question. Please try again.",
            sources=[],
            timestamp=datetime.utcnow()
        )


@router.post("/selected-text", response_model=ChatResponse, summary="Selected text query")
async def chat_selected_text(http_request: Request, request: SelectedTextChatRequest, db: Session = Depends(get_db)):
    """
    Answer questions about specific selected text from the textbook
    """
    log_api_request(logger, "/api/chat/selected-text", "POST", session_id=request.session_id)
    
    try:
        # Get or create session
        session = get_or_create_session(db, request.session_id)
        
        # Save user message with selected text
        save_message(
            db=db,
            session_id=session.id,
            role="user",
            content=request.message,
            selected_text=request.selected_text
        )
        
        # Generate response (await async function)
        response_text, citations = await generate_selected_text_response(
            user_question=request.message,
            selected_text=request.selected_text,
            session_id=str(session.id)
        )
        
        if response_text is None:
            response_text = "I'm having trouble answering that. Please try again."
            citations = []
        
        # Save assistant response
        save_message(
            db=db,
            session_id=session.id,
            role="assistant",
            content=response_text
        )
        
        return ChatResponse(
            session_id=str(session.id),
            message=response_text,
            sources=citations,
            timestamp=datetime.utcnow()
        )
    
    except Exception as e:
        logger.error(f"Selected text chat error: {e}")
        
        return ChatResponse(
            session_id=request.session_id,
            message="An error occurred while processing your question about the selected text.",
            sources=[],
            timestamp=datetime.utcnow()
        )


@router.get("/history/{session_id}", response_model=ChatHistoryResponse, summary="Get chat history")
async def get_history(session_id: str, db: Session = Depends(get_db)):
    """
    Retrieve chat history for a session
    """
    log_api_request(logger, f"/api/chat/history/{session_id}", "GET", session_id=session_id)
    
    try:
        # Get session
        from app.models.chat_history import ChatSession
        import uuid
        
        session_uuid = uuid.UUID(session_id)
        session = db.query(ChatSession).filter(ChatSession.id == session_uuid).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get messages
        messages = get_session_history(db, session_id)
        
        from app.models.schemas import ChatMessageSchema
        
        return ChatHistoryResponse(
            session_id=session.id,
            messages=[ChatMessageSchema.model_validate(msg) for msg in messages],
            created_at=session.created_at,
            updated_at=session.updated_at
        )
    
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get history error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history")


@router.post("/clear", response_model=ClearHistoryResponse, summary="Clear chat history")
async def clear_history(http_request: Request, request: ClearHistoryRequest, db: Session = Depends(get_db)):
    """
    Clear chat history for a specific session or all sessions
    """
    log_api_request(logger, "/api/chat/clear", "POST", session_id=request.session_id)
    
    try:
        deleted_sessions, deleted_messages = clear_session_history(
            db=db,
            session_id=request.session_id
        )
        
        if request.session_id:
            message = f"Cleared session {request.session_id}"
        else:
            message = "Cleared all chat history"
        
        return ClearHistoryResponse(
            success=True,
            message=message,
            deleted_sessions=deleted_sessions,
            deleted_messages=deleted_messages
        )
    
    except Exception as e:
        logger.error(f"Clear history error: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear history")
