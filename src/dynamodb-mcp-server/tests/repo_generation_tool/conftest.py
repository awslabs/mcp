"""Shared fixtures for repo_generation_tool tests."""

import pytest
import subprocess
from pathlib import Path


# ============================================================================
# MODULE CONSTANTS
# ============================================================================

FIXTURES_DIR = Path(__file__).parent / 'fixtures'
VALID_SCHEMAS_DIR = FIXTURES_DIR / 'valid_schemas'
VALID_USAGE_DATA_DIR = FIXTURES_DIR / 'valid_usage_data'
INVALID_SCHEMAS_DIR = FIXTURES_DIR / 'invalid_schemas'
INVALID_USAGE_DATA_DIR = FIXTURES_DIR / 'invalid_usage_data'

# Social Media App
SOCIAL_MEDIA_SCHEMA = VALID_SCHEMAS_DIR / 'social_media_app' / 'social_media_app_schema.json'
SOCIAL_MEDIA_USAGE_DATA = (
    VALID_USAGE_DATA_DIR / 'social_media_app' / 'social_media_app_usage_data.json'
)

# Ecommerce App
ECOMMERCE_SCHEMA = VALID_SCHEMAS_DIR / 'ecommerce_app' / 'ecommerce_schema.json'
ECOMMERCE_USAGE_DATA = VALID_USAGE_DATA_DIR / 'ecommerce_app' / 'ecommerce_usage_data.json'

# E-Learning Platform
ELEARNING_SCHEMA = VALID_SCHEMAS_DIR / 'elearning_platform' / 'elearning_schema.json'
ELEARNING_USAGE_DATA = VALID_USAGE_DATA_DIR / 'elearning_platform' / 'elearning_usage_data.json'

# Gaming Leaderboard
GAMING_LEADERBOARD_SCHEMA = (
    VALID_SCHEMAS_DIR / 'gaming_leaderboard' / 'gaming_leaderboard_schema.json'
)
GAMING_LEADERBOARD_USAGE_DATA = (
    VALID_USAGE_DATA_DIR / 'gaming_leaderboard' / 'gaming_leaderboard_usage_data.json'
)

# SaaS App
SAAS_SCHEMA = VALID_SCHEMAS_DIR / 'saas_app' / 'project_management_schema.json'
SAAS_USAGE_DATA = VALID_USAGE_DATA_DIR / 'saas_app' / 'project_management_usage_data.json'

# User Analytics
USER_ANALYTICS_SCHEMA = VALID_SCHEMAS_DIR / 'user_analytics' / 'user_analytics_schema.json'
USER_ANALYTICS_USAGE_DATA = (
    VALID_USAGE_DATA_DIR / 'user_analytics' / 'user_analytics_usage_data.json'
)

# Deals App
DEALS_SCHEMA = VALID_SCHEMAS_DIR / 'deals_app' / 'deals_schema.json'
DEALS_USAGE_DATA = VALID_USAGE_DATA_DIR / 'deals_app' / 'deals_usage_data.json'

# Invalid Schemas
INVALID_COMPREHENSIVE_SCHEMA = INVALID_SCHEMAS_DIR / 'comprehensive_invalid_schema.json'
INVALID_ENTITY_REF_SCHEMA = INVALID_SCHEMAS_DIR / 'test_entity_ref_schema.json'
INVALID_CROSS_TABLE_SCHEMA = INVALID_SCHEMAS_DIR / 'test_cross_table_refs.json'
INVALID_GSI_SCHEMA = INVALID_SCHEMAS_DIR / 'invalid_gsi_schema.json'


# ============================================================================
# SHARED FIXTURES (used by both unit and integration tests)
# ============================================================================


@pytest.fixture(scope='session')
def repo_generation_tool_path():
    """Path to the repo_generation_tool directory."""
    return (
        Path(__file__).parent.parent.parent
        / 'awslabs'
        / 'dynamodb_mcp_server'
        / 'repo_generation_tool'
    )


@pytest.fixture(scope='session')
def sample_schemas():
    """Sample schema paths for testing."""
    return {
        'social_media': SOCIAL_MEDIA_SCHEMA,
        'ecommerce': ECOMMERCE_SCHEMA,
        'elearning': ELEARNING_SCHEMA,
        'gaming_leaderboard': GAMING_LEADERBOARD_SCHEMA,
        'saas': SAAS_SCHEMA,
        'user_analytics': USER_ANALYTICS_SCHEMA,
        'deals': DEALS_SCHEMA,
        'invalid_comprehensive': INVALID_COMPREHENSIVE_SCHEMA,
        'invalid_entity_ref': INVALID_ENTITY_REF_SCHEMA,
        'invalid_cross_table': INVALID_CROSS_TABLE_SCHEMA,
        'invalid_gsi': INVALID_GSI_SCHEMA,
    }


# ============================================================================
# UNIT TEST SPECIFIC FIXTURES
# ============================================================================


@pytest.fixture
def mock_schema_data():
    """Mock schema data for unit tests - no file I/O needed."""
    return {
        'tables': [
            {
                'table_config': {
                    'table_name': 'TestTable',
                    'partition_key': 'pk',
                    'sort_key': 'sk',
                },
                'entities': {
                    'TestEntity': {
                        'entity_type': 'TEST',
                        'pk_template': '{id}',
                        'sk_template': 'ENTITY',
                        'fields': [
                            {'name': 'id', 'type': 'string', 'required': True},
                            {'name': 'name', 'type': 'string', 'required': True},
                        ],
                        'access_patterns': [],
                    }
                },
            }
        ]
    }


@pytest.fixture
def mock_language_config():
    """Mock language configuration for unit tests."""
    from awslabs.dynamodb_mcp_server.repo_generation_tool.core.language_config import (
        LanguageConfig,
        LinterConfig,
        NamingConventions,
    )

    naming_conventions = NamingConventions(
        method_naming='snake_case',
        crud_patterns={
            'create': 'create_{entity_name}',
            'get': 'get_{entity_name}',
            'update': 'update_{entity_name}',
            'delete': 'delete_{entity_name}',
        },
    )

    linter_config = LinterConfig(
        command=['ruff'],
        check_args=['check'],
        fix_args=['check', '--fix'],
        format_command=['ruff', 'format'],
        config_file='ruff.toml',
    )

    return LanguageConfig(
        name='python',
        file_extension='.py',
        naming_conventions=naming_conventions,
        file_patterns={'entities': 'entities.py', 'repositories': 'repositories.py'},
        support_files=[],
        linter=linter_config,
    )


# ============================================================================
# INTEGRATION TEST SPECIFIC FIXTURES
# ============================================================================


@pytest.fixture
def generation_output_dir(tmp_path):
    """Clean temporary directory for integration test file generation."""
    output_dir = tmp_path / 'generated_output'
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def code_generator(repo_generation_tool_path):
    """Helper function to run code generation for integration tests."""
    # Map schema paths to their corresponding usage data paths
    schema_to_usage_data = {
        SOCIAL_MEDIA_SCHEMA: SOCIAL_MEDIA_USAGE_DATA,
        ECOMMERCE_SCHEMA: ECOMMERCE_USAGE_DATA,
        ELEARNING_SCHEMA: ELEARNING_USAGE_DATA,
        GAMING_LEADERBOARD_SCHEMA: GAMING_LEADERBOARD_USAGE_DATA,
        SAAS_SCHEMA: SAAS_USAGE_DATA,
        USER_ANALYTICS_SCHEMA: USER_ANALYTICS_USAGE_DATA,
        DEALS_SCHEMA: DEALS_USAGE_DATA,
    }

    def _generate_code(
        schema_path: Path, output_dir: Path, **kwargs
    ) -> subprocess.CompletedProcess:
        """Run code generation and return subprocess result."""
        # Run as a module from the project root (parent of awslabs)
        project_root = repo_generation_tool_path.parent.parent.parent
        cmd = [
            'uv',
            'run',
            'python',
            '-m',
            'awslabs.dynamodb_mcp_server.repo_generation_tool.codegen',
            '--schema',
            str(schema_path),
            '--output',
            str(output_dir),
        ]

        # Add optional flags
        if kwargs.get('generate_sample_usage'):
            cmd.append('--generate_sample_usage')
        if kwargs.get('no_lint'):
            cmd.append('--no-lint')
        if kwargs.get('validate_only'):
            cmd.append('--validate-only')
        if kwargs.get('language'):
            cmd.extend(['--language', kwargs['language']])

        # Look up usage data from the mapping
        usage_data_file = schema_to_usage_data.get(schema_path)
        if usage_data_file and usage_data_file.exists():
            cmd.extend(['--usage-data-path', str(usage_data_file)])

        return subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)

    return _generate_code


@pytest.fixture(scope='class')
def pre_generated_social_media(tmp_path_factory, repo_generation_tool_path):
    """Pre-generate social media output for performance optimization."""
    temp_dir = tmp_path_factory.mktemp('pre_generated_social_media')
    output_dir = temp_dir / 'output'
    output_dir.mkdir()

    # Run as a module from the project root (parent of awslabs)
    project_root = repo_generation_tool_path.parent.parent.parent
    cmd = [
        'uv',
        'run',
        'python',
        '-m',
        'awslabs.dynamodb_mcp_server.repo_generation_tool.codegen',
        '--schema',
        str(SOCIAL_MEDIA_SCHEMA),
        '--output',
        str(output_dir),
        '--no-lint',  # Skip linting for faster pre-generation
    ]

    if SOCIAL_MEDIA_USAGE_DATA.exists():
        cmd.extend(['--usage-data-path', str(SOCIAL_MEDIA_USAGE_DATA)])

    result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)
    if result.returncode != 0:
        pytest.fail(f'Pre-generation failed: {result.stderr}')

    return output_dir


# ============================================================================
# UTILITY FIXTURES
# ============================================================================


@pytest.fixture(autouse=True)
def ensure_clean_environment():
    """Ensure clean test environment before and after each test."""
    # Pre-test cleanup (if needed)
    yield
    # Post-test cleanup (if needed)
    # Note: tmp_path cleanup is automatic, this is for any global state


# ============================================================================
# MARKERS AND CONFIGURATION
# ============================================================================


def pytest_configure(config):
    """Configure pytest with any dynamic settings."""
    # Markers are now defined in pyproject.toml [tool.pytest.ini_options]
    pass


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Auto-mark unit tests
        if 'unit' in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Auto-mark integration tests
        elif 'integration' in str(item.fspath):
            item.add_marker(pytest.mark.integration)

            # Mark file generation tests
            if 'file_generation' in item.name or 'generation' in item.name:
                item.add_marker(pytest.mark.file_generation)
