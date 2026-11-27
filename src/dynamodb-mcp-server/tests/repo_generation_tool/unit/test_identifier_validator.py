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
    validate_comment_text,
    validate_description,
    validate_key_template,
    validate_python_identifier,
    validate_string_literal_value,
    validate_table_name,
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

    def test_template_breakout_char_message(self):
        """A template with a break-out character reports the disallowed-characters message."""
        errors = validate_key_template('USER#{user_id}"; x', 'p.pk_template', 'pk_template')
        assert len(errors) == 1
        assert 'disallowed characters' in errors[0].message

    def test_template_non_string_message(self):
        """A non-string template reports a must-be-a-string message."""
        errors = validate_key_template(123, 'p.pk_template', 'pk_template')
        assert len(errors) == 1
        assert 'pk_template must be a string' in errors[0].message

    def test_string_literal_non_string_message(self):
        """A non-string string-literal value reports a must-be-a-string message."""
        errors = validate_string_literal_value(123, 'p.entity_type', 'entity_type')
        assert len(errors) == 1
        assert 'entity_type must be a string' in errors[0].message


@pytest.mark.unit
class TestStringAndGsiInjectionRejectedEndToEnd:
    """End-to-end: string-literal, f-string, GSI-name, and pattern-name injection is rejected."""

    def _schema(
        self,
        *,
        entity_type='USER',
        pk_template='USER#{user_id}',
        table_name='Users',
        partition_key='pk',
        sort_key=None,
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
            'table_config': {'table_name': table_name, 'partition_key': partition_key},
            'entities': {'User': entity},
        }
        if sort_key is not None:
            table['table_config']['sort_key'] = sort_key
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

    def test_partition_key_quote_breakout_rejected(self):
        """A partition_key that breaks out of the super().__init__ string literal is rejected."""
        result = self._validate(self._schema(partition_key='pk"; import os; x = "'))
        assert result.is_valid is False
        assert any('partition_key' in e.message for e in result.errors)

    def test_sort_key_quote_breakout_rejected(self):
        """A sort_key that breaks out of the super().__init__ string literal is rejected."""
        result = self._validate(self._schema(sort_key='sk"; import os; x = "'))
        assert result.is_valid is False
        assert any('sort_key' in e.message for e in result.errors)

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


DESCRIPTION_PAYLOADS = [
    pytest.param('x """ + __import__("os").system("id") + """', id='triple-quote'),
    pytest.param("{__import__('os').system('id')}", id='fstring-expression'),
    pytest.param('line one\nimport os', id='newline'),
    pytest.param('say "hi"', id='double-quote'),
    pytest.param('back\\slash', id='backslash'),
    pytest.param('a # comment', id='hash'),
    pytest.param('a}b', id='close-brace'),
    pytest.param('a\rb', id='carriage-return'),
    pytest.param('a\x00b', id='nul-byte'),
    pytest.param('a\x0bb', id='vertical-tab'),
    pytest.param('a\x7fb', id='delete-char'),
    pytest.param('a\ud800b', id='lone-surrogate'),
    pytest.param('a\u0085b', id='next-line'),
    pytest.param('a\u2028b', id='line-separator'),
    pytest.param('a\u2029b', id='paragraph-separator'),
    pytest.param('evil \u202e txt', id='bidi-override'),
    pytest.param('a\u2066b', id='bidi-isolate'),
    pytest.param('a\u200fb', id='right-to-left-mark'),
]


@pytest.mark.unit
class TestValidateDescription:
    """Unit tests for validate_description."""

    @pytest.mark.parametrize(
        'value',
        [
            'Get user by ID',
            "Get user's profile",
            'Query orders (newest first) - up to 10, e.g. a/b: c; d!',
            '',
        ],
    )
    def test_accepts_plain_text(self, value):
        """Ordinary descriptions pass."""
        assert validate_description(value, 'p', 'Pattern description') == []

    @pytest.mark.parametrize('value', DESCRIPTION_PAYLOADS)
    def test_rejects_payloads(self, value):
        """Each break-out character is rejected."""
        errors = validate_description(value, 'p.description', 'Pattern description')
        assert len(errors) == 1
        assert errors[0].path == 'p.description'
        assert 'Pattern description contains disallowed characters' in errors[0].message

    @pytest.mark.parametrize('value', [None, 5, ['a']])
    def test_rejects_non_string(self, value):
        """Non-string values are rejected."""
        errors = validate_description(value, 'p', 'Parameter description')
        assert len(errors) == 1
        assert 'must be a string' in errors[0].message


@pytest.mark.unit
class TestDescriptionInjectionRejectedEndToEnd:
    """End-to-end: malicious descriptions are rejected by SchemaValidator."""

    def _schema(self, pattern_description='d', param_description=None):
        param = {'name': 'user_id', 'type': 'string'}
        if param_description is not None:
            param['description'] = param_description
        return {
            'tables': [
                {
                    'table_config': {'table_name': 'Users', 'partition_key': 'pk'},
                    'entities': {
                        'User': {
                            'entity_type': 'USER',
                            'pk_template': 'USER#{user_id}',
                            'fields': [{'name': 'user_id', 'type': 'string', 'required': True}],
                            'access_patterns': [
                                {
                                    'pattern_id': 1,
                                    'name': 'get_user',
                                    'description': pattern_description,
                                    'operation': 'GetItem',
                                    'return_type': 'single_entity',
                                    'parameters': [param],
                                }
                            ],
                        }
                    },
                }
            ]
        }

    def test_clean_descriptions_pass(self):
        """Plain descriptions on the pattern and parameter are accepted."""
        result = _validate_schema_dict(self._schema('Get user by ID', 'The user id'))
        assert result.is_valid is True, result.errors

    @pytest.mark.parametrize('payload', DESCRIPTION_PAYLOADS)
    def test_pattern_description_rejected(self, payload):
        """A malicious pattern description fails validation."""
        result = _validate_schema_dict(self._schema(pattern_description=payload))
        assert result.is_valid is False
        assert any(
            'Pattern description' in e.message and e.path.endswith('.description')
            for e in result.errors
        )

    @pytest.mark.parametrize('payload', DESCRIPTION_PAYLOADS)
    def test_parameter_description_rejected(self, payload):
        """A malicious parameter description fails validation."""
        result = _validate_schema_dict(self._schema(param_description=payload))
        assert result.is_valid is False
        assert any(
            'Parameter description' in e.message and '.parameters[0].description' in e.path
            for e in result.errors
        )


@pytest.mark.unit
def test_nul_description_is_rejected_so_generated_code_stays_parseable():
    """A NUL in a description is rejected; it would make the generated Python unparseable."""
    result = _validate_schema_dict(
        TestDescriptionInjectionRejectedEndToEnd()._schema(pattern_description='bad\x00nul')
    )
    assert result.is_valid is False
    assert any('Pattern description' in e.message for e in result.errors)


@pytest.mark.unit
@pytest.mark.parametrize('payload', ['a\ud800b', 'evil \u202e txt', 'a\x00b'])
def test_rejected_description_never_reaches_generated_files(payload, tmp_path):
    """The CLI stops on these descriptions and writes no output; accepted ones always parse."""
    import ast
    from awslabs.dynamodb_mcp_server.repo_generation_tool.codegen import main
    from unittest.mock import patch

    schema = TestDescriptionInjectionRejectedEndToEnd()._schema(pattern_description=payload)
    schema_file = tmp_path / 'schema.json'
    schema_file.write_text(json.dumps(schema))
    out = tmp_path / 'out'
    with patch(
        'sys.argv', ['codegen', '--schema', str(schema_file), '--output', str(out), '--no-lint']
    ):
        exit_code = main()
    assert exit_code != 0
    assert not out.exists() or not list(out.glob('*.py'))
    for py in out.glob('*.py') if out.exists() else []:
        ast.parse(py.read_text(encoding='utf-8'))


# --- One-pass audit: every other schema value that reaches generated code -----------------------

_AUDIT_FIELDS = [
    # (id, fixture, path to the value, payloads that must be rejected)
    (
        'cross-table-pattern-name',
        'USER_REGISTRATION_SCHEMA',
        ('cross_table_access_patterns', 0, 'name'),
        ['x(self):\n        ZZEXEC = 1\n    def y', 'a b', 'a"b'],
    ),
    (
        'parameter-default',
        'FOOD_DELIVERY_SCHEMA',
        ('tables', 0, 'entities', 'Delivery', 'access_patterns', 1, 'parameters', 1, 'default'),
        ['a", ZZEXEC=__import__("os").getcwd(), zz="', 'a\\', 'a\nb', 'a\x00b'],
    ),
    (
        'filter-condition-param',
        'FOOD_DELIVERY_SCHEMA',
        (
            'tables',
            0,
            'entities',
            'Delivery',
            'access_patterns',
            1,
            'filter_expression',
            'conditions',
            0,
            'param',
        ),
        ['a\n        ZZEXEC = 1\n        #', 'a b', 'a"b'],
    ),
    (
        'filter-condition-params-item',
        'FOOD_DELIVERY_SCHEMA',
        (
            'tables',
            0,
            'entities',
            'Delivery',
            'access_patterns',
            3,
            'filter_expression',
            'conditions',
            0,
            'params',
            0,
        ),
        ['a\n        ZZEXEC = 1\n        #', 'a b', 'a"b'],
    ),
    (
        'entity-involved-condition',
        'USER_REGISTRATION_SCHEMA',
        ('cross_table_access_patterns', 0, 'entities_involved', 0, 'condition'),
        ['a\n        ZZEXEC = 1\n        #', 'a\rb', 'a\u2028b', 'a\x00b'],
    ),
    (
        'gsi-list-partition-key',
        'DEALS_SCHEMA',
        ('tables', 0, 'gsi_list', 0, 'partition_key'),
        ['a\n        ZZEXEC = 1\n        #', 'a"b', 'a\\b', 'a\x00b'],
    ),
    (
        'gsi-list-sort-key',
        'DEALS_SCHEMA',
        ('tables', 0, 'gsi_list', 0, 'sort_key'),
        ['a\n        ZZEXEC = 1\n        #', 'a"b', 'a\\b', 'a\x00b'],
    ),
]


def _load_fixture(name):
    from tests.repo_generation_tool import conftest

    with open(getattr(conftest, name)) as f:
        return json.load(f)


def _set_path(obj, path, value):
    for key in path[:-1]:
        obj = obj[key]
    obj[path[-1]] = value


@pytest.mark.unit
class TestRemainingCodeSinksRejectedEndToEnd:
    """Each schema value that reaches generated code is validated, not only descriptions."""

    @pytest.mark.parametrize('field_id,fixture,path,payloads', _AUDIT_FIELDS)
    def test_clean_fixture_is_valid(self, field_id, fixture, path, payloads):
        """The unmodified valid fixtures still validate."""
        assert _validate_schema_dict(_load_fixture(fixture)).is_valid is True

    @pytest.mark.parametrize(
        'field_id,fixture,path,payload',
        [(i, f, p, pay) for i, f, p, payloads in _AUDIT_FIELDS for pay in payloads],
    )
    def test_malicious_value_rejected(self, field_id, fixture, path, payload):
        """A code-injection payload in the field fails validation at the field's path."""
        schema = _load_fixture(fixture)
        _set_path(schema, path, payload)
        result = _validate_schema_dict(schema)
        assert result.is_valid is False
        last = path[-1]
        suffix = f'[{last}]' if isinstance(last, int) else f'.{last}'
        assert any(e.path.endswith(suffix) for e in result.errors), [e.path for e in result.errors]

    def test_list_form_gsi_keys_are_checked(self):
        """Multi-attribute (list) GSI keys are checked per element."""
        schema = _load_fixture('DEALS_SCHEMA')
        gsi = schema['tables'][0]['gsi_list'][0]
        gsi['partition_key'] = ['ok_attr', 'a\nZZEXEC = 1\n#']
        result = _validate_schema_dict(schema)
        assert result.is_valid is False
        assert any('partition_key[1]' in e.path for e in result.errors)

    def test_non_string_defaults_are_unchanged(self):
        """Numeric and boolean defaults are not string literals and are not rejected."""
        schema = _load_fixture('FOOD_DELIVERY_SCHEMA')
        params = schema['tables'][0]['entities']['Delivery']['access_patterns'][1]['parameters']
        params[1]['default'] = 'CANCELLED'
        assert _validate_schema_dict(schema).is_valid is True


@pytest.mark.unit
class TestValidateCommentText:
    """Unit tests for validate_comment_text."""

    @pytest.mark.parametrize(
        'value',
        ['attribute_not_exists(pk)', 'a #b {c} "d" \'e\' \\ f', 'tab\there', 'caf\u00e9 \u4e2d'],
    )
    def test_accepts_single_line_text(self, value):
        """Quotes, braces, # and backslash are harmless in a one-line comment."""
        assert validate_comment_text(value, 'p', 'Condition') == []

    @pytest.mark.parametrize(
        'value',
        ['a\nb', 'a\rb', 'a\x00b', 'a\u2028b', 'a\u0085b', 'a\u202eb', 'a\ud800b'],
    )
    def test_rejects_line_breaks_and_unsafe_characters(self, value):
        """Anything that starts a new line or corrupts the output is rejected."""
        errors = validate_comment_text(value, 'p.condition', 'Condition')
        assert len(errors) == 1
        assert errors[0].path == 'p.condition'

    @pytest.mark.parametrize('value', [None, 3, ['a']])
    def test_rejects_non_string(self, value):
        """Non-string values are rejected."""
        errors = validate_comment_text(value, 'p', 'Condition')
        assert 'must be a string' in errors[0].message


@pytest.mark.unit
class TestStringLiteralControlCharacters:
    """Existing string-literal and key-template guards also reject control characters."""

    @pytest.mark.parametrize('value', ['a\x00b', 'a\x7fb', 'a\u2028b', 'a\u202eb', 'a\ud800b'])
    def test_string_literal_rejects_control_characters(self, value):
        """A control character would make the generated source unparseable or misleading."""
        assert is_safe_string_literal_value(value) is False
        assert is_safe_key_template('USER#' + value) is False

    def test_string_literal_still_accepts_normal_text(self):
        """Normal names, including non-ASCII text and tabs, still pass."""
        assert is_safe_string_literal_value('Users caf\u00e9\tone') is True
        assert is_safe_key_template('USER#{user_id}') is True


@pytest.mark.unit
class TestNonFiniteAndUsageDataOutputStaysParseable:
    """Values that would make the generated files unparseable are rejected or escaped."""

    @pytest.mark.parametrize('literal', ['NaN', 'Infinity', '-Infinity'])
    def test_non_finite_parameter_default_rejected(self, literal, tmp_path):
        """JSON NaN/Infinity defaults would be written as bare names and fail at import."""
        from tests.repo_generation_tool import conftest

        text = (
            open(conftest.FOOD_DELIVERY_SCHEMA)
            .read()
            .replace('"default": "CANCELLED"', f'"default": {literal}', 1)
        )
        schema_file = tmp_path / 's.json'
        schema_file.write_text(text)
        result = SchemaValidator().validate_schema_file(str(schema_file))
        assert result.is_valid is False
        assert any(
            'Parameter default must be a finite number' in e.message
            and e.path.endswith('.default')
            for e in result.errors
        )

    @pytest.mark.parametrize('default', [1.5, 3, True, 'CANCELLED'])
    def test_finite_and_other_defaults_still_accepted(self, default):
        """Ordinary numbers, booleans and strings are not affected."""
        schema = _load_fixture('FOOD_DELIVERY_SCHEMA')
        params = schema['tables'][0]['entities']['Delivery']['access_patterns'][1]['parameters']
        params[1]['default'] = default
        assert _validate_schema_dict(schema).is_valid is True

    @pytest.mark.parametrize(
        'value',
        [
            'a\nb',
            'a\rb',
            'a\tb',
            'a\x00b',
            'a\x7fb',
            'a\u0085b',
            'a\u2028b',
            'a\ud800b',
            'say "hi" \\ done',
            'a"\nZZEXEC = 1\n#',
            "caf\u00e9 \u4e2d\u6587 it's",
        ],
    )
    def test_usage_data_string_round_trips_through_generated_source(self, value):
        """The escaped literal parses as one string and evaluates back to the original value."""
        import ast
        from awslabs.dynamodb_mcp_server.repo_generation_tool.languages.python.usage_data_formatter import (
            PythonUsageDataFormatter,
        )

        fmt = PythonUsageDataFormatter()
        for source in (
            fmt.format_value(value, 'string'),
            fmt.format_value([value], 'array'),
            fmt.format_value({'k': value}, 'object'),
        ):
            tree = ast.parse(f'x = {source}')
            assert len(tree.body) == 1
            source.encode('utf-8')  # must be writable to a UTF-8 file
            assert ast.literal_eval(source) in (value, [value], {'k': value})


@pytest.mark.unit
class TestValidateTableName:
    """Unit tests for validate_table_name (placeholder strings only)."""

    @pytest.mark.parametrize(
        'value', ['Users', 'user-table_1.v2', 'ELearningPlatform', 'a' * 255, 'T1']
    )
    def test_accepts_dynamodb_table_names(self, value):
        """Names made of the characters DynamoDB allows pass."""
        assert validate_table_name(value, 'p.table_name') == []

    @pytest.mark.parametrize(
        'value',
        [
            '{PLACEHOLDER}',
            'a{b}c',
            'a}b',
            'a{b',
            'a"b',
            "a'b",
            'a b',
            'a\nb',
            'a\\b',
            'a#b',
            'a(b)',
            '',
            'caf\u00e9',
        ],
    )
    def test_rejects_other_characters(self, value):
        """Braces, quotes, spaces, line breaks and other characters are rejected."""
        errors = validate_table_name(value, 'p.table_name')
        assert len(errors) == 1
        assert errors[0].path == 'p.table_name'

    @pytest.mark.parametrize('value', [None, 5, ['Users']])
    def test_rejects_non_string(self, value):
        """Non-string values are rejected."""
        errors = validate_table_name(value, 'p.table_name')
        assert 'must be a string' in errors[0].message

    @pytest.mark.parametrize('value', ['{PLACEHOLDER}', 'Users{x}', 'a b'])
    def test_schema_validator_rejects_bad_table_name(self, value):
        """SchemaValidator reports the bad table name at its field path."""
        schema = _load_fixture('USER_REGISTRATION_SCHEMA')
        schema['tables'][0]['table_config']['table_name'] = value
        result = _validate_schema_dict(schema)
        assert result.is_valid is False
        assert any(e.path.endswith('.table_config.table_name') for e in result.errors)

    def test_schema_validator_keeps_good_table_name(self):
        """A normal table name still validates."""
        schema = _load_fixture('USER_REGISTRATION_SCHEMA')
        assert _validate_schema_dict(schema).is_valid is True
