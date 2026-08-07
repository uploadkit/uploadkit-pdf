"""PDF-oriented UploadPolicy helpers."""

from __future__ import annotations

from collections.abc import Sequence

from uploadkit import UploadPolicy
from uploadkit.async_pipeline import AsyncStreamingValidator
from uploadkit.pipeline import Validator

from uploadkit_pdf.async_validators import default_async_pdf_validators
from uploadkit_pdf.validators import default_pdf_validators

_DEFAULT_MAX_SIZE = 10 * 1024 * 1024
_PDF_EXTENSIONS = frozenset({"pdf"})
_PDF_MIME_TYPES = frozenset({"application/pdf"})


def PdfPolicy(
    *,
    max_size: int | None = _DEFAULT_MAX_SIZE,
    max_pages: int | None = 100,
    allow_encrypted: bool = False,
    allow_javascript: bool = False,
    allow_embedded_files: bool = False,
    allow_launch_actions: bool = False,
    allow_open_action: bool = True,
    validators: Sequence[Validator] | None = None,
    async_validators: Sequence[AsyncStreamingValidator] | None = None,
) -> UploadPolicy:
    """Safe-by-default policy for PDF uploads (no JS, embeds, or encryption)."""
    return UploadPolicy(
        max_size=max_size,
        allowed_extensions=_PDF_EXTENSIONS,
        allowed_mime_types=_PDF_MIME_TYPES,
        validators=tuple(
            validators
            if validators is not None
            else default_pdf_validators(
                max_pages=max_pages,
                allow_encrypted=allow_encrypted,
                allow_javascript=allow_javascript,
                allow_embedded_files=allow_embedded_files,
                allow_launch_actions=allow_launch_actions,
                allow_open_action=allow_open_action,
            )
        ),
        async_validators=tuple(
            async_validators
            if async_validators is not None
            else default_async_pdf_validators(
                max_pages=max_pages,
                allow_encrypted=allow_encrypted,
                allow_javascript=allow_javascript,
                allow_embedded_files=allow_embedded_files,
                allow_launch_actions=allow_launch_actions,
                allow_open_action=allow_open_action,
            )
        ),
    )
