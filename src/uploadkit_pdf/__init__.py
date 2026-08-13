"""PDF validators, policies, and metadata for UploadKit."""

from uploadkit_pdf.async_validators import (
    AsyncPdfPageLimitValidator,
    AsyncPdfSecurityValidator,
    AsyncPdfStructureValidator,
    default_async_pdf_validators,
)
from uploadkit_pdf.metadata import UPLOADER_PDF_ATTR, PdfMetadata, inspect_pdf
from uploadkit_pdf.policy import PdfPolicy
from uploadkit_pdf.validators import (
    PdfPageLimitValidator,
    PdfSecurityValidator,
    PdfStructureValidator,
    default_pdf_validators,
)

__all__ = [
    "PdfMetadata",
    "UPLOADER_PDF_ATTR",
    "inspect_pdf",
    "PdfStructureValidator",
    "PdfSecurityValidator",
    "PdfPageLimitValidator",
    "default_pdf_validators",
    "AsyncPdfStructureValidator",
    "AsyncPdfSecurityValidator",
    "AsyncPdfPageLimitValidator",
    "default_async_pdf_validators",
    "PdfPolicy",
]

__version__ = "0.1.1"
