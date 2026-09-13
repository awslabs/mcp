# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security
- Fixed a path containment bypass in the `DOCUMENT_BASE_DIR` sandbox (CVE pending).
  `_get_base_directory()` previously returned the filesystem root (`/`) whenever
  the ambient `CI`, `GITHUB_ACTIONS`, or `PYTEST_CURRENT_TEST` environment
  variables were present, silently disabling path containment for
  `read_document`, `read_image`, and `extract_slides_as_images`. Because CI
  platforms set these variables unconditionally, standard CI/CD deployments lost
  the sandbox with no log warning, leaving only the file-extension allowlist as a
  guard. The sandbox is now always enforced: file access is restricted to
  `DOCUMENT_BASE_DIR` when set, otherwise the current working directory, with no
  environment-based bypass.
- Base directory paths are now resolved to canonical (symlink-free) form before
  containment checks.

### Fixed
- Deployments relying on the default (current working directory) sandbox no
  longer have it disabled when running under CI. Deployments that need broader
  access must set `DOCUMENT_BASE_DIR` explicitly.

## [1.0.0] - 2025-09-10

### Added
- Initial public release of Document Loader MCP Server for AWS Labs MCP repository
- PDF text extraction using pdfplumber
- Word document processing (DOCX/DOC) using markitdown
- Excel spreadsheet reading (XLSX/XLS) using markitdown
- PowerPoint presentation processing (PPTX/PPT) using markitdown
- Image loading support for PNG, JPG, JPEG, GIF, BMP, TIFF, WEBP formats
- Comprehensive test suite with sample document generation
- FastMCP framework integration for MCP protocol support

### Features
- `read_document`: Unified document processing tool supporting PDF, Word, Excel, and PowerPoint formats
- `read_image`: Load and display image files for LLM analysis

### Technical Details
- Built with FastMCP framework for MCP protocol compliance
- Uses pdfplumber for reliable PDF text extraction
- Uses markitdown library for Office document conversion
- Supports Python 3.10+ with comprehensive error handling
- Includes automated test generation for validation
