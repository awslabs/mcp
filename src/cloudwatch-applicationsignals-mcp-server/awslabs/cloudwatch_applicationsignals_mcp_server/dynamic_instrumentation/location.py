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
"""Location ADT for dynamic instrumentation.

A "location" is the central domain noun of this package: where in customer
code (or which endpoint) an instrumentation configuration applies. The
``application-signals`` API exposes three flavors:

* ``CodeLocation``    — language + file/class/method/line, used by BREAKPOINT
                        and PROBE.
* ``LocationHash``    — a 16-character hex identifier referring to an
                        already-created configuration.

This module collapses the seven module-level helpers that used to build,
identify, and render those three shapes into a single sealed ``Location``
sum type. Two parsers cover input flow (create vs. lookup), and one parser
covers response flow.

Tools never construct API dicts directly; they call ``parse_*_inputs`` and
then ``loc.to_api_payload()`` / ``loc.to_identifier()``. Renderers never
inspect raw union dicts; they call ``location_from_response`` and use the
type's instance methods.
"""

from .validation import _validate_location_inputs, canonical_language
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union


_EMPTY_EXTRA_FIELDS: Mapping[str, Any] = MappingProxyType({})


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    """Wrap an extra-fields dict in a read-only proxy.

    Prevents frozen dataclasses from being mutated through their containers.
    Idempotent: an existing ``MappingProxyType`` is returned unchanged.
    """
    if isinstance(value, MappingProxyType):
        return value
    return MappingProxyType(dict(value))


@dataclass(frozen=True)
class CodeLocation:
    """A code-based instrumentation target (BREAKPOINT or PROBE).

    Which fields identify the target vs. which are metadata depends on language:

    * Java       — ``code_unit`` (package), ``class_name`` (simple name), and
                   ``method_name`` together identify the target; all required.
    * Python     — ``code_unit`` (dotted module path) and ``method_name``
                   identify the target; ``class_name`` is optional (qualifies a
                   method defined in a class).
    * JavaScript — ``file_path`` + ``line_number`` identify the target;
                   ``code_unit``/``class_name``/``method_name`` are not used.

    ``line_number`` makes any target line-level (fires at that line rather than
    on method entry/exit).
    """

    language: str
    file_path: str
    code_unit: Optional[str] = None
    class_name: Optional[str] = None
    method_name: Optional[str] = None
    line_number: Optional[int] = None
    extra_fields: Mapping[str, Any] = field(default_factory=lambda: _EMPTY_EXTRA_FIELDS)

    def __post_init__(self) -> None:
        """Freeze ``extra_fields`` past the dataclass frozen guard."""
        # frozen=True only blocks reassignment; the dict itself stays
        # mutable unless we wrap it. Use object.__setattr__ to assign past
        # the frozen guard.
        object.__setattr__(self, 'extra_fields', _freeze_mapping(self.extra_fields))

    def describe(self) -> str:
        """Return a one-line human description of the code target."""
        target = self.file_path or 'N/A'
        if self.class_name:
            target += f' :: {self.class_name}'
        if self.method_name:
            target += f'.{self.method_name}'
        if self.line_number is not None:
            target += f':L{self.line_number}'
        return target

    def level(self) -> str:
        """Return the breakpoint granularity (line-level or function-level)."""
        if self.line_number is not None:
            return f'LINE-LEVEL (L{self.line_number})'
        return 'FUNCTION/METHOD-LEVEL'

    def format_details(self, location_hash: Optional[str] = None) -> str:
        """Render the code location as labeled detail lines."""
        lines = ['- LocationKind: CODE']
        if location_hash:
            lines.append(f'- LocationHash: {location_hash}')
        ordered = [
            ('Language', self.language),
            ('File Path', self.file_path),
            ('Code Unit', self.code_unit),
            ('Class Name', self.class_name),
            ('Method Name', self.method_name),
            ('Line Number', self.line_number),
        ]
        for label, value in ordered:
            # Mirror legacy ``format_location_details`` semantics: present-but-empty
            # fields (``Language=""``) still render as ``- Language: `` so missing
            # API fields produce a visible blank instead of being silently dropped.
            if value is not None:
                lines.append(f'- {label}: {value}')
        for key in sorted(self.extra_fields.keys()):
            lines.append(f'- {key}: {self.extra_fields[key]}')
        return '\n'.join(lines) + '\n'

    def to_api_payload(self) -> Dict[str, Any]:
        """Return the CodeLocation create-request payload."""
        return {'CodeLocation': self._to_code_location_dict()}

    def to_identifier(self) -> Dict[str, Any]:
        """Return the CodeLocation lookup identifier payload."""
        return {'CodeLocation': self._to_code_location_dict()}

    def _to_code_location_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            'Language': self.language,
            'FilePath': self.file_path,
        }
        if self.code_unit:
            payload['CodeUnit'] = self.code_unit
        if self.class_name:
            payload['ClassName'] = self.class_name
        if self.method_name:
            payload['MethodName'] = self.method_name
        if self.line_number is not None:
            payload['LineNumber'] = self.line_number
        return payload


@dataclass(frozen=True)
class HashLocation:
    """An existing configuration referenced by its 16-char location hash.

    Carries a deliberately narrower interface than its sibling variants:

    * ``to_api_payload`` is *unsupported*: a hash cannot describe a *new*
      configuration — ``create_instrumentation_configuration`` requires
      a real CodeLocation.
    * ``format_details`` is *unsupported*: a hash has no fields beyond
      itself; ``render_location_block`` prints the hash via its
      ``HashLocation`` special case instead.

    Both methods exist as stubs that raise ``NotImplementedError`` with a
    descriptive message rather than being absent. The asymmetry is still
    the design — these are lookup-only — but the explicit raise turns
    a confusing ``AttributeError`` into a clear "use ``to_identifier()``
    instead" message when a future caller forgets the discipline.
    """

    location_hash: str

    def describe(self) -> str:
        """Return a one-line description naming the location hash."""
        return f'LocationHash {self.location_hash}'

    def level(self) -> Optional[str]:
        """Return None — a hash carries no breakpoint granularity."""
        return None

    def to_identifier(self) -> Dict[str, Any]:
        """Return the LocationHash lookup identifier payload."""
        return {'LocationHash': self.location_hash}

    def to_api_payload(self) -> Dict[str, Any]:
        """Unsupported — a hash cannot describe a new configuration."""
        raise NotImplementedError(
            'HashLocation cannot be used in create requests — use to_identifier() instead. '
            'create_instrumentation_configuration requires a CodeLocation.'
        )

    def format_details(self, location_hash: Optional[str] = None) -> str:
        """Unsupported — a hash has no fields; describe() gives a one-liner."""
        raise NotImplementedError(
            'HashLocation has no fields to format — render_location_block handles it directly. '
            'Use describe() for a one-line target string.'
        )


@dataclass(frozen=True)
class UnknownLocation:
    """A location union returned by the API that does not match any known variant.

    A forward-compat fallback: ``location_from_response`` produces this so
    renderers don't crash on future API additions. Input parsers never
    produce it. Mirrors ``UnknownCapture`` in shape and naming — both are
    public so callers doing exhaustive ``isinstance`` matching don't need
    to reach into a private name.

    ``raw`` is wrapped in ``MappingProxyType`` so the ``frozen=True``
    contract holds against mutation through the source dict.
    """

    raw: Mapping[str, Any]

    def __post_init__(self) -> None:
        """Wrap ``raw`` in a read-only proxy to honor the frozen contract."""
        if not isinstance(self.raw, MappingProxyType):
            object.__setattr__(self, 'raw', MappingProxyType(dict(self.raw)))

    def describe(self) -> str:
        """Return 'N/A' — an unknown location has no describable target."""
        return 'N/A'

    def level(self) -> Optional[str]:
        """Return None — an unknown location has no granularity."""
        return None

    def format_details(self, location_hash: Optional[str] = None) -> str:
        """Render the unknown location's raw fields as detail lines."""
        lines = ['- LocationKind: UNKNOWN']
        if location_hash:
            lines.append(f'- LocationHash: {location_hash}')
        if self.raw:
            for key in sorted(self.raw.keys()):
                lines.append(f'- {key}: {self.raw[key]}')
        else:
            lines.append('- Location payload could not be parsed.')
        return '\n'.join(lines) + '\n'


Location = Union[CodeLocation, HashLocation, UnknownLocation]

# A location resolved from *caller* inputs (create/lookup). Unlike ``Location``,
# this never includes ``UnknownLocation`` — that variant only arises when parsing
# an API *response* (see ``location_from_response``). Narrowing the parser return
# types to this union lets callers use ``to_identifier``/``to_api_payload``
# without a cast, since both members implement them.
ResolvedLocation = Union[CodeLocation, HashLocation]


# ──────────────────────────── input parsers ────────────────────────────


def parse_create_inputs(
    *,
    normalized_type: str,
    language: Optional[str] = None,
    file_path: Optional[str] = None,
    code_unit: Optional[str] = None,
    class_name: Optional[str] = None,
    method_name: Optional[str] = None,
    line_number: Optional[int] = None,
) -> Tuple[Optional[ResolvedLocation], Optional[str]]:
    """Parse MCP-tool kwargs into a ``Location`` for a create-instrumentation call.

    HashLocation is not accepted: callers cannot create an instrumentation from
    an existing hash. Returns ``(location, None)`` on success or
    ``(None, error_text)`` when inputs are invalid; ``error_text`` is rendered
    verbatim back to the MCP caller.
    """
    if not language or not file_path:
        return None, (
            'ERROR: BREAKPOINT/PROBE require language and file_path.\n'
            'Example: language="Python", file_path="/app/handler.py"'
        )

    location_validation_error = _validate_location_inputs(
        language=language,
        file_path=file_path,
        code_unit=code_unit,
        class_name=class_name,
        method_name=method_name,
        line_number=line_number,
    )
    if location_validation_error:
        return None, location_validation_error

    return (
        CodeLocation(
            language=canonical_language(language) or language,
            file_path=file_path,
            code_unit=code_unit,
            class_name=class_name,
            method_name=method_name,
            line_number=line_number,
        ),
        None,
    )


def parse_lookup_inputs(
    *,
    normalized_type: str,
    location_hash: Optional[str] = None,
    language: Optional[str] = None,
    file_path: Optional[str] = None,
    code_unit: Optional[str] = None,
    class_name: Optional[str] = None,
    method_name: Optional[str] = None,
    line_number: Optional[int] = None,
    allow_code_location_lookup: bool = True,
) -> Tuple[Optional[ResolvedLocation], Optional[str]]:
    """Parse MCP-tool kwargs into a ``Location`` for a lookup operation.

    Lookup accepts a location_hash or a code location. Resolution order:
    hash > code location. Returns ``(location, None)`` or ``(None, error_text)``.
    """
    if location_hash:
        return HashLocation(location_hash=location_hash), None

    if language and file_path:
        if not allow_code_location_lookup:
            return None, 'code location lookup is not supported for this operation.'
        return (
            CodeLocation(
                language=language,
                file_path=file_path,
                code_unit=code_unit,
                class_name=class_name,
                method_name=method_name,
                line_number=line_number,
            ),
            None,
        )

    return None, (
        'missing location identifier input. Provide location_hash '
        'OR language+file_path (code location).'
    )


# ──────────────────────────── response parser ────────────────────────────


_KNOWN_CODE_FIELDS = {'Language', 'FilePath', 'CodeUnit', 'ClassName', 'MethodName', 'LineNumber'}


def location_from_response(union_dict: Optional[Dict[str, Any]]) -> Location:
    """Parse a ``Location`` union returned by the API into the ADT.

    Returns ``UnknownLocation`` if the dict has no recognized variant — this
    keeps response rendering forward-compatible with future API additions.
    """
    if not isinstance(union_dict, dict):
        return UnknownLocation(raw={})

    code = union_dict.get('CodeLocation')
    if isinstance(code, dict):
        return _code_location_from_dict(code)

    if 'Language' in union_dict or 'FilePath' in union_dict:
        return _code_location_from_dict(union_dict)

    return UnknownLocation(raw=dict(union_dict))


def _code_location_from_dict(payload: Dict[str, Any]) -> CodeLocation:
    extras = {k: v for k, v in payload.items() if k not in _KNOWN_CODE_FIELDS}
    return CodeLocation(
        language=payload.get('Language', ''),
        file_path=payload.get('FilePath', ''),
        code_unit=payload.get('CodeUnit'),
        class_name=payload.get('ClassName'),
        method_name=payload.get('MethodName'),
        line_number=payload.get('LineNumber'),
        extra_fields=extras,
    )


# ──────────────────────────── shared helpers ────────────────────────────


def render_location_block(location: Location, location_hash: Optional[str] = None) -> str:
    """Render the standard LOCATION block plus the optional INSTRUMENTATION level line."""
    if isinstance(location, HashLocation):
        # HashLocation has no API-side dict to format; should not normally
        # reach a renderer, but keep the path safe.
        block = f'- LocationKind: HASH\n- LocationHash: {location.location_hash}\n'
        return block

    output = location.format_details(location_hash=location_hash)
    level = location.level()
    if level:
        output += '\nINSTRUMENTATION:\n'
        output += f'- Level: {level}\n'
    return output


__all__: List[str] = [
    'CodeLocation',
    'HashLocation',
    'UnknownLocation',
    'Location',
    'ResolvedLocation',
    'parse_create_inputs',
    'parse_lookup_inputs',
    'location_from_response',
    'render_location_block',
]
