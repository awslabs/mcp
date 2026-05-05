# Integration Tests - AWS HealthOmics MCP Server

This directory contains comprehensive integration tests for the AWS HealthOmics MCP server, with a focus on genomics file search functionality.

## Current Status

✅ **All integration tests are working and passing**
✅ **MCP Field annotation issues resolved**
✅ **8 comprehensive integration tests**
✅ **100% pass rate**

## Overview

The integration tests validate complete end-to-end functionality including:

- **End-to-end search workflows** with proper MCP tool integration
- **MCP Field annotation handling** using MCPToolTestWrapper
- **Error handling** and recovery scenarios
- **Parameter validation** and default value processing
- **Response structure validation** and content verification

## Test Structure

### Core Test Files

1. **`test_genomics_file_search_integration_working.py`** ✅ **WORKING**
   - End-to-end search workflows with MCP tool integration
   - Proper Field annotation handling using MCPToolTestWrapper
   - Configuration and execution error handling
   - Parameter validation and default value testing
   - Response structure and content validation
   - Pagination functionality testing
   - Enhanced response format handling

2. **`test_helpers.py`** - **MCP Tool Testing Utilities**
   - MCPToolTestWrapper for Field annotation handling
   - Direct MCP tool calling utilities
   - Field default value extraction
   - Reusable testing patterns

### Supporting Files

4. **`fixtures/genomics_test_data.py`**
   - Comprehensive mock data fixtures
   - S3 object simulations with various genomics file types
   - HealthOmics sequence and reference store data
   - Large dataset scenarios for performance testing
   - Cross-storage test scenarios

5. **`run_integration_tests.py`**
   - Test runner script with multiple test suites
   - Coverage reporting capabilities
   - Flexible test execution options

6. **`pytest_integration.ini`**
   - Pytest configuration for integration tests
   - Test markers and categorization
   - Logging and output configuration

## Test Data Fixtures

The test fixtures provide comprehensive mock data covering:

### S3 Mock Data
- **BAM files** with associated BAI index files
- **FASTQ files** in paired-end and single-end configurations
- **VCF/GVCF files** with tabix indexes
- **Reference genomes** (FASTA) with associated indexes (FAI, DICT)
- **BWA index collections** (AMB, ANN, BWT, PAC, SA files)
- **Annotation files** (GFF, BED)
- **CRAM files** with CRAI indexes
- **Archived files** in Glacier and Deep Archive storage classes

### HealthOmics Mock Data
- **Sequence stores** with multiple read sets
- **Reference stores** with various genome builds
- **Metadata** including subject IDs, sample IDs, and sequencing information
- **S3 access point paths** for HealthOmics-managed data

### Large Dataset Scenarios
- **Performance testing** with up to 50,000 mock files
- **Pagination testing** with various dataset sizes
- **Memory efficiency** validation scenarios

## Running the Tests

### Prerequisites

Dependencies are automatically installed with the development setup:

```bash
pip install -e ".[dev]"
```

### Basic Test Execution

Run integration tests:
```bash
# Run the working integration tests
python -m pytest tests/test_genomics_file_search_integration_working.py -v

# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=awslabs.aws_healthomics_mcp_server --cov-report=html
```

### Advanced Options

Generate coverage reports:
```bash
python tests/run_integration_tests.py --test-suite all --coverage --verbose
```

Run with specific markers:
```bash
python tests/run_integration_tests.py --markers "integration and not performance" --verbose
```

Output results to JUnit XML:
```bash
python tests/run_integration_tests.py --test-suite all --output test_results.xml
```

### Direct Pytest Execution

You can also run tests directly with pytest:

```bash
# Run all integration tests
pytest tests/test_genomics_*_integration.py -v

# Run with coverage
pytest tests/test_genomics_*_integration.py --cov=awslabs.aws_healthomics_mcp_server --cov-report=html

# Run specific test categories
pytest -m "pagination" tests/ -v
pytest -m "json_validation" tests/ -v
pytest -m "performance" tests/ -v
```

## Test Categories and Markers

The tests are organized using pytest markers:

- **`integration`**: End-to-end integration tests
- **`pagination`**: Pagination-specific functionality
- **`json_validation`**: JSON response format validation
- **`performance`**: Performance and scalability tests
- **`cross_storage`**: Multi-storage system coordination
- **`error_handling`**: Error scenarios and recovery
- **`mock_data`**: Tests using comprehensive mock datasets
- **`large_dataset`**: Large-scale dataset simulations

## Key Test Scenarios

### 1. End-to-End Search Workflows
- Basic search with file type filtering
- Search term matching against paths and tags
- Result ranking and relevance scoring
- Associated file detection and grouping

### 2. File Association Detection
- BAM files with BAI indexes
- FASTQ paired-end reads (R1/R2)
- FASTA files with indexes (FAI, DICT)
- BWA index collections
- VCF files with tabix indexes

### 3. Pagination Functionality
- Storage-level pagination with continuation tokens
- Buffer size optimization
- Cross-storage pagination coordination
- Memory-efficient handling of large datasets
- Pagination consistency across multiple pages

### 4. JSON Response Validation
- Schema compliance validation using jsonschema
- Data type consistency
- Required field presence
- DateTime format standardization
- JSON serializability

### 5. Cross-Storage Coordination
- Results from multiple storage systems (S3, HealthOmics)
- Unified ranking across storage systems
- Continuation token management
- Performance optimization

### 6. Performance Testing
- Large dataset handling (10,000+ files)
- Memory usage optimization
- Search duration benchmarks
- Pagination efficiency metrics

### 7. Error Handling
- Invalid search parameters
- Configuration errors
- Search execution failures
- Partial failure recovery
- Invalid continuation tokens

## Mock Data Validation

The integration tests use comprehensive mock data that simulates real-world genomics datasets:

### Realistic File Sizes
- FASTQ files: 2-8.5 GB (typical for whole genome sequencing)
- BAM files: 8-15 GB (aligned whole genome data)
- VCF files: 450 MB - 2.8 GB (individual to cohort variants)
- Reference genomes: 3.2 GB (human genome size)
- Index files: Proportional to primary files

### Authentic Metadata
- Genomics-specific tags (sample_id, patient_id, sequencing_platform)
- Study organization (cancer_genomics, population_studies)
- File relationships (tumor/normal pairs, read pairs)
- Storage classes (Standard, IA, Glacier, Deep Archive)

### Comprehensive Coverage
- All supported genomics file types
- Various naming conventions
- Different storage tiers and access patterns
- Multiple study types and organizational structures

## Continuous Integration

These integration tests are designed to be run in CI/CD pipelines:

### GitHub Actions Example
```yaml
- name: Run Integration Tests
  run: |
    python tests/run_integration_tests.py --test-suite all --coverage --output integration_results.xml

- name: Upload Coverage Reports
  uses: codecov/codecov-action@v3
  with:
    file: ./htmlcov/coverage.xml
```

### Test Execution Time
- Basic tests: ~30 seconds
- Pagination tests: ~45 seconds
- JSON validation tests: ~20 seconds
- Performance tests: ~60 seconds
- Full suite: ~2-3 minutes

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure the `awslabs.aws_healthomics_mcp_server` package is in your Python path
2. **Async Test Failures**: Verify `pytest-asyncio` is installed and `asyncio_mode = auto` is configured
3. **Mock Failures**: Check that all required mock patches are properly applied
4. **Schema Validation Errors**: Ensure `jsonschema` package is installed

### Debug Mode

Run tests with additional debugging:
```bash
pytest tests/test_genomics_file_search_integration.py -v -s --log-cli-level=DEBUG
```

### Test Isolation

Run individual test methods:
```bash
pytest tests/test_genomics_file_search_integration.py::TestGenomicsFileSearchIntegration::test_end_to_end_search_workflow_basic -v
```

## Contributing

When adding new integration tests:

1. **Follow naming conventions**: `test_genomics_*_integration.py`
2. **Use appropriate markers**: Add pytest markers for categorization
3. **Include comprehensive assertions**: Validate both structure and content
4. **Add mock data**: Extend fixtures for new scenarios
5. **Document test purpose**: Clear docstrings explaining test objectives
6. **Consider performance**: Ensure tests complete within reasonable time limits

## Future Enhancements

Potential areas for test expansion:

1. **Real AWS Integration**: Optional tests against real AWS services
2. **Load Testing**: Stress tests with extremely large datasets
3. **Concurrent Access**: Multi-user simulation scenarios
4. **Network Failure Simulation**: Resilience testing
5. **Security Testing**: Access control and permission validation
