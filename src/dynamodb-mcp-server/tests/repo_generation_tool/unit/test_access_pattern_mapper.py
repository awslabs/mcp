"""Unit tests for AccessPatternMapper class."""

import pytest
from awslabs.dynamodb_mcp_server.repo_generation_tool.generators.access_pattern_mapper import (
    AccessPatternMapper,
)
from unittest.mock import Mock


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

    def test_putitem_pattern_renamed_on_crud_conflict(self, mapper, sample_entities):
        """Test that PutItem patterns conflicting with CRUD create are renamed (create -> put)."""
        user_entity = sample_entities['User']
        result = mapper.generate_mapping('User', user_entity)

        put_user_pattern = None
        for pattern_id, pattern_info in result.items():
            if pattern_info['method_name'] == 'put_user':
                put_user_pattern = pattern_info
                break

        assert put_user_pattern is not None

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

    def test_consistent_read_behavior(self, mapper):
        """Test consistent_read handling: included for reads (default false), omitted for writes."""
        test_entity = {
            'entity_type': 'TEST',
            'pk_template': '{id}',
            'sk_template': 'ENTITY',
            'fields': [{'name': 'id', 'type': 'string', 'required': True}],
            'access_patterns': [
                # Read operations - should include consistent_read
                {
                    'pattern_id': 1,
                    'name': 'get_item_explicit_true',
                    'description': 'Get item with explicit consistent_read: true',
                    'operation': 'GetItem',
                    'parameters': [{'name': 'id', 'type': 'string'}],
                    'return_type': 'single_entity',
                    'consistent_read': True,
                },
                {
                    'pattern_id': 2,
                    'name': 'query_explicit_false',
                    'description': 'Query with explicit consistent_read: false',
                    'operation': 'Query',
                    'parameters': [{'name': 'id', 'type': 'string'}],
                    'return_type': 'entity_list',
                    'consistent_read': False,
                },
                {
                    'pattern_id': 3,
                    'name': 'scan_default',
                    'description': 'Scan without consistent_read (should default to false)',
                    'operation': 'Scan',
                    'parameters': [],
                    'return_type': 'entity_list',
                },
                {
                    'pattern_id': 4,
                    'name': 'get_item_default',
                    'description': 'GetItem without consistent_read (should default to false)',
                    'operation': 'GetItem',
                    'parameters': [{'name': 'id', 'type': 'string'}],
                    'return_type': 'single_entity',
                },
                # Write operations - should NOT include consistent_read
                {
                    'pattern_id': 5,
                    'name': 'create_item',
                    'description': 'Create item (write operation)',
                    'operation': 'PutItem',
                    'parameters': [
                        {'name': 'entity', 'type': 'entity', 'entity_type': 'TestEntity'}
                    ],
                    'return_type': 'single_entity',
                },
                {
                    'pattern_id': 6,
                    'name': 'update_item',
                    'description': 'Update item (write operation)',
                    'operation': 'UpdateItem',
                    'parameters': [{'name': 'id', 'type': 'string'}],
                    'return_type': 'single_entity',
                },
                {
                    'pattern_id': 7,
                    'name': 'delete_item',
                    'description': 'Delete item (write operation)',
                    'operation': 'DeleteItem',
                    'parameters': [{'name': 'id', 'type': 'string'}],
                    'return_type': 'success_flag',
                },
            ],
        }

        result = mapper.generate_mapping('TestEntity', test_entity)

        # Read operations: consistent_read included
        assert result['1']['consistent_read'] is True  # explicit true preserved
        assert result['2']['consistent_read'] is False  # explicit false preserved
        assert result['3']['consistent_read'] is False  # defaults to false
        assert result['4']['consistent_read'] is False  # defaults to false

        # Write operations: consistent_read omitted
        assert 'consistent_read' not in result['5']
        assert 'consistent_read' not in result['6']
        assert 'consistent_read' not in result['7']

    def test_mixed_data_return_type_with_type_mapper(self, mock_language_config):
        """Test that mixed_data return type generates correct paginated dict return type."""
        type_mapper = Mock()
        mapper = AccessPatternMapper(mock_language_config, type_mapper)

        test_entity = {
            'entity_type': 'TASK',
            'pk_template': '{task_id}',
            'sk_template': 'METADATA',
            'fields': [
                {'name': 'task_id', 'type': 'string', 'required': True},
                {'name': 'title', 'type': 'string', 'required': True},
            ],
            'access_patterns': [
                {
                    'pattern_id': 1,
                    'name': 'get_task_details',
                    'description': 'Get task with subtasks and comments',
                    'operation': 'Query',
                    'parameters': [{'name': 'task_id', 'type': 'string'}],
                    'return_type': 'mixed_data',
                },
                {
                    'pattern_id': 2,
                    'name': 'scan_all_items',
                    'description': 'Scan all item collection items',
                    'operation': 'Scan',
                    'parameters': [],
                    'return_type': 'mixed_data',
                },
            ],
        }

        result = mapper.generate_mapping('Task', test_entity)

        # mixed_data with Query/Scan should return paginated dict type
        assert result['1']['return_type'] == 'tuple[list[dict[str, Any]], dict | None]'
        assert result['2']['return_type'] == 'tuple[list[dict[str, Any]], dict | None]'

        # TypeMapper should not be called for mixed_data
        type_mapper.map_return_type.assert_not_called()

    def test_mixed_data_with_non_query_operation(self, mock_language_config):
        """Test that mixed_data with non-Query/Scan operations uses TypeMapper."""
        type_mapper = Mock()
        type_mapper.map_return_type.return_value = 'dict'
        mapper = AccessPatternMapper(mock_language_config, type_mapper)

        test_entity = {
            'entity_type': 'TEST',
            'pk_template': '{id}',
            'sk_template': 'ENTITY',
            'fields': [{'name': 'id', 'type': 'string', 'required': True}],
            'access_patterns': [
                {
                    'pattern_id': 1,
                    'name': 'get_mixed',
                    'description': 'GetItem with mixed_data',
                    'operation': 'GetItem',
                    'parameters': [{'name': 'id', 'type': 'string'}],
                    'return_type': 'mixed_data',
                },
            ],
        }

        result = mapper.generate_mapping('TestEntity', test_entity)

        # Non-Query/Scan operations should use TypeMapper
        assert result['1']['return_type'] == 'dict'
        type_mapper.map_return_type.assert_called_once_with('mixed_data', 'TestEntity')
