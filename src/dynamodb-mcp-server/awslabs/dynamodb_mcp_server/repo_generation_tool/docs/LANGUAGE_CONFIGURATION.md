# Language Configuration System

The generator supports multiple programming languages through a flexible configuration system. Each language defines its own file patterns, support files, and tooling.

## Language Configuration Structure

```json
{
  "name": "python",
  "file_extension": ".py",
  "file_patterns": {
    "entities": "entities.py",
    "repositories": "repositories.py",
    "usage_examples": "usage_examples.py"
  },
  "support_files": [
    {
      "source": "base_repository.py",
      "dest": "base_repository.py",
      "description": "Base repository class",
      "category": "config"
    },
    {
      "source": "ruff.toml",
      "dest": "ruff.toml",
      "description": "Linting configuration",
      "category": "linter_config"
    }
  ],
  "linter": {
    "command": ["uv", "run", "ruff"],
    "check_args": ["check"],
    "fix_args": ["check", "--fix"],
    "format_command": ["uv", "run", "ruff", "format"],
    "config_file": "ruff.toml"
  }
}
```

## Language Support

| Language       | Status          | File Extension | Linter       | Notes                                        |
| -------------- | --------------- | -------------- | ------------ | -------------------------------------------- |
| **Python**     | ✅ Full Support | `.py`          | Ruff         | Complete implementation with type hints      |
| **TypeScript** | 🚧 Planned      | `.ts`          | ESLint       | Interface-based entities, class repositories |
| **Java**       | 🚧 Planned      | `.java`        | Checkstyle   | One class per file, Maven integration        |
| **C#**         | 🚧 Planned      | `.cs`          | EditorConfig | Namespace organization, NuGet packages       |

## Adding New Languages

1. Create language directory: `languages/{language}/`
2. Add `language_config.json` with file patterns and linter config
3. Implement `sample_generators.{ext}` with `LanguageSampleGeneratorInterface`
4. Create language-specific templates in `templates/` subdirectory
5. Add support files (base classes, config files)
6. Test with sample schema

## Generated Code Structure

```
generated/
├── python/                        # Python-specific generated code
│   ├── entities.py                # All entity classes with Pydantic validation
│   ├── repositories.py            # All repository classes with CRUD + access patterns
│   ├── base_repository.py         # Base repository class (copied from source)
│   ├── ruff.toml                  # Linting configuration for generated code
│   ├── access_pattern_mapping.json # Complete mapping of all access patterns for testing
│   └── usage_examples.py          # Interactive examples (with --generate_sample_usage flag)
├── typescript/                    # Future: TypeScript-specific generated code
└── java/                          # Future: Java-specific generated code
```

## File Manifest System

The generator uses a flexible file manifest system that supports any file organization pattern:

```python
@dataclass
class GeneratedFile:
    path: str        # Any file path: "entities.py", "models/User.java", "types/user.ts"
    description: str # Human-readable description
    category: str    # Logical grouping: "entities", "repositories", "config", "examples"
    content: str     # Complete file content
    count: int = 0   # Optional count for summary
```

**Benefits:**

- **Language-agnostic**: Works with any file extension or naming convention
- **Flexible organization**: Supports single files, multiple files, or nested directories
- **Rich metadata**: Each file has description, category, and optional count
- **Future-proof**: Ready for any language's file organization patterns

## Multi-Language Support

The generator supports multiple programming languages through language-specific directories:

```
python/                  # Python-specific files
├── sample_generators.py        # Language-specific sample value generation
├── base_repository.py
├── ruff.toml
└── templates/
    ├── entity_template.j2
    ├── repository_template.j2
    └── usage_examples_template.j2  # Generates schema-specific examples
typescript/              # Future: TypeScript-specific files
├── sample_generators.ts        # TypeScript sample value generation
├── base_repository.ts
├── eslint.config.js
└── templates/
    └── usage_examples_template.j2  # Generates TypeScript examples
java/                    # Future: Java-specific files
├── SampleGenerators.java       # Java sample value generation
├── BaseRepository.java
├── checkstyle.xml
└── templates/
    └── usage_examples_template.j2  # Generates Java examples
```

**Currently Supported:**

- ✅ **Python** - Full support with modern Python 3.10+ syntax

**Planned:**

- 🚧 **TypeScript** - Coming soon
- 🚧 **Java** - Coming soon

## Sample Generators System

Each language implements a sample generator class that provides language-specific sample values for templates:

```python
# Example: Python Sample Generator
class PythonSampleGenerator(LanguageSampleGeneratorInterface):
    def get_sample_value(self, field_type: str, field_name: str, **kwargs) -> str:
        # Returns Python-specific sample values like 'Decimal("3.14")'

    def get_update_value(self, field_type: str, field_name: str, **kwargs) -> str:
        # Returns Python-specific update values

    def get_default_values(self) -> Dict[str, str]:
        # Returns default sample values for all field types

    def get_default_update_values(self) -> Dict[str, str]:
        # Returns default update values for all field types
```

**Key Features:**
- **Language-Agnostic Templates**: Templates use `generate_sample_value()` functions instead of hardcoded values
- **Type-Aware**: Handles language-specific type representations (e.g., `Decimal("3.14")` in Python)
- **Context-Aware**: Generates different values based on field names (IDs, timestamps, etc.)
- **Extensible**: Easy to add new field types or special cases

## Language-Aware Features

- **Smart Linting**: Automatically detects and runs the appropriate linter for each language
- **Conditional Linting**: Only runs if linter configuration file exists
- **Language-Specific Output**: File names, extensions, and organization based on language config
- **Support File Management**: Automatically copies language-specific base classes and config files
- **Sample Value Generation**: Language-specific sample data generation for templates

## Self-Contained Output

- **Complete Dependencies**: All required files copied to generated folder
- **Portable Code**: Generated folder can be moved anywhere and used independently
- **No External References**: All imports resolved within generated folder
- **Code Quality**: Integrated linting with ruff enabled by default for clean, consistent code

## Template System

### Template Directory Structure

```
languages/{language}/templates/
├── entity_template.j2           # Entity class generation
├── repository_template.j2       # Repository class generation
├── usage_examples_template.j2   # Usage examples generation
├── entities_header.j2           # Header for entities file
└── repositories_header.j2       # Header for repositories file
```

### Template Variables

Templates have access to:

- `entities` - List of all entity configurations
- `table_config` - Table configuration (name, keys)
- `language_config` - Language-specific settings
- `access_patterns` - Mapped access patterns
- `type_mapper` - Language-specific type mappings
- `generate_sample_value(field)` - Generate language-specific sample values
- `generate_update_value(field)` - Generate language-specific update values

### Custom Templates

1. **Create Templates**: Add custom `.j2` files to templates directory
2. **Modify Generator**: Update `generators.py` to use custom templates
3. **Generate**: Use `--templates-dir` option

```bash
# Use custom templates (from dynamodb-mcp-server root)
uv run python -m awslabs.dynamodb_mcp_server.repo_generation_tool.codegen --schema schema.json --templates-dir custom/templates/
```
