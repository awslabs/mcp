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

import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.aws_clients as aws_clients
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.capture as capture
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.constants as constants
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.crud_rendering as crud_rendering
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.crud_tools as crud_tools
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.error_translation as error_translation
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.location as location
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.registration as registration
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.snapshot_parsing as snapshot_parsing
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.snapshot_rendering as snapshot_rendering
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.status_rendering as status_rendering
import awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.validation as validation
import json
import os
import pytest
from botocore.exceptions import ClientError, EndpointConnectionError, NoCredentialsError
from botocore.stub import Stubber
from datetime import datetime, timezone


class RecorderMCP:
    """Capture tool registration without depending on a live MCP server."""

    def __init__(self):
        """Initialize the recorder."""
        self.registered = []

    def tool(self):
        """Return a decorator that records the registered tool's name."""

        def _decorator(func):
            self.registered.append(func.__name__)
            return func

        return _decorator


@pytest.fixture(autouse=True)
def _reset_dynamic_instrumentation_clients():
    """Drop cached boto3 clients between tests so Stubber can target a fresh client."""
    aws_clients._reset_clients()
    yield
    aws_clients._reset_clients()


class TestBoto3ClientFactory:
    """Test the lazy boto3 client factory for dynamic instrumentation."""

    def test_application_signals_client_loads_private_model(self):
        """Application signals client loads private model."""
        client = aws_clients.get_application_signals_client()
        assert 'CreateInstrumentationConfiguration' in client.meta.service_model.operation_names
        assert client.meta.service_model.api_version == aws_clients.APPLICATION_SIGNALS_API_VERSION

    def test_application_signals_client_is_singleton(self):
        """Application signals client is singleton."""
        first = aws_clients.get_application_signals_client()
        second = aws_clients.get_application_signals_client()
        assert first is second

    def test_default_endpoint_resolution(self):
        """The client uses normal AWS endpoint resolution."""
        aws_clients._reset_clients()
        client = aws_clients.get_application_signals_client()
        assert client.meta.endpoint_url.startswith('https://')
        assert 'application-signals' in client.meta.endpoint_url


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

    def _stub_application_signals(self) -> Stubber:
        client = aws_clients.get_application_signals_client()
        stubber = Stubber(client)
        stubber.activate()
        return stubber

    def test_list_instrumentations_renders_empty_list(self):
        """List instrumentations renders empty list."""
        stubber = self._stub_application_signals()
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
        stubber = self._stub_application_signals()
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

    def test_create_instrumentation_strips_wildcard_capture_argument(self):
        """Create instrumentation strips wildcard capture argument."""
        stubber = self._stub_application_signals()
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
                        'MethodName': 'run',
                    }
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
            capture_arguments=['order_id', '*'],
        )
        stubber.assert_no_pending_responses()
        assert 'Successfully created BREAKPOINT instrumentation' in rendered
        assert 'wildcard * is not supported and was ignored' in rendered
        assert 'aaaabbbbccccdddd' in rendered

    def test_create_instrumentation_renders_client_error_with_attempted_block(self):
        """Create instrumentation renders client error with attempted block."""
        stubber = self._stub_application_signals()
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
        stubber = self._stub_application_signals()
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
        stubber = self._stub_application_signals()
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
        stubber = self._stub_application_signals()
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

    def test_normalize_status_defaults_signal_to_snapshot(self):
        """Normalize status defaults signal to snapshot."""
        normalized, error = validation.normalize_status_configurations(
            [
                {
                    'InstrumentationType': 'BREAKPOINT',
                    'LocationHash': 'aaaabbbbccccdddd',
                    'Status': 'READY',
                    'Time': '2026-03-06T00:00:00Z',
                }
            ]
        )
        assert error is None
        assert normalized is not None
        assert normalized[0]['SignalType'] == 'SNAPSHOT'

    def test_normalize_status_rejects_watcher(self):
        """Normalize status rejects watcher."""
        normalized, error = validation.normalize_status_configurations(
            [
                {
                    'InstrumentationType': 'WATCHER',
                    'SignalType': 'SNAPSHOT',
                    'LocationHash': 'aaaabbbbccccdddd',
                    'Status': 'READY',
                    'Time': '2026-03-06T00:00:00Z',
                }
            ]
        )
        assert normalized is None
        assert error is not None
        assert 'invalid InstrumentationType' in error


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
        assert '- Arguments: (none)' in rendered
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


class TestCodeInstrumentationArgumentContract:
    """Test code-instrumentation-specific guardrails."""

    def test_create_requires_capture_arguments_for_code_instrumentation(self):
        """Create requires capture arguments for code instrumentation."""
        rendered = crud_tools.create_instrumentation(
            instrumentation_type='BREAKPOINT',
            service='svc',
            environment='env',
            language='Python',
            file_path='/app/demo_app.py',
            code_unit='__main__',
            method_name='process_payment',
        )
        assert 'capture_arguments is required' in rendered
        assert 'Inspect the source file' in rendered

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
            'report_instrumentation_configuration_status',
            'search_snapshots_for_status_event',
            'get_sample_snapshot_for_breakpoint',
        ]


class TestSnapshotLogGroupResolution:
    """Test per-service snapshot log group resolution."""

    def test_substitutes_service_name(self):
        """The template is filled with the target service name."""
        assert (
            constants.resolve_snapshot_log_group('checkout-service')
            == '/aws/service-events/checkout-service'
        )


# Ensure tests don't depend on any pre-existing AWS credentials in the env.
# Stubber injects responses without making real API calls, but boto3 still
# requires *some* credentials when constructing the client. Set placeholders
# so the factory succeeds in CI environments without configured credentials.
os.environ.setdefault('AWS_ACCESS_KEY_ID', 'test')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'test')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-west-2')
