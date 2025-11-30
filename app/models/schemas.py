"""
Pydantic schemas for request/response validation
Provides type safety and automatic API documentation
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


# Chat Request/Response Schemas

class ChatRequest(BaseModel):
    """Request schema for general chat queries"""
    session_id: str = Field(..., description="Unique session identifier")
    message: str = Field(..., min_length=1, max_length=2000, description="User's question")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "What is ROS 2?"
            }
        }


class SelectedTextChatRequest(BaseModel):
    """Request schema for selected text queries"""
    session_id: str = Field(..., description="Unique session identifier")
    message: str = Field(..., min_length=1, max_length=2000, description="User's question about selected text")
    selected_text: str = Field(..., min_length=1, max_length=5000, description="Text selected by user for context")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Can you explain this in simpler terms?",
                "selected_text": "ROS 2 uses DDS for inter-process communication..."
            }
        }


class SourceCitation(BaseModel):
    """Source citation for RAG responses"""
    chapter: str = Field(..., description="Chapter number (e.g., '01')")
    lesson: str = Field(..., description="Lesson number (e.g., '01')")
    section_title: str = Field(..., description="Section title")
    file_path: str = Field(..., description="File path to source document")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0-1)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "chapter": "01",
                "lesson": "01",
                "section_title": "Introduction to ROS 2",
                "file_path": "docs/chapter-01/lesson-01.md",
                "similarity_score": 0.92
            }
        }


class ChatResponse(BaseModel):
    """Response schema for chat queries"""
    session_id: str = Field(..., description="Session identifier")
    message: str = Field(..., description="Assistant's response")
    sources: List[SourceCitation] = Field(default_factory=list, description="Source citations")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "ROS 2 (Robot Operating System 2) is a flexible framework for writing robot software...",
                "sources": [
                    {
                        "chapter": "01",
                        "lesson": "01",
                        "section_title": "Introduction to ROS 2",
                        "file_path": "docs/chapter-01/lesson-01.md",
                        "similarity_score": 0.92
                    }
                ],
                "timestamp": "2025-01-29T12:00:00Z"
            }
        }


# Chat History Schemas

class ChatMessageSchema(BaseModel):
    """Schema for individual chat message"""
    id: UUID
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str
    selected_text: Optional[str] = None
    retrieved_chunks: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    """Response schema for chat history"""
    session_id: UUID
    messages: List[ChatMessageSchema]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ClearHistoryRequest(BaseModel):
    """Request schema for clearing chat history"""
    session_id: Optional[str] = Field(None, description="Session ID to clear (omit to clear all sessions)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class ClearHistoryResponse(BaseModel):
    """Response schema for clearing chat history"""
    success: bool
    message: str
    deleted_sessions: int = Field(0, description="Number of sessions deleted")
    deleted_messages: int = Field(0, description="Number of messages deleted")


# Embeddings Schemas

class EmbeddingIngestRequest(BaseModel):
    """Request schema for embeddings ingestion"""
    force_reindex: bool = Field(False, description="Force re-indexing even if collection exists")
    
    class Config:
        json_schema_extra = {
            "example": {
                "force_reindex": False
            }
        }


class EmbeddingIngestResponse(BaseModel):
    """Response schema for embeddings ingestion"""
    success: bool
    message: str
    chunks_processed: int = Field(0, description="Number of chunks processed")
    vectors_created: int = Field(0, description="Number of vectors created in Qdrant")
    duration_seconds: float = Field(0.0, description="Total processing time")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Embeddings ingestion completed successfully",
                "chunks_processed": 450,
                "vectors_created": 450,
                "duration_seconds": 127.5
            }
        }


# Health Check Schema

class HealthCheckResponse(BaseModel):
    """Response schema for health check"""
    status: str = Field(..., description="Overall status: 'healthy' or 'unhealthy'")
    database: str = Field(..., description="Database connection status")
    qdrant: str = Field(..., description="Qdrant connection status")
    openai: str = Field(..., description="OpenAI client status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "database": "connected",
                "qdrant": "connected",
                "openai": "configured"
            }
        }
