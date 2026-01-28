"""
Document Processing Service
===========================

Document parsing and extraction using Docling.
Supports PDF, DOCX, PPTX, XLSX, images, and more.
"""

import hashlib
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import ConversionStatus
from docling.datamodel.document import ConversionResult

from app.core.config import settings
from app.schemas.api_schemas import DocumentType, PIICategory

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Document processing service using Docling.
    
    Handles document conversion, text extraction, and metadata extraction
    for various document formats.
    """
    
    def __init__(self):
        """Initialize the document processor."""
        self._converter = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the Docling converter."""
        if self._initialized:
            return
        
        logger.info("Initializing Docling document converter...")
        self._converter = DocumentConverter()
        self._initialized = True
        logger.info("Docling converter initialized successfully")
    
    def _get_converter(self) -> DocumentConverter:
        """Get or create the document converter."""
        if self._converter is None:
            self._converter = DocumentConverter()
        return self._converter
    
    @staticmethod
    def detect_file_type(file_path: str, filename: str) -> DocumentType:
        """Detect the document type from file extension and content."""
        extension = Path(filename).suffix.lower().lstrip(".")
        
        type_mapping = {
            "pdf": DocumentType.PDF,
            "docx": DocumentType.DOCX,
            "pptx": DocumentType.PPTX,
            "xlsx": DocumentType.XLSX,
            "txt": DocumentType.TXT,
            "md": DocumentType.MD,
            "html": DocumentType.HTML,
            "htm": DocumentType.HTML,
            "png": DocumentType.IMAGE,
            "jpg": DocumentType.IMAGE,
            "jpeg": DocumentType.IMAGE,
            "tiff": DocumentType.IMAGE,
            "webp": DocumentType.IMAGE,
        }
        
        return type_mapping.get(extension, DocumentType.TXT)
    
    @staticmethod
    def generate_document_id(content: bytes, filename: str) -> str:
        """Generate a unique document ID based on content hash."""
        hash_input = content + filename.encode()
        return hashlib.sha256(hash_input).hexdigest()[:16]
    
    async def process_document(
        self,
        file_path: str,
        filename: str,
        document_id: str,
    ) -> Dict[str, Any]:
        """
        Process a document and extract its content.
        
        Args:
            file_path: Path to the document file
            filename: Original filename
            document_id: Unique document identifier
            
        Returns:
            Dictionary containing processed document data
        """
        logger.info(f"Processing document: {filename} (ID: {document_id})")
        
        converter = self._get_converter()
        file_type = self.detect_file_type(file_path, filename)
        
        try:
            # Convert document using Docling
            result: ConversionResult = converter.convert(file_path)
            
            if result.status != ConversionStatus.SUCCESS:
                raise ValueError(f"Document conversion failed: {result.status}")
            
            # Extract content as markdown
            markdown_content = result.document.export_to_markdown()
            
            # Extract metadata
            metadata = self._extract_metadata(result, file_type, filename)
            
            # Chunk the content
            chunks = self._chunk_content(
                markdown_content,
                document_id,
                metadata
            )
            
            logger.info(
                f"Document processed successfully: {filename}, "
                f"{len(chunks)} chunks created"
            )
            
            return {
                "document_id": document_id,
                "filename": filename,
                "file_type": file_type,
                "content": markdown_content,
                "chunks": chunks,
                "metadata": metadata,
                "page_count": metadata.get("page_count"),
                "word_count": len(markdown_content.split()),
            }
            
        except Exception as e:
            logger.error(f"Error processing document {filename}: {e}")
            raise
    
    def _extract_metadata(
        self,
        result: ConversionResult,
        file_type: DocumentType,
        filename: str,
    ) -> Dict[str, Any]:
        """Extract metadata from the converted document."""
        doc = result.document
        
        metadata = {
            "filename": filename,
            "file_type": file_type.value,
            "page_count": len(doc.pages) if hasattr(doc, "pages") else None,
            "has_tables": False,
            "has_images": False,
            "title": None,
            "author": None,
        }
        
        # Extract title if available
        if hasattr(doc, "title") and doc.title:
            metadata["title"] = doc.title
        
        # Check for tables
        if hasattr(doc, "tables") and doc.tables:
            metadata["has_tables"] = True
            metadata["table_count"] = len(doc.tables)
        
        # Check for images/figures
        if hasattr(doc, "pictures") and doc.pictures:
            metadata["has_images"] = True
            metadata["image_count"] = len(doc.pictures)
        
        return metadata
    
    def _chunk_content(
        self,
        content: str,
        document_id: str,
        metadata: Dict[str, Any],
        chunk_size: int = None,
        chunk_overlap: int = None,
    ) -> List[Dict[str, Any]]:
        """
        Split content into chunks for embedding.
        
        Uses a simple character-based chunking strategy with overlap.
        """
        chunk_size = chunk_size or settings.CHUNK_SIZE
        chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        
        chunks = []
        text = content.strip()
        
        if not text:
            return chunks
        
        # Split into paragraphs first
        paragraphs = text.split("\n\n")
        
        current_chunk = ""
        current_chunk_start = 0
        chunk_index = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Check if adding this paragraph exceeds chunk size
            if len(current_chunk) + len(para) + 2 > chunk_size:
                if current_chunk:
                    # Save current chunk
                    chunks.append(self._create_chunk(
                        content=current_chunk.strip(),
                        document_id=document_id,
                        chunk_index=chunk_index,
                        metadata=metadata,
                    ))
                    chunk_index += 1
                    
                    # Start new chunk with overlap
                    overlap_start = max(0, len(current_chunk) - chunk_overlap)
                    current_chunk = current_chunk[overlap_start:].strip()
                    if current_chunk:
                        current_chunk += "\n\n"
            
            current_chunk += para + "\n\n"
        
        # Don't forget the last chunk
        if current_chunk.strip():
            chunks.append(self._create_chunk(
                content=current_chunk.strip(),
                document_id=document_id,
                chunk_index=chunk_index,
                metadata=metadata,
            ))
        
        return chunks
    
    def _create_chunk(
        self,
        content: str,
        document_id: str,
        chunk_index: int,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a chunk dictionary with metadata."""
        chunk_id = f"{document_id}_chunk_{chunk_index}"
        
        return {
            "chunk_id": chunk_id,
            "document_id": document_id,
            "content": content,
            "chunk_index": chunk_index,
            "char_count": len(content),
            "word_count": len(content.split()),
            "metadata": {
                **metadata,
                "chunk_index": chunk_index,
            },
        }
    
    async def extract_text_only(self, file_path: str) -> str:
        """Extract plain text from a document."""
        converter = self._get_converter()
        result = converter.convert(file_path)
        
        if result.status != ConversionStatus.SUCCESS:
            raise ValueError(f"Text extraction failed: {result.status}")
        
        return result.document.export_to_markdown()


# Global instance
document_processor = DocumentProcessor()