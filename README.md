# 🧠 Knowledge Base RAG Backend

A production-ready unified knowledge base API for document processing, vectorization, and intelligent search using RAG (Retrieval-Augmented Generation).

![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 🌟 Features

| Feature | Description |
|---------|-------------|
| 📄 **Document Upload** | Support for PDF, DOCX, PPTX, XLSX, images, and more |
| 🔍 **Intelligent Processing** | Uses [Docling](https://github.com/docling-project/docling) for advanced document parsing |
| 🔒 **PII Protection** | Automatic detection and redaction using [LangExtract](https://github.com/google/langextract) |
| 🌲 **Reasoning-based RAG** | [PageIndex](https://github.com/VectifyAI/PageIndex) for human-like document retrieval |
| 🎯 **Vector Search** | [Pinecone](https://www.pinecone.io/) for semantic similarity search |
| 🤖 **Agent Integration** | Query your knowledge base with AI agents |
| 📊 **Monitoring** | Prometheus + Grafana for metrics and dashboards |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend App                             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Documents  │  │   Search    │  │   Agents    │              │
│  │    API      │  │    API      │  │    API      │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Docling   │    │  Pinecone   │    │   OpenAI    │
│  (Parsing)  │    │  (Vectors)  │    │   (LLM)     │
└─────────────┘    └─────────────┘    └─────────────┘
         │
         ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ LangExtract │    │  PageIndex  │    │    Redis    │
│   (PII)     │    │ (Tree RAG)  │    │  (Cache)    │
└─────────────┘    └─────────────┘    └─────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12 or 3.13
- Docker & Docker Compose (optional)
- API Keys (see below)

### Required API Keys

| Service | Purpose | Get Key |
|---------|---------|---------|
| **OpenAI** | LLM & PageIndex | [platform.openai.com](https://platform.openai.com/api-keys) |
| **Pinecone** | Vector Database | [app.pinecone.io](https://app.pinecone.io/) |
| **Google** | LangExtract PII | [aistudio.google.com](https://aistudio.google.com/app/apikey) |

---

## 📦 Installation

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-org/knowledge-base-backend.git
cd knowledge-base-backend

# Configure environment
cp .env.example .env
# Edit .env and add your API keys

# Start all services
docker-compose up -d

# With monitoring (Prometheus + Grafana)
docker-compose --profile monitoring up -d
```

### Option 2: Local Development

```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Install PageIndex from GitHub
pip install git+https://github.com/VectifyAI/PageIndex.git

# Configure environment
cp .env.example .env
# Edit .env and add your API keys

# Start Redis (required for background tasks)
docker run -d -p 6379:6379 redis:7-alpine

# Run the API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## ⚙️ Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# Required API Keys
OPENAI_API_KEY=sk-your-openai-api-key
PINECONE_API_KEY=your-pinecone-api-key
GOOGLE_API_KEY=your-google-api-key

# Pinecone Settings
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=knowledge-base

# Model Settings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
LLM_MODEL=gpt-4o-mini

# See .env.example for all options
```

### Key Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model |
| `LLM_MODEL` | `gpt-4o-mini` | OpenAI model for RAG |
| `CHUNK_SIZE` | `1000` | Document chunk size |
| `TOP_K_RESULTS` | `5` | Search results count |
| `PII_DETECTION_ENABLED` | `true` | Enable PII protection |

---

## 📡 API Endpoints

### Base URL
```
http://localhost:8000
```

### Health Check
```http
GET /health
```

### Documents

```http
# Upload a document
POST /api/v1/documents/upload
Content-Type: multipart/form-data
file: <your-file>

# List documents
GET /api/v1/documents

# Get document details
GET /api/v1/documents/{document_id}

# Delete document
DELETE /api/v1/documents/{document_id}

# Get processing status
GET /api/v1/documents/{document_id}/status
```

### Search

```http
# Semantic search
POST /api/v1/search
Content-Type: application/json

{
  "query": "What are the key findings?",
  "top_k": 5,
  "use_pageindex": false
}

# Reasoning-based search (PageIndex)
POST /api/v1/search
Content-Type: application/json

{
  "query": "What are the key findings?",
  "top_k": 5,
  "use_pageindex": true
}
```

### Agent/Chat

```http
# Ask a question
POST /api/v1/agents/query
Content-Type: application/json

{
  "query": "Summarize the Q3 financial report",
  "include_sources": true
}
```

### API Documentation

- **Swagger UI**: http://localhost:8000/docs (debug mode only)
- **ReDoc**: http://localhost:8000/redoc (debug mode only)

---

## 🔄 Document Processing Pipeline

```
1. Upload Document
       │
       ▼
2. Docling Parsing
   - Text extraction
   - Table detection
   - Image extraction
   - Layout analysis
       │
       ▼
3. PII Detection (LangExtract)
   - Passwords
   - API keys
   - Credit cards
   - SSN, emails, phones
       │
       ▼
4. Chunking
   - Split into chunks
   - Preserve context
       │
       ▼
5. Embedding Generation
   - sentence-transformers
       │
       ▼
6. Vector Storage (Pinecone)
       │
       ▼
7. PageIndex Tree (Optional)
   - Hierarchical index
   - Reasoning-based retrieval
```

---

## 🐳 Docker Services

| Service | Port | Description |
|---------|------|-------------|
| `api` | 8000 | FastAPI backend |
| `celery-worker` | - | Background tasks |
| `celery-beat` | - | Scheduled tasks |
| `redis` | 6379 | Message broker & cache |
| `prometheus` | 9090 | Metrics (optional) |
| `grafana` | 3000 | Dashboards (optional) |

### Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop all services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# Start with monitoring
docker-compose --profile monitoring up -d
```

---

## 📊 Monitoring

### Prometheus Metrics

Available at: http://localhost:9090

- Request latency
- Request count
- Error rates
- Document processing time

### Grafana Dashboards

Available at: http://localhost:3000

- Default credentials: `admin` / `admin`

---

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/test_documents.py -v
```

---

## 📁 Project Structure

```
knowledge-base-backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── documents.py    # Document endpoints
│   │       ├── search.py       # Search endpoints
│   │       ├── agents.py       # Agent/chat endpoints
│   │       └── health.py       # Health checks
│   ├── core/
│   │   ├── config.py           # Settings
│   │   ├── logging.py          # Logging setup
│   │   └── celery_app.py       # Background tasks
│   ├── services/
│   │   ├── document_service.py # Docling processing
│   │   ├── pii_service.py      # LangExtract PII
│   │   ├── embedding_service.py# Embeddings
│   │   ├── pinecone_service.py # Vector DB
│   │   └── pageindex_service.py# Tree RAG
│   ├── schemas/
│   │   └── api_schemas.py      # Pydantic models
│   └── main.py                 # FastAPI app
├── monitoring/
│   ├── prometheus.yml
│   └── grafana/
├── tests/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🔒 Security

- **PII Detection**: Automatic detection and redaction of sensitive data
- **Non-root Docker**: Runs as unprivileged user
- **JWT Authentication**: Token-based auth (configurable)
- **Rate Limiting**: Request throttling
- **CORS**: Configurable origins

---

## 🛠️ Troubleshooting

### Common Issues

**1. Pinecone Connection Error**
```
Ensure PINECONE_API_KEY is set correctly
Check PINECONE_ENVIRONMENT matches your index region
```

**2. OpenAI Rate Limits**
```
Use gpt-4o-mini instead of gpt-4o
Implement retry logic (built-in with tenacity)
```

**3. Redis Connection Error**
```bash
# Check Redis is running
docker ps | grep redis

# Start Redis
docker run -d -p 6379:6379 redis:7-alpine
```

**4. Out of Memory (Embeddings)**
```
Reduce batch size in embedding_service.py
Use a smaller embedding model
```

---

## 📈 Performance Tips

1. **Enable Embedding Cache**: Set `EMBEDDING_CACHE_ENABLED=true`
2. **Adjust Chunk Size**: Larger chunks = fewer vectors, but less precision
3. **Use PageIndex for Long Documents**: Better for 50+ page documents
4. **Scale Celery Workers**: `docker-compose up -d --scale celery-worker=4`

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Docling](https://github.com/docling-project/docling) - Document processing
- [PageIndex](https://github.com/VectifyAI/PageIndex) - Reasoning-based RAG
- [LangExtract](https://github.com/google/langextract) - PII detection
- [Pinecone](https://www.pinecone.io/) - Vector database
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework

---

## 📞 Support

- 📧 Email: support@example.com
- 💬 Discord: [Join Server](#)
- 📖 Docs: [Documentation](#)

---

Made with ❤️ for building intelligent knowledge bases