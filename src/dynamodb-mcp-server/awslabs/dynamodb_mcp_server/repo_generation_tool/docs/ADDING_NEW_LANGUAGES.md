# Adding New Language Support

This guide provides a high-level overview of adding support for a new programming language to the DynamoDB code generation tool.

## 📋 Overview

Adding a new language requires implementing these key components:

1. **Language Configuration** - File patterns, naming conventions, and linter setup
2. **Type Mappings** - Map DynamoDB types to language-specific types
3. **Sample Generators** - Language-specific sample value generation for templates
4. **Templates** - Jinja2 templates for generating entities and repositories
5. **Support Files** - Base classes and configuration files
6. **Integration Tests** - Language-specific test suites
7. **Documentation** - Update CLI and documentation

## 🗂️ Required Directory Structure

For a new language (e.g., TypeScript), create:

```
languages/
└── typescript/
    ├── language_config.json              # Language configuration
    ├── sample_generators.ts               # Language-specific sample value generation
    ├── base_repository.ts                 # Base repository class
    ├── eslint.config.js                   # Linter configuration
    └── templates/                         # Jinja2 templates
        ├── entity_template.j2
        ├── repository_template.j2
        ├── usage_examples_template.j2
        ├── entities_header.j2
        └── repositories_header.j2
```

## 🔧 Implementation Steps

### 1. Language Configuration

Create `languages/{language}/language_config.json` with:

- File extension and naming patterns
- Support files to copy (base classes, linter configs)
- Naming conventions (camelCase, PascalCase, etc.)
- Linter command and configuration

**Reference**: See `languages/python/language_config.json` for structure.

### 2. Type Mappings

Add a new class in `core/type_mappings.py`:

- Map DynamoDB field types to language types
- Map return types for access patterns
- Map parameter types for method signatures
- Add to `TYPE_MAPPERS` dictionary

**Reference**: See `PythonTypeMappings` class for implementation pattern.

### 3. Sample Generators

Create `languages/{language}/sample_generators.{ext}` implementing `LanguageSampleGeneratorInterface`:

- Generate language-specific sample values for template usage
- Provide default values for all DynamoDB field types
- Handle special cases based on field names (IDs, timestamps, etc.)
- Support array types with item type specifications
- Generate both sample and update values

**Key Methods to Implement**:
- `get_sample_value(field_type, field_name, **kwargs)` - Generate sample values
- `get_update_value(field_type, field_name, **kwargs)` - Generate update values
- `get_default_values()` - Return default sample values for all types
- `get_default_update_values()` - Return default update values for all types

**Important Considerations**:
- Handle language-specific type representations (e.g., `Decimal("3.14")` in Python)
- Escape special characters for string formatting (e.g., `{{` for braces)
- Support array types with `item_type` parameter
- Consider field name patterns for context-aware generation (IDs, timestamps)

**Reference**: See `languages/python/sample_generators.py` for implementation pattern.

### 4. Base Repository Class

Create `languages/{language}/base_repository.{ext}`:

- Generic base class with CRUD operations
- Entity configuration interface
- DynamoDB integration (or stubs for implementation)

**Reference**: See `languages/python/base_repository.py` for functionality.

### 5. Jinja2 Templates

Create templates in `languages/{language}/templates/`:

- **Entity template**: Generate entity classes with fields and key builders
- **Repository template**: Generate repository classes with CRUD and access patterns
- **Usage examples template**: Generate sample usage code
- **Header templates**: File headers and imports

**Reference**: See `languages/python/templates/` for template structure and variables.

### 6. Integration Tests

Create language-specific test files:

- `test_{language}_code_generation_pipeline.py` - End-to-end generation testing
- `test_{language}_snapshot_generation.py` - Generated code consistency testing

**Reference**: See `test_python_*.py` files for test structure and patterns.

### 7. Core Integration

Update these core files:

- `codegen.py` - Add language to CLI choices
- `core/language_config.py` - Ensure loader supports new language
- `pyproject.toml` - Add pytest marker for language

### 8. Documentation Updates

Update documentation:

- `README.md` - Add language to support table
- `documentation/TESTING.md` - Add language-specific test commands

## 🧪 Testing Strategy

### Development Testing

```bash
# Test basic generation (from dynamodb-mcp-server root)
uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen --schema sample_schema.json --language {language}

# Test with all options
uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen --schema sample_schema.json --language {language} --generate_sample_usage
```

### Integration Testing

```bash
# Run language-specific tests
uv run pytest tests/repo_generation_tool/ -m {language}

# Create and validate snapshots
python tests/repo_generation_tool/scripts/manage_snapshots.py create --language {language}
python tests/repo_generation_tool/scripts/manage_snapshots.py test
```

## 🎯 Key Considerations

### Language-Specific Features

- **Naming Conventions**: Follow language idioms (camelCase vs snake_case)
- **Type System**: Leverage language type features (generics, interfaces, etc.)
- **Error Handling**: Use language-appropriate error patterns
- **Package Management**: Consider dependency management (npm, maven, etc.)

### Template Variables

Templates have access to:

- `entities` - List of entity configurations
- `table_config` - Table configuration (name, keys)
- `language_config` - Language-specific settings
- `type_mapper` - Type mapping utilities
- `generate_sample_value(field)` - Generate language-specific sample values
- `generate_update_value(field)` - Generate language-specific update values

### Quality Assurance

- **Linting**: Integrate language-specific linters
- **Syntax Validation**: Test generated code compiles/runs
- **Consistency**: Use snapshot testing for regression detection
- **Documentation**: Generate inline documentation and comments

## ✅ Completion Checklist

- [ ] Language configuration file created
- [ ] Type mappings implemented for all DynamoDB types
- [ ] Sample generators class implementing `LanguageSampleGeneratorInterface`
- [ ] Base repository class provides CRUD operations
- [ ] Templates generate syntactically correct code
- [ ] Linter integration produces clean output
- [ ] Integration tests validate generation pipeline
- [ ] Snapshot tests ensure consistency
- [ ] CLI updated with new language option
- [ ] Documentation updated (README, testing docs)
- [ ] Pytest markers configured

## 🔍 Reference Implementation

Use the existing **Python implementation** as a reference:

- `languages/python/` - Complete language implementation
- `tests/repo_generation_tool/integration/test_python_*.py` - Test patterns
- `core/type_mappings.py` - Type mapping implementation

## 🚀 Getting Started

1. **Study the Python implementation** to understand the patterns
2. **Start with configuration** - create the language config file
3. **Implement type mappings** - map all DynamoDB types
4. **Create sample generators** - implement language-specific sample value generation
5. **Create basic templates** - start with simple entity generation
6. **Test incrementally** - validate each component as you build
7. **Add integration tests** - ensure end-to-end functionality
8. **Create snapshots** - establish consistency baselines

---

This modular approach ensures consistency across languages while allowing for language-specific optimizations and idioms.
