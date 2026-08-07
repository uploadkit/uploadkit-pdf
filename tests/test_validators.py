"""Tests for sync PDF validators."""

from __future__ import annotations

import io

import pytest
from pypdf import PdfWriter
from uploadkit import InvalidFileContent, Uploader, UploadPolicy
from uploadkit_testing import FakeStorageProvider, make_upload_file

from uploadkit_pdf import (
    UPLOADER_PDF_ATTR,
    PdfMetadata,
    PdfPageLimitValidator,
    PdfPolicy,
    PdfSecurityValidator,
    PdfStructureValidator,
    default_pdf_validators,
    inspect_pdf,
)


def _make_pdf_bytes(*, pages: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_inspect_pdf_basic() -> None:
    data = _make_pdf_bytes(pages=2)
    meta = inspect_pdf(data)
    assert isinstance(meta, PdfMetadata)
    assert meta.page_count == 2
    assert meta.encrypted is False
    assert meta.has_javascript is False


def test_inspect_pdf_rejects_non_pdf() -> None:
    with pytest.raises(InvalidFileContent, match="not a PDF"):
        inspect_pdf(b"not a pdf")


def test_structure_validator_attaches_metadata() -> None:
    file = make_upload_file(_make_pdf_bytes(), name="doc.pdf")
    PdfStructureValidator().validate(file, UploadPolicy())
    meta = getattr(file, UPLOADER_PDF_ATTR)
    assert meta.page_count == 1


def test_page_limit_validator() -> None:
    file = make_upload_file(_make_pdf_bytes(pages=3), name="doc.pdf")
    with pytest.raises(InvalidFileContent, match="pages"):
        PdfPageLimitValidator(max_pages=2).validate(file, UploadPolicy())


def test_security_rejects_encrypted() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt("secret")
    buf = io.BytesIO()
    writer.write(buf)
    file = make_upload_file(buf.getvalue(), name="secret.pdf")
    with pytest.raises(InvalidFileContent, match="Encrypted"):
        PdfSecurityValidator().validate(file, UploadPolicy())


def test_pdf_policy_upload_success() -> None:
    storage = FakeStorageProvider()
    uploader = Uploader(PdfPolicy(max_pages=5), storage)
    result = uploader.upload(
        make_upload_file(_make_pdf_bytes(pages=2), name="ok.pdf"),
        bucket="b",
        object_name="ok.pdf",
    )
    assert result.etag == "fake-etag"


def test_default_pdf_validators_exclude() -> None:
    stack = default_pdf_validators(exclude=PdfPageLimitValidator)
    assert len(stack) == 2
    assert all(not isinstance(v, PdfPageLimitValidator) for v in stack)


def test_pdf_policy_rejects_bad_content() -> None:
    storage = FakeStorageProvider()
    uploader = Uploader(PdfPolicy(), storage)
    with pytest.raises(InvalidFileContent):
        uploader.upload(
            make_upload_file(b"hello", name="fake.pdf"),
            bucket="b",
            object_name="fake.pdf",
        )
