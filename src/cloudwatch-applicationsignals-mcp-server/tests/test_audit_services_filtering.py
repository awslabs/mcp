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

"""Tests for audit_services function with instrumented service filtering."""

import pytest
from awslabs.cloudwatch_applicationsignals_mcp_server.server import audit_services
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_applicationsignals_client():
    """Mock applicationsignals client for testing."""
    mock_client = MagicMock()
    return mock_client


@pytest.fixture
def mock_execute_audit_api():
    """Mock execute_audit_api function."""
    with patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.server.execute_audit_api'
    ) as mock_execute:
        mock_execute.return_value = 'Mock audit result'
        yield mock_execute


class TestAuditServicesFiltering:
    """Test audit_services function with service filtering integration."""

    @pytest.mark.asyncio
    async def test_audit_services_with_filtering_stats(
        self, mock_applicationsignals_client, mock_execute_audit_api
    ):
        """Test audit_services includes filtering statistics in banner."""
        # Mock services response with mixed instrumentation
        mock_services_response = {
            'ServiceSummaries': [
                {
                    'KeyAttributes': {
                        'Name': 'instrumented-service',
                        'Type': 'Service',
                        'Environment': 'prod',
                    },
                    'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
                },
                {
                    'KeyAttributes': {
                        'Name': 'uninstrumented-service',
                        'Type': 'Service',
                        'Environment': 'prod',
                    },
                    'AttributeMaps': [{'InstrumentationType': 'UNINSTRUMENTED'}],
                },
                {
                    'KeyAttributes': {
                        'Name': 'aws-native-service',
                        'Type': 'Service',
                        'Environment': 'prod',
                    },
                    'AttributeMaps': [{'InstrumentationType': 'AWS_NATIVE'}],
                },
            ]
        }

        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.server.applicationsignals_client',
            mock_applicationsignals_client,
        ):
            mock_applicationsignals_client.list_services.return_value = mock_services_response

            # Mock the validation function to return the filtered services
            with patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.validate_and_enrich_service_targets'
            ) as mock_validate:
                mock_validate.return_value = [
                    {
                        'Type': 'service',
                        'Data': {
                            'Service': {
                                'Type': 'Service',
                                'Name': 'instrumented-service',
                                'Environment': 'prod',
                            }
                        },
                    }
                ]

                await audit_services(
                    service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*"}}}]'
                )

                # Verify execute_audit_api was called
                mock_execute_audit_api.assert_called_once()

                # Check the banner includes filtering statistics
                call_args = mock_execute_audit_api.call_args[0]
                banner = call_args[2]  # Third argument is the banner

                assert '🔍 Service Filtering:' in banner
                assert '1 instrumented out of 3 total services' in banner
                assert '(2 filtered out)' in banner

    @pytest.mark.asyncio
    async def test_audit_services_no_filtering_when_no_wildcards(
        self, mock_applicationsignals_client, mock_execute_audit_api
    ):
        """Test audit_services doesn't show filtering stats when no wildcards used."""
        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.server.applicationsignals_client',
            mock_applicationsignals_client,
        ):
            # Mock the validation function
            with patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.validate_and_enrich_service_targets'
            ) as mock_validate:
                mock_validate.return_value = [
                    {
                        'Type': 'service',
                        'Data': {
                            'Service': {
                                'Type': 'Service',
                                'Name': 'specific-service',
                                'Environment': 'prod',
                            }
                        },
                    }
                ]

                await audit_services(
                    service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"specific-service"}}}]',
                    next_token=None,
                )

                # Verify execute_audit_api was called
                mock_execute_audit_api.assert_called_once()

                # Check the banner doesn't include filtering statistics
                call_args = mock_execute_audit_api.call_args[0]
                banner = call_args[2]  # Third argument is the banner

                assert '🔍 Service Filtering:' not in banner

    @pytest.mark.asyncio
    async def test_audit_services_wildcard_expansion_with_filtering(
        self, mock_applicationsignals_client, mock_execute_audit_api
    ):
        """Test audit_services wildcard expansion includes filtering."""
        # Mock services response
        mock_services_response = {
            'ServiceSummaries': [
                {
                    'KeyAttributes': {
                        'Name': 'payment-service-1',
                        'Type': 'Service',
                        'Environment': 'prod',
                    },
                    'AttributeMaps': [{'InstrumentationType': 'INSTRUMENTED'}],
                },
                {
                    'KeyAttributes': {
                        'Name': 'payment-service-2',
                        'Type': 'Service',
                        'Environment': 'prod',
                    },
                    'AttributeMaps': [{'InstrumentationType': 'UNINSTRUMENTED'}],
                },
            ]
        }

        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.server.applicationsignals_client',
            mock_applicationsignals_client,
        ):
            mock_applicationsignals_client.list_services.return_value = mock_services_response

            # Mock expand_service_wildcard_patterns to return filtering stats
            with patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_service_wildcard_patterns'
            ) as mock_expand:
                mock_expand.return_value = (
                    [
                        {
                            'Type': 'service',
                            'Data': {
                                'Service': {
                                    'Type': 'Service',
                                    'Name': 'payment-service-1',
                                    'Environment': 'prod',
                                }
                            },
                        }
                    ],
                    None,  # returned_next_token
                    ['payment-service-1'],  # service_names_in_batch
                    {
                        'total_services': 2,
                        'instrumented_services': 1,
                        'filtered_out': 1,
                    },
                )

                # Mock the validation function
                with patch(
                    'awslabs.cloudwatch_applicationsignals_mcp_server.server.validate_and_enrich_service_targets'
                ) as mock_validate:
                    mock_validate.return_value = [
                        {
                            'Type': 'service',
                            'Data': {
                                'Service': {
                                    'Type': 'Service',
                                    'Name': 'payment-service-1',
                                    'Environment': 'prod',
                                }
                            },
                        }
                    ]

                    await audit_services(
                        service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*payment*"}}}]'
                    )

                    # Verify filtering statistics are included
                    call_args = mock_execute_audit_api.call_args[0]
                    banner = call_args[2]

                    assert '🔍 Service Filtering:' in banner
                    assert '1 instrumented out of 2 total services' in banner
                    assert '(1 filtered out)' in banner

    @pytest.mark.asyncio
    async def test_audit_services_no_services_after_filtering(
        self, mock_applicationsignals_client, mock_execute_audit_api
    ):
        """Test audit_services when no services remain after filtering."""
        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.server.applicationsignals_client',
            mock_applicationsignals_client,
        ):
            # Mock expand_service_wildcard_patterns to return empty results
            with patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_service_wildcard_patterns'
            ) as mock_expand:
                mock_expand.return_value = (
                    [],  # No services after filtering
                    None,  # returned_next_token
                    [],  # service_names_in_batch
                    {
                        'total_services': 2,
                        'instrumented_services': 0,
                        'filtered_out': 2,
                    },
                )

                result = await audit_services(
                    service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*"}}}]'
                )

                # Should return error message about no services found
                assert (
                    'Error: No services found matching the wildcard pattern' in result
                    or 'No services found' in result
                )

                # execute_audit_api should not be called
                mock_execute_audit_api.assert_not_called()

    @pytest.mark.asyncio
    async def test_audit_services_shorthand_format_with_wildcards(
        self, mock_applicationsignals_client, mock_execute_audit_api
    ):
        """Test audit_services with shorthand format containing wildcards."""
        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.server.applicationsignals_client',
            mock_applicationsignals_client,
        ):
            # Mock expand_service_wildcard_patterns
            with patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_service_wildcard_patterns'
            ) as mock_expand:
                mock_expand.return_value = (
                    [
                        {
                            'Type': 'service',
                            'Data': {
                                'Service': {
                                    'Type': 'Service',
                                    'Name': 'payment-service',
                                    'Environment': 'prod',
                                }
                            },
                        }
                    ],
                    None,  # returned_next_token
                    ['payment-service'],  # service_names_in_batch
                    {
                        'total_services': 3,
                        'instrumented_services': 1,
                        'filtered_out': 2,
                    },
                )

                # Mock the validation function
                with patch(
                    'awslabs.cloudwatch_applicationsignals_mcp_server.server.validate_and_enrich_service_targets'
                ) as mock_validate:
                    mock_validate.return_value = [
                        {
                            'Type': 'service',
                            'Data': {
                                'Service': {
                                    'Type': 'Service',
                                    'Name': 'payment-service',
                                    'Environment': 'prod',
                                }
                            },
                        }
                    ]

                    # Test with shorthand format
                    await audit_services(
                        service_targets='[{"Type":"service","Service":"*payment*"}]'
                    )

                    # Verify wildcard expansion was called
                    mock_expand.assert_called_once()

                    # Verify filtering statistics are included
                    call_args = mock_execute_audit_api.call_args[0]
                    banner = call_args[2]

                    assert '🔍 Service Filtering:' in banner

    @pytest.mark.asyncio
    async def test_audit_services_multiple_wildcard_targets(
        self, mock_applicationsignals_client, mock_execute_audit_api
    ):
        """Test audit_services with multiple targets containing wildcards."""
        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.server.applicationsignals_client',
            mock_applicationsignals_client,
        ):
            # Mock expand_service_wildcard_patterns
            with patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_service_wildcard_patterns'
            ) as mock_expand:
                mock_expand.return_value = (
                    [
                        {
                            'Type': 'service',
                            'Data': {
                                'Service': {
                                    'Type': 'Service',
                                    'Name': 'payment-service',
                                    'Environment': 'prod',
                                }
                            },
                        },
                        {
                            'Type': 'service',
                            'Data': {
                                'Service': {
                                    'Type': 'Service',
                                    'Name': 'user-service',
                                    'Environment': 'prod',
                                }
                            },
                        },
                    ],
                    None,  # returned_next_token
                    ['payment-service', 'user-service'],  # service_names_in_batch
                    {
                        'total_services': 5,
                        'instrumented_services': 2,
                        'filtered_out': 3,
                    },
                )

                # Mock the validation function
                with patch(
                    'awslabs.cloudwatch_applicationsignals_mcp_server.server.validate_and_enrich_service_targets'
                ) as mock_validate:
                    mock_validate.return_value = [
                        {
                            'Type': 'service',
                            'Data': {
                                'Service': {
                                    'Type': 'Service',
                                    'Name': 'payment-service',
                                    'Environment': 'prod',
                                }
                            },
                        },
                        {
                            'Type': 'service',
                            'Data': {
                                'Service': {
                                    'Type': 'Service',
                                    'Name': 'user-service',
                                    'Environment': 'prod',
                                }
                            },
                        },
                    ]

                    # Test with multiple wildcard targets
                    await audit_services(
                        service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*payment*"}}},{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*user*"}}}]'
                    )

                    # Verify filtering statistics are included
                    call_args = mock_execute_audit_api.call_args[0]
                    banner = call_args[2]

                    assert '🔍 Service Filtering:' in banner
                    assert '2 instrumented out of 5 total services' in banner
                    assert '(3 filtered out)' in banner

    @pytest.mark.asyncio
    async def test_audit_services_filtering_stats_zero_filtered(
        self, mock_applicationsignals_client, mock_execute_audit_api
    ):
        """Test audit_services when no services are filtered out."""
        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.server.applicationsignals_client',
            mock_applicationsignals_client,
        ):
            # Mock expand_service_wildcard_patterns - all services are instrumented
            with patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_service_wildcard_patterns'
            ) as mock_expand:
                mock_expand.return_value = (
                    [
                        {
                            'Type': 'service',
                            'Data': {
                                'Service': {
                                    'Type': 'Service',
                                    'Name': 'service-1',
                                    'Environment': 'prod',
                                }
                            },
                        },
                        {
                            'Type': 'service',
                            'Data': {
                                'Service': {
                                    'Type': 'Service',
                                    'Name': 'service-2',
                                    'Environment': 'prod',
                                }
                            },
                        },
                    ],
                    None,  # returned_next_token
                    ['service-1', 'service-2'],  # service_names_in_batch
                    {
                        'total_services': 2,
                        'instrumented_services': 2,
                        'filtered_out': 0,
                    },
                )

                # Mock the validation function
                with patch(
                    'awslabs.cloudwatch_applicationsignals_mcp_server.server.validate_and_enrich_service_targets'
                ) as mock_validate:
                    mock_validate.return_value = [
                        {
                            'Type': 'service',
                            'Data': {
                                'Service': {
                                    'Type': 'Service',
                                    'Name': 'service-1',
                                    'Environment': 'prod',
                                }
                            },
                        },
                        {
                            'Type': 'service',
                            'Data': {
                                'Service': {
                                    'Type': 'Service',
                                    'Name': 'service-2',
                                    'Environment': 'prod',
                                }
                            },
                        },
                    ]

                    await audit_services(
                        service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*"}}}]'
                    )

                    # Verify filtering statistics show no filtering
                    call_args = mock_execute_audit_api.call_args[0]
                    banner = call_args[2]

                    assert '🔍 Service Filtering:' in banner
                    assert '2 instrumented out of 2 total services' in banner
                    assert '(0 filtered out)' in banner

    @pytest.mark.asyncio
    async def test_audit_services_wildcard_detection_data_service_name(
        self, mock_applicationsignals_client, mock_execute_audit_api
    ):
        """Test wildcard detection in Data.Service.Name format."""
        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.server.applicationsignals_client',
            mock_applicationsignals_client,
        ):
            # Mock expand_service_wildcard_patterns
            with patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_service_wildcard_patterns'
            ) as mock_expand:
                mock_expand.return_value = (
                    [
                        {
                            'Type': 'service',
                            'Data': {
                                'Service': {
                                    'Type': 'Service',
                                    'Name': 'test-service',
                                    'Environment': 'prod',
                                }
                            },
                        }
                    ],
                    None,  # returned_next_token
                    ['test-service'],  # service_names_in_batch
                    {
                        'total_services': 1,
                        'instrumented_services': 1,
                        'filtered_out': 0,
                    },
                )

                # Mock the validation function
                with patch(
                    'awslabs.cloudwatch_applicationsignals_mcp_server.server.validate_and_enrich_service_targets'
                ) as mock_validate:
                    mock_validate.return_value = [
                        {
                            'Type': 'service',
                            'Data': {
                                'Service': {
                                    'Type': 'Service',
                                    'Name': 'test-service',
                                    'Environment': 'prod',
                                }
                            },
                        }
                    ]

                    # Test with Data.Service.Name format containing wildcard
                    await audit_services(
                        service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*test*"}}}]'
                    )

                    # Verify wildcard expansion was called
                    mock_expand.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_services_wildcard_detection_shorthand_service(
        self, mock_applicationsignals_client, mock_execute_audit_api
    ):
        """Test wildcard detection in shorthand Service format."""
        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.server.applicationsignals_client',
            mock_applicationsignals_client,
        ):
            # Mock expand_service_wildcard_patterns
            with patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_service_wildcard_patterns'
            ) as mock_expand:
                mock_expand.return_value = (
                    [
                        {
                            'Type': 'service',
                            'Data': {
                                'Service': {
                                    'Type': 'Service',
                                    'Name': 'test-service',
                                    'Environment': 'prod',
                                }
                            },
                        }
                    ],
                    None,  # returned_next_token
                    ['test-service'],  # service_names_in_batch
                    {
                        'total_services': 1,
                        'instrumented_services': 1,
                        'filtered_out': 0,
                    },
                )

                # Mock the validation function
                with patch(
                    'awslabs.cloudwatch_applicationsignals_mcp_server.server.validate_and_enrich_service_targets'
                ) as mock_validate:
                    mock_validate.return_value = [
                        {
                            'Type': 'service',
                            'Data': {
                                'Service': {
                                    'Type': 'Service',
                                    'Name': 'test-service',
                                    'Environment': 'prod',
                                }
                            },
                        }
                    ]

                    # Test with shorthand Service format containing wildcard
                    await audit_services(service_targets='[{"Type":"service","Service":"*test*"}]')

                    # Verify wildcard expansion was called
                    mock_expand.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_services_no_wildcard_detection_empty_service_name(
        self, mock_applicationsignals_client, mock_execute_audit_api
    ):
        """Test no wildcard detection when service name is empty."""
        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.server.applicationsignals_client',
            mock_applicationsignals_client,
        ):
            # Test with empty service name - this should return an error
            result = await audit_services(
                service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":""}}}]'
            )

            # Should return an error due to empty service name
            assert 'Error:' in result

            # execute_audit_api should not be called due to validation error
            mock_execute_audit_api.assert_not_called()

    @pytest.mark.asyncio
    async def test_audit_services_batching_with_filtering_stats(
        self, mock_applicationsignals_client, mock_execute_audit_api
    ):
        """Test audit_services shows both batching and filtering stats."""
        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.server.applicationsignals_client',
            mock_applicationsignals_client,
        ):
            # Mock expand_service_wildcard_patterns to return many services (trigger batching)
            with patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_service_wildcard_patterns'
            ) as mock_expand:
                # Create 10 services to trigger batching (threshold is 5)
                expanded_services = [
                    {
                        'Type': 'service',
                        'Data': {
                            'Service': {
                                'Type': 'Service',
                                'Name': f'service-{i}',
                                'Environment': 'prod',
                            }
                        },
                    }
                    for i in range(10)
                ]

                mock_expand.return_value = (
                    expanded_services,
                    None,  # returned_next_token
                    [f'service-{i}' for i in range(10)],  # service_names_in_batch
                    {
                        'total_services': 15,
                        'instrumented_services': 10,
                        'filtered_out': 5,
                    },
                )

                # Mock the validation function
                with patch(
                    'awslabs.cloudwatch_applicationsignals_mcp_server.server.validate_and_enrich_service_targets'
                ) as mock_validate:
                    mock_validate.return_value = expanded_services

                    await audit_services(
                        service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*"}}}]'
                    )

                    # Verify both filtering and batching statistics are included
                    call_args = mock_execute_audit_api.call_args[0]
                    banner = call_args[2]

                    assert '🔍 Service Filtering:' in banner
                    assert '10 instrumented out of 15 total services' in banner
                    assert '(5 filtered out)' in banner
                    assert '📦 Batching:' in banner
                    assert 'Processing 10 targets in batches of 5' in banner
