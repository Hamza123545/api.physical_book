"""
Configuration management for Physical AI Textbook Backend
Handles database connections, API clients, and environment variables
"""
import os
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from qdrant_client import QdrantClient
from openai import OpenAI
from dotenv import load_dotenv
from app.utils.logger import setup_logger

# Load environment variables
load_dotenv()

# Setup logger
logger = setup_logger(__name__)

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.warning("DATABASE_URL not set - using SQLite fallback for development")
    DATABASE_URL = "sqlite:///./physical_ai_textbook.db"

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections after 1 hour
    echo=os.getenv("ENVIRONMENT") == "development"  # Log SQL in development
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base for models
Base = declarative_base()


def get_db():
    """
    Dependency function for FastAPI to get database session
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Qdrant Configuration
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION_NAME = "physical_ai_textbook"

# Initialize Qdrant client (will be None if credentials not provided)
qdrant_client: Optional[QdrantClient] = None

if QDRANT_URL and QDRANT_API_KEY:
    try:
        qdrant_client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=30,  # 30 second timeout for operations
        )
        logger.info("Qdrant client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant client: {e}")
        qdrant_client = None
else:
    logger.warning("Qdrant credentials not provided - vector search will be unavailable")


def get_qdrant_client() -> QdrantClient:
    """
    Dependency function to get Qdrant client
    Raises ValueError if client is not initialized
    """
    if qdrant_client is None:
        raise ValueError("Qdrant client not initialized - check QDRANT_URL and QDRANT_API_KEY")
    return qdrant_client


# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client (for embeddings - still needed)
openai_client: Optional[OpenAI] = None

if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info("OpenAI client initialized successfully (for embeddings)")
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        openai_client = None
else:
    logger.warning("OpenAI API key not provided - LLM features will be unavailable")


def get_openai_client() -> OpenAI:
    """
    Dependency function to get OpenAI client (for embeddings)
    Raises ValueError if client is not initialized
    """
    if openai_client is None:
        raise ValueError("OpenAI client not initialized - check OPENAI_API_KEY")
    return openai_client


# OpenAI Agents SDK Configuration
# Agents SDK uses OPENAI_API_KEY environment variable automatically
# No explicit initialization needed - SDK reads from environment


# Application Configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE") or "10")

# Embedding Configuration
# FastEmbed (local, free) vs OpenAI (paid API)
USE_FASTEMBED = os.getenv("USE_FASTEMBED", "true").lower() == "true"

if USE_FASTEMBED:
    # FastEmbed model: BAAI/bge-small-en-v1.5 (384 dimensions)
    EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSION = 384
    logger.info("Using FastEmbed for local, free embeddings")
else:
    # OpenAI model: text-embedding-3-small (1536 dimensions)
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSION = 1536
    logger.info("Using OpenAI embeddings (API costs apply)")

# RAG Configuration
CHUNK_SIZE = 512  # tokens per chunk
CHUNK_OVERLAP = 100  # token overlap between chunks
TOP_K_CHUNKS = 5  # number of chunks to retrieve
SIMILARITY_THRESHOLD = 0.7  # minimum similarity score

# Chat Configuration
# OpenAI Agents SDK supports:
# - OpenAI models natively (gpt-4-turbo-preview, gpt-4, gpt-4o, gpt-5, etc.)
# - Non-OpenAI models via LiteLLM (litellm/provider/model format)
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4-turbo-preview")

USE_GEMINI = os.getenv("USE_GEMINI", "false").lower() == "true"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if USE_GEMINI:
    if not GEMINI_API_KEY:
        logger.warning("USE_GEMINI=true but GEMINI_API_KEY not set - falling back to OpenAI")
        CHAT_MODEL = "gpt-4-turbo-preview"
    else:
        # Use Gemini via LiteLLM integration (requires openai-agents[litellm])
        # Free tier models (using v1 API, not v1beta):
        # - gemini-2.5-flash (free tier, fast, recommended)
        # - gemini-1.5-flash (free tier, fast)
        # - gemini-1.5-pro (free tier, more capable)
        # Note: GEMINI_API_VERSION=v1 is set in agent_service.py to avoid v1beta issues
        gemini_model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        # Use litellm/ prefix format
        CHAT_MODEL = f"litellm/gemini/{gemini_model_name}"
        logger.info(f"Using FREE Gemini model via LiteLLM (v1 API): {CHAT_MODEL}")

MAX_CHAT_HISTORY = 50  # maximum messages to keep in history per session

# Settings object for easy access in services
class Settings:
    """Application settings accessible throughout the app"""
    CHAT_MODEL = CHAT_MODEL
    USE_GEMINI = USE_GEMINI
    GEMINI_API_KEY = GEMINI_API_KEY
    ENVIRONMENT = ENVIRONMENT

settings = Settings()

logger.info(f"Configuration loaded - Environment: {ENVIRONMENT}")
