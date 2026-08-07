"""Tests for async PDF validators."""

from __future__ import annotations

import io

import pytest
from pypdf import PdfWriter
from uploadkit import AsyncUploader, InvalidFileContent, UploadPolicy

from uploadkit_pdf import (
    AsyncPdfPageLimitValidator,
    AsyncPdfSecurityValidator,
    AsyncPdfStructureValidator,
    PdfPolicy,
    default_async_pdf_validators,
)


def _make_pdf_bytes(*, pages: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


class MemoryAsyncSource:
    def __init__(
        self,
        content: bytes,
        *,
        name: str = "a.pdf",
        content_type: str | None = "application/pdf",
    ) -> None:
        self._content = content
        self._offset = 0
        self.name = name
        self.size = len(content)
        self.content_type = content_type

    async def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self._content) - self._offset
        data = self._content[self._offset : self._offset + size]
        self._offset += len(data)
        return data


class FakeAsyncWriter:
    def __init__(self, storage: FakeAsyncStorage) -> None:
        self._storage = storage
        self._chunks: list[bytes] = []

    async def write(self, chunk: bytes) -> None:
        self._chunks.append(chunk)

    async def abort(self) -> None:
        return

    async def complete(self) -> str | None:
        self._storage.puts.append(b"".join(self._chunks))
        return "async-etag"


class FakeAsyncStorage:
    def __init__(self) -> None:
        self.puts: list[bytes] = []

    async def open_write(
        self,
        *,
        bucket: str,
        object_name: str,
        content_type: str,
    ) -> FakeAsyncWriter:
        return FakeAsyncWriter(self)


@pytest.mark.asyncio
async def test_async_structure_ok() -> None:
    storage = FakeAsyncStorage()
    policy = UploadPolicy(async_validators=(AsyncPdfStructureValidator(),))
    uploader = AsyncUploader(policy, storage)
    result = await uploader.upload(
        MemoryAsyncSource(_make_pdf_bytes()),
        bucket="b",
        object_name="a.pdf",
    )
    assert result.etag == "async-etag"


@pytest.mark.asyncio
async def test_async_page_limit() -> None:
    storage = FakeAsyncStorage()
    policy = UploadPolicy(
        async_validators=(AsyncPdfPageLimitValidator(max_pages=1),)
    )
    uploader = AsyncUploader(policy, storage)
    with pytest.raises(InvalidFileContent, match="pages"):
        await uploader.upload(
            MemoryAsyncSource(_make_pdf_bytes(pages=3)),
            bucket="b",
            object_name="a.pdf",
        )


@pytest.mark.asyncio
async def test_async_security_encrypted() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt("secret")
    buf = io.BytesIO()
    writer.write(buf)
    storage = FakeAsyncStorage()
    policy = UploadPolicy(async_validators=(AsyncPdfSecurityValidator(),))
    uploader = AsyncUploader(policy, storage)
    with pytest.raises(InvalidFileContent, match="Encrypted"):
        await uploader.upload(
            MemoryAsyncSource(buf.getvalue()),
            bucket="b",
            object_name="a.pdf",
        )


@pytest.mark.asyncio
async def test_pdf_policy_async() -> None:
    storage = FakeAsyncStorage()
    uploader = AsyncUploader(PdfPolicy(max_pages=5), storage)
    result = await uploader.upload(
        MemoryAsyncSource(_make_pdf_bytes(pages=2)),
        bucket="b",
        object_name="a.pdf",
    )
    assert result.etag == "async-etag"


def test_default_async_exclude() -> None:
    stack = default_async_pdf_validators(exclude=AsyncPdfPageLimitValidator)
    assert len(stack) == 2
