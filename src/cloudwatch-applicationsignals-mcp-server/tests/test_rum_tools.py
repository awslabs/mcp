"""Tests for rum_tools.py functions."""

import json
import pytest
from awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools import (
    analyze_rum_log_group,
    audit_rum_health,
    check_rum_data_access,
    correlate_rum_to_backend,
    create_rum_app_monitor,
    delete_rum_app_monitor,
    delete_rum_resource_policy,
    get_rum_app_launches,
    get_rum_app_monitor,
    get_rum_crashes,
    get_rum_errors,
    get_rum_metrics,
    get_rum_page_views,
    get_rum_performance,
    get_rum_resource_policy,
    get_rum_sessions,
    list_rum_app_monitors,
    list_rum_tags,
    put_rum_resource_policy,
    query_rum_events,
    tag_rum_resource,
    untag_rum_resource,
    update_rum_app_monitor,
)
from unittest.mock import MagicMock, patch


START = '2026-03-01T00:00:00Z'
END = '2026-03-18T00:00:00Z'
LOG_GROUP = '/aws/vendedlogs/RUMService_test'
ARN = 'arn:aws:rum:us-east-1:123456789012:appmonitor/test'


def _app_monitor_response(cw_log_enabled=True, enable_xray=False,
                           telemetries=None, sample_rate=1.0, allow_cookies=True):
    """Build a mock get_app_monitor response."""
    return {'AppMonitor': {
        'Name': 'test', 'Id': 'test-id', 'Domain': 'example.com', 'State': 'ACTIVE',
        'DataStorage': {'CwLog': {
            'CwLogEnabled': cw_log_enabled,
            'CwLogGroup': LOG_GROUP if cw_log_enabled else None,
        }},
        'AppMonitorConfiguration': {
            'EnableXRay': enable_xray,
            'Telemetries': telemetries or ['errors', 'performance', 'http'],
            'SessionSampleRate': sample_rate,
            'AllowCookies': allow_cookies,
        },
    }}


def _logs_result(rows=None):
    """Build a mock get_query_results response."""
    if rows is None:
        rows = [[{'field': '@timestamp', 'value': '2026-03-01'}, {'field': 'count', 'value': '42'}]]
    return {'status': 'Complete', 'results': rows, 'statistics': {'recordsMatched': float(len(rows))}}


@pytest.fixture(autouse=True)
def mock_aws_clients():
    """Mock all AWS clients used by rum_tools."""
    mock_rum = MagicMock()
    mock_logs = MagicMock()
    mock_cw = MagicMock()
    mock_xray = MagicMock()
    mock_time = MagicMock()
    mock_time.monotonic.side_effect = [0, 0, 100] * 20
    mock_time.sleep = MagicMock()

    patches = [
        patch('awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools.rum_client', mock_rum),
        patch('awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools.logs_client', mock_logs),
        patch('awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools.cloudwatch_client', mock_cw),
        patch('awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools.xray_client', mock_xray),
        patch('awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools.time', mock_time),
    ]
    for p in patches:
        p.start()
    try:
        yield {'rum_client': mock_rum, 'logs_client': mock_logs,
               'cloudwatch_client': mock_cw, 'xray_client': mock_xray, 'time': mock_time}
    finally:
        for p in patches:
            p.stop()


# --- check_rum_data_access ---


@pytest.mark.asyncio
async def test_check_rum_data_access_all_good(mock_aws_clients):
    """Test check_rum_data_access with fully configured app monitor."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response(
        cw_log_enabled=True, enable_xray=True, allow_cookies=True)
    result = json.loads(await check_rum_data_access('test'))
    assert result['state'] == 'ACTIVE'
    assert len(result['findings']) == 0
    assert len(result['capabilities']) > 0


@pytest.mark.asyncio
async def test_check_rum_data_access_cw_log_disabled(mock_aws_clients):
    """Test check_rum_data_access flags CW Logs disabled as HIGH severity."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response(cw_log_enabled=False)
    result = json.loads(await check_rum_data_access('test'))
    assert any(f['severity'] == 'HIGH' for f in result['findings'])


@pytest.mark.asyncio
async def test_check_rum_data_access_not_found(mock_aws_clients):
    """Test check_rum_data_access returns error for missing app monitor."""
    exc = type('ResourceNotFoundException', (Exception,), {})
    mock_aws_clients['rum_client'].exceptions.ResourceNotFoundException = exc
    mock_aws_clients['rum_client'].get_app_monitor.side_effect = exc('not found')
    result = json.loads(await check_rum_data_access('missing'))
    assert 'error' in result


# --- CRUD tools ---


@pytest.mark.asyncio
async def test_list_rum_app_monitors(mock_aws_clients):
    """Test list_rum_app_monitors returns paginated results."""
    paginator = MagicMock()
    paginator.paginate.return_value = [{'AppMonitorSummaries': [
        {'Name': 'app1', 'Id': 'id1', 'State': 'ACTIVE'},
    ]}]
    mock_aws_clients['rum_client'].get_paginator.return_value = paginator
    result = json.loads(await list_rum_app_monitors())
    assert result['count'] == 1
    assert result['app_monitors'][0]['Name'] == 'app1'


@pytest.mark.asyncio
async def test_get_rum_app_monitor_success(mock_aws_clients):
    """Test get_rum_app_monitor returns app monitor config."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response()
    result = json.loads(await get_rum_app_monitor('test'))
    assert result['Name'] == 'test'


@pytest.mark.asyncio
async def test_get_rum_app_monitor_error(mock_aws_clients):
    """Test get_rum_app_monitor returns error on exception."""
    mock_aws_clients['rum_client'].get_app_monitor.side_effect = Exception('boom')
    result = json.loads(await get_rum_app_monitor('test'))
    assert 'error' in result


@pytest.mark.asyncio
async def test_create_rum_app_monitor(mock_aws_clients):
    """Test create_rum_app_monitor with default CwLogEnabled=true."""
    mock_aws_clients['rum_client'].create_app_monitor.return_value = {'Id': 'new-id'}
    result = json.loads(await create_rum_app_monitor('new-app', 'example.com'))
    assert result['id'] == 'new-id'
    assert result['cw_log_enabled'] is True


@pytest.mark.asyncio
async def test_update_rum_app_monitor(mock_aws_clients):
    """Test update_rum_app_monitor with partial fields."""
    result = json.loads(await update_rum_app_monitor('test', domain='new.com'))
    mock_aws_clients['rum_client'].update_app_monitor.assert_called_once()
    assert 'updated' in result['message'].lower()


@pytest.mark.asyncio
async def test_delete_rum_app_monitor(mock_aws_clients):
    """Test delete_rum_app_monitor calls API and returns confirmation."""
    result = json.loads(await delete_rum_app_monitor('test'))
    mock_aws_clients['rum_client'].delete_app_monitor.assert_called_once_with(Name='test')
    assert 'deleted' in result['message'].lower()


@pytest.mark.asyncio
async def test_tag_rum_resource(mock_aws_clients):
    """Test tag_rum_resource parses JSON tags and calls API."""
    result = json.loads(await tag_rum_resource(ARN, '{"env":"prod"}'))
    mock_aws_clients['rum_client'].tag_resource.assert_called_once_with(
        ResourceArn=ARN, Tags={'env': 'prod'})
    assert 'added' in result['message'].lower()


@pytest.mark.asyncio
async def test_untag_rum_resource(mock_aws_clients):
    """Test untag_rum_resource parses JSON keys and calls API."""
    result = json.loads(await untag_rum_resource(ARN, '["env"]'))
    mock_aws_clients['rum_client'].untag_resource.assert_called_once_with(
        ResourceArn=ARN, TagKeys=['env'])
    assert 'removed' in result['message'].lower()


@pytest.mark.asyncio
async def test_list_rum_tags(mock_aws_clients):
    """Test list_rum_tags returns tag map."""
    mock_aws_clients['rum_client'].list_tags_for_resource.return_value = {'Tags': {'env': 'prod'}}
    result = json.loads(await list_rum_tags(ARN))
    assert result['tags'] == {'env': 'prod'}


@pytest.mark.asyncio
async def test_get_rum_resource_policy(mock_aws_clients):
    """Test get_rum_resource_policy parses policy document."""
    mock_aws_clients['rum_client'].get_resource_policy.return_value = {
        'PolicyDocument': '{"Version":"2012-10-17"}'}
    result = json.loads(await get_rum_resource_policy('test'))
    assert result['policy']['Version'] == '2012-10-17'


@pytest.mark.asyncio
async def test_put_rum_resource_policy(mock_aws_clients):
    """Test put_rum_resource_policy sets policy."""
    result = json.loads(await put_rum_resource_policy('test', '{"Version":"2012-10-17"}'))
    assert 'policy set' in result['message'].lower()


@pytest.mark.asyncio
async def test_delete_rum_resource_policy(mock_aws_clients):
    """Test delete_rum_resource_policy removes policy."""
    result = json.loads(await delete_rum_resource_policy('test'))
    assert 'deleted' in result['message'].lower()


# --- Logs Insights query tools ---


def _setup_logs_mocks(clients):
    """Configure mocks for tools that use Logs Insights."""
    clients['rum_client'].get_app_monitor.return_value = _app_monitor_response()
    clients['logs_client'].start_query.return_value = {'queryId': 'qid'}
    clients['logs_client'].get_query_results.return_value = _logs_result()


@pytest.mark.asyncio
async def test_query_rum_events_success(mock_aws_clients):
    """Test query_rum_events runs custom query against log group."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await query_rum_events('test', 'fields @timestamp', START, END))
    assert result['status'] == 'Complete'
    assert result['app_monitor'] == 'test'
    assert result['log_group'] == LOG_GROUP


@pytest.mark.asyncio
async def test_query_rum_events_cw_log_disabled(mock_aws_clients):
    """Test query_rum_events returns error when CW Logs not enabled."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response(cw_log_enabled=False)
    result = json.loads(await query_rum_events('test', 'fields @timestamp', START, END))
    assert 'error' in result


@pytest.mark.asyncio
async def test_audit_rum_health(mock_aws_clients):
    """Test audit_rum_health runs 3 parallel queries."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await audit_rum_health('test', START, END))
    assert 'error_breakdown' in result
    assert 'slowest_pages' in result
    assert 'sessions_with_errors' in result


@pytest.mark.asyncio
async def test_get_rum_errors(mock_aws_clients):
    """Test get_rum_errors returns error aggregation."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await get_rum_errors('test', START, END))
    assert result['status'] == 'Complete'


@pytest.mark.asyncio
async def test_get_rum_errors_with_filters(mock_aws_clients):
    """Test get_rum_errors with page_url and group_by filters."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await get_rum_errors('test', START, END, page_url='/checkout', group_by='browser'))
    assert result['status'] == 'Complete'


@pytest.mark.asyncio
async def test_get_rum_performance(mock_aws_clients):
    """Test get_rum_performance returns navigation timings and web vitals."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await get_rum_performance('test', START, END))
    assert 'navigation_timings' in result
    assert 'web_vitals' in result


@pytest.mark.asyncio
async def test_get_rum_sessions(mock_aws_clients):
    """Test get_rum_sessions returns session list."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await get_rum_sessions('test', START, END))
    assert result['status'] == 'Complete'


@pytest.mark.asyncio
async def test_get_rum_page_views(mock_aws_clients):
    """Test get_rum_page_views returns top pages."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await get_rum_page_views('test', START, END))
    assert result['status'] == 'Complete'


@pytest.mark.asyncio
async def test_get_rum_crashes_android(mock_aws_clients):
    """Test get_rum_crashes with android platform filter."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await get_rum_crashes('test', START, END, platform='android'))
    assert 'android' in result
    assert 'ios' not in result


@pytest.mark.asyncio
async def test_get_rum_crashes_all(mock_aws_clients):
    """Test get_rum_crashes with all platforms."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await get_rum_crashes('test', START, END, platform='all'))
    assert 'android' in result
    assert 'ios' in result


@pytest.mark.asyncio
async def test_get_rum_app_launches(mock_aws_clients):
    """Test get_rum_app_launches returns both platforms."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await get_rum_app_launches('test', START, END))
    assert 'android' in result
    assert 'ios' in result


@pytest.mark.asyncio
async def test_analyze_rum_log_group(mock_aws_clients):
    """Test analyze_rum_log_group checks anomalies and runs pattern queries."""
    _setup_logs_mocks(mock_aws_clients)
    mock_aws_clients['logs_client'].list_log_anomaly_detectors.return_value = {'anomalyDetectors': []}
    result = json.loads(await analyze_rum_log_group('test', START, END))
    assert 'anomaly_detection' in result
    assert 'top_patterns' in result
    assert 'error_patterns' in result


# --- Correlation + Metrics ---


@pytest.mark.asyncio
async def test_correlate_rum_to_backend_with_traces(mock_aws_clients):
    """Test correlate_rum_to_backend finds traces and summarizes backend services."""
    _setup_logs_mocks(mock_aws_clients)
    mock_aws_clients['logs_client'].get_query_results.return_value = _logs_result(
        rows=[[{'field': 'event_details.trace_id', 'value': '1-abc-def'},
               {'field': 'event_details.duration', 'value': '5000'}]])
    mock_aws_clients['xray_client'].batch_get_traces.return_value = {
        'Traces': [{'Id': '1-abc-def', 'Segments': [
            {'Document': json.dumps({'name': 'payment-svc', 'start_time': 1.0, 'end_time': 2.0,
                                     'error': False, 'fault': False})}
        ]}]}
    result = json.loads(await correlate_rum_to_backend('test', '/checkout', START, END))
    assert result['trace_count'] == 1
    assert 'payment-svc' in result['backend_services']


@pytest.mark.asyncio
async def test_correlate_rum_to_backend_no_traces(mock_aws_clients):
    """Test correlate_rum_to_backend returns message when no traces found."""
    _setup_logs_mocks(mock_aws_clients)
    mock_aws_clients['logs_client'].get_query_results.return_value = _logs_result(rows=[])
    result = json.loads(await correlate_rum_to_backend('test', '/checkout', START, END))
    assert 'No X-Ray trace events found' in result.get('message', '')


@pytest.mark.asyncio
async def test_get_rum_metrics_success(mock_aws_clients):
    """Test get_rum_metrics returns metric data from AWS/RUM namespace."""
    mock_aws_clients['cloudwatch_client'].get_metric_data.return_value = {
        'MetricDataResults': [{'Id': 'm0', 'Timestamps': [], 'Values': [], 'StatusCode': 'Complete'}]}
    result = json.loads(await get_rum_metrics('test', '["JsErrorCount"]', START, END))
    assert 'JsErrorCount' in result['metrics']


@pytest.mark.asyncio
async def test_get_rum_metrics_error(mock_aws_clients):
    """Test get_rum_metrics returns error on API failure."""
    mock_aws_clients['cloudwatch_client'].get_metric_data.side_effect = Exception('throttled')
    result = json.loads(await get_rum_metrics('test', '["JsErrorCount"]', START, END))
    assert 'error' in result
