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

"""AWS IoT SiteWise Monitor Read-Only APIs and Dashboard Conversion Tools."""

import json
import uuid
from awslabs.aws_iot_sitewise_mcp_server.client import create_sitewise_client
from awslabs.aws_iot_sitewise_mcp_server.tool_metadata import tool_metadata
from botocore.exceptions import ClientError
from mcp.server.fastmcp.tools import Tool
from pydantic import Field
from pydantic.fields import FieldInfo
from typing import Any, Dict, List, Optional


@tool_metadata(readonly=True)
def describe_access_policy(
    access_policy_id: str = Field(..., description='The ID of the access policy'),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Describe an access policy."""
    try:
        client = create_sitewise_client(region)
        response = client.describe_access_policy(accessPolicyId=access_policy_id)
        return {'success': True, **response}
    except ClientError as e:
        return {'success': False, 'error': str(e), 'error_code': e.response['Error']['Code']}


@tool_metadata(readonly=True)
def describe_dashboard(
    dashboard_id: str = Field(..., description='The ID of the dashboard'),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Describe a dashboard."""
    try:
        client = create_sitewise_client(region)
        response = client.describe_dashboard(dashboardId=dashboard_id)
        return {'success': True, **response}
    except ClientError as e:
        return {'success': False, 'error': str(e), 'error_code': e.response['Error']['Code']}


@tool_metadata(readonly=True)
def describe_portal(
    portal_id: str = Field(..., description='The ID of the portal'),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Describe a portal."""
    try:
        client = create_sitewise_client(region)
        response = client.describe_portal(portalId=portal_id)
        return {'success': True, **response}
    except ClientError as e:
        return {'success': False, 'error': str(e), 'error_code': e.response['Error']['Code']}


@tool_metadata(readonly=True)
def describe_project(
    project_id: str = Field(..., description='The ID of the project'),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Describe a project."""
    try:
        client = create_sitewise_client(region)
        response = client.describe_project(projectId=project_id)
        return {'success': True, **response}
    except ClientError as e:
        return {'success': False, 'error': str(e), 'error_code': e.response['Error']['Code']}


@tool_metadata(readonly=True)
def list_access_policies(
    identity_type: Optional[str] = Field(None, description='The type of identity (USER, GROUP, IAM)'),
    identity_id: Optional[str] = Field(None, description='The ARN of the identity'),
    resource_type: Optional[str] = Field(None, description='The type of resource (PORTAL, PROJECT)'),
    resource_id: Optional[str] = Field(None, description='The ID of the resource'),
    next_token: Optional[str] = Field(None, description='Token for pagination'),
    max_results: Optional[int] = Field(None, description='Maximum number of results'),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """List access policies."""
    try:
        client = create_sitewise_client(region)
        params = {}
        if identity_type and not isinstance(identity_type, FieldInfo):
            params['identityType'] = identity_type
        if identity_id and not isinstance(identity_id, FieldInfo):
            params['identityId'] = identity_id
        if resource_type and not isinstance(resource_type, FieldInfo):
            params['resourceType'] = resource_type
        if resource_id and not isinstance(resource_id, FieldInfo):
            params['resourceId'] = resource_id
        if next_token and not isinstance(next_token, FieldInfo):
            params['nextToken'] = next_token
        if max_results and not isinstance(max_results, FieldInfo):
            params['maxResults'] = max_results
        
        response = client.list_access_policies(**params)
        return {'success': True, **response}
    except ClientError as e:
        return {'success': False, 'error': str(e), 'error_code': e.response['Error']['Code']}


@tool_metadata(readonly=True)
def list_dashboards(
    project_id: str = Field(..., description='The ID of the project'),
    next_token: Optional[str] = Field(None, description='Token for pagination'),
    max_results: Optional[int] = Field(None, description='Maximum number of results'),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """List dashboards in a project."""
    try:
        client = create_sitewise_client(region)
        params = {'projectId': project_id}
        if next_token and not isinstance(next_token, FieldInfo):
            params['nextToken'] = next_token
        if max_results and not isinstance(max_results, FieldInfo):
            params['maxResults'] = max_results
        
        response = client.list_dashboards(**params)
        return {'success': True, **response}
    except ClientError as e:
        return {'success': False, 'error': str(e), 'error_code': e.response['Error']['Code']}


@tool_metadata(readonly=True)
def list_portals(
    next_token: Optional[str] = Field(None, description='Token for pagination'),
    max_results: Optional[int] = Field(None, description='Maximum number of results'),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """List portals."""
    try:
        client = create_sitewise_client(region)
        params = {}
        if next_token and not isinstance(next_token, FieldInfo):
            params['nextToken'] = next_token
        if max_results and not isinstance(max_results, FieldInfo):
            params['maxResults'] = max_results
        
        response = client.list_portals(**params)
        return {'success': True, **response}
    except ClientError as e:
        return {'success': False, 'error': str(e), 'error_code': e.response['Error']['Code']}


@tool_metadata(readonly=True)
def list_projects(
    portal_id: str = Field(..., description='The ID of the portal'),
    next_token: Optional[str] = Field(None, description='Token for pagination'),
    max_results: Optional[int] = Field(None, description='Maximum number of results'),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """List projects in a portal."""
    try:
        client = create_sitewise_client(region)
        params = {'portalId': portal_id}
        if next_token and not isinstance(next_token, FieldInfo):
            params['nextToken'] = next_token
        if max_results and not isinstance(max_results, FieldInfo):
            params['maxResults'] = max_results
        
        response = client.list_projects(**params)
        return {'success': True, **response}
    except ClientError as e:
        return {'success': False, 'error': str(e), 'error_code': e.response['Error']['Code']}


# Dashboard Conversion Helper Functions

def _generate_ref_id(index: int) -> str:
    """Generate reference ID for Grafana targets using Query-{index} naming scheme.
    
    Pattern: Query-0, Query-1, Query-2, ... (unlimited support)
    """
    return f"Query-{index}"


def _convert_position_and_size(x: int, y: int, width: int, height: int) -> Dict[str, int]:
    """Convert classic monitor dashboard position and size to Grafana grid position.
    
    Classic monitor dashboard max width is 6, Grafana max width is 24.
    Conversion ratio is 1:4 for all dimensions.
    """
    return {
        'x': x * 4,
        'y': y * 4,
        'w': width * 4,
        'h': height * 4
    }


def _create_grafana_target(metric: Dict[str, Any], ref_id: str, datasource_uid: str, region: str, query_type: str = 'PropertyValueHistory') -> Dict[str, Any]:
    """Create a Grafana target from a classic monitor metric."""
    return {
        'assetIds': [metric['assetId']],
        'clientCache': True,
        'datasource': {
            'type': 'grafana-iot-sitewise-datasource',
            'uid': datasource_uid
        },
        'flattenL4e': True,
        'maxPageAggregations': 1,
        'propertyIds': [metric['propertyId']],
        'queryType': query_type,
        'refId': ref_id,
        'region': region,
        'timeOrdering': 'ASCENDING'
    }


def _convert_widget_to_panel(widget: Dict[str, Any], datasource_uid: str, region: str) -> Dict[str, Any]:
    """Convert a classic monitor widget to a Grafana panel."""
    widget_type = widget['type']
    title = widget.get('title', 'Widget Title')
    
    # Convert position and size
    grid_pos = _convert_position_and_size(
        widget['x'], widget['y'], widget['width'], widget['height']
    )
    
    # Create targets from metrics
    targets = []
    
    for i, metric in enumerate(widget.get('metrics', [])):
        ref_id = _generate_ref_id(i)
        query_type = 'PropertyValueHistory'
        
        # Use PropertyValue for stat panels (status-grid, kpi, table)
        if widget_type in ['sc-status-grid', 'sc-kpi', 'sc-table']:
            query_type = 'PropertyValue'
        
        target = _create_grafana_target(metric, ref_id, datasource_uid, region, query_type)
        
        # Hide additional targets except the first one
        if i > 0:
            target['hide'] = False
            
        targets.append(target)
    
    # Base panel structure
    panel = {
        'datasource': {
            'type': 'grafana-iot-sitewise-datasource',
            'uid': datasource_uid
        },
        'gridPos': grid_pos,
        'targets': targets,
        'title': title
    }
    
    # Widget-specific configurations
    if widget_type == 'sc-line-chart':
        panel['type'] = 'timeseries'
        # Line chart is the default for timeseries, no additional config needed
        
    elif widget_type == 'sc-scatter-chart':
        panel['type'] = 'timeseries'
        panel['fieldConfig'] = {
            'defaults': {
                'custom': {
                    'drawStyle': 'points'
                }
            }
        }
        
    elif widget_type == 'sc-bar-chart':
        panel['type'] = 'timeseries'
        panel['fieldConfig'] = {
            'defaults': {
                'custom': {
                    'drawStyle': 'bars'
                }
            }
        }
        
    elif widget_type == 'sc-status-grid':
        panel['type'] = 'stat'
        
    elif widget_type == 'sc-status-timeline':
        panel['type'] = 'state-timeline'
        
    elif widget_type == 'sc-kpi':
        panel['type'] = 'stat'
        panel['options'] = {
            'graphMode': 'none'
        }
        
    elif widget_type == 'sc-table':
        panel['type'] = 'table'
        panel['transformations'] = [
            {
                'id': 'reduce',
                'options': {
                    'reducers': ['last']
                }
            }
        ]
    
    return panel


@tool_metadata(readonly=True)
def convert_monitor_dashboard_to_grafana(
    dashboard_definition: str = Field(..., description='JSON string of the classic monitor dashboard definition'),
    dashboard_name: Optional[str] = Field(None, description='Name for the Grafana dashboard (defaults to extracted from definition)'),
    datasource_uid: str = Field(..., description='UID of the Grafana IoT SiteWise datasource'),
    region: str = Field('us-east-1', description='AWS region for the datasource'),
    dashboard_uid: Optional[str] = Field(None, description='Custom UID for the Grafana dashboard (auto-generated if not provided)')
) -> Dict[str, Any]:
    """Convert a classic monitor dashboard definition to Grafana dashboard format.
    
    This tool converts AWS IoT SiteWise classic monitor dashboards to Grafana dashboard format
    following the conversion rules specified in the ConvertionContext.md file.
    
    Supported widget types:
    - sc-line-chart -> timeseries with line style
    - sc-scatter-chart -> timeseries with points style  
    - sc-bar-chart -> timeseries with bars style
    - sc-status-grid -> stat panel
    - sc-status-timeline -> state-timeline panel
    - sc-kpi -> stat panel with no graph mode
    - sc-table -> table panel with transformations
    
    The conversion follows these rules:
    - Widget dimensions are scaled 1:4 (classic max width 6 -> Grafana max width 24)
    - Position coordinates are scaled 1:4
    - Each metric becomes a Grafana target with Query-{index} reference IDs
    - Query types are automatically selected based on widget type
    """
    try:
        # Parse the dashboard definition
        try:
            dashboard_def = json.loads(dashboard_definition)
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'error': f'Invalid JSON in dashboard definition: {str(e)}',
                'error_code': 'InvalidJSON'
            }
        
        # Extract dashboard name
        if not dashboard_name or isinstance(dashboard_name, FieldInfo):
            dashboard_name = dashboard_def.get('name', 'Converted Dashboard')
        
        # Generate dashboard UID if not provided
        if not dashboard_uid or isinstance(dashboard_uid, FieldInfo):
            dashboard_uid = str(uuid.uuid4()).replace('-', '')[:16]
        
        # Convert widgets to panels
        panels = []
        for widget in dashboard_def.get('widgets', []):
            panel = _convert_widget_to_panel(widget, datasource_uid, region)
            panels.append(panel)
        
        # Create Grafana dashboard structure
        grafana_dashboard = {
            'panels': panels,
            'title': dashboard_name,
            'uid': dashboard_uid,
            'version': 1
        }
        
        return {
            'success': True,
            'grafana_dashboard': grafana_dashboard,
            'conversion_summary': {
                'total_widgets_converted': len(panels),
                'widget_types_converted': list(set(widget['type'] for widget in dashboard_def.get('widgets', []))),
                'dashboard_name': dashboard_name,
                'dashboard_uid': dashboard_uid,
                'total_metrics': sum(len(widget.get('metrics', [])) for widget in dashboard_def.get('widgets', []))
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Conversion error: {str(e)}',
            'error_code': 'ConversionError'
        }


@tool_metadata(readonly=True)
def convert_dashboard_by_id(
    dashboard_id: str = Field(..., description='The ID of the classic monitor dashboard to convert'),
    datasource_uid: str = Field(..., description='UID of the Grafana IoT SiteWise datasource'),
    dashboard_name: Optional[str] = Field(None, description='Name for the Grafana dashboard (defaults to original dashboard name)'),
    dashboard_uid: Optional[str] = Field(None, description='Custom UID for the Grafana dashboard (auto-generated if not provided)'),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Fetch a classic monitor dashboard by ID and convert it to Grafana format.
    
    This tool first retrieves the dashboard definition from AWS IoT SiteWise using the dashboard ID,
    then converts it to Grafana dashboard format using the conversion rules.
    """
    try:
        # First, get the dashboard definition
        client = create_sitewise_client(region)
        response = client.describe_dashboard(dashboardId=dashboard_id)
        
        if not response.get('dashboardDefinition'):
            return {
                'success': False,
                'error': 'Dashboard definition not found in response',
                'error_code': 'MissingDashboardDefinition'
            }
        
        # Use the dashboard name from the response if not provided
        if not dashboard_name or isinstance(dashboard_name, FieldInfo):
            dashboard_name = response.get('dashboardName', 'Converted Dashboard')
        
        # Handle dashboard_uid parameter
        if isinstance(dashboard_uid, FieldInfo):
            dashboard_uid = None
        
        # Convert the dashboard
        conversion_result = convert_monitor_dashboard_to_grafana(
            dashboard_definition=response['dashboardDefinition'],
            dashboard_name=dashboard_name,
            datasource_uid=datasource_uid,
            region=region,
            dashboard_uid=dashboard_uid
        )
        
        if conversion_result['success']:
            # Add original dashboard metadata to the result
            conversion_result['original_dashboard'] = {
                'dashboard_id': dashboard_id,
                'dashboard_name': response.get('dashboardName'),
                'dashboard_description': response.get('dashboardDescription'),
                'project_id': response.get('projectId'),
                'dashboard_arn': response.get('dashboardArn'),
                'creation_date': response.get('dashboardCreationDate').isoformat() if response.get('dashboardCreationDate') else None,
                'last_update_date': response.get('dashboardLastUpdateDate').isoformat() if response.get('dashboardLastUpdateDate') else None
            }
        
        return conversion_result
        
    except ClientError as e:
        return {
            'success': False,
            'error': f'AWS API error: {str(e)}',
            'error_code': e.response['Error']['Code']
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Conversion error: {str(e)}',
            'error_code': 'ConversionError'
        }


@tool_metadata(readonly=True)
def validate_dashboard_definition(
    dashboard_definition: str = Field(..., description='JSON string of the dashboard definition to validate')
) -> Dict[str, Any]:
    """Validate a classic monitor dashboard definition for conversion compatibility.
    
    This tool checks if a dashboard definition is valid and identifies any potential
    issues that might affect the conversion to Grafana format.
    """
    try:
        # Parse the dashboard definition
        try:
            dashboard_def = json.loads(dashboard_definition)
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'valid': False,
                'error': f'Invalid JSON: {str(e)}',
                'error_code': 'InvalidJSON'
            }
        
        validation_results = {
            'success': True,
            'valid': True,
            'warnings': [],
            'errors': [],
            'summary': {}
        }
        
        # Check for required fields
        if 'widgets' not in dashboard_def:
            validation_results['errors'].append('Missing required field: widgets')
            validation_results['valid'] = False
        
        widgets = dashboard_def.get('widgets', [])
        validation_results['summary']['total_widgets'] = len(widgets)
        
        # Supported widget types
        supported_types = [
            'sc-line-chart', 'sc-scatter-chart', 'sc-bar-chart',
            'sc-status-grid', 'sc-status-timeline', 'sc-kpi', 'sc-table'
        ]
        
        widget_types = []
        unsupported_types = []
        total_metrics = 0
        
        for i, widget in enumerate(widgets):
            widget_type = widget.get('type')
            if not widget_type:
                validation_results['errors'].append(f'Widget {i}: Missing type field')
                validation_results['valid'] = False
                continue
            
            widget_types.append(widget_type)
            
            if widget_type not in supported_types:
                unsupported_types.append(widget_type)
                validation_results['warnings'].append(f'Widget {i}: Unsupported type "{widget_type}"')
            
            # Check required widget fields
            required_fields = ['x', 'y', 'width', 'height']
            for field in required_fields:
                if field not in widget:
                    validation_results['errors'].append(f'Widget {i}: Missing required field "{field}"')
                    validation_results['valid'] = False
            
            # Check metrics
            metrics = widget.get('metrics', [])
            total_metrics += len(metrics)
            
            if not metrics:
                validation_results['warnings'].append(f'Widget {i}: No metrics defined')
            
            for j, metric in enumerate(metrics):
                if 'assetId' not in metric:
                    validation_results['errors'].append(f'Widget {i}, Metric {j}: Missing assetId')
                    validation_results['valid'] = False
                if 'propertyId' not in metric:
                    validation_results['errors'].append(f'Widget {i}, Metric {j}: Missing propertyId')
                    validation_results['valid'] = False
        
        validation_results['summary']['widget_types'] = list(set(widget_types))
        validation_results['summary']['supported_types'] = [t for t in widget_types if t in supported_types]
        validation_results['summary']['unsupported_types'] = list(set(unsupported_types))
        validation_results['summary']['total_metrics'] = total_metrics
        validation_results['summary']['conversion_ready'] = validation_results['valid'] and len(unsupported_types) == 0
        
        return validation_results
        
    except Exception as e:
        return {
            'success': False,
            'valid': False,
            'error': f'Validation error: {str(e)}',
            'error_code': 'ValidationError'
        }


@tool_metadata(readonly=True)
def get_conversion_rules() -> Dict[str, Any]:
    """Get the conversion rules for classic monitor dashboard to Grafana dashboard conversion.
    
    This tool returns the detailed conversion rules and mappings used by the conversion functions.
    """
    return {
        'success': True,
        'conversion_rules': {
            'dimension_scaling': {
                'ratio': '1:4',
                'description': 'Classic monitor max width 6 -> Grafana max width 24',
                'applies_to': ['x', 'y', 'width', 'height']
            },
            'widget_mappings': {
                'sc-line-chart': {
                    'grafana_type': 'timeseries',
                    'draw_style': 'line',
                    'query_type': 'PropertyValueHistory'
                },
                'sc-scatter-chart': {
                    'grafana_type': 'timeseries',
                    'draw_style': 'points',
                    'query_type': 'PropertyValueHistory'
                },
                'sc-bar-chart': {
                    'grafana_type': 'timeseries',
                    'draw_style': 'bars',
                    'query_type': 'PropertyValueHistory'
                },
                'sc-status-grid': {
                    'grafana_type': 'stat',
                    'query_type': 'PropertyValue'
                },
                'sc-status-timeline': {
                    'grafana_type': 'state-timeline',
                    'query_type': 'PropertyValueHistory'
                },
                'sc-kpi': {
                    'grafana_type': 'stat',
                    'graph_mode': 'none',
                    'query_type': 'PropertyValue',
                    'note': 'Classic monitor trend comparison not available in Grafana'
                },
                'sc-table': {
                    'grafana_type': 'table',
                    'query_type': 'PropertyValue',
                    'transformations': ['reduce with last reducer'],
                    'columns': [
                        {'name': 'Property', 'content': 'Asset Name and Property Name'},
                        {'name': 'Latest value', 'content': 'Latest property value'}
                    ]
                }
            },
            'reference_id_pattern': {
                'description': 'Unlimited reference IDs using Query-{index} naming scheme',
                'examples': ['Query-0', 'Query-1', 'Query-2', 'Query-100']
            },
            'datasource_requirements': {
                'type': 'grafana-iot-sitewise-datasource',
                'required_fields': ['uid', 'region']
            }
        }
    }


# Create MCP tools
describe_access_policy_tool = Tool.from_function(
    fn=describe_access_policy,
    name='describe_access_policy',
    description='Describe an access policy.',
)

describe_dashboard_tool = Tool.from_function(
    fn=describe_dashboard,
    name='describe_dashboard',
    description='Describe a dashboard.',
)

describe_portal_tool = Tool.from_function(
    fn=describe_portal,
    name='describe_portal',
    description='Describe a portal.',
)

describe_project_tool = Tool.from_function(
    fn=describe_project,
    name='describe_project',
    description='Describe a project.',
)

list_access_policies_tool = Tool.from_function(
    fn=list_access_policies,
    name='list_access_policies',
    description='List access policies.',
)

list_dashboards_tool = Tool.from_function(
    fn=list_dashboards,
    name='list_dashboards',
    description='List dashboards in a project.',
)

list_portals_tool = Tool.from_function(
    fn=list_portals,
    name='list_portals',
    description='List portals.',
)

list_projects_tool = Tool.from_function(
    fn=list_projects,
    name='list_projects',
    description='List projects in a portal.',
)

convert_monitor_dashboard_to_grafana_tool = Tool.from_function(
    fn=convert_monitor_dashboard_to_grafana,
    name='convert_monitor_dashboard_to_grafana',
    description='Convert a classic monitor dashboard definition to Grafana dashboard format.',
)

convert_dashboard_by_id_tool = Tool.from_function(
    fn=convert_dashboard_by_id,
    name='convert_dashboard_by_id',
    description='Fetch a classic monitor dashboard by ID and convert it to Grafana format.',
)

validate_dashboard_definition_tool = Tool.from_function(
    fn=validate_dashboard_definition,
    name='validate_dashboard_definition',
    description='Validate a classic monitor dashboard definition for conversion compatibility.',
)

get_conversion_rules_tool = Tool.from_function(
    fn=get_conversion_rules,
    name='get_conversion_rules',
    description='Get the conversion rules for classic monitor dashboard to Grafana dashboard conversion.',
)
