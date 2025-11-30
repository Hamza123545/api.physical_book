"""
Database service for chat history management
Handles saving and retrieving chat sessions and messages
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
import uuid
from datetime import datetime
from app.models.chat_history import ChatSession, ChatMessage
from app.utils.logger import setup_logger, log_db_operation
import time

logger = setup_logger(__name__)


def get_or_create_session(db: Session, session_id: str, user_id: Optional[str] = None) -> ChatSession:
    """
    Get existing session or create new one
    
    Args:
        db: Database session
        session_id: Session identifier
        user_id: Optional user identifier
    
    Returns:
        ChatSession object
    """
    start_time = time.time()
    
    try:
        # Try to parse as UUID
        try:
            session_uuid = uuid.UUID(session_id)
        except ValueError:
            # If not valid UUID, create new session with provided ID as string reference
            session_uuid = uuid.uuid4()
        
        # Check if session exists
        session = db.query(ChatSession).filter(ChatSession.id == session_uuid).first()
        
        if session:
            # Update timestamp
            session.updated_at = datetime.utcnow()
            db.commit()
            
            duration_ms = (time.time() - start_time) * 1000
            log_db_operation(logger, "get_session", "chat_sessions", duration_ms=duration_ms)
            
            return session
        
        # Create new session
        session = ChatSession(
            id=session_uuid,
            user_id=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        duration_ms = (time.time() - start_time) * 1000
        log_db_operation(logger, "create_session", "chat_sessions", duration_ms=duration_ms)
        
        logger.info(f"Created new chat session: {session.id}")
        return session
    
    except Exception as e:
        logger.error(f"Failed to get/create session: {e}")
        db.rollback()
        raise


def save_message(
    db: Session,
    session_id: uuid.UUID,
    role: str,
    content: str,
    selected_text: Optional[str] = None,
    retrieved_chunks: Optional[List[dict]] = None
) -> ChatMessage:
    """
    Save a chat message to database
    
    Args:
        db: Database session
        session_id: Session UUID
        role: 'user' or 'assistant'
        content: Message content
        selected_text: Optional selected text for context
        retrieved_chunks: Optional RAG context chunks
    
    Returns:
        ChatMessage object
    """
    start_time = time.time()
    
    try:
        message = ChatMessage(
            id=uuid.uuid4(),
            session_id=session_id,
            role=role,
            content=content,
            selected_text=selected_text,
            retrieved_chunks=retrieved_chunks,
            created_at=datetime.utcnow()
        )
        
        db.add(message)
        db.commit()
        db.refresh(message)
        
        duration_ms = (time.time() - start_time) * 1000
        log_db_operation(logger, "insert_message", "chat_messages", duration_ms=duration_ms)
        
        return message
    
    except Exception as e:
        logger.error(f"Failed to save message: {e}")
        db.rollback()
        raise


def get_session_history(db: Session, session_id: str, limit: int = 50) -> List[ChatMessage]:
    """
    Get chat history for a session
    
    Args:
        db: Database session
        session_id: Session identifier
        limit: Maximum messages to return
    
    Returns:
        List of ChatMessage objects
    """
    start_time = time.time()
    
    try:
        # Parse session ID
        try:
            session_uuid = uuid.UUID(session_id)
        except ValueError:
            logger.warning(f"Invalid session ID format: {session_id}")
            return []
        
        # Query messages
        messages = db.query(ChatMessage)\
            .filter(ChatMessage.session_id == session_uuid)\
            .order_by(ChatMessage.created_at)\
            .limit(limit)\
            .all()
        
        duration_ms = (time.time() - start_time) * 1000
        log_db_operation(logger, "select_messages", "chat_messages", duration_ms=duration_ms)
        
        return messages
    
    except Exception as e:
        logger.error(f"Failed to get session history: {e}")
        return []


def clear_session_history(db: Session, session_id: Optional[str] = None) -> tuple[int, int]:
    """
    Clear chat history for a session or all sessions
    
    Args:
        db: Database session
        session_id: Optional session ID (if None, clears all)
    
    Returns:
        Tuple of (deleted_sessions, deleted_messages)
    """
    start_time = time.time()
    
    try:
        if session_id:
            # Clear specific session
            try:
                session_uuid = uuid.UUID(session_id)
            except ValueError:
                logger.warning(f"Invalid session ID: {session_id}")
                return 0, 0
            
            # Count messages before deletion
            message_count = db.query(ChatMessage)\
                .filter(ChatMessage.session_id == session_uuid)\
                .count()
            
            # Delete session (messages cascade)
            deleted_sessions = db.query(ChatSession)\
                .filter(ChatSession.id == session_uuid)\
                .delete()
            
            db.commit()
            
            duration_ms = (time.time() - start_time) * 1000
            log_db_operation(logger, "delete_session", "chat_sessions", duration_ms=duration_ms)
            
            return deleted_sessions, message_count
        
        else:
            # Clear all sessions
            message_count = db.query(ChatMessage).count()
            session_count = db.query(ChatSession).count()
            
            db.query(ChatMessage).delete()
            db.query(ChatSession).delete()
            db.commit()
            
            duration_ms = (time.time() - start_time) * 1000
            log_db_operation(logger, "delete_all_sessions", "chat_sessions", duration_ms=duration_ms)
            
            return session_count, message_count
    
    except Exception as e:
        logger.error(f"Failed to clear history: {e}")
        db.rollback()
        return 0, 0
