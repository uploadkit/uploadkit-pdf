"""Sync PDF validators for UploadKit."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from uploadkit import InvalidFileContent, UploadableFile, UploadPolicy, Validator

from uploadkit_pdf.metadata import (
    UPLOADER_PDF_ATTR,
    PdfMetadata,
    inspect_pdf,
    read_file_bytes,
)


class PdfStructureValidator:
    """Confirm the file is a parseable PDF and attach metadata."""

    def validate(self, file: UploadableFile, policy: UploadPolicy) -> None:
        data = read_file_bytes(file)
        meta = inspect_pdf(data)
        setattr(file, UPLOADER_PDF_ATTR, meta)


class PdfPageLimitValidator:
    """Reject PDFs exceeding ``max_pages``."""

    def __init__(self, *, max_pages: int | None = 100) -> None:
        self.max_pages = max_pages

    def validate(self, file: UploadableFile, policy: UploadPolicy) -> None:
        meta = self._meta(file)
        if self.max_pages is not None and meta.page_count > self.max_pages:
            raise InvalidFileContent(
                f"PDF has {meta.page_count} pages; maximum allowed is {self.max_pages}"
            )

    def _meta(self, file: UploadableFile) -> PdfMetadata:
        existing = getattr(file, UPLOADER_PDF_ATTR, None)
        if isinstance(existing, PdfMetadata):
            return existing
        data = read_file_bytes(file)
        meta = inspect_pdf(data)
        setattr(file, UPLOADER_PDF_ATTR, meta)
        return meta


class PdfSecurityValidator:
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
        self.allow_encrypted = allow_encrypted
        self.allow_javascript = allow_javascript
        self.allow_embedded_files = allow_embedded_files
        self.allow_launch_actions = allow_launch_actions
        self.allow_open_action = allow_open_action

    def validate(self, file: UploadableFile, policy: UploadPolicy) -> None:
        meta = self._meta(file)
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

    def _meta(self, file: UploadableFile) -> PdfMetadata:
        existing = getattr(file, UPLOADER_PDF_ATTR, None)
        if isinstance(existing, PdfMetadata):
            return existing
        data = read_file_bytes(file)
        meta = inspect_pdf(data)
        setattr(file, UPLOADER_PDF_ATTR, meta)
        return meta


_DEFAULT_VALIDATOR_TYPES: Final[tuple[type, ...]] = (
    PdfStructureValidator,
    PdfSecurityValidator,
    PdfPageLimitValidator,
)


def _as_type_set(
    value: type | tuple[type, ...] | list[type] | frozenset[type] | set[type],
) -> frozenset[type]:
    if isinstance(value, (tuple, list, set, frozenset)):
        return frozenset(value)
    return frozenset((value,))


def default_pdf_validators(
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
    extra: Sequence[Validator] = (),
) -> tuple[Validator, ...]:
    """Build the stock PDF validator stack."""
    excluded = _as_type_set(exclude)
    if include is None:
        selected = frozenset(_DEFAULT_VALIDATOR_TYPES) - excluded
    else:
        selected = _as_type_set(include) - excluded

    stock: list[Validator] = []
    if PdfStructureValidator in selected:
        stock.append(PdfStructureValidator())
    if PdfSecurityValidator in selected:
        stock.append(
            PdfSecurityValidator(
                allow_encrypted=allow_encrypted,
                allow_javascript=allow_javascript,
                allow_embedded_files=allow_embedded_files,
                allow_launch_actions=allow_launch_actions,
                allow_open_action=allow_open_action,
            )
        )
    if PdfPageLimitValidator in selected:
        stock.append(PdfPageLimitValidator(max_pages=max_pages))
    return (*stock, *extra)
