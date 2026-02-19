#!/usr/bin/env python3
"""Utility script for managing test snapshots."""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def get_project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent.parent


def get_snapshots_dir(language: str = 'python'):
    """Get the snapshots directory for a specific language."""
    return (
        get_project_root()
        / 'tests'
        / 'repo_generation_tool'
        / 'fixtures'
        / 'expected_outputs'
        / language
    )


def get_repo_generation_tool_path():
    """Get the repo_generation_tool directory."""
    return get_project_root() / 'awslabs' / 'dynamodb_mcp_server' / 'repo_generation_tool'


def get_sample_schemas():
    """Get sample schema paths."""
    fixtures_path = get_project_root() / 'tests' / 'repo_generation_tool' / 'fixtures'
    return {
        'social_media': fixtures_path
        / 'valid_schemas'
        / 'social_media_app'
        / 'social_media_app_schema.json',
        'ecommerce': fixtures_path / 'valid_schemas' / 'ecommerce_app' / 'ecommerce_schema.json',
        'elearning': fixtures_path
        / 'valid_schemas'
        / 'elearning_platform'
        / 'elearning_schema.json',
        'gaming_leaderboard': fixtures_path
        / 'valid_schemas'
        / 'gaming_leaderboard'
        / 'gaming_leaderboard_schema.json',
        'saas': fixtures_path / 'valid_schemas' / 'saas_app' / 'project_management_schema.json',
        'user_analytics': fixtures_path
        / 'valid_schemas'
        / 'user_analytics'
        / 'user_analytics_schema.json',
        'deals': fixtures_path / 'valid_schemas' / 'deals_app' / 'deals_schema.json',
        'user_registration': fixtures_path
        / 'valid_schemas'
        / 'user_registration'
        / 'user_registration_schema.json',
    }


def generate_code(schema_path: Path, output_dir: Path, **kwargs) -> subprocess.CompletedProcess:
    """Generate code using the CLI."""
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
        # Enable linting for consistent, high-quality output (matches snapshot tests)
    ]

    if kwargs.get('generate_sample_usage'):
        cmd.append('--generate_sample_usage')

    if kwargs.get('language'):
        cmd.extend(['--language', kwargs['language']])

    schema_dir = schema_path.parent
    schema_name = schema_path.stem.replace('_schema', '')

    # Look for usage data in the new standardized location
    fixtures_dir = schema_dir.parent.parent
    valid_usage_data_dir = fixtures_dir / 'valid_usage_data'
    usage_data_file = valid_usage_data_dir / schema_dir.name / f'{schema_name}_usage_data.json'

    if usage_data_file.exists():
        cmd.extend(['--usage-data-path', str(usage_data_file)])
        print(f'  📊 Using usage data: {usage_data_file.name}')

    return subprocess.run(cmd, cwd=get_project_root(), capture_output=True, text=True)


def create_snapshots(schema_names: list[str] = None, language: str = 'python'):
    """Create or update snapshots for specified schemas and language."""
    snapshots_dir = get_snapshots_dir(language)
    sample_schemas = get_sample_schemas()

    if schema_names is None:
        schema_names = list(sample_schemas.keys())

    for schema_name in schema_names:
        if schema_name not in sample_schemas:
            print(f'❌ Unknown schema: {schema_name}')
            continue

        print(f'📸 Creating snapshot for {schema_name}...')

        # Create temporary output directory
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_output = Path(temp_dir) / 'output'
            temp_output.mkdir()

            # Generate code
            result = generate_code(
                sample_schemas[schema_name],
                temp_output,
                generate_sample_usage=True,  # Generate usage examples for all schemas
                language=language,
            )

            if result.returncode != 0:
                print(f'❌ Generation failed for {schema_name}: {result.stderr}')
                continue

            # Create snapshot directory
            snapshot_dir = snapshots_dir / schema_name
            snapshot_dir.mkdir(parents=True, exist_ok=True)

            # Copy generated files to snapshots
            files_to_snapshot = [
                'entities.py',
                'repositories.py',
                'access_pattern_mapping.json',
                'usage_examples.py',
                'base_repository.py',
                'transaction_service.py',  # Conditional - only for schemas with cross_table_access_patterns
                'ruff.toml',
            ]

            for file_name in files_to_snapshot:
                generated_file = temp_output / file_name
                snapshot_file = snapshot_dir / file_name

                if generated_file.exists():
                    if file_name.endswith('.json'):
                        # Pretty-print JSON
                        with open(generated_file) as f:
                            data = json.load(f)
                        with open(snapshot_file, 'w') as f:
                            json.dump(data, f, indent=2, sort_keys=True)
                            f.write('\n')  # Add trailing newline for pre-commit compatibility
                    else:
                        # Copy text files
                        shutil.copy2(generated_file, snapshot_file)

                    print(f'  ✅ Created {file_name}')
                else:
                    print(f'  ⚠️  Missing {file_name}')

        print(f'✅ Snapshot created for {schema_name}')


def delete_snapshots(schema_names: list[str] = None, language: str = 'python'):
    """Delete snapshots for specified schemas and language."""
    snapshots_dir = get_snapshots_dir(language)

    if schema_names is None:
        schema_names = list(get_sample_schemas().keys())

    for schema_name in schema_names:
        snapshot_dir = snapshots_dir / schema_name
        if snapshot_dir.exists():
            shutil.rmtree(snapshot_dir)
            print(f'🗑️  Deleted snapshot for {language}/{schema_name}')
        else:
            print(f'⚠️  No snapshot found for {language}/{schema_name}')


def list_snapshots(language: str = None):
    """List all existing snapshots."""
    base_snapshots_dir = (
        get_project_root() / 'tests' / 'repo_generation_tool' / 'fixtures' / 'expected_outputs'
    )

    if not base_snapshots_dir.exists():
        print('📁 No snapshots directory found')
        return

    if language:
        # List snapshots for specific language
        snapshots_dir = base_snapshots_dir / language
        if not snapshots_dir.exists():
            print(f'📁 No snapshots found for language: {language}')
            return

        schema_dirs = [d for d in snapshots_dir.iterdir() if d.is_dir()]
        if not schema_dirs:
            print(f'📁 No snapshots found for language: {language}')
            return

        print(f'📸 Existing snapshots for {language}:')
        for schema_dir in sorted(schema_dirs):
            files = list(schema_dir.glob('*'))
            print(f'  {schema_dir.name}/ ({len(files)} files)')
            for file_path in sorted(files):
                size = file_path.stat().st_size
                print(f'    {file_path.name} ({size} bytes)')
    else:
        # List all languages and their snapshots
        language_dirs = [d for d in base_snapshots_dir.iterdir() if d.is_dir()]
        if not language_dirs:
            print('📁 No snapshots found')
            return

        print('📸 Existing snapshots:')
        for language_dir in sorted(language_dirs):
            schema_dirs = [d for d in language_dir.iterdir() if d.is_dir()]
            print(f'  {language_dir.name}/ ({len(schema_dirs)} schemas)')
            for schema_dir in sorted(schema_dirs):
                files = list(schema_dir.glob('*'))
                print(f'    {schema_dir.name}/ ({len(files)} files)')
                for file_path in sorted(files):
                    size = file_path.stat().st_size
                    print(f'      {file_path.name} ({size} bytes)')


def validate_snapshots():
    """Validate that all snapshots are syntactically correct."""
    snapshots_dir = get_snapshots_dir()

    if not snapshots_dir.exists():
        print('📁 No snapshots directory found')
        return False

    all_valid = True

    # Check JSON files
    json_files = list(snapshots_dir.rglob('*.json'))
    for json_file in json_files:
        try:
            with open(json_file) as f:
                json.load(f)
            print(f'✅ Valid JSON: {json_file.relative_to(snapshots_dir)}')
        except json.JSONDecodeError as e:
            print(f'❌ Invalid JSON: {json_file.relative_to(snapshots_dir)} - {e}')
            all_valid = False

    # Check Python files
    python_files = list(snapshots_dir.rglob('*.py'))
    for python_file in python_files:
        try:
            with open(python_file) as f:
                content = f.read()
            compile(content, str(python_file), 'exec')
            print(f'✅ Valid Python: {python_file.relative_to(snapshots_dir)}')
        except SyntaxError as e:
            print(f'❌ Invalid Python: {python_file.relative_to(snapshots_dir)} - {e}')
            all_valid = False

    return all_valid


def run_snapshot_tests():
    """Run the snapshot tests."""
    project_root = get_project_root()

    cmd = [
        'uv',
        'run',
        'pytest',
        'tests/repo_generation_tool/integration/test_python_snapshot_generation.py',
        '-v',
        '-m',
        'snapshot',
    ]

    result = subprocess.run(cmd, cwd=project_root)
    return result.returncode == 0


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description='Manage test snapshots for repo_generation_tool')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Create command
    create_parser = subparsers.add_parser('create', help='Create or update snapshots')
    create_parser.add_argument('schemas', nargs='*', help='Schema names to create snapshots for')
    create_parser.add_argument(
        '--language', default='python', help='Language to generate snapshots for'
    )

    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete snapshots')
    delete_parser.add_argument('schemas', nargs='*', help='Schema names to delete snapshots for')
    delete_parser.add_argument(
        '--language', default='python', help='Language to delete snapshots for'
    )

    # List command
    list_parser = subparsers.add_parser('list', help='List existing snapshots')
    list_parser.add_argument(
        '--language', help='Language to list snapshots for (omit for all languages)'
    )

    # Validate command
    subparsers.add_parser('validate', help='Validate snapshot syntax')

    # Test command
    subparsers.add_parser('test', help='Run snapshot tests')

    args = parser.parse_args()

    if args.command == 'create':
        create_snapshots(args.schemas if args.schemas else None, args.language)
    elif args.command == 'delete':
        delete_snapshots(args.schemas if args.schemas else None, args.language)
    elif args.command == 'list':
        list_snapshots(args.language)
    elif args.command == 'validate':
        if validate_snapshots():
            print('✅ All snapshots are valid')
            sys.exit(0)
        else:
            print('❌ Some snapshots are invalid')
            sys.exit(1)
    elif args.command == 'test':
        if run_snapshot_tests():
            print('✅ All snapshot tests passed')
            sys.exit(0)
        else:
            print('❌ Some snapshot tests failed')
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
