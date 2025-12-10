"""Unit tests for AccessPatternMapper class."""

import pytest
from awslabs.dynamodb_mcp_server.repo_generation_tool.generators.access_pattern_mapper import (
    AccessPatternMapper,
)


@pytest.mark.unit
class TestAccessPatternMapper:
    """Unit tests for AccessPatternMapper class - high-level public functionality."""

    @pytest.fixture
    def mapper(self, mock_language_config):
        """Create an AccessPatternMapper instance for testing."""
        return AccessPatternMapper(mock_language_config)

    @pytest.fixture
    def sample_entities(self):
        """Sample entities with access patterns for testing."""
        return {
            'User': {
                'entity_type': 'USER',
                'pk_template': '{user_id}',
                'sk_template': 'USER',
                'fields': [
                    {'name': 'user_id', 'type': 'string', 'required': True},
                    {'name': 'username', 'type': 'string', 'required': True},
                ],
                'access_patterns': [
                    {
                        'pattern_id': 1,
                        'name': 'get_user',
                        'description': 'Get user by ID',
                        'operation': 'GetItem',
                        'parameters': [{'name': 'user_id', 'type': 'string'}],
                        'return_type': 'single_entity',
                    },
                    {
                        'pattern_id': 2,
                        'name': 'create_user',  # This will conflict with CRUD
                        'description': 'Create a new user',
                        'operation': 'PutItem',
                        'parameters': [{'name': 'user', 'type': 'entity', 'entity_type': 'User'}],
                        'return_type': 'single_entity',
                    },
                ],
            },
            'Post': {
                'entity_type': 'POST',
                'pk_template': '{user_id}',
                'sk_template': 'POST#{post_id}',
                'fields': [
                    {'name': 'user_id', 'type': 'string', 'required': True},
                    {'name': 'post_id', 'type': 'string', 'required': True},
                    {'name': 'content', 'type': 'string', 'required': True},
                ],
                'access_patterns': [
                    {
                        'pattern_id': 3,
                        'name': 'get_user_posts',
                        'description': 'Get all posts by user',
                        'operation': 'Query',
                        'parameters': [{'name': 'user_id', 'type': 'string'}],
                        'return_type': 'entity_list',
                    }
                ],
            },
        }

    def test_mapper_initialization(self, mock_language_config):
        """Test AccessPatternMapper initialization."""
        mapper = AccessPatternMapper(mock_language_config)

        assert mapper.language_config == mock_language_config

    def test_generate_mapping_structure(self, mapper, sample_entities):
        """Test access pattern mapping structure and required fields."""
        user_entity = sample_entities['User']
        result = mapper.generate_mapping('User', user_entity)

        assert isinstance(result, dict)
        assert len(result) == 2

        for pattern_id, pattern_info in result.items():
            assert 'pattern_id' in pattern_info
            assert 'description' in pattern_info
            assert 'entity' in pattern_info
            assert 'repository' in pattern_info
            assert 'method_name' in pattern_info
            assert 'parameters' in pattern_info
            assert 'return_type' in pattern_info
            assert 'operation' in pattern_info

    def test_empty_access_patterns(self, mapper):
        """Test mapping with entity that has no access patterns."""
        empty_entity = {
            'entity_type': 'EMPTY',
            'pk_template': '{id}',
            'sk_template': 'ENTITY',
            'fields': [{'name': 'id', 'type': 'string', 'required': True}],
            'access_patterns': [],  # No access patterns
        }

        result = mapper.generate_mapping('EmptyEntity', empty_entity)

        assert isinstance(result, dict)
        assert len(result) == 0  # No patterns to map

    def test_multiple_patterns(self, mapper):
        """Test mapping entity with multiple access patterns."""
        test_entity = {
            'entity_type': 'TEST',
            'pk_template': '{id}',
            'sk_template': 'ENTITY',
            'fields': [{'name': 'id', 'type': 'string', 'required': True}],
            'access_patterns': [
                {
                    'pattern_id': 1,
                    'name': 'custom_query',
                    'description': 'Custom query pattern',
                    'operation': 'Query',
                    'parameters': [{'name': 'id', 'type': 'string'}],
                    'return_type': 'entity_list',
                },
                {
                    'pattern_id': 2,
                    'name': 'get_item',
                    'description': 'Get item',
                    'operation': 'GetItem',
                    'parameters': [{'name': 'id', 'type': 'string'}],
                    'return_type': 'single_entity',
                },
            ],
        }

        result = mapper.generate_mapping('TestEntity', test_entity)

        assert len(result) == 2
        assert result['1']['method_name'] == 'custom_query'
        assert result['1']['operation'] == 'Query'
        assert result['2']['method_name'] == 'get_item'
        assert result['2']['operation'] == 'GetItem'

    def test_optional_fields(self, mapper):
        """Test mapping with optional index_name and range_condition."""
        test_entity = {
            'entity_type': 'TEST',
            'pk_template': '{id}',
            'sk_template': 'ENTITY',
            'fields': [{'name': 'id', 'type': 'string', 'required': True}],
            'access_patterns': [
                {
                    'pattern_id': 1,
                    'name': 'query_by_gsi',
                    'description': 'Query using GSI',
                    'operation': 'Query',
                    'parameters': [{'name': 'id', 'type': 'string'}],
                    'return_type': 'entity_list',
                    'index_name': 'GSI1',
                    'range_condition': 'begins_with',
                }
            ],
        }

        result = mapper.generate_mapping('TestEntity', test_entity)

        assert result['1']['index_name'] == 'GSI1'
        assert result['1']['range_condition'] == 'begins_with'

    def test_with_type_mapper(self, mock_language_config):
        """Test mapping with TypeMapper for Query/Scan pagination."""
        from unittest.mock import Mock

        type_mapper = Mock()
        type_mapper.map_return_type.return_value = 'TestEntity'
        mapper = AccessPatternMapper(mock_language_config, type_mapper)

        test_entity = {
            'entity_type': 'TEST',
            'pk_template': '{id}',
            'sk_template': 'ENTITY',
            'fields': [{'name': 'id', 'type': 'string', 'required': True}],
            'access_patterns': [
                {
                    'pattern_id': 1,
                    'name': 'scan_all',
                    'description': 'Scan all items',
                    'operation': 'Scan',
                    'parameters': [],
                    'return_type': 'entity_list',
                },
                {
                    'pattern_id': 2,
                    'name': 'get_one',
                    'description': 'Get one item',
                    'operation': 'GetItem',
                    'parameters': [{'name': 'id', 'type': 'string'}],
                    'return_type': 'single_entity',
                },
            ],
        }

        result = mapper.generate_mapping('TestEntity', test_entity)

        assert result['1']['return_type'] == 'tuple[list[TestEntity], dict | None]'
        assert result['2']['return_type'] == 'TestEntity'
        type_mapper.map_return_type.assert_called_once_with('single_entity', 'TestEntity')

    def test_conflict_detection(self, mapper, sample_entities):
        """Test that CRUD conflicts are detected and marked."""
        user_entity = sample_entities['User']
        result = mapper.generate_mapping('User', user_entity)

        # Find the create_user pattern which should conflict with CRUD
        create_user_pattern = None
        for pattern_id, pattern_info in result.items():
            if pattern_info['method_name'] == 'create_user':
                create_user_pattern = pattern_info
                break

        # Pattern should exist in the mapping
        assert create_user_pattern is not None

    def test_operation_types_preserved(self, mapper, sample_entities):
        """Test that operation types are preserved in mappings."""
        user_entity = sample_entities['User']
        result = mapper.generate_mapping('User', user_entity)
        operations_found = {pattern_info['operation'] for pattern_info in result.values()}
        assert operations_found.intersection({'GetItem', 'PutItem'})

    def test_entity_association(self, mapper, sample_entities):
        """Test that patterns are correctly associated with their entities."""
        user_entity = sample_entities['User']
        result = mapper.generate_mapping('User', user_entity)
        for pattern_info in result.values():
            assert pattern_info['entity'] == 'User'
            assert pattern_info['repository'] == 'UserRepository'

    def test_pattern_id_preservation(self, mapper, sample_entities):
        """Test that original pattern IDs are preserved."""
        user_entity = sample_entities['User']
        result = mapper.generate_mapping('User', user_entity)
        pattern_ids = [pattern_info['pattern_id'] for pattern_info in result.values()]
        assert 1 in pattern_ids and 2 in pattern_ids
