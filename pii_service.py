"""
PII Protection Service
======================

Detection and redaction of sensitive information using LangExtract.
Protects passwords, API keys, credit cards, SSNs, and other PII.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.schemas.api_schemas import PIICategory, PIIDetectionResult

logger = logging.getLogger(__name__)


class PIIProtectionService:
    """
    PII (Personally Identifiable Information) protection service.
    
    Uses LangExtract for intelligent PII detection and redaction,
    with fallback to regex-based detection for common patterns.
    """
    
    def __init__(self):
        """Initialize the PII protection service."""
        self._initialized = False
        self._langextract = None
        
        # Regex patterns for common PII types
        self._patterns = {
            PIICategory.PASSWORD: [
                r'(?i)password\s*[:=]\s*[\'"]?([^\s\'"]+)[\'"]?',
                r'(?i)pwd\s*[:=]\s*[\'"]?([^\s\'"]+)[\'"]?',
                r'(?i)pass\s*[:=]\s*[\'"]?([^\s\'"]+)[\'"]?',
            ],
            PIICategory.API_KEY: [
                r'(?i)api[_-]?key\s*[:=]\s*[\'"]?([a-zA-Z0-9_-]{20,})[\'"]?',
                r'(?i)secret[_-]?key\s*[:=]\s*[\'"]?([a-zA-Z0-9_-]{20,})[\'"]?',
                r'(?i)access[_-]?token\s*[:=]\s*[\'"]?([a-zA-Z0-9_-]{20,})[\'"]?',
                r'sk-[a-zA-Z0-9]{32,}',  # OpenAI API keys
                r'pk-[a-zA-Z0-9]{32,}',  # Pinecone API keys
                r'AIza[a-zA-Z0-9_-]{35}',  # Google API keys
            ],
            PIICategory.CREDIT_CARD: [
                r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b',
            ],
            PIICategory.SSN: [
                r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b',
            ],
            PIICategory.EMAIL: [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            ],
            PIICategory.PHONE: [
                r'\b(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
                r'\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b',
            ],
            PIICategory.ADDRESS: [
                r'\b\d{1,5}\s+\w+(?:\s+\w+)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct)\b',
            ],
        }
        
        # Redaction strings for each category
        self._redaction_strings = {
            PIICategory.PASSWORD: "[REDACTED_PASSWORD]",
            PIICategory.API_KEY: "[REDACTED_API_KEY]",
            PIICategory.CREDIT_CARD: "[REDACTED_CREDIT_CARD]",
            PIICategory.SSN: "[REDACTED_SSN]",
            PIICategory.EMAIL: "[REDACTED_EMAIL]",
            PIICategory.PHONE: "[REDACTED_PHONE]",
            PIICategory.ADDRESS: "[REDACTED_ADDRESS]",
        }
    
    async def initialize(self) -> None:
        """Initialize LangExtract for intelligent PII detection."""
        if self._initialized:
            return
        
        try:
            if settings.GOOGLE_API_KEY:
                import langextract as lx
                self._langextract = lx
                logger.info("LangExtract initialized for intelligent PII detection")
            else:
                logger.warning(
                    "GOOGLE_API_KEY not set, falling back to regex-based PII detection"
                )
        except ImportError:
            logger.warning(
                "LangExtract not available, using regex-based PII detection"
            )
        
        self._initialized = True
    
    async def detect_pii(
        self,
        content: str,
        categories: Optional[List[PIICategory]] = None,
    ) -> PIIDetectionResult:
        """
        Detect PII in the given content.
        
        Args:
            content: Text content to scan for PII
            categories: List of PII categories to detect (defaults to all)
            
        Returns:
            PIIDetectionResult with detection details
        """
        if not settings.PII_DETECTION_ENABLED:
            return PIIDetectionResult(
                has_pii=False,
                categories_found=[],
                detections=[],
            )
        
        categories = categories or list(PIICategory)
        detections = []
        categories_found = set()
        
        # Use LangExtract if available for intelligent detection
        if self._langextract and settings.GOOGLE_API_KEY:
            try:
                langextract_result = await self._detect_with_langextract(
                    content, categories
                )
                detections.extend(langextract_result.get("detections", []))
                categories_found.update(langextract_result.get("categories", []))
            except Exception as e:
                logger.warning(f"LangExtract detection failed, using regex: {e}")
        
        # Always run regex detection as backup/supplement
        regex_result = self._detect_with_regex(content, categories)
        
        # Merge results, avoiding duplicates based on position
        existing_positions = {(d["start"], d["end"]) for d in detections}
        for detection in regex_result["detections"]:
            pos = (detection["start"], detection["end"])
            if pos not in existing_positions:
                detections.append(detection)
                existing_positions.add(pos)
        
        categories_found.update(regex_result["categories"])
        
        return PIIDetectionResult(
            has_pii=len(detections) > 0,
            categories_found=list(categories_found),
            detections=detections,
        )
    
    async def redact_pii(
        self,
        content: str,
        categories: Optional[List[PIICategory]] = None,
    ) -> Tuple[str, PIIDetectionResult]:
        """
        Detect and redact PII from content.
        
        Args:
            content: Text content to redact
            categories: List of PII categories to redact
            
        Returns:
            Tuple of (redacted_content, detection_result)
        """
        detection_result = await self.detect_pii(content, categories)
        
        if not detection_result.has_pii:
            detection_result.redacted_content = content
            return content, detection_result
        
        # Sort detections by position (reverse order for safe replacement)
        sorted_detections = sorted(
            detection_result.detections,
            key=lambda x: x["start"],
            reverse=True,
        )
        
        redacted = content
        for detection in sorted_detections:
            start = detection["start"]
            end = detection["end"]
            category = PIICategory(detection["category"])
            redaction = self._redaction_strings.get(
                category, "[REDACTED]"
            )
            redacted = redacted[:start] + redaction + redacted[end:]
        
        detection_result.redacted_content = redacted
        return redacted, detection_result
    
    async def _detect_with_langextract(
        self,
        content: str,
        categories: List[PIICategory],
    ) -> Dict[str, Any]:
        """Use LangExtract for intelligent PII detection."""
        import langextract as lx
        
        # Define extraction prompt for PII
        prompt = """
        Extract all sensitive personal information from the text, including:
        - Passwords and credentials
        - API keys and access tokens
        - Credit card numbers
        - Social Security Numbers (SSN)
        - Email addresses
        - Phone numbers
        - Physical addresses
        
        Only extract actual PII, not references to PII concepts.
        Use exact text for extractions.
        """
        
        # Define example for few-shot learning
        examples = [
            lx.data.ExampleData(
                text="My password is secret123 and my email is john@example.com",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="password",
                        extraction_text="secret123",
                        attributes={"type": "credential"},
                    ),
                    lx.data.Extraction(
                        extraction_class="email",
                        extraction_text="john@example.com",
                        attributes={"type": "personal_email"},
                    ),
                ],
            ),
        ]
        
        try:
            result = lx.extract(
                text_or_documents=content,
                prompt_description=prompt,
                examples=examples,
                model_id=settings.LANGEXTRACT_MODEL,
                api_key=settings.GOOGLE_API_KEY,
            )
            
            detections = []
            categories_found = []
            
            if result and hasattr(result, "extractions"):
                for extraction in result.extractions:
                    category = self._map_extraction_to_category(
                        extraction.extraction_class
                    )
                    if category and category in categories:
                        # Find position in text
                        text = extraction.extraction_text
                        start = content.find(text)
                        if start != -1:
                            detections.append({
                                "category": category.value,
                                "text": text,
                                "start": start,
                                "end": start + len(text),
                                "confidence": 0.9,
                                "source": "langextract",
                            })
                            if category not in categories_found:
                                categories_found.append(category)
            
            return {
                "detections": detections,
                "categories": categories_found,
            }
            
        except Exception as e:
            logger.error(f"LangExtract extraction failed: {e}")
            return {"detections": [], "categories": []}
    
    def _detect_with_regex(
        self,
        content: str,
        categories: List[PIICategory],
    ) -> Dict[str, Any]:
        """Detect PII using regex patterns."""
        detections = []
        categories_found = []
        
        for category in categories:
            patterns = self._patterns.get(category, [])
            for pattern in patterns:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    # Get the actual matched text (group 1 if exists, else group 0)
                    text = match.group(1) if match.lastindex else match.group(0)
                    start = match.start(1) if match.lastindex else match.start()
                    end = match.end(1) if match.lastindex else match.end()
                    
                    detections.append({
                        "category": category.value,
                        "text": text,
                        "start": start,
                        "end": end,
                        "confidence": 0.8,
                        "source": "regex",
                    })
                    
                    if category not in categories_found:
                        categories_found.append(category)
        
        return {
            "detections": detections,
            "categories": categories_found,
        }
    
    def _map_extraction_to_category(
        self,
        extraction_class: str,
    ) -> Optional[PIICategory]:
        """Map LangExtract extraction class to PII category."""
        mapping = {
            "password": PIICategory.PASSWORD,
            "credential": PIICategory.PASSWORD,
            "api_key": PIICategory.API_KEY,
            "access_token": PIICategory.API_KEY,
            "secret": PIICategory.API_KEY,
            "credit_card": PIICategory.CREDIT_CARD,
            "card_number": PIICategory.CREDIT_CARD,
            "ssn": PIICategory.SSN,
            "social_security": PIICategory.SSN,
            "email": PIICategory.EMAIL,
            "phone": PIICategory.PHONE,
            "phone_number": PIICategory.PHONE,
            "address": PIICategory.ADDRESS,
        }
        
        extraction_lower = extraction_class.lower()
        return mapping.get(extraction_lower)


# Global instance
pii_service = PIIProtectionService()