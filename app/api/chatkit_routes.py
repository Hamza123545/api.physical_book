"""
ChatKit session management routes
Provides OpenAI ChatKit client secret generation
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
from openai import OpenAI
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)

# OpenAI client for ChatKit session management
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class ChatKitSessionRequest(BaseModel):
    """Request model for ChatKit session creation"""
    existing_session: Optional[str] = None


class ChatKitSessionResponse(BaseModel):
    """Response model for ChatKit session"""
    client_secret: str
    session_id: str


@router.post("/session", response_model=ChatKitSessionResponse)
async def create_chatkit_session(request: ChatKitSessionRequest):
    """
    Create or refresh a ChatKit client session

    ChatKit requires a client secret for authentication.
    This endpoint generates the secret using OpenAI's ChatKit API.

    Supports two modes:
    1. ChatKit Workflow (if CHATKIT_WORKFLOW_ID is set): Uses OpenAI ChatKit workflow
    2. Custom Backend (default): Uses custom backend RAG pipeline

    Returns:
        ChatKitSessionResponse with client_secret and session_id
    """
    try:
        import uuid
        
        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        
        # Check if ChatKit Workflow ID is configured
        workflow_id = os.getenv("CHATKIT_WORKFLOW_ID")
        
        if workflow_id:
            # Option 1: Use OpenAI ChatKit Workflow
            try:
                logger.info(f"Creating ChatKit session with workflow: {workflow_id}")
                
                # Create session with workflow
                # Note: This requires OpenAI ChatKit API access
                # Uncomment when you have a workflow ID:
                # response = openai_client.chatkit.sessions.create(
                #     workflow_id=workflow_id,
                #     metadata={"session_id": session_id}
                # )
                # client_secret = response.client_secret
                
                # For now, use placeholder (replace with actual API call above)
                logger.warning("ChatKit workflow configured but API call commented out. Using fallback.")
                client_secret = f"chatkit_workflow_{session_id}"
                
            except Exception as workflow_error:
                logger.error(f"Failed to create ChatKit workflow session: {workflow_error}")
                # Fallback to custom backend
                client_secret = f"chatkit_session_{session_id}"
        else:
            # Option 2: Custom Backend (default)
            # ChatKit SDK will use custom backend via /api/chatkit/message
            logger.info("Using custom backend mode (no workflow ID configured)")
            client_secret = f"chatkit_session_{session_id}"

        logger.info(f"Created ChatKit session: {session_id}")

        return ChatKitSessionResponse(
            client_secret=client_secret,
            session_id=session_id
        )

    except Exception as e:
        logger.error(f"Failed to create ChatKit session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create ChatKit session: {str(e)}"
        )


@router.post("/message")
async def handle_chatkit_message(message: dict):
    """
    Handle ChatKit message proxy

    ChatKit sends messages to this endpoint, which forwards them
    to our RAG pipeline and returns the response.

    This allows ChatKit UI to work with our existing RAG backend.
    """
    try:
        # Extract message from ChatKit payload
        user_message = message.get("content", "")
        session_id = message.get("session_id", "")

        logger.info(f"ChatKit message received: session={session_id}")

        # Import our RAG service
        from app.services.rag_service import generate_rag_response

        # Generate RAG response
        response_text, citations = await generate_rag_response(
            user_question=user_message,
            session_id=session_id,
            chat_history=[]  # ChatKit manages history
        )

        # Format response for ChatKit
        return {
            "content": response_text,
            "sources": [
                {
                    "title": f"Chapter {c.chapter}, Lesson {c.lesson}",
                    "description": c.section_title,
                    "similarity": c.similarity_score
                }
                for c in citations
            ]
        }

    except Exception as e:
        logger.error(f"ChatKit message handler error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process message: {str(e)}"
        )
