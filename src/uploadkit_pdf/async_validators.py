"""Async streaming PDF validators for UploadKit.

PDF checks need the full byte stream; validators buffer in ``feed`` and
run inspection in ``finalize``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from uploadkit import InvalidFileContent, UploadContext, UploadPolicy
from uploadkit.async_pipeline import AsyncStreamingValidator

from uploadkit_pdf.metadata import PdfMetadata, inspect_pdf
from uploadkit_pdf.validators import (
    PdfPageLimitValidator,
    PdfSecurityValidator,
    PdfStructureValidator,
)

_CONTEXT_KEY = "pdf_metadata"


class _AsyncPdfBufferMixin:
    """Shared begin/feed buffering for PDF async validators."""

    def __init__(self) -> None:
        self._policy: UploadPolicy | None = None
        self._context: UploadContext | None = None
        self._buffer = bytearray()

    async def begin(
        self,
        *,
        name: str | None,
        size: int | None,
        content_type: str | None,
        policy: UploadPolicy,
        context: UploadContext,
    ) -> None:
        self._policy = policy
        self._context = context
        self._buffer.clear()

    async def feed(self, chunk: bytes) -> None:
        if chunk:
            self._buffer.extend(chunk)

    def _resolve_meta(self) -> PdfMetadata:
        if self._context is not None:
            existing = self._context.extras.get(_CONTEXT_KEY)
            if isinstance(existing, PdfMetadata):
                return existing
        if not self._buffer:
            raise InvalidFileContent("Uploaded file is empty")
        meta = inspect_pdf(bytes(self._buffer))
        if self._context is not None:
            self._context.extras[_CONTEXT_KEY] = meta
        return meta


class AsyncPdfStructureValidator(_AsyncPdfBufferMixin):
    """Confirm the streamed file is a parseable PDF."""

    async def finalize(self) -> None:
        self._resolve_meta()


class AsyncPdfPageLimitValidator(_AsyncPdfBufferMixin):
    """Reject streamed PDFs exceeding ``max_pages``."""

    def __init__(self, *, max_pages: int | None = 100) -> None:
        super().__init__()
        self.max_pages = max_pages

    async def finalize(self) -> None:
        meta = self._resolve_meta()
        if self.max_pages is not None and meta.page_count > self.max_pages:
            raise InvalidFileContent(
                f"PDF has {meta.page_count} pages; maximum allowed is {self.max_pages}"
            )


class AsyncPdfSecurityValidator(_AsyncPdfBufferMixin):
    """Reject encrypted PDFs, JavaScript, embeds, and dangerous actions."""

    def __init__(
        self,
        *,
        allow_encrypted: bool = False,
        allow_javascript: bool = False,
        allow_embedded_files: bool = False,
        allow_launch_actions: bool = False,
        allow_open_action: bool = True,
    ) -> None:
        super().__init__()
        self.allow_encrypted = allow_encrypted
        self.allow_javascript = allow_javascript
        self.allow_embedded_files = allow_embedded_files
        self.allow_launch_actions = allow_launch_actions
        self.allow_open_action = allow_open_action

    async def finalize(self) -> None:
        meta = self._resolve_meta()
        if meta.encrypted and not self.allow_encrypted:
            raise InvalidFileContent("Encrypted PDFs are not allowed")
        if meta.has_javascript and not self.allow_javascript:
            raise InvalidFileContent("PDFs with JavaScript are not allowed")
        if meta.has_embedded_files and not self.allow_embedded_files:
            raise InvalidFileContent("PDFs with embedded files are not allowed")
        if meta.has_launch_actions and not self.allow_launch_actions:
            raise InvalidFileContent(
                "PDFs with Launch/GoToR actions are not allowed"
            )
        if meta.has_open_action and not self.allow_open_action:
            raise InvalidFileContent("PDFs with OpenAction are not allowed")


_DEFAULT_ASYNC_VALIDATOR_TYPES: Final[tuple[type, ...]] = (
    AsyncPdfStructureValidator,
    AsyncPdfSecurityValidator,
    AsyncPdfPageLimitValidator,
)


def _as_type_set(
    value: type | tuple[type, ...] | list[type] | frozenset[type] | set[type],
) -> frozenset[type]:
    if isinstance(value, (tuple, list, set, frozenset)):
        return frozenset(value)
    return frozenset((value,))


def default_async_pdf_validators(
    *,
    max_pages: int | None = 100,
    allow_encrypted: bool = False,
    allow_javascript: bool = False,
    allow_embedded_files: bool = False,
    allow_launch_actions: bool = False,
    allow_open_action: bool = True,
    include: type
    | tuple[type, ...]
    | list[type]
    | frozenset[type]
    | set[type]
    | None = None,
    exclude: type | tuple[type, ...] | list[type] | frozenset[type] | set[type] = (),
    extra: Sequence[AsyncStreamingValidator] = (),
) -> tuple[AsyncStreamingValidator, ...]:
    """Build the stock async PDF validator stack."""
    excluded = _as_type_set(exclude)
    if include is None:
        selected = frozenset(_DEFAULT_ASYNC_VALIDATOR_TYPES) - excluded
    else:
        selected = _as_type_set(include) - excluded

    stock: list[AsyncStreamingValidator] = []
    if AsyncPdfStructureValidator in selected:
        stock.append(AsyncPdfStructureValidator())
    if AsyncPdfSecurityValidator in selected:
        stock.append(
            AsyncPdfSecurityValidator(
                allow_encrypted=allow_encrypted,
                allow_javascript=allow_javascript,
                allow_embedded_files=allow_embedded_files,
                allow_launch_actions=allow_launch_actions,
                allow_open_action=allow_open_action,
            )
        )
    if AsyncPdfPageLimitValidator in selected:
        stock.append(AsyncPdfPageLimitValidator(max_pages=max_pages))
    return (*stock, *extra)


# Re-export sync type names used for include/exclude docs parity
__all_sync_types__ = (
    PdfStructureValidator,
    PdfSecurityValidator,
    PdfPageLimitValidator,
)
