# Physical AI Textbook - RAG Chatbot Backend

Backend API for the RAG-based chatbot using FastAPI, Qdrant, and OpenAI GPT-4.

## 🎯 Implementation Status: 18/80 Tasks Complete (22.5%)

### ✅ Complete
- **Phase 1**: Setup & Project Structure (100%)
- **Phase 2**: Foundational Infrastructure (100%)
  - Database models and migrations
  - Qdrant Cloud integration
  - OpenAI client setup
  - Rate limiting middleware

### 🚧 In Progress
- **Phase 3**: Embeddings Ingestion (37.5%)
  - ✅ Markdown processor with chunking
  - ⏳ OpenAI embedding service
  - ⏳ Ingestion endpoint

See `IMPLEMENTATION_STATUS.md` for detailed progress.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Neon Postgres database
- Qdrant Cloud account
- OpenAI API key

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```env
DATABASE_URL=postgresql://user:pass@host:5432/dbname
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key
OPENAI_API_KEY=sk-your-openai-key
ENVIRONMENT=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,https://your-site.github.io
```

### 3. Run Database Migrations

```bash
alembic upgrade head
```

### 4. Start Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at: http://localhost:8000
API docs (Swagger): http://localhost:8000/docs

## 📂 Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration and client initialization
│   ├── api/                 # API route handlers
│   │   └── __init__.py
│   ├── models/              # Database and Pydantic models
│   │   ├── chat_history.py  # SQLAlchemy models
│   │   └── schemas.py       # Pydantic request/response schemas
│   ├── services/            # Business logic
│   │   └── embeddings_service.py  # Qdrant operations
│   └── utils/               # Utilities
│       ├── logger.py        # Structured logging
│       └── markdown_processor.py  # MDX parsing & chunking
├── alembic/                 # Database migrations
│   ├── versions/
│   └── env.py
├── requirements.txt
├── .env.example
└── README.md
```

## 🔧 Configuration

### Database Models
- **ChatSession**: Groups related messages
- **ChatMessage**: Individual messages with RAG context

### API Schemas
- Request/response validation with Pydantic
- Automatic OpenAPI documentation

### Services
- **Embeddings Service**: Qdrant vector operations
- **Markdown Processor**: MDX parsing and chunking (512 tokens, 100 overlap)

## 🌐 API Endpoints (Planned)

### Health & Info
- `GET /` - Service status
- `GET /health` - Detailed health check

### Embeddings (In Progress)
- `POST /api/embeddings/ingest` - Ingest book content

### Chat (Pending)
- `POST /api/chat` - General chat query
- `POST /api/chat/selected-text` - Context-specific query
- `GET /api/chat/history/{session_id}` - Get chat history
- `POST /api/chat/clear` - Clear chat history

## 🛠️ Development

### Run Tests
```bash
pytest
```

### Check Logs
Logs are structured JSON for easy parsing:
```json
{
  "timestamp": "2025-01-29T12:00:00Z",
  "level": "INFO",
  "message": "Request processed",
  "endpoint": "/api/chat",
  "duration_ms": 245.3
}
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## 📊 Next Implementation Steps

1. **Complete Embeddings Ingestion** (T019-T023)
   - Add OpenAI embedding batch processing
   - Create ingestion API endpoint
   - Test with book content

2. **Implement RAG Chat** (T024-T033)
   - Vector similarity search
   - GPT-4 response generation
   - Source citation extraction

3. **Build Frontend Integration** (T045-T056)
   - React chatbot component
   - WebSocket or polling for real-time updates
   - Docusaurus theme integration

## 🐛 Troubleshooting

### Database Connection Issues
- Verify DATABASE_URL is correct
- Check Neon dashboard for connection limits
- Test connection: `psql $DATABASE_URL`

### Qdrant Errors
- Verify API key and URL
- Check Qdrant dashboard for collection
- Ensure collection exists before searching

### OpenAI Rate Limits
- Monitor usage in OpenAI dashboard
- Adjust rate limiting in config.py
- Consider caching embeddings

## 📝 License

Part of the Physical AI & Humanoid Robotics Textbook project.
