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
"""Validation and normalization helpers for instrumentation inputs."""

import re
from .constants import SNAPSHOT_SIGNAL_TYPE
from typing import List, Optional, Tuple


_LOCATION_HASH_RE = re.compile(r'[0-9a-f]{16}')

_CANONICAL_LANGUAGES = {'python': 'Python', 'java': 'Java', 'javascript': 'Javascript'}


def canonical_language(language: Optional[str]) -> Optional[str]:
    """Return the API's canonical ``ProgrammingLanguage`` casing, or None if unknown.

    The bundled service model's enum is case-sensitive (``Java``, ``Python``,
    ``Javascript``). Callers accept any casing (e.g. ``"javascript"``,
    ``"JavaScript"``) and map to the canonical form before sending to the API,
    so a validated language is not rejected by the backend on a casing mismatch.
    """
    return _CANONICAL_LANGUAGES.get((language or '').strip().lower())


def normalize_instrumentation_type(
    instrumentation_type: str,
) -> Tuple[str, Optional[str]]:
    """Normalize the type to upper-case; return ``(normalized, error)``.

    The normalized value is always a ``str`` (the upper-cased received value
    even on the error path) so callers get a non-optional type once they
    return early on ``error``. Callers must check ``error`` before using
    ``normalized``.
    """
    normalized = (instrumentation_type or '').strip().upper()
    allowed = {'BREAKPOINT', 'PROBE'}
    if normalized not in allowed:
        return normalized, (
            'ERROR: instrumentation_type must be one of BREAKPOINT, PROBE '
            f'(received: {instrumentation_type})'
        )
    return normalized, None


def validate_capture_names(field_name: str, names: Optional[List[str]]) -> Optional[str]:
    """Validate a capture-name list (``capture_arguments`` / ``capture_locals``).

    Returns an error string if invalid, else ``None``. An omitted list
    (``None``) is valid and means "capture nothing for that field". A provided
    list must be non-empty and may not contain the ``*`` wildcard — both the
    empty list and ``*`` are rejected so the ambiguous "capture all" shapes
    never reach the API.
    """
    if names is None:
        return None
    if not names:
        return (
            f'ERROR: {field_name} must contain at least one name if provided. '
            'Omit it to capture none.'
        )
    if '*' in names:
        return (
            f'ERROR: {field_name} does not support the wildcard "*". '
            'List explicit names, or omit it to capture none.'
        )
    return None


def validate_probe_constraints(
    normalized_type: str,
    language: Optional[str],
    line_number: Optional[int],
) -> Optional[str]:
    """Validate PROBE-only constraints; return error text if invalid, else None.

    PROBE differs from BREAKPOINT in two ways the SDKs enforce:

    * PROBE is not supported for JavaScript.
    * PROBE is method/function-level only — the SDKs ignore line_number, so a
      PROBE with line_number set would silently not behave as written.
    """
    if normalized_type != 'PROBE':
        return None
    lang = (language or '').strip().lower()
    if lang == 'javascript':
        return (
            'ERROR: PROBE is not supported for JavaScript. '
            'Use instrumentation_type=BREAKPOINT for JavaScript targets.'
        )
    if line_number is not None:
        return (
            'ERROR: PROBE does not support line_number (the SDKs ignore it). '
            'Omit line_number for PROBE — it is method/function-level only.'
        )
    return None


def is_valid_location_hash(location_hash: Optional[str]) -> bool:
    """Return True for a 16-character lowercase hexadecimal location hash.

    Location hashes are 16 lowercase hex characters by API design. Validating
    against this shape (rather than only checking length) lets snapshot/status
    tools reject malformed input before it is interpolated into a CloudWatch
    Logs Insights query — hex can never contain the double-quote that would
    otherwise break out of a query string literal.
    """
    return bool(location_hash and _LOCATION_HASH_RE.fullmatch(location_hash))


def validate_snapshot_signal(signal_type: str) -> Optional[str]:
    """Return an error message unless ``signal_type`` is SNAPSHOT, else None."""
    normalized = (signal_type or '').strip().upper()
    if normalized != SNAPSHOT_SIGNAL_TYPE:
        return f'ERROR: signal_type must be SNAPSHOT for this API (received: {signal_type})'
    return None


def _format_code_location_troubleshooting(
    language: Optional[str],
    file_path: Optional[str],
    code_unit: Optional[str],
    class_name: Optional[str],
    method_name: Optional[str],
    line_number: Optional[int],
) -> str:
    """Build troubleshooting guidance for code-location create failures.

    ``language``/``file_path`` are ``Optional`` because callers pass raw,
    unvalidated MCP inputs (which may be ``None``); the body renders them
    verbatim and guards with ``(language or '')`` where it matters.
    """
    lang = (language or '').strip().lower()

    lines = [
        'CODE LOCATION TROUBLESHOOTING:',
        '- file_path: source file path for the target code.',
        '- code_unit: Python runtime module path OR Java package name.',
        '- class_name: use for class methods (Java: simple class name only).',
        '- method_name: function/method name.',
        '- line_number: set only for line-level breakpoints (1-based).',
    ]

    if line_number is None:
        lines.append('- Breakpoint level: FUNCTION/METHOD-level (line_number omitted).')
    else:
        lines.append(f'- Breakpoint level: LINE-LEVEL (L{line_number}).')
        if lang in ('python', 'java'):
            lines.append(
                '  * NOTE: target an executable statement. In Python/Java a non-executable '
                'line (blank, comment, decorator, signature) is ignored and the breakpoint '
                'never fires.'
            )
        elif lang == 'javascript':
            lines.append(
                '  * NOTE: in JavaScript a breakpoint on a non-executable line slides to the '
                'next parseable line and fires there — verify it lands where you intend.'
            )

    if lang == 'python':
        lines.extend(
            [
                '- Python rules:',
                '  * Set code_unit to the dotted runtime import path for the module that defines the target code.',
                '  * Example: services.billing, not billing.py or /app/services/billing.py.',
                '  * Use code_unit="__main__" only when the target file is executed',
                '    directly as the process entry script.',
                '  * If call site uses direct import aliasing, target importing module and alias name.',
                '  * If you cannot determine the runtime module path confidently, inspect first instead of guessing.',
            ]
        )
    elif lang == 'java':
        lines.extend(
            [
                '- Java rules:',
                '  * Set code_unit to the Java package name (e.g., com.amazon.sampleapp).',
                '  * class_name must be simple name (e.g., OrderContext), not fully qualified.',
            ]
        )
    elif lang == 'javascript':
        lines.extend(
            [
                '- JavaScript rules:',
                '  * JavaScript binds by file_path + line_number; line_number is required (>= 1).',
                '  * code_unit, class_name, and method_name are not used for JavaScript.',
                '  * Point line_number at the executable statement you want to observe.',
            ]
        )

    lines.extend(
        [
            'LOCATION INPUTS RECEIVED:',
            f'- language={language}',
            f'- file_path={file_path}',
            f'- code_unit={code_unit}',
            f'- class_name={class_name}',
            f'- method_name={method_name}',
            f'- line_number={line_number}',
        ]
    )

    return '\n'.join(lines)


def _validate_location_inputs(
    language: str,
    file_path: str,
    code_unit: Optional[str],
    class_name: Optional[str],
    method_name: Optional[str],
    line_number: Optional[int],
) -> Optional[str]:
    """Validate location fields and return actionable error text if invalid.

    Enforces the per-language fields the SDK needs to bind the instrumentation;
    without them the SDK silently drops the configuration and nothing fires:

    * Java       — requires code_unit, class_name, and method_name.
    * Python     — requires code_unit and method_name (class_name optional).
    * JavaScript — requires line_number (>= 1); binds by file + line.
    """
    lang = (language or '').strip().lower()

    errors: List[str] = []
    suggestions: List[str] = []

    if not file_path or not str(file_path).strip():
        errors.append('file_path is required and must be non-empty.')

    if line_number is not None and line_number < 1:
        errors.append(f'line_number must be >= 1 (received: {line_number}).')

    if lang not in {'python', 'java', 'javascript'}:
        errors.append(f'language must be Python, Java, or JavaScript (received: {language}).')

    if lang == 'java':
        if not code_unit:
            errors.append('Java requires code_unit (the package name, e.g. com.amazon.sampleapp).')
        if not class_name:
            errors.append('Java requires class_name (the simple class name, e.g. OrderContext).')
        if not method_name:
            errors.append('Java requires method_name.')
        if class_name and '.' in class_name:
            errors.append(
                'For Java, class_name must be simple (e.g., "OrderContext"), '
                'not fully qualified (e.g., "com.example.OrderContext").'
            )
            if not code_unit:
                parts = class_name.split('.')
                if len(parts) > 1:
                    suggestions.append(
                        f'Use code_unit="{".".join(parts[:-1])}" and class_name="{parts[-1]}".'
                    )
        if code_unit and '/' in code_unit:
            suggestions.append(
                'Java code_unit should be a package name with dots, not a path with slashes.'
            )

    elif lang == 'python':
        if not code_unit:
            errors.append(
                'Python requires code_unit (the dotted runtime module path, e.g. services.billing).'
            )
        if not method_name:
            errors.append('Python requires method_name.')
        if code_unit and code_unit.endswith('.py'):
            suggestions.append(
                'Python code_unit should be a module path (e.g., services.billing), not a .py filename.'
            )

    elif lang == 'javascript':
        if line_number is None:
            errors.append('JavaScript requires line_number (>= 1); it binds by file and line.')

    if not errors:
        return None

    message = 'Invalid breakpoint location inputs:\n'
    for idx, err in enumerate(errors, 1):
        message += f'{idx}. {err}\n'

    if suggestions:
        message += '\nSuggestions:\n'
        for idx, item in enumerate(suggestions, 1):
            message += f'{idx}. {item}\n'

    message += '\n' + _format_code_location_troubleshooting(
        language=language,
        file_path=file_path,
        code_unit=code_unit,
        class_name=class_name,
        method_name=method_name,
        line_number=line_number,
    )

    return message
