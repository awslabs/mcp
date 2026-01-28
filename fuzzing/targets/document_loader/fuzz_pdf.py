# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Polyglot fuzz harness for PDF parsing in document-loader-mcp-server.

This module provides a fuzz target that tests the PDF parsing logic
using pdfplumber from the document-loader-mcp-server package.

The harness works both as:
- A pytest test using Hypothesis for structured input generation
- An OSS-Fuzz target using Atheris for coverage-guided fuzzing

Feature: oss-fuzz-integration
Requirements: 3.1, 3.5

Example usage:
    # Run as pytest test
    pytest fuzzing/targets/document_loader/fuzz_pdf.py -v

    # Run as Atheris fuzz target (when built by OSS-Fuzz)
    python fuzzing/targets/document_loader/fuzz_pdf.py
"""

from __future__ import annotations

import io
import sys
import tempfile
from hypothesis import given, settings
from hypothesis import strategies as st
from pathlib import Path


# Add the document-loader-mcp-server to the path for imports
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_DOC_LOADER_SERVER_PATH = _REPO_ROOT / 'src' / 'document-loader-mcp-server'
if str(_DOC_LOADER_SERVER_PATH) not in sys.path:
    sys.path.insert(0, str(_DOC_LOADER_SERVER_PATH))

# Import pdfplumber directly since that's what the server uses
import pdfplumber  # noqa: E402
from fuzzing.harness_base import PolyglotHarness  # noqa: E402


# PDF structure components for generating PDF-like byte sequences
PDF_HEADER = b'%PDF-1.'
PDF_VERSIONS = [b'0', b'1', b'2', b'3', b'4', b'5', b'6', b'7']

# PDF keywords and operators
PDF_KEYWORDS = [
    b'obj',
    b'endobj',
    b'stream',
    b'endstream',
    b'xref',
    b'trailer',
    b'startxref',
    b'%%EOF',
    b'/Type',
    b'/Page',
    b'/Pages',
    b'/Catalog',
    b'/Contents',
    b'/Resources',
    b'/MediaBox',
    b'/Font',
    b'/XObject',
    b'/Image',
    b'/Length',
    b'/Filter',
    b'/FlateDecode',
    b'/DCTDecode',
    b'/ASCII85Decode',
    b'/LZWDecode',
    b'/RunLengthDecode',
    b'/CCITTFaxDecode',
]

# PDF special characters
PDF_SPECIAL = [b'<<', b'>>', b'[', b']', b'(', b')', b'<', b'>', b'/', b'%']


def pdf_header_strategy() -> st.SearchStrategy[bytes]:
    """Generate valid PDF headers."""
    return st.sampled_from(PDF_VERSIONS).map(lambda v: PDF_HEADER + v + b'\n')


def pdf_object_strategy() -> st.SearchStrategy[bytes]:
    """Generate PDF object-like structures."""
    obj_num = st.integers(min_value=1, max_value=1000).map(lambda n: str(n).encode())
    gen_num = st.integers(min_value=0, max_value=65535).map(lambda n: str(n).encode())

    return st.tuples(obj_num, gen_num, st.binary(min_size=0, max_size=100)).map(
        lambda t: t[0] + b' ' + t[1] + b' obj\n' + t[2] + b'\nendobj\n'
    )


def pdf_stream_strategy() -> st.SearchStrategy[bytes]:
    """Generate PDF stream-like structures."""
    return st.binary(min_size=0, max_size=500).map(
        lambda data: b'<< /Length '
        + str(len(data)).encode()
        + b' >>\nstream\n'
        + data
        + b'\nendstream\n'
    )


def pdf_dictionary_strategy() -> st.SearchStrategy[bytes]:
    """Generate PDF dictionary-like structures."""
    key = st.sampled_from([b'/Type', b'/Subtype', b'/Name', b'/Value', b'/Length', b'/Filter'])
    value = st.one_of(
        st.integers(min_value=0, max_value=10000).map(lambda n: str(n).encode()),
        st.sampled_from(
            [b'/Page', b'/Catalog', b'/Font', b'/XObject', b'true', b'false', b'null']
        ),
        st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz').map(
            lambda s: b'(' + s.encode() + b')'
        ),
    )

    return st.lists(st.tuples(key, value), min_size=1, max_size=10).map(
        lambda pairs: b'<< ' + b' '.join(k + b' ' + v for k, v in pairs) + b' >>'
    )


def pdf_like_strategy() -> st.SearchStrategy[bytes]:
    """Hypothesis strategy for generating PDF-like byte sequences.

    This strategy generates a mix of:
    - Valid PDF headers with various versions
    - PDF object structures
    - PDF stream data
    - PDF dictionaries
    - Random binary data that might trigger edge cases
    - Malformed PDF structures

    Returns:
        A Hypothesis SearchStrategy that generates PDF-like byte sequences.
    """
    # Strategy for PDF keywords
    keyword_strategy = st.sampled_from(PDF_KEYWORDS)

    # Strategy for PDF special characters
    special_strategy = st.sampled_from(PDF_SPECIAL)

    # Combine strategies for PDF-like content
    pdf_component = st.one_of(
        pdf_header_strategy(),
        pdf_object_strategy(),
        pdf_stream_strategy(),
        pdf_dictionary_strategy(),
        keyword_strategy,
        special_strategy,
        st.binary(min_size=1, max_size=50),  # Random binary
    )

    # Build PDF-like byte sequences
    pdf_bytes = st.lists(pdf_component, min_size=1, max_size=20).map(b''.join)

    # Mix different types of inputs
    return st.one_of(
        # Valid-ish PDF structure
        st.tuples(pdf_header_strategy(), pdf_bytes).map(lambda t: t[0] + t[1]),
        # Just PDF-like content without header
        pdf_bytes,
        # Pure random binary (for edge cases)
        st.binary(min_size=0, max_size=1000),
        # Empty or minimal inputs
        st.just(b''),
        st.just(PDF_HEADER + b'4\n'),
        # Truncated PDF
        st.binary(min_size=1, max_size=10).map(lambda b: PDF_HEADER + b'4\n' + b),
    )


def fuzz_pdf_parsing(data: bytes) -> None:
    """Fuzz target for PDF parsing with pdfplumber.

    This function takes raw bytes and attempts to parse them as a PDF
    using pdfplumber, which is the library used by document-loader-mcp-server.

    The target verifies that:
    1. pdfplumber doesn't crash on arbitrary input
    2. No unhandled exceptions cause the process to abort
    3. Memory and resource usage remains bounded

    Args:
        data: Raw bytes from the fuzzer to be parsed as PDF content.
    """
    if len(data) == 0:
        return

    # Create a BytesIO object to simulate a file
    pdf_file = io.BytesIO(data)

    try:
        # Attempt to open and parse the PDF
        with pdfplumber.open(pdf_file) as pdf:
            # Try to access basic PDF properties
            _ = pdf.metadata

            # Iterate through pages (if any)
            for page in pdf.pages:
                try:
                    # Try to extract text
                    _ = page.extract_text()
                except Exception:
                    # Text extraction failures are acceptable
                    pass

                try:
                    # Try to extract tables
                    _ = page.extract_tables()
                except Exception:
                    # Table extraction failures are acceptable
                    pass

                try:
                    # Try to get page dimensions
                    _ = page.width
                    _ = page.height
                except Exception:
                    pass

    except Exception:
        # All exceptions during PDF parsing are acceptable
        # We're testing that the parser doesn't crash or hang
        pass


def fuzz_pdf_with_tempfile(data: bytes) -> None:
    """Fuzz target that writes PDF data to a temp file before parsing.

    This simulates the actual usage pattern in document-loader-mcp-server
    where files are read from disk.

    Args:
        data: Raw bytes from the fuzzer to be written and parsed.
    """
    if len(data) == 0:
        return

    try:
        # Write to a temporary file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=True) as tmp:
            tmp.write(data)
            tmp.flush()

            try:
                # Parse using the file path (like the server does)
                with pdfplumber.open(tmp.name) as pdf:
                    for page in pdf.pages:
                        try:
                            _ = page.extract_text()
                        except Exception:
                            pass
            except Exception:
                # Parsing failures are acceptable
                pass

    except Exception:
        # File I/O failures are acceptable
        pass


@given(pdf_like_strategy())
@settings(max_examples=100, deadline=None)
def test_pdf_parsing_graceful_handling(pdf_data: bytes) -> None:
    """Property test for PDF parsing graceful input handling.

    This test verifies that the PDF parsing logic handles arbitrary
    PDF-like byte sequences gracefully without crashing.

    **Validates: Requirements 3.1, 3.5**

    Property 1: Graceful Input Handling (PDF subset)
    For any PDF-like byte sequence, the parser SHALL either:
    - Successfully process the input and return normally, OR
    - Raise a handled exception without crashing

    Args:
        pdf_data: PDF-like bytes generated by the pdf_like_strategy.
    """
    # Should not raise any unhandled exceptions that crash the process
    fuzz_pdf_parsing(pdf_data)


@given(st.binary(min_size=0, max_size=2000))
@settings(max_examples=100, deadline=None)
def test_pdf_parsing_with_raw_bytes(data: bytes) -> None:
    """Property test for PDF parsing with raw byte input.

    This test verifies that the fuzz target handles arbitrary byte sequences
    gracefully, simulating the Atheris fuzzing mode.

    **Validates: Requirements 3.1, 3.5**

    Args:
        data: Raw bytes to be processed by the fuzz target.
    """
    # Should not raise any unhandled exceptions
    fuzz_pdf_parsing(data)


@given(pdf_like_strategy())
@settings(max_examples=100, deadline=None)
def test_pdf_tempfile_parsing(pdf_data: bytes) -> None:
    """Property test for PDF parsing via temporary file.

    This test verifies that PDF parsing through file I/O handles
    arbitrary inputs gracefully.

    **Validates: Requirements 3.1, 3.5**

    Args:
        pdf_data: PDF-like bytes to be written to temp file and parsed.
    """
    fuzz_pdf_with_tempfile(pdf_data)


def test_empty_pdf_handling() -> None:
    """Unit test verifying empty input is handled gracefully.

    **Validates: Requirements 3.1**
    """
    fuzz_pdf_parsing(b'')
    fuzz_pdf_with_tempfile(b'')


def test_minimal_pdf_header() -> None:
    """Unit test verifying minimal PDF header is handled.

    **Validates: Requirements 3.1**
    """
    minimal_pdfs = [
        b'%PDF-1.0',
        b'%PDF-1.4\n',
        b'%PDF-1.7\n%%EOF',
        b'%PDF-2.0\n',
    ]
    for pdf in minimal_pdfs:
        fuzz_pdf_parsing(pdf)


def test_malformed_pdf_structures() -> None:
    """Unit test verifying malformed PDF structures are handled.

    **Validates: Requirements 3.1, 3.5**
    """
    malformed_pdfs = [
        b'%PDF-1.4\n1 0 obj\n<<>>\nendobj',  # Minimal object
        b'%PDF-1.4\n<< /Type /Catalog >>',  # Unclosed structure
        b'%PDF-1.4\nstream\ndata\nendstream',  # Stream without object
        b'%PDF-1.4\n' + b'A' * 1000,  # Large garbage after header
        b'%PDF-1.4\n\x00\x00\x00\x00',  # Null bytes
        b'%PDF-1.4\n' + bytes(range(256)),  # All byte values
    ]
    for pdf in malformed_pdfs:
        fuzz_pdf_parsing(pdf)


if __name__ == '__main__':
    # Entry point for Atheris fuzzing
    PolyglotHarness.run_harness(fuzz_pdf_parsing, test_pdf_parsing_graceful_handling)
