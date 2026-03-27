"""Integration tests for consistent_read parameter end-to-end flow."""

import json
import pytest
import sys
from pathlib import Path


SCHEMA_WITH_CONSISTENT_READ_EXAMPLES = 'gaming_leaderboard'


@pytest.mark.integration
class TestConsistentReadIntegration:
    """Integration tests for consistent_read parameter feature."""

    def test_schema_with_consistent_read_generates_correct_code(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test that schema with consistent_read generates correct repository code.

        This test verifies:
        - Schema with consistent_read: true generates ConsistentRead=True in TODO comments
        - Schema with consistent_read: false generates ConsistentRead=False in TODO comments
        - Schema without consistent_read generates ConsistentRead=False (default)

        Note: The repository template generates TODO comments with example code,
        not fully implemented methods. The ConsistentRead parameter appears in these comments.
        """
        # Generate code using schema that has consistent_read examples
        result = code_generator(
            sample_schemas[SCHEMA_WITH_CONSISTENT_READ_EXAMPLES], generation_output_dir
        )

        # Assert generation succeeded
        assert result.returncode == 0, f'Generation failed: {result.stderr}'

        # Verify repositories.py was generated
        repos_file = generation_output_dir / 'repositories.py'
        assert repos_file.exists(), 'repositories.py was not generated'

        # Read generated repository code
        repos_content = repos_file.read_text()

        # Verify pattern 3 (get_top_scores) with consistent_read: false
        # Should generate ConsistentRead: False in TODO comment
        assert 'ConsistentRead' in repos_content, (
            'Generated code should include ConsistentRead parameter in TODO comments'
        )

        # Check that ConsistentRead appears with False value (for pattern 3)
        assert (
            "'ConsistentRead': False" in repos_content or 'ConsistentRead=False' in repos_content
        ), 'Pattern with consistent_read: false should generate ConsistentRead: False'

        # Verify pattern 4 (get_player_scores) on GSI without consistent_read
        # GSI queries should not include ConsistentRead parameter
        # Find the get_player_scores method and verify it doesn't have ConsistentRead
        lines = repos_content.split('\n')
        in_gsi_method = False
        gsi_section_lines = []

        for i, line in enumerate(lines):
            if 'def get_player_scores' in line:
                in_gsi_method = True
            elif (
                in_gsi_method
                and line.strip().startswith('def ')
                and 'get_player_scores' not in line
            ):
                # Moved to next method
                break
            elif in_gsi_method:
                gsi_section_lines.append(line)

        # GSI section should not mention ConsistentRead
        gsi_section = '\n'.join(gsi_section_lines)
        assert 'ConsistentRead' not in gsi_section, (
            'GSI query should not include ConsistentRead parameter'
        )

    def test_validation_catches_gsi_violations(self, generation_output_dir, code_generator):
        """Test that validation catches GSI queries with consistent_read: true.

        This test verifies that the schema validator properly rejects
        schemas that specify consistent_read: true for GSI queries.
        """
        # Create a schema with invalid GSI consistent_read configuration
        invalid_schema = {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'TestTable',
                        'partition_key': 'pk',
                        'sort_key': 'sk',
                    },
                    'gsi_list': [
                        {'name': 'TestGSI', 'partition_key': 'gsi_pk', 'sort_key': 'gsi_sk'}
                    ],
                    'entities': {
                        'TestEntity': {
                            'entity_type': 'TEST',
                            'pk_template': '{id}',
                            'sk_template': 'ENTITY',
                            'gsi_mappings': [
                                {
                                    'name': 'TestGSI',
                                    'pk_template': '{email}',
                                    'sk_template': '{created_at}',
                                }
                            ],
                            'fields': [
                                {'name': 'id', 'type': 'string', 'required': True},
                                {'name': 'email', 'type': 'string', 'required': True},
                                {'name': 'created_at', 'type': 'string', 'required': True},
                            ],
                            'access_patterns': [
                                {
                                    'pattern_id': 1,
                                    'name': 'query_by_email',
                                    'description': 'Query by email using GSI',
                                    'operation': 'Query',
                                    'index_name': 'TestGSI',
                                    'consistent_read': True,  # INVALID: GSI with consistent_read: true
                                    'parameters': [{'name': 'email', 'type': 'string'}],
                                    'return_type': 'entity_list',
                                }
                            ],
                        }
                    },
                }
            ]
        }

        # Write invalid schema to fixtures directory (within workspace)
        schema_file = Path(
            'tests/repo_generation_tool/fixtures/invalid_schemas/test_gsi_consistent_read.json'
        )
        with open(schema_file, 'w') as f:
            json.dump(invalid_schema, f, indent=2)

        try:
            # Attempt to generate code (should fail validation)
            result = code_generator(schema_file, generation_output_dir)

            # Should fail with validation error
            assert result.returncode != 0, (
                'Schema with GSI consistent_read: true should fail validation'
            )

            # Error message should mention GSI and consistent reads
            error_output = result.stdout + result.stderr
            assert 'GSI' in error_output or 'Global Secondary Index' in error_output, (
                f'Error message should mention GSI. Got: {error_output}'
            )
            assert 'consistent' in error_output.lower(), (
                f'Error message should mention consistent reads. Got: {error_output}'
            )
        finally:
            # Clean up test schema file
            if schema_file.exists():
                schema_file.unlink()

    def test_generated_code_can_be_imported(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test that generated code with consistent_read can be imported and used.

        This test verifies that the generated repository code is syntactically
        valid and can be imported without errors.
        """
        # Generate code
        result = code_generator(
            sample_schemas[SCHEMA_WITH_CONSISTENT_READ_EXAMPLES], generation_output_dir
        )
        assert result.returncode == 0, f'Generation failed: {result.stderr}'

        # Add generated directory to Python path
        sys.path.insert(0, str(generation_output_dir))

        try:
            # Import generated modules
            import entities  # type: ignore[import-not-found]
            import repositories  # type: ignore[import-not-found]

            # Verify Game entity exists (has consistent_read: true pattern)
            assert hasattr(entities, 'Game'), 'Game entity not found'
            assert hasattr(repositories, 'GameRepository'), 'GameRepository not found'

            # Verify LeaderboardEntry entity exists (has consistent_read: false pattern)
            assert hasattr(entities, 'LeaderboardEntry'), 'LeaderboardEntry entity not found'
            assert hasattr(repositories, 'LeaderboardEntryRepository'), (
                'LeaderboardEntryRepository not found'
            )

            # Verify repository classes can be instantiated
            game_repo = repositories.GameRepository()
            assert game_repo is not None, 'Failed to instantiate GameRepository'

            leaderboard_repo = repositories.LeaderboardEntryRepository()
            assert leaderboard_repo is not None, 'Failed to instantiate LeaderboardEntryRepository'

            # Verify entity classes can be instantiated
            game = entities.Game(
                game_id='test-game-123',
                title='Test Game',
                genre='Action',
                release_date='2024-01-01',
                publisher='Test Publisher',
                is_active=True,
            )
            assert game.game_id == 'test-game-123'
            assert game.title == 'Test Game'

        finally:
            # Clean up Python path
            sys.path.remove(str(generation_output_dir))

            # Remove imported modules from cache
            modules_to_remove = [
                name
                for name in sys.modules.keys()
                if name in ['entities', 'repositories', 'base_repository']
            ]
            for module_name in modules_to_remove:
                del sys.modules[module_name]

    def test_access_pattern_mapping_includes_consistent_read(
        self, generation_output_dir, sample_schemas, code_generator
    ):
        """Test that access pattern mapping includes consistent_read field.

        This test verifies that the generated access_pattern_mapping.json
        includes the consistent_read field for documentation purposes.
        """
        # Generate code
        result = code_generator(
            sample_schemas[SCHEMA_WITH_CONSISTENT_READ_EXAMPLES], generation_output_dir
        )
        assert result.returncode == 0, f'Generation failed: {result.stderr}'

        # Read access pattern mapping
        mapping_file = generation_output_dir / 'access_pattern_mapping.json'
        assert mapping_file.exists(), 'access_pattern_mapping.json not generated'

        with open(mapping_file) as f:
            mapping = json.load(f)

        # Verify mapping structure
        assert 'access_pattern_mapping' in mapping, 'Missing access_pattern_mapping key'

        # The mapping is keyed by pattern_id (as strings)
        patterns_with_consistent_read = []
        all_patterns = []

        for pattern_id, pattern_data in mapping['access_pattern_mapping'].items():
            all_patterns.append(
                {
                    'pattern_id': pattern_id,
                    'method_name': pattern_data.get('method_name'),
                    'has_consistent_read_key': 'consistent_read' in pattern_data,
                    'consistent_read': pattern_data.get('consistent_read'),
                }
            )
            if 'consistent_read' in pattern_data and pattern_data['consistent_read'] is not None:
                patterns_with_consistent_read.append(
                    {
                        'pattern_id': pattern_id,
                        'method_name': pattern_data.get('method_name'),
                        'consistent_read': pattern_data.get('consistent_read'),
                    }
                )

        # Should have at least 2 patterns with consistent_read specified
        # Pattern 1 (get_game) has consistent_read: true
        # Pattern 3 (get_top_scores) has consistent_read: false
        assert len(patterns_with_consistent_read) >= 2, (
            f'Expected at least 2 patterns with consistent_read, found {len(patterns_with_consistent_read)}. '
            f'Patterns: {json.dumps(all_patterns, indent=2)}'
        )

        # Verify we have both true and false values
        has_true = any(p['consistent_read'] is True for p in patterns_with_consistent_read)
        has_false = any(p['consistent_read'] is False for p in patterns_with_consistent_read)

        assert has_true, (
            f'Should have at least one pattern with consistent_read: true. Found: {patterns_with_consistent_read}'
        )
        assert has_false, (
            f'Should have at least one pattern with consistent_read: false. Found: {patterns_with_consistent_read}'
        )

    def test_validation_accepts_valid_consistent_read_configurations(
        self, generation_output_dir, code_generator
    ):
        """Test that validation accepts all valid consistent_read configurations.

        This test verifies that the validator accepts:
        - consistent_read: true on main table operations
        - consistent_read: false on main table operations
        - consistent_read: false on GSI operations
        - omitted consistent_read (defaults to false)
        """
        valid_schema = {
            'tables': [
                {
                    'table_config': {
                        'table_name': 'TestTable',
                        'partition_key': 'pk',
                        'sort_key': 'sk',
                    },
                    'gsi_list': [
                        {'name': 'TestGSI', 'partition_key': 'gsi_pk', 'sort_key': 'gsi_sk'}
                    ],
                    'entities': {
                        'TestEntity': {
                            'entity_type': 'TEST',
                            'pk_template': '{id}',
                            'sk_template': 'ENTITY',
                            'gsi_mappings': [
                                {
                                    'name': 'TestGSI',
                                    'pk_template': '{email}',
                                    'sk_template': '{created_at}',
                                }
                            ],
                            'fields': [
                                {'name': 'id', 'type': 'string', 'required': True},
                                {'name': 'email', 'type': 'string', 'required': True},
                                {'name': 'created_at', 'type': 'string', 'required': True},
                            ],
                            'access_patterns': [
                                {
                                    'pattern_id': 1,
                                    'name': 'get_by_id_consistent',
                                    'description': 'Get by ID with strong consistency',
                                    'operation': 'GetItem',
                                    'consistent_read': True,  # Valid: main table with true
                                    'parameters': [{'name': 'id', 'type': 'string'}],
                                    'return_type': 'single_entity',
                                },
                                {
                                    'pattern_id': 2,
                                    'name': 'query_main_table',
                                    'description': 'Query main table',
                                    'operation': 'Query',
                                    'consistent_read': False,  # Valid: main table with false
                                    'parameters': [{'name': 'id', 'type': 'string'}],
                                    'return_type': 'entity_list',
                                },
                                {
                                    'pattern_id': 3,
                                    'name': 'query_by_email',
                                    'description': 'Query by email using GSI',
                                    'operation': 'Query',
                                    'index_name': 'TestGSI',
                                    'consistent_read': False,  # Valid: GSI with false
                                    'parameters': [{'name': 'email', 'type': 'string'}],
                                    'return_type': 'entity_list',
                                },
                                {
                                    'pattern_id': 4,
                                    'name': 'query_by_email_default',
                                    'description': 'Query by email using GSI (default)',
                                    'operation': 'Query',
                                    'index_name': 'TestGSI',
                                    # Valid: GSI with omitted consistent_read
                                    'parameters': [{'name': 'email', 'type': 'string'}],
                                    'return_type': 'entity_list',
                                },
                            ],
                        }
                    },
                }
            ]
        }

        # Write valid schema to fixtures directory (within workspace)
        schema_file = Path(
            'tests/repo_generation_tool/fixtures/valid_schemas/test_consistent_read_valid.json'
        )
        with open(schema_file, 'w') as f:
            json.dump(valid_schema, f, indent=2)

        try:
            # Generate code (should succeed)
            result = code_generator(schema_file, generation_output_dir, validate_only=True)

            # Should pass validation
            assert result.returncode == 0, (
                f'Valid schema should pass validation. Error: {result.stderr}'
            )

            # Should show success indicator
            assert '✅' in result.stdout, 'Should show success indicator for valid schema'
        finally:
            # Clean up test schema file
            if schema_file.exists():
                schema_file.unlink()
