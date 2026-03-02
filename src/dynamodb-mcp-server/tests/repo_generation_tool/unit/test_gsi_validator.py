"""Unit tests for GSI validation system."""

import pytest
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.gsi_validator import GSIValidator
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_definitions import (
    AccessPattern,
    Field,
    GSIDefinition,
    GSIMapping,
)


@pytest.mark.unit
class TestGSIValidator:
    """Unit tests for GSIValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = GSIValidator()

        # Sample GSI definitions
        self.sample_gsi_list = [
            GSIDefinition(name='UserStatusIndex', partition_key='GSI1PK', sort_key='GSI1SK'),
            GSIDefinition(name='CreatedAtIndex', partition_key='GSI2PK', sort_key='GSI2SK'),
        ]

        # Sample entity fields
        self.sample_fields = [
            Field(name='user_id', type='string', required=True),
            Field(name='status', type='string', required=False),
            Field(name='created_at', type='string', required=True),
            Field(name='score', type='integer', required=False),
        ]

        # Sample GSI mappings
        self.sample_gsi_mappings = [
            GSIMapping(
                name='UserStatusIndex', pk_template='USER#{user_id}', sk_template='STATUS#{status}'
            ),
            GSIMapping(
                name='CreatedAtIndex',
                pk_template='DATE#{created_at}',
                sk_template='USER#{user_id}',
            ),
        ]


@pytest.mark.unit
class TestValidateGSINamesUnique(TestGSIValidator):
    """Test GSI name uniqueness validation."""

    def test_validate_unique_gsi_names_success(self):
        """Test validation passes when all GSI names are unique."""
        errors = self.validator.validate_gsi_names_unique(self.sample_gsi_list)
        assert errors == []
        assert self.validator.validate_gsi_names_unique([]) == []

    def test_validate_duplicate_gsi_names(self):
        """Test validation fails when GSI names are duplicated."""
        duplicate_gsi_list = [
            GSIDefinition(name='UserIndex', partition_key='GSI1PK', sort_key='GSI1SK'),
            GSIDefinition(name='UserIndex', partition_key='GSI2PK', sort_key='GSI2SK'),
            GSIDefinition(name='StatusIndex', partition_key='GSI3PK', sort_key='GSI3SK'),
        ]
        errors = self.validator.validate_gsi_names_unique(duplicate_gsi_list)
        assert len(errors) == 1
        assert "Duplicate GSI name 'UserIndex'" in errors[0].message

    def test_validate_multiple_duplicates(self):
        """Test validation with multiple duplicate GSI names."""
        duplicate_gsi_list = [
            GSIDefinition(name='Index1', partition_key='GSI1PK', sort_key='GSI1SK'),
            GSIDefinition(name='Index1', partition_key='GSI2PK', sort_key='GSI2SK'),
            GSIDefinition(name='Index2', partition_key='GSI3PK', sort_key='GSI3SK'),
            GSIDefinition(name='Index2', partition_key='GSI4PK', sort_key='GSI4SK'),
        ]
        errors = self.validator.validate_gsi_names_unique(duplicate_gsi_list)
        assert len(errors) == 2
        duplicate_names = {error.message.split("'")[1] for error in errors}
        assert duplicate_names == {'Index1', 'Index2'}

    def test_validate_gsi_names_unique_invalid_gsi_object(self):
        """Test GSI name validation with invalid GSI object."""
        invalid_gsi_list = ['not_a_gsi_object']
        errors = self.validator.validate_gsi_names_unique(invalid_gsi_list)
        assert len(errors) == 1
        assert 'GSI definition must be a GSIDefinition object' in errors[0].message


@pytest.mark.unit
class TestValidateGSIMappings(TestGSIValidator):
    """Test GSI mapping validation."""

    def test_validate_mappings_all_valid(self):
        """Test validation passes when all GSI mappings reference valid GSIs."""
        errors = self.validator.validate_gsi_mappings(
            self.sample_gsi_mappings, self.sample_gsi_list
        )
        assert errors == []
        assert self.validator.validate_gsi_mappings([], self.sample_gsi_list) == []

    def test_validate_mappings_multiple_invalid(self):
        """Test validation with multiple invalid GSI references."""
        invalid_mappings = [
            GSIMapping(
                name='InvalidIndex1', pk_template='USER#{user_id}', sk_template='STATUS#{status}'
            ),
            GSIMapping(
                name='InvalidIndex2', pk_template='DATE#{created_at}', sk_template='USER#{user_id}'
            ),
        ]
        errors = self.validator.validate_gsi_mappings(invalid_mappings, self.sample_gsi_list)
        assert len(errors) == 2
        invalid_names = {error.message.split("'")[1] for error in errors}
        assert invalid_names == {'InvalidIndex1', 'InvalidIndex2'}

    def test_validate_gsi_mappings_invalid_mapping_object(self):
        """Test GSI mapping validation with invalid mapping object."""
        invalid_mappings = ['not_a_mapping_object']
        errors = self.validator.validate_gsi_mappings(invalid_mappings, self.sample_gsi_list)
        assert len(errors) == 1
        assert 'GSI mapping must be a GSIMapping object' in errors[0].message


@pytest.mark.unit
class TestValidateTemplateParameters(TestGSIValidator):
    """Test template parameter validation."""

    def test_validate_template_parameters_valid(self):
        """Test validation passes when all template parameters exist in entity fields."""
        template = 'USER#{user_id}#STATUS#{status}'
        errors = self.validator.validate_template_parameters(
            template, self.sample_fields, 'gsi_mappings[0]', 'pk_template'
        )
        assert errors == []

    def test_validate_template_parameters_errors(self):
        """Test template parameter validation with various error conditions."""
        # Missing field
        template = 'USER#{user_id}#INVALID#{invalid_field}'
        errors = self.validator.validate_template_parameters(
            template, self.sample_fields, 'gsi_mappings[0]', 'pk_template'
        )
        assert len(errors) == 1
        assert 'invalid_field' in errors[0].message

        # Syntax error
        template = 'USER#{user_id}#STATUS#{'
        errors = self.validator.validate_template_parameters(
            template, self.sample_fields, 'gsi_mappings[0]', 'sk_template'
        )
        assert len(errors) == 1
        assert 'Unmatched braces' in errors[0].message

        # Empty template
        errors = self.validator.validate_template_parameters(
            '', self.sample_fields, 'gsi_mappings[0]', 'pk_template'
        )
        assert len(errors) == 1
        assert 'Template cannot be empty' in errors[0].message

        # Static template (no errors)
        errors = self.validator.validate_template_parameters(
            'STATIC_VALUE', self.sample_fields, 'gsi_mappings[0]', 'pk_template'
        )
        assert errors == []


@pytest.mark.unit
class TestValidateRangeConditions(TestGSIValidator):
    """Test range condition validation."""

    def test_validate_range_conditions_valid_values(self):
        """Test validation passes for all valid range condition values."""
        valid_conditions = ['begins_with', 'between', '>', '<', '>=', '<=']
        for condition in valid_conditions:
            errors = self.validator.validate_range_conditions(condition, 'test_path')
            assert errors == []

    def test_validate_range_conditions_invalid_value(self):
        """Test validation fails for invalid range condition."""
        errors = self.validator.validate_range_conditions('invalid_condition', 'test_path')
        assert len(errors) == 1
        assert 'invalid_condition' in errors[0].message


@pytest.mark.unit
class TestValidateParameterCount(TestGSIValidator):
    """Test parameter count validation."""

    def test_validate_parameter_count_valid(self):
        """Test validation passes for correct parameter count."""
        pattern = AccessPattern(
            pattern_id=1,
            name='test',
            description='test',
            operation='query',
            parameters=['param1', 'param2'],
            return_type='single',
            range_condition='begins_with',
        )
        errors = self.validator.validate_parameter_count(pattern, 'test_path')
        assert errors == []

    def test_validate_parameter_count_invalid(self):
        """Test validation fails for incorrect parameter count."""
        pattern = AccessPattern(
            pattern_id=1,
            name='test',
            description='test',
            operation='query',
            parameters=[],
            return_type='single',
            range_condition='between',
        )
        errors = self.validator.validate_parameter_count(pattern, 'test_path')
        assert len(errors) >= 1


@pytest.mark.unit
class TestValidateGSIAccessPatterns(TestGSIValidator):
    """Test GSI access pattern validation."""

    def test_validate_gsi_access_patterns_valid(self):
        """Test validation passes for valid GSI access patterns."""
        patterns = [
            AccessPattern(
                pattern_id=1,
                name='test',
                description='test',
                operation='query',
                parameters=['param1'],
                return_type='single',
                index_name='UserStatusIndex',
            )
        ]
        errors = self.validator.validate_gsi_access_patterns(patterns, self.sample_gsi_list)
        assert errors == []
        assert self.validator.validate_gsi_access_patterns([], self.sample_gsi_list) == []

        # Pattern without index_name
        patterns = [
            AccessPattern(
                pattern_id=1,
                name='test',
                description='test',
                operation='query',
                parameters=['param1'],
                return_type='single',
                index_name=None,
            )
        ]
        assert self.validator.validate_gsi_access_patterns(patterns, self.sample_gsi_list) == []

    def test_validate_gsi_access_patterns_invalid_index(self):
        """Test validation fails for invalid GSI reference."""
        patterns = [
            AccessPattern(
                pattern_id=1,
                name='test',
                description='test',
                operation='query',
                parameters=['param1'],
                return_type='single',
                index_name='InvalidIndex',
            )
        ]
        errors = self.validator.validate_gsi_access_patterns(patterns, self.sample_gsi_list)
        assert len(errors) == 1
        assert 'InvalidIndex' in errors[0].message


@pytest.mark.unit
class TestValidateCompleteGSIConfiguration(TestGSIValidator):
    """Test complete GSI configuration validation."""

    def test_validate_complete_gsi_configuration_valid(self):
        """Test validation passes for valid complete configuration."""
        table_data = {
            'gsi_list': [{'name': 'UserIndex', 'partition_key': 'GSI1PK', 'sort_key': 'GSI1SK'}],
            'entities': {
                'User': {
                    'fields': [{'name': 'user_id', 'type': 'string', 'required': True}],
                    'gsi_mappings': [{'name': 'UserIndex', 'pk_template': 'USER#{user_id}'}],
                }
            },
        }
        errors = self.validator.validate_complete_gsi_configuration(table_data)
        assert errors == []

        # Without entities
        table_data = {
            'gsi_list': [{'name': 'UserIndex', 'partition_key': 'GSI1PK', 'sort_key': 'GSI1SK'}]
        }
        assert self.validator.validate_complete_gsi_configuration(table_data) == []

    def test_validate_complete_gsi_configuration_invalid_gsi_list(self):
        """Test validation fails for invalid GSI list."""
        table_data = {'gsi_list': 'not_a_list'}
        errors = self.validator.validate_complete_gsi_configuration(table_data)
        assert len(errors) == 1
        assert 'gsi_list must be an array' in errors[0].message


@pytest.mark.unit
class TestPrivateHelperMethods(TestGSIValidator):
    """Test private helper methods."""

    def test_parse_gsi_list_errors(self):
        """Test GSI list parsing with various error conditions."""
        # Invalid GSI object
        table_data = {'gsi_list': ['not_an_object']}
        gsi_list, errors = self.validator._parse_gsi_list(table_data, 'table')
        assert len(errors) == 1
        assert 'GSI definition must be an object' in errors[0].message

        # Missing required fields
        table_data = {'gsi_list': [{'name': 'TestIndex'}]}
        gsi_list, errors = self.validator._parse_gsi_list(table_data, 'table')
        assert len(errors) == 1
        assert 'missing required fields' in errors[0].message
        assert 'partition_key' in errors[0].message

    def test_parse_gsi_list_exception_in_loop(self):
        """Test GSI list parsing with exception during GSIDefinition creation."""

        # Create a mock that raises exception when accessing name
        class BadDict(dict):
            def __getitem__(self, key):
                if key == 'name':
                    raise ValueError('Test exception')
                return super().__getitem__(key)

        bad_gsi = BadDict({'name': 'test', 'partition_key': 'pk'})
        table_data = {'gsi_list': [bad_gsi]}
        gsi_list, errors = self.validator._parse_gsi_list(table_data, 'table')
        assert len(errors) == 1
        assert 'Failed to parse GSI definitions' in errors[0].message

    def test_parse_entity_fields(self):
        """Test parsing entity fields with various conditions."""
        # Invalid fields structure
        entity_data = {'fields': 'not_a_list'}
        fields, errors = self.validator._parse_entity_fields(entity_data, 'entity')
        assert len(errors) == 1
        assert 'Entity fields must be an array' in errors[0].message

        # No fields key
        entity_data = {}
        fields, errors = self.validator._parse_entity_fields(entity_data, 'entity')
        assert fields == []
        assert errors == []

    def test_validate_entity_gsi_mappings_errors(self):
        """Test GSI mapping validation with various error conditions."""
        # Invalid mappings structure
        entity_data = {'gsi_mappings': 'not_a_list'}
        errors = self.validator._validate_entity_gsi_mappings(
            entity_data, self.sample_fields, self.sample_gsi_list, 'entity'
        )
        assert len(errors) == 1
        assert 'GSI mappings must be an array' in errors[0].message

        # Invalid mapping dict
        entity_data = {'gsi_mappings': ['not_a_dict']}
        errors = self.validator._validate_entity_gsi_mappings(
            entity_data, self.sample_fields, self.sample_gsi_list, 'entity'
        )
        assert len(errors) == 1
        assert 'GSI mapping must be an object' in errors[0].message

        # Missing required fields
        entity_data = {'gsi_mappings': [{'pk_template': 'USER#{user_id}'}]}
        errors = self.validator._validate_entity_gsi_mappings(
            entity_data, self.sample_fields, self.sample_gsi_list, 'entity'
        )
        assert len(errors) == 1
        assert 'missing required fields' in errors[0].message

    def test_validate_entity_gsi_mappings_exception_in_loop(self):
        """Test GSI mapping validation with exception during GSIMapping creation."""

        # Create a mock that raises exception when accessing name
        class BadDict(dict):
            def __getitem__(self, key):
                if key == 'name':
                    raise ValueError('Test exception')
                return super().__getitem__(key)

        bad_mapping = BadDict({'name': 'test', 'pk_template': 'USER#{user_id}'})
        entity_data = {'gsi_mappings': [bad_mapping]}
        errors = self.validator._validate_entity_gsi_mappings(
            entity_data, self.sample_fields, self.sample_gsi_list, 'entity'
        )
        assert len(errors) == 1
        assert 'Failed to parse GSI mappings' in errors[0].message

    def test_validate_entities_gsi_configuration_field_errors(self):
        """Test entity validation with field parsing errors."""
        entities = {'User': {'fields': 'invalid_fields'}}
        errors = self.validator._validate_entities_gsi_configuration(
            entities, self.sample_gsi_list, 'table'
        )
        assert len(errors) == 1
        assert 'Entity fields must be an array' in errors[0].message

    def test_validate_entity_gsi_mappings_templates(self):
        """Test GSI mapping validation with valid and invalid templates."""
        # Empty gsi_mappings
        assert (
            self.validator._validate_entity_gsi_mappings(
                {}, self.sample_fields, self.sample_gsi_list, 'entity'
            )
            == []
        )
        assert (
            self.validator._validate_entity_gsi_mappings(
                {'gsi_mappings': []}, self.sample_fields, self.sample_gsi_list, 'entity'
            )
            == []
        )

        # Valid with sk_template
        entity_data = {
            'gsi_mappings': [
                {
                    'name': 'UserStatusIndex',
                    'pk_template': 'USER#{user_id}',
                    'sk_template': 'STATUS#{status}',
                }
            ]
        }
        errors = self.validator._validate_entity_gsi_mappings(
            entity_data, self.sample_fields, self.sample_gsi_list, 'entity'
        )
        assert errors == []

        # Invalid pk_template
        entity_data = {
            'gsi_mappings': [{'name': 'UserStatusIndex', 'pk_template': 'USER#{invalid_field}'}]
        }
        errors = self.validator._validate_entity_gsi_mappings(
            entity_data, self.sample_fields, self.sample_gsi_list, 'entity'
        )
        assert len(errors) == 1
        assert 'invalid_field' in errors[0].message

        # Invalid sk_template
        entity_data = {
            'gsi_mappings': [
                {
                    'name': 'UserStatusIndex',
                    'pk_template': 'USER#{user_id}',
                    'sk_template': 'STATUS#{invalid_field}',
                }
            ]
        }
        errors = self.validator._validate_entity_gsi_mappings(
            entity_data, self.sample_fields, self.sample_gsi_list, 'entity'
        )
        assert len(errors) == 1
        assert 'invalid_field' in errors[0].message

    def test_validate_gsi_mappings_empty_gsi_list(self):
        """Test GSI mapping validation when no GSIs are defined."""
        errors = self.validator.validate_gsi_mappings(self.sample_gsi_mappings, [])
        assert len(errors) == 2
        for error in errors:
            assert 'not found in table gsi_list' in error.message

    def test_parse_gsi_list_empty_missing_and_optional_sort_key(self):
        """Test GSI list parsing with empty/missing gsi_list and optional sort_key."""
        # Missing and empty gsi_list
        assert self.validator._parse_gsi_list({}, 'table') == ([], [])
        assert self.validator._parse_gsi_list({'gsi_list': []}, 'table') == ([], [])

        # Optional sort_key
        table_data = {
            'gsi_list': [
                {'name': 'TestIndex', 'partition_key': 'GSI1PK', 'sort_key': 'GSI1SK'},
                {'name': 'TestIndex2', 'partition_key': 'GSI2PK'},
            ]
        }
        gsi_list, errors = self.validator._parse_gsi_list(table_data, 'table')
        assert len(errors) == 0 and len(gsi_list) == 2
        assert gsi_list[0].sort_key == 'GSI1SK' and gsi_list[1].sort_key is None

    def test_validate_template_parameters_extraction_exception(self):
        """Test template parameter validation when extraction fails."""
        # Mock a scenario where extract_parameters raises an exception
        template = 'USER#{user_id}'
        # Force an exception by passing invalid data to the parser
        original_extract = self.validator.template_parser.extract_parameters
        self.validator.template_parser.extract_parameters = lambda template: (_ for _ in ()).throw(
            Exception('Test error')
        )

        errors = self.validator.validate_template_parameters(
            template, self.sample_fields, 'test_path', 'pk_template'
        )

        # Restore original method
        self.validator.template_parser.extract_parameters = original_extract

        assert len(errors) == 1
        assert 'Failed to extract parameters' in errors[0].message

    def test_validate_gsi_access_patterns_invalid_range_and_empty_gsi(self):
        """Test GSI access pattern validation with invalid range condition and empty GSI list."""
        # Invalid range condition
        patterns = [
            AccessPattern(
                pattern_id=1,
                name='test',
                description='test',
                operation='query',
                parameters=['param1'],
                return_type='single',
                index_name='UserStatusIndex',
                range_condition='invalid_op',
            )
        ]
        errors = self.validator.validate_gsi_access_patterns(patterns, self.sample_gsi_list)
        assert len(errors) >= 1

        # Empty GSI list
        patterns = [
            AccessPattern(
                pattern_id=1,
                name='test',
                description='test',
                operation='query',
                parameters=['param1'],
                return_type='single',
                index_name='InvalidIndex',
            )
        ]
        errors = self.validator.validate_gsi_access_patterns(patterns, [])
        assert len(errors) == 1
        assert 'Define GSI in table gsi_list' in errors[0].suggestion

    def test_validate_entity_access_patterns_comprehensive(self):
        """Test entity access pattern validation with various scenarios."""
        # Missing/invalid access_patterns
        assert (
            self.validator._validate_entity_access_patterns({}, self.sample_gsi_list, 'entity')
            == []
        )
        assert (
            self.validator._validate_entity_access_patterns(
                {'access_patterns': 'not_a_list'}, self.sample_gsi_list, 'entity'
            )
            == []
        )

        # Valid patterns with parameters
        entity_data = {
            'access_patterns': [
                {
                    'pattern_id': 1,
                    'name': 'test',
                    'description': 'test',
                    'operation': 'query',
                    'parameters': ['param1', 'param2'],
                    'return_type': 'single',
                    'index_name': 'UserStatusIndex',
                }
            ]
        }
        assert (
            self.validator._validate_entity_access_patterns(
                entity_data, self.sample_gsi_list, 'entity'
            )
            == []
        )

        # Non-dict patterns (skipped), missing parameters, invalid parameters
        entity_data = {
            'access_patterns': [
                'not_a_dict',
                {
                    'pattern_id': 1,
                    'name': 'valid',
                    'description': 'test',
                    'operation': 'query',
                    'return_type': 'single',
                    'index_name': 'UserStatusIndex',
                },
                {
                    'pattern_id': 2,
                    'name': 'test2',
                    'description': 'test',
                    'operation': 'query',
                    'parameters': 'not_a_list',
                    'return_type': 'single',
                    'index_name': 'UserStatusIndex',
                },
            ]
        }
        assert (
            self.validator._validate_entity_access_patterns(
                entity_data, self.sample_gsi_list, 'entity'
            )
            == []
        )

    def test_validate_entity_access_patterns_exception_handling(self):
        """Test entity access pattern validation exception handling."""
        entity_data = {'access_patterns': [{'pattern_id': None, 'name': None}]}
        original_validate = self.validator.validate_gsi_access_patterns
        self.validator.validate_gsi_access_patterns = lambda *args, **kwargs: (
            _ for _ in ()
        ).throw(Exception('Test'))
        errors = self.validator._validate_entity_access_patterns(
            entity_data, self.sample_gsi_list, 'entity'
        )
        self.validator.validate_gsi_access_patterns = original_validate
        assert len(errors) >= 1 and 'Failed to parse access patterns' in errors[0].message

    def test_validate_entities_gsi_configuration_invalid_entities(self):
        """Test entity GSI configuration validation with invalid entities."""
        assert (
            self.validator._validate_entities_gsi_configuration(
                'not_a_dict', self.sample_gsi_list, 'table'
            )
            == []
        )
        assert (
            self.validator._validate_entities_gsi_configuration(
                {'User': 'not_a_dict'}, self.sample_gsi_list, 'table'
            )
            == []
        )

    def test_parse_entity_fields_comprehensive(self):
        """Test parsing entity fields with various scenarios."""
        # Valid fields with item_type and invalid field objects (non-dict, missing name)
        entity_data = {
            'fields': [
                {'name': 'user_id', 'type': 'string', 'required': True},
                {'name': 'status', 'type': 'string', 'required': False, 'item_type': 'list'},
            ]
        }
        fields, errors = self.validator._parse_entity_fields(entity_data, 'entity')
        assert (
            len(fields) == 2
            and errors == []
            and fields[0].name == 'user_id'
            and fields[1].item_type == 'list'
        )

        entity_data = {
            'fields': ['not_a_dict', {'type': 'string'}, {'name': 'valid_field', 'type': 'string'}]
        }
        fields, errors = self.validator._parse_entity_fields(entity_data, 'entity')
        assert len(fields) == 1 and fields[0].name == 'valid_field' and errors == []


@pytest.mark.unit
class TestKeyTemplateLengthMatch(TestGSIValidator):
    """Test cross-validation between GSI key definitions and mapping templates."""

    def test_matching_string_pk_passes(self):
        """String partition_key with string pk_template — no error."""
        gsi_def = GSIDefinition(name='Idx', partition_key='pk_attr', sort_key='sk_attr')
        mapping = GSIMapping(name='Idx', pk_template='PREFIX#{user_id}', sk_template='SK#{status}')
        errors = self.validator._validate_key_template_length_match(gsi_def, mapping, 'path')
        assert errors == []

    def test_matching_array_pk_passes(self):
        """Array partition_key with same-length array pk_template — no error."""
        gsi_def = GSIDefinition(name='Idx', partition_key=['a', 'b'], sort_key='sk')
        mapping = GSIMapping(name='Idx', pk_template=['{a}', '{b}'], sk_template='{sk}')
        errors = self.validator._validate_key_template_length_match(gsi_def, mapping, 'path')
        assert errors == []

    def test_matching_array_sk_passes(self):
        """Array sort_key with same-length array sk_template — no error."""
        gsi_def = GSIDefinition(name='Idx', partition_key='pk', sort_key=['s1', 's2', 's3'])
        mapping = GSIMapping(name='Idx', pk_template='{pk}', sk_template=['{s1}', '{s2}', '{s3}'])
        errors = self.validator._validate_key_template_length_match(gsi_def, mapping, 'path')
        assert errors == []

    def test_pk_array_length_mismatch(self):
        """Array partition_key with different-length array pk_template — error."""
        gsi_def = GSIDefinition(name='Idx', partition_key=['a', 'b'], sort_key='sk')
        mapping = GSIMapping(name='Idx', pk_template=['{a}'], sk_template='{sk}')
        errors = self.validator._validate_key_template_length_match(gsi_def, mapping, 'path')
        assert len(errors) == 1
        assert 'pk_template array length (1)' in errors[0].message
        assert 'partition_key array length (2)' in errors[0].message

    def test_sk_array_length_mismatch(self):
        """Array sort_key with different-length array sk_template — error."""
        gsi_def = GSIDefinition(name='Idx', partition_key='pk', sort_key=['s1', 's2', 's3'])
        mapping = GSIMapping(name='Idx', pk_template='{pk}', sk_template=['{s1}', '{s2}'])
        errors = self.validator._validate_key_template_length_match(gsi_def, mapping, 'path')
        assert len(errors) == 1
        assert 'sk_template array length (2)' in errors[0].message
        assert 'sort_key array length (3)' in errors[0].message

    def test_pk_type_mismatch_array_vs_string(self):
        """Array partition_key with string pk_template — type mismatch error."""
        gsi_def = GSIDefinition(name='Idx', partition_key=['a', 'b'], sort_key='sk')
        mapping = GSIMapping(name='Idx', pk_template='{a}', sk_template='{sk}')
        errors = self.validator._validate_key_template_length_match(gsi_def, mapping, 'path')
        assert len(errors) == 1
        assert 'pk_template type (string)' in errors[0].message
        assert 'partition_key type (array)' in errors[0].message

    def test_pk_type_mismatch_string_vs_array(self):
        """String partition_key with array pk_template — type mismatch error."""
        gsi_def = GSIDefinition(name='Idx', partition_key='pk_attr', sort_key='sk')
        mapping = GSIMapping(name='Idx', pk_template=['{a}', '{b}'], sk_template='{sk}')
        errors = self.validator._validate_key_template_length_match(gsi_def, mapping, 'path')
        assert len(errors) == 1
        assert 'pk_template type (array)' in errors[0].message
        assert 'partition_key type (string)' in errors[0].message

    def test_sk_type_mismatch(self):
        """Array sort_key with string sk_template — type mismatch error."""
        gsi_def = GSIDefinition(name='Idx', partition_key='pk', sort_key=['s1', 's2'])
        mapping = GSIMapping(name='Idx', pk_template='{pk}', sk_template='{s1}')
        errors = self.validator._validate_key_template_length_match(gsi_def, mapping, 'path')
        assert len(errors) == 1
        assert 'sk_template type (string)' in errors[0].message
        assert 'sort_key type (array)' in errors[0].message

    def test_sk_skipped_when_either_is_none(self):
        """No SK cross-validation when sort_key or sk_template is None."""
        # sort_key is None
        gsi_def = GSIDefinition(name='Idx', partition_key='pk', sort_key=None)
        mapping = GSIMapping(name='Idx', pk_template='{pk}', sk_template='{something}')
        errors = self.validator._validate_key_template_length_match(gsi_def, mapping, 'path')
        assert errors == []

        # sk_template is None
        gsi_def = GSIDefinition(name='Idx', partition_key='pk', sort_key=['s1', 's2'])
        mapping = GSIMapping(name='Idx', pk_template='{pk}', sk_template=None)
        errors = self.validator._validate_key_template_length_match(gsi_def, mapping, 'path')
        assert errors == []

    def test_both_pk_and_sk_mismatch(self):
        """Both PK and SK mismatches produce two errors."""
        gsi_def = GSIDefinition(name='Idx', partition_key=['a', 'b'], sort_key=['s1', 's2', 's3'])
        mapping = GSIMapping(name='Idx', pk_template=['{a}'], sk_template=['{s1}'])
        errors = self.validator._validate_key_template_length_match(gsi_def, mapping, 'path')
        assert len(errors) == 2
        assert any('pk_template' in e.message for e in errors)
        assert any('sk_template' in e.message for e in errors)

    def test_integration_via_complete_gsi_configuration(self):
        """Cross-validation fires through the full validate_complete_gsi_configuration path."""
        table_data = {
            'gsi_list': [
                {
                    'name': 'MultiIdx',
                    'partition_key': ['tenant_id', 'region'],
                    'sort_key': ['created_at', 'order_id'],
                }
            ],
            'entities': {
                'Order': {
                    'fields': [
                        {'name': 'tenant_id', 'type': 'string', 'required': True},
                        {'name': 'region', 'type': 'string', 'required': True},
                        {'name': 'created_at', 'type': 'string', 'required': True},
                        {'name': 'order_id', 'type': 'string', 'required': True},
                    ],
                    'gsi_mappings': [
                        {
                            'name': 'MultiIdx',
                            'pk_template': ['{tenant_id}'],  # length 1 vs partition_key length 2
                            'sk_template': ['{created_at}', '{order_id}'],  # correct length
                        }
                    ],
                }
            },
        }
        errors = self.validator.validate_complete_gsi_configuration(table_data)
        assert any('pk_template array length (1)' in e.message for e in errors)
        # SK should pass — correct length
        assert not any('sk_template array length' in e.message for e in errors)


@pytest.mark.unit
class TestValidateMultiAttributeKey(TestGSIValidator):
    """Test _validate_multi_attribute_key static method."""

    def test_none_required_key_errors(self):
        """Required key that is None produces error."""
        errors = GSIValidator._validate_multi_attribute_key(
            None, 'partition_key', 'path', is_required=True
        )
        assert len(errors) == 1
        assert 'Missing required partition_key' in errors[0].message

    def test_none_optional_key_passes(self):
        """Optional key that is None produces no error."""
        errors = GSIValidator._validate_multi_attribute_key(
            None, 'sort_key', 'path', is_required=False
        )
        assert errors == []

    def test_invalid_type_errors(self):
        """Non-string, non-list value produces error."""
        errors = GSIValidator._validate_multi_attribute_key(123, 'partition_key', 'path')
        assert len(errors) == 1
        assert 'must be a string or array of strings' in errors[0].message

    def test_empty_string_errors(self):
        """Empty string key produces error."""
        errors = GSIValidator._validate_multi_attribute_key('  ', 'partition_key', 'path')
        assert len(errors) == 1
        assert 'cannot be empty' in errors[0].message

    def test_valid_string_passes(self):
        """Valid string key produces no error."""
        errors = GSIValidator._validate_multi_attribute_key('pk_attr', 'partition_key', 'path')
        assert errors == []

    def test_empty_array_errors(self):
        """Empty array produces error."""
        errors = GSIValidator._validate_multi_attribute_key([], 'partition_key', 'path')
        assert len(errors) == 1
        assert 'array cannot be empty' in errors[0].message

    def test_array_over_four_errors(self):
        """Array with >4 elements produces error."""
        errors = GSIValidator._validate_multi_attribute_key(
            ['a', 'b', 'c', 'd', 'e'], 'sort_key', 'path'
        )
        assert len(errors) == 1
        assert 'more than 4 attributes' in errors[0].message

    def test_array_non_string_element_errors(self):
        """Non-string element in array produces error."""
        errors = GSIValidator._validate_multi_attribute_key(['a', 123], 'partition_key', 'path')
        assert len(errors) == 1
        assert 'Attribute at index 1 must be a string' in errors[0].message

    def test_array_empty_string_element_errors(self):
        """Empty string element in array produces error."""
        errors = GSIValidator._validate_multi_attribute_key(['a', '  '], 'sort_key', 'path')
        assert len(errors) == 1
        assert 'Attribute at index 1 cannot be empty' in errors[0].message

    def test_valid_array_passes(self):
        """Valid array with 1-4 string elements passes."""
        errors = GSIValidator._validate_multi_attribute_key(
            ['a', 'b', 'c'], 'partition_key', 'path'
        )
        assert errors == []


@pytest.mark.unit
class TestValidateTemplateParametersArray(TestGSIValidator):
    """Test validate_template_parameters with array inputs."""

    def test_invalid_type_errors(self):
        """Non-string, non-list template produces error."""
        errors = self.validator.validate_template_parameters(
            123, self.sample_fields, 'path', 'pk_template'
        )
        assert len(errors) == 1
        assert 'must be a string or array of strings' in errors[0].message

    def test_empty_array_errors(self):
        """Empty array template produces error."""
        errors = self.validator.validate_template_parameters(
            [], self.sample_fields, 'path', 'sk_template'
        )
        assert len(errors) == 1
        assert 'array cannot be empty' in errors[0].message

    def test_array_over_four_errors(self):
        """Array with >4 templates produces error."""
        errors = self.validator.validate_template_parameters(
            ['{a}', '{b}', '{c}', '{d}', '{e}'], self.sample_fields, 'path', 'pk_template'
        )
        assert any('more than 4 templates' in e.message for e in errors)

    def test_array_non_string_element_errors(self):
        """Non-string element in template array produces error."""
        errors = self.validator.validate_template_parameters(
            ['{user_id}', 123], self.sample_fields, 'path', 'sk_template'
        )
        assert any('Template at index 1 must be a string' in e.message for e in errors)

    def test_valid_array_with_field_validation(self):
        """Valid array templates with existing fields pass."""
        errors = self.validator.validate_template_parameters(
            ['{user_id}', '{status}'], self.sample_fields, 'path', 'sk_template'
        )
        assert errors == []

    def test_array_with_invalid_field_reference(self):
        """Array template referencing non-existent field produces error."""
        errors = self.validator.validate_template_parameters(
            ['{user_id}', '{nonexistent}'], self.sample_fields, 'path', 'sk_template'
        )
        assert any('nonexistent' in e.message for e in errors)


@pytest.mark.unit
class TestParseGsiListMultiAttributeKeys(TestGSIValidator):
    """Test _parse_gsi_list with multi-attribute key validation errors."""

    def test_invalid_multi_attribute_pk_skips_gsi(self):
        """GSI with invalid multi-attribute PK is skipped (not added to list)."""
        table_data = {
            'gsi_list': [
                {
                    'name': 'BadIdx',
                    'partition_key': [],  # empty array — invalid
                }
            ]
        }
        gsi_list, errors = self.validator._parse_gsi_list(table_data, 'table')
        assert gsi_list == []
        assert len(errors) >= 1
        assert any('array cannot be empty' in e.message for e in errors)

    def test_invalid_multi_attribute_sk_skips_gsi(self):
        """GSI with invalid multi-attribute SK is skipped."""
        table_data = {
            'gsi_list': [
                {
                    'name': 'BadIdx',
                    'partition_key': 'pk',
                    'sort_key': ['a', 'b', 'c', 'd', 'e'],  # >4 — invalid
                }
            ]
        }
        gsi_list, errors = self.validator._parse_gsi_list(table_data, 'table')
        assert gsi_list == []
        assert any('more than 4 attributes' in e.message for e in errors)

    def test_valid_multi_attribute_keys_parsed(self):
        """GSI with valid multi-attribute keys is parsed correctly."""
        table_data = {
            'gsi_list': [
                {
                    'name': 'MultiIdx',
                    'partition_key': ['tenant', 'region'],
                    'sort_key': ['date', 'id'],
                }
            ]
        }
        gsi_list, errors = self.validator._parse_gsi_list(table_data, 'table')
        assert errors == []
        assert len(gsi_list) == 1
        assert gsi_list[0].partition_key == ['tenant', 'region']
        assert gsi_list[0].sort_key == ['date', 'id']


@pytest.mark.unit
class TestIncludeProjectionSafety(TestGSIValidator):
    """Test validate_include_projection_safety."""

    def test_non_include_projection_skipped(self):
        """GSIs with ALL or KEYS_ONLY projection produce no warnings."""
        gsi_list = [GSIDefinition(name='Idx', partition_key='pk', sort_key='sk', projection='ALL')]
        warnings = self.validator.validate_include_projection_safety(gsi_list, {}, {}, 'table')
        assert warnings == []

    def test_include_with_all_fields_projected_no_warning(self):
        """INCLUDE projection where all required fields are projected — no warning."""
        gsi_list = [
            GSIDefinition(
                name='Idx',
                partition_key='gsi_pk',
                sort_key='gsi_sk',
                projection='INCLUDE',
                included_attributes=['email'],
            )
        ]
        entities = {
            'User': {
                'gsi_mappings': [
                    {'name': 'Idx', 'pk_template': '{user_id}', 'sk_template': '{status}'}
                ],
                'fields': [
                    {'name': 'user_id', 'type': 'string', 'required': True},
                    {'name': 'status', 'type': 'string', 'required': True},
                    {'name': 'email', 'type': 'string', 'required': True},
                ],
            }
        }
        table_config = {'partition_key': 'pk', 'sort_key': 'sk'}
        warnings = self.validator.validate_include_projection_safety(
            gsi_list, entities, table_config, 'table'
        )
        assert warnings == []

    def test_include_with_required_non_projected_field_warns(self):
        """INCLUDE projection missing a required field produces warning."""
        gsi_list = [
            GSIDefinition(
                name='Idx',
                partition_key='gsi_pk',
                sort_key='gsi_sk',
                projection='INCLUDE',
                included_attributes=['email'],
            )
        ]
        entities = {
            'User': {
                'gsi_mappings': [{'name': 'Idx', 'pk_template': '{user_id}'}],
                'fields': [
                    {'name': 'user_id', 'type': 'string', 'required': True},
                    {'name': 'email', 'type': 'string', 'required': True},
                    {'name': 'age', 'type': 'integer', 'required': True},  # not projected
                ],
            }
        }
        table_config = {'partition_key': 'pk'}
        warnings = self.validator.validate_include_projection_safety(
            gsi_list, entities, table_config, 'table'
        )
        assert len(warnings) == 1
        assert 'age' in warnings[0].message
        assert warnings[0].severity == 'warning'

    def test_include_entity_not_using_gsi_skipped(self):
        """Entity that doesn't use the INCLUDE GSI produces no warning."""
        gsi_list = [
            GSIDefinition(
                name='Idx',
                partition_key='gsi_pk',
                projection='INCLUDE',
                included_attributes=['email'],
            )
        ]
        entities = {
            'User': {
                'gsi_mappings': [{'name': 'OtherIdx', 'pk_template': '{user_id}'}],
                'fields': [
                    {'name': 'user_id', 'type': 'string', 'required': True},
                    {'name': 'missing_field', 'type': 'string', 'required': True},
                ],
            }
        }
        warnings = self.validator.validate_include_projection_safety(
            gsi_list, entities, {}, 'table'
        )
        assert warnings == []

    def test_include_with_multi_attribute_sk_template(self):
        """INCLUDE projection with multi-attribute sk_template extracts fields correctly."""
        gsi_list = [
            GSIDefinition(
                name='Idx',
                partition_key='gsi_pk',
                sort_key=['s1', 's2'],
                projection='INCLUDE',
                included_attributes=['extra'],
            )
        ]
        entities = {
            'Order': {
                'gsi_mappings': [
                    {
                        'name': 'Idx',
                        'pk_template': '{store_id}',
                        'sk_template': ['{status}', '{date}'],
                    }
                ],
                'fields': [
                    {'name': 'store_id', 'type': 'string', 'required': True},
                    {'name': 'status', 'type': 'string', 'required': True},
                    {'name': 'date', 'type': 'string', 'required': True},
                    {'name': 'extra', 'type': 'string', 'required': True},
                ],
            }
        }
        table_config = {'partition_key': 'pk'}
        warnings = self.validator.validate_include_projection_safety(
            gsi_list, entities, table_config, 'table'
        )
        # store_id, status, date are in templates (always projected), extra is in included_attributes
        assert warnings == []


@pytest.mark.unit
class TestValidateIncludedAttributesExist(TestGSIValidator):
    """Test _validate_included_attributes_exist."""

    def test_non_include_projection_skipped(self):
        """GSIs without INCLUDE projection are skipped."""
        gsi_list = [GSIDefinition(name='Idx', partition_key='pk', projection='ALL')]
        errors = self.validator._validate_included_attributes_exist(gsi_list, {}, {}, 'table')
        assert errors == []

    def test_valid_included_attributes_pass(self):
        """Included attributes that exist in entity fields pass."""
        gsi_list = [
            GSIDefinition(
                name='Idx',
                partition_key='gsi_pk',
                projection='INCLUDE',
                included_attributes=['email'],
            )
        ]
        entities = {
            'User': {
                'gsi_mappings': [{'name': 'Idx', 'pk_template': '{user_id}'}],
                'fields': [
                    {'name': 'user_id', 'type': 'string', 'required': True},
                    {'name': 'email', 'type': 'string', 'required': True},
                ],
            }
        }
        errors = self.validator._validate_included_attributes_exist(
            gsi_list, entities, {}, 'table'
        )
        assert errors == []

    def test_nonexistent_included_attribute_errors(self):
        """Included attribute not in any entity field produces error."""
        gsi_list = [
            GSIDefinition(
                name='Idx',
                partition_key='gsi_pk',
                projection='INCLUDE',
                included_attributes=['nonexistent'],
            )
        ]
        entities = {
            'User': {
                'gsi_mappings': [{'name': 'Idx', 'pk_template': '{user_id}'}],
                'fields': [{'name': 'user_id', 'type': 'string', 'required': True}],
            }
        }
        errors = self.validator._validate_included_attributes_exist(
            gsi_list, entities, {}, 'table'
        )
        assert len(errors) == 1
        assert "'nonexistent' not found" in errors[0].message

    def test_key_attribute_in_included_attributes_errors(self):
        """Key attributes in included_attributes produce error (redundant)."""
        gsi_list = [
            GSIDefinition(
                name='Idx',
                partition_key='gsi_pk',
                sort_key='gsi_sk',
                projection='INCLUDE',
                included_attributes=['gsi_pk', 'email'],
            )
        ]
        entities = {
            'User': {
                'gsi_mappings': [{'name': 'Idx', 'pk_template': '{user_id}'}],
                'fields': [
                    {'name': 'user_id', 'type': 'string', 'required': True},
                    {'name': 'email', 'type': 'string', 'required': True},
                    {'name': 'gsi_pk', 'type': 'string', 'required': True},
                ],
            }
        }
        table_config = {'partition_key': 'pk', 'sort_key': 'sk'}
        errors = self.validator._validate_included_attributes_exist(
            gsi_list, entities, table_config, 'table'
        )
        assert any('key attributes in included_attributes' in e.message for e in errors)

    def test_entity_not_using_gsi_ignored(self):
        """Entity that doesn't use the GSI is not checked for field existence."""
        gsi_list = [
            GSIDefinition(
                name='Idx',
                partition_key='gsi_pk',
                projection='INCLUDE',
                included_attributes=['special_field'],
            )
        ]
        entities = {
            'User': {
                'gsi_mappings': [{'name': 'OtherIdx', 'pk_template': '{user_id}'}],
                'fields': [{'name': 'user_id', 'type': 'string', 'required': True}],
            }
        }
        errors = self.validator._validate_included_attributes_exist(
            gsi_list, entities, {}, 'table'
        )
        # special_field not found in any entity using this GSI
        assert any("'special_field' not found" in e.message for e in errors)

    def test_multi_attribute_gsi_keys_detected_as_key_attrs(self):
        """Multi-attribute GSI keys are correctly identified as key attributes."""
        gsi_list = [
            GSIDefinition(
                name='Idx',
                partition_key=['tenant', 'region'],
                sort_key=['date'],
                projection='INCLUDE',
                included_attributes=['tenant', 'email'],
            )
        ]
        entities = {
            'Order': {
                'gsi_mappings': [
                    {
                        'name': 'Idx',
                        'pk_template': ['{tenant}', '{region}'],
                        'sk_template': ['{date}'],
                    }
                ],
                'fields': [
                    {'name': 'tenant', 'type': 'string', 'required': True},
                    {'name': 'region', 'type': 'string', 'required': True},
                    {'name': 'date', 'type': 'string', 'required': True},
                    {'name': 'email', 'type': 'string', 'required': True},
                ],
            }
        }
        table_config = {'partition_key': 'pk'}
        errors = self.validator._validate_included_attributes_exist(
            gsi_list, entities, table_config, 'table'
        )
        # 'tenant' is a GSI key attribute — should be flagged as unnecessary
        assert any('tenant' in e.message and 'key attributes' in e.message for e in errors)


@pytest.mark.unit
class TestValidateGsiProjections(TestGSIValidator):
    """Test _validate_gsi_projections."""

    def test_valid_projections_pass(self):
        """ALL, KEYS_ONLY, INCLUDE (with attributes) all pass."""
        gsi_list_data = [
            {'name': 'Idx1', 'partition_key': 'pk', 'projection': 'ALL'},
            {'name': 'Idx2', 'partition_key': 'pk', 'projection': 'KEYS_ONLY'},
            {
                'name': 'Idx3',
                'partition_key': 'pk',
                'projection': 'INCLUDE',
                'included_attributes': ['field1'],
            },
        ]
        errors = self.validator._validate_gsi_projections(gsi_list_data, 'gsi_list')
        assert errors == []

    def test_invalid_projection_type_errors(self):
        """Invalid projection type produces error."""
        gsi_list_data = [{'name': 'Idx', 'partition_key': 'pk', 'projection': 'INVALID'}]
        errors = self.validator._validate_gsi_projections(gsi_list_data, 'gsi_list')
        assert len(errors) == 1
        assert "invalid projection 'INVALID'" in errors[0].message

    def test_include_missing_included_attributes_errors(self):
        """INCLUDE projection without included_attributes produces error."""
        gsi_list_data = [{'name': 'Idx', 'partition_key': 'pk', 'projection': 'INCLUDE'}]
        errors = self.validator._validate_gsi_projections(gsi_list_data, 'gsi_list')
        assert len(errors) == 1
        assert "missing 'included_attributes'" in errors[0].message

    def test_include_non_list_included_attributes_errors(self):
        """INCLUDE projection with non-list included_attributes produces error."""
        gsi_list_data = [
            {
                'name': 'Idx',
                'partition_key': 'pk',
                'projection': 'INCLUDE',
                'included_attributes': 'not_a_list',
            }
        ]
        errors = self.validator._validate_gsi_projections(gsi_list_data, 'gsi_list')
        assert len(errors) == 1
        assert 'must be an array' in errors[0].message

    def test_include_empty_included_attributes_errors(self):
        """INCLUDE projection with empty included_attributes produces error."""
        gsi_list_data = [
            {
                'name': 'Idx',
                'partition_key': 'pk',
                'projection': 'INCLUDE',
                'included_attributes': [],
            }
        ]
        errors = self.validator._validate_gsi_projections(gsi_list_data, 'gsi_list')
        assert len(errors) == 1
        # Empty list is falsy, so it hits the "missing" check before the len==0 check
        assert (
            "missing 'included_attributes'" in errors[0].message
            or 'cannot be empty' in errors[0].message
        )

    def test_non_include_with_included_attributes_errors(self):
        """Non-INCLUDE projection with included_attributes produces error."""
        gsi_list_data = [
            {
                'name': 'Idx',
                'partition_key': 'pk',
                'projection': 'ALL',
                'included_attributes': ['field1'],
            }
        ]
        errors = self.validator._validate_gsi_projections(gsi_list_data, 'gsi_list')
        assert len(errors) == 1
        assert 'only allowed for INCLUDE' in errors[0].message

    def test_no_projection_field_passes(self):
        """GSI without projection field produces no error."""
        gsi_list_data = [{'name': 'Idx', 'partition_key': 'pk'}]
        errors = self.validator._validate_gsi_projections(gsi_list_data, 'gsi_list')
        assert errors == []

    def test_non_dict_gsi_skipped(self):
        """Non-dict entries in gsi_list are skipped."""
        gsi_list_data = [
            'not_a_dict',
            {'name': 'Idx', 'partition_key': 'pk', 'projection': 'INVALID'},
        ]
        errors = self.validator._validate_gsi_projections(gsi_list_data, 'gsi_list')
        assert len(errors) == 1  # only the dict entry produces an error
