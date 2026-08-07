"""PDF metadata extraction (read-only)."""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from uploadkit import InvalidFileContent

UPLOADER_PDF_ATTR = "uploader_pdf_metadata"

_PDF_MAGIC = b"%PDF-"


@dataclass(frozen=True, slots=True)
class PdfMetadata:
    """Read-only PDF inspection result."""

    version: str | None
    page_count: int
    encrypted: bool
    has_javascript: bool
    has_embedded_files: bool
    has_launch_actions: bool
    has_open_action: bool
    title: str | None = None
    author: str | None = None
    creator: str | None = None
    producer: str | None = None


def _meta_str(info: Any, key: str) -> str | None:
    if info is None:
        return None
    try:
        value = info.get(key) if hasattr(info, "get") else getattr(info, key, None)
    except Exception:  # noqa: BLE001 — pypdf metadata access can raise
        return None
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _catalog_has_js(reader: PdfReader) -> bool:
    root = reader.root_object
    if root is None:
        return False
    if "/JavaScript" in root or "/JS" in root:
        return True
    names = root.get("/Names")
    if names is not None and "/JavaScript" in names:
        return True
    return False


def _has_open_action(reader: PdfReader) -> bool:
    root = reader.root_object
    return root is not None and "/OpenAction" in root


def _has_launch_or_goto_r(reader: PdfReader) -> bool:
    """Scan page annotations for Launch / GoToR actions."""
    try:
        for page in reader.pages:
            annots = page.get("/Annots")
            if not annots:
                continue
            for annot in annots:
                try:
                    obj = annot.get_object() if hasattr(annot, "get_object") else annot
                except Exception:  # noqa: BLE001
                    continue
                action = obj.get("/A") if hasattr(obj, "get") else None
                if action is None:
                    continue
                try:
                    action_obj = (
                        action.get_object() if hasattr(action, "get_object") else action
                    )
                except Exception:  # noqa: BLE001
                    continue
                subtype = action_obj.get("/S") if hasattr(action_obj, "get") else None
                if subtype in ("/Launch", "/GoToR"):
                    return True
    except Exception:  # noqa: BLE001 — malformed annotation trees
        return False
    return False


def _has_embedded_files(reader: PdfReader) -> bool:
    root = reader.root_object
    if root is None:
        return False
    names = root.get("/Names")
    if names is not None and "/EmbeddedFiles" in names:
        return True
    if "/AF" in root:  # associated files (PDF 2.0 / PDF/A-3)
        return True
    return False


def inspect_pdf(data: bytes) -> PdfMetadata:
    """Parse PDF bytes and return metadata. Raises InvalidFileContent on failure."""
    if not data.lstrip().startswith(_PDF_MAGIC) and not data.startswith(_PDF_MAGIC):
        # Allow leading whitespace/BOM-ish noise only before %PDF-
        head = data[:1024]
        if _PDF_MAGIC not in head:
            raise InvalidFileContent("File is not a PDF (missing %PDF- header)")

    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
    except PdfReadError as exc:
        raise InvalidFileContent(f"Invalid PDF structure: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        raise InvalidFileContent(f"Failed to parse PDF: {exc}") from exc

    encrypted = bool(reader.is_encrypted)
    # Encrypted PDFs often cannot expose pages/catalog without a password.
    if encrypted:
        version = None
        if getattr(reader, "pdf_header", None):
            version = str(reader.pdf_header).removeprefix("%PDF-").strip() or None
        return PdfMetadata(
            version=version,
            page_count=0,
            encrypted=True,
            has_javascript=False,
            has_embedded_files=False,
            has_launch_actions=False,
            has_open_action=False,
        )

    try:
        page_count = len(reader.pages)
    except Exception as exc:  # noqa: BLE001
        raise InvalidFileContent(f"Failed to read PDF pages: {exc}") from exc

    info = reader.metadata
    version = None
    if getattr(reader, "pdf_header", None):
        version = str(reader.pdf_header).removeprefix("%PDF-").strip() or None

    return PdfMetadata(
        version=version,
        page_count=page_count,
        encrypted=False,
        has_javascript=_catalog_has_js(reader),
        has_embedded_files=_has_embedded_files(reader),
        has_launch_actions=_has_launch_or_goto_r(reader),
        has_open_action=_has_open_action(reader),
        title=_meta_str(info, "/Title"),
        author=_meta_str(info, "/Author"),
        creator=_meta_str(info, "/Creator"),
        producer=_meta_str(info, "/Producer"),
    )


def read_file_bytes(file: Any) -> bytes:
    """Read all bytes from an UploadableFile and rewind."""
    position = file.tell() if hasattr(file, "tell") else None
    try:
        if hasattr(file, "seek"):
            file.seek(0)
        data = file.read()
    finally:
        if hasattr(file, "seek"):
            file.seek(position if position is not None else 0)
    if not data:
        raise InvalidFileContent("Uploaded file is empty")
    return data
