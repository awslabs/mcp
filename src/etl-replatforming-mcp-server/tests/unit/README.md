# Unit Tests

Fast, isolated tests for individual components.

## Test Files

- `test_bedrock_service.py` - Bedrock AI service tests
- `test_generators.py` - Framework code generators tests  
- `test_llm_config.py` - LLM configuration model tests
- `test_naming_conventions.py` - Naming conventions tests
- `test_parsers.py` - Source framework parsers tests
- `test_server.py` - MCP server function tests
- `test_single_workflow_tools.py` - Single workflow MCP tools tests

## Running Unit Tests

```bash
# All unit tests
python -m pytest tests/unit/ -v

# Specific test file
python -m pytest tests/unit/test_generators.py -v
```