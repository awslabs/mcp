# OSS-Fuzz Integration for AWS MCP Servers

This directory contains the fuzzing infrastructure for the AWS MCP Servers monorepo, designed for integration with [Google's OSS-Fuzz](https://github.com/google/oss-fuzz) continuous fuzzing service.

## Overview

The fuzzing infrastructure uses:
- **[Atheris](https://github.com/google/atheris)**: Coverage-guided Python fuzzing engine
- **[Hypothesis](https://hypothesis.readthedocs.io/)**: Property-based testing library
- **Polyglot Harnesses**: Fuzz targets that work both as pytest tests and OSS-Fuzz targets

## Directory Structure

```
fuzzing/
├── targets/              # Fuzz target implementations
│   ├── postgres/         # SQL injection detection fuzzers
│   ├── document_loader/  # Document parsing fuzzers
│   ├── openapi/          # OpenAPI specification fuzzers
│   ├── dynamodb/         # DynamoDB/JSON validation fuzzers
│   ├── aws_api/          # AWS CLI command parsing fuzzers
│   ├── neptune/          # Graph query (Gremlin/SPARQL) fuzzers
│   ├── aws_documentation/# URL and path validation fuzzers
│   ├── mq/               # Amazon MQ message fuzzers
│   ├── sns_sqs/          # SNS/SQS message fuzzers
│   └── core/             # Configuration parsing fuzzers
├── corpus/               # Seed corpus files for each target
├── dictionaries/         # Fuzzing dictionaries (SQL, JSON, etc.)
├── scripts/              # Local build and run scripts
├── tests/                # Infrastructure tests
├── harness_base.py       # Polyglot harness base class
├── classifier.py         # Finding severity classifier
├── coverage_reporter.py  # Coverage report generator
├── project.yaml          # OSS-Fuzz project configuration
├── Dockerfile            # OSS-Fuzz build environment
└── build.sh              # OSS-Fuzz build script
```

## Quick Start

### Prerequisites

- Python 3.10 or later
- pip or uv package manager

### Installation

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install fuzzing package with development dependencies
pip install -e "fuzzing[dev]"

# Optional: Install Atheris for coverage-guided fuzzing
pip install atheris
```

### Running Tests with Hypothesis

The polyglot harnesses can be run as pytest tests using Hypothesis for structured input generation:

```bash
# Run all fuzz tests
pytest fuzzing/tests/ -v

# Run tests for a specific target category
pytest fuzzing/targets/postgres/ -v

# Run with more examples (default is 100)
HYPOTHESIS_MAX_EXAMPLES=500 pytest fuzzing/targets/ -v

# Run with coverage reporting
pytest fuzzing/ --cov=fuzzing --cov-report=html
```

### Running Local Fuzzing with Atheris

For coverage-guided fuzzing locally:

```bash
# Build fuzz targets
./fuzzing/scripts/build_local.sh

# Run a specific fuzz target
./fuzzing/scripts/run_local.sh -t postgres/fuzz_sql_injection -d 60

# Run with verbose output and coverage
./fuzzing/scripts/run_local.sh -t openapi/fuzz_spec_parser -d 120 --coverage -v

# Run as pytest instead of Atheris
./fuzzing/scripts/run_local.sh -t dynamodb/fuzz_json_nesting --pytest --examples 500
```

## Available Fuzz Targets

| Target | Description | Dictionary |
|--------|-------------|------------|
| `postgres/fuzz_sql_injection` | SQL injection detection bypass | `sql.dict` |
| `document_loader/fuzz_pdf` | PDF parsing with malformed content | - |
| `document_loader/fuzz_path_validation` | Path traversal attempts | - |
| `openapi/fuzz_spec_parser` | OpenAPI/Swagger specification parsing | `openapi.dict` |
| `dynamodb/fuzz_item_validation` | DynamoDB item structure validation | `json.dict` |
| `dynamodb/fuzz_json_nesting` | Deeply nested JSON structures | `json.dict` |
| `aws_api/fuzz_command_parser` | AWS CLI command string parsing | `aws_cli.dict` |
| `neptune/fuzz_gremlin` | Gremlin traversal query parsing | `gremlin.dict` |
| `neptune/fuzz_sparql` | SPARQL query parsing | `sparql.dict` |
| `aws_documentation/fuzz_url_validation` | URL parsing and validation | - |
| `aws_documentation/fuzz_path_traversal` | Directory traversal detection | - |
| `mq/fuzz_message_payload` | Amazon MQ message payload parsing | - |
| `sns_sqs/fuzz_message_structure` | SNS/SQS message structure parsing | - |
| `core/fuzz_config_parser` | Configuration structure parsing | `yaml.dict` |
| `core/fuzz_yaml_toml` | YAML and TOML configuration parsing | `yaml.dict`, `toml.dict` |

## Polyglot Harness Architecture

Each fuzz target is implemented as a "polyglot harness" that works in two modes:

1. **Hypothesis Mode** (pytest): Uses Hypothesis strategies for structured input generation
2. **Atheris Mode** (OSS-Fuzz): Consumes raw bytes from the fuzzer

Example harness structure:

```python
from hypothesis import given, strategies as st
from fuzzing.harness_base import PolyglotHarness

# Hypothesis strategy for structured inputs
@given(st.text(min_size=0, max_size=1000))
def test_fuzz_target(input_data: str) -> None:
    """Hypothesis test for local development."""
    fuzz_target(input_data.encode())

def fuzz_target(data: bytes) -> None:
    """Core fuzzing logic used by both modes."""
    # Test the target function with the input
    pass

if __name__ == "__main__":
    # Atheris entry point for OSS-Fuzz
    import atheris
    atheris.Setup(sys.argv, fuzz_target)
    atheris.Fuzz()
```

## OSS-Fuzz Integration

### Project Configuration

The `project.yaml` file configures the OSS-Fuzz project:

```yaml
homepage: "https://github.com/awslabs/mcp"
language: python
fuzzing_engines:
  - libfuzzer
sanitizers:
  - address
  - undefined
```

### Building for OSS-Fuzz

OSS-Fuzz builds the project using the `Dockerfile` and `build.sh`:

```bash
# Test the OSS-Fuzz build locally (requires oss-fuzz repo)
cd /path/to/oss-fuzz
python infra/helper.py build_fuzzers --sanitizer address mcp

# Run a fuzz target
python infra/helper.py run_fuzzer mcp fuzz_sql_injection
```

### Submitting to OSS-Fuzz

To submit this project to OSS-Fuzz:

1. Fork the [oss-fuzz repository](https://github.com/google/oss-fuzz)
2. Create a new project directory: `projects/mcp/`
3. Copy the following files:
   - `fuzzing/project.yaml` → `projects/mcp/project.yaml`
   - `fuzzing/Dockerfile` → `projects/mcp/Dockerfile`
   - `fuzzing/build.sh` → `projects/mcp/build.sh`
4. Submit a pull request to the oss-fuzz repository

For detailed instructions, see the [OSS-Fuzz New Project Guide](https://google.github.io/oss-fuzz/getting-started/new-project-guide/).

## Seed Corpus

Seed corpus files are organized in `corpus/<target_category>/` directories. These provide meaningful starting inputs for the fuzzer:

```bash
# View corpus for a target
ls fuzzing/corpus/postgres/

# Add new corpus entries
echo "SELECT * FROM users WHERE id = 1" > fuzzing/corpus/postgres/valid_select.sql
```

## Dictionaries

Fuzzing dictionaries in `dictionaries/` help the fuzzer generate structured inputs:

- `sql.dict` - SQL keywords and injection tokens
- `json.dict` - JSON syntax tokens
- `yaml.dict` - YAML syntax tokens
- `toml.dict` - TOML syntax tokens
- `openapi.dict` - OpenAPI specification keywords
- `gremlin.dict` - Gremlin graph query tokens
- `sparql.dict` - SPARQL query keywords
- `aws_cli.dict` - AWS CLI options and service names

## Coverage Reporting

Generate coverage reports to identify untested code paths:

```bash
# Run with coverage
pytest fuzzing/ --cov=fuzzing --cov-report=html --cov-report=json

# View HTML report
open htmlcov/index.html

# Use the coverage reporter utility
python -c "from fuzzing.coverage_reporter import CoverageReporter; ..."
```

## Finding Classification

Crashes are classified by severity:

| Severity | Description |
|----------|-------------|
| CRITICAL | Memory corruption, code execution |
| HIGH | Denial of service, information disclosure |
| MEDIUM | Unhandled exceptions in non-security code |
| LOW | Minor issues |

## Development

### Adding a New Fuzz Target

1. Create a new directory in `targets/<category>/`
2. Implement the polyglot harness following the pattern in existing targets
3. Add seed corpus files in `corpus/<category>/`
4. Add or reuse a dictionary in `dictionaries/`
5. Update `build.sh` if needed for dictionary mapping
6. Run tests to verify: `pytest fuzzing/targets/<category>/ -v`

### Running Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Run on all fuzzing files
pre-commit run --files fuzzing/**/*.py
```

## Troubleshooting

### Atheris Not Found

```bash
pip install atheris
```

Note: Atheris requires a compatible C++ compiler. On macOS, ensure Xcode Command Line Tools are installed.

### Import Errors

Ensure the Python path includes the repository root:

```bash
export PYTHONPATH="${PWD}:${PWD}/src:${PYTHONPATH:-}"
```

### Slow Fuzzing

- Increase timeout: `-d 300` (5 minutes)
- Use a seed corpus for faster coverage
- Check for expensive operations in the target function

## License

This project is licensed under the Apache License 2.0. See [LICENSE](../LICENSE) for details.

## References

- [OSS-Fuzz Documentation](https://google.github.io/oss-fuzz/)
- [Atheris GitHub](https://github.com/google/atheris)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [libFuzzer Documentation](https://llvm.org/docs/LibFuzzer.html)
