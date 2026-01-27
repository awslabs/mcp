# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- v0.0.22
  - **ListECRRepositories**: List ECR repositories with HealthOmics accessibility status
  - **CheckContainerAvailability**: Check if a container image is available in ECR and accessible by HealthOmics
  - **CloneContaienrToECR**: Clone a container from a public registry into an ECR repository. Uses pull through caches when they exist otherwise uses CodeBuild to copy the image
  - **CreateContainerRegistryMap**: Creates container registry maps suitable for use when creating a workflow.
  - **GrantHealthOmicsRepositoryAccess**: Grant HealthOmics access to an ECR repository by updating its policy
  - **ListPullThroughCacheRules**: List pull-through cache rules with HealthOmics usability status
  - **CreatePullThroughCacheForHealthOmics**: Create a pull-through cache rule configured for HealthOmics
  - **ValidateHealthOmicsECRConfig**: Validate ECR configuration for HealthOmics workflows

- v0.0.19
  - **Run Timeline Tool** - Generates a GANTT style timeline plot of a run as base64 encoded SVG
  - **Run Analysis Tool** - Adds cost estimation and potential cost saving estimation based on AWS pricing and run duration

- v0.018 **Genomics File Search Tool** - Comprehensive file discovery across multiple storage systems
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
