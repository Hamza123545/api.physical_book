"""
Hugging Face Spaces Entry Point
This file is used by Hugging Face Spaces to start the FastAPI application
"""

import os
import uvicorn

if __name__ == "__main__":
    # Hugging Face Spaces sets PORT environment variable
    port = int(os.getenv("PORT", 7860))
    host = os.getenv("HOST", "0.0.0.0")
    
    # Start the FastAPI app
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        workers=1,
        log_level="info"
    )

