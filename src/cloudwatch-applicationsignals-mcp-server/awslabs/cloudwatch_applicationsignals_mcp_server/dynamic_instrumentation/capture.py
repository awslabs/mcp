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
"""Capture configuration ADT for dynamic instrumentation.

Mirrors the ``Location`` design: a sealed sum type covers the two
``CaptureConfiguration`` variants the ``application-signals`` API exposes,
plus an ``UnknownCapture`` fallback so renderers stay forward-compatible.

The type owns the API shape — payload assembly via ``to_api_payload`` and
inverse parsing via ``capture_from_response``. It does *not* own prose
rendering (renderers keep their CAPTURE SETTINGS / CAPTURE CONFIGURATION
blocks) and it does *not* fill in tool-input defaults (defaults like
``capture_return=True`` resolve at the tool layer where the success-message
prose can read the resolved value).

The ADT preserves the distinction between an *omitted* list (``None`` — key
absent from the API payload) and a *present-but-empty* list (``()`` — key
emitted as ``[]``) so an API response round-trips parse → payload → parse
without losing information. It does *not* assert what the backend means by
either shape. The MCP *create* tool deliberately does not expose both shapes:
it rejects empty lists and the ``*`` wildcard and treats an omitted list as
"capture nothing for that field" (see ``create_instrumentation``). Renderers
report the raw shape rather than labeling it "all" or "none".
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, Mapping, Optional, Sequence, Union


@dataclass(frozen=True)
class CaptureLimits:
    """Optional size caps applied to a code-capture payload."""

    max_hits: Optional[int] = None
    max_string_length: Optional[int] = None
    max_collection_width: Optional[int] = None
    max_collection_depth: Optional[int] = None
    max_stack_frames: Optional[int] = None
    max_stack_trace_size: Optional[int] = None
    max_object_depth: Optional[int] = None
    max_fields_per_object: Optional[int] = None

    def is_empty(self) -> bool:
        """Return True when no capture limit is set."""
        return all(
            v is None
            for v in (
                self.max_hits,
                self.max_string_length,
                self.max_collection_width,
                self.max_collection_depth,
                self.max_stack_frames,
                self.max_stack_trace_size,
                self.max_object_depth,
                self.max_fields_per_object,
            )
        )

    def to_api_payload(self) -> Dict[str, int]:
        """Render the set capture limits as the CaptureLimits payload."""
        payload: Dict[str, int] = {}
        if self.max_hits is not None:
            payload['MaxHits'] = self.max_hits
        if self.max_string_length is not None:
            payload['MaxStringLength'] = self.max_string_length
        if self.max_collection_width is not None:
            payload['MaxCollectionWidth'] = self.max_collection_width
        if self.max_collection_depth is not None:
            payload['MaxCollectionDepth'] = self.max_collection_depth
        if self.max_stack_frames is not None:
            payload['MaxStackFrames'] = self.max_stack_frames
        if self.max_stack_trace_size is not None:
            payload['MaxStackTraceSize'] = self.max_stack_trace_size
        if self.max_object_depth is not None:
            payload['MaxObjectDepth'] = self.max_object_depth
        if self.max_fields_per_object is not None:
            payload['MaxFieldsPerObject'] = self.max_fields_per_object
        return payload


@dataclass(frozen=True)
class CodeCapture:
    """Capture configuration for BREAKPOINT and PROBE.

    ``capture_arguments`` and ``capture_locals`` are stored as tuples so the
    ``frozen=True`` immutability contract holds against mutation through the
    container (a caller's reference to the source list cannot mutate this
    instance). Constructors still accept any iterable of strings — including
    a list — and ``__post_init__`` converts to ``tuple``. This is the same
    discipline ``Location`` applies to ``extra_fields`` via
    ``MappingProxyType``.

    The ``Optional`` distinction is preserved across the round-trip: ``None``
    omits the key from the API payload, while an empty tuple ``()`` emits the
    key as ``[]``. This ADT does not assign semantics to either shape; the
    create tool restricts which shapes it will send (see
    ``create_instrumentation``).
    """

    capture_return: bool
    capture_stack_trace: bool
    # Declared as ``Sequence[str]`` because the constructor accepts any string
    # sequence (commonly a list); ``__post_init__`` coerces to ``tuple`` so the
    # stored value is always an immutable tuple despite the broader input type.
    capture_arguments: Optional[Sequence[str]] = None
    capture_locals: Optional[Sequence[str]] = None
    limits: CaptureLimits = field(default_factory=CaptureLimits)

    def __post_init__(self) -> None:
        """Coerce argument/local name lists to tuples for the frozen contract."""
        if self.capture_arguments is not None and not isinstance(self.capture_arguments, tuple):
            object.__setattr__(self, 'capture_arguments', tuple(self.capture_arguments))
        if self.capture_locals is not None and not isinstance(self.capture_locals, tuple):
            object.__setattr__(self, 'capture_locals', tuple(self.capture_locals))

    def to_api_payload(self) -> Dict[str, Any]:
        """Render the CodeCapture create-request payload."""
        config: Dict[str, Any] = {
            'CaptureReturn': self.capture_return,
            'CaptureStackTrace': self.capture_stack_trace,
            'CaptureLimits': self.limits.to_api_payload(),
        }
        if self.capture_arguments is not None:
            config['CaptureArguments'] = list(self.capture_arguments)
        if self.capture_locals is not None:
            config['CaptureLocals'] = list(self.capture_locals)
        return {'CodeCapture': config}


@dataclass(frozen=True)
class UnknownCapture:
    """A CaptureConfiguration union that did not match a known variant.

    ``raw`` is wrapped in ``MappingProxyType`` to keep the ``frozen=True``
    contract intact against mutation through the source dict — the same
    discipline applied to ``Location.extra_fields`` and
    ``CodeCapture.capture_arguments``.
    """

    raw: Mapping[str, Any]

    def __post_init__(self) -> None:
        """Wrap ``raw`` in a read-only proxy to honor the frozen contract."""
        if not isinstance(self.raw, MappingProxyType):
            object.__setattr__(self, 'raw', MappingProxyType(dict(self.raw)))


Capture = Union[CodeCapture, UnknownCapture]


_CODE_CAPTURE_HINT_KEYS = (
    'CaptureReturn',
    'CaptureLimits',
    'CaptureArguments',
    'CaptureStackTrace',
)


def capture_from_response(union_dict: Optional[Dict[str, Any]]) -> Capture:
    """Parse a ``CaptureConfiguration`` union returned by the API into the ADT.

    Falls back to inferring a ``CodeCapture`` if a CodeCapture-shaped dict
    is passed without the ``CodeCapture`` wrapper key — this matches the
    legacy ``extract_capture_variant`` fallback that some response shapes
    relied on.
    """
    if not isinstance(union_dict, dict):
        return UnknownCapture(raw={})

    code = union_dict.get('CodeCapture')
    if isinstance(code, dict):
        return _code_capture_from_dict(code)

    if any(key in union_dict for key in _CODE_CAPTURE_HINT_KEYS):
        return _code_capture_from_dict(union_dict)

    return UnknownCapture(raw=dict(union_dict))


def _code_capture_from_dict(payload: Dict[str, Any]) -> CodeCapture:
    raw_limits = payload.get('CaptureLimits') or {}
    if not isinstance(raw_limits, dict):
        raw_limits = {}
    limits = CaptureLimits(
        max_hits=raw_limits.get('MaxHits'),
        max_string_length=raw_limits.get('MaxStringLength'),
        max_collection_width=raw_limits.get('MaxCollectionWidth'),
        max_collection_depth=raw_limits.get('MaxCollectionDepth'),
        max_stack_frames=raw_limits.get('MaxStackFrames'),
        max_stack_trace_size=raw_limits.get('MaxStackTraceSize'),
        max_object_depth=raw_limits.get('MaxObjectDepth'),
        max_fields_per_object=raw_limits.get('MaxFieldsPerObject'),
    )
    return CodeCapture(
        capture_return=bool(payload.get('CaptureReturn')),
        capture_stack_trace=bool(payload.get('CaptureStackTrace')),
        capture_arguments=payload.get('CaptureArguments')
        if 'CaptureArguments' in payload
        else None,
        capture_locals=payload.get('CaptureLocals') if 'CaptureLocals' in payload else None,
        limits=limits,
    )


__all__ = [
    'CaptureLimits',
    'CodeCapture',
    'UnknownCapture',
    'Capture',
    'capture_from_response',
]
