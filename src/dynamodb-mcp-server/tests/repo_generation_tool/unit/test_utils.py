"""Unit tests for utility functions."""

import pytest
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.language_config import (
    LanguageConfig,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.utils import (
    detect_item_collection,
    filter_conflicting_patterns,
    format_entity_imports,
    generate_renamed_method_name,
    generate_test_instruction,
    get_crud_method_names,
    get_crud_signature,
    get_pattern_signature,
    get_sk_prefix,
    has_signature_conflict,
    is_semantically_equivalent_to_crud,
    to_pascal_case,
    to_snake_case,
)


@pytest.mark.unit
class TestUtilityFunctions:
    """Unit tests for utility functions."""

    def test_to_snake_case(self):
        """Test snake_case conversion."""
        test_cases = [
            ('UserProfile', 'user_profile'),
            ('XMLHttpRequest', 'xml_http_request'),
            ('simpleWord', 'simple_word'),
            ('already_snake', 'already_snake'),
            ('APIKey', 'api_key'),
            ('', ''),
            ('A', 'a'),
        ]

        for input_str, expected in test_cases:
            result = to_snake_case(input_str)
            assert result == expected, f'Expected {input_str} -> {expected}, got {result}'

    def test_to_snake_case_with_hyphens(self):
        """Test snake_case conversion handles hyphens correctly.

        GSI names often contain hyphens (e.g., 'Events-ByDate') which need to be
        converted to valid Python identifiers with underscores.
        """
        test_cases = [
            # GSI name patterns
            ('Events-ByDate', 'events_by_date'),
            ('Orders-ByEmail', 'orders_by_email'),
            ('Orders-ByUser', 'orders_by_user'),
            ('Events-ByVenue', 'events_by_venue'),
            ('Events-ByCategory', 'events_by_category'),
            # Edge cases
            ('simple-name', 'simple_name'),
            ('UPPER-CASE', 'upper_case'),
            ('mixed-Case-Name', 'mixed_case_name'),
            ('multiple--hyphens', 'multiple_hyphens'),
            ('hyphen-at-end-', 'hyphen_at_end_'),
            ('-hyphen-at-start', '_hyphen_at_start'),
            # Combined with CamelCase
            ('MyGSI-ByStatus', 'my_gsi_by_status'),
            ('UserData-ByCreatedAt', 'user_data_by_created_at'),
        ]

        for input_str, expected in test_cases:
            result = to_snake_case(input_str)
            assert result == expected, f'Expected {input_str} -> {expected}, got {result}'

    def test_filter_conflicting_patterns(self):
        """Test filtering of conflicting access patterns."""
        # PutItem patterns are renamed (create -> put), other conflicts are filtered
        access_patterns = [
            {'name': 'create_user', 'operation': 'PutItem'},
            {'name': 'get_user', 'operation': 'GetItem'},
            {'name': 'create_user_profile', 'operation': 'PutItem'},
            {'name': 'custom_query', 'operation': 'Query'},
        ]
        crud_methods = ['create_user_profile', 'get_user_profile', 'get_user']
        result, crud_consistent_read = filter_conflicting_patterns(access_patterns, crud_methods)

        assert len(result) == 3
        result_names = [p['name'] for p in result]
        assert 'put_user_profile' in result_names  # PutItem renamed
        assert 'create_user' in result_names  # No conflict
        assert 'custom_query' in result_names  # No conflict
        assert 'get_user' not in result_names  # GetItem filtered

        # Empty inputs
        result, _ = filter_conflicting_patterns([], ['create_user'])
        assert result == []
        result, _ = filter_conflicting_patterns([{'name': 'query', 'operation': 'Query'}], [])
        assert result == [{'name': 'query', 'operation': 'Query'}]


@pytest.mark.unit
class TestUtilityFunctionsAdvanced:
    """Unit tests for advanced utility function scenarios."""

    def test_to_pascal_case(self):
        """Test to_pascal_case function."""
        test_cases = [
            ('user_profile', 'UserProfile'),
            ('simple', 'Simple'),
            ('', ''),
            ('multiple_words_here', 'MultipleWordsHere'),
            ('single', 'Single'),
        ]

        for input_str, expected in test_cases:
            result = to_pascal_case(input_str)
            assert result == expected

    def test_generate_test_instruction(self):
        """Test generate_test_instruction function."""
        # Test filtered (CRUD) method
        result = generate_test_instruction('User', 'create_user', True, [])
        assert result == 'Use CRUD method: user_repo.create_user()'

        # Test non-filtered method with parameters
        params = [{'name': 'id'}, {'name': 'data'}]
        result = generate_test_instruction('Product', 'find_by_category', False, params)
        assert result == 'Use generated method: product_repo.find_by_category(..., ...)'

        # Test with different entity name
        result = generate_test_instruction('OrderItem', 'update_item', True, params)
        assert result == 'Use CRUD method: orderitem_repo.update_item(..., ...)'

    def test_format_entity_imports(self):
        """Test format_entity_imports function."""
        # Test with multiple entities (should be sorted)
        result = format_entity_imports(['User', 'Post', 'Comment'])
        assert result == 'from entities import Comment, Post, User'

        # Test with single entity
        result = format_entity_imports(['User'])
        assert result == 'from entities import User'

        # Test with empty list
        result = format_entity_imports([])
        assert result == 'from entities import '


@pytest.mark.unit
class TestSignatureConflictDetection:
    """Unit tests for signature-based conflict detection."""

    def test_get_crud_signature_create(self):
        """Test CRUD signature for create method."""
        entity_config = {'pk_params': ['user_id'], 'sk_params': []}
        sig = get_crud_signature('User', 'create_user', entity_config)
        assert sig == ('entity',)

    def test_get_crud_signature_get(self):
        """Test CRUD signature for get method with pk+sk."""
        entity_config = {'pk_params': ['patient_id'], 'sk_params': ['record_date', 'record_id']}
        sig = get_crud_signature(
            'PatientMedicalHistory', 'get_patient_medical_history', entity_config
        )
        assert sig == ('string', 'string', 'string')

    def test_get_crud_signature_update(self):
        """Test CRUD signature for update method."""
        entity_config = {'pk_params': ['user_id'], 'sk_params': []}
        sig = get_crud_signature('User', 'update_user', entity_config)
        assert sig == ('entity',)

    def test_get_crud_signature_delete(self):
        """Test CRUD signature for delete method."""
        entity_config = {'pk_params': ['user_id'], 'sk_params': ['sk_field']}
        sig = get_crud_signature('User', 'delete_user', entity_config)
        assert sig == ('string', 'string')

    def test_get_pattern_signature(self):
        """Test pattern signature extraction."""
        pattern = {
            'parameters': [
                {'name': 'appointment', 'type': 'entity'},
                {'name': 'patient', 'type': 'entity'},
                {'name': 'provider', 'type': 'entity'},
            ]
        }
        sig = get_pattern_signature(pattern)
        assert sig == ('entity', 'entity', 'entity')

    def test_get_pattern_signature_mixed(self):
        """Test pattern signature with mixed types."""
        pattern = {
            'parameters': [
                {'name': 'user_id', 'type': 'string'},
                {'name': 'data', 'type': 'entity'},
            ]
        }
        sig = get_pattern_signature(pattern)
        assert sig == ('string', 'entity')

    def test_has_signature_conflict_true(self):
        """Test true signature conflict (same name and signature)."""
        pattern = {'name': 'create_user', 'parameters': [{'name': 'user', 'type': 'entity'}]}
        entity_config = {'pk_params': ['user_id'], 'sk_params': []}
        crud_methods = {'create_user', 'get_user', 'update_user', 'delete_user'}

        result = has_signature_conflict(pattern, 'User', crud_methods, entity_config)
        assert result is True

    def test_has_signature_conflict_false_different_signature(self):
        """Test no conflict when signatures differ."""
        # Pattern with 3 entity params vs CRUD with 1 entity param
        pattern = {
            'name': 'create_appointment',
            'parameters': [
                {'name': 'appointment', 'type': 'entity'},
                {'name': 'patient', 'type': 'entity'},
                {'name': 'provider', 'type': 'entity'},
            ],
        }
        entity_config = {'pk_params': ['appointment_id'], 'sk_params': []}
        crud_methods = {
            'create_appointment',
            'get_appointment',
            'update_appointment',
            'delete_appointment',
        }

        result = has_signature_conflict(pattern, 'Appointment', crud_methods, entity_config)
        assert result is False

    def test_has_signature_conflict_false_different_name(self):
        """Test no conflict when names differ."""
        pattern = {'name': 'custom_create', 'parameters': [{'name': 'user', 'type': 'entity'}]}
        entity_config = {'pk_params': ['user_id'], 'sk_params': []}
        crud_methods = {'create_user', 'get_user'}

        result = has_signature_conflict(pattern, 'User', crud_methods, entity_config)
        assert result is False

    def test_generate_renamed_method_name_with_refs(self):
        """Test renaming for patterns with multiple entity references."""
        pattern = {
            'name': 'create_appointment',
            'operation': 'PutItem',
            'parameters': [
                {'name': 'appointment', 'type': 'entity'},
                {'name': 'patient', 'type': 'entity'},
                {'name': 'provider', 'type': 'entity'},
            ],
        }
        result = generate_renamed_method_name('create_appointment', pattern)
        assert result == 'create_appointment_with_refs'

    def test_generate_renamed_method_name_query_list(self):
        """Test renaming for Query patterns conflicting with GetItem."""
        pattern = {
            'name': 'get_patient_medical_history',
            'operation': 'Query',
            'parameters': [{'name': 'patient_id', 'type': 'string'}],
        }
        result = generate_renamed_method_name('get_patient_medical_history', pattern)
        assert result == 'get_patient_medical_history_list'

    def test_generate_renamed_method_name_with_params(self):
        """Test renaming with additional non-entity parameters."""
        pattern = {
            'name': 'create_user',
            'operation': 'PutItem',
            'parameters': [
                {'name': 'user', 'type': 'entity'},
                {'name': 'role_id', 'type': 'string'},
            ],
        }
        result = generate_renamed_method_name('create_user', pattern)
        assert result == 'create_user_with_role_id'

    def test_generate_renamed_method_name_fallback(self):
        """Test fallback naming with pattern_id."""
        pattern = {
            'name': 'create_user',
            'operation': 'PutItem',
            'pattern_id': 42,
            'parameters': [{'name': 'user', 'type': 'entity'}],
        }
        result = generate_renamed_method_name('create_user', pattern)
        assert result == 'create_user_pattern_42'

    def test_filter_conflicting_patterns_with_signature_check(self):
        """Test non-PutItem patterns with signature-based conflict detection."""
        access_patterns = [
            # Query with different signature than GetItem CRUD - should be renamed
            {
                'name': 'get_appointment',
                'pattern_id': 4,
                'operation': 'Query',
                'parameters': [{'name': 'appointment_id', 'type': 'string'}],
            },
            # No conflict
            {
                'name': 'update_appointment_status',
                'pattern_id': 18,
                'operation': 'UpdateItem',
                'parameters': [{'name': 'appointment_id', 'type': 'string'}],
            },
        ]

        crud_methods = {
            'create_appointment',
            'get_appointment',
            'update_appointment',
            'delete_appointment',
        }
        entity_config = {'pk_params': ['appointment_id'], 'sk_params': ['date']}

        result, _ = filter_conflicting_patterns(
            access_patterns, crud_methods, entity_name='Appointment', entity_config=entity_config
        )

        assert len(result) == 2
        result_names = [p['name'] for p in result]
        assert 'get_appointment_list' in result_names  # Query renamed
        assert 'update_appointment_status' in result_names

    def test_filter_conflicting_patterns_query_vs_getitem(self):
        """Test Query pattern conflicting with GetItem CRUD."""
        access_patterns = [
            # Query pattern - different signature than GetItem CRUD
            {
                'name': 'get_patient_medical_history',
                'pattern_id': 4,
                'operation': 'Query',
                'parameters': [{'name': 'patient_id', 'type': 'string'}],
            }
        ]

        crud_methods = {
            'create_patient_medical_history',
            'get_patient_medical_history',
            'update_patient_medical_history',
            'delete_patient_medical_history',
        }
        entity_config = {'pk_params': ['patient_id'], 'sk_params': ['record_date', 'record_id']}

        result, _ = filter_conflicting_patterns(
            access_patterns,
            crud_methods,
            entity_name='PatientMedicalHistory',
            entity_config=entity_config,
        )

        # Should be renamed to _list since it's a Query
        assert len(result) == 1
        assert result[0]['name'] == 'get_patient_medical_history_list'
        assert result[0].get('original_name') == 'get_patient_medical_history'


@pytest.mark.unit
class TestSemanticEquivalenceDetection:
    """Unit tests for semantic equivalence detection."""

    def test_getitem_equivalent_to_crud_get(self):
        """Test GetItem with same key params is equivalent to CRUD get."""
        pattern = {
            'name': 'get_user_by_id',
            'operation': 'GetItem',
            'parameters': [{'name': 'user_id', 'type': 'string'}],
        }
        entity_config = {'pk_params': ['user_id'], 'sk_params': []}

        result = is_semantically_equivalent_to_crud(pattern, 'User', entity_config)
        assert result is True

    def test_getitem_with_composite_key_equivalent(self):
        """Test GetItem with pk+sk params is equivalent to CRUD get."""
        pattern = {
            'name': 'get_order_item_by_keys',
            'operation': 'GetItem',
            'parameters': [
                {'name': 'order_id', 'type': 'string'},
                {'name': 'item_id', 'type': 'string'},
            ],
        }
        entity_config = {'pk_params': ['order_id'], 'sk_params': ['item_id']}

        result = is_semantically_equivalent_to_crud(pattern, 'OrderItem', entity_config)
        assert result is True

    def test_getitem_with_different_params_not_equivalent(self):
        """Test GetItem with different params is NOT equivalent."""
        pattern = {
            'name': 'get_user_by_email',
            'operation': 'GetItem',
            'parameters': [{'name': 'email', 'type': 'string'}],
        }
        entity_config = {'pk_params': ['user_id'], 'sk_params': []}

        result = is_semantically_equivalent_to_crud(pattern, 'User', entity_config)
        assert result is False

    def test_deleteitem_equivalent_to_crud_delete(self):
        """Test DeleteItem with same key params is equivalent when name matches."""
        pattern = {
            'name': 'delete_user_by_id',  # Contains 'delete_user'
            'operation': 'DeleteItem',
            'parameters': [{'name': 'user_id', 'type': 'string'}],
        }
        entity_config = {'pk_params': ['user_id'], 'sk_params': []}

        result = is_semantically_equivalent_to_crud(pattern, 'User', entity_config)
        assert result is True

    def test_deleteitem_different_name_not_equivalent(self):
        """Test DeleteItem with different name is NOT equivalent."""
        pattern = {
            'name': 'remove_user',  # Does NOT contain 'delete_user'
            'operation': 'DeleteItem',
            'parameters': [{'name': 'user_id', 'type': 'string'}],
        }
        entity_config = {'pk_params': ['user_id'], 'sk_params': []}

        result = is_semantically_equivalent_to_crud(pattern, 'User', entity_config)
        assert result is False

    def test_query_not_equivalent_to_crud(self):
        """Test Query operation is NOT equivalent to any CRUD."""
        pattern = {
            'name': 'get_user_orders',
            'operation': 'Query',
            'parameters': [{'name': 'user_id', 'type': 'string'}],
        }
        entity_config = {'pk_params': ['user_id'], 'sk_params': []}

        result = is_semantically_equivalent_to_crud(pattern, 'User', entity_config)
        assert result is False


@pytest.mark.unit
class TestItemCollectionDetection:
    """Test item collection detection for Query SK filtering."""

    def test_detect_item_collection_true(self):
        """Test detection of item collection (multiple entities share PK)."""
        entity_config = {'pk_template': 'TENANT#{tenant_id}#USER#{user_id}'}
        table_data = {
            'entities': {
                'TenantUser': {'pk_template': 'TENANT#{tenant_id}#USER#{user_id}'},
                'TenantProgress': {'pk_template': 'TENANT#{tenant_id}#USER#{user_id}'},
            }
        }
        result = detect_item_collection('TenantUser', entity_config, table_data)
        assert result is True

    def test_detect_item_collection_false_different_pks(self):
        """Test no item collection when entities have different PKs."""
        entity_config = {'pk_template': 'USER#{user_id}'}
        table_data = {
            'entities': {
                'User': {'pk_template': 'USER#{user_id}'},
                'Order': {'pk_template': 'ORDER#{order_id}'},
            }
        }
        result = detect_item_collection('User', entity_config, table_data)
        assert result is False

    def test_detect_item_collection_single_entity(self):
        """Test no item collection when only one entity in table."""
        entity_config = {'pk_template': 'USER#{user_id}'}
        table_data = {'entities': {'User': {'pk_template': 'USER#{user_id}'}}}
        result = detect_item_collection('User', entity_config, table_data)
        assert result is False

    def test_get_sk_prefix_with_variables(self):
        """Test SK prefix extraction with template variables."""
        assert get_sk_prefix('PROGRESS#{course_id}#{lesson_id}') == 'PROGRESS#'
        assert get_sk_prefix('ENROLLMENT#{date}') == 'ENROLLMENT#'
        assert get_sk_prefix('USER#{id}') == 'USER#'

    def test_get_sk_prefix_no_variables(self):
        """Test SK prefix extraction without template variables."""
        assert get_sk_prefix('USER#PROFILE') == 'USER#PROFILE'
        assert get_sk_prefix('METADATA') == 'METADATA'

    def test_get_sk_prefix_only_variable(self):
        """Test SK prefix extraction when template is only a variable."""
        assert get_sk_prefix('{timestamp}') == ''
        assert get_sk_prefix('{id}') == ''

    def test_get_sk_prefix_empty(self):
        """Test SK prefix extraction with empty template."""
        assert get_sk_prefix('') == ''
        assert get_sk_prefix(None) == ''


@pytest.mark.unit
class TestCrudMethodNames:
    """Tests for get_crud_method_names function."""

    def test_get_crud_method_names_fallback_no_naming_conventions(self):
        """Test CRUD method name generation fallback when no naming conventions (lines 50-58)."""
        # Create a language config without naming conventions
        language_config = LanguageConfig(
            name='test',
            file_extension='.test',
            naming_conventions=None,  # No naming conventions - triggers fallback
            file_patterns={},
            support_files=[],
            linter=None,
        )

        result = get_crud_method_names('UserProfile', language_config)
        expected = {
            'create_user_profile',
            'get_user_profile',
            'update_user_profile',
            'delete_user_profile',
        }
        assert result == expected


@pytest.mark.unit
class TestCrudSignatureEdgeCases:
    """Tests for edge cases in get_crud_signature."""

    def test_get_crud_signature_delete_with_single_key(self):
        """Test delete signature with single key parameter (line 115)."""
        entity_config = {
            'pk_template': 'USER#{user_id}',
            # No sk_template - single key
        }

        result = get_crud_signature('User', 'delete_user', entity_config)
        # Should return tuple with single 'string'
        assert result == ('string',)


@pytest.mark.unit
class TestSemanticEquivalenceEdgeCases:
    """Tests for edge cases in is_semantically_equivalent_to_crud."""

    def test_update_item_with_entity_param_equivalent(self):
        """Test UpdateItem with entity parameter is equivalent to update (line 179)."""
        pattern = {
            'name': 'update_user',
            'operation': 'UpdateItem',
            'parameters': [{'name': 'user', 'type': 'entity', 'entity_type': 'User'}],
        }
        entity_config = {'entity_type': 'USER'}

        result = is_semantically_equivalent_to_crud(pattern, 'User', entity_config)
        assert result is True


@pytest.mark.unit
class TestConsistentReadCapture:
    """Tests for consistent_read value capture in filter_conflicting_patterns.

    Background:
    - consistent_read parameter is supported by DynamoDB for: GetItem, Query, Scan, BatchGetItem, TransactGetItems
    - GSI queries do NOT support consistent_read=true (only eventually consistent)
    - Only GetItem operations have CRUD method equivalents (get_entity)
    - Query/Scan operations generate stubs with ConsistentRead hints in comments

    This test class focuses on GetItem patterns that map to CRUD get methods.
    """

    def test_capture_consistent_read_true_for_exact_name_match(self):
        """Test capturing consistent_read=true when pattern name exactly matches CRUD method."""
        access_patterns = [
            {
                'name': 'get_user',
                'operation': 'GetItem',
                'consistent_read': True,
                'parameters': [{'name': 'user_id', 'type': 'string'}],
            }
        ]
        crud_methods = {'create_user', 'get_user', 'update_user', 'delete_user'}
        entity_config = {'pk_params': ['user_id'], 'sk_params': []}

        filtered, crud_consistent_read = filter_conflicting_patterns(
            access_patterns, crud_methods, 'User', entity_config
        )

        # Pattern should be filtered out (semantically equivalent to CRUD)
        assert len(filtered) == 0
        # consistent_read value should be captured
        assert crud_consistent_read == {'get_user': True}

    def test_capture_consistent_read_true_for_semantic_equivalent(self):
        """Test capturing consistent_read=true when pattern is semantically equivalent but has different name."""
        access_patterns = [
            {
                'name': 'get_deal_by_id',
                'operation': 'GetItem',
                'consistent_read': True,
                'parameters': [{'name': 'deal_id', 'type': 'string'}],
            }
        ]
        crud_methods = {'create_deal', 'get_deal', 'update_deal', 'delete_deal'}
        entity_config = {'pk_params': ['deal_id'], 'sk_params': []}

        filtered, crud_consistent_read = filter_conflicting_patterns(
            access_patterns, crud_methods, 'Deal', entity_config
        )

        # Pattern should be filtered out (semantically equivalent to CRUD get_deal)
        assert len(filtered) == 0
        # consistent_read value should be captured for get_deal
        assert crud_consistent_read == {'get_deal': True}

    def test_no_capture_for_non_getitem_operations(self):
        """Test that consistent_read is NOT captured for Query/Scan operations.

        Rationale:
        - Query/Scan don't have CRUD method equivalents
        - They generate stubs with ConsistentRead hints in comments
        - No need to capture for template rendering
        """
        access_patterns = [
            {
                'name': 'query_users',
                'operation': 'Query',
                'consistent_read': True,
                'parameters': [{'name': 'status', 'type': 'string'}],
            },
            {
                'name': 'scan_all_users',
                'operation': 'Scan',
                'consistent_read': True,
                'parameters': [],
            },
        ]
        crud_methods = {'create_user', 'get_user', 'update_user', 'delete_user'}
        entity_config = {'pk_params': ['user_id'], 'sk_params': []}

        filtered, crud_consistent_read = filter_conflicting_patterns(
            access_patterns, crud_methods, 'User', entity_config
        )

        # Patterns kept (no CRUD conflict)
        assert len(filtered) == 2
        # No consistent_read captured (only GetItem operations are captured)
        assert crud_consistent_read == {}

    def test_or_logic_any_true_wins(self):
        """Test OR logic: if multiple patterns map to same CRUD, any true wins.

        Critical: Without OR logic, last pattern overwrites previous values.
        This test ensures consistent_read=true is preserved when multiple patterns
        with different values map to the same CRUD method.
        """
        access_patterns = [
            {
                'name': 'get_game',
                'operation': 'GetItem',
                'consistent_read': True,
                'parameters': [{'name': 'game_id', 'type': 'string'}],
            },
            {
                'name': 'get_game_by_id',
                'operation': 'GetItem',
                'consistent_read': False,
                'parameters': [{'name': 'game_id', 'type': 'string'}],
            },
        ]
        crud_methods = {'create_game', 'get_game', 'update_game', 'delete_game'}
        entity_config = {'pk_params': ['game_id'], 'sk_params': []}

        filtered, crud_consistent_read = filter_conflicting_patterns(
            access_patterns, crud_methods, 'Game', entity_config
        )

        assert len(filtered) == 0
        assert crud_consistent_read == {'get_game': True}  # True wins over False
