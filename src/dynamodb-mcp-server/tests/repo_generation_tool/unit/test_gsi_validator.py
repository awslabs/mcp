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
