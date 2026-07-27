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

"""Tests for the ServiceEvents incident call-tree formatting helpers."""

from awslabs.cloudwatch_applicationsignals_mcp_server.service_events import formatting


# ============================================================================
# _call_path_to_ascii
# ============================================================================


class TestCallPathToAscii:
    """Tests for rendering a flat call_path adjacency list as an ASCII tree."""

    def test_empty_path_returns_empty(self):
        """Return an empty string for an empty call path."""
        assert formatting._call_path_to_ascii([]) == ''

    def test_entries_without_function_name_skipped(self):
        """Skip entries lacking a function_name; empty result when none are valid."""
        # No entry has a function_name -> nodes stays empty -> early empty return.
        assert formatting._call_path_to_ascii([{'duration_ns': 100}, {}]) == ''

    def test_skips_nameless_but_renders_named(self):
        """A nameless entry is skipped while a named root still renders."""
        call_path = [
            {'function_name': '', 'duration_ns': 1},
            {'function_name': 'root', 'duration_ns': 1_000_000},
        ]
        out = formatting._call_path_to_ascii(call_path)
        assert 'root' in out
        assert out.count('\n') == 1

    def test_root_and_child_tree(self):
        """Render a parent and its child with indentation and percentages."""
        call_path = [
            {'function_name': 'root', 'duration_ns': 2_000_000},
            {
                'function_name': 'child',
                'caller_function_name': 'root',
                'duration_ns': 1_000_000,
            },
        ]
        out = formatting._call_path_to_ascii(call_path)
        assert 'root [2.0ms, 100.0%]' in out
        assert '└── child [1.0ms, 50.0%]' in out

    def test_error_and_async_flags(self):
        """Mark failing frames with ERROR and async frames with [async]."""
        call_path = [
            {
                'function_name': 'root',
                'duration_ns': 1_000_000,
                'error': True,
                'is_async': True,
            },
        ]
        out = formatting._call_path_to_ascii(call_path)
        assert '★ ERROR' in out
        assert '[async]' in out

    def test_zero_duration_all_frames(self):
        """Handle a zero max duration without dividing by zero (pct=0)."""
        call_path = [{'function_name': 'root', 'duration_ns': 0}]
        out = formatting._call_path_to_ascii(call_path)
        assert 'root [0.0ms, 0%]' in out

    def test_multiple_roots(self):
        """Render multiple roots when callers are outside the instrumented set."""
        call_path = [
            {'function_name': 'r1', 'duration_ns': 1_000_000},
            {'function_name': 'r2', 'caller_function_name': 'missing', 'duration_ns': 1_000_000},
        ]
        out = formatting._call_path_to_ascii(call_path)
        assert 'r1' in out
        assert 'r2' in out


# ============================================================================
# render_incident_call_tree
# ============================================================================


class TestRenderIncidentCallTree:
    """Tests for the public call-tree renderer with the source header."""

    def test_empty_path_returns_empty(self):
        """Return empty (no header) when there is nothing to render."""
        assert formatting.render_incident_call_tree([]) == ''

    def test_prepends_header(self):
        """Prepend the instrumentation-source header to a non-empty tree."""
        out = formatting.render_incident_call_tree(
            [{'function_name': 'root', 'duration_ns': 1_000_000}]
        )
        assert out.startswith('[Timing: function-call instrumentation]\n')
        assert 'root' in out
