"""
Documents domain facade.
"""

from .service import DocumentService, document_service
from .processor import document_processor
from .chunked_upload import chunked_upload_service

__all__ = [
    "DocumentService",
    "document_service",
    "document_processor",
    "chunked_upload_service",
]
