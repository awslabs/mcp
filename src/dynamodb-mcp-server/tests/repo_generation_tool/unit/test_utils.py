"""Unit tests for utility functions."""

import pytest
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.utils import (
    filter_conflicting_patterns,
    format_entity_imports,
    generate_renamed_method_name,
    generate_test_instruction,
    get_crud_signature,
    get_pattern_signature,
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

    def test_filter_conflicting_patterns(self):
        """Test filtering of conflicting access patterns - comprehensive scenarios."""
        # Test normal conflicts
        access_patterns = [
            {'name': 'create_user', 'operation': 'PutItem'},
            {'name': 'get_user', 'operation': 'GetItem'},
            {'name': 'create_user_profile', 'operation': 'PutItem'},  # Conflicts with CRUD
            {'name': 'custom_query', 'operation': 'Query'},
            {'name': 'update_user_profile', 'operation': 'UpdateItem'},  # Conflicts with CRUD
            {'name': 'special_operation', 'operation': 'Scan'},
        ]
        crud_methods = [
            'create_user_profile',
            'get_user_profile',
            'update_user_profile',
            'delete_user_profile',
        ]
        result = filter_conflicting_patterns(access_patterns, crud_methods)
        assert len(result) == 4
        result_names = [pattern['name'] for pattern in result]
        assert 'create_user_profile' not in result_names
        assert 'update_user_profile' not in result_names
        assert 'create_user' in result_names
        assert 'custom_query' in result_names

        # Test no conflicts
        no_conflict_patterns = [
            {'name': 'custom_query', 'operation': 'Query'},
            {'name': 'special_scan', 'operation': 'Scan'},
            {'name': 'batch_operation', 'operation': 'BatchGetItem'},
        ]
        result = filter_conflicting_patterns(no_conflict_patterns, ['create_user', 'get_user'])
        assert len(result) == 3
        assert result == no_conflict_patterns

        # Test all conflicts
        all_conflict_patterns = [
            {'name': 'create_user', 'operation': 'PutItem'},
            {'name': 'get_user', 'operation': 'GetItem'},
        ]
        result = filter_conflicting_patterns(all_conflict_patterns, ['create_user', 'get_user'])
        assert len(result) == 0

        # Test empty inputs
        assert filter_conflicting_patterns([], ['create_user']) == []
        assert filter_conflicting_patterns([{'name': 'query', 'operation': 'Query'}], []) == [
            {'name': 'query', 'operation': 'Query'}
        ]
        assert filter_conflicting_patterns([], []) == []

        # Test case sensitivity
        case_patterns = [
            {'name': 'Create_User', 'operation': 'PutItem'},
            {'name': 'create_user', 'operation': 'PutItem'},
        ]
        result = filter_conflicting_patterns(case_patterns, ['create_user'])
        assert len(result) == 1
        assert result[0]['name'] == 'Create_User'


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
        """Test filter_conflicting_patterns with signature-based detection."""
        access_patterns = [
            # True duplicate - same signature as CRUD create
            {
                'name': 'create_appointment',
                'pattern_id': 1,
                'operation': 'PutItem',
                'parameters': [{'name': 'appointment', 'type': 'entity'}],
            },
            # Different signature - should be renamed
            {
                'name': 'create_appointment',
                'pattern_id': 17,
                'operation': 'PutItem',
                'parameters': [
                    {'name': 'appointment', 'type': 'entity'},
                    {'name': 'patient', 'type': 'entity'},
                    {'name': 'provider', 'type': 'entity'},
                ],
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
        entity_config = {'pk_params': ['appointment_id'], 'sk_params': []}

        result = filter_conflicting_patterns(
            access_patterns, crud_methods, entity_name='Appointment', entity_config=entity_config
        )

        # Should have 2 patterns: renamed create_appointment_with_refs and update_appointment_status
        assert len(result) == 2

        result_names = [p['name'] for p in result]
        assert 'create_appointment_with_refs' in result_names
        assert 'update_appointment_status' in result_names
        assert 'create_appointment' not in result_names

        # Check that original_name is preserved
        renamed_pattern = next(p for p in result if p['name'] == 'create_appointment_with_refs')
        assert renamed_pattern.get('original_name') == 'create_appointment'
        assert renamed_pattern['pattern_id'] == 17

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

        result = filter_conflicting_patterns(
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

    def test_putitem_single_entity_equivalent_to_crud_create(self):
        """Test PutItem with single entity param is equivalent to CRUD create when name matches."""
        pattern = {
            'name': 'create_user_account',  # Contains 'create_user'
            'operation': 'PutItem',
            'parameters': [{'name': 'user', 'type': 'entity', 'entity_type': 'User'}],
        }
        entity_config = {'pk_params': ['user_id'], 'sk_params': []}

        result = is_semantically_equivalent_to_crud(pattern, 'User', entity_config)
        assert result is True

    def test_putitem_different_name_not_equivalent(self):
        """Test PutItem with different name is NOT equivalent (e.g., add_product_to_category)."""
        pattern = {
            'name': 'add_product_to_category',  # Does NOT contain 'create_product_category'
            'operation': 'PutItem',
            'parameters': [{'name': 'category_item', 'type': 'entity'}],
        }
        entity_config = {'pk_params': ['category_name'], 'sk_params': ['product_id']}

        result = is_semantically_equivalent_to_crud(pattern, 'ProductCategory', entity_config)
        assert result is False

    def test_putitem_with_extra_params_not_equivalent(self):
        """Test PutItem with extra params is NOT equivalent (cross-table ref)."""
        pattern = {
            'name': 'create_appointment',
            'operation': 'PutItem',
            'parameters': [
                {'name': 'appointment', 'type': 'entity'},
                {'name': 'patient', 'type': 'entity'},
                {'name': 'provider', 'type': 'entity'},
            ],
        }
        entity_config = {'pk_params': ['appointment_id'], 'sk_params': []}

        result = is_semantically_equivalent_to_crud(pattern, 'Appointment', entity_config)
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

    def test_filter_removes_semantic_duplicates(self):
        """Test filter_conflicting_patterns removes semantic duplicates."""
        access_patterns = [
            # Semantic duplicate of get_user (name contains 'get_user', same operation+params)
            {
                'name': 'get_user_by_id',
                'pattern_id': 1,
                'operation': 'GetItem',
                'parameters': [{'name': 'user_id', 'type': 'string'}],
            },
            # Semantic duplicate of create_user (name contains 'create_user')
            {
                'name': 'create_user_account',
                'pattern_id': 2,
                'operation': 'PutItem',
                'parameters': [{'name': 'user', 'type': 'entity'}],
            },
            # NOT a duplicate - different name pattern (doesn't contain 'create_user')
            {
                'name': 'add_new_user',
                'pattern_id': 3,
                'operation': 'PutItem',
                'parameters': [{'name': 'user', 'type': 'entity'}],
            },
            # NOT a duplicate - Query operation
            {
                'name': 'get_user_orders',
                'pattern_id': 4,
                'operation': 'Query',
                'parameters': [{'name': 'user_id', 'type': 'string'}],
            },
        ]

        crud_methods = {'create_user', 'get_user', 'update_user', 'delete_user'}
        entity_config = {'pk_params': ['user_id'], 'sk_params': []}

        result = filter_conflicting_patterns(
            access_patterns, crud_methods, entity_name='User', entity_config=entity_config
        )

        # add_new_user and get_user_orders should remain
        assert len(result) == 2
        result_names = [p['name'] for p in result]
        assert 'add_new_user' in result_names
        assert 'get_user_orders' in result_names
