"""
API Request/Response Schemas
============================

Pydantic models for API validation and serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


# ==========================================
# Enums
# ==========================================

class DocumentStatus(str, Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(str, Enum):
    """Supported document types."""
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"
    TXT = "txt"
    MD = "md"
    HTML = "html"
    IMAGE = "image"


class PIICategory(str, Enum):
    """PII categories for detection."""
    PASSWORD = "password"
    API_KEY = "api_key"
    CREDIT_CARD = "credit_card"
    SSN = "ssn"
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"


# ==========================================
# Document Schemas
# ==========================================

class DocumentUploadResponse(BaseModel):
    """Response after document upload."""
    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="Detected file type")
    file_size: int = Field(..., description="File size in bytes")
    status: DocumentStatus = Field(..., description="Processing status")
    task_id: Optional[str] = Field(None, description="Background task ID")
    message: str = Field(..., description="Status message")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentMetadata(BaseModel):
    """Document metadata."""
    document_id: str
    filename: str
    file_type: DocumentType
    file_size: int
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    chunk_count: Optional[int] = None
    has_pii: bool = False
    pii_categories_found: List[PIICategory] = []
    created_at: datetime
    processed_at: Optional[datetime] = None
    status: DocumentStatus
    error_message: Optional[str] = None
    
    # PageIndex metadata
    has_tree_index: bool = False
    tree_node_count: Optional[int] = None


class DocumentListResponse(BaseModel):
    """Response for document listing."""
    documents: List[DocumentMetadata]
    total: int
    page: int
    page_size: int
    has_more: bool


class DocumentDeleteResponse(BaseModel):
    """Response after document deletion."""
    document_id: str
    deleted: bool
    message: str


# ==========================================
# Search Schemas
# ==========================================

class SearchRequest(BaseModel):
    """Search request body."""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results")
    namespace: Optional[str] = Field(None, description="Pinecone namespace")
    filters: Optional[Dict[str, Any]] = Field(None, description="Metadata filters")
    include_metadata: bool = Field(default=True, description="Include metadata in results")
    similarity_threshold: float = Field(default=0.7, ge=0, le=1, description="Minimum similarity score")
    use_pageindex: bool = Field(default=False, description="Use PageIndex reasoning-based retrieval")
    rerank: bool = Field(default=False, description="Rerank results")


class SearchResult(BaseModel):
    """Individual search result."""
    document_id: str
    chunk_id: str
    content: str
    score: float
    metadata: Dict[str, Any] = {}
    page_number: Optional[int] = None
    section_title: Optional[str] = None


class SearchResponse(BaseModel):
    """Search response."""
    query: str
    results: List[SearchResult]
    total_results: int
    processing_time_ms: float
    used_pageindex: bool = False


# ==========================================
# Agent/Chat Schemas
# ==========================================

class AgentQueryRequest(BaseModel):
    """Agent query request."""
    query: str = Field(..., min_length=1, max_length=2000, description="User question")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    namespace: Optional[str] = Field(None, description="Knowledge base namespace")
    include_sources: bool = Field(default=True, description="Include source references")
    stream: bool = Field(default=False, description="Stream response")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "What were the key findings from the Q3 financial report?",
                "include_sources": True,
            }
        }
    )


class SourceReference(BaseModel):
    """Source reference for agent response."""
    document_id: str
    document_name: str
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    snippet: str
    relevance_score: float


class AgentQueryResponse(BaseModel):
    """Agent query response."""
    answer: str
    sources: List[SourceReference] = []
    conversation_id: str
    processing_time_ms: float
    token_usage: Optional[Dict[str, int]] = None


# ==========================================
# PII Detection Schemas
# ==========================================

class PIIDetectionResult(BaseModel):
    """PII detection result."""
    has_pii: bool
    categories_found: List[PIICategory]
    detections: List[Dict[str, Any]] = []
    redacted_content: Optional[str] = None


class PIIRedactionRequest(BaseModel):
    """PII redaction request."""
    content: str = Field(..., min_length=1, description="Content to check for PII")
    categories: List[PIICategory] = Field(
        default=[PIICategory.PASSWORD, PIICategory.API_KEY, PIICategory.CREDIT_CARD],
        description="PII categories to detect"
    )
    redact: bool = Field(default=True, description="Redact detected PII")


# ==========================================
# Health Check Schemas
# ==========================================

class ServiceHealth(BaseModel):
    """Individual service health status."""
    name: str
    status: str  # "healthy", "unhealthy", "degraded"
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str  # "healthy", "unhealthy", "degraded"
    version: str
    environment: str
    services: List[ServiceHealth]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ==========================================
# Task Status Schemas
# ==========================================

class TaskStatusResponse(BaseModel):
    """Background task status response."""
    task_id: str
    status: str  # "pending", "started", "success", "failure", "revoked"
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: Optional[int] = None  # 0-100
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ==========================================
# Error Schemas
# ==========================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None