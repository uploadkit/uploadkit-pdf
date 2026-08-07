# uploadkit-pdf

PDF validators, policies, and metadata for UploadKit.

## What problem does this solve?

PDF-specific structure, security, and page-limit checks that plug into
`UploadPolicy.validators` without modifying UploadKit Core.

## When to use it

Use when uploads must accept PDFs safely (no JavaScript, embeds, or encryption
by default).

## When not to use it

- Do not render, edit, merge, or OCR PDFs here.
- Do not put generic MIME/filename checks here (see `uploadkit-security`).

## Installation

Requires **Python 3.10+**.

```bash
pip install uploadkit-pdf
```

## Quick Start

```python
from uploadkit import Uploader
from uploadkit_pdf import PdfPolicy

uploader = Uploader(PdfPolicy(max_size=5 * 1024 * 1024, max_pages=50), storage=my_storage)
```

### Customize validators

```python
from uploadkit import UploadPolicy
from uploadkit_pdf import default_pdf_validators, PdfPageLimitValidator

policy = UploadPolicy(
    allowed_extensions=frozenset({"pdf"}),
    allowed_mime_types=frozenset({"application/pdf"}),
    validators=default_pdf_validators(max_pages=20, exclude=PdfPageLimitValidator),
)
```

### Inspect metadata

```python
from uploadkit_pdf import inspect_pdf

meta = inspect_pdf(open("doc.pdf", "rb").read())
print(meta.page_count, meta.encrypted, meta.has_javascript)
```

## Public API

| Symbol | Kind |
|--------|------|
| `PdfPolicy` | Public |
| `PdfMetadata` / `inspect_pdf` | Public |
| `PdfStructureValidator` | Public |
| `PdfSecurityValidator` | Public |
| `PdfPageLimitValidator` | Public |
| `default_pdf_validators` | Public |
| `AsyncPdfStructureValidator` | Public |
| `AsyncPdfSecurityValidator` | Public |
| `AsyncPdfPageLimitValidator` | Public |
| `default_async_pdf_validators` | Public |

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
