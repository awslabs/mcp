# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

r"""Validation for schema names that reach generated-code identifier positions.

The code generator renders Jinja2 templates with autoescape disabled (appropriate for
generating source code, not HTML). Several schema-supplied names are interpolated into raw
Python identifier positions in the generated code, where escaping cannot be applied:

- entity names   -> ``class {{ entity_name }}(ConfigurableEntity):`` and the
                    ``{{ entity_name.upper() }}_CONFIG`` module-level constant
- field names    -> ``{{ field.name }}: {{ map_field_type(field) }}`` in the entity body
- parameter names-> lambda argument names, ``self.{{ ... }}`` and ``entity.{{ ... }}``
                    attribute accesses in the generated key builders

A name in these positions is not data inside a quoted string; it becomes part of the Python
grammar. A name that contains Python syntax (for example ``x = 0\\n    import os\\n    ...``)
is written straight into the class body and executes when the generated module is imported or
run. This is the same class of issue as the CDK generator's, which was addressed by rejecting
names that are not valid identifiers (see ``cdk_generator/models.py`` ``_validate_ddb_name``).

Because an identifier position cannot be escaped, these names must be *rejected* rather than
sanitized. A valid name here is one that Python itself accepts as an identifier and that is
not a (hard or soft) keyword, so it can only ever be an ordinary name token in the generated
source.

The same autoescape-disabled, no-escaping-filter setup also interpolates schema values into
quoted string-literal and f-string positions:

- ``entity_type`` / ``table_name`` -> quoted string literals such as
  ``entity_type="{{ entity_config.entity_type }}"`` and the repository ``table_name`` default.
  A value containing ``"``/``\``/newline can close the string and append code.
- ``pk_template`` / ``sk_template`` / GSI templates -> f-strings such as
  ``f"{{ pk_template | substitute_params(...) }}"``. On top of a quote break-out, an f-string
  evaluates ``{expr}``, so a brace expression that is not a known ``{field}`` placeholder (for
  example ``{__import__('os').system('...')}``) executes when the generated builder runs.

GSI mapping / index names reach identifier positions too: ``safe_name`` is
``to_snake_case(gsi_name)``, which only swaps case and hyphens, and is emitted as the method
name ``def build_gsi_pk_for_lookup_{{ safe_name }}(...)``. These names are validated as
identifiers like entity/field/parameter names.

All of these are rejected rather than escaped: string-literal values must contain no break-out
characters, and key templates must additionally contain only well-formed ``{field}``
placeholders.
"""

import keyword
import re


# Soft keywords (``match``, ``case``, ``type``, ``_``) satisfy ``str.isidentifier()`` and are
# not reported by ``keyword.iskeyword()``, but they are reserved in specific grammar positions
# and must not be emitted as entity/field/parameter identifiers. ``keyword.softkwlist`` is
# available on the supported runtimes; fall back to a literal list defensively.
_SOFT_KEYWORDS = frozenset(getattr(keyword, 'softkwlist', ['_', 'case', 'match', 'type']))

# Characters that let a value break out of the string literal / f-string it is rendered into.
_STRING_BREAKOUT_CHARS = ('"', '\\', '\n', '\r')

# A single well-formed key-template placeholder: ``{field}`` or ``{field:format}`` where the
# field is a plain identifier-like token and the format spec contains no braces.
_TEMPLATE_PLACEHOLDER = re.compile(r'\{(\w+)(?::[^{}]*)?\}')


def is_valid_python_identifier(name: object) -> bool:
    """Return True if ``name`` is safe to emit in a generated-code identifier position.

    A safe name is a ``str`` that Python accepts as an identifier (``str.isidentifier()``) and
    that is not a reserved word (neither a hard keyword via ``keyword.iskeyword()`` nor a soft
    keyword). Such a name can only be lexed as an ordinary identifier token, so it cannot carry
    statements, operators, or other syntax into the generated source.

    Args:
        name: The candidate name. Any non-string value is rejected.

    Returns:
        True if the name is a valid, non-reserved Python identifier; False otherwise.
    """
    if not isinstance(name, str):
        return False
    if not name.isidentifier():
        return False
    if keyword.iskeyword(name) or name in _SOFT_KEYWORDS:
        return False
    return True


def is_safe_string_literal_value(value: object) -> bool:
    """Return True if ``value`` is safe to emit inside a quoted string literal in generated code.

    Values such as ``entity_type`` and ``table_name`` are interpolated into quoted string
    positions with autoescape disabled and no escaping filter. A value containing a quote,
    backslash, or newline can close the string early and append arbitrary code, so such values
    are rejected.

    Args:
        value: The candidate value. Any non-string value is rejected.

    Returns:
        True if the value is a string free of string break-out characters; False otherwise.
    """
    if not isinstance(value, str):
        return False
    return not any(ch in value for ch in _STRING_BREAKOUT_CHARS)


def is_safe_key_template(template: object) -> bool:
    """Return True if ``template`` is safe to emit into an f-string key builder.

    Key templates (``pk_template``, ``sk_template``, GSI templates) are literal text with
    ``{field}`` placeholders and are rendered into f-strings. Two things must hold: the template
    must not contain string break-out characters, and every ``{...}`` must be a well-formed field
    placeholder. The latter matters because an f-string evaluates ``{expr}``: an arbitrary brace
    expression (for example ``{__import__('os').system('...')}``) would execute when the builder
    runs. Validating that all braces are simple placeholders prevents expression injection while
    still allowing ordinary templates like ``USER#{user_id}``.

    Args:
        template: The candidate template. Any non-string value is rejected.

    Returns:
        True if the template is a string with no break-out characters and only well-formed
        ``{field}`` placeholders; False otherwise.
    """
    if not isinstance(template, str):
        return False
    if any(ch in template for ch in _STRING_BREAKOUT_CHARS):
        return False
    # Remove every well-formed placeholder; what remains is the literal text. If any stray brace
    # survives, the template contains a malformed or arbitrary brace expression and is rejected.
    remainder = _TEMPLATE_PLACEHOLDER.sub('', template)
    if '{' in remainder or '}' in remainder:
        return False
    return True


def _single_error(path: str, message: str, suggestion: str) -> list:
    """Build a one-element ``ValidationError`` list.

    Centralizes the error-list construction (and the local ``validation_utils`` import used to
    avoid a circular import: ``validation_utils`` is imported widely and this module is imported
    by ``schema_definitions``, which ``validation_utils`` does not depend on).
    """
    from awslabs.dynamodb_mcp_server.repo_generation_tool.core.validation_utils import (
        ValidationError,
    )

    return [ValidationError(path=path, message=message, suggestion=suggestion)]


def validate_python_identifier(name: object, path: str, kind: str) -> list:
    """Validate a name destined for a generated-code identifier position.

    Args:
        name: The candidate name to validate.
        path: Field path for error reporting (for example ``tables[0].entities.User``).
        kind: Human-readable description of what is being named (for example ``Entity name``,
            ``Field name``, ``Parameter name``, ``GSI name``) used in the error message.

    Returns:
        A list of ``ValidationError`` objects. The list is empty when the name is valid.
    """
    if is_valid_python_identifier(name):
        return []

    message = (
        f'{kind} must be a string'
        if not isinstance(name, str)
        else f"{kind} '{name}' is not a valid identifier"
    )
    return _single_error(
        path,
        message,
        'Use a valid Python identifier: letters, digits and underscores, not starting '
        'with a digit, and not a reserved word.',
    )


def validate_string_literal_value(value: object, path: str, kind: str) -> list:
    """Validate a value destined for a quoted string-literal position in generated code.

    Args:
        value: The candidate value to validate.
        path: Field path for error reporting.
        kind: Human-readable description of the value (for example ``entity_type``,
            ``table_name``) used in the error message.

    Returns:
        A list of ``ValidationError`` objects. The list is empty when the value is safe.
    """
    if is_safe_string_literal_value(value):
        return []

    message = (
        f'{kind} must be a string'
        if not isinstance(value, str)
        else f'{kind} contains disallowed characters (quote, backslash, or newline)'
    )
    return _single_error(
        path, message, 'Remove any double-quote, backslash, or newline characters.'
    )


def validate_key_template(template: object, path: str, kind: str) -> list:
    """Validate a key template destined for an f-string key builder in generated code.

    Args:
        template: The candidate template to validate.
        path: Field path for error reporting.
        kind: Human-readable description of the template (for example ``pk_template``,
            ``sk_template``) used in the error message.

    Returns:
        A list of ``ValidationError`` objects. The list is empty when the template is safe.
    """
    if is_safe_key_template(template):
        return []

    if not isinstance(template, str):
        message = f'{kind} must be a string'
    elif any(ch in template for ch in _STRING_BREAKOUT_CHARS):
        message = f'{kind} contains disallowed characters (quote, backslash, or newline)'
    else:
        message = (
            f'{kind} contains a brace expression that is not a simple {{field}} placeholder; '
            f'only {{field_name}} or {{field_name:format}} placeholders are allowed'
        )
    return _single_error(
        path,
        message,
        'Use only literal text and {field_name} (or {field_name:format}) placeholders, '
        'for example "USER#{user_id}".',
    )
