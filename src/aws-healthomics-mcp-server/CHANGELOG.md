# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- **Genomics File Search Tool** - Comprehensive file discovery across multiple storage systems
  - Added `SearchGenomicsFiles` tool for intelligent file discovery across S3 buckets, HealthOmics sequence stores, and reference stores
  - Pattern matching with fuzzy search capabilities for file paths and object tags
  - Automatic file association detection (BAM/BAI indexes, FASTQ R1/R2 pairs, FASTA indexes, BWA index collections)
  - Relevance scoring and ranking system based on pattern match quality, file type relevance, and associated files
  - Support for standard genomics file formats: FASTQ, FASTA, BAM, CRAM, SAM, VCF, GVCF, BCF, BED, GFF, and their indexes
  - Configurable S3 bucket paths via environment variables
  - Structured JSON responses with comprehensive file metadata including storage class, size, and access paths
  - Performance optimizations with parallel searches and result streaming
- S3 URI support for workflow definitions in `CreateAHOWorkflow` and `CreateAHOWorkflowVersion` tools
  - Added `definition_uri` parameter as alternative to `definition_zip_base64`
  - Supports direct reference to workflow definition ZIP files stored in S3
  - Includes validation for S3 URI format and mutual exclusivity with base64 parameter
  - Added comprehensive test coverage for S3 URI functionality
- Initial project setup
