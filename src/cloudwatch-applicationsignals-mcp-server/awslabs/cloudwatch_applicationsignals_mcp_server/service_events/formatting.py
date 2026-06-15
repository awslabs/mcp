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

"""Presentation helpers for ServiceEvents incident call trees.

Incidents carry a flat ``call_path`` adjacency list inside
``body.exception_info[]``. Each entry looks like::

    {
        'function_name': 'module.func',
        'caller_function_name': 'module.caller',  # optional; null/absent for a root
        'duration_ns': 1958,
        'error': false,
        'is_async': false,
    }

These helpers reconstruct the call tree and render it as indented ASCII for
root-cause analysis.
"""

from typing import List, Optional


def _call_path_to_ascii(call_path: Optional[List[dict]]) -> str:
    """Render a flat ``call_path`` adjacency list as an indented ASCII call tree.

    Reconstructs parent→child edges from ``caller_function_name``. Nodes whose
    caller is absent or refers to a function not present in the path are treated
    as roots (the caller was outside the instrumented set). Durations are shown
    in milliseconds with a percentage relative to the slowest frame; failing
    frames are marked ``★ ERROR``.
    """
    if not call_path:
        return ''

    # Index nodes by function_name (preserve first-seen order; last entry wins on dup).
    nodes = {}
    order = []
    for entry in call_path:
        fn = entry.get('function_name')
        if not fn:
            continue
        if fn not in nodes:
            order.append(fn)
        nodes[fn] = entry

    if not nodes:
        return ''

    children = {fn: [] for fn in nodes}
    roots = []
    for fn in order:
        caller = nodes[fn].get('caller_function_name')
        if caller and caller in nodes and caller != fn:
            children[caller].append(fn)
        else:
            roots.append(fn)

    max_ns = max((nodes[fn].get('duration_ns') or 0) for fn in nodes) or 0

    def _render(fn: str, indent: str, is_last: bool, depth: int, visited: set) -> str:
        if fn in visited:
            # Cycle guard — render the frame once more as a leaf and stop.
            connector = '└── ' if is_last else '├── '
            return f'{indent}{connector}{fn} [↻ cycle]\n'
        visited = visited | {fn}

        node = nodes[fn]
        dur_ns = node.get('duration_ns') or 0
        ms = round(dur_ns / 1_000_000, 2)
        pct = round(dur_ns / max_ns * 100, 1) if max_ns else 0
        flags = ''
        if node.get('error'):
            flags += ' ★ ERROR'
        if node.get('is_async'):
            flags += ' [async]'
        label = f'{fn} [{ms}ms, {pct}%]{flags}'

        if depth == 0:
            line = label + '\n'
            child_indent = ''
        else:
            connector = '└── ' if is_last else '├── '
            line = indent + connector + label + '\n'
            child_indent = indent + ('    ' if is_last else '│   ')

        kids = children[fn]
        for i, kid in enumerate(kids):
            line += _render(kid, child_indent, i == len(kids) - 1, depth + 1, visited)
        return line

    out = ''
    for i, root in enumerate(roots):
        out += _render(root, '', i == len(roots) - 1, 0, set())
    return out


def render_incident_call_tree(call_path: List[dict]) -> str:
    """Render an incident call_path with a header indicating the data source.

    The call tree is built from function-call instrumentation (per-function
    timing captured at incident time).
    """
    tree = _call_path_to_ascii(call_path)
    if not tree:
        return ''
    header = '[Timing: function-call instrumentation]'
    return f'{header}\n{tree}'
