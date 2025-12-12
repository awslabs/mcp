# Unit Tests for ETL Replatforming MCP Server

## Overview

Unit tests follow the **1:1 mapping pattern** - each source file has a corresponding test file. This is the recommended approach for maintainable, discoverable tests.

## Test Structure (1:1 Mapping)

```
awslabs/etl_replatforming_mcp_server/    tests/unit/
├── parsers/                             ├── parsers/
│   ├── airflow_parser.py               │   ├── test_airflow_parser.py
│   ├── step_functions_parser.py        │   ├── test_step_functions_parser.py
│   ├── azure_data_factory_parser.py    │   ├── test_azure_data_factory_parser.py
│   └── base_parser.py                  │   └── test_base_parser.py
├── generators/                          ├── generators/
│   ├── airflow_generator.py            │   ├── test_airflow_generator.py
│   ├── step_functions_generator.py     │   ├── test_step_functions_generator.py
│   └── base_generator.py               │   └── test_base_generator.py
├── models/                              ├── models/
│   ├── flex_workflow.py                │   ├── test_flex_workflow.py
│   ├── llm_config.py                   │   ├── test_llm_config.py
│   └── exceptions.py                   │   └── test_exceptions.py
├── services/                            ├── services/
│   ├── bedrock_service.py              │   ├── test_bedrock_service.py
│   └── response_formatter.py           │   └── test_response_formatter.py
├── utils/                               ├── utils/
│   └── directory_processor.py          │   └── test_directory_processor.py
├── validators/                          ├── validators/
│   └── workflow_validator.py           │   └── test_workflow_validator.py
├── registries.py                        ├── test_registries.py
└── server.py                           └── test_server.py
```

## Architecture Overview

The codebase follows a **simplified layered architecture** with clear separation of concerns:

### **Core Components**
- **`server.py`** - MCP tool definitions and orchestration functions
- **`registries.py`** - Component discovery and instantiation
- **`parsers/`** - Framework → FLEX conversion
- **`generators/`** - FLEX → Framework conversion
- **`services/`** - External service integration (Bedrock, response formatting)
- **`models/`** - Data models and configuration
- **`validators/`** - FLEX workflow validation
- **`utils/`** - File system operations

### **Key Design Principles**
1. **Registry Pattern** - Centralized component discovery eliminates duplication
2. **Single Responsibility** - Each module has one clear purpose
3. **No Unnecessary Layers** - Direct function calls, no handler/service wrappers
4. **Testable Architecture** - All components can be tested in isolation

See [CODE_ORGANIZATION.md](CODE_ORGANIZATION.md) for detailed architecture documentation.

## Benefits of 1:1 Mapping

### 1. **Easy Discovery**
- `airflow_parser.py` → `test_airflow_parser.py`
- No guessing where tests are located
- IDE navigation works seamlessly

### 2. **Clear Responsibility**
- Each test file tests exactly one source file
- Changes to source code have obvious test locations
- Easier code reviews and maintenance

### 3. **Standard Practice**
- Follows Python testing conventions
- Compatible with pytest discovery
- Works well with CI/CD systems

### 4. **Parallel Structure**
- Test directory mirrors source directory
- Easy to add tests for new source files
- Consistent organization

## Adding Tests for New Source Files

### Step 1: Identify Source File Location
```bash
# Source file location
awslabs/etl_replatforming_mcp_server/parsers/prefect_parser.py
```

### Step 2: Create Corresponding Test File
```bash
# Test file location (mirrors source structure)
tests/unit/parsers/test_prefect_parser.py
```

### Step 3: Follow Test Template
```python
#!/usr/bin/env python3

import pytest
from awslabs.etl_replatforming_mcp_server.parsers.prefect_parser import PrefectParser


class TestPrefectParser:
    """Tests for awslabs.etl_replatforming_mcp_server.parsers.prefect_parser"""

    def setup_method(self):
        self.parser = PrefectParser()

    def test_basic_functionality(self):
        """Test basic functionality"""
        # Test implementation
        pass

    def test_error_handling(self):
        """Test error handling"""
        # Test implementation
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

## Test File Naming Convention

### Pattern: `test_<source_filename>.py`
- `airflow_parser.py` → `test_airflow_parser.py`
- `bedrock_service.py` → `test_bedrock_service.py`
- `flex_workflow.py` → `test_flex_workflow.py`

### Class Naming: `Test<ClassName>`
- `AirflowParser` → `TestAirflowParser`
- `BedrockService` → `TestBedrockService`
- `FlexWorkflow` → `TestFlexWorkflow`

### Docstring Pattern
```python
class TestAirflowParser:
    """Tests for awslabs.etl_replatforming_mcp_server.parsers.airflow_parser"""
```

## Running Tests

### Run All Tests
```bash
python -m pytest tests/unit/ -v
```

### Run Tests for Specific Module
```bash
# Test specific parser
python -m pytest tests/unit/parsers/test_airflow_parser.py -v

# Test specific generator
python -m pytest tests/unit/generators/test_step_functions_generator.py -v

# Test specific service
python -m pytest tests/unit/services/test_bedrock_service.py -v
```

### Run Tests by Directory
```bash
# Test all parsers
python -m pytest tests/unit/parsers/ -v

# Test all generators
python -m pytest tests/unit/generators/ -v

# Test all models
python -m pytest tests/unit/models/ -v
```

### Run with Coverage
```bash
# Coverage for specific module
python -m pytest tests/unit/parsers/test_airflow_parser.py --cov=awslabs.etl_replatforming_mcp_server.parsers.airflow_parser

# Coverage for all tests
python -m pytest tests/unit/ --cov=awslabs.etl_replatforming_mcp_server --cov-report=term-missing
```

## Test Categories by Directory

### `tests/unit/parsers/`
- Framework-specific parsing logic
- Input validation and error handling
- Parsing completeness tracking
- Framework-specific features

### `tests/unit/generators/`
- FLEX to target framework conversion
- Schedule generation
- Task type mapping
- Dependency handling

### `tests/unit/models/`
- Data model validation
- Serialization/deserialization
- Model relationships
- Configuration handling

### `tests/unit/services/`
- External service integration
- API communication
- Error handling and retries
- Service configuration

### `tests/unit/utils/`
- Utility functions
- Helper methods
- Common operations
- File processing

### `tests/unit/validators/`
- Validation logic
- Rule enforcement
- Error reporting
- Completeness checking

## Legacy Test Files

Some existing test files don't follow the 1:1 mapping pattern:

```
tests/unit/
├── test_parsers.py                  # Cross-framework parser tests
├── test_generators.py               # Cross-framework generator tests
├── test_single_workflow_tools.py    # MCP tool integration tests
├── test_validation_failures.py      # Validation error scenarios
├── test_schedule_handling.py        # Schedule parsing tests
├── test_parsing_completeness.py     # Parsing completeness tests
├── test_bedrock_ignored_elements.py # Bedrock integration tests
├── test_llm_config.py               # LLM configuration tests
├── test_generator_architecture.py   # Generator architecture tests
├── test_coverage_improvements.py    # Edge cases and coverage
└── test_framework_template.py       # Template for new frameworks
```

These files serve specific purposes:
- **Cross-framework testing** - Testing interfaces across multiple frameworks
- **Integration testing** - Testing component interactions
- **Edge case testing** - Comprehensive coverage scenarios
- **Template files** - Development aids

## Method-Level Coverage Requirement

**Each public method in the source file should have at least one test case.** This ensures comprehensive coverage and catches regressions.

### Coverage Analysis Example

**Source File**: `airflow_parser.py` (25+ methods)
- ✅ `framework_name` → `test_framework_name()`
- ✅ `can_parse()` → `test_can_parse_with_dag_code()`, `test_can_parse_invalid_format()`
- ✅ `parse()` → `test_parse_valid_source_data()`, `test_parse_invalid_source_data()`
- ✅ `parse_code()` → `test_parse_code_basic_dag()`, `test_parse_code_invalid_syntax()`
- ✅ `_extract_dag_info()` → `test_extract_dag_info()`
- ✅ `_map_operator_to_type()` → `test_map_operator_to_type_sql()`, `test_map_operator_to_type_python()`
- ✅ `parse_tasks()` → `test_parse_tasks()`
- ✅ `parse_loops()` → `test_parse_loops_taskgroup()`
- ✅ `analyze_completeness()` → `test_analyze_completeness()`
- ... (all 25+ methods covered)

### Checking Coverage

```bash
# Generate coverage report to identify missing methods
python -m pytest tests/unit/parsers/test_airflow_parser.py --cov=awslabs.etl_replatforming_mcp_server.parsers.airflow_parser --cov-report=term-missing

# Look for uncovered lines - these indicate missing test methods
```

## Best Practices

### 1. One Test Method per Source Method (Minimum)
```python
# Source method
def parse_code(self, input_code: str) -> FlexWorkflow:
    # Implementation

# Test methods (multiple scenarios)
def test_parse_code_basic_dag(self):      # Happy path
def test_parse_code_invalid_syntax(self): # Error case
def test_parse_code_empty_input(self):    # Edge case
```

### 2. Test Method Naming Convention
```python
def test_<method_name>_<scenario>(self):
    # Examples:
    def test_parse_code_basic_dag(self):           # Good: method + scenario
    def test_generate_schedule_cron_expression(self): # Good: method + input type
    def test_can_parse_invalid_format(self):       # Good: method + condition
    def test_parse(self):                          # Bad: Too generic
```

### 3. Cover All Code Paths
```python
# Source method with multiple branches
def _map_operator_to_type(self, operator_name: str) -> str:
    if 'SQL' in operator_name:
        return "sql"
    elif 'Python' in operator_name:
        return "python"
    elif 'Bash' in operator_name:
        return "bash"
    else:
        return "python"  # Default

# Test all branches
def test_map_operator_to_type_sql(self):     # SQL branch
def test_map_operator_to_type_python(self):  # Python branch
def test_map_operator_to_type_bash(self):    # Bash branch
def test_map_operator_to_type_default(self): # Default branch
```

### 4. Test Both Success and Failure Cases
```python
def test_parse_valid_source_data(self):   # Success case
def test_parse_invalid_source_data(self): # Failure case (should raise exception)
```

### 5. Use Setup Methods for Common Data
```python
def setup_method(self):
    self.parser = AirflowParser()
    self.sample_dag = create_sample_dag()
    self.invalid_code = "invalid python {"
```

### 6. Test Private Methods When Complex
```python
# Private methods with complex logic should be tested
def test_extract_dag_info(self):         # Tests _extract_dag_info()
def test_extract_schedule_value(self):   # Tests _extract_schedule_value()
```

## Coverage Verification

### Quick Coverage Check
```bash
# Check if all methods are covered
python -c "
import inspect
from awslabs.etl_replatforming_mcp_server.parsers.airflow_parser import AirflowParser
methods = [m for m in dir(AirflowParser) if not m.startswith('__')]
print(f'Total methods to test: {len(methods)}')
print('Methods:', methods)
"
```

### Coverage Goals
- **100% method coverage** - Every public method has at least one test
- **90%+ line coverage** - Most code paths are tested
- **Edge case coverage** - Error conditions and boundary cases tested

This 1:1 mapping structure with method-level coverage provides comprehensive, maintainable tests that catch regressions and ensure code quality as the codebase grows.
