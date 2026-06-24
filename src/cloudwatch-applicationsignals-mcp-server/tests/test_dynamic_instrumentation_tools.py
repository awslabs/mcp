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

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for dynamic instrumentation helper modules."""

import awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients as parent_aws_clients
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.capture as capture
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.constants as constants
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.crud_rendering as crud_rendering
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.crud_tools as crud_tools
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.error_translation as error_translation
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.location as location
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.registration as registration
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.snapshot_parsing as snapshot_parsing
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.snapshot_queries as snapshot_queries
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.snapshot_rendering as snapshot_rendering
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.snapshot_tools as snapshot_tools
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.status_rendering as status_rendering
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.status_tools as status_tools
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.validation as validation
import json
import pytest
from botocore.exceptions import ClientError, EndpointConnectionError, NoCredentialsError
from botocore.stub import Stubber
from datetime import datetime, timedelta, timezone


class RecorderMCP:
    """Capture tool registration without depending on a live MCP server."""

    def __init__(self):
        """Initialize the recorder."""
        self.registered = []
        self.annotations = {}

    def tool(self, *, annotations=None):
        """Return a decorator that records the registered tool's name and annotations."""

        def _decorator(func):
            self.registered.append(func.__name__)
            self.annotations[func.__name__] = annotations
            return func

        return _decorator


@pytest.fixture(autouse=True)
def _deactivate_stubbers():
    """Deactivate any Stubber attached to the shared client between tests.

    The dynamic-instrumentation tools call the parent package's *module-level*
    ``application-signals`` client (``parent_aws_clients.applicationsignals_client``).
    Unlike a per-test lazy client, that singleton persists across tests, so a
    Stubber activated on it would leak its queued responses into the next test.
    Tests register their Stubber on ``_active_stubbers`` (via the shared
    ``_stub_application_signals`` helper) and this fixture deactivates them on
    teardown.
    """
    yield
    # Drain in a finally so that if one deactivate() raises, the remaining
    # stubbers are still detached from the shared client and cannot leak their
    # queued responses into the next test.
    while _active_stubbers:
        stubber = _active_stubbers.pop()
        try:
            stubber.deactivate()
        except Exception:  # pragma: no cover - defensive teardown
            pass


# Stubbers registered by _stub_application_signals(); drained by the autouse
# fixture above so each test starts with a clean shared client.
_active_stubbers: list = []


def _stub_application_signals() -> Stubber:
    """Activate a Stubber on the shared application-signals client and track it.

    Returns the activated Stubber; the autouse ``_deactivate_stubbers`` fixture
    tears it down after the test so it cannot leak into the next one.
    """
    client = parent_aws_clients.get_applicationsignals_client()
    stubber = Stubber(client)
    stubber.activate()
    _active_stubbers.append(stubber)
    return stubber


class TestApplicationSignalsModel:
    """The shared application-signals client exposes the DI operations."""

    def test_application_signals_client_exposes_instrumentation_operations(self):
        """The public application-signals model exposes the DI operations."""
        client = parent_aws_clients.get_applicationsignals_client()
        operations = client.meta.service_model.operation_names
        assert 'CreateInstrumentationConfiguration' in operations
        assert 'ListInstrumentationConfigurations' in operations


class TestErrorTranslator:
    """Test the boto3 exception → human message helper."""

    def _make_client_error(self, code: str, message: str) -> ClientError:
        return ClientError(
            error_response={'Error': {'Code': code, 'Message': message}},
            operation_name='CreateInstrumentationConfiguration',
        )

    def test_client_error_includes_code_and_message(self):
        """Client error includes code and message."""
        rendered = error_translation.translate_aws_error(
            self._make_client_error('ValidationException', 'bad input'),
            action='create instrumentation',
            context={'Service': 'svc', 'Environment': 'env'},
        )
        assert 'ValidationException' in rendered
        assert 'bad input' in rendered
        assert 'ATTEMPTED PARAMETERS:' in rendered
        assert '- Service: svc' in rendered

    def test_endpoint_connection_error_renders_endpoint_guidance(self):
        """Endpoint connection error renders endpoint guidance."""
        rendered = error_translation.translate_aws_error(
            EndpointConnectionError(endpoint_url='http://x'),
            action='list instrumentations',
        )
        assert 'EndpointConnectionError' in rendered
        assert 'network connectivity' in rendered

    def test_no_credentials_error_renders_credential_guidance(self):
        """No credentials error renders credential guidance."""
        rendered = error_translation.translate_aws_error(
            NoCredentialsError(),
            action='get instrumentation',
        )
        assert 'NoCredentialsError' in rendered
        assert 'aws configure list' in rendered

    def test_generic_exception_falls_back_to_unexpected_error(self):
        """Generic exception falls back to unexpected error."""
        rendered = error_translation.translate_aws_error(
            RuntimeError('boom'),
            action='probe',
        )
        assert 'Unexpected error: boom' in rendered

    def test_context_with_blank_values_renders_without_placeholders(self):
        """Context with blank values renders without placeholders."""
        rendered = error_translation.translate_aws_error(
            self._make_client_error('InternalFailure', 'whoops'),
            action='x',
            context={'Service': 'svc', 'Environment': ''},
        )
        assert '- Service: svc' in rendered
        assert 'Environment: ' not in rendered

    def test_render_client_error_emits_all_sections_in_order(self):
        """Render client error emits all sections in order."""
        rendered = error_translation.render_client_error(
            self._make_client_error('ValidationException', 'bad input'),
            action='create instrumentation',
            attempted_label='ATTEMPTED CONFIGURATION:',
            attempted={'Service': 'svc', 'Environment': 'env'},
            possible_causes=['First cause', 'Second cause'],
            troubleshooting=['Step one'],
            trailer='LOCATION TROUBLESHOOTING:\n- something',
        )
        assert 'Failed to create instrumentation' in rendered
        assert 'Error: ValidationException - bad input' in rendered
        assert 'ATTEMPTED CONFIGURATION:\n- Service: svc' in rendered
        assert 'POSSIBLE CAUSES:\n1. First cause\n2. Second cause' in rendered
        assert 'TROUBLESHOOTING:\n1. Step one' in rendered
        assert rendered.endswith('LOCATION TROUBLESHOOTING:\n- something')


class TestCrudToolsBoto3Integration:
    """Stubber-driven coverage for the boto3 CRUD path."""

    def test_list_instrumentations_renders_empty_list(self):
        """List instrumentations renders empty list."""
        stubber = _stub_application_signals()
        stubber.add_response(
            'list_instrumentation_configurations',
            {
                'Service': 'svc',
                'Environment': 'env',
                'Changed': False,
                'LatestConfigurations': [],
                'SyncedAt': datetime(2026, 3, 9, 12, 0, 0, tzinfo=timezone.utc),
                'SyncInterval': 60,
            },
            expected_params={
                'Service': 'svc',
                'Environment': 'env',
                'InstrumentationType': 'BREAKPOINT',
            },
        )
        rendered = crud_tools.list_instrumentations(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
        )
        stubber.assert_no_pending_responses()
        assert 'No active BREAKPOINT instrumentations found' in rendered

    def test_list_instrumentations_translates_client_error(self):
        """List instrumentations translates client error."""
        stubber = _stub_application_signals()
        stubber.add_client_error(
            'list_instrumentation_configurations',
            service_error_code='ValidationException',
            service_message='bad scope',
        )
        rendered = crud_tools.list_instrumentations(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
        )
        assert 'Failed to list instrumentations' in rendered
        assert 'ValidationException' in rendered
        assert 'bad scope' in rendered

    def test_create_instrumentation_rejects_wildcard_capture_argument(self):
        """Create instrumentation rejects a wildcard in capture_arguments before any API call."""
        stubber = _stub_application_signals()
        rendered = crud_tools.create_instrumentation(
            instrumentation_type='BREAKPOINT',
            service='svc',
            environment='env',
            language='Python',
            file_path='/app/handler.py',
            code_unit='services.handler',
            method_name='run',
            capture_arguments=['order_id', '*'],
        )
        # No API call should have been made — the wildcard is rejected up front.
        stubber.assert_no_pending_responses()
        assert 'capture_arguments does not support the wildcard' in rendered

    def test_create_line_level_success_suppresses_arguments_and_return(self):
        """A line-level create success message shows locals/stack traces, not arguments/return."""
        stubber = _stub_application_signals()
        stubber.add_response(
            'create_instrumentation_configuration',
            {
                'InstrumentationType': 'BREAKPOINT',
                'Service': 'svc',
                'Environment': 'env',
                'SignalType': 'SNAPSHOT',
                'Location': {
                    'CodeLocation': {
                        'Language': 'Python',
                        'FilePath': '/app/handler.py',
                        'LineNumber': 42,
                    }
                },
                'LocationHash': 'aaaabbbbccccdddd',
                'Description': 'MCP dynamic instrumentation',
                'CaptureConfiguration': {
                    'CodeCapture': {
                        'CaptureLocals': ['total'],
                        'CaptureReturn': True,
                        'CaptureStackTrace': True,
                        'CaptureLimits': {},
                    }
                },
                'CreatedAt': datetime(2026, 3, 9, 12, 0, 0, tzinfo=timezone.utc),
                'ARN': 'arn:demo',
            },
        )
        rendered = crud_tools.create_instrumentation(
            instrumentation_type='BREAKPOINT',
            service='svc',
            environment='env',
            language='Python',
            file_path='/app/handler.py',
            code_unit='services.handler',
            method_name='run',
            line_number=42,
            capture_locals=['total'],
        )
        stubber.assert_no_pending_responses()
        assert 'Successfully created BREAKPOINT instrumentation' in rendered
        assert '- Local Variables: total' in rendered
        assert '- Stack Traces: Enabled' in rendered
        assert '- Arguments:' not in rendered
        assert '- Return Values:' not in rendered

    def test_create_instrumentation_renders_client_error_with_attempted_block(self):
        """Create instrumentation renders client error with attempted block."""
        stubber = _stub_application_signals()
        stubber.add_client_error(
            'create_instrumentation_configuration',
            service_error_code='ResourceAlreadyExistsException',
            service_message='duplicate location',
        )
        rendered = crud_tools.create_instrumentation(
            instrumentation_type='BREAKPOINT',
            service='svc',
            environment='env',
            language='Python',
            file_path='/app/handler.py',
            code_unit='services.handler',
            method_name='run',
            capture_arguments=['order_id'],
        )
        assert 'Failed to create BREAKPOINT instrumentation' in rendered
        assert 'ResourceAlreadyExistsException' in rendered
        assert 'ATTEMPTED CONFIGURATION:' in rendered
        assert '/app/handler.py.run' in rendered

    def test_delete_instrumentation_uses_dict_location_identifier(self):
        """Delete instrumentation uses dict location identifier."""
        stubber = _stub_application_signals()
        stubber.add_response(
            'delete_instrumentation_configuration',
            {'DeletionStatus': 'DELETED'},
            expected_params={
                'InstrumentationType': 'BREAKPOINT',
                'Service': 'svc',
                'Environment': 'env',
                'SignalType': 'SNAPSHOT',
                'LocationIdentifier': {'LocationHash': 'aaaabbbbccccdddd'},
            },
        )
        rendered = crud_tools.delete_instrumentation(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
        )
        stubber.assert_no_pending_responses()
        assert 'Successfully deleted BREAKPOINT instrumentation' in rendered

    def test_get_instrumentation_unwraps_configuration(self):
        """Get instrumentation unwraps configuration."""
        stubber = _stub_application_signals()
        stubber.add_response(
            'get_instrumentation_configuration',
            {
                'Configuration': {
                    'InstrumentationType': 'BREAKPOINT',
                    'Service': 'svc',
                    'Environment': 'env',
                    'SignalType': 'SNAPSHOT',
                    'LocationHash': 'aaaabbbbccccdddd',
                    'Location': {
                        'CodeLocation': {
                            'Language': 'Python',
                            'FilePath': '/app/handler.py',
                            'MethodName': 'run',
                        }
                    },
                    'CaptureConfiguration': {
                        'CodeCapture': {
                            'CaptureArguments': ['order_id'],
                            'CaptureReturn': True,
                            'CaptureStackTrace': True,
                            'CaptureLimits': {},
                        }
                    },
                    'CreatedAt': datetime(2026, 3, 9, 11, 0, 0, tzinfo=timezone.utc),
                    'Description': 'demo',
                    'ARN': 'arn:demo',
                }
            },
        )
        rendered = crud_tools.get_instrumentation(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
        )
        stubber.assert_no_pending_responses()
        assert 'INSTRUMENTATION CONFIGURATION' in rendered
        assert 'aaaabbbbccccdddd' in rendered

    def test_batch_delete_by_scope_renders_summary(self):
        """Batch delete by scope renders summary."""
        stubber = _stub_application_signals()
        stubber.add_response(
            'batch_delete_instrumentation_configurations',
            {
                'DeletedCount': 2,
                'SuccessfulDeletions': [
                    {'SignalType': 'SNAPSHOT', 'LocationHash': 'aaaabbbbccccdddd'},
                    {'SignalType': 'SNAPSHOT', 'LocationHash': '1111111111111111'},
                ],
                'Errors': [],
            },
            expected_params={
                'DeletionTarget': {
                    'Scope': {
                        'Service': 'svc',
                        'Environment': 'env',
                        'InstrumentationType': 'BREAKPOINT',
                    }
                }
            },
        )
        rendered = crud_tools.batch_delete_instrumentations_by_scope(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
        )
        stubber.assert_no_pending_responses()
        assert 'DeletedCount: 2' in rendered
        assert 'SuccessfulDeletions: 2' in rendered


class TestLocationLookupParser:
    """Test parse_lookup_inputs across supported input shapes."""

    def test_resolves_hash(self):
        """Resolves hash."""
        loc, error = location.parse_lookup_inputs(
            normalized_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
        )
        assert error is None
        assert loc is not None
        assert loc.describe() == 'LocationHash aaaabbbbccccdddd'
        assert loc.to_identifier() == {'LocationHash': 'aaaabbbbccccdddd'}

    def test_resolves_code_location(self):
        """Resolves code location."""
        loc, error = location.parse_lookup_inputs(
            normalized_type='PROBE',
            language='Python',
            file_path='/app/handler.py',
            method_name='run',
        )
        assert error is None
        assert loc is not None
        assert loc.to_identifier() == {
            'CodeLocation': {
                'Language': 'Python',
                'FilePath': '/app/handler.py',
                'MethodName': 'run',
            }
        }
        assert loc.describe() == '/app/handler.py.run'


class TestLocationVariantContracts:
    """Pin the asymmetric-by-design interface on HashLocation and UnknownLocation.

    The asymmetric-by-design interface on HashLocation and the
    forward-compat behavior on UnknownLocation, so a future refactor
    that calls these methods generically fails loudly instead of
    silently producing malformed output.
    """

    def test_hash_location_to_api_payload_raises_with_teaching_message(self):
        """Hash location to api payload raises with teaching message."""
        loc = location.HashLocation(location_hash='aaaabbbbccccdddd')
        with pytest.raises(NotImplementedError) as exc_info:
            loc.to_api_payload()
        message = str(exc_info.value)
        assert 'HashLocation cannot be used in create requests' in message
        assert 'to_identifier()' in message

    def test_hash_location_format_details_raises_with_teaching_message(self):
        """Hash location format details raises with teaching message."""
        loc = location.HashLocation(location_hash='aaaabbbbccccdddd')
        with pytest.raises(NotImplementedError) as exc_info:
            loc.format_details()
        message = str(exc_info.value)
        assert 'HashLocation has no fields to format' in message
        assert 'describe()' in message

    def test_hash_location_describe_and_identifier_still_work(self):
        """Hash location describe and identifier still work."""
        loc = location.HashLocation(location_hash='aaaabbbbccccdddd')
        assert loc.describe() == 'LocationHash aaaabbbbccccdddd'
        assert loc.to_identifier() == {'LocationHash': 'aaaabbbbccccdddd'}
        assert loc.level() is None

    def test_unknown_location_describe_returns_placeholder(self):
        """Unknown location describe returns placeholder."""
        loc = location.location_from_response({'FuturisticLocation': {'Foo': 1}})
        assert isinstance(loc, location.UnknownLocation)
        assert loc.describe() == 'N/A'
        assert loc.level() is None

    def test_unknown_location_format_details_renders_unknown_kind(self):
        """Unknown location format details renders unknown kind."""
        loc = location.location_from_response({'FuturisticLocation': {'Foo': 1}})
        rendered = loc.format_details(location_hash='aaaabbbbccccdddd')
        assert '- LocationKind: UNKNOWN' in rendered
        assert '- LocationHash: aaaabbbbccccdddd' in rendered
        assert '- FuturisticLocation: ' in rendered

    def test_unknown_location_format_details_handles_empty_payload(self):
        """Unknown location format details handles empty payload."""
        loc = location.location_from_response(None)
        assert isinstance(loc, location.UnknownLocation)
        rendered = loc.format_details()
        assert '- LocationKind: UNKNOWN' in rendered
        assert 'Location payload could not be parsed.' in rendered


class TestSignalValidationAndNormalization:
    """Test signal validation and status normalization helpers."""

    def test_validate_snapshot_signal_accepts_snapshot(self):
        """Validate snapshot signal accepts snapshot."""
        assert validation.validate_snapshot_signal('SNAPSHOT') is None

    def test_validate_snapshot_signal_rejects_span(self):
        """Validate snapshot signal rejects span."""
        error = validation.validate_snapshot_signal('SPAN')
        assert error is not None
        assert 'must be SNAPSHOT' in error


class TestProbeConstraints:
    """Test PROBE-only constraint validation."""

    def test_breakpoint_is_unconstrained(self):
        """A BREAKPOINT type returns None regardless of language/line_number."""
        assert validation.validate_probe_constraints('BREAKPOINT', 'JavaScript', 5) is None

    def test_probe_rejects_javascript(self):
        """PROBE on JavaScript is rejected."""
        error = validation.validate_probe_constraints('PROBE', 'JavaScript', None)
        assert error is not None
        assert 'PROBE is not supported for JavaScript' in error

    def test_probe_rejects_line_number(self):
        """PROBE with a line_number is rejected (the SDKs ignore it)."""
        error = validation.validate_probe_constraints('PROBE', 'Python', 42)
        assert error is not None
        assert 'PROBE does not support line_number' in error

    def test_valid_probe_passes(self):
        """A method-level PROBE on a supported language passes."""
        assert validation.validate_probe_constraints('PROBE', 'Python', None) is None

    def test_create_probe_javascript_rejected_end_to_end(self):
        """create_instrumentation rejects a PROBE on JavaScript before any API call."""
        rendered = crud_tools.create_instrumentation(
            instrumentation_type='PROBE',
            service='svc',
            environment='env',
            language='JavaScript',
            file_path='/app/handler.js',
            line_number=10,
            capture_locals=['total'],
        )
        assert 'PROBE is not supported for JavaScript' in rendered

    def test_create_probe_with_line_number_rejected_end_to_end(self):
        """create_instrumentation rejects a PROBE with line_number before any API call."""
        rendered = crud_tools.create_instrumentation(
            instrumentation_type='PROBE',
            service='svc',
            environment='env',
            language='Python',
            file_path='/app/handler.py',
            code_unit='services.handler',
            method_name='run',
            line_number=42,
            capture_arguments=['order_id'],
        )
        assert 'PROBE does not support line_number' in rendered


class TestBatchDeleteFormatting:
    """Test batch-delete response rendering."""

    def test_batch_delete_response_includes_success_and_errors(self):
        """Batch delete response includes success and errors."""
        rendered = crud_rendering._format_batch_delete_response(
            mode='ResourceArns',
            instrumentation_type='BREAKPOINT',
            data={
                'DeletedCount': 1,
                'SuccessfulDeletions': [
                    {
                        'ResourceArn': (
                            'arn:aws:application-signals:us-west-1:123456789012:'
                            'instrumentationConfig/svc/env/SNAPSHOT/aaaabbbbccccdddd'
                        )
                    }
                ],
                'Errors': [
                    {
                        'ResourceArn': (
                            'arn:aws:application-signals:us-west-1:123456789012:'
                            'instrumentationConfig/svc/env/SNAPSHOT/1111111111111111'
                        ),
                        'Code': 'ResourceNotFoundException',
                        'Message': 'not found',
                    }
                ],
            },
        )
        assert 'DeletedCount: 1' in rendered
        assert 'SuccessfulDeletions: 1' in rendered
        assert 'Errors: 1' in rendered
        assert 'ResourceNotFoundException' in rendered


class TestCrudRenderingHelpers:
    """Test CRUD response renderers."""

    def test_render_list_output_formats_boto3_datetimes_in_iso_format(self):
        """Datetime timestamps render in the original CLI shape.

        boto3 returns timestamps as ``datetime`` objects; the renderer must
        emit them in the original CLI's ``YYYY-MM-DDTHH:MM:SSZ`` shape so MCP
        clients see no contract change.
        """
        rendered = crud_rendering.render_list_instrumentations_output(
            data={
                'SyncedAt': datetime(2026, 3, 9, 12, 0, 0, tzinfo=timezone.utc),
                'LatestConfigurations': [
                    {
                        'LocationHash': 'aaaabbbbccccdddd',
                        'Location': {'CodeLocation': {'Language': 'Python', 'FilePath': '/x.py'}},
                        'CaptureConfiguration': {'CodeCapture': {'CaptureLimits': {}}},
                        'CreatedAt': datetime(2026, 3, 9, 11, 0, 0, tzinfo=timezone.utc),
                        'ExpiresAt': datetime(2026, 3, 10, 11, 0, 0, tzinfo=timezone.utc),
                        'ARN': 'arn:demo',
                    }
                ],
            },
            normalized_type='BREAKPOINT',
            service='svc',
            environment='env',
        )
        assert 'Synced At: 2026-03-09T12:00:00Z' in rendered
        assert '- Created: 2026-03-09T11:00:00Z' in rendered
        assert '- Expires: 2026-03-10T11:00:00Z' in rendered

    def test_render_list_output_includes_location_and_limits(self):
        """Render list output includes location and limits."""
        rendered = crud_rendering.render_list_instrumentations_output(
            data={
                'SyncedAt': '2026-03-09T12:00:00Z',
                'LatestConfigurations': [
                    {
                        'LocationHash': 'aaaabbbbccccdddd',
                        'Location': {
                            'CodeLocation': {
                                'Language': 'Python',
                                'FilePath': '/app/handler.py',
                                'MethodName': 'run',
                            }
                        },
                        'CaptureConfiguration': {
                            'CodeCapture': {
                                'CaptureArguments': ['order_id'],
                                'CaptureReturn': True,
                                'CaptureStackTrace': False,
                                'CaptureLocals': ['result'],
                                'CaptureLimits': {
                                    'MaxHits': 3,
                                    'MaxStringLength': 128,
                                    'MaxCollectionWidth': 10,
                                },
                            }
                        },
                        'CreatedAt': '2026-03-09T11:00:00Z',
                        'ExpiresAt': '2026-03-10T11:00:00Z',
                        'Description': 'demo',
                        'ARN': 'arn:demo',
                    }
                ],
            },
            normalized_type='BREAKPOINT',
            service='svc',
            environment='env',
        )
        assert 'Active BREAKPOINT Instrumentations (1 found)' in rendered
        assert 'LocationHash: aaaabbbbccccdddd' in rendered
        assert '- Level: FUNCTION/METHOD-LEVEL' in rendered
        assert '- Limits: MaxHits=3, MaxStringLen=128, MaxCollWidth=10' in rendered

    def test_render_get_output_includes_attribute_filters_and_metadata(self):
        """Render get output includes attribute filters and metadata."""
        rendered = crud_rendering.render_get_instrumentation_output(
            config={
                'InstrumentationType': 'BREAKPOINT',
                'SignalType': 'SNAPSHOT',
                'LocationHash': 'aaaabbbbccccdddd',
                'Location': {
                    'CodeLocation': {
                        'Language': 'Python',
                        'FilePath': '/app/handler.py',
                        'MethodName': 'run',
                    }
                },
                'CaptureConfiguration': {
                    'CodeCapture': {
                        'CaptureArguments': [],
                        'CaptureReturn': True,
                        'CaptureStackTrace': True,
                        'CaptureLimits': {
                            'MaxCollectionDepth': 4,
                            'MaxObjectDepth': 2,
                        },
                    }
                },
                'AttributeFilters': [{'Key': 'stage', 'Value': 'prod'}],
                'Description': 'demo',
                'CreatedAt': '2026-03-09T11:00:00Z',
                'ExpiresAt': 'Never',
                'ARN': 'arn:demo',
            },
            service='svc',
            environment='env',
        )
        assert 'INSTRUMENTATION CONFIGURATION' in rendered
        assert '- Arguments: (empty list)' in rendered
        assert '- Max Collection Depth: 4' in rendered
        assert '- Max Object Depth: 2' in rendered
        assert 'ATTRIBUTE FILTERS: 1 filter group(s)' in rendered
        assert '- ARN: arn:demo' in rendered


class TestStatusRenderingHelpers:
    """Test status response renderers."""

    def test_render_get_status_output_includes_confirmation_and_pagination(self):
        """Render get status output includes confirmation and pagination."""
        rendered = status_rendering.render_get_instrumentation_configuration_status_output(
            data={
                'Service': 'svc',
                'Environment': 'env',
                'SignalType': 'SNAPSHOT',
                'Status': 'READY',
                'LocationHash': 'aaaabbbbccccdddd',
                'Location': {
                    'CodeLocation': {
                        'Language': 'Python',
                        'FilePath': '/app/handler.py',
                        'MethodName': 'run',
                    }
                },
                'Events': [{'Time': '2026-03-09T12:00:00Z'}],
                'NextToken': 'next-page',
            },
            normalized_type='BREAKPOINT',
            service='svc',
            environment='env',
            requested_status='READY',
        )
        assert 'REQUESTED STATUS FILTER: READY' in rendered
        assert 'Status Confirmation: CONFIRMED' in rendered
        assert '- Level: FUNCTION/METHOD-LEVEL' in rendered
        assert 'next_token="next-page"' in rendered

    def test_render_consolidated_error_output_includes_troubleshooting(self):
        """Render consolidated error output includes troubleshooting."""
        rendered = status_rendering.render_consolidated_error_or_pending_status_output(
            location_hash='aaaabbbbccccdddd',
            service='svc',
            environment='env',
            normalized_type='BREAKPOINT',
            created_at='2026-03-09T11:00:00Z',
            requested_start_str='2026-03-09T11:05:00Z',
            active_query_start_str='2026-03-09T11:05:00Z',
            query_end_str='2026-03-09T11:10:00Z',
            active_has_events=False,
            active_events=[],
            active_error=None,
            ready_has_events=False,
            ready_events=[],
            ready_error=None,
            error_has_events=True,
            error_events=[{'Time': '2026-03-09T11:06:00Z', 'ErrorCause': 'METHOD_NOT_FOUND'}],
            error_error=None,
        )
        assert 'ERROR STATUS:' in rendered
        assert 'OVERALL STATUS: ERROR (METHOD_NOT_FOUND)' in rendered
        assert 'Verify method_name and code_unit are correct' in rendered


class TestSnapshotHelpers:
    """Test snapshot parsing and rendering helpers."""

    def test_parse_snapshot_fields_extracts_core_fields(self):
        """Parse snapshot fields extracts core fields."""
        rendered = snapshot_parsing._parse_snapshot_fields(
            {
                '@timestamp': '2026-03-09T12:00:00Z',
                '@message': json.dumps(
                    {
                        'timeUnixNano': 1762689600000000000,
                        'traceId': 'trace-123',
                        'attributes': {
                            'event.name': 'aws.dynamic_instrumentation.snapshot',
                            'aws.di.snapshot_id': 'snap-1',
                            'aws.di.location_hash': 'aaaabbbbccccdddd',
                            'aws.di.instrumentation_level': 'method',
                            'aws.di.method_name': 'run',
                            'aws.di.duration_ms': 42,
                        },
                        'body': {
                            'captures': {
                                'entry': {
                                    'arguments': {'order_id': {'type': 'str', 'value': 'A-1'}}
                                },
                                'return': {'return_value': {'type': 'int', 'value': '1'}},
                            },
                        },
                    }
                ),
            }
        )
        assert rendered['snapshot_id'] == 'snap-1'
        assert rendered['duration_ms'] == 42
        assert rendered['entry_argument_names'] == ['order_id']
        assert rendered['return_value']['value'] == '1'

    def test_parse_snapshot_fields_handles_absent_body(self):
        """Missing snapshot body degrades gracefully.

        Per spec, `body` is absent when the agent produced no stack/captures.
        The parser must degrade gracefully without raising.
        """
        rendered = snapshot_parsing._parse_snapshot_fields(
            {
                '@timestamp': '2026-03-09T12:00:00Z',
                '@message': json.dumps(
                    {
                        'timeUnixNano': 1762689600000000000,
                        'attributes': {
                            'event.name': 'aws.dynamic_instrumentation.snapshot',
                            'aws.di.snapshot_id': 'snap-nobody',
                            'aws.di.location_hash': 'aaaabbbbccccdddd',
                            'aws.di.instrumentation_level': 'method',
                            'aws.di.method_name': 'run',
                        },
                    }
                ),
            }
        )
        assert rendered['snapshot_id'] == 'snap-nobody'
        assert rendered['stack_preview'] == []
        assert rendered['stack_frame_count'] == 0
        assert rendered['entry_argument_names'] == []
        assert rendered['entry_local_names'] == []
        assert rendered['return_value'] is None
        assert rendered['line_numbers'] == []

    def test_render_sample_snapshot_output_includes_suggested_filters(self):
        """Render sample snapshot output includes suggested filters."""
        rendered = snapshot_rendering.render_get_sample_snapshot_for_breakpoint_output(
            service_name='svc',
            environment='env',
            location_hash='aaaabbbbccccdddd',
            start_time_utc='2026-03-09T11:59:55Z',
            end_time_utc='2026-03-09T12:01:00Z',
            max_timeout=30,
            query_string='fields @timestamp, @message | limit 1',
            query_result={
                'status': 'Complete',
                'queryId': 'query-123',
                'results': [
                    {
                        '@timestamp': '2026-03-09T12:00:00Z',
                        '@message': json.dumps(
                            {
                                'timeUnixNano': 1762689600000000000,
                                'traceId': 'trace-123',
                                'attributes': {
                                    'event.name': 'aws.dynamic_instrumentation.snapshot',
                                    'aws.di.snapshot_id': 'snap-1',
                                    'aws.di.location_hash': 'aaaabbbbccccdddd',
                                    'aws.di.instrumentation_level': 'method',
                                    'aws.di.method_name': 'run',
                                },
                                'body': {
                                    'captures': {
                                        'entry': {
                                            'arguments': {
                                                'order_id': {'type': 'str', 'value': 'A-1'}
                                            }
                                        },
                                    },
                                },
                            }
                        ),
                    }
                ],
                'messages': [],
            },
        )
        parsed = json.loads(rendered)
        assert parsed['status'] == 'SUCCESS'
        assert parsed['sample_snapshot']['attributes']['aws.di.snapshot_id'] == 'snap-1'
        assert parsed['field_documentation']
        assert 'attributes.aws.di.location_hash' in parsed['field_documentation']


class TestGetInstrumentationConfigurationStatusTool:
    """Stubber-driven coverage for the get-status tool entrypoint."""

    def test_requires_status_argument(self):
        """Omitting status returns the explicit-status guidance, not an API call."""
        rendered = status_tools.get_instrumentation_configuration_status(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
        )
        assert 'status is required' in rendered

    def test_rejects_invalid_status(self):
        """An out-of-enum status is rejected before any API call."""
        rendered = status_tools.get_instrumentation_configuration_status(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
            status='WAT',
        )
        assert 'invalid status' in rendered

    def test_requires_location_identifier(self):
        """Without a location identifier, the tool returns usage help."""
        rendered = status_tools.get_instrumentation_configuration_status(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            status='READY',
        )
        assert 'Must provide one of' in rendered

    def test_renders_confirmed_status_with_events(self):
        """A READY response with events renders a CONFIRMED report."""
        stubber = _stub_application_signals()
        stubber.add_response(
            'get_instrumentation_configuration_status',
            {
                'Service': 'svc',
                'Environment': 'env',
                'SignalType': 'SNAPSHOT',
                'Location': {
                    'CodeLocation': {
                        'Language': 'Python',
                        'FilePath': '/app/handler.py',
                        'MethodName': 'run',
                    }
                },
                'Status': 'READY',
                'Events': [{'Time': datetime(2026, 3, 9, 12, 0, 0, tzinfo=timezone.utc)}],
            },
            expected_params={
                'InstrumentationType': 'BREAKPOINT',
                'Service': 'svc',
                'Environment': 'env',
                'SignalType': 'SNAPSHOT',
                'Status': 'READY',
                'LocationIdentifier': {'LocationHash': 'aaaabbbbccccdddd'},
            },
        )
        rendered = status_tools.get_instrumentation_configuration_status(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
            status='READY',
        )
        stubber.assert_no_pending_responses()
        assert 'INSTRUMENTATION STATUS' in rendered
        assert 'CONFIRMED' in rendered
        assert 'Events Returned: 1' in rendered

    def test_translates_client_error_with_attempted_block(self):
        """A backend error renders the attempted-retrieval block."""
        stubber = _stub_application_signals()
        stubber.add_client_error(
            'get_instrumentation_configuration_status',
            service_error_code='ResourceNotFoundException',
            service_message='no such config',
        )
        rendered = status_tools.get_instrumentation_configuration_status(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
            status='READY',
        )
        assert 'ATTEMPTED TO RETRIEVE:' in rendered
        assert 'ResourceNotFoundException' in rendered

    def test_rejects_invalid_instrumentation_type(self):
        """An invalid instrumentation_type is rejected before any API call."""
        rendered = status_tools.get_instrumentation_configuration_status(
            service='svc',
            environment='env',
            instrumentation_type='WATCHER',
            location_hash='aaaabbbbccccdddd',
            status='READY',
        )
        assert 'instrumentation_type must be one of' in rendered

    def test_rejects_invalid_signal_type(self):
        """A non-SNAPSHOT signal_type is rejected before any API call."""
        rendered = status_tools.get_instrumentation_configuration_status(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
            status='READY',
            signal_type='METRIC',
        )
        assert 'must be SNAPSHOT' in rendered

    def test_rejects_invalid_start_time(self):
        """A malformed start_time is rejected before any API call."""
        rendered = status_tools.get_instrumentation_configuration_status(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
            status='READY',
            start_time='nope',
        )
        assert 'Invalid start_time format' in rendered

    def test_rejects_invalid_end_time(self):
        """A malformed end_time is rejected before any API call."""
        rendered = status_tools.get_instrumentation_configuration_status(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
            status='READY',
            start_time='2026-03-09T12:00:00Z',
            end_time='nope',
        )
        assert 'Invalid end_time format' in rendered

    def test_forwards_optional_params_and_renders_pagination(self):
        """Optional time/paging params are forwarded; a NextToken yields pagination hint."""
        stubber = _stub_application_signals()
        stubber.add_response(
            'get_instrumentation_configuration_status',
            {
                'Service': 'svc',
                'Environment': 'env',
                'SignalType': 'SNAPSHOT',
                'Location': {
                    'CodeLocation': {'Language': 'Python', 'FilePath': '/app/handler.py'}
                },
                'Status': 'ACTIVE',
                'Events': [],
                'NextToken': 'next-page-token',
            },
            expected_params={
                'InstrumentationType': 'BREAKPOINT',
                'Service': 'svc',
                'Environment': 'env',
                'SignalType': 'SNAPSHOT',
                'Status': 'ACTIVE',
                'LocationIdentifier': {'LocationHash': 'aaaabbbbccccdddd'},
                'StartTime': datetime(2026, 3, 9, 12, 0, 0, tzinfo=timezone.utc),
                'EndTime': datetime(2026, 3, 9, 12, 5, 0, tzinfo=timezone.utc),
                'MaxResults': 5,
                'NextToken': 'prev-token',
            },
        )
        rendered = status_tools.get_instrumentation_configuration_status(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
            status='ACTIVE',
            start_time='2026-03-09T12:00:00Z',
            end_time='2026-03-09T12:05:00Z',
            max_results=5,
            next_token='prev-token',
        )
        stubber.assert_no_pending_responses()
        # ACTIVE with no events triggers the clarification block and pagination hint.
        assert 'ACTIVE Clarification' in rendered
        assert 'next-page-token' in rendered


def _full_instrumentation_configuration() -> dict:
    """A Configuration block with every field the bundled model marks required."""
    return {
        'InstrumentationType': 'BREAKPOINT',
        'Service': 'svc',
        'Environment': 'env',
        'SignalType': 'SNAPSHOT',
        'Location': {
            'CodeLocation': {
                'Language': 'Python',
                'FilePath': '/app/handler.py',
                'MethodName': 'run',
            }
        },
        'LocationHash': 'aaaabbbbccccdddd',
        'CaptureConfiguration': {
            'CodeCapture': {
                'CaptureArguments': ['order_id'],
                'CaptureReturn': True,
                'CaptureStackTrace': True,
                'CaptureLimits': {},
            }
        },
        'CreatedAt': datetime(2026, 3, 9, 11, 0, 0, tzinfo=timezone.utc),
        'ARN': 'arn:demo',
    }


class TestCheckInstrumentationStatusTool:
    """Stubber-driven coverage for the consolidated status-check tool."""

    def test_rejects_bad_location_hash_length(self):
        """A non-16-character location hash is rejected before any API call."""
        rendered = status_tools.check_instrumentation_status(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='short',
            start_time='2026-03-09T12:00:00Z',
            end_time='2026-03-09T12:05:00Z',
        )
        assert 'location_hash must be a 16-character' in rendered

    def test_rejects_end_before_start(self):
        """end_time must be later than start_time; this is caught after config fetch."""
        stubber = _stub_application_signals()
        stubber.add_response(
            'get_instrumentation_configuration',
            {'Configuration': _full_instrumentation_configuration()},
        )
        rendered = status_tools.check_instrumentation_status(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
            start_time='2026-03-09T12:05:00Z',
            end_time='2026-03-09T12:00:00Z',
        )
        assert 'end_time must be later than start_time' in rendered

    def test_config_fetch_error_reports_failure(self):
        """A backend error fetching the configuration surfaces a created_at failure."""
        stubber = _stub_application_signals()
        stubber.add_client_error(
            'get_instrumentation_configuration',
            service_error_code='ResourceNotFoundException',
            service_message='no such config',
        )
        rendered = status_tools.check_instrumentation_status(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
            start_time='2026-03-09T12:00:00Z',
            end_time='2026-03-09T12:05:00Z',
        )
        assert 'Failed to fetch created_at' in rendered

    def test_active_verdict_renders_when_active_events_present(self):
        """A populated ACTIVE check yields an ACTIVE consolidated assessment."""
        stubber = _stub_application_signals()
        stubber.add_response(
            'get_instrumentation_configuration',
            {'Configuration': _full_instrumentation_configuration()},
        )
        # The consolidated check queries ACTIVE first; one event short-circuits to ACTIVE.
        stubber.add_response(
            'get_instrumentation_configuration_status',
            {
                'Service': 'svc',
                'Environment': 'env',
                'SignalType': 'SNAPSHOT',
                'Location': {'CodeLocation': {'Language': 'Python', 'FilePath': '/app/h.py'}},
                'Status': 'ACTIVE',
                'Events': [{'Time': datetime(2026, 3, 9, 12, 1, 0, tzinfo=timezone.utc)}],
            },
        )
        rendered = status_tools.check_instrumentation_status(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
            start_time='2026-03-09T12:00:00Z',
            end_time='2026-03-09T12:05:00Z',
        )
        stubber.assert_no_pending_responses()
        assert 'ACTIVE' in rendered

    def test_rejects_invalid_instrumentation_type(self):
        """An invalid instrumentation_type is rejected before any API call."""
        rendered = status_tools.check_instrumentation_status(
            service='svc',
            environment='env',
            instrumentation_type='WATCHER',
            location_hash='aaaabbbbccccdddd',
            start_time='2026-03-09T12:00:00Z',
            end_time='2026-03-09T12:05:00Z',
        )
        assert 'instrumentation_type must be one of' in rendered

    def test_rejects_invalid_signal_type(self):
        """A non-SNAPSHOT signal_type is rejected before any API call."""
        rendered = status_tools.check_instrumentation_status(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
            start_time='2026-03-09T12:00:00Z',
            end_time='2026-03-09T12:05:00Z',
            signal_type='METRIC',
        )
        assert 'must be SNAPSHOT' in rendered

    def test_rejects_invalid_start_time(self):
        """A malformed start_time is rejected after the config fetch succeeds."""
        stubber = _stub_application_signals()
        stubber.add_response(
            'get_instrumentation_configuration',
            {'Configuration': _full_instrumentation_configuration()},
        )
        rendered = status_tools.check_instrumentation_status(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
            start_time='nope',
            end_time='2026-03-09T12:05:00Z',
        )
        assert 'Invalid start_time format' in rendered

    def test_rejects_invalid_end_time(self):
        """A malformed end_time is rejected after the config fetch succeeds."""
        stubber = _stub_application_signals()
        stubber.add_response(
            'get_instrumentation_configuration',
            {'Configuration': _full_instrumentation_configuration()},
        )
        rendered = status_tools.check_instrumentation_status(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
            start_time='2026-03-09T12:00:00Z',
            end_time='nope',
        )
        assert 'Invalid end_time format' in rendered


class TestSnapshotToolsCloudWatchPath:
    """Cover the snapshot tool entrypoints by stubbing the parent logs client.

    The parent ``logs_client`` is a module-level singleton, so each test uses
    ``Stubber`` as a context manager to guarantee it deactivates before the next
    test stubs the same client.
    """

    def test_search_rejects_bad_timestamp(self):
        """A non-ISO status_timestamp returns a usage error before querying."""
        rendered = snapshot_tools.search_snapshots_for_status_event(
            service_name='svc',
            environment='env',
            location_hash='aaaabbbbccccdddd',
            status_timestamp='not-a-timestamp',
        )
        assert 'ISO 8601 format' in rendered

    def test_search_renders_results_from_logs_insights(self):
        """A completed Logs Insights query renders snapshot summaries as JSON."""
        with Stubber(parent_aws_clients.logs_client) as stubber:
            stubber.add_response('start_query', {'queryId': 'q-1'})
            stubber.add_response(
                'get_query_results',
                {
                    'status': 'Complete',
                    'results': [
                        [
                            {'field': '@timestamp', 'value': '2026-03-09 12:00:00.000'},
                            {
                                'field': '@message',
                                'value': json.dumps(
                                    {
                                        'traceId': 'trace-1',
                                        'attributes': {
                                            'aws.di.snapshot_id': 'snap-1',
                                            'aws.di.location_hash': 'aaaabbbbccccdddd',
                                        },
                                    }
                                ),
                            },
                        ]
                    ],
                },
            )
            rendered = snapshot_tools.search_snapshots_for_status_event(
                service_name='svc',
                environment='env',
                location_hash='aaaabbbbccccdddd',
                status_timestamp='2026-03-09T12:00:00Z',
            )
            stubber.assert_no_pending_responses()
        parsed = json.loads(rendered)
        assert parsed['status'] == 'Complete'
        assert parsed['snapshot_summaries'][0]['snapshot_id'] == 'snap-1'

    def test_search_renders_error_when_start_query_fails(self):
        """A start_query ClientError surfaces as a structured ERROR response."""
        with Stubber(parent_aws_clients.logs_client) as stubber:
            stubber.add_client_error(
                'start_query',
                service_error_code='ResourceNotFoundException',
                service_message='no log group',
            )
            rendered = snapshot_tools.search_snapshots_for_status_event(
                service_name='svc',
                environment='env',
                location_hash='aaaabbbbccccdddd',
                status_timestamp='2026-03-09T12:00:00Z',
            )
        parsed = json.loads(rendered)
        assert parsed['status'] == 'ERROR'
        assert 'Failed to start query' in parsed['error']

    def test_sample_rejects_bad_timestamp(self):
        """get_sample_snapshot_for_breakpoint validates the timestamp too."""
        rendered = snapshot_tools.get_sample_snapshot_for_breakpoint(
            service_name='svc',
            environment='env',
            location_hash='aaaabbbbccccdddd',
            status_timestamp='nope',
        )
        assert 'ISO 8601 format' in rendered

    def test_sample_renders_single_snapshot(self):
        """A single completed result renders a SUCCESS sample-snapshot response."""
        with Stubber(parent_aws_clients.logs_client) as stubber:
            stubber.add_response('start_query', {'queryId': 'q-2'})
            stubber.add_response(
                'get_query_results',
                {
                    'status': 'Complete',
                    'results': [
                        [
                            {'field': '@timestamp', 'value': '2026-03-09 12:00:00.000'},
                            {
                                'field': '@message',
                                'value': json.dumps(
                                    {
                                        'traceId': 'trace-1',
                                        'attributes': {
                                            'event.name': 'aws.dynamic_instrumentation.snapshot',
                                            'aws.di.snapshot_id': 'snap-1',
                                            'aws.di.location_hash': 'aaaabbbbccccdddd',
                                        },
                                    }
                                ),
                            },
                        ]
                    ],
                },
            )
            rendered = snapshot_tools.get_sample_snapshot_for_breakpoint(
                service_name='svc',
                environment='env',
                location_hash='aaaabbbbccccdddd',
                status_timestamp='2026-03-09T12:00:00Z',
                include_raw=True,
            )
            stubber.assert_no_pending_responses()
        parsed = json.loads(rendered)
        assert parsed['status'] == 'SUCCESS'
        assert parsed['sample_snapshot']['attributes']['aws.di.snapshot_id'] == 'snap-1'


class TestCodeInstrumentationArgumentContract:
    """Test code-instrumentation-specific guardrails."""

    def test_create_rejects_empty_capture_arguments_list(self):
        """An explicit empty capture_arguments list is rejected (omit to capture none)."""
        rendered = crud_tools.create_instrumentation(
            instrumentation_type='BREAKPOINT',
            service='svc',
            environment='env',
            language='Python',
            file_path='/app/demo_app.py',
            code_unit='__main__',
            method_name='process_payment',
            capture_arguments=[],
        )
        assert 'capture_arguments must contain at least one name' in rendered

    def test_create_rejects_empty_capture_locals_list(self):
        """An explicit empty capture_locals list is rejected (omit to capture none)."""
        rendered = crud_tools.create_instrumentation(
            instrumentation_type='BREAKPOINT',
            service='svc',
            environment='env',
            language='Python',
            file_path='/app/demo_app.py',
            code_unit='__main__',
            method_name='process_payment',
            capture_arguments=['order_id'],
            capture_locals=[],
        )
        assert 'capture_locals must contain at least one name' in rendered

    def test_create_line_level_requires_capture_locals(self):
        """A line-level config (line_number set) without capture_locals is rejected."""
        rendered = crud_tools.create_instrumentation(
            instrumentation_type='BREAKPOINT',
            service='svc',
            environment='env',
            language='Python',
            file_path='/app/demo_app.py',
            code_unit='services.demo',
            method_name='process_payment',
            line_number=42,
            capture_arguments=['order_id'],
        )
        assert 'line-level instrumentation (line_number set) requires capture_locals' in rendered

    def test_code_capture_preserves_explicit_empty_argument_list(self):
        """Code capture preserves explicit empty argument list."""
        cap = capture.CodeCapture(
            capture_return=True,
            capture_stack_trace=True,
            capture_arguments=[],
        )
        payload = cap.to_api_payload()
        assert 'CodeCapture' in payload
        assert 'CaptureArguments' in payload['CodeCapture']
        assert payload['CodeCapture']['CaptureArguments'] == []


class TestToolRegistration:
    """Test MCP registration for the dynamic instrumentation surface."""

    def test_register_tools_registers_dynamic_instrumentation_surface(self):
        """Register tools registers dynamic instrumentation surface."""
        recorder = RecorderMCP()

        registration.register_tools(recorder)

        assert recorder.registered == [
            'create_instrumentation',
            'list_instrumentations',
            'get_instrumentation',
            'delete_instrumentation',
            'batch_delete_instrumentations_by_scope',
            'batch_delete_instrumentations_by_arns',
            'get_instrumentation_configuration_status',
            'check_instrumentation_status',
            'search_snapshots_for_status_event',
            'get_sample_snapshot_for_breakpoint',
        ]

    def test_read_only_tools_are_annotated_read_only(self):
        """Read-only tools carry ``readOnlyHint=True`` for MCP clients."""
        recorder = RecorderMCP()

        registration.register_tools(recorder)

        for name in (
            'list_instrumentations',
            'get_instrumentation',
            'get_instrumentation_configuration_status',
            'check_instrumentation_status',
            'search_snapshots_for_status_event',
            'get_sample_snapshot_for_breakpoint',
        ):
            assert recorder.annotations[name].readOnlyHint is True

    def test_destructive_tools_are_annotated_destructive(self):
        """Delete tools carry ``destructiveHint=True`` so clients can warn first."""
        recorder = RecorderMCP()

        registration.register_tools(recorder)

        for name in (
            'delete_instrumentation',
            'batch_delete_instrumentations_by_scope',
            'batch_delete_instrumentations_by_arns',
        ):
            annotations = recorder.annotations[name]
            assert annotations.readOnlyHint is False
            assert annotations.destructiveHint is True
            assert annotations.idempotentHint is True

    def test_create_tool_is_state_changing_but_not_destructive(self):
        """create_instrumentation is a write, not a read and not destructive."""
        recorder = RecorderMCP()

        registration.register_tools(recorder)

        annotations = recorder.annotations['create_instrumentation']
        assert annotations.readOnlyHint is False
        assert annotations.destructiveHint is False
        assert annotations.idempotentHint is False

    def test_every_tool_is_annotated_open_world(self):
        """Every tool calls the AWS API, so all carry ``openWorldHint=True``."""
        recorder = RecorderMCP()

        registration.register_tools(recorder)

        for name in recorder.registered:
            assert recorder.annotations[name].openWorldHint is True


class TestSnapshotLogGroupResolution:
    """Test per-service snapshot log group resolution."""

    def test_substitutes_service_name(self):
        """The template is filled with the target service name."""
        assert (
            constants.resolve_snapshot_log_group('checkout-service')
            == '/aws/service-events/checkout-service'
        )


class TestSnapshotParsingPreviewHelper:
    """Direct coverage for snapshot_parsing._preview_captured_value."""

    def test_non_dict_returns_input_unchanged(self):
        """A non-dict captured value is returned verbatim."""
        assert snapshot_parsing._preview_captured_value('plain') == 'plain'
        assert snapshot_parsing._preview_captured_value(7) == 7

    def test_is_null_short_circuits(self):
        """is_null=True yields just type and is_null."""
        preview = snapshot_parsing._preview_captured_value(
            {'type': 'str', 'is_null': True, 'value': 'ignored'}
        )
        assert preview == {'type': 'str', 'is_null': True}

    def test_not_captured_reason_short_circuits(self):
        """not_captured_reason short-circuits with its reason."""
        preview = snapshot_parsing._preview_captured_value(
            {'type': 'obj', 'not_captured_reason': 'depth'}
        )
        assert preview == {'type': 'obj', 'not_captured_reason': 'depth'}

    def test_value_with_truncated_and_size(self):
        """A primitive value carries truncated and size flags."""
        preview = snapshot_parsing._preview_captured_value(
            {'type': 'str', 'value': 'abc', 'truncated': True, 'size': 99}
        )
        assert preview == {'type': 'str', 'value': 'abc', 'truncated': True, 'size': 99}

    def test_fields_preview_expands_one_level(self):
        """Fields preview expands primitives and collapses nested objects."""
        preview = snapshot_parsing._preview_captured_value(
            {
                'type': 'Order',
                'size': 4,
                'fields': {
                    'id': {'type': 'str', 'value': 'A-1'},
                    'missing': {'type': 'str', 'is_null': True},
                    'skipped': {'type': 'obj', 'not_captured_reason': 'timeout'},
                    'nested': {'type': 'Address'},
                    'raw': 'literal',
                },
            }
        )
        assert isinstance(preview, dict)
        assert preview['type'] == 'Order'
        assert preview['size'] == 4
        fp = preview['fields_preview']
        assert isinstance(fp, dict)
        assert fp['id'] == 'A-1'
        assert fp['missing'] is None
        assert fp['skipped'] == '<timeout>'
        assert fp['nested'] == '<Address>'
        assert fp['raw'] == 'literal'

    def test_elements_preview_summarizes_first_element(self):
        """Elements preview reports count and previews the first element."""
        preview = snapshot_parsing._preview_captured_value(
            {
                'type': 'list',
                'elements': [
                    {'type': 'int', 'value': '1'},
                    {'type': 'int', 'value': '2'},
                ],
            }
        )
        assert isinstance(preview, dict)
        assert preview['element_count'] == 2
        assert preview['first_element'] == {'type': 'int', 'value': '1'}

    def test_empty_elements_omits_first_element(self):
        """An empty elements list reports count zero and no first_element."""
        preview = snapshot_parsing._preview_captured_value({'type': 'list', 'elements': []})
        assert isinstance(preview, dict)
        assert preview['element_count'] == 0
        assert 'first_element' not in preview

    def test_entries_preview_reports_count(self):
        """Entries preview reports the entry count."""
        preview = snapshot_parsing._preview_captured_value(
            {'type': 'dict', 'entries': [{'key': 1}, {'key': 2}]}
        )
        assert isinstance(preview, dict)
        assert preview['entry_count'] == 2

    def test_bare_type_only_returns_preview(self):
        """A captured value with only a type returns the type preview."""
        preview = snapshot_parsing._preview_captured_value({'type': 'CustomObject'})
        assert preview == {'type': 'CustomObject'}

    def test_empty_dict_returns_original(self):
        """An empty dict (no type, no value) returns the original dict."""
        assert snapshot_parsing._preview_captured_value({}) == {}


class TestSnapshotParsingFields:
    """Direct coverage for snapshot_parsing._parse_snapshot_fields edge cases."""

    def test_invalid_json_message_degrades_to_empty(self):
        """Non-JSON @message degrades to empty parsed output."""
        parsed = snapshot_parsing._parse_snapshot_fields({'@message': 'not-json{'})
        assert parsed['snapshot_id'] is None
        assert parsed['raw_snapshot'] == {}
        assert parsed['stack_frame_count'] == 0

    def test_non_dict_json_message_degrades_to_empty(self):
        """A JSON array @message degrades to empty parsed output."""
        parsed = snapshot_parsing._parse_snapshot_fields({'@message': json.dumps([1, 2, 3])})
        assert parsed['raw_snapshot'] == {}

    def test_non_dict_attributes_resource_body_are_coerced(self):
        """Non-dict attributes/resource/body fields coerce to empty dicts."""
        parsed = snapshot_parsing._parse_snapshot_fields(
            {
                '@message': json.dumps(
                    {
                        'attributes': ['not', 'a', 'dict'],
                        'resource': 'nope',
                        'body': 42,
                        'traceId': 't',
                        'spanId': 's',
                    }
                )
            }
        )
        assert parsed['snapshot_id'] is None
        assert parsed['trace'] == {'traceId': 't', 'spanId': 's'}
        assert parsed['stack_preview'] == []

    def test_non_list_stack_and_non_dict_captures_coerced(self):
        """Non-list stack and non-dict capture sub-objects coerce safely."""
        parsed = snapshot_parsing._parse_snapshot_fields(
            {
                '@message': json.dumps(
                    {
                        'body': {
                            'stack': 'not-a-list',
                            'captures': {
                                'entry': 'nope',
                                'return': 5,
                                'lines': [],
                            },
                        },
                    }
                )
            }
        )
        assert parsed['stack_frame_count'] == 0
        assert parsed['entry_argument_names'] == []
        assert parsed['return_value'] is None

    def test_stack_preview_skips_non_dict_frames_and_caps_at_five(self):
        """Stack preview skips non-dict frames and previews at most five."""
        stack: list = [
            {'file_path': f'/f{i}.py', 'function': 'fn', 'line_number': i} for i in range(7)
        ]
        stack.insert(0, 'garbage')
        parsed = snapshot_parsing._parse_snapshot_fields(
            {'@message': json.dumps({'body': {'stack': stack}})}
        )
        assert parsed['stack_frame_count'] == 8
        # stack[:5] is ['garbage', f0, f1, f2, f3]; the string frame is skipped.
        assert len(parsed['stack_preview']) == 4

    def test_entry_locals_and_return_arguments_locals(self):
        """Entry locals and return arguments/locals are previewed."""
        parsed = snapshot_parsing._parse_snapshot_fields(
            {
                '@message': json.dumps(
                    {
                        'body': {
                            'captures': {
                                'entry': {
                                    'arguments': {'a': {'type': 'int', 'value': '1'}},
                                    'locals': {'tmp': {'type': 'int', 'value': '2'}},
                                },
                                'return': {
                                    'arguments': {'a': {'type': 'int', 'value': '1'}},
                                    'locals': {'r': {'type': 'int', 'value': '3'}},
                                    'return_value': {'type': 'int', 'value': '9'},
                                    'throwable': {
                                        'type': 'ValueError',
                                        'message': 'boom',
                                        'stacktrace': [{}, {}],
                                    },
                                },
                            },
                        },
                    }
                )
            }
        )
        assert parsed['entry_local_names'] == ['tmp']
        assert parsed['return_argument_names'] == ['a']
        assert parsed['return_local_names'] == ['r']
        assert parsed['return_value']['value'] == '9'
        assert parsed['throwable']['type'] == 'ValueError'
        assert parsed['throwable']['stacktrace_frame_count'] == 2

    def test_throwable_with_non_list_stacktrace_counts_zero(self):
        """A throwable whose stacktrace is not a list reports zero frames."""
        parsed = snapshot_parsing._parse_snapshot_fields(
            {
                '@message': json.dumps(
                    {
                        'body': {
                            'captures': {
                                'return': {
                                    'throwable': {'type': 'E', 'message': 'm', 'stacktrace': 'x'}
                                }
                            }
                        }
                    }
                )
            }
        )
        assert parsed['throwable']['stacktrace_frame_count'] == 0

    def test_line_captures_with_locals_args_return_and_throwable(self):
        """Line captures aggregate locals, arguments, return values, and throwables."""
        parsed = snapshot_parsing._parse_snapshot_fields(
            {
                '@message': json.dumps(
                    {
                        'body': {
                            'captures': {
                                'lines': {
                                    'not-a-dict-line': 'skip-me',
                                    '10': {
                                        'locals': {'x': {'type': 'int', 'value': '1'}},
                                        'arguments': {'y': {'type': 'int', 'value': '2'}},
                                        'return_value': {'type': 'int', 'value': '5'},
                                        'throwable': {
                                            'type': 'IOError',
                                            'message': 'bad',
                                            'stacktrace': [{}],
                                        },
                                    },
                                    '2': {
                                        'locals': {},
                                        'arguments': {},
                                    },
                                }
                            }
                        }
                    }
                )
            }
        )
        assert parsed['line_numbers'] == ['10']
        assert parsed['line_locals']['10'] == ['x']
        assert parsed['line_arguments']['10'] == ['y']
        assert parsed['line_return_values']['10']['value'] == '5'
        assert parsed['line_throwables']['10']['type'] == 'IOError'
        assert parsed['line_throwables']['10']['stacktrace_frame_count'] == 1

    def test_line_throwable_non_list_stacktrace_counts_zero(self):
        """A line throwable with non-list stacktrace reports zero frames."""
        parsed = snapshot_parsing._parse_snapshot_fields(
            {
                '@message': json.dumps(
                    {
                        'body': {
                            'captures': {
                                'lines': {
                                    '5': {
                                        'throwable': {
                                            'type': 'E',
                                            'message': 'm',
                                            'stacktrace': 'notlist',
                                        }
                                    }
                                }
                            }
                        }
                    }
                )
            }
        )
        assert parsed['line_throwables']['5']['stacktrace_frame_count'] == 0

    def test_mixed_numeric_and_non_numeric_line_keys_sort_without_crash(self):
        """Numeric and non-numeric line keys sort with a total order, no TypeError.

        A bare ``int(v) if v.isdigit() else v`` sort key would raise TypeError
        comparing int vs str. ``'-1'.isdigit()`` is False, so a negative line
        number is the realistic trigger. Numeric keys sort first by value
        (so ``'9'`` before ``'10'``), non-numeric keys sort last lexically.
        """
        parsed = snapshot_parsing._parse_snapshot_fields(
            {
                '@message': json.dumps(
                    {
                        'body': {
                            'captures': {
                                'lines': {
                                    '10': {'locals': {'a': {'type': 'int', 'value': '1'}}},
                                    '9': {'locals': {'b': {'type': 'int', 'value': '2'}}},
                                    '-1': {'locals': {'c': {'type': 'int', 'value': '3'}}},
                                    'entry': {'locals': {'d': {'type': 'int', 'value': '4'}}},
                                }
                            }
                        }
                    }
                )
            }
        )
        assert parsed['line_numbers'] == ['9', '10', '-1', 'entry']


class TestValidationLocationInputs:
    """Direct coverage for validation._validate_location_inputs and troubleshooting."""

    def test_valid_python_location_returns_none(self):
        """A valid Python location passes validation."""
        assert (
            validation._validate_location_inputs(
                language='Python',
                file_path='/app/h.py',
                code_unit='services.billing',
                class_name=None,
                method_name='run',
                line_number=None,
            )
            is None
        )

    def test_missing_file_path_reports_error(self):
        """A missing file_path produces a required-field error."""
        message = validation._validate_location_inputs(
            language='Python',
            file_path='',
            code_unit='services.billing',
            class_name=None,
            method_name='run',
            line_number=None,
        )
        assert message is not None
        assert 'file_path is required' in message

    def test_line_number_below_one_reports_error(self):
        """A line_number below 1 produces a range error."""
        message = validation._validate_location_inputs(
            language='Python',
            file_path='/app/h.py',
            code_unit='services.billing',
            class_name=None,
            method_name='run',
            line_number=0,
        )
        assert message is not None
        assert 'line_number must be >= 1' in message

    def test_unsupported_language_reports_error(self):
        """An unsupported language produces a language error."""
        message = validation._validate_location_inputs(
            language='Ruby',
            file_path='/app/h.rb',
            code_unit=None,
            class_name=None,
            method_name='run',
            line_number=None,
        )
        assert message is not None
        assert 'language must be Python, Java, or JavaScript' in message

    def test_java_fully_qualified_class_name_errors_with_suggestion(self):
        """A fully qualified Java class_name errors and suggests a split."""
        message = validation._validate_location_inputs(
            language='Java',
            file_path='/app/Order.java',
            code_unit=None,
            class_name='com.example.OrderContext',
            method_name='run',
            line_number=None,
        )
        assert message is not None
        assert 'class_name must be simple' in message
        assert 'code_unit="com.example"' in message
        assert 'class_name="OrderContext"' in message

    def test_java_code_unit_with_slashes_adds_suggestion(self):
        """A Java code_unit with slashes adds a package-name suggestion."""
        message = validation._validate_location_inputs(
            language='Java',
            file_path='',
            code_unit='com/example/app',
            class_name='com.example.Order',
            method_name='run',
            line_number=None,
        )
        assert message is not None
        assert 'package name with dots, not a path with slashes' in message

    def test_python_code_unit_with_py_extension_adds_suggestion(self):
        """A Python code_unit ending in .py adds a module-path suggestion."""
        message = validation._validate_location_inputs(
            language='Python',
            file_path='',
            code_unit='billing.py',
            class_name=None,
            method_name='run',
            line_number=None,
        )
        assert message is not None
        assert 'module path (e.g., services.billing), not a .py filename' in message

    def test_java_missing_required_fields_reports_errors(self):
        """Java without code_unit/class_name/method_name reports each as required."""
        message = validation._validate_location_inputs(
            language='Java',
            file_path='/app/Order.java',
            code_unit=None,
            class_name=None,
            method_name=None,
            line_number=None,
        )
        assert message is not None
        assert 'Java requires code_unit' in message
        assert 'Java requires class_name' in message
        assert 'Java requires method_name' in message

    def test_python_missing_required_fields_reports_errors(self):
        """Python without code_unit/method_name reports each as required."""
        message = validation._validate_location_inputs(
            language='Python',
            file_path='/app/h.py',
            code_unit=None,
            class_name=None,
            method_name=None,
            line_number=None,
        )
        assert message is not None
        assert 'Python requires code_unit' in message
        assert 'Python requires method_name' in message

    def test_valid_javascript_line_location_returns_none(self):
        """A valid JavaScript line location (line_number set) passes validation."""
        assert (
            validation._validate_location_inputs(
                language='JavaScript',
                file_path='/app/handler.js',
                code_unit=None,
                class_name=None,
                method_name=None,
                line_number=42,
            )
            is None
        )

    def test_javascript_without_line_number_reports_error(self):
        """JavaScript without a line_number reports the line-binding requirement."""
        message = validation._validate_location_inputs(
            language='JavaScript',
            file_path='/app/handler.js',
            code_unit=None,
            class_name=None,
            method_name=None,
            line_number=None,
        )
        assert message is not None
        assert 'JavaScript requires line_number' in message

    def test_canonical_language_maps_casing(self):
        """canonical_language maps any casing to the API's enum casing, else None."""
        assert validation.canonical_language('javascript') == 'Javascript'
        assert validation.canonical_language('JavaScript') == 'Javascript'
        assert validation.canonical_language('PYTHON') == 'Python'
        assert validation.canonical_language('java') == 'Java'
        assert validation.canonical_language('ruby') is None
        assert validation.canonical_language(None) is None

    def test_troubleshooting_python_branch_renders_python_rules(self):
        """The Python troubleshooting branch renders Python-specific rules."""
        rendered = validation._format_code_location_troubleshooting(
            language='Python',
            file_path='/app/h.py',
            code_unit='services.billing',
            class_name=None,
            method_name='run',
            line_number=12,
        )
        assert 'Python rules:' in rendered
        assert 'LINE-LEVEL (L12)' in rendered
        assert 'language=Python' in rendered

    def test_troubleshooting_java_branch_renders_java_rules(self):
        """The Java troubleshooting branch renders Java-specific rules."""
        rendered = validation._format_code_location_troubleshooting(
            language='Java',
            file_path='/app/Order.java',
            code_unit='com.example',
            class_name='OrderContext',
            method_name='run',
            line_number=None,
        )
        assert 'Java rules:' in rendered
        assert 'FUNCTION/METHOD-level' in rendered

    def test_troubleshooting_javascript_branch_renders_js_rules_and_slide_note(self):
        """The JavaScript branch renders JS rules and the line-slide note for line-level."""
        rendered = validation._format_code_location_troubleshooting(
            language='JavaScript',
            file_path='/app/handler.js',
            code_unit=None,
            class_name=None,
            method_name=None,
            line_number=42,
        )
        assert 'JavaScript rules:' in rendered
        assert 'binds by file_path + line_number' in rendered
        assert 'slides to the next parseable line' in rendered
        assert 'LINE-LEVEL (L42)' in rendered

    def test_troubleshooting_python_line_level_notes_non_executable(self):
        """The Python branch warns that a non-executable line never fires."""
        rendered = validation._format_code_location_troubleshooting(
            language='Python',
            file_path='/app/h.py',
            code_unit='services.billing',
            class_name=None,
            method_name='run',
            line_number=12,
        )
        assert 'non-executable' in rendered
        assert 'never fires' in rendered


class TestCrudRenderingMoreHelpers:
    """Additional coverage for crud_rendering renderers."""

    def test_create_capture_limits_empty_returns_blank(self):
        """No limits produce an empty capture-limits block."""
        assert (
            crud_rendering._render_create_capture_limits(
                max_hits=None,
                max_string_length=None,
                max_collection_width=None,
                max_collection_depth=None,
                max_stack_frames=None,
                max_stack_trace_size=None,
                max_object_depth=None,
                max_fields_per_object=None,
            )
            == ''
        )

    def test_create_capture_limits_renders_all_set_limits(self):
        """Every populated limit renders its labeled line."""
        rendered = crud_rendering._render_create_capture_limits(
            max_hits=1,
            max_string_length=2,
            max_collection_width=3,
            max_collection_depth=4,
            max_stack_frames=5,
            max_stack_trace_size=6,
            max_object_depth=7,
            max_fields_per_object=8,
        )
        assert '- Max Hits: 1' in rendered
        assert '- Max String Length: 2' in rendered
        assert '- Max Collection Width: 3' in rendered
        assert '- Max Collection Depth: 4' in rendered
        assert '- Max Stack Frames: 5' in rendered
        assert '- Max Stack Trace Size: 6' in rendered
        assert '- Max Object Depth: 7' in rendered
        assert '- Max Fields Per Object: 8' in rendered

    def test_render_create_success_message_full(self):
        """A full create-success message renders expiry, locals, limits, and filters."""
        loc = location.CodeLocation(language='Python', file_path='/app/h.py', method_name='run')
        rendered = crud_rendering.render_create_success_message(
            response={
                'LocationHash': 'aaaabbbbccccdddd',
                'ARN': 'arn:demo',
                'CreatedAt': datetime(2026, 3, 9, 11, 0, 0, tzinfo=timezone.utc),
                'ExpiresAt': datetime(2026, 3, 10, 11, 0, 0, tzinfo=timezone.utc),
            },
            normalized_type='BREAKPOINT',
            service='svc',
            environment='env',
            location=loc,
            ttl_hours=24,
            capture_arguments=['order_id'],
            code_capture_locals=['result'],
            is_line_level=False,
            code_capture_return=True,
            code_capture_stack_trace=False,
            max_hits=3,
            max_string_length=None,
            max_collection_width=None,
            max_collection_depth=None,
            max_stack_frames=None,
            max_stack_trace_size=None,
            max_object_depth=None,
            max_fields_per_object=None,
            attribute_filters=[{'Key': 'stage', 'Value': 'prod'}],
        )
        assert 'Successfully created BREAKPOINT instrumentation' in rendered
        assert '- Expires: 2026-03-10T11:00:00Z (requested 24 hours)' in rendered
        assert '- Arguments: order_id' in rendered
        assert '- Local Variables: result' in rendered
        assert '- Return Values: Enabled' in rendered
        assert '- Stack Traces: Disabled' in rendered
        assert '- Max Hits: 3' in rendered
        assert 'ATTRIBUTE FILTERS: 1 filter group(s) applied' in rendered

    def test_render_create_success_message_never_expires_no_args(self):
        """No ExpiresAt and empty arguments render the never-expires/none paths."""
        loc = location.CodeLocation(language='Python', file_path='/app/h.py', method_name='run')
        rendered = crud_rendering.render_create_success_message(
            response={'LocationHash': 'aaaabbbbccccdddd'},
            normalized_type='BREAKPOINT',
            service='svc',
            environment='env',
            location=loc,
            ttl_hours=None,
            capture_arguments=[],
            code_capture_locals=None,
            is_line_level=False,
            code_capture_return=False,
            code_capture_stack_trace=True,
            max_hits=None,
            max_string_length=None,
            max_collection_width=None,
            max_collection_depth=None,
            max_stack_frames=None,
            max_stack_trace_size=None,
            max_object_depth=None,
            max_fields_per_object=None,
            attribute_filters=None,
        )
        assert '- Expires: Never (unless deleted)' in rendered
        assert '- Arguments: (none)' in rendered
        assert '- Return Values: Disabled' in rendered

    def test_render_list_output_capture_payload_unparseable(self):
        """A non-code capture payload renders the could-not-parse note."""
        rendered = crud_rendering.render_list_instrumentations_output(
            data={
                'SyncedAt': '2026-03-09T12:00:00Z',
                'NextToken': 'more',
                'LatestConfigurations': [
                    {
                        'LocationHash': 'aaaabbbbccccdddd',
                        'Location': {'CodeLocation': {'Language': 'Python', 'FilePath': '/x.py'}},
                        'CaptureConfiguration': {},
                        'CreatedAt': '2026-03-09T11:00:00Z',
                    }
                ],
            },
            normalized_type='BREAKPOINT',
            service='svc',
            environment='env',
        )
        assert 'Capture payload could not be parsed.' in rendered
        assert 'next_token="more"' in rendered

    def test_render_get_output_capture_payload_unparseable(self):
        """A get-instrumentation render with no code capture notes the parse failure."""
        rendered = crud_rendering.render_get_instrumentation_output(
            config={
                'InstrumentationType': 'BREAKPOINT',
                'SignalType': 'SNAPSHOT',
                'LocationHash': 'aaaabbbbccccdddd',
                'Location': {'CodeLocation': {'Language': 'Python', 'FilePath': '/x.py'}},
                'CaptureConfiguration': {},
            },
            service='svc',
            environment='env',
        )
        assert 'Capture payload could not be parsed.' in rendered

    def test_render_get_output_arguments_not_set_and_full_limits(self):
        """Omitted CaptureArguments renders '(not set)' and every populated limit renders."""
        rendered = crud_rendering.render_get_instrumentation_output(
            config={
                'InstrumentationType': 'BREAKPOINT',
                'SignalType': 'SNAPSHOT',
                'LocationHash': 'aaaabbbbccccdddd',
                'Location': {'CodeLocation': {'Language': 'Python', 'FilePath': '/x.py'}},
                'CaptureConfiguration': {
                    'CodeCapture': {
                        'CaptureReturn': True,
                        'CaptureStackTrace': True,
                        'CaptureLimits': {
                            'MaxHits': 1,
                            'MaxStringLength': 2,
                            'MaxCollectionWidth': 3,
                            'MaxCollectionDepth': 4,
                            'MaxStackFrames': 5,
                            'MaxStackTraceSize': 6,
                            'MaxObjectDepth': 7,
                            'MaxFieldsPerObject': 8,
                        },
                    }
                },
            },
            service='svc',
            environment='env',
        )
        assert '- Arguments: (not set)' in rendered
        assert '- Max Hits: 1' in rendered
        assert '- Max Stack Frames: 5' in rendered
        assert '- Max Fields Per Object: 8' in rendered

    def test_batch_delete_response_minimal_no_sections(self):
        """An empty batch-delete response renders counts without item sections."""
        rendered = crud_rendering._format_batch_delete_response(
            mode='Scope',
            instrumentation_type='BREAKPOINT',
            data={},
        )
        assert 'DeletedCount: 0' in rendered
        assert 'SUCCESSFUL DELETIONS:' not in rendered
        assert 'DELETE ERRORS:' not in rendered


class TestStatusRenderingMoreHelpers:
    """Additional coverage for status_rendering renderers."""

    def test_render_status_section_skipped_branch(self):
        """A 'Skipped:' error renders the check-skipped line."""
        rendered = status_rendering._render_status_section(
            title='READY',
            start_time='s',
            end_time='e',
            has_events=False,
            events=[],
            error='Skipped: not needed',
        )
        assert '- Check Skipped: Skipped: not needed' in rendered

    def test_render_status_section_failed_branch(self):
        """A non-skipped error renders the check-failed line."""
        rendered = status_rendering._render_status_section(
            title='READY',
            start_time='s',
            end_time='e',
            has_events=False,
            events=[],
            error='boom',
        )
        assert '- Check Failed: boom' in rendered

    def test_render_status_section_truncates_after_three_events(self):
        """More than three events render a truncation note."""
        events = [{'Time': f'2026-03-09T12:0{i}:00Z'} for i in range(5)]
        rendered = status_rendering._render_status_section(
            title='ERROR',
            start_time='s',
            end_time='e',
            has_events=True,
            events=events,
            error=None,
            include_error_cause=True,
        )
        assert '- Confirmed: YES (5 event(s))' in rendered
        assert '... and 2 more' in rendered
        assert 'ErrorCause: Unknown' in rendered

    def test_render_active_status_with_events_renders_snapshot_tips(self):
        """A confirmed ACTIVE status renders snapshot timestamp tips."""
        rendered = status_rendering.render_consolidated_active_status_output(
            location_hash='aaaabbbbccccdddd',
            service='svc',
            environment='env',
            normalized_type='BREAKPOINT',
            created_at='2026-03-09T11:00:00Z',
            requested_start_str='2026-03-09T11:05:00Z',
            active_query_start_str='2026-03-09T11:05:00Z',
            query_end_str='2026-03-09T11:10:00Z',
            active_has_events=True,
            active_events=[
                {'Time': '2026-03-09T11:06:00Z'},
                {'Time': '2026-03-09T11:07:00Z'},
            ],
            active_error=None,
        )
        assert 'SNAPSHOT QUERY TIP' in rendered
        assert 'OVERALL STATUS: ACTIVE' in rendered
        assert '(oldest, try first)' in rendered
        assert '(most recent)' in rendered

    def test_render_active_status_without_events_not_confirmed(self):
        """An ACTIVE status with no events renders the not-confirmed verdict."""
        rendered = status_rendering.render_consolidated_active_status_output(
            location_hash='aaaabbbbccccdddd',
            service='svc',
            environment='env',
            normalized_type='BREAKPOINT',
            created_at='2026-03-09T11:00:00Z',
            requested_start_str='2026-03-09T11:05:00Z',
            active_query_start_str='2026-03-09T11:05:00Z',
            query_end_str='2026-03-09T11:10:00Z',
            active_has_events=False,
            active_events=[],
            active_error=None,
        )
        assert 'OVERALL STATUS: ACTIVE not confirmed yet' in rendered

    def test_render_ready_status_output(self):
        """A READY consolidated render appends the READY section and verdict."""
        rendered = status_rendering.render_consolidated_ready_status_output(
            location_hash='aaaabbbbccccdddd',
            service='svc',
            environment='env',
            normalized_type='BREAKPOINT',
            created_at='2026-03-09T11:00:00Z',
            requested_start_str='2026-03-09T11:05:00Z',
            active_query_start_str='2026-03-09T11:05:00Z',
            query_end_str='2026-03-09T11:10:00Z',
            active_has_events=False,
            active_events=[],
            active_error=None,
            ready_has_events=True,
            ready_events=[{'Time': '2026-03-09T11:06:00Z'}],
            ready_error=None,
        )
        assert 'READY STATUS:' in rendered
        assert 'OVERALL STATUS: READY (waiting for traffic)' in rendered

    def test_error_output_file_not_found_branch(self):
        """An ERROR cause FILE_NOT_FOUND renders the file_path troubleshooting."""
        rendered = status_rendering.render_consolidated_error_or_pending_status_output(
            location_hash='aaaabbbbccccdddd',
            service='svc',
            environment='env',
            normalized_type='BREAKPOINT',
            created_at='2026-03-09T11:00:00Z',
            requested_start_str='2026-03-09T11:05:00Z',
            active_query_start_str='2026-03-09T11:05:00Z',
            query_end_str='2026-03-09T11:10:00Z',
            active_has_events=False,
            active_events=[],
            active_error=None,
            ready_has_events=False,
            ready_events=[],
            ready_error=None,
            error_has_events=True,
            error_events=[{'Time': '2026-03-09T11:06:00Z', 'ErrorCause': 'FILE_NOT_FOUND'}],
            error_error=None,
        )
        assert 'OVERALL STATUS: ERROR (FILE_NOT_FOUND)' in rendered
        assert 'Verify file_path is correct' in rendered

    def test_error_output_line_not_executable_branch(self):
        """An ERROR cause LINE_NOT_EXECUTABLE renders the line troubleshooting."""
        rendered = status_rendering.render_consolidated_error_or_pending_status_output(
            location_hash='aaaabbbbccccdddd',
            service='svc',
            environment='env',
            normalized_type='BREAKPOINT',
            created_at='2026-03-09T11:00:00Z',
            requested_start_str='2026-03-09T11:05:00Z',
            active_query_start_str='2026-03-09T11:05:00Z',
            query_end_str='2026-03-09T11:10:00Z',
            active_has_events=False,
            active_events=[],
            active_error=None,
            ready_has_events=False,
            ready_events=[],
            ready_error=None,
            error_has_events=True,
            error_events=[{'Time': '2026-03-09T11:06:00Z', 'ErrorCause': 'LINE_NOT_EXECUTABLE'}],
            error_error=None,
        )
        assert 'OVERALL STATUS: ERROR (LINE_NOT_EXECUTABLE)' in rendered
        assert 'executable code' in rendered

    def test_error_output_other_cause_branch(self):
        """An unrecognized ERROR cause renders the generic troubleshooting."""
        rendered = status_rendering.render_consolidated_error_or_pending_status_output(
            location_hash='aaaabbbbccccdddd',
            service='svc',
            environment='env',
            normalized_type='BREAKPOINT',
            created_at='2026-03-09T11:00:00Z',
            requested_start_str='2026-03-09T11:05:00Z',
            active_query_start_str='2026-03-09T11:05:00Z',
            query_end_str='2026-03-09T11:10:00Z',
            active_has_events=False,
            active_events=[],
            active_error=None,
            ready_has_events=False,
            ready_events=[],
            ready_error=None,
            error_has_events=True,
            error_events=[{'Time': '2026-03-09T11:06:00Z', 'ErrorCause': 'WEIRD_CAUSE'}],
            error_error=None,
        )
        assert 'OVERALL STATUS: ERROR (WEIRD_CAUSE)' in rendered
        assert 'Check instrumentation configuration for WEIRD_CAUSE' in rendered

    def test_error_output_pending_branch(self):
        """No ACTIVE/READY/ERROR events renders the PENDING verdict."""
        rendered = status_rendering.render_consolidated_error_or_pending_status_output(
            location_hash='aaaabbbbccccdddd',
            service='svc',
            environment='env',
            normalized_type='BREAKPOINT',
            created_at='2026-03-09T11:00:00Z',
            requested_start_str='2026-03-09T11:05:00Z',
            active_query_start_str='2026-03-09T11:05:00Z',
            query_end_str='2026-03-09T11:10:00Z',
            active_has_events=False,
            active_events=[],
            active_error=None,
            ready_has_events=False,
            ready_events=[],
            ready_error=None,
            error_has_events=False,
            error_events=[],
            error_error=None,
        )
        assert 'OVERALL STATUS: PENDING' in rendered
        assert 'can take 1-2 minutes' in rendered

    def test_get_status_output_active_clarification_when_no_events(self):
        """An ACTIVE filter with no events renders the ACTIVE clarification."""
        rendered = status_rendering.render_get_instrumentation_configuration_status_output(
            data={'Status': 'ACTIVE', 'Events': []},
            normalized_type='BREAKPOINT',
            service='svc',
            environment='env',
            requested_status='ACTIVE',
        )
        assert 'ACTIVE Clarification' in rendered
        assert 'NOT CONFIRMED' in rendered
        assert 'No ACTIVE status events found' in rendered


class TestSnapshotRenderingMoreHelpers:
    """Additional coverage for snapshot_rendering branches."""

    def test_search_output_error_branch(self):
        """An Error query_result renders the ERROR JSON envelope."""
        rendered = snapshot_rendering.render_search_snapshots_for_status_event_output(
            service_name='svc',
            environment='env',
            location_hash='aaaabbbbccccdddd',
            custom_filters=None,
            start_time_utc='2026-03-09T11:59:55Z',
            end_time_utc='2026-03-09T12:01:00Z',
            start_epoch=1,
            end_epoch=2,
            query_string='fields @timestamp',
            query_result={'status': 'Error', 'error': 'kaboom'},
        )
        parsed = json.loads(rendered)
        assert parsed['status'] == 'ERROR'
        assert parsed['error'] == 'kaboom'

    def test_search_output_timeout_branch(self):
        """A Polling Timeout query_result renders the TIMEOUT envelope."""
        rendered = snapshot_rendering.render_search_snapshots_for_status_event_output(
            service_name='svc',
            environment='env',
            location_hash='aaaabbbbccccdddd',
            custom_filters=['x'],
            start_time_utc='2026-03-09T11:59:55Z',
            end_time_utc='2026-03-09T12:01:00Z',
            start_epoch=1,
            end_epoch=2,
            query_string='fields @timestamp',
            query_result={'status': 'Polling Timeout', 'queryId': 'q-9'},
        )
        parsed = json.loads(rendered)
        assert parsed['status'] == 'TIMEOUT'
        assert parsed['queryId'] == 'q-9'
        assert parsed['custom_filters'] == ['x']

    def test_search_output_handles_invalid_message_json(self):
        """A result with non-JSON @message yields a summary with null fields."""
        rendered = snapshot_rendering.render_search_snapshots_for_status_event_output(
            service_name='svc',
            environment='env',
            location_hash='aaaabbbbccccdddd',
            custom_filters=None,
            start_time_utc='2026-03-09T11:59:55Z',
            end_time_utc='2026-03-09T12:01:00Z',
            start_epoch=1,
            end_epoch=2,
            query_string='fields @timestamp',
            query_result={
                'status': 'Complete',
                'queryId': 'q-1',
                'results': [{'@timestamp': 't', '@message': 'not-json{'}],
            },
        )
        parsed = json.loads(rendered)
        assert parsed['status'] == 'Complete'
        assert parsed['snapshot_summaries'][0]['snapshot_id'] is None

    def test_sample_output_error_branch(self):
        """An Error sample query renders the ERROR envelope."""
        rendered = snapshot_rendering.render_get_sample_snapshot_for_breakpoint_output(
            service_name='svc',
            environment='env',
            location_hash='aaaabbbbccccdddd',
            start_time_utc='s',
            end_time_utc='e',
            max_timeout=30,
            query_string='q',
            query_result={'status': 'Error', 'error': 'kaboom'},
        )
        parsed = json.loads(rendered)
        assert parsed['status'] == 'ERROR'
        assert parsed['error'] == 'kaboom'

    def test_sample_output_timeout_branch(self):
        """A Polling Timeout sample query renders the TIMEOUT envelope."""
        rendered = snapshot_rendering.render_get_sample_snapshot_for_breakpoint_output(
            service_name='svc',
            environment='env',
            location_hash='aaaabbbbccccdddd',
            start_time_utc='s',
            end_time_utc='e',
            max_timeout=30,
            query_string='q',
            query_result={'status': 'Polling Timeout', 'queryId': 'q-7'},
        )
        parsed = json.loads(rendered)
        assert parsed['status'] == 'TIMEOUT'
        assert '30 seconds' in parsed['message']

    def test_sample_output_non_complete_status_branch(self):
        """A non-Complete, non-error status renders a passthrough envelope."""
        rendered = snapshot_rendering.render_get_sample_snapshot_for_breakpoint_output(
            service_name='svc',
            environment='env',
            location_hash='aaaabbbbccccdddd',
            start_time_utc='s',
            end_time_utc='e',
            max_timeout=30,
            query_string='q',
            query_result={'status': 'Running', 'queryId': 'q-3'},
        )
        parsed = json.loads(rendered)
        assert parsed['status'] == 'Running'

    def test_sample_output_no_results_branch(self):
        """A Complete status with no results renders NO_SNAPSHOTS_FOUND."""
        rendered = snapshot_rendering.render_get_sample_snapshot_for_breakpoint_output(
            service_name='svc',
            environment='env',
            location_hash='aaaabbbbccccdddd',
            start_time_utc='s',
            end_time_utc='e',
            max_timeout=30,
            query_string='q',
            query_result={'status': 'Complete', 'queryId': 'q-4', 'results': []},
        )
        parsed = json.loads(rendered)
        assert parsed['status'] == 'NO_SNAPSHOTS_FOUND'

    def test_sample_output_large_snapshot_uses_parsed_summary(self):
        """A >10KB snapshot with include_raw=False is replaced by a parsed summary."""
        big_value = 'x' * 11000
        message = json.dumps(
            {
                'timeUnixNano': 1762689600000000000,
                'traceId': 'trace-1',
                'attributes': {
                    'aws.di.snapshot_id': 'snap-big',
                    'aws.di.location_hash': 'aaaabbbbccccdddd',
                },
                'body': {
                    'captures': {
                        'entry': {'arguments': {'blob': {'type': 'str', 'value': big_value}}}
                    }
                },
            }
        )
        rendered = snapshot_rendering.render_get_sample_snapshot_for_breakpoint_output(
            service_name='svc',
            environment='env',
            location_hash='aaaabbbbccccdddd',
            start_time_utc='s',
            end_time_utc='e',
            max_timeout=30,
            query_string='q',
            query_result={
                'status': 'Complete',
                'queryId': 'q-5',
                'results': [{'@timestamp': 't', '@message': message}],
            },
            include_raw=False,
        )
        parsed = json.loads(rendered)
        assert parsed['status'] == 'SUCCESS'
        assert 'note' in parsed
        assert 'compact parsed summary' in parsed['note']
        assert parsed['sample_snapshot']['snapshot_id'] == 'snap-big'
        assert 'raw_snapshot' not in parsed['sample_snapshot']

    def test_sample_output_invalid_message_json_yields_empty_snapshot(self):
        """A small result with invalid JSON @message yields an empty sample snapshot."""
        rendered = snapshot_rendering.render_get_sample_snapshot_for_breakpoint_output(
            service_name='svc',
            environment='env',
            location_hash='aaaabbbbccccdddd',
            start_time_utc='s',
            end_time_utc='e',
            max_timeout=30,
            query_string='q',
            query_result={
                'status': 'Complete',
                'queryId': 'q-6',
                'results': [{'@timestamp': 't', '@message': 'not-json{'}],
            },
            include_raw=False,
        )
        parsed = json.loads(rendered)
        assert parsed['status'] == 'SUCCESS'
        assert parsed['sample_snapshot'] == {}


class TestCrudToolsMoreEntrypoints:
    """Additional Stubber-driven and validation coverage for crud_tools."""

    def test_create_rejects_invalid_instrumentation_type(self):
        """An invalid instrumentation_type short-circuits create."""
        rendered = crud_tools.create_instrumentation(
            instrumentation_type='BOGUS',
            service='svc',
            environment='env',
            language='Python',
            file_path='/app/h.py',
            method_name='run',
            capture_arguments=['x'],
        )
        assert 'instrumentation_type must be one of' in rendered

    def test_create_rejects_missing_file_path(self):
        """A missing file_path returns the location validation error."""
        rendered = crud_tools.create_instrumentation(
            instrumentation_type='BREAKPOINT',
            service='svc',
            environment='env',
            language='Python',
            file_path=None,
            method_name='run',
            capture_arguments=['x'],
        )
        assert 'file_path' in rendered

    def test_list_instrumentations_renders_populated_results(self):
        """A populated list response renders configuration details."""
        stubber = _stub_application_signals()
        stubber.add_response(
            'list_instrumentation_configurations',
            {
                'Service': 'svc',
                'Environment': 'env',
                'Changed': True,
                'LatestConfigurations': [
                    {
                        'InstrumentationType': 'BREAKPOINT',
                        'SignalType': 'SNAPSHOT',
                        'LocationHash': 'aaaabbbbccccdddd',
                        'Location': {
                            'CodeLocation': {
                                'Language': 'Python',
                                'FilePath': '/app/handler.py',
                                'MethodName': 'run',
                            }
                        },
                        'CaptureConfiguration': {
                            'CodeCapture': {
                                'CaptureArguments': ['order_id'],
                                'CaptureReturn': True,
                                'CaptureStackTrace': True,
                                'CaptureLimits': {},
                            }
                        },
                        'CreatedAt': datetime(2026, 3, 9, 11, 0, 0, tzinfo=timezone.utc),
                        'ARN': 'arn:demo',
                    }
                ],
                'SyncedAt': datetime(2026, 3, 9, 12, 0, 0, tzinfo=timezone.utc),
                'SyncInterval': 60,
            },
        )
        rendered = crud_tools.list_instrumentations(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
        )
        stubber.assert_no_pending_responses()
        assert 'Active BREAKPOINT Instrumentations (1 found)' in rendered
        assert 'aaaabbbbccccdddd' in rendered

    def test_list_instrumentations_forwards_optional_params(self):
        """Optional synced_at/max_results/next_token are forwarded to the API."""
        stubber = _stub_application_signals()
        stubber.add_response(
            'list_instrumentation_configurations',
            {
                'Service': 'svc',
                'Environment': 'env',
                'Changed': False,
                'LatestConfigurations': [],
                'SyncedAt': datetime(2026, 3, 9, 12, 0, 0, tzinfo=timezone.utc),
                'SyncInterval': 60,
            },
            expected_params={
                'Service': 'svc',
                'Environment': 'env',
                'InstrumentationType': 'BREAKPOINT',
                'SyncedAt': '2026-03-09T11:00:00Z',
                'MaxResults': 5,
                'NextToken': 'tok',
            },
        )
        rendered = crud_tools.list_instrumentations(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            synced_at='2026-03-09T11:00:00Z',
            max_results=5,
            next_token='tok',
        )
        stubber.assert_no_pending_responses()
        assert 'No active BREAKPOINT instrumentations found' in rendered

    def test_get_instrumentation_error_path(self):
        """A backend error on get renders the attempted-retrieve block."""
        stubber = _stub_application_signals()
        stubber.add_client_error(
            'get_instrumentation_configuration',
            service_error_code='ResourceNotFoundException',
            service_message='no such config',
        )
        rendered = crud_tools.get_instrumentation(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
        )
        assert 'ATTEMPTED TO RETRIEVE:' in rendered
        assert 'ResourceNotFoundException' in rendered

    def test_get_instrumentation_requires_location_identifier(self):
        """Get without any location identifier returns usage help."""
        rendered = crud_tools.get_instrumentation(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
        )
        assert 'Must provide one of' in rendered

    def test_delete_instrumentation_by_code_location(self):
        """Delete resolves a code location into a CodeLocation identifier."""
        stubber = _stub_application_signals()
        stubber.add_response(
            'delete_instrumentation_configuration',
            {'DeletionStatus': 'DELETED'},
            expected_params={
                'InstrumentationType': 'BREAKPOINT',
                'Service': 'svc',
                'Environment': 'env',
                'SignalType': 'SNAPSHOT',
                'LocationIdentifier': {
                    'CodeLocation': {
                        'Language': 'Python',
                        'FilePath': '/app/handler.py',
                        'MethodName': 'run',
                    }
                },
            },
        )
        rendered = crud_tools.delete_instrumentation(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            language='Python',
            file_path='/app/handler.py',
            method_name='run',
        )
        stubber.assert_no_pending_responses()
        assert 'Successfully deleted BREAKPOINT instrumentation' in rendered

    def test_delete_instrumentation_requires_location_identifier(self):
        """Delete without any location identifier returns usage help."""
        rendered = crud_tools.delete_instrumentation(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
        )
        assert 'Must provide one of' in rendered

    def test_delete_instrumentation_error_path(self):
        """A backend error on delete renders the attempted-delete block."""
        stubber = _stub_application_signals()
        stubber.add_client_error(
            'delete_instrumentation_configuration',
            service_error_code='ResourceNotFoundException',
            service_message='gone',
        )
        rendered = crud_tools.delete_instrumentation(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
        )
        assert 'ATTEMPTED TO DELETE:' in rendered
        assert 'ResourceNotFoundException' in rendered

    def test_batch_delete_by_arns_success(self):
        """Batch delete by ARNs renders a successful summary."""
        stubber = _stub_application_signals()
        arn = (
            'arn:aws:application-signals:us-west-1:123456789012:'
            'instrumentationConfig/svc/env/SNAPSHOT/aaaabbbbccccdddd'
        )
        stubber.add_response(
            'batch_delete_instrumentation_configurations',
            {
                'DeletedCount': 1,
                'SuccessfulDeletions': [{'ResourceArn': arn}],
                'Errors': [],
            },
            expected_params={
                'DeletionTarget': {
                    'ResourceArns': {
                        'ResourceArns': [arn],
                        'InstrumentationType': 'BREAKPOINT',
                    }
                }
            },
        )
        rendered = crud_tools.batch_delete_instrumentations_by_arns(
            resource_arns=[arn],
            instrumentation_type='BREAKPOINT',
        )
        stubber.assert_no_pending_responses()
        assert 'DeletedCount: 1' in rendered
        assert 'Mode: ResourceArns' in rendered

    def test_batch_delete_by_arns_error_path(self):
        """A backend error on ARN batch delete renders the attempted block."""
        stubber = _stub_application_signals()
        arn = (
            'arn:aws:application-signals:us-west-1:123456789012:'
            'instrumentationConfig/svc/env/SNAPSHOT/aaaabbbbccccdddd'
        )
        stubber.add_client_error(
            'batch_delete_instrumentation_configurations',
            service_error_code='ValidationException',
            service_message='bad arns',
        )
        rendered = crud_tools.batch_delete_instrumentations_by_arns(
            resource_arns=[arn],
            instrumentation_type='BREAKPOINT',
        )
        assert 'ValidationException' in rendered
        assert 'bad arns' in rendered

    def test_batch_delete_by_arns_rejects_empty_list(self):
        """An empty ARN list is rejected before any API call."""
        rendered = crud_tools.batch_delete_instrumentations_by_arns(
            resource_arns=[],
            instrumentation_type='BREAKPOINT',
        )
        assert 'at least one ARN' in rendered

    def test_batch_delete_by_arns_rejects_too_many(self):
        """More than 50 ARNs are rejected before any API call."""
        rendered = crud_tools.batch_delete_instrumentations_by_arns(
            resource_arns=['arn'] * 51,
            instrumentation_type='BREAKPOINT',
        )
        assert 'at most 50 ARNs' in rendered

    def test_batch_delete_by_arns_rejects_blank_arn(self):
        """A blank ARN entry is rejected before any API call."""
        rendered = crud_tools.batch_delete_instrumentations_by_arns(
            resource_arns=['  '],
            instrumentation_type='BREAKPOINT',
        )
        assert 'non-empty ARN strings only' in rendered

    def test_batch_delete_by_scope_error_path(self):
        """A backend error on scope batch delete renders the failure block."""
        stubber = _stub_application_signals()
        stubber.add_client_error(
            'batch_delete_instrumentation_configurations',
            service_error_code='ValidationException',
            service_message='bad scope',
        )
        rendered = crud_tools.batch_delete_instrumentations_by_scope(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
        )
        assert 'ValidationException' in rendered
        assert 'bad scope' in rendered

    def test_batch_delete_by_scope_rejects_invalid_type(self):
        """An invalid instrumentation_type short-circuits scope batch delete."""
        rendered = crud_tools.batch_delete_instrumentations_by_scope(
            service='svc',
            environment='env',
            instrumentation_type='NOPE',
        )
        assert 'instrumentation_type must be one of' in rendered


class TestCaptureLimitsPayload:
    """Cover each CaptureLimits field being emitted into the API payload."""

    def test_each_limit_field_emitted(self):
        """Every set CaptureLimits field is rendered into to_api_payload."""
        limits = capture.CaptureLimits(
            max_hits=1,
            max_string_length=2,
            max_collection_width=3,
            max_collection_depth=4,
            max_stack_frames=5,
            max_stack_trace_size=6,
            max_object_depth=7,
            max_fields_per_object=8,
        )
        payload = limits.to_api_payload()
        assert payload == {
            'MaxHits': 1,
            'MaxStringLength': 2,
            'MaxCollectionWidth': 3,
            'MaxCollectionDepth': 4,
            'MaxStackFrames': 5,
            'MaxStackTraceSize': 6,
            'MaxObjectDepth': 7,
            'MaxFieldsPerObject': 8,
        }


class TestCodeCapturePayloadAndParsing:
    """Cover CodeCapture payload locals emission and capture_from_response branches."""

    def test_capture_locals_emitted_in_payload(self):
        """A non-None capture_locals is emitted as CaptureLocals in the payload."""
        cap = capture.CodeCapture(
            capture_return=True,
            capture_stack_trace=False,
            capture_arguments=['a'],
            capture_locals=['x', 'y'],
        )
        payload = cap.to_api_payload()
        assert payload['CodeCapture']['CaptureLocals'] == ['x', 'y']

    def test_non_dict_input_yields_unknown_capture(self):
        """A non-dict union value parses to UnknownCapture with empty raw."""
        result = capture.capture_from_response(None)
        assert isinstance(result, capture.UnknownCapture)
        assert dict(result.raw) == {}

    def test_inferred_code_capture_without_wrapper_key(self):
        """A CodeCapture-shaped dict without the wrapper key infers a CodeCapture."""
        result = capture.capture_from_response({'CaptureReturn': True, 'CaptureStackTrace': True})
        assert isinstance(result, capture.CodeCapture)
        assert result.capture_return is True

    def test_capture_limits_present_but_not_a_dict_coerced(self):
        """A non-dict CaptureLimits is coerced to an empty CaptureLimits."""
        result = capture.capture_from_response(
            {'CodeCapture': {'CaptureReturn': True, 'CaptureLimits': 'oops'}}
        )
        assert isinstance(result, capture.CodeCapture)
        assert result.limits.is_empty()


class TestCrudRenderingBranches:
    """Cover the empty-arguments and locals rendering branches in crud_rendering."""

    def test_create_success_renders_empty_arguments_as_none(self):
        """An empty capture_arguments tuple renders '- Arguments: (none)'."""
        loc = location.CodeLocation(language='Python', file_path='/app/h.py')
        rendered = crud_rendering.render_create_success_message(
            response={'LocationHash': 'h', 'ARN': 'arn', 'CreatedAt': None},
            normalized_type='BREAKPOINT',
            service='svc',
            environment='env',
            location=loc,
            ttl_hours=None,
            capture_arguments=[],
            code_capture_locals=None,
            is_line_level=False,
            code_capture_return=True,
            code_capture_stack_trace=True,
            max_hits=None,
            max_string_length=None,
            max_collection_width=None,
            max_collection_depth=None,
            max_stack_frames=None,
            max_stack_trace_size=None,
            max_object_depth=None,
            max_fields_per_object=None,
            attribute_filters=None,
        )
        assert '- Arguments: (none)' in rendered

    def test_list_output_renders_empty_arguments_as_empty_list(self):
        """A listed config with present-but-empty CaptureArguments renders '(empty list)'."""
        data = {
            'LatestConfigurations': [
                {
                    'Location': {'CodeLocation': {'Language': 'Python', 'FilePath': '/app/h.py'}},
                    'LocationHash': 'h',
                    'CaptureConfiguration': {
                        'CodeCapture': {
                            'CaptureReturn': True,
                            'CaptureStackTrace': True,
                            'CaptureArguments': [],
                        }
                    },
                }
            ]
        }
        rendered = crud_rendering.render_list_instrumentations_output(
            data=data,
            normalized_type='BREAKPOINT',
            service='svc',
            environment='env',
        )
        assert '- Arguments: (empty list)' in rendered

    def test_get_instrumentation_output_renders_local_variables(self):
        """A CodeCapture with capture_locals renders the Local Variables line."""
        config = {
            'InstrumentationType': 'BREAKPOINT',
            'Location': {'CodeLocation': {'Language': 'Python', 'FilePath': '/app/h.py'}},
            'CaptureConfiguration': {
                'CodeCapture': {
                    'CaptureReturn': True,
                    'CaptureStackTrace': True,
                    'CaptureLocals': ['counter', 'total'],
                }
            },
        }
        rendered = crud_rendering.render_get_instrumentation_output(
            config=config, service='svc', environment='env'
        )
        assert '- Local Variables: counter, total' in rendered

    def test_list_output_renders_empty_locals_as_empty_list(self):
        """A listed config with present-but-empty CaptureLocals renders '(empty list)'."""
        data = {
            'LatestConfigurations': [
                {
                    'Location': {'CodeLocation': {'Language': 'Python', 'FilePath': '/app/h.py'}},
                    'LocationHash': 'h',
                    'CaptureConfiguration': {
                        'CodeCapture': {
                            'CaptureReturn': True,
                            'CaptureStackTrace': True,
                            'CaptureArguments': ['order_id'],
                            'CaptureLocals': [],
                        }
                    },
                }
            ]
        }
        rendered = crud_rendering.render_list_instrumentations_output(
            data=data,
            normalized_type='BREAKPOINT',
            service='svc',
            environment='env',
        )
        assert '- Locals: (empty list)' in rendered

    def test_get_output_renders_empty_locals_as_empty_list(self):
        """A get config with present-but-empty CaptureLocals renders '(empty list)'."""
        config = {
            'InstrumentationType': 'BREAKPOINT',
            'Location': {'CodeLocation': {'Language': 'Python', 'FilePath': '/app/h.py'}},
            'CaptureConfiguration': {
                'CodeCapture': {
                    'CaptureReturn': True,
                    'CaptureStackTrace': True,
                    'CaptureArguments': ['order_id'],
                    'CaptureLocals': [],
                }
            },
        }
        rendered = crud_rendering.render_get_instrumentation_output(
            config=config, service='svc', environment='env'
        )
        assert '- Local Variables: (empty list)' in rendered

    def test_create_success_message_probe_shows_longer_ready_window(self):
        """A PROBE create-success message shows the ~10-12 min READY window."""
        loc = location.CodeLocation(language='Python', file_path='/app/h.py', method_name='run')
        rendered = crud_rendering.render_create_success_message(
            response={'LocationHash': 'aaaabbbbccccdddd', 'ARN': 'arn', 'CreatedAt': None},
            normalized_type='PROBE',
            service='svc',
            environment='env',
            location=loc,
            ttl_hours=None,
            capture_arguments=['order_id'],
            code_capture_locals=None,
            is_line_level=False,
            code_capture_return=True,
            code_capture_stack_trace=True,
            max_hits=None,
            max_string_length=None,
            max_collection_width=None,
            max_collection_depth=None,
            max_stack_frames=None,
            max_stack_trace_size=None,
            max_object_depth=None,
            max_fields_per_object=None,
            attribute_filters=None,
        )
        assert 'Allow ~10-12 min before this configuration reports READY' in rendered


class TestErrorTranslationEmptyHelpers:
    """Cover the empty-input early returns in error_translation helpers."""

    def test_format_block_with_all_blank_values_returns_empty(self):
        """A context whose values are all blank yields an empty block."""
        assert error_translation._format_block('LABEL:', {'a': None, 'b': ''}) == ''

    def test_numbered_section_with_empty_items_returns_empty(self):
        """An empty items sequence yields an empty numbered section."""
        assert error_translation._format_numbered_section('LABEL:', []) == ''

    def test_read_timeout_renders_timeout_guidance(self):
        """A ReadTimeoutError renders the timeout troubleshooting block."""
        from botocore.exceptions import ReadTimeoutError

        rendered = error_translation.translate_aws_error(
            ReadTimeoutError(endpoint_url='http://x'),
            action='create instrumentation',
        )
        assert 'TimeoutError' in rendered
        assert 'did not respond within the socket timeout' in rendered


class TestLocationBranches:
    """Cover the describe/format/payload/parse branches in location."""

    def test_describe_with_class_method_and_line(self):
        """Describe renders class_name, method_name, and line_number segments."""
        loc = location.CodeLocation(
            language='Java',
            file_path='/app/Order.java',
            class_name='Order',
            method_name='submit',
            line_number=42,
        )
        assert loc.describe() == '/app/Order.java :: Order.submit:L42'

    def test_level_line_level_when_line_number_set(self):
        """Level reports LINE-LEVEL when a line_number is present."""
        loc = location.CodeLocation(language='Python', file_path='/app/h.py', line_number=7)
        assert loc.level() == 'LINE-LEVEL (L7)'

    def test_format_details_with_extra_fields(self):
        """format_details renders extra_fields after the known fields."""
        loc = location.CodeLocation(
            language='Python',
            file_path='/app/h.py',
            extra_fields={'CustomKey': 'CustomVal'},
        )
        rendered = loc.format_details()
        assert '- CustomKey: CustomVal' in rendered

    def test_to_api_payload_with_class_and_line(self):
        """to_api_payload includes ClassName and LineNumber when set."""
        loc = location.CodeLocation(
            language='Java',
            file_path='/app/Order.java',
            class_name='Order',
            line_number=42,
        )
        payload = loc.to_api_payload()['CodeLocation']
        assert payload['ClassName'] == 'Order'
        assert payload['LineNumber'] == 42

    def test_parse_create_inputs_validation_error(self):
        """An invalid line_number surfaces a validation error from parse_create_inputs."""
        loc, err = location.parse_create_inputs(
            normalized_type='BREAKPOINT',
            language='Python',
            file_path='/app/h.py',
            code_unit='services.h',
            method_name='run',
            line_number=0,
        )
        assert loc is None
        assert err

    def test_parse_create_inputs_canonicalizes_language_casing(self):
        """parse_create_inputs maps language casing to the API enum (javascript -> Javascript)."""
        loc, err = location.parse_create_inputs(
            normalized_type='BREAKPOINT',
            language='javascript',
            file_path='/app/handler.js',
            line_number=42,
        )
        assert err is None
        assert loc is not None
        assert loc.to_api_payload()['CodeLocation']['Language'] == 'Javascript'

    def test_parse_lookup_inputs_disallows_code_location(self):
        """allow_code_location_lookup=False rejects a code-location lookup."""
        loc, err = location.parse_lookup_inputs(
            normalized_type='BREAKPOINT',
            language='Python',
            file_path='/app/h.py',
            allow_code_location_lookup=False,
        )
        assert loc is None
        assert err is not None
        assert 'not supported' in err

    def test_location_from_response_bare_code_fields(self):
        """A bare Language/FilePath dict (no wrapper) parses to a CodeLocation."""
        result = location.location_from_response({'Language': 'Python', 'FilePath': '/app/h.py'})
        assert isinstance(result, location.CodeLocation)
        assert result.file_path == '/app/h.py'

    def test_render_location_block_hash_location(self):
        """A HashLocation renders the HASH location block."""
        rendered = location.render_location_block(
            location.HashLocation(location_hash='aaaabbbbccccdddd')
        )
        assert '- LocationKind: HASH' in rendered
        assert '- LocationHash: aaaabbbbccccdddd' in rendered


class TestSnapshotParsingCoercion:
    """Cover the non-dict coercion branches and the regex escape helper."""

    def test_escape_regex_with_slash(self):
        """A value containing '/' is escaped for a Logs Insights /.../ regex."""
        escaped = snapshot_parsing._escape_logs_insights_regex('a/b')
        assert escaped == r'a\/b'

    def test_non_dict_subfields_coerced_to_empty(self):
        """Non-dict resource/captures/throwable subfields are coerced to {}."""
        message = json.dumps(
            {
                'resource': {'attributes': 'not-a-dict'},
                'body': {
                    'captures': {
                        'entry': {'arguments': 'x', 'locals': 1},
                        'return': {'arguments': [], 'locals': 2, 'throwable': 'oops'},
                    }
                },
            }
        )
        parsed = snapshot_parsing._parse_snapshot_fields({'@message': message})
        assert parsed['entry_argument_names'] == []
        assert parsed['entry_local_names'] == []
        assert parsed['return_argument_names'] == []
        assert parsed['return_local_names'] == []
        assert parsed['throwable'] is None

    def test_non_dict_captures_coerced_to_empty(self):
        """A non-dict body.captures is coerced to {} before sub-extraction."""
        message = json.dumps({'body': {'captures': 'not-a-dict'}})
        parsed = snapshot_parsing._parse_snapshot_fields({'@message': message})
        assert parsed['entry_argument_names'] == []
        assert parsed['return_value'] is None


class TestSnapshotRenderingCoercion:
    """Cover the non-dict attributes coercion in snapshot search rendering."""

    def test_non_dict_attributes_coerced(self):
        """A snapshot whose attributes are not a dict is coerced to {}."""
        query_result = {
            'status': 'Complete',
            'queryId': 'q-1',
            'results': [{'@message': json.dumps({'attributes': 'nope'})}],
            'messages': [],
        }
        rendered = snapshot_rendering.render_search_snapshots_for_status_event_output(
            service_name='svc',
            environment='env',
            location_hash='h',
            custom_filters=None,
            start_time_utc='s',
            end_time_utc='e',
            start_epoch=0,
            end_epoch=1,
            query_string='q',
            query_result=query_result,
        )
        parsed = json.loads(rendered)
        assert parsed['snapshot_summaries'][0]['snapshot_id'] is None


class TestSnapshotQueriesPolling:
    """Cover the polling loop, terminal status, timeout, and exception paths."""

    def test_terminal_status_returns_results(self, monkeypatch):
        """A Complete status returns parsed results immediately."""

        class _Logs:
            def start_query(self, **kwargs):
                return {'queryId': 'q-1'}

            def get_query_results(self, **kwargs):
                return {
                    'status': 'Complete',
                    'results': [[{'field': '@message', 'value': '{}'}]],
                    'messages': [],
                }

        monkeypatch.setattr(snapshot_queries.aws_clients, 'logs_client', _Logs())
        result = snapshot_queries._execute_cloudwatch_query(
            query_string='q',
            start_epoch=0,
            end_epoch=1,
            log_group_name='lg',
        )
        assert result['status'] == 'Complete'
        assert result['results'] == [{'@message': '{}'}]

    def test_sleep_then_complete(self, monkeypatch):
        """A Running poll triggers time.sleep(1), then the next poll completes."""
        sleeps = []
        monkeypatch.setattr(snapshot_queries.time, 'sleep', lambda s: sleeps.append(s))

        statuses = iter(['Running', 'Complete'])

        class _Logs:
            def start_query(self, **kwargs):
                return {'queryId': 'q-1'}

            def get_query_results(self, **kwargs):
                return {'status': next(statuses), 'results': [], 'messages': []}

        monkeypatch.setattr(snapshot_queries.aws_clients, 'logs_client', _Logs())
        result = snapshot_queries._execute_cloudwatch_query(
            query_string='q',
            start_epoch=0,
            end_epoch=1,
            log_group_name='lg',
        )
        assert result['status'] == 'Complete'
        assert sleeps == [1]

    def test_missing_query_id_returns_error(self, monkeypatch):
        """A start_query response without a queryId returns an error dict."""

        class _Logs:
            def start_query(self, **kwargs):
                return {}

        monkeypatch.setattr(snapshot_queries.aws_clients, 'logs_client', _Logs())
        result = snapshot_queries._execute_cloudwatch_query(
            query_string='q',
            start_epoch=0,
            end_epoch=1,
            log_group_name='lg',
        )
        assert result['status'] == 'Error'
        assert 'did not return a queryId' in result['error']

    def test_start_query_generic_exception_handled(self, monkeypatch):
        """A non-ClientError from start_query yields an error dict."""

        class _Logs:
            def start_query(self, **kwargs):
                raise RuntimeError('start-boom')

        monkeypatch.setattr(snapshot_queries.aws_clients, 'logs_client', _Logs())
        result = snapshot_queries._execute_cloudwatch_query(
            query_string='q',
            start_epoch=0,
            end_epoch=1,
            log_group_name='lg',
        )
        assert result['status'] == 'Error'
        assert result['error'] == 'start-boom'

    def test_get_results_client_error_handled(self, monkeypatch):
        """A ClientError from get_query_results yields a structured error dict."""

        class _Logs:
            def start_query(self, **kwargs):
                return {'queryId': 'q-1'}

            def get_query_results(self, **kwargs):
                raise ClientError(
                    error_response={'Error': {'Code': 'X', 'Message': 'nope'}},
                    operation_name='GetQueryResults',
                )

        monkeypatch.setattr(snapshot_queries.aws_clients, 'logs_client', _Logs())
        result = snapshot_queries._execute_cloudwatch_query(
            query_string='q',
            start_epoch=0,
            end_epoch=1,
            log_group_name='lg',
        )
        assert result['status'] == 'Error'
        assert 'Failed to get results' in result['error']
        assert result['queryId'] == 'q-1'

    def test_polling_timeout_returns_timeout(self, monkeypatch):
        """When the deadline passes without a terminal status, a timeout dict results."""
        monkeypatch.setattr(snapshot_queries.time, 'sleep', lambda s: None)
        # First time() call (poll_start) is small; subsequent calls exceed the deadline.
        times = iter([1000.0, 1000.0, 2000.0, 2000.0])
        monkeypatch.setattr(snapshot_queries.time, 'time', lambda: next(times))

        class _Logs:
            def start_query(self, **kwargs):
                return {'queryId': 'q-1'}

            def get_query_results(self, **kwargs):
                return {'status': 'Running', 'results': [], 'messages': []}

        monkeypatch.setattr(snapshot_queries.aws_clients, 'logs_client', _Logs())
        result = snapshot_queries._execute_cloudwatch_query(
            query_string='q',
            start_epoch=0,
            end_epoch=1,
            log_group_name='lg',
            max_timeout=5,
        )
        assert result['status'] == 'Polling Timeout'
        assert result['queryId'] == 'q-1'

    def test_get_results_generic_exception_handled(self, monkeypatch):
        """A non-ClientError from get_query_results yields an error dict."""

        class _Logs:
            def start_query(self, **kwargs):
                return {'queryId': 'q-1'}

            def get_query_results(self, **kwargs):
                raise RuntimeError('boom')

        monkeypatch.setattr(snapshot_queries.aws_clients, 'logs_client', _Logs())
        result = snapshot_queries._execute_cloudwatch_query(
            query_string='q',
            start_epoch=0,
            end_epoch=1,
            log_group_name='lg',
        )
        assert result['status'] == 'Error'
        assert result['error'] == 'boom'
        assert result['queryId'] == 'q-1'


class TestSnapshotToolsNaiveTimeAndFilters:
    """Cover naive-timestamp tz handling and custom_filters appending."""

    def test_search_appends_custom_filters_with_naive_timestamp(self, monkeypatch):
        """A naive timestamp gets UTC tzinfo and custom filters are appended."""
        captured = {}

        def _fake_query(*, query_string, **kwargs):
            captured['query_string'] = query_string
            return {'status': 'Complete', 'queryId': 'q', 'results': [], 'messages': []}

        monkeypatch.setattr(snapshot_tools, '_execute_cloudwatch_query', _fake_query)
        rendered = snapshot_tools.search_snapshots_for_status_event(
            service_name='svc',
            environment='env',
            location_hash='aaaabbbbccccdddd',
            status_timestamp='2026-03-09T12:00:00',
            custom_filters=['@message like /boom/', '   ', ''],
        )
        assert '@message like /boom/' in captured['query_string']
        parsed = json.loads(rendered)
        assert parsed['status'] == 'Complete'

    def test_sample_handles_naive_timestamp(self, monkeypatch):
        """get_sample_snapshot_for_breakpoint accepts a naive timestamp."""

        def _fake_query(**kwargs):
            return {'status': 'Complete', 'queryId': 'q', 'results': [], 'messages': []}

        monkeypatch.setattr(snapshot_tools, '_execute_cloudwatch_query', _fake_query)
        rendered = snapshot_tools.get_sample_snapshot_for_breakpoint(
            service_name='svc',
            environment='env',
            location_hash='aaaabbbbccccdddd',
            status_timestamp='2026-03-09T12:00:00',
        )
        parsed = json.loads(rendered)
        assert parsed['status'] == 'NO_SNAPSHOTS_FOUND'


class TestIsValidLocationHash:
    """Cover the shared 16-char lowercase-hex location-hash validator."""

    def test_valid_lowercase_hex(self):
        """A 16-char lowercase hex string is valid."""
        assert validation.is_valid_location_hash('0123456789abcdef') is True

    def test_uppercase_hex_rejected(self):
        """Uppercase hex is rejected (hashes are lowercase by API design)."""
        assert validation.is_valid_location_hash('0123456789ABCDEF') is False

    def test_wrong_length_rejected(self):
        """A hash that is not exactly 16 characters is rejected."""
        assert validation.is_valid_location_hash('abc') is False
        assert validation.is_valid_location_hash('a' * 17) is False

    def test_non_hex_characters_rejected(self):
        """A 16-char string with a non-hex character is rejected."""
        assert validation.is_valid_location_hash('zzzzzzzzzzzzzzzz') is False

    def test_none_and_empty_rejected(self):
        """None and empty input are rejected."""
        assert validation.is_valid_location_hash(None) is False
        assert validation.is_valid_location_hash('') is False


class TestSnapshotToolsQueryHardening:
    """Cover injection-hardening guards on the snapshot query tools."""

    def test_search_rejects_invalid_location_hash(self):
        """search_snapshots rejects a non-hex location_hash before querying."""
        rendered = snapshot_tools.search_snapshots_for_status_event(
            service_name='svc',
            environment='env',
            location_hash='not-a-hash',
            status_timestamp='2026-03-09T12:00:00Z',
        )
        assert rendered == 'ERROR: location_hash must be a 16-character hex string'

    def test_sample_rejects_invalid_location_hash(self):
        """get_sample_snapshot rejects a non-hex location_hash before querying."""
        rendered = snapshot_tools.get_sample_snapshot_for_breakpoint(
            service_name='svc',
            environment='env',
            location_hash='not-a-hash',
            status_timestamp='2026-03-09T12:00:00Z',
        )
        assert rendered == 'ERROR: location_hash must be a 16-character hex string'

    def test_search_rejects_non_integer_limit(self, monkeypatch):
        """A non-integer limit is rejected before the query runs."""
        monkeypatch.setattr(
            snapshot_tools,
            '_execute_cloudwatch_query',
            lambda **kwargs: pytest.fail('query should not run'),
        )
        rendered = snapshot_tools.search_snapshots_for_status_event(
            service_name='svc',
            environment='env',
            location_hash='aaaabbbbccccdddd',
            status_timestamp='2026-03-09T12:00:00Z',
            limit='ten',  # type: ignore[arg-type]
        )
        assert rendered == 'ERROR: limit must be an integer'

    def test_search_rejects_unbalanced_quote_in_custom_filter(self, monkeypatch):
        """A custom filter with an unbalanced double-quote is rejected."""
        monkeypatch.setattr(
            snapshot_tools,
            '_execute_cloudwatch_query',
            lambda **kwargs: pytest.fail('query should not run'),
        )
        rendered = snapshot_tools.search_snapshots_for_status_event(
            service_name='svc',
            environment='env',
            location_hash='aaaabbbbccccdddd',
            status_timestamp='2026-03-09T12:00:00Z',
            custom_filters=['service.name = "leak'],
        )
        assert 'unbalanced quotes' in rendered

    def test_search_escapes_quotes_in_service_and_environment(self, monkeypatch):
        """A double-quote in service_name/environment is escaped, not left raw.

        Without escaping, the quote would terminate the Logs Insights string
        literal and the rest would become caller-controlled query syntax.
        """
        captured = {}

        def _fake_query(*, query_string, **kwargs):
            captured['query_string'] = query_string
            return {'status': 'Complete', 'queryId': 'q', 'results': [], 'messages': []}

        monkeypatch.setattr(snapshot_tools, '_execute_cloudwatch_query', _fake_query)
        snapshot_tools.search_snapshots_for_status_event(
            service_name='svc" or "1"="1',
            environment='env',
            location_hash='aaaabbbbccccdddd',
            status_timestamp='2026-03-09T12:00:00Z',
        )
        # The injected quote is backslash-escaped, so the literal is not broken.
        assert 'service.name = "svc\\" or \\"1\\"=\\"1"' in captured['query_string']


class TestStatusRenderingBranches:
    """Cover error-cause, ACTIVE-not-confirmed, and verdict dispatch branches."""

    def _result(self, has_events=False, events=None, error=None):
        from awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation import (
            status_assessment,
        )

        return status_assessment._StatusCheckResult(
            has_events=has_events, events=events or [], error=error
        )

    def _time_window(self):
        from awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation import (
            status_assessment,
        )

        return status_assessment.TimeWindow(
            created_at='2026-03-09T11:00:00Z',
            requested_start='2026-03-09T12:00:00Z',
            active_query_start='2026-03-09T12:00:00Z',
            query_end='2026-03-09T12:05:00Z',
        )

    def test_explicit_status_renders_error_cause(self):
        """An event with an ErrorCause appends the ErrorCause segment."""
        data = {
            'Status': 'ERROR',
            'Location': {'CodeLocation': {'Language': 'Python', 'FilePath': '/app/h.py'}},
            'Events': [
                {
                    'Time': datetime(2026, 3, 9, 12, 0, 0, tzinfo=timezone.utc),
                    'ErrorCause': 'FILE_NOT_FOUND',
                }
            ],
        }
        rendered = status_rendering.render_get_instrumentation_configuration_status_output(
            data=data,
            normalized_type='BREAKPOINT',
            service='svc',
            environment='env',
            requested_status='ERROR',
        )
        assert 'ErrorCause: FILE_NOT_FOUND' in rendered

    def test_ready_dispatch_includes_active_not_confirmed_strip(self):
        """A Ready verdict dispatches to the ready renderer (ACTIVE strip path)."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation import (
            status_assessment,
        )

        verdict = status_assessment.Ready(
            active=self._result(has_events=False),
            ready=self._result(has_events=True, events=[{'Time': None}]),
        )
        rendered = status_rendering.render_status_assessment(
            verdict,
            location_hash='h',
            service='svc',
            environment='env',
            normalized_type='BREAKPOINT',
            time_window=self._time_window(),
        )
        assert 'OVERALL STATUS: READY (waiting for traffic)' in rendered
        assert 'ACTIVE not confirmed yet' not in rendered

    def test_active_dispatch_renders_active_output(self):
        """An Active verdict dispatches to the active renderer."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation import (
            status_assessment,
        )

        verdict = status_assessment.Active(
            active=self._result(
                has_events=True,
                events=[{'Time': datetime(2026, 3, 9, 12, 1, 0, tzinfo=timezone.utc)}],
            )
        )
        rendered = status_rendering.render_status_assessment(
            verdict,
            location_hash='h',
            service='svc',
            environment='env',
            normalized_type='BREAKPOINT',
            time_window=self._time_window(),
        )
        assert 'OVERALL STATUS: ACTIVE' in rendered

    def test_error_or_pending_dispatch_renders_pending(self):
        """An ErrorOrPending verdict with no events renders PENDING."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation import (
            status_assessment,
        )

        verdict = status_assessment.ErrorOrPending(
            active=self._result(),
            ready=self._result(),
            error=self._result(),
        )
        rendered = status_rendering.render_status_assessment(
            verdict,
            location_hash='h',
            service='svc',
            environment='env',
            normalized_type='BREAKPOINT',
            time_window=self._time_window(),
        )
        assert 'OVERALL STATUS: PENDING' in rendered

    def test_unknown_verdict_raises_type_error(self):
        """An unknown verdict type raises a TypeError from the dispatcher."""
        with pytest.raises(TypeError):
            status_rendering.render_status_assessment(
                object(),  # type: ignore[arg-type]
                location_hash='h',
                service='svc',
                environment='env',
                normalized_type='BREAKPOINT',
                time_window=self._time_window(),
            )


class TestStatusAssessmentBranches:
    """Cover the empty-ACTIVE-window skip and READY/ERROR fall-through branches."""

    def test_empty_active_window_skips_active_check(self):
        """When the ACTIVE window is empty after clamping, ACTIVE is skipped."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation import (
            status_assessment,
        )

        created = datetime(2026, 3, 9, 13, 0, 0, tzinfo=timezone.utc)
        start = datetime(2026, 3, 9, 12, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 9, 12, 30, 0, tzinfo=timezone.utc)

        calls = []

        def check(status, s, e):
            calls.append(status)
            return False, [], None

        verdict, _window = status_assessment.assess(
            created_at=created,
            requested_start=start,
            query_end=end,
            check_status=check,
        )
        assert isinstance(verdict, status_assessment.ErrorOrPending)
        assert 'ACTIVE' not in calls
        assert verdict.active.error is not None
        assert verdict.active.error.startswith('Skipped:')

    def test_ready_has_events_returns_ready(self):
        """When ACTIVE is empty but READY has events, a Ready verdict results."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation import (
            status_assessment,
        )

        created = datetime(2026, 3, 9, 11, 0, 0, tzinfo=timezone.utc)
        start = datetime(2026, 3, 9, 12, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 9, 12, 30, 0, tzinfo=timezone.utc)

        def check(status, s, e):
            return (status == 'READY'), ([{'Time': start}] if status == 'READY' else []), None

        verdict, _window = status_assessment.assess(
            created_at=created,
            requested_start=start,
            query_end=end,
            check_status=check,
        )
        assert isinstance(verdict, status_assessment.Ready)


class TestParseIsoTimestamp:
    """Cover naive vs tz-aware handling in status_tools._parse_iso_timestamp."""

    def test_naive_input_assumed_utc(self):
        """A naive timestamp (no Z/offset) is tagged UTC without shifting digits."""
        parsed = status_tools._parse_iso_timestamp('2025-02-03T18:42:00')
        assert parsed.tzinfo is timezone.utc
        assert parsed.hour == 18  # not shifted into host-local time

    def test_z_suffix_parsed_as_utc(self):
        """A trailing Z is parsed as a UTC offset."""
        parsed = status_tools._parse_iso_timestamp('2025-02-03T18:42:00Z')
        assert parsed.utcoffset() == timedelta(0)

    def test_explicit_offset_preserved(self):
        """An explicit offset is preserved rather than overwritten with UTC."""
        parsed = status_tools._parse_iso_timestamp('2025-02-03T18:42:00+05:00')
        assert parsed.utcoffset() == timedelta(hours=5)


class TestStatusToolsBranches:
    """Cover gateway-error, empty-config, and missing-CreatedAt branches."""

    def test_check_status_with_time_range_gateway_error(self, monkeypatch):
        """_check_status_with_time_range maps a GatewayError to an API error string."""

        def _raise(method_name, **kwargs):
            raise status_tools.gateway.GatewayError(RuntimeError('boom'))

        monkeypatch.setattr(status_tools.gateway, 'call', _raise)
        has_events, events, error = status_tools._check_status_with_time_range(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_identifier={'LocationHash': 'h'},
            status='ACTIVE',
            start_time=datetime(2026, 3, 9, 12, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 3, 9, 12, 5, 0, tzinfo=timezone.utc),
        )
        assert has_events is False
        assert events == []
        assert error is not None
        assert 'API error: boom' in error

    def test_get_status_renders_error_for_lookup_error(self, monkeypatch):
        """A non-'missing' lookup error surfaces as an ERROR string."""
        monkeypatch.setattr(
            status_tools, 'parse_lookup_inputs', lambda **kwargs: (None, 'bad location')
        )
        rendered = status_tools.get_instrumentation_configuration_status(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
            status='READY',
        )
        assert rendered == 'ERROR: bad location'

    def test_get_status_defensive_location_none(self, monkeypatch):
        """A lookup parser returning (None, None) trips the defensive internal-error path."""
        monkeypatch.setattr(status_tools, 'parse_lookup_inputs', lambda **kwargs: (None, None))
        rendered = status_tools.get_instrumentation_configuration_status(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
            status='READY',
        )
        assert 'Internal error resolving location' in rendered

    def test_check_status_empty_config_reports_not_found(self, monkeypatch):
        """An empty Configuration block surfaces a no-instrumentation error."""
        monkeypatch.setattr(
            status_tools.gateway,
            'call',
            lambda method_name, **kwargs: {'Configuration': {}},
        )
        rendered = status_tools.check_instrumentation_status(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
            start_time='2026-03-09T12:00:00Z',
            end_time='2026-03-09T12:05:00Z',
        )
        assert 'No instrumentation found for LocationHash' in rendered

    def test_check_status_missing_created_at(self, monkeypatch):
        """A configuration lacking CreatedAt surfaces a created_at error."""
        config = _full_instrumentation_configuration()
        config.pop('CreatedAt')
        monkeypatch.setattr(
            status_tools.gateway,
            'call',
            lambda method_name, **kwargs: {'Configuration': config},
        )
        rendered = status_tools.check_instrumentation_status(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
            start_time='2026-03-09T12:00:00Z',
            end_time='2026-03-09T12:05:00Z',
        )
        assert 'CreatedAt not found' in rendered


class TestCrudToolsTtlAndFilters:
    """Cover ExpiresAt/AttributeFilters emission and code-location lookup errors."""

    def test_create_with_ttl_and_attribute_filters(self):
        """ttl_hours adds ExpiresAt and attribute_filters adds AttributeFilters."""
        stubber = _stub_application_signals()
        stubber.add_response(
            'create_instrumentation_configuration',
            {
                'InstrumentationType': 'BREAKPOINT',
                'Service': 'svc',
                'Environment': 'env',
                'SignalType': 'SNAPSHOT',
                'Location': {
                    'CodeLocation': {'Language': 'Python', 'FilePath': '/app/handler.py'}
                },
                'LocationHash': 'aaaabbbbccccdddd',
                'Description': 'MCP dynamic instrumentation',
                'ExpiresAt': datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc),
                'CaptureConfiguration': {
                    'CodeCapture': {
                        'CaptureArguments': ['order_id'],
                        'CaptureReturn': True,
                        'CaptureStackTrace': True,
                        'CaptureLimits': {},
                    }
                },
                'CreatedAt': datetime(2026, 3, 9, 12, 0, 0, tzinfo=timezone.utc),
                'ARN': 'arn:demo',
            },
        )
        rendered = crud_tools.create_instrumentation(
            instrumentation_type='BREAKPOINT',
            service='svc',
            environment='env',
            language='Python',
            file_path='/app/handler.py',
            code_unit='services.handler',
            method_name='run',
            capture_arguments=['order_id'],
            ttl_hours=3,
            attribute_filters=[{'Key': 'stage', 'Value': 'prod'}],
        )
        stubber.assert_no_pending_responses()
        assert 'Successfully created BREAKPOINT instrumentation' in rendered
        assert 'ATTRIBUTE FILTERS: 1 filter group(s) applied' in rendered

    def test_delete_renders_error_for_lookup_error(self, monkeypatch):
        """delete_instrumentation surfaces a non-'missing' lookup error as ERROR."""
        monkeypatch.setattr(
            crud_tools, 'parse_lookup_inputs', lambda **kwargs: (None, 'bad location')
        )
        rendered = crud_tools.delete_instrumentation(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
        )
        assert rendered == 'ERROR: bad location'

    def test_get_renders_error_for_lookup_error(self, monkeypatch):
        """get_instrumentation surfaces a non-'missing' lookup error as ERROR."""
        monkeypatch.setattr(
            crud_tools, 'parse_lookup_inputs', lambda **kwargs: (None, 'bad location')
        )
        rendered = crud_tools.get_instrumentation(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
        )
        assert rendered == 'ERROR: bad location'

    def test_get_reports_no_instrumentation_for_empty_config(self, monkeypatch):
        """get_instrumentation reports no-instrumentation when Configuration is empty."""
        monkeypatch.setattr(
            crud_tools.gateway,
            'call',
            lambda method_name, **kwargs: {'Configuration': {}},
        )
        rendered = crud_tools.get_instrumentation(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
        )
        assert 'No instrumentation found for' in rendered


class TestCrudToolsTypeAndDefensiveBranches:
    """Cover the invalid-type early returns and defensive location-None branches."""

    def test_list_rejects_invalid_type(self):
        """list_instrumentations short-circuits on an invalid instrumentation_type."""
        rendered = crud_tools.list_instrumentations(
            service='svc', environment='env', instrumentation_type='NOPE'
        )
        assert 'instrumentation_type must be one of' in rendered

    def test_by_arns_rejects_invalid_type(self):
        """batch_delete_instrumentations_by_arns short-circuits on an invalid type."""
        rendered = crud_tools.batch_delete_instrumentations_by_arns(
            resource_arns=['arn:demo'], instrumentation_type='NOPE'
        )
        assert 'instrumentation_type must be one of' in rendered

    def test_delete_rejects_invalid_type(self):
        """delete_instrumentation short-circuits on an invalid instrumentation_type."""
        rendered = crud_tools.delete_instrumentation(
            service='svc',
            environment='env',
            instrumentation_type='NOPE',
            location_hash='aaaabbbbccccdddd',
        )
        assert 'instrumentation_type must be one of' in rendered

    def test_get_rejects_invalid_type(self):
        """get_instrumentation short-circuits on an invalid instrumentation_type."""
        rendered = crud_tools.get_instrumentation(
            service='svc',
            environment='env',
            instrumentation_type='NOPE',
            location_hash='aaaabbbbccccdddd',
        )
        assert 'instrumentation_type must be one of' in rendered

    def test_create_defensive_location_none(self, monkeypatch):
        """A parser returning (None, None) trips the defensive internal-error path."""
        monkeypatch.setattr(crud_tools, 'parse_create_inputs', lambda **kwargs: (None, None))
        rendered = crud_tools.create_instrumentation(
            instrumentation_type='BREAKPOINT',
            service='svc',
            environment='env',
            language='Python',
            file_path='/app/h.py',
            capture_arguments=['a'],
        )
        assert 'Internal error resolving location' in rendered

    def test_delete_defensive_location_none(self, monkeypatch):
        """A lookup parser returning (None, None) trips delete's defensive path."""
        monkeypatch.setattr(crud_tools, 'parse_lookup_inputs', lambda **kwargs: (None, None))
        rendered = crud_tools.delete_instrumentation(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
        )
        assert 'Internal error resolving location' in rendered

    def test_get_defensive_location_none(self, monkeypatch):
        """A lookup parser returning (None, None) trips get's defensive path."""
        monkeypatch.setattr(crud_tools, 'parse_lookup_inputs', lambda **kwargs: (None, None))
        rendered = crud_tools.get_instrumentation(
            service='svc',
            environment='env',
            instrumentation_type='BREAKPOINT',
            location_hash='aaaabbbbccccdddd',
        )
        assert 'Internal error resolving location' in rendered
