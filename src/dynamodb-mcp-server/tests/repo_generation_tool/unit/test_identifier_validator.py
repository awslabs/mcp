"""Unit tests for identifier validation (code-injection hardening).

These tests cover the ``identifier_validator`` module and verify end-to-end that schema names
carrying Python code are rejected before they can be interpolated into generated-code
identifier positions. This is the Python-repo-generator counterpart to the CDK generator's
identifier validation (GHSA-35jj-hwvm-792x).
"""

import json
import os
import pytest
import tempfile
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.identifier_validator import (
    is_safe_key_template,
    is_safe_string_literal_value,
    is_valid_python_identifier,
    validate_key_template,
    validate_python_identifier,
    validate_string_literal_value,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_validator import (
    SchemaValidator,
)


# The exact field-name payload from the vulnerability report: it closes the field annotation
# and injects a class-body statement block that would run at import time.
INJECTION_PAYLOAD = (
    "x = 0\n    import os\n    os.system('id > /tmp/PWNED_dynamodb_poc 2>&1')\n    y"
)


@pytest.mark.unit
class TestIsValidPythonIdentifier:
    """Unit tests for the is_valid_python_identifier predicate."""

    @pytest.mark.parametrize(
        'name',
        [
            'user_id',
            'UserProfile',
            'order',
            '_private',
            'x2',
            'camelCase',
            'ALL_CAPS',
            'ü',  # non-ASCII identifiers are valid Python identifiers
            # A reserved word as a *substring* of one longer identifier is fine: iskeyword()
            # is a whole-string test, and these are each a single legal identifier token.
            'classroom',
            'classType',
            'import_path',
            'return_value',
            'match_id',
            'lambda_fn',
            'defer',
        ],
    )
    def test_accepts_valid_identifiers(self, name):
        """Ordinary identifiers are accepted, including ones that merely contain a keyword."""
        assert is_valid_python_identifier(name) is True

    @pytest.mark.parametrize(
        'name',
        [
            INJECTION_PAYLOAD,
            'x = 0; import os',  # inline statement injection
            'class Foo',  # keyword + more: a keyword embedded in a code fragment (not one token)
            'return 0',  # keyword followed by other syntax
            'import os',  # keyword + space + name
            'x\n',  # trailing newline bypass (str.isidentifier is already False, but explicit)
            'has space',
            'a-b',  # hyphen is not an identifier char
            'a.b',  # attribute-style injection
            '2x',  # cannot start with a digit
            '',  # empty
            'class',  # hard keyword
            'def',
            'import',
            'return',
            'lambda',
            'None',
            'True',
            'match',  # soft keyword
            'case',  # soft keyword
            '_',  # soft keyword / wildcard
        ],
    )
    def test_rejects_injection_and_reserved(self, name):
        """Names that are not plain, non-reserved identifiers are rejected."""
        assert is_valid_python_identifier(name) is False

    @pytest.mark.parametrize('name', [None, 123, 1.5, True, ['x'], {'x': 1}, b'bytes'])
    def test_rejects_non_strings(self, name):
        """Non-string inputs are rejected rather than raising."""
        assert is_valid_python_identifier(name) is False

    def test_trailing_newline_is_rejected(self):
        """A valid identifier with a trailing newline is rejected (fullmatch semantics).

        This mirrors the CDK generator comment that validation must not accept a trailing
        newline (re.match / '$' would), which would otherwise smuggle a newline into an
        identifier position.
        """
        assert is_valid_python_identifier('user_id') is True
        assert is_valid_python_identifier('user_id\n') is False


@pytest.mark.unit
class TestValidatePythonIdentifier:
    """Unit tests for the validate_python_identifier error-list helper."""

    def test_valid_name_returns_no_errors(self):
        """A valid identifier produces an empty error list."""
        assert validate_python_identifier('user_id', 'path.to.name', 'Field name') == []

    def test_invalid_name_returns_error_with_context(self):
        """An injection payload produces one error carrying the field path and kind."""
        errors = validate_python_identifier(INJECTION_PAYLOAD, 'tables[0].x.name', 'Field name')
        assert len(errors) == 1
        err = errors[0]
        assert err.path == 'tables[0].x.name'
        assert 'Field name' in err.message
        assert 'not a valid identifier' in err.message
        assert err.severity == 'error'

    def test_non_string_name_reports_type_message(self):
        """A non-string name produces a type-oriented error message."""
        errors = validate_python_identifier(123, 'p', 'Parameter name')
        assert len(errors) == 1
        assert 'Parameter name must be a string' in errors[0].message


def _validate_schema_dict(schema_dict):
    """Validate an in-memory schema dict through the full SchemaValidator path."""
    validator = SchemaValidator()
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(schema_dict, f)
        temp_file = f.name
    try:
        return validator.validate_schema_file(temp_file)
    finally:
        os.unlink(temp_file)


def _base_entity(fields):
    return {
        'entity_type': 'TEST',
        'pk_template': 'USER#{user_id}',
        'fields': fields,
        'access_patterns': [],
    }


@pytest.mark.unit
class TestInjectionRejectedEndToEnd:
    """End-to-end: malicious names are rejected by SchemaValidator; valid names pass."""

    def _schema_with_entities(self, entities):
        return {
            'tables': [
                {
                    'table_config': {'table_name': 'Users', 'partition_key': 'pk'},
                    'entities': entities,
                }
            ]
        }

    def test_malicious_field_name_rejected(self):
        """The reported field-name payload fails validation."""
        schema = self._schema_with_entities(
            {
                'User': _base_entity(
                    [
                        {'name': 'user_id', 'type': 'string', 'required': True},
                        {'name': INJECTION_PAYLOAD, 'type': 'string', 'required': True},
                    ]
                )
            }
        )
        result = _validate_schema_dict(schema)
        assert result.is_valid is False
        assert any(
            'not a valid identifier' in e.message and 'Field name' in e.message
            for e in result.errors
        )

    def test_malicious_entity_name_rejected(self):
        """An entity name carrying Python code fails validation."""
        schema = self._schema_with_entities(
            {
                "User(ConfigurableEntity):\n    import os\n    os.system('id')\nclass Z": _base_entity(
                    [{'name': 'user_id', 'type': 'string', 'required': True}]
                )
            }
        )
        result = _validate_schema_dict(schema)
        assert result.is_valid is False
        assert any(
            'not a valid identifier' in e.message and 'Entity name' in e.message
            for e in result.errors
        )

    def test_malicious_parameter_name_rejected(self):
        """A parameter name carrying Python code fails validation."""
        entity = _base_entity([{'name': 'user_id', 'type': 'string', 'required': True}])
        entity['access_patterns'] = [
            {
                'pattern_id': 1,
                'name': 'get_user',
                'description': 'Get a user',
                'operation': 'GetItem',
                'return_type': 'single_entity',
                'parameters': [
                    {'name': "user_id): import os; os.system('id')  #", 'type': 'string'}
                ],
            }
        ]
        schema = self._schema_with_entities({'User': entity})
        result = _validate_schema_dict(schema)
        assert result.is_valid is False
        assert any(
            'not a valid identifier' in e.message and 'Parameter name' in e.message
            for e in result.errors
        )

    def test_keyword_names_rejected(self):
        """A field named like a Python keyword is rejected."""
        schema = self._schema_with_entities(
            {
                'User': _base_entity(
                    [
                        {'name': 'user_id', 'type': 'string', 'required': True},
                        {'name': 'class', 'type': 'string', 'required': True},
                    ]
                )
            }
        )
        result = _validate_schema_dict(schema)
        assert result.is_valid is False
        assert any('Field name' in e.message for e in result.errors)

    def test_valid_names_still_pass(self):
        """A schema with ordinary identifiers validates successfully (no false positives)."""
        entity = _base_entity(
            [
                {'name': 'user_id', 'type': 'string', 'required': True},
                {'name': 'display_name', 'type': 'string', 'required': False},
            ]
        )
        entity['access_patterns'] = [
            {
                'pattern_id': 1,
                'name': 'get_user',
                'description': 'Get a user by id',
                'operation': 'GetItem',
                'return_type': 'single_entity',
                'parameters': [{'name': 'user_id', 'type': 'string'}],
            }
        ]
        schema = self._schema_with_entities({'User': entity})
        result = _validate_schema_dict(schema)
        assert result.is_valid is True
        assert len(result.errors) == 0


@pytest.mark.unit
class TestIsSafeStringLiteralValue:
    """Unit tests for the is_safe_string_literal_value predicate (entity_type, table_name)."""

    @pytest.mark.parametrize(
        'value', ['USER', 'Users', 'ORDER_ITEM', 'tenant.table-name', 'prefix#SUFFIX', '']
    )
    def test_accepts_plain_values(self, value):
        """Ordinary string values with no break-out characters are accepted."""
        assert is_safe_string_literal_value(value) is True

    @pytest.mark.parametrize(
        'value',
        [
            'USER"; import os; x = "',  # quote break-out
            'USER"',
            'a\\b',  # backslash
            'line1\nline2',  # newline
            'carriage\rreturn',  # carriage return
        ],
    )
    def test_rejects_breakout_values(self, value):
        """Values containing quote, backslash, or newline are rejected."""
        assert is_safe_string_literal_value(value) is False

    @pytest.mark.parametrize('value', [None, 123, True, ['x'], {'x': 1}])
    def test_rejects_non_strings(self, value):
        """Non-string values are rejected rather than raising."""
        assert is_safe_string_literal_value(value) is False


@pytest.mark.unit
class TestIsSafeKeyTemplate:
    """Unit tests for the is_safe_key_template predicate (pk/sk/GSI templates)."""

    @pytest.mark.parametrize(
        'template',
        [
            'USER#{user_id}',
            'ORDER#{order_id}#ITEM#{item_id}',
            'PROFILE',  # static, no placeholders
            '{user_id}',
            'SCORE#{score:05d}',  # format spec
            'DATE#{created_at:%Y-%m-%d}',
        ],
    )
    def test_accepts_valid_templates(self, template):
        """Ordinary key templates with only {field} placeholders are accepted."""
        assert is_safe_key_template(template) is True

    @pytest.mark.parametrize(
        'template',
        [
            "{__import__('os').system('id')}",  # f-string expression injection
            'USER#{user_id.__class__}',  # attribute access
            'USER#{1+1}',  # expression
            'USER#{user_id}"; import os; "',  # quote break-out
            'USER#{user_id}\nimport os',  # newline
            'USER#{',  # unmatched brace
            'USER#}',  # stray closing brace
            'USER#{ user_id }',  # spaces -> not a bare {field}
        ],
    )
    def test_rejects_dangerous_templates(self, template):
        """Templates with break-out chars or non-placeholder brace expressions are rejected."""
        assert is_safe_key_template(template) is False

    @pytest.mark.parametrize('template', [None, 123, ['USER#{user_id}']])
    def test_rejects_non_strings(self, template):
        """Non-string templates are rejected rather than raising."""
        assert is_safe_key_template(template) is False


@pytest.mark.unit
class TestStringAndTemplateHelpers:
    """Unit tests for the string-literal and key-template error-list helpers."""

    def test_valid_string_literal_returns_no_errors(self):
        """A safe string value produces an empty error list."""
        assert validate_string_literal_value('USER', 'p.entity_type', 'entity_type') == []

    def test_invalid_string_literal_returns_error(self):
        """A break-out value produces one error naming the field."""
        errors = validate_string_literal_value('USER"', 'p.entity_type', 'entity_type')
        assert len(errors) == 1
        assert 'entity_type' in errors[0].message
        assert errors[0].severity == 'error'

    def test_valid_template_returns_no_errors(self):
        """A safe key template produces an empty error list."""
        assert validate_key_template('USER#{user_id}', 'p.pk_template', 'pk_template') == []

    def test_invalid_template_returns_error(self):
        """A dangerous template produces one error naming the field."""
        errors = validate_key_template(
            "{__import__('os').system('id')}", 'p.pk_template', 'pk_template'
        )
        assert len(errors) == 1
        assert 'pk_template' in errors[0].message


@pytest.mark.unit
class TestStringAndGsiInjectionRejectedEndToEnd:
    """End-to-end: string-literal, f-string, GSI-name, and pattern-name injection is rejected."""

    def _schema(
        self,
        *,
        entity_type='USER',
        pk_template='USER#{user_id}',
        table_name='Users',
        pattern_name=None,
        gsi_name=None,
    ):
        entity = {
            'entity_type': entity_type,
            'pk_template': pk_template,
            'fields': [{'name': 'user_id', 'type': 'string', 'required': True}],
            'access_patterns': [],
        }
        if pattern_name is not None:
            entity['access_patterns'] = [
                {
                    'pattern_id': 1,
                    'name': pattern_name,
                    'description': 'd',
                    'operation': 'GetItem',
                    'return_type': 'single_entity',
                    'parameters': [{'name': 'user_id', 'type': 'string'}],
                }
            ]
        table = {
            'table_config': {'table_name': table_name, 'partition_key': 'pk'},
            'entities': {'User': entity},
        }
        if gsi_name is not None:
            table['gsi_list'] = [{'name': gsi_name, 'partition_key': 'user_id'}]
            entity['gsi_mappings'] = [{'name': gsi_name, 'pk_template': 'GSI#{user_id}'}]
        return {'tables': [table]}

    def _validate(self, schema):
        validator = SchemaValidator()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(schema, f)
            temp_file = f.name
        try:
            return validator.validate_schema_file(temp_file)
        finally:
            os.unlink(temp_file)

    def test_entity_type_quote_breakout_rejected(self):
        """An entity_type that breaks out of its string literal is rejected."""
        result = self._validate(self._schema(entity_type='USER"; import os; x = "'))
        assert result.is_valid is False
        assert any('entity_type' in e.message for e in result.errors)

    def test_table_name_quote_breakout_rejected(self):
        """A table_name that breaks out of its string literal is rejected."""
        result = self._validate(self._schema(table_name='Users"; import os; x = "'))
        assert result.is_valid is False
        assert any('table_name' in e.message for e in result.errors)

    def test_pk_template_fstring_expression_rejected(self):
        """A pk_template with an arbitrary f-string brace expression is rejected."""
        result = self._validate(self._schema(pk_template="{__import__('os').system('id')}"))
        assert result.is_valid is False
        assert any('pk_template' in e.message for e in result.errors)

    def test_pattern_name_identifier_injection_rejected(self):
        """An access-pattern name carrying code (emitted as a method name) is rejected."""
        result = self._validate(
            self._schema(pattern_name="get_user(self): import os; os.system('id')  #")
        )
        assert result.is_valid is False
        assert any('Pattern name' in e.message for e in result.errors)

    def test_gsi_name_identifier_injection_rejected(self):
        """A GSI name carrying code (feeds the generated method name) is rejected."""
        result = self._validate(
            self._schema(gsi_name="x(cls):\n    import os\n    os.system('id')\n    def y")
        )
        assert result.is_valid is False
        assert any('GSI name' in e.message for e in result.errors)

    def test_valid_schema_with_gsi_and_pattern_passes(self):
        """A schema with ordinary values, a GSI, and a pattern validates successfully."""
        result = self._validate(
            self._schema(pattern_name='get_user_by_id', gsi_name='UsersByEmail')
        )
        assert result.is_valid is True
        assert len(result.errors) == 0
