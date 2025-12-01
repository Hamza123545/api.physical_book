"""
Physical AI Textbook Backend - RAG Chatbot
FastAPI application entry point with CORS and middleware configuration
"""
import os
from fastapi import FastAPI, Request
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
    redirect_slashes=False,  # Disable automatic trailing slash redirects
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS - MUST be added before routes
# In development, allow all localhost origins (any port)
# In production, use specific origins from environment
is_development = os.getenv("ENVIRONMENT", "development").lower() == "development"

# Parse CORS origins
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
    "http://localhost:3000",
    "http://localhost:3001",
]

# Combine environment origins with defaults (avoid duplicates)
all_origins = list(set(env_origins + default_origins))

# Log for debugging
import logging
logger = logging.getLogger(__name__)
logger.info(f"CORS configuration - Environment: {is_development}, Allowed origins: {all_origins}")
print(f"CORS allowed origins: {all_origins}")

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
    # Production: Use specific origins with regex support for GitHub Pages
    # Allow both exact match and any subdomain/path under GitHub Pages
    app.add_middleware(
        CORSMiddleware,
        allow_origins=all_origins,
        allow_origin_regex=r"https://hamza123545\.github\.io.*",  # Allow any path under GitHub Pages
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
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
    """Detailed health check for monitoring and Docker health checks"""
    from app.config import engine, QDRANT_CLIENT
    from sqlalchemy import text
    
    health_status = {
        "status": "healthy",
        "service": "Physical AI Textbook RAG Chatbot",
        "version": "0.1.0"
    }
    
    # Check database connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)[:50]}"
        health_status["status"] = "degraded"
    
    # Check Qdrant connection
    try:
        if QDRANT_CLIENT:
            QDRANT_CLIENT.get_collections()
            health_status["qdrant"] = "connected"
        else:
            health_status["qdrant"] = "not_configured"
    except Exception as e:
        health_status["qdrant"] = f"error: {str(e)[:50]}"
        health_status["status"] = "degraded"
    
    return health_status



# Middleware to add CORS headers to all responses (backup for CORSMiddleware)
# This runs AFTER CORSMiddleware to ensure headers are always set
@app.middleware("http")
async def add_cors_headers_backup(request: Request, call_next):
    """Add CORS headers to all responses as backup"""
    import re
    from urllib.parse import urlparse
    
    response = await call_next(request)
    
    # Only add headers if not already set by CORSMiddleware
    if "Access-Control-Allow-Origin" not in response.headers:
        # Get origin from request
        origin = request.headers.get("origin", "")
        
        # Determine allowed origin
        allowed_origin = None
        
        # Check if origin is in allowed list
        if origin in all_origins:
            allowed_origin = origin
        # Check if origin matches GitHub Pages pattern
        elif origin and re.match(r"https://hamza123545\.github\.io.*", origin):
            # Extract base origin (without path)
            parsed = urlparse(origin)
            allowed_origin = f"{parsed.scheme}://{parsed.netloc}"
        # Check if origin is localhost (for development)
        elif origin and re.match(r"https?://(localhost|127\.0\.0\.1)(:\d+)?", origin):
            allowed_origin = origin
        
        # If origin is allowed, add CORS headers
        if allowed_origin:
            response.headers["Access-Control-Allow-Origin"] = allowed_origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Expose-Headers"] = "*"
    
    return response


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


# Explicit OPTIONS handler for all API routes (AFTER routes are included)
# This handles CORS preflight requests explicitly as fallback
@app.options("/api/{full_path:path}")
async def options_api_handler(full_path: str, request: Request):
    """Handle CORS preflight requests for API routes"""
    from fastapi import Response
    import re
    
    # Get origin from request
    origin = request.headers.get("origin", "")
    
    # Log for debugging
    logger.info(f"OPTIONS request for /api/{full_path} from origin: {origin}")
    print(f"OPTIONS request for /api/{full_path} from origin: {origin}, Allowed origins: {all_origins}")
    
    # Determine allowed origin
    allowed_origin = None
    
    # Check if origin is in allowed list
    if origin in all_origins:
        allowed_origin = origin
    # Check if origin matches GitHub Pages pattern
    elif origin and re.match(r"https://hamza123545\.github\.io.*", origin):
        # Extract base origin (without path)
        from urllib.parse import urlparse
        parsed = urlparse(origin)
        allowed_origin = f"{parsed.scheme}://{parsed.netloc}"
    # Check if origin is localhost (for development)
    elif origin and re.match(r"https?://(localhost|127\.0\.0\.1)(:\d+)?", origin):
        allowed_origin = origin
    
    # If no match, use default GitHub Pages origin
    if not allowed_origin:
        allowed_origin = "https://hamza123545.github.io"
    
    logger.info(f"OPTIONS response: 200 OK, Allowed-Origin: {allowed_origin}")
    print(f"OPTIONS response: 200 OK, Allowed-Origin: {allowed_origin}")
    
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": allowed_origin,
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "3600",
        }
    )
