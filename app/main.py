"""
Physical AI Textbook Backend - RAG Chatbot
FastAPI application entry point with CORS and middleware configuration
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title="Physical AI Textbook - RAG Chatbot API",
    description="Backend API for RAG-based chatbot with Qdrant vector search and OpenAI GPT-4",
    version="0.1.0",
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
# In development, allow all localhost origins (any port)
# In production, use specific origins from environment
is_development = os.getenv("ENVIRONMENT", "development").lower() == "development"

if is_development:
    # Development: Allow all localhost origins (any port)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
else:
    # Production: Use specific origins
    env_origins_str = os.getenv("CORS_ORIGINS", "")
    env_origins = []
    if env_origins_str:
        # Parse and clean origins - remove paths and trailing slashes
        for origin in env_origins_str.split(","):
            origin = origin.strip()
            if origin:
                # Remove trailing slash
                origin = origin.rstrip("/")
                # Extract just protocol + domain (remove path if present)
                # e.g., "https://hamza123545.github.io/physical-ai-book" -> "https://hamza123545.github.io"
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(origin)
                    # Reconstruct with just scheme and netloc (no path)
                    clean_origin = f"{parsed.scheme}://{parsed.netloc}"
                    env_origins.append(clean_origin)
                except Exception:
                    # Fallback: just use the origin as-is if parsing fails
                    env_origins.append(origin)
    
    # Default production origins (GitHub Pages frontend)
    # IMPORTANT: CORS origin is just protocol + domain, NOT the path
    # Browser sends: https://hamza123545.github.io (not the /physical-ai-book path)
    default_origins = [
        "https://hamza123545.github.io",
    ]
    
    # Combine environment origins with defaults (avoid duplicates)
    all_origins = list(set(env_origins + default_origins))
    
    # Log for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"CORS configuration - Environment: {is_development}, Allowed origins: {all_origins}")
    print(f"CORS allowed origins: {all_origins}")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=all_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=3600,  # Cache preflight for 1 hour
    )


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Physical AI Textbook RAG Chatbot",
        "version": "0.1.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check for monitoring"""
    return {
        "status": "healthy",
        "database": "pending",  # Will update after DB connection
        "qdrant": "pending",    # Will update after Qdrant connection
        "openai": "pending"     # Will update after OpenAI client setup
    }


# API routes
from app.api import embeddings_routes, chat_routes, chatkit_routes, content_routes
from app.api.user import routes as user_routes
from app.auth import routes as auth_routes

app.include_router(embeddings_routes.router, prefix="/api/embeddings", tags=["embeddings"])
app.include_router(chat_routes.router, prefix="/api/chat", tags=["chat"])
# ChatKit session endpoint (minimal backend needed for client_secret generation)
app.include_router(chatkit_routes.router, prefix="/api/chatkit", tags=["chatkit"])
# Authentication routes
app.include_router(auth_routes.router, prefix="/api/auth", tags=["authentication"])
# User background routes
app.include_router(user_routes.router, prefix="/api/user", tags=["user"])
# Content personalization routes
app.include_router(content_routes.router, prefix="/api/content", tags=["content"])
