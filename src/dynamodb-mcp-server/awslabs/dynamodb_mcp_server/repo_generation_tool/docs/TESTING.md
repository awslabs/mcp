# Testing Framework

The system includes comprehensive testing at three levels to ensure reliability and catch regressions:

## Test Types

| Test Type             | Purpose                  | Speed  | Focus                            |
| --------------------- | ------------------------ | ------ | -------------------------------- |
| **Unit Tests**        | Component isolation      | Fast   | Individual modules and functions |
| **Integration Tests** | End-to-end functionality | Medium | Complete generation pipeline     |
| **Snapshot Tests**    | Output consistency       | Fast   | Generated code format stability  |

## Unit Tests (~100 tests)

Test individual components in isolation:

- **Schema Loading**: Validates JSON parsing and error handling
- **Language Configuration**: Tests language-specific settings and templates
- **Code Generation**: Verifies template rendering and output creation
- **Access Pattern Mapping**: Tests pattern conflict detection and resolution
- **Type Mappings**: Validates language-specific type conversions
- **Validation Logic**: Tests schema validation rules and error messages

```bash
# Run all unit tests
uv run pytest tests/repo_generation_tool/unit/ -v

# Run specific component tests
uv run pytest tests/repo_generation_tool/unit/test_schema_loader.py -v
uv run pytest tests/repo_generation_tool/unit/test_jinja2_generator.py -v
```

## Integration Tests (~25 tests)

Test complete end-to-end functionality:

- **CLI Integration**: Tests all command-line options and error handling
- **Generation Pipeline**: Validates complete schema-to-code generation
- **Multi-Schema Support**: Tests different schema types and patterns
- **Language Support**: Verifies language-specific generation
- **File Operations**: Tests output management and file creation

```bash
# Run all integration tests
uv run pytest tests/repo_generation_tool/integration/ -v

# Run CLI-specific tests
uv run pytest tests/repo_generation_tool/integration/test_cli_integration.py -v

# Run Python pipeline tests
uv run pytest tests/repo_generation_tool/integration/test_python_code_generation_pipeline.py -v
```

## Snapshot Tests (8 tests)

Detect changes in generated code output:

- **Template Consistency**: Ensures template changes produce expected results
- **Format Stability**: Catches unintended changes in code structure
- **Language-Specific Output**: Validates language-specific code generation
- **Regression Detection**: Prevents accidental output modifications

```bash
# Run Python snapshot tests
uv run pytest tests/repo_generation_tool/integration/test_python_snapshot_generation.py -v

# Manage snapshots
python tests/repo_generation_tool/scripts/manage_snapshots.py list
python tests/repo_generation_tool/scripts/manage_snapshots.py create --language python
python tests/repo_generation_tool/scripts/manage_snapshots.py test
```

## Development Workflow

```bash
# Development workflow (marker-based)
uv run pytest tests/repo_generation_tool/ -m unit -v       # ← Verify components work
uv run pytest tests/repo_generation_tool/ -m integration -v # ← Verify functionality works
uv run tests/repo_generation_tool/scripts/manage_snapshots.py test  # ← Verify output unchanged

# Alternative: Directory-based workflow
uv run pytest tests/repo_generation_tool/unit/ -v          # ← Verify components work
uv run pytest tests/repo_generation_tool/integration/ -v   # ← Verify functionality works
uv run tests/repo_generation_tool/scripts/manage_snapshots.py test  # ← Verify output unchanged

# Template change workflow
1. Edit template files
2. uv run pytest tests/repo_generation_tool/ -m integration -v  # ← Still works?
3. uv run tests/repo_generation_tool/scripts/manage_snapshots.py test  # ← What changed?
4. Review diffs in test output                               # ← Intentional?
5. uv run tests/repo_generation_tool/scripts/manage_snapshots.py create  # ← Accept changes
```

## Pre-Push Checklist

```bash
# Quick validation (30 seconds) - run before every push
uv run pytest tests/repo_generation_tool/ --tb=no -q                    # ← All 134 tests pass?
uv run tests/repo_generation_tool/scripts/manage_snapshots.py test      # ← Output unchanged?

# If snapshots differ and changes are intentional:
uv run tests/repo_generation_tool/scripts/manage_snapshots.py create    # ← Accept new output

# Alternative: Run specific test categories
uv run pytest tests/repo_generation_tool/ -m unit -q                    # ← Fast unit tests only
uv run pytest tests/repo_generation_tool/ -m integration -q             # ← Integration + snapshots
```

## Test Commands

### Running Tests by Category

```bash
# 1. Run Everything (Including Snapshots)
# This runs ALL tests: unit + integration + snapshots
uv run pytest tests/repo_generation_tool/ -v

# 2. Run Only Unit Tests (Fast)
# Only fast, isolated unit tests
uv run pytest tests/repo_generation_tool/ -m unit -v

# 3. Run Only Integration Tests (Including Snapshots)
# Integration + snapshot tests (slower but comprehensive)
uv run pytest tests/repo_generation_tool/ -m integration -v

# 4. Run Only Snapshot Tests
# Only snapshot consistency tests
uv run pytest tests/repo_generation_tool/ -m snapshot -v

# 5. Run Non-Snapshot Tests
# Everything except snapshots
uv run pytest tests/repo_generation_tool/ -m "not snapshot" -v
```

### Running Tests by Directory

```bash
# Run by test type (directory-based)
uv run pytest tests/repo_generation_tool/unit/ -v          # Unit tests only
uv run pytest tests/repo_generation_tool/integration/ -v   # Integration tests only

# Run specific test files
uv run pytest tests/repo_generation_tool/unit/test_schema_loader.py -v
uv run pytest tests/repo_generation_tool/integration/test_cli_integration.py -v
```

### Snapshot Management Commands

```bash
# Validate all snapshots (syntax check)
uv run tests/repo_generation_tool/scripts/manage_snapshots.py validate

# Run snapshot tests specifically
uv run tests/repo_generation_tool/scripts/manage_snapshots.py test

# Update all snapshots (when templates change)
uv run tests/repo_generation_tool/scripts/manage_snapshots.py create --language python

# List and manage specific snapshots
uv run tests/repo_generation_tool/scripts/manage_snapshots.py list --language python
uv run tests/repo_generation_tool/scripts/manage_snapshots.py create social_media --language python
```

### Quick Reference

| Command                                                       | Purpose                 | Speed  | Use Case              |
| ------------------------------------------------------------- | ----------------------- | ------ | --------------------- |
| `uv run pytest tests/repo_generation_tool/ -v`                | All tests               | Medium | Pre-commit validation |
| `uv run pytest tests/repo_generation_tool/ -m unit -v`        | Unit only               | Fast   | Development feedback  |
| `uv run pytest tests/repo_generation_tool/ -m integration -v` | Integration + snapshots | Slow   | Template changes      |
| `uv run pytest tests/repo_generation_tool/ -m snapshot -v`    | Snapshots only          | Fast   | Output validation     |
| `uv run pytest tests/repo_generation_tool/ -q --tb=short`     | All tests (quiet)       | Medium | CI/CD pipeline        |

## Snapshot Testing

Snapshot tests ensure generated code consistency across template changes:

### Fixture Files with Realistic Data

The test fixtures in `tests/repo_generation_tool/fixtures/` include both schema files in `valid_schemas/` and corresponding `usage_data.json` files in `valid_usage_data/` with realistic sample data:

```
fixtures/
├── valid_schemas/
│   ├── deals_app/
│   │   ├── deals_schema.json
│   │   └── README.md
│   ├── ecommerce_app/
│   │   ├── ecommerce_schema.json
│   │   └── README.md
│   ├── elearning_platform/
│   │   ├── elearning_schema.json
│   │   └── README.md
│   ├── gaming_leaderboard/
│   │   ├── gaming_leaderboard_schema.json
│   │   └── README.md
│   ├── saas_app/
│   │   ├── project_management_schema.json
│   │   └── README.md
│   ├── social_media_app/
│   │   ├── social_media_app_schema.json
│   │   └── README.md
│   └── user_analytics/
│       ├── user_analytics_schema.json
│       └── README.md
└── valid_usage_data/
    ├── deals_app/
    │   └── deals_usage_data.json          # Realistic sample data for deals domain
    ├── ecommerce_app/
    │   └── ecommerce_usage_data.json      # Realistic sample data for e-commerce
    ├── elearning_platform/
    │   └── elearning_usage_data.json      # Realistic sample data for e-learning
    ├── gaming_leaderboard/
    │   └── gaming_leaderboard_usage_data.json  # Realistic sample data for gaming
    ├── saas_app/
    │   └── project_management_usage_data.json  # Realistic sample data for project management
    ├── social_media_app/
    │   └── social_media_app_usage_data.json  # Realistic sample data for social media
    └── user_analytics/
        └── user_analytics_usage_data.json  # Realistic sample data for user analytics
```

**Snapshot Tests with Realistic Data:**

Snapshot tests automatically use the `usage_data.json` files when generating code, ensuring that:

- Generated `usage_examples.py` files contain realistic business values instead of generic placeholders
- Snapshot comparisons reflect actual usage patterns with domain-specific data
- Template changes are validated against realistic code examples
- Regression testing includes verification of realistic data integration

This means snapshot tests validate not just the code structure, but also the realistic data integration throughout the generated examples.

### When snapshots are used:

- Template modifications that change generated code structure
- Code reviews to visualize the impact of changes
- Regression testing to ensure consistent output
- CI/CD pipelines for automated validation

### Snapshot workflow:

1. **First run**: Creates snapshots automatically if they don't exist
2. **Subsequent runs**: Compares generated output against stored snapshots
3. **Failures**: Shows detailed diffs and provides update instructions
4. **Updates**: Regenerate snapshots when changes are intentional

### How snapshots are managed:

- **Automatic Creation**: The `expected_outputs/` directory is populated automatically by snapshot tests
- **First Test Run**: If no snapshot exists, the test generates code and creates the snapshot file
- **No Manual Setup**: You don't need to manually create or populate snapshot files
- **Test-Driven**: Snapshots are created by running `uv run pytest tests/repo_generation_tool/integration/test_python_snapshot_generation.py`
- **Manual Management**: Use `manage_snapshots.py` script only when you need to update existing snapshots

### Language-specific snapshots:

```
tests/repo_generation_tool/fixtures/expected_outputs/
├── python/                    # Python language snapshots
│   ├── social_media/         # Schema-specific outputs
│   ├── ecommerce/
│   ├── elearning/
│   ├── gaming_leaderboard/
│   └── saas/
└── typescript/               # Future: TypeScript snapshots
```

Each schema directory contains:

- `entities.py` - Generated entity classes
- `repositories.py` - Generated repository classes
- `usage_examples.py` - Generated usage examples
- `access_pattern_mapping.json` - Access pattern mapping
- `base_repository.py` - Base repository support file
- `ruff.toml` - Linting configuration

## Snapshot Management

### Creating and Updating Snapshots

```bash
# Create snapshots for all schemas (Python by default)
python tests/repo_generation_tool/scripts/manage_snapshots.py create

# Create snapshots for specific schemas and language
python tests/repo_generation_tool/scripts/manage_snapshots.py create social_media ecommerce --language python

# Delete and regenerate for specific language
python tests/repo_generation_tool/scripts/manage_snapshots.py delete social_media --language python
python tests/repo_generation_tool/scripts/manage_snapshots.py create social_media --language python

# Recreate all snapshots for Python
python tests/repo_generation_tool/scripts/manage_snapshots.py delete --language python
python tests/repo_generation_tool/scripts/manage_snapshots.py create --language python
```

### Validating Snapshots

```bash
# Check that all snapshots have valid syntax
python tests/repo_generation_tool/scripts/manage_snapshots.py validate

# List all snapshots (all languages)
python tests/repo_generation_tool/scripts/manage_snapshots.py list

# List snapshots for specific language
python tests/repo_generation_tool/scripts/manage_snapshots.py list --language python
```

### Workflow for Template Changes

**Before making changes:**

```bash
# Ensure current snapshots are up to date
python tests/repo_generation_tool/scripts/manage_snapshots.py test
```

**After making template changes:**

```bash
# Run Python snapshot tests to see what changed
pytest tests/repo_generation_tool/integration/test_python_snapshot_generation.py -m snapshot -v

# If changes are intentional, update snapshots
python tests/repo_generation_tool/scripts/manage_snapshots.py create

# Verify updated snapshots
python tests/repo_generation_tool/scripts/manage_snapshots.py test
```

### Best Practices

**✅ Do:**

- Review snapshot diffs carefully before updating
- Update snapshots only when changes are intentional
- Include snapshot updates in the same commit as template changes
- Run snapshot tests before and after template modifications

**❌ Don't:**

- Update snapshots without understanding why they changed
- Commit snapshot updates without reviewing the diffs
- Ignore snapshot test failures

### CI/CD Integration

Include snapshot tests in your CI pipeline:

```yaml
# Example GitHub Actions step
- name: Run Snapshot Tests
  run: |
    python tests/repo_generation_tool/scripts/manage_snapshots.py test
```

### Schema Coverage

**Current Python snapshots:**

- **social_media**: Single-table design with complex relationships
- **ecommerce**: Multi-table design with cross-references
- **elearning**: Multi-tenant single-table design
- **gaming_leaderboard**: Numeric sort keys for score-based ranking
- **saas**: Project management with hierarchical data

**Adding new language snapshots:**

1. Implement language support in `languages/` directory
2. Create snapshots: `python manage_snapshots.py create --language new_language`
3. Add test cases to language-specific test files

**Adding new schema snapshots:**

1. Add schema to `manage_snapshots.py`
2. Create snapshot: `python manage_snapshots.py create new_schema --language python`
3. Add test case to appropriate test files
