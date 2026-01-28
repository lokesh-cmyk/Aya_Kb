"""
Knowledge Base RAG Backend - Main Application Entry Point
==========================================================

A production-ready unified knowledge base system featuring:
- Document processing with Docling
- Reasoning-based RAG with PageIndex
- PII protection with LangExtract
- Vector storage with Pinecone
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from app.api.v1 import documents, search, health, agents
from app.core.config import settings
from app.core.logging import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Knowledge Base Backend...")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Initialize services
    from app.services.pinecone_service import PineconeService
    from app.services.embedding_service import EmbeddingService
    
    # Warm up embedding model
    embedding_service = EmbeddingService()
    await embedding_service.initialize()
    
    # Initialize Pinecone connection
    pinecone_service = PineconeService()
    await pinecone_service.initialize()
    
    logger.info("All services initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Knowledge Base Backend...")
    await pinecone_service.close()
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Knowledge Base RAG API",
    description="""
    A unified knowledge base API for document processing, vectorization, 
    and intelligent search using RAG (Retrieval-Augmented Generation).
    
    ## Features
    
    * **Document Upload** - Support for PDF, DOCX, PPTX, XLSX, images, and more
    * **Intelligent Processing** - Uses Docling for advanced document parsing
    * **PII Protection** - Automatic detection and redaction using LangExtract
    * **Reasoning-based RAG** - PageIndex for human-like document retrieval
    * **Vector Search** - Pinecone for semantic similarity search
    * **Agent Integration** - Query your knowledge base with AI agents
    """,
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ==========================================
# Middleware Configuration
# ==========================================

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression for responses
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add a unique request ID to each request for tracing."""
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions gracefully."""
    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=True,
        extra={"request_id": getattr(request.state, "request_id", "unknown")}
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
            "request_id": getattr(request.state, "request_id", "unknown"),
        },
    )


# ==========================================
# API Routes
# ==========================================

# Health check endpoints
app.include_router(
    health.router,
    tags=["Health"],
)

# Document management endpoints
app.include_router(
    documents.router,
    prefix="/api/v1/documents",
    tags=["Documents"],
)

# Search endpoints
app.include_router(
    search.router,
    prefix="/api/v1/search",
    tags=["Search"],
)

# Agent/Chat endpoints
app.include_router(
    agents.router,
    prefix="/api/v1/agents",
    tags=["Agents"],
)

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# ==========================================
# Root Endpoint
# ==========================================

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Knowledge Base RAG API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.DEBUG else "disabled",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.WORKERS,
    )