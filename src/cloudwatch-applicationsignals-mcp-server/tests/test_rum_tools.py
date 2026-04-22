"""Tests for rum_tools.py — all calls go through the unified rum() dispatcher."""

import json
import pytest
from awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools import rum
from unittest.mock import MagicMock, patch


START = '2026-03-01T00:00:00Z'
END = '2026-03-18T00:00:00Z'
LOG_GROUP = '/aws/vendedlogs/RUMService_test'


def _app_monitor_response(cw_log_enabled=True, enable_xray=False,
                           telemetries=None, sample_rate=1.0, allow_cookies=True,
                           platform='Web'):
    """Build a mock get_app_monitor response."""
    return {'AppMonitor': {
        'Name': 'test', 'Id': 'test-id', 'Domain': 'example.com', 'State': 'ACTIVE',
        'Platform': platform,
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
    mock_appsignals = MagicMock()
    mock_time = MagicMock()
    _time_counter = iter(range(0, 10000, 1))
    mock_time.monotonic.side_effect = lambda: next(_time_counter)
    mock_time.sleep = MagicMock()

    patches = [
        patch('awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools.rum_client', mock_rum),
        patch('awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools.logs_client', mock_logs),
        patch('awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools.cloudwatch_client', mock_cw),
        patch('awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools.xray_client', mock_xray),
        patch('awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools.applicationsignals_client', mock_appsignals),
        patch('awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools.time', mock_time),
    ]
    for p in patches:
        p.start()
    try:
        yield {'rum_client': mock_rum, 'logs_client': mock_logs,
               'cloudwatch_client': mock_cw, 'xray_client': mock_xray,
               'applicationsignals_client': mock_appsignals, 'time': mock_time}
    finally:
        for p in patches:
            p.stop()


# --- Unknown action ---


@pytest.mark.asyncio
async def test_unknown_action():
    result = json.loads(await rum(action='bogus'))
    assert 'error' in result
    assert 'available_actions' in result


# --- Discovery ---


@pytest.mark.asyncio
async def test_check_data_access_all_good(mock_aws_clients):
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response(
        cw_log_enabled=True, enable_xray=True, allow_cookies=True)
    result = json.loads(await rum(action='check_data_access', app_monitor_name='test'))
    assert result['state'] == 'ACTIVE'
    assert len(result['findings']) == 0


@pytest.mark.asyncio
async def test_check_data_access_cw_log_disabled(mock_aws_clients):
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response(cw_log_enabled=False)
    result = json.loads(await rum(action='check_data_access', app_monitor_name='test'))
    assert any(f['severity'] == 'HIGH' for f in result['findings'])


@pytest.mark.asyncio
async def test_check_data_access_xray_disabled(mock_aws_clients):
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response(enable_xray=False)
    result = json.loads(await rum(action='check_data_access', app_monitor_name='test'))
    xray_finding = [f for f in result['findings'] if 'X-Ray' in f['issue']]
    assert len(xray_finding) == 1
    assert xray_finding[0]['severity'] == 'MEDIUM'
    assert 'correlate' in xray_finding[0]['impact'].lower()


@pytest.mark.asyncio
async def test_check_data_access_not_found(mock_aws_clients):
    exc = type('ResourceNotFoundException', (Exception,), {})
    mock_aws_clients['rum_client'].exceptions.ResourceNotFoundException = exc
    mock_aws_clients['rum_client'].get_app_monitor.side_effect = exc('not found')
    result = json.loads(await rum(action='check_data_access', app_monitor_name='missing'))
    assert 'error' in result


@pytest.mark.asyncio
async def test_list_monitors(mock_aws_clients):
    paginator = MagicMock()
    paginator.paginate.return_value = [{'AppMonitorSummaries': [
        {'Name': 'app1', 'Id': 'id1', 'State': 'ACTIVE'},
    ]}]
    mock_aws_clients['rum_client'].get_paginator.return_value = paginator
    result = json.loads(await rum(action='list_monitors'))
    assert result['count'] == 1


@pytest.mark.asyncio
async def test_get_monitor(mock_aws_clients):
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response()
    result = json.loads(await rum(action='get_monitor', app_monitor_name='test'))
    assert result['Name'] == 'test'


@pytest.mark.asyncio
async def test_get_monitor_error(mock_aws_clients):
    mock_aws_clients['rum_client'].get_app_monitor.side_effect = Exception('boom')
    result = json.loads(await rum(action='get_monitor', app_monitor_name='test'))
    assert 'error' in result


@pytest.mark.asyncio
async def test_list_tags(mock_aws_clients):
    mock_aws_clients['rum_client'].list_tags_for_resource.return_value = {'Tags': {'env': 'prod'}}
    result = json.loads(await rum(action='list_tags', resource_arn='arn:aws:rum:us-east-1:123:appmonitor/test'))
    assert result['tags'] == {'env': 'prod'}


@pytest.mark.asyncio
async def test_get_policy(mock_aws_clients):
    mock_aws_clients['rum_client'].get_resource_policy.return_value = {
        'PolicyDocument': '{"Version":"2012-10-17"}'}
    result = json.loads(await rum(action='get_policy', app_monitor_name='test'))
    assert result['policy']['Version'] == '2012-10-17'


# --- Logs Insights query tools ---


def _setup_logs_mocks(clients):
    clients['rum_client'].get_app_monitor.return_value = _app_monitor_response()
    clients['logs_client'].start_query.return_value = {'queryId': 'qid'}
    clients['logs_client'].get_query_results.return_value = _logs_result()


@pytest.mark.asyncio
async def test_query(mock_aws_clients):
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await rum(action='query', app_monitor_name='test',
                                  query_string='fields @timestamp', start_time=START, end_time=END))
    assert result['status'] == 'Complete'
    assert result['log_group'] == LOG_GROUP


@pytest.mark.asyncio
async def test_query_cw_log_disabled(mock_aws_clients):
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response(cw_log_enabled=False)
    result = json.loads(await rum(action='query', app_monitor_name='test',
                                  query_string='fields @timestamp', start_time=START, end_time=END))
    assert 'error' in result


@pytest.mark.asyncio
async def test_health(mock_aws_clients):
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await rum(action='health', app_monitor_name='test',
                                  start_time=START, end_time=END))
    assert 'error_breakdown' in result
    assert 'slowest_pages' in result
    assert 'sessions_with_errors' in result
    assert 'previous_period' not in result


@pytest.mark.asyncio
async def test_health_compare_previous(mock_aws_clients):
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await rum(action='health', app_monitor_name='test',
                                  start_time=START, end_time=END, compare_previous=True))
    assert 'error_breakdown' in result
    assert 'previous_period' in result
    assert 'error_breakdown' in result['previous_period']


@pytest.mark.asyncio
async def test_errors(mock_aws_clients):
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await rum(action='errors', app_monitor_name='test',
                                  start_time=START, end_time=END))
    assert result['status'] == 'Complete'


@pytest.mark.asyncio
async def test_errors_with_filters(mock_aws_clients):
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await rum(action='errors', app_monitor_name='test',
                                  start_time=START, end_time=END,
                                  page_url='/checkout', group_by='browser'))
    assert result['status'] == 'Complete'


@pytest.mark.asyncio
async def test_performance(mock_aws_clients):
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await rum(action='performance', app_monitor_name='test',
                                  start_time=START, end_time=END))
    assert 'navigation_timings' in result
    assert 'web_vitals' in result


@pytest.mark.asyncio
async def test_performance_vitals_bucketing(mock_aws_clients):
    """Test that Web Vitals results get good/needs-improvement/poor assessment."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response()
    mock_aws_clients['logs_client'].start_query.return_value = {'queryId': 'qid'}
    # Return a CLS result with p90=0.05 (good) and LCP with p90=5000 (poor)
    call_count = [0]
    def mock_get_results(**kwargs):
        call_count[0] += 1
        if call_count[0] <= 1:  # nav query
            return _logs_result()
        # vitals query
        return {'status': 'Complete', 'results': [
            [{'field': 'event_type', 'value': 'com.amazon.rum.cumulative_layout_shift_event'},
             {'field': 'p90', 'value': '0.05'}, {'field': 'p50', 'value': '0.02'},
             {'field': 'p99', 'value': '0.1'}, {'field': 'samples', 'value': '100'},
             {'field': 'metadata.pageId', 'value': '/home'}],
            [{'field': 'event_type', 'value': 'com.amazon.rum.largest_contentful_paint_event'},
             {'field': 'p90', 'value': '5000'}, {'field': 'p50', 'value': '3000'},
             {'field': 'p99', 'value': '8000'}, {'field': 'samples', 'value': '50'},
             {'field': 'metadata.pageId', 'value': '/home'}],
        ], 'statistics': {'recordsMatched': 2.0}}
    mock_aws_clients['logs_client'].get_query_results.side_effect = mock_get_results
    result = json.loads(await rum(action='performance', app_monitor_name='test',
                                  start_time=START, end_time=END))
    vitals = result['web_vitals']['results']
    cls_row = [r for r in vitals if 'cumulative_layout_shift' in r.get('event_type', '')][0]
    lcp_row = [r for r in vitals if 'largest_contentful_paint' in r.get('event_type', '')][0]
    assert cls_row['assessment'] == 'good'
    assert lcp_row['assessment'] == 'poor'


@pytest.mark.asyncio
async def test_sessions(mock_aws_clients):
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await rum(action='sessions', app_monitor_name='test',
                                  start_time=START, end_time=END))
    assert result['status'] == 'Complete'


@pytest.mark.asyncio
async def test_page_views(mock_aws_clients):
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await rum(action='page_views', app_monitor_name='test',
                                  start_time=START, end_time=END))
    assert result['status'] == 'Complete'


@pytest.mark.asyncio
async def test_crashes_android(mock_aws_clients):
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await rum(action='crashes', app_monitor_name='test',
                                  start_time=START, end_time=END, platform='android'))
    assert 'android' in result
    assert 'ios_crashes' not in result


@pytest.mark.asyncio
async def test_crashes_all(mock_aws_clients):
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await rum(action='crashes', app_monitor_name='test',
                                  start_time=START, end_time=END, platform='all'))
    assert 'android' in result
    assert 'android_anrs' in result
    assert 'ios_crashes' in result
    assert 'ios_hangs' in result


@pytest.mark.asyncio
async def test_app_launches(mock_aws_clients):
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await rum(action='app_launches', app_monitor_name='test',
                                  start_time=START, end_time=END))
    assert 'android' in result
    assert 'ios' in result


@pytest.mark.asyncio
async def test_analyze(mock_aws_clients):
    _setup_logs_mocks(mock_aws_clients)
    mock_aws_clients['logs_client'].list_log_anomaly_detectors.return_value = {'anomalyDetectors': []}
    result = json.loads(await rum(action='analyze', app_monitor_name='test',
                                  start_time=START, end_time=END))
    assert 'anomaly_detection' in result
    assert 'top_patterns' in result
    assert 'error_patterns' in result


# --- Correlation + Metrics ---


@pytest.mark.asyncio
async def test_timeseries_errors(mock_aws_clients):
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await rum(action='timeseries', app_monitor_name='test',
                                  start_time=START, end_time=END, metric='errors'))
    assert result['metric'] == 'errors'
    assert result['status'] == 'Complete'


@pytest.mark.asyncio
async def test_timeseries_unknown_metric(mock_aws_clients):
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await rum(action='timeseries', app_monitor_name='test',
                                  start_time=START, end_time=END, metric='bogus'))
    assert 'error' in result


@pytest.mark.asyncio
async def test_locations(mock_aws_clients):
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await rum(action='locations', app_monitor_name='test',
                                  start_time=START, end_time=END))
    assert 'sessions_by_country' in result
    assert 'performance_by_country' in result


@pytest.mark.asyncio
async def test_http_requests(mock_aws_clients):
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await rum(action='http_requests', app_monitor_name='test',
                                  start_time=START, end_time=END))
    assert result['status'] == 'Complete'


@pytest.mark.asyncio
async def test_session_detail(mock_aws_clients):
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await rum(action='session_detail', app_monitor_name='test',
                                  session_id='abc-123', start_time=START, end_time=END))
    assert result['session_id'] == 'abc-123'
    assert result['status'] == 'Complete'


@pytest.mark.asyncio
async def test_resources(mock_aws_clients):
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await rum(action='resources', app_monitor_name='test',
                                  start_time=START, end_time=END))
    assert result['status'] == 'Complete'


@pytest.mark.asyncio
async def test_page_flows(mock_aws_clients):
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(await rum(action='page_flows', app_monitor_name='test',
                                  start_time=START, end_time=END))
    assert result['status'] == 'Complete'


@pytest.mark.asyncio
async def test_correlate_with_traces(mock_aws_clients):
    _setup_logs_mocks(mock_aws_clients)
    mock_aws_clients['logs_client'].get_query_results.return_value = _logs_result(
        rows=[[{'field': 'event_details.trace_id', 'value': '1-abc-def'},
               {'field': 'event_details.duration', 'value': '5000'}]])
    mock_aws_clients['xray_client'].batch_get_traces.return_value = {
        'Traces': [{'Id': '1-abc-def', 'Segments': [
            {'Document': json.dumps({'name': 'payment-svc', 'start_time': 1.0, 'end_time': 2.0,
                                     'error': False, 'fault': False})}
        ]}]}
    result = json.loads(await rum(action='correlate', app_monitor_name='test',
                                  page_url='/checkout', start_time=START, end_time=END))
    assert result['trace_count'] == 1
    assert 'payment-svc' in result['backend_services']


@pytest.mark.asyncio
async def test_correlate_no_traces(mock_aws_clients):
    _setup_logs_mocks(mock_aws_clients)
    mock_aws_clients['logs_client'].get_query_results.return_value = _logs_result(rows=[])
    result = json.loads(await rum(action='correlate', app_monitor_name='test',
                                  page_url='/checkout', start_time=START, end_time=END))
    assert 'No X-Ray trace events found' in result.get('message', '')


@pytest.mark.asyncio
async def test_metrics(mock_aws_clients):
    mock_aws_clients['cloudwatch_client'].get_metric_data.return_value = {
        'MetricDataResults': [{'Id': 'm0', 'Timestamps': [], 'Values': [], 'StatusCode': 'Complete'}]}
    result = json.loads(await rum(action='metrics', app_monitor_name='test',
                                  metric_names='["JsErrorCount"]', start_time=START, end_time=END))
    assert 'JsErrorCount' in result['metrics']


@pytest.mark.asyncio
async def test_metrics_error(mock_aws_clients):
    mock_aws_clients['cloudwatch_client'].get_metric_data.side_effect = Exception('throttled')
    result = json.loads(await rum(action='metrics', app_monitor_name='test',
                                  metric_names='["JsErrorCount"]', start_time=START, end_time=END))
    assert 'error' in result


# --- SLO Health ---


@pytest.mark.asyncio
async def test_slo_health_no_slos(mock_aws_clients):
    paginator = MagicMock()
    paginator.paginate.return_value = [{'SloSummaries': []}]
    mock_aws_clients['applicationsignals_client'].get_paginator.return_value = paginator
    result = json.loads(await rum(action='slo_health', app_monitor_name='test',
                                  start_time=START, end_time=END))
    assert result['status'] == 'NO_SLO'
    assert result['total'] == 0


@pytest.mark.asyncio
async def test_slo_health_ok(mock_aws_clients):
    paginator = MagicMock()
    paginator.paginate.return_value = [{'SloSummaries': [{'Name': 'my-slo'}]}]
    mock_aws_clients['applicationsignals_client'].get_paginator.return_value = paginator
    mock_aws_clients['applicationsignals_client'].get_service_level_objective.return_value = {
        'Slo': {'Goal': {'AttainmentGoal': 99.9}}}
    mock_aws_clients['applicationsignals_client'].batch_get_service_level_objective_budget_report.return_value = {
        'Reports': [{'BudgetStatus': 'OK', 'Attainment': 99.95}]}
    result = json.loads(await rum(action='slo_health', app_monitor_name='test',
                                  start_time=START, end_time=END))
    assert result['status'] == 'OK'
    assert result['healthy'] == 1
    assert result['breaching'] == 0


@pytest.mark.asyncio
async def test_slo_health_breached(mock_aws_clients):
    paginator = MagicMock()
    paginator.paginate.return_value = [{'SloSummaries': [{'Name': 'my-slo'}]}]
    mock_aws_clients['applicationsignals_client'].get_paginator.return_value = paginator
    mock_aws_clients['applicationsignals_client'].get_service_level_objective.return_value = {
        'Slo': {'Goal': {'AttainmentGoal': 99.9},
                'RequestBasedSli': {'RequestBasedSliMetric': {
                    'MonitoredRequestCountMetric': {'BadCountMetric': [
                        {'Id': 'fault_m1', 'MetricStat': {'Metric': {'MetricName': 'JsErrorCount'}}}
                    ]}}}}}
    mock_aws_clients['applicationsignals_client'].batch_get_service_level_objective_budget_report.return_value = {
        'Reports': [{'BudgetStatus': 'BREACHED', 'Attainment': 98.5}]}
    result = json.loads(await rum(action='slo_health', app_monitor_name='test',
                                  start_time=START, end_time=END))
    assert result['status'] == 'BREACHED'
    assert result['breaching'] == 1
    assert result['breaching_slos'][0]['metric'] == 'JsErrorCount'
