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

"""Tests for AWS IoT SiteWise Monitor Tools."""

import json
import os
import pytest
import sys
from awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_monitor import (
    describe_access_policy,
    describe_dashboard,
    describe_portal,
    describe_project,
    list_access_policies,
    list_dashboards,
    list_portals,
    list_projects,
    # Dashboard conversion functions
    convert_monitor_dashboard_to_grafana,
    convert_dashboard_by_id,
    validate_dashboard_definition,
    get_conversion_rules,
    # Helper functions for testing
    _generate_ref_id,
    _convert_position_and_size,
    _create_grafana_target,
    _convert_widget_to_panel,
)
from botocore.exceptions import ClientError
from unittest.mock import Mock, patch


# Add the project root directory and its parent to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
sys.path.insert(0, project_dir)
sys.path.insert(0, os.path.dirname(project_dir))
sys.path.insert(0, os.path.dirname(os.path.dirname(project_dir)))


class TestSiteWiseMonitor:
    """Test cases for SiteWise monitor tools."""

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_monitor.create_sitewise_client')
    def test_describe_access_policy_success(self, mock_boto_client):
        """Test successful access policy description."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'accessPolicyId': 'policy-123',
            'accessPolicyArn': 'arn:aws:iotsitewise:us-east-1:123456789012:access-policy/policy-123',
            'accessPolicyIdentity': {'user': {'id': 'user-123'}},
            'accessPolicyResource': {'portal': {'id': 'portal-123'}},
            'accessPolicyPermission': 'ADMINISTRATOR',
        }
        mock_client.describe_access_policy.return_value = mock_response

        result = describe_access_policy(access_policy_id='policy-123', region='us-east-1')

        assert result['success'] is True
        assert result['accessPolicyId'] == 'policy-123'
        mock_client.describe_access_policy.assert_called_once_with(accessPolicyId='policy-123')

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_monitor.create_sitewise_client')
    def test_describe_dashboard_success(self, mock_boto_client):
        """Test successful dashboard description."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'dashboardId': 'dashboard-123',
            'dashboardArn': 'arn:aws:iotsitewise:us-east-1:123456789012:dashboard/dashboard-123',
            'dashboardName': 'Test Dashboard',
            'projectId': 'project-123',
            'dashboardDefinition': '{}',
        }
        mock_client.describe_dashboard.return_value = mock_response

        result = describe_dashboard(dashboard_id='dashboard-123', region='us-east-1')

        assert result['success'] is True
        assert result['dashboardId'] == 'dashboard-123'
        mock_client.describe_dashboard.assert_called_once_with(dashboardId='dashboard-123')

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_monitor.create_sitewise_client')
    def test_describe_portal_success(self, mock_boto_client):
        """Test successful portal description."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'portalId': 'portal-123',
            'portalArn': 'arn:aws:iotsitewise:us-east-1:123456789012:portal/portal-123',
            'portalName': 'Test Portal',
            'portalStatus': {'state': 'ACTIVE'},
        }
        mock_client.describe_portal.return_value = mock_response

        result = describe_portal(portal_id='portal-123', region='us-east-1')

        assert result['success'] is True
        assert result['portalId'] == 'portal-123'
        mock_client.describe_portal.assert_called_once_with(portalId='portal-123')

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_monitor.create_sitewise_client')
    def test_describe_project_success(self, mock_boto_client):
        """Test successful project description."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'projectId': 'project-123',
            'projectArn': 'arn:aws:iotsitewise:us-east-1:123456789012:project/project-123',
            'projectName': 'Test Project',
            'portalId': 'portal-123',
        }
        mock_client.describe_project.return_value = mock_response

        result = describe_project(project_id='project-123', region='us-east-1')

        assert result['success'] is True
        assert result['projectId'] == 'project-123'
        mock_client.describe_project.assert_called_once_with(projectId='project-123')

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_monitor.create_sitewise_client')
    def test_list_access_policies_success(self, mock_boto_client):
        """Test successful access policies listing."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'accessPolicySummaries': [
                {'id': 'policy-1', 'identity': {'user': {'id': 'user-1'}}},
                {'id': 'policy-2', 'identity': {'user': {'id': 'user-2'}}},
            ],
            'nextToken': 'next-token-123',
        }
        mock_client.list_access_policies.return_value = mock_response

        result = list_access_policies(region='us-east-1')

        assert result['success'] is True
        assert len(result['accessPolicySummaries']) == 2
        mock_client.list_access_policies.assert_called_once_with()

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_monitor.create_sitewise_client')
    def test_list_dashboards_success(self, mock_boto_client):
        """Test successful dashboards listing."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'dashboardSummaries': [
                {'id': 'dashboard-1', 'name': 'Dashboard 1'},
                {'id': 'dashboard-2', 'name': 'Dashboard 2'},
            ],
            'nextToken': 'next-token-123',
        }
        mock_client.list_dashboards.return_value = mock_response

        result = list_dashboards(project_id='project-123', region='us-east-1')

        assert result['success'] is True
        assert len(result['dashboardSummaries']) == 2
        mock_client.list_dashboards.assert_called_once_with(projectId='project-123')

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_monitor.create_sitewise_client')
    def test_list_portals_success(self, mock_boto_client):
        """Test successful portals listing."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'portalSummaries': [
                {'id': 'portal-1', 'name': 'Portal 1'},
                {'id': 'portal-2', 'name': 'Portal 2'},
            ],
            'nextToken': 'next-token-123',
        }
        mock_client.list_portals.return_value = mock_response

        result = list_portals(region='us-east-1')

        assert result['success'] is True
        assert len(result['portalSummaries']) == 2
        mock_client.list_portals.assert_called_once_with()

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_monitor.create_sitewise_client')
    def test_list_projects_success(self, mock_boto_client):
        """Test successful projects listing."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'projectSummaries': [
                {'id': 'project-1', 'name': 'Project 1'},
                {'id': 'project-2', 'name': 'Project 2'},
            ],
            'nextToken': 'next-token-123',
        }
        mock_client.list_projects.return_value = mock_response

        result = list_projects(portal_id='portal-123', region='us-east-1')

        assert result['success'] is True
        assert len(result['projectSummaries']) == 2
        mock_client.list_projects.assert_called_once_with(portalId='portal-123')

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_monitor.create_sitewise_client')
    def test_client_error_handling(self, mock_boto_client):
        """Test that ClientError exceptions are properly handled."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        error_response = {
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'Resource not found',
            }
        }
        mock_client.describe_access_policy.side_effect = ClientError(error_response, 'DescribeAccessPolicy')

        result = describe_access_policy(access_policy_id='nonexistent-policy', region='us-east-1')

        assert result['success'] is False
        assert result['error_code'] == 'ResourceNotFoundException'
        assert 'Resource not found' in result['error']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_monitor.create_sitewise_client')
    def test_list_access_policies_with_filters(self, mock_boto_client):
        """Test list access policies with filter parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {'accessPolicySummaries': [], 'nextToken': None}
        mock_client.list_access_policies.return_value = mock_response

        result = list_access_policies(
            identity_type='USER',
            identity_id='user-123',
            resource_type='PORTAL',
            resource_id='portal-123',
            next_token='token',
            max_results=10,
            region='us-east-1'
        )

        assert result['success'] is True
        mock_client.list_access_policies.assert_called_once_with(
            identityType='USER',
            identityId='user-123',
            resourceType='PORTAL',
            resourceId='portal-123',
            nextToken='token',
            maxResults=10
        )


class TestDashboardConversion:
    """Test cases for dashboard conversion functionality."""

    def test_generate_ref_id(self):
        """Test reference ID generation."""
        assert _generate_ref_id(0) == "Query-0"
        assert _generate_ref_id(1) == "Query-1"
        assert _generate_ref_id(25) == "Query-25"
        assert _generate_ref_id(100) == "Query-100"

    def test_convert_position_and_size(self):
        """Test position and size conversion (1:4 ratio)."""
        # Test basic conversion
        result = _convert_position_and_size(0, 0, 6, 6)
        expected = {'x': 0, 'y': 0, 'w': 24, 'h': 24}
        assert result == expected

        # Test with different values
        result = _convert_position_and_size(1, 2, 3, 4)
        expected = {'x': 4, 'y': 8, 'w': 12, 'h': 16}
        assert result == expected

    def test_create_grafana_target(self):
        """Test Grafana target creation."""
        metric = {
            'assetId': 'test-asset-id',
            'propertyId': 'test-property-id'
        }

        target = _create_grafana_target(metric, 'Query-0', 'test-datasource-uid', 'us-east-1')

        assert target['assetIds'] == ['test-asset-id']
        assert target['propertyIds'] == ['test-property-id']
        assert target['refId'] == 'Query-0'
        assert target['region'] == 'us-east-1'
        assert target['queryType'] == 'PropertyValueHistory'
        assert target['datasource']['uid'] == 'test-datasource-uid'
        assert target['datasource']['type'] == 'grafana-iot-sitewise-datasource'

    def test_convert_widget_to_panel_line_chart(self):
        """Test converting sc-line-chart widget to Grafana panel."""
        widget = {
            'type': 'sc-line-chart',
            'title': 'Line Chart Widget',
            'x': 0,
            'y': 0,
            'width': 6,
            'height': 6,
            'metrics': [
                {
                    'assetId': 'test-asset-id',
                    'propertyId': 'test-property-id'
                }
            ]
        }

        panel = _convert_widget_to_panel(widget, 'test-datasource-uid', 'us-east-1')

        assert panel['type'] == 'timeseries'
        assert panel['title'] == 'Line Chart Widget'
        assert panel['gridPos'] == {'x': 0, 'y': 0, 'w': 24, 'h': 24}
        assert len(panel['targets']) == 1
        assert panel['targets'][0]['refId'] == 'Query-0'
        assert panel['targets'][0]['queryType'] == 'PropertyValueHistory'

    def test_convert_widget_to_panel_scatter_chart(self):
        """Test converting sc-scatter-chart widget to Grafana panel."""
        widget = {
            'type': 'sc-scatter-chart',
            'title': 'Scatter Chart Widget',
            'x': 1,
            'y': 1,
            'width': 3,
            'height': 3,
            'metrics': [
                {
                    'assetId': 'test-asset-id',
                    'propertyId': 'test-property-id'
                }
            ]
        }

        panel = _convert_widget_to_panel(widget, 'test-datasource-uid', 'us-east-1')

        assert panel['type'] == 'timeseries'
        assert panel['fieldConfig']['defaults']['custom']['drawStyle'] == 'points'
        assert panel['gridPos'] == {'x': 4, 'y': 4, 'w': 12, 'h': 12}

    def test_convert_widget_to_panel_bar_chart(self):
        """Test converting sc-bar-chart widget to Grafana panel."""
        widget = {
            'type': 'sc-bar-chart',
            'title': 'Bar Chart Widget',
            'x': 0,
            'y': 0,
            'width': 6,
            'height': 6,
            'metrics': [
                {
                    'assetId': 'test-asset-id',
                    'propertyId': 'test-property-id'
                }
            ]
        }

        panel = _convert_widget_to_panel(widget, 'test-datasource-uid', 'us-east-1')

        assert panel['type'] == 'timeseries'
        assert panel['fieldConfig']['defaults']['custom']['drawStyle'] == 'bars'

    def test_convert_widget_to_panel_status_grid(self):
        """Test converting sc-status-grid widget to Grafana panel."""
        widget = {
            'type': 'sc-status-grid',
            'title': 'Status Grid Widget',
            'x': 0,
            'y': 0,
            'width': 6,
            'height': 6,
            'metrics': [
                {
                    'assetId': 'test-asset-id',
                    'propertyId': 'test-property-id'
                }
            ]
        }

        panel = _convert_widget_to_panel(widget, 'test-datasource-uid', 'us-east-1')

        assert panel['type'] == 'stat'
        assert panel['targets'][0]['queryType'] == 'PropertyValue'

    def test_convert_widget_to_panel_status_timeline(self):
        """Test converting sc-status-timeline widget to Grafana panel."""
        widget = {
            'type': 'sc-status-timeline',
            'title': 'Status Timeline Widget',
            'x': 0,
            'y': 0,
            'width': 6,
            'height': 6,
            'metrics': [
                {
                    'assetId': 'test-asset-id',
                    'propertyId': 'test-property-id'
                }
            ]
        }

        panel = _convert_widget_to_panel(widget, 'test-datasource-uid', 'us-east-1')

        assert panel['type'] == 'state-timeline'
        assert panel['targets'][0]['queryType'] == 'PropertyValueHistory'

    def test_convert_widget_to_panel_kpi(self):
        """Test converting sc-kpi widget to Grafana panel."""
        widget = {
            'type': 'sc-kpi',
            'title': 'KPI Widget',
            'x': 0,
            'y': 0,
            'width': 6,
            'height': 6,
            'metrics': [
                {
                    'assetId': 'test-asset-id',
                    'propertyId': 'test-property-id'
                }
            ]
        }

        panel = _convert_widget_to_panel(widget, 'test-datasource-uid', 'us-east-1')

        assert panel['type'] == 'stat'
        assert panel['options']['graphMode'] == 'none'
        assert panel['targets'][0]['queryType'] == 'PropertyValue'

    def test_convert_widget_to_panel_table(self):
        """Test converting sc-table widget to Grafana panel."""
        widget = {
            'type': 'sc-table',
            'title': 'Table Widget',
            'x': 0,
            'y': 0,
            'width': 6,
            'height': 6,
            'metrics': [
                {
                    'assetId': 'test-asset-id',
                    'propertyId': 'test-property-id'
                }
            ]
        }

        panel = _convert_widget_to_panel(widget, 'test-datasource-uid', 'us-east-1')

        assert panel['type'] == 'table'
        assert len(panel['transformations']) == 1
        assert panel['transformations'][0]['id'] == 'reduce'
        assert panel['transformations'][0]['options']['reducers'] == ['last']
        assert panel['targets'][0]['queryType'] == 'PropertyValue'

    def test_convert_widget_multiple_metrics(self):
        """Test converting widget with multiple metrics."""
        widget = {
            'type': 'sc-line-chart',
            'title': 'Multi-Metric Widget',
            'x': 0,
            'y': 0,
            'width': 6,
            'height': 6,
            'metrics': [
                {
                    'assetId': 'asset-1',
                    'propertyId': 'property-1'
                },
                {
                    'assetId': 'asset-2',
                    'propertyId': 'property-2'
                },
                {
                    'assetId': 'asset-3',
                    'propertyId': 'property-3'
                }
            ]
        }

        panel = _convert_widget_to_panel(widget, 'test-datasource-uid', 'us-east-1')

        assert len(panel['targets']) == 3
        assert panel['targets'][0]['refId'] == 'Query-0'
        assert panel['targets'][1]['refId'] == 'Query-1'
        assert panel['targets'][2]['refId'] == 'Query-2'
        
        # First target should not have hide property, others should have hide=False
        assert 'hide' not in panel['targets'][0]
        assert panel['targets'][1]['hide'] is False
        assert panel['targets'][2]['hide'] is False

    def test_convert_monitor_dashboard_to_grafana_success(self):
        """Test successful dashboard conversion."""
        classic_dashboard = {
            "name": "Test Dashboard",
            "widgets": [
                {
                    "type": "sc-line-chart",
                    "title": "Line Chart Widget",
                    "x": 0,
                    "y": 0,
                    "height": 6,
                    "width": 6,
                    "metrics": [
                        {
                            "type": "iotsitewise",
                            "label": "Test Metric",
                            "assetId": "test-asset-id",
                            "propertyId": "test-property-id",
                            "dataType": "DOUBLE"
                        }
                    ]
                }
            ]
        }

        dashboard_json = json.dumps(classic_dashboard)

        result = convert_monitor_dashboard_to_grafana(
            dashboard_definition=dashboard_json,
            datasource_uid='test-datasource-uid',
            region='us-east-1'
        )

        assert result['success'] is True
        assert 'grafana_dashboard' in result
        
        grafana_dashboard = result['grafana_dashboard']
        assert grafana_dashboard['title'] == 'Test Dashboard'
        assert grafana_dashboard['version'] == 1
        assert len(grafana_dashboard['panels']) == 1
        
        panel = grafana_dashboard['panels'][0]
        assert panel['type'] == 'timeseries'
        assert panel['title'] == 'Line Chart Widget'
        
        # Check conversion summary
        summary = result['conversion_summary']
        assert summary['total_widgets_converted'] == 1
        assert summary['widget_types_converted'] == ['sc-line-chart']
        assert summary['total_metrics'] == 1

    def test_convert_monitor_dashboard_invalid_json(self):
        """Test dashboard conversion with invalid JSON."""
        invalid_json = '{"invalid": json}'

        result = convert_monitor_dashboard_to_grafana(
            dashboard_definition=invalid_json,
            datasource_uid='test-datasource-uid',
            region='us-east-1'
        )

        assert result['success'] is False
        assert result['error_code'] == 'InvalidJSON'
        assert 'Invalid JSON' in result['error']

    def test_convert_monitor_dashboard_custom_name_and_uid(self):
        """Test dashboard conversion with custom name and UID."""
        classic_dashboard = {
            "widgets": []
        }

        dashboard_json = json.dumps(classic_dashboard)

        result = convert_monitor_dashboard_to_grafana(
            dashboard_definition=dashboard_json,
            dashboard_name='Custom Dashboard Name',
            dashboard_uid='custom-uid-123',
            datasource_uid='test-datasource-uid',
            region='us-east-1'
        )

        assert result['success'] is True
        grafana_dashboard = result['grafana_dashboard']
        assert grafana_dashboard['title'] == 'Custom Dashboard Name'
        assert grafana_dashboard['uid'] == 'custom-uid-123'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_monitor.create_sitewise_client')
    def test_convert_dashboard_by_id_success(self, mock_boto_client):
        """Test successful dashboard conversion by ID."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        classic_dashboard = {
            "widgets": [
                {
                    "type": "sc-line-chart",
                    "title": "Test Widget",
                    "x": 0,
                    "y": 0,
                    "height": 6,
                    "width": 6,
                    "metrics": [
                        {
                            "assetId": "test-asset-id",
                            "propertyId": "test-property-id"
                        }
                    ]
                }
            ]
        }

        mock_response = {
            'dashboardId': 'dashboard-123',
            'dashboardName': 'Original Dashboard',
            'dashboardDescription': 'Test description',
            'projectId': 'project-123',
            'dashboardArn': 'arn:aws:iotsitewise:us-east-1:123456789012:dashboard/dashboard-123',
            'dashboardDefinition': json.dumps(classic_dashboard),
            'dashboardCreationDate': Mock(),
            'dashboardLastUpdateDate': Mock()
        }
        mock_response['dashboardCreationDate'].isoformat.return_value = '2023-01-01T00:00:00Z'
        mock_response['dashboardLastUpdateDate'].isoformat.return_value = '2023-01-02T00:00:00Z'
        
        mock_client.describe_dashboard.return_value = mock_response

        result = convert_dashboard_by_id(
            dashboard_id='dashboard-123',
            datasource_uid='test-datasource-uid',
            region='us-east-1'
        )

        assert result['success'] is True
        assert 'grafana_dashboard' in result
        assert 'original_dashboard' in result
        
        original = result['original_dashboard']
        assert original['dashboard_id'] == 'dashboard-123'
        assert original['dashboard_name'] == 'Original Dashboard'
        assert original['project_id'] == 'project-123'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_monitor.create_sitewise_client')
    def test_convert_dashboard_by_id_missing_definition(self, mock_boto_client):
        """Test dashboard conversion by ID with missing definition."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'dashboardId': 'dashboard-123',
            'dashboardName': 'Test Dashboard'
            # Missing dashboardDefinition
        }
        mock_client.describe_dashboard.return_value = mock_response

        result = convert_dashboard_by_id(
            dashboard_id='dashboard-123',
            datasource_uid='test-datasource-uid',
            region='us-east-1'
        )

        assert result['success'] is False
        assert result['error_code'] == 'MissingDashboardDefinition'

    def test_validate_dashboard_definition_valid(self):
        """Test validation of valid dashboard definition."""
        valid_dashboard = {
            "widgets": [
                {
                    "type": "sc-line-chart",
                    "x": 0,
                    "y": 0,
                    "width": 6,
                    "height": 6,
                    "metrics": [
                        {
                            "assetId": "test-asset",
                            "propertyId": "test-property"
                        }
                    ]
                }
            ]
        }

        result = validate_dashboard_definition(json.dumps(valid_dashboard))

        assert result['success'] is True
        assert result['valid'] is True
        assert len(result['errors']) == 0
        assert result['summary']['conversion_ready'] is True
        assert result['summary']['total_widgets'] == 1
        assert result['summary']['total_metrics'] == 1

    def test_validate_dashboard_definition_invalid(self):
        """Test validation of invalid dashboard definition."""
        invalid_dashboard = {
            "widgets": [
                {
                    "type": "sc-line-chart",
                    # Missing required fields: x, y, width, height
                    "metrics": [
                        {
                            # Missing assetId and propertyId
                        }
                    ]
                }
            ]
        }

        result = validate_dashboard_definition(json.dumps(invalid_dashboard))

        assert result['success'] is True
        assert result['valid'] is False
        assert len(result['errors']) > 0
        assert result['summary']['conversion_ready'] is False

    def test_validate_dashboard_definition_unsupported_widget(self):
        """Test validation with unsupported widget type."""
        dashboard_with_unsupported = {
            "widgets": [
                {
                    "type": "unsupported-widget-type",
                    "x": 0,
                    "y": 0,
                    "width": 6,
                    "height": 6,
                    "metrics": [
                        {
                            "assetId": "test-asset",
                            "propertyId": "test-property"
                        }
                    ]
                }
            ]
        }

        result = validate_dashboard_definition(json.dumps(dashboard_with_unsupported))

        assert result['success'] is True
        assert result['valid'] is True  # Valid structure but has warnings
        assert len(result['warnings']) > 0
        assert result['summary']['conversion_ready'] is False  # Not ready due to unsupported type
        assert 'unsupported-widget-type' in result['summary']['unsupported_types']

    def test_validate_dashboard_definition_invalid_json(self):
        """Test validation with invalid JSON."""
        invalid_json = '{"invalid": json}'

        result = validate_dashboard_definition(invalid_json)

        assert result['success'] is False
        assert result['valid'] is False
        assert result['error_code'] == 'InvalidJSON'

    def test_get_conversion_rules(self):
        """Test retrieval of conversion rules."""
        result = get_conversion_rules()

        assert result['success'] is True
        assert 'conversion_rules' in result
        
        rules = result['conversion_rules']
        assert 'dimension_scaling' in rules
        assert 'widget_mappings' in rules
        assert 'reference_id_pattern' in rules
        assert 'datasource_requirements' in rules
        
        # Check dimension scaling
        assert rules['dimension_scaling']['ratio'] == '1:4'
        
        # Check widget mappings
        widget_mappings = rules['widget_mappings']
        assert widget_mappings['sc-line-chart']['grafana_type'] == 'timeseries'
        assert widget_mappings['sc-scatter-chart']['draw_style'] == 'points'
        assert widget_mappings['sc-bar-chart']['draw_style'] == 'bars'
        assert widget_mappings['sc-status-grid']['grafana_type'] == 'stat'
        assert widget_mappings['sc-status-timeline']['grafana_type'] == 'state-timeline'
        assert widget_mappings['sc-kpi']['graph_mode'] == 'none'
        assert widget_mappings['sc-table']['grafana_type'] == 'table'
        
        # Check reference ID pattern
        ref_pattern = rules['reference_id_pattern']
        assert 'Query-0' in ref_pattern['examples']
        assert 'Query-100' in ref_pattern['examples']


if __name__ == '__main__':
    pytest.main([__file__])
