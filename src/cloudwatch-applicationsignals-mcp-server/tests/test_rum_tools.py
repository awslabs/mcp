"""Tests for rum_tools.py — all calls go through the unified query_rum_events() dispatcher."""

import json
import pytest
from awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools import query_rum_events
from unittest.mock import MagicMock, patch


START = '2026-03-01T00:00:00Z'
END = '2026-03-18T00:00:00Z'
LOG_GROUP = '/aws/vendedlogs/RUMService_test'


def _app_monitor_response(
    cw_log_enabled=True,
    enable_xray=False,
    telemetries=None,
    sample_rate=1.0,
    allow_cookies=True,
    platform: 'str | None' = 'Web',
):
    """Build a mock get_app_monitor response."""
    return {
        'AppMonitor': {
            'Name': 'test',
            'Id': 'test-id',
            'Domain': 'example.com',
            'State': 'ACTIVE',
            'Platform': platform,
            'DataStorage': {
                'CwLog': {
                    'CwLogEnabled': cw_log_enabled,
                    'CwLogGroup': LOG_GROUP if cw_log_enabled else None,
                }
            },
            'AppMonitorConfiguration': {
                'EnableXRay': enable_xray,
                'Telemetries': telemetries or ['errors', 'performance', 'http'],
                'SessionSampleRate': sample_rate,
                'AllowCookies': allow_cookies,
            },
        }
    }


def _logs_result(rows=None):
    """Build a mock get_query_results response."""
    if rows is None:
        rows = [
            [{'field': '@timestamp', 'value': '2026-03-01'}, {'field': 'count', 'value': '42'}]
        ]
    return {
        'status': 'Complete',
        'results': rows,
        'statistics': {'recordsMatched': float(len(rows))},
    }


@pytest.fixture(autouse=True)
def mock_aws_clients():
    """Mock all AWS clients used by rum_tools."""
    from awslabs.cloudwatch_applicationsignals_mcp_server import rum_tools as _rt

    # Clear process-wide caches so test cases are independent.
    _rt._clear_module_caches()

    mock_rum = MagicMock()
    mock_logs = MagicMock()
    mock_cw = MagicMock()
    mock_xray = MagicMock()
    mock_appsignals = MagicMock()
    mock_sts = MagicMock()
    mock_sts.get_caller_identity.return_value = {'Account': '123456789012'}
    mock_time = MagicMock()
    _time_counter = iter(range(0, 10000, 1))
    mock_time.monotonic.side_effect = lambda: next(_time_counter)
    mock_time.sleep = MagicMock()

    patches = [
        patch('awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools.rum_client', mock_rum),
        patch('awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools.logs_client', mock_logs),
        patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools.cloudwatch_client', mock_cw
        ),
        patch('awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools.xray_client', mock_xray),
        patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools.applicationsignals_client',
            mock_appsignals,
        ),
        patch('awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools.sts_client', mock_sts),
        patch('awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools.time', mock_time),
    ]
    for p in patches:
        p.start()
    try:
        yield {
            'rum_client': mock_rum,
            'logs_client': mock_logs,
            'cloudwatch_client': mock_cw,
            'xray_client': mock_xray,
            'applicationsignals_client': mock_appsignals,
            'sts_client': mock_sts,
            'time': mock_time,
        }
    finally:
        for p in patches:
            p.stop()


# --- Unknown action ---


@pytest.mark.asyncio
async def test_unknown_action():
    """Unknown action."""
    result = json.loads(await query_rum_events(action='bogus'))
    assert 'error' in result
    assert 'available_actions' in result


# --- Discovery ---


@pytest.mark.asyncio
async def test_check_data_access_all_good(mock_aws_clients):
    """Check data access all good."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response(
        cw_log_enabled=True, enable_xray=True, allow_cookies=True
    )
    result = json.loads(
        await query_rum_events(action='check_data_access', app_monitor_name='test')
    )
    assert result['state'] == 'ACTIVE'
    assert len(result['findings']) == 0


@pytest.mark.asyncio
async def test_check_data_access_cw_log_disabled(mock_aws_clients):
    """Check data access cw log disabled."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response(
        cw_log_enabled=False
    )
    result = json.loads(
        await query_rum_events(action='check_data_access', app_monitor_name='test')
    )
    assert any(f['severity'] == 'HIGH' for f in result['findings'])


@pytest.mark.asyncio
async def test_check_data_access_xray_disabled(mock_aws_clients):
    """Check data access xray disabled."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response(
        enable_xray=False
    )
    result = json.loads(
        await query_rum_events(action='check_data_access', app_monitor_name='test')
    )
    xray_finding = [f for f in result['findings'] if 'X-Ray' in f['issue']]
    assert len(xray_finding) == 1
    assert xray_finding[0]['severity'] == 'MEDIUM'
    assert 'correlate' in xray_finding[0]['impact'].lower()


@pytest.mark.asyncio
async def test_check_data_access_not_found(mock_aws_clients):
    """Check data access not found."""
    exc = type('ResourceNotFoundException', (Exception,), {})
    mock_aws_clients['rum_client'].exceptions.ResourceNotFoundException = exc
    mock_aws_clients['rum_client'].get_app_monitor.side_effect = exc('not found')
    result = json.loads(
        await query_rum_events(action='check_data_access', app_monitor_name='missing')
    )
    assert 'error' in result


@pytest.mark.asyncio
async def test_list_monitors(mock_aws_clients):
    """List monitors."""
    paginator = MagicMock()
    paginator.paginate.return_value = [
        {
            'AppMonitorSummaries': [
                {'Name': 'app1', 'Id': 'id1', 'State': 'ACTIVE'},
            ]
        }
    ]
    mock_aws_clients['rum_client'].get_paginator.return_value = paginator
    result = json.loads(await query_rum_events(action='list_monitors'))
    assert result['count'] == 1


@pytest.mark.asyncio
async def test_get_monitor(mock_aws_clients):
    """Get monitor."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response()
    result = json.loads(await query_rum_events(action='get_monitor', app_monitor_name='test'))
    assert result['Name'] == 'test'


@pytest.mark.asyncio
async def test_get_monitor_error(mock_aws_clients):
    """Get monitor error."""
    mock_aws_clients['rum_client'].get_app_monitor.side_effect = Exception('boom')
    result = json.loads(await query_rum_events(action='get_monitor', app_monitor_name='test'))
    assert 'error' in result


@pytest.mark.asyncio
async def test_list_tags(mock_aws_clients):
    """List tags."""
    mock_aws_clients['rum_client'].list_tags_for_resource.return_value = {'Tags': {'env': 'prod'}}
    result = json.loads(
        await query_rum_events(
            action='list_tags', resource_arn='arn:aws:rum:us-east-1:123:appmonitor/test'
        )
    )
    assert result['tags'] == {'env': 'prod'}


@pytest.mark.asyncio
async def test_get_policy(mock_aws_clients):
    """Get policy."""
    mock_aws_clients['rum_client'].get_resource_policy.return_value = {
        'PolicyDocument': '{"Version":"2012-10-17"}'
    }
    result = json.loads(await query_rum_events(action='get_policy', app_monitor_name='test'))
    assert result['policy']['Version'] == '2012-10-17'


# --- Logs Insights query tools ---


def _setup_logs_mocks(clients):
    clients['rum_client'].get_app_monitor.return_value = _app_monitor_response()
    clients['logs_client'].start_query.return_value = {'queryId': 'qid'}
    clients['logs_client'].get_query_results.return_value = _logs_result()


@pytest.mark.asyncio
async def test_query(mock_aws_clients):
    """Query."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='query',
            app_monitor_name='test',
            query_string='fields @timestamp',
            start_time=START,
            end_time=END,
        )
    )
    assert result['status'] == 'Complete'
    assert result['log_group'] == LOG_GROUP


@pytest.mark.asyncio
async def test_query_cw_log_disabled(mock_aws_clients):
    """Query cw log disabled."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response(
        cw_log_enabled=False
    )
    result = json.loads(
        await query_rum_events(
            action='query',
            app_monitor_name='test',
            query_string='fields @timestamp',
            start_time=START,
            end_time=END,
        )
    )
    assert 'error' in result


@pytest.mark.asyncio
async def test_health(mock_aws_clients):
    """Health."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='health', app_monitor_name='test', start_time=START, end_time=END
        )
    )
    assert 'error_breakdown' in result
    assert 'slowest_pages' in result
    assert 'sessions_with_errors' in result
    assert 'previous_period' not in result


@pytest.mark.asyncio
async def test_health_compare_previous(mock_aws_clients):
    """Health compare previous."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='health',
            app_monitor_name='test',
            start_time=START,
            end_time=END,
            compare_previous=True,
        )
    )
    assert 'error_breakdown' in result
    assert 'previous_period' in result
    assert 'error_breakdown' in result['previous_period']


@pytest.mark.asyncio
async def test_errors(mock_aws_clients):
    """Errors."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='errors', app_monitor_name='test', start_time=START, end_time=END
        )
    )
    assert result['status'] == 'Complete'


@pytest.mark.asyncio
async def test_errors_with_filters(mock_aws_clients):
    """Errors with filters."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='errors',
            app_monitor_name='test',
            start_time=START,
            end_time=END,
            page_url='/checkout',
            group_by='browser',
        )
    )
    assert result['status'] == 'Complete'


@pytest.mark.asyncio
async def test_performance(mock_aws_clients):
    """Performance."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='performance', app_monitor_name='test', start_time=START, end_time=END
        )
    )
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
        return {
            'status': 'Complete',
            'results': [
                [
                    {
                        'field': 'event_type',
                        'value': 'com.amazon.rum.cumulative_layout_shift_event',
                    },
                    {'field': 'p90', 'value': '0.05'},
                    {'field': 'p50', 'value': '0.02'},
                    {'field': 'p99', 'value': '0.1'},
                    {'field': 'samples', 'value': '100'},
                    {'field': 'metadata.pageId', 'value': '/home'},
                ],
                [
                    {
                        'field': 'event_type',
                        'value': 'com.amazon.rum.largest_contentful_paint_event',
                    },
                    {'field': 'p90', 'value': '5000'},
                    {'field': 'p50', 'value': '3000'},
                    {'field': 'p99', 'value': '8000'},
                    {'field': 'samples', 'value': '50'},
                    {'field': 'metadata.pageId', 'value': '/home'},
                ],
            ],
            'statistics': {'recordsMatched': 2.0},
        }

    mock_aws_clients['logs_client'].get_query_results.side_effect = mock_get_results
    result = json.loads(
        await query_rum_events(
            action='performance', app_monitor_name='test', start_time=START, end_time=END
        )
    )
    vitals = result['web_vitals']['results']
    cls_row = [r for r in vitals if 'cumulative_layout_shift' in r.get('event_type', '')][0]
    lcp_row = [r for r in vitals if 'largest_contentful_paint' in r.get('event_type', '')][0]
    assert cls_row['assessment'] == 'good'
    assert lcp_row['assessment'] == 'poor'


@pytest.mark.asyncio
async def test_sessions(mock_aws_clients):
    """Sessions."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='sessions', app_monitor_name='test', start_time=START, end_time=END
        )
    )
    assert result['status'] == 'Complete'


@pytest.mark.asyncio
async def test_page_views(mock_aws_clients):
    """Page views."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='page_views', app_monitor_name='test', start_time=START, end_time=END
        )
    )
    assert result['status'] == 'Complete'


def _setup_mobile_logs_mocks(clients):
    """Same as _setup_logs_mocks but with a mobile app monitor."""
    clients['rum_client'].get_app_monitor.return_value = _app_monitor_response(platform='Android')
    clients['logs_client'].start_query.return_value = {'queryId': 'qid'}
    clients['logs_client'].get_query_results.return_value = _logs_result()


@pytest.mark.asyncio
async def test_crashes_android(mock_aws_clients):
    """Crashes android."""
    _setup_mobile_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='crashes',
            app_monitor_name='test',
            start_time=START,
            end_time=END,
            platform='android',
        )
    )
    assert 'android' in result
    assert 'ios_crashes' not in result


@pytest.mark.asyncio
async def test_crashes_all(mock_aws_clients):
    """Crashes all."""
    _setup_mobile_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='crashes',
            app_monitor_name='test',
            start_time=START,
            end_time=END,
            platform='all',
        )
    )
    assert 'android' in result
    assert 'android_anrs' in result
    assert 'ios_crashes' in result
    assert 'ios_hangs' in result


@pytest.mark.asyncio
async def test_crashes_platform_mismatch(mock_aws_clients):
    """A web monitor called with platform='android' should error cleanly."""
    _setup_logs_mocks(mock_aws_clients)  # web monitor
    result = json.loads(
        await query_rum_events(
            action='crashes',
            app_monitor_name='test',
            start_time=START,
            end_time=END,
            platform='android',
        )
    )
    assert 'error' in result
    assert result.get('monitor_platform') == 'web'


@pytest.mark.asyncio
async def test_app_launches(mock_aws_clients):
    """App launches."""
    _setup_mobile_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='app_launches', app_monitor_name='test', start_time=START, end_time=END
        )
    )
    assert 'android' in result
    assert 'ios' in result


@pytest.mark.asyncio
async def test_analyze(mock_aws_clients):
    """Analyze."""
    _setup_logs_mocks(mock_aws_clients)
    mock_aws_clients['logs_client'].list_log_anomaly_detectors.return_value = {
        'anomalyDetectors': []
    }
    result = json.loads(
        await query_rum_events(
            action='analyze', app_monitor_name='test', start_time=START, end_time=END
        )
    )
    assert 'anomaly_detection' in result
    assert 'top_patterns' in result
    assert 'error_patterns' in result


# --- Correlation + Metrics ---


@pytest.mark.asyncio
async def test_timeseries_errors(mock_aws_clients):
    """Timeseries errors."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='timeseries',
            app_monitor_name='test',
            start_time=START,
            end_time=END,
            metric='errors',
        )
    )
    assert result['metric'] == 'errors'
    assert result['status'] == 'Complete'


@pytest.mark.asyncio
async def test_timeseries_unknown_metric(mock_aws_clients):
    """Timeseries unknown metric."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='timeseries',
            app_monitor_name='test',
            start_time=START,
            end_time=END,
            metric='bogus',
        )
    )
    assert 'error' in result


@pytest.mark.asyncio
async def test_locations(mock_aws_clients):
    """Locations."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='locations', app_monitor_name='test', start_time=START, end_time=END
        )
    )
    assert 'sessions_by_country' in result
    assert 'performance_by_country' in result


@pytest.mark.asyncio
async def test_http_requests(mock_aws_clients):
    """Http requests."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='http_requests', app_monitor_name='test', start_time=START, end_time=END
        )
    )
    assert result['status'] == 'Complete'


@pytest.mark.asyncio
async def test_session_detail(mock_aws_clients):
    """Session detail."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='session_detail',
            app_monitor_name='test',
            session_id='abc-123',
            start_time=START,
            end_time=END,
        )
    )
    assert result['session_id'] == 'abc-123'
    assert result['status'] == 'Complete'


@pytest.mark.asyncio
async def test_resources(mock_aws_clients):
    """Resources."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='resources', app_monitor_name='test', start_time=START, end_time=END
        )
    )
    assert result['status'] == 'Complete'


@pytest.mark.asyncio
async def test_page_flows(mock_aws_clients):
    """Page flows."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='page_flows', app_monitor_name='test', start_time=START, end_time=END
        )
    )
    assert result['status'] == 'Complete'


@pytest.mark.asyncio
async def test_correlate_with_traces(mock_aws_clients):
    """Correlate with traces."""
    _setup_logs_mocks(mock_aws_clients)
    mock_aws_clients['logs_client'].get_query_results.return_value = _logs_result(
        rows=[
            [
                {'field': 'event_details.trace_id', 'value': '1-abc-def'},
                {'field': 'event_details.duration', 'value': '5000'},
            ]
        ]
    )
    mock_aws_clients['xray_client'].batch_get_traces.return_value = {
        'Traces': [
            {
                'Id': '1-abc-def',
                'Segments': [
                    {
                        'Document': json.dumps(
                            {
                                'name': 'payment-svc',
                                'start_time': 1.0,
                                'end_time': 2.0,
                                'error': False,
                                'fault': False,
                            }
                        )
                    }
                ],
            }
        ]
    }
    result = json.loads(
        await query_rum_events(
            action='correlate',
            app_monitor_name='test',
            page_url='/checkout',
            start_time=START,
            end_time=END,
        )
    )
    assert result['trace_count'] == 1
    assert 'payment-svc' in result['backend_services']


@pytest.mark.asyncio
async def test_correlate_no_traces(mock_aws_clients):
    """Correlate no traces."""
    _setup_logs_mocks(mock_aws_clients)
    mock_aws_clients['logs_client'].get_query_results.return_value = _logs_result(rows=[])
    result = json.loads(
        await query_rum_events(
            action='correlate',
            app_monitor_name='test',
            page_url='/checkout',
            start_time=START,
            end_time=END,
        )
    )
    assert 'No X-Ray trace events found' in result.get('message', '')
    # Response shape stays consistent with the success branch for uniform parsing.
    assert result['trace_ids'] == []
    assert result['trace_count'] == 0
    assert result['backend_services'] == {}


@pytest.mark.asyncio
async def test_metrics(mock_aws_clients):
    """Metrics."""
    mock_aws_clients['cloudwatch_client'].get_metric_data.return_value = {
        'MetricDataResults': [
            {'Id': 'm0', 'Timestamps': [], 'Values': [], 'StatusCode': 'Complete'}
        ]
    }
    result = json.loads(
        await query_rum_events(
            action='metrics',
            app_monitor_name='test',
            metric_names='["JsErrorCount"]',
            start_time=START,
            end_time=END,
        )
    )
    assert 'JsErrorCount' in result['metrics']


@pytest.mark.asyncio
async def test_metrics_error(mock_aws_clients):
    """Metrics error."""
    mock_aws_clients['cloudwatch_client'].get_metric_data.side_effect = Exception('throttled')
    result = json.loads(
        await query_rum_events(
            action='metrics',
            app_monitor_name='test',
            metric_names='["JsErrorCount"]',
            start_time=START,
            end_time=END,
        )
    )
    assert 'error' in result


# --- SLO Health ---


@pytest.mark.asyncio
async def test_slo_health_no_slos(mock_aws_clients):
    """Slo health no slos."""
    paginator = MagicMock()
    paginator.paginate.return_value = [{'SloSummaries': []}]
    mock_aws_clients['applicationsignals_client'].get_paginator.return_value = paginator
    result = json.loads(
        await query_rum_events(
            action='slo_health', app_monitor_name='test', start_time=START, end_time=END
        )
    )
    assert result['status'] == 'NO_SLO'
    assert result['total'] == 0


@pytest.mark.asyncio
async def test_slo_health_ok(mock_aws_clients):
    """Slo health ok."""
    paginator = MagicMock()
    paginator.paginate.return_value = [{'SloSummaries': [{'Name': 'my-slo'}]}]
    mock_aws_clients['applicationsignals_client'].get_paginator.return_value = paginator
    mock_aws_clients['applicationsignals_client'].get_service_level_objective.return_value = {
        'Slo': {'Goal': {'AttainmentGoal': 99.9}}
    }
    mock_aws_clients[
        'applicationsignals_client'
    ].batch_get_service_level_objective_budget_report.return_value = {
        'Reports': [{'BudgetStatus': 'OK', 'Attainment': 99.95}]
    }
    result = json.loads(
        await query_rum_events(
            action='slo_health', app_monitor_name='test', start_time=START, end_time=END
        )
    )
    assert result['status'] == 'OK'
    assert result['healthy'] == 1
    assert result['breaching'] == 0


@pytest.mark.asyncio
async def test_slo_health_breached(mock_aws_clients):
    """Slo health breached."""
    paginator = MagicMock()
    paginator.paginate.return_value = [{'SloSummaries': [{'Name': 'my-slo'}]}]
    mock_aws_clients['applicationsignals_client'].get_paginator.return_value = paginator
    mock_aws_clients['applicationsignals_client'].get_service_level_objective.return_value = {
        'Slo': {
            'Goal': {'AttainmentGoal': 99.9},
            'RequestBasedSli': {
                'RequestBasedSliMetric': {
                    'MonitoredRequestCountMetric': {
                        'BadCountMetric': [
                            {
                                'Id': 'fault_m1',
                                'MetricStat': {'Metric': {'MetricName': 'JsErrorCount'}},
                            }
                        ]
                    }
                }
            },
        }
    }
    mock_aws_clients[
        'applicationsignals_client'
    ].batch_get_service_level_objective_budget_report.return_value = {
        'Reports': [{'BudgetStatus': 'BREACHED', 'Attainment': 98.5}]
    }
    result = json.loads(
        await query_rum_events(
            action='slo_health', app_monitor_name='test', start_time=START, end_time=END
        )
    )
    assert result['status'] == 'BREACHED'
    assert result['breaching'] == 1
    assert result['breaching_slos'][0]['metric'] == 'JsErrorCount'


# --- Round-3 review fixes ---


def _setup_unknown_platform_mocks(clients):
    """Monitor returns no Platform and log group has no sample events -> 'unknown'."""
    resp = _app_monitor_response(platform=None)
    resp['AppMonitor'].pop('Platform', None)
    clients['rum_client'].get_app_monitor.return_value = resp
    clients['logs_client'].filter_log_events.return_value = {'events': []}
    clients['logs_client'].start_query.return_value = {'queryId': 'qid'}
    clients['logs_client'].get_query_results.return_value = _logs_result()


@pytest.mark.asyncio
async def test_crashes_unknown_platform_guard(mock_aws_clients):
    """platform='all' against an unknown-platform monitor returns the guard, not 4 queries."""
    _setup_unknown_platform_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='crashes',
            app_monitor_name='test',
            start_time=START,
            end_time=END,
            platform='all',
        )
    )
    assert result.get('monitor_platform') == 'unknown'
    assert 'error' in result
    assert mock_aws_clients['logs_client'].start_query.call_count == 0


@pytest.mark.asyncio
async def test_app_launches_unknown_platform_guard(mock_aws_clients):
    """App launches unknown platform guard."""
    _setup_unknown_platform_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='app_launches',
            app_monitor_name='test',
            start_time=START,
            end_time=END,
            platform='all',
        )
    )
    assert result.get('monitor_platform') == 'unknown'
    assert 'error' in result
    assert mock_aws_clients['logs_client'].start_query.call_count == 0


@pytest.mark.asyncio
async def test_session_detail_limit_capped(mock_aws_clients):
    """Session detail limit capped."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='session_detail',
            app_monitor_name='test',
            session_id='abc',
            start_time=START,
            end_time=END,
            limit=100000,
        )
    )
    assert result['limit'] == 500
    assert result['limit_cap'] == 500


@pytest.mark.asyncio
async def test_session_detail_limit_invalid(mock_aws_clients):
    """Session detail limit invalid."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='session_detail',
            app_monitor_name='test',
            session_id='abc',
            start_time=START,
            end_time=END,
            limit='abc',  # pyright: ignore[reportArgumentType]
        )
    )
    assert result.get('error_type') == 'bad_request'


@pytest.mark.asyncio
async def test_timeseries_bad_bucket_shape(mock_aws_clients):
    """Timeseries bad bucket shape."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='timeseries',
            app_monitor_name='test',
            start_time=START,
            end_time=END,
            metric='errors',
            bucket='1year',
        )
    )
    assert result.get('error_type') == 'bad_request'


@pytest.mark.asyncio
async def test_metrics_malformed_response(mock_aws_clients):
    """Malformed MetricDataResults entry should return internal_error, not crash."""
    mock_aws_clients['cloudwatch_client'].get_metric_data.return_value = {
        'MetricDataResults': [
            {'Id': 'BAD', 'Timestamps': [], 'Values': [], 'StatusCode': 'Complete'}
        ]
    }
    result = json.loads(
        await query_rum_events(
            action='metrics',
            app_monitor_name='test',
            metric_names='["JsErrorCount"]',
            start_time=START,
            end_time=END,
        )
    )
    assert result.get('error_type') == 'internal_error'


# --- Regression tests for review round 1 fixes ---


@pytest.mark.parametrize(
    'bad_names',
    [
        '{"x": 1}',  # dict, not list
        '"JsErrorCount"',  # bare string
        '[]',  # empty list
        '[""]',  # empty-string entry
        '[1, 2]',  # non-string entries
    ],
)
@pytest.mark.asyncio
async def test_metrics_names_validation_rejects_non_list(mock_aws_clients, bad_names):
    """Metrics names validation rejects non list."""
    result = json.loads(
        await query_rum_events(
            action='metrics',
            app_monitor_name='test',
            metric_names=bad_names,
            start_time=START,
            end_time=END,
        )
    )
    assert result.get('error_type') == 'bad_request'


@pytest.mark.asyncio
async def test_crashes_unknown_platform_takes_precedence_over_mismatch(mock_aws_clients):
    """Unknown monitor platform returns the unknown-platform hint, not a mismatch message."""
    resp = _app_monitor_response()
    resp['AppMonitor'].pop('Platform')
    mock_aws_clients['rum_client'].get_app_monitor.return_value = resp
    mock_aws_clients['logs_client'].filter_log_events.return_value = {'events': []}
    result = json.loads(
        await query_rum_events(
            action='crashes',
            app_monitor_name='test',
            start_time=START,
            end_time=END,
            platform='android',
        )
    )
    assert result.get('monitor_platform') == 'unknown'
    assert 'mismatch' not in result.get('error', '').lower()


@pytest.mark.asyncio
async def test_correlate_dedupes_and_oversamples(mock_aws_clients):
    """Correlate dedupes trace IDs and oversamples to compensate for duplicates."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response()
    mock_aws_clients['logs_client'].start_query.return_value = {'queryId': 'qid'}
    # 10 rows, but only 3 unique trace IDs (a 3.3x duplication factor)
    dupe_rows = []
    for trace_id in ['T1', 'T2', 'T3']:
        for _ in range(3):
            dupe_rows.append([{'field': 'event_details.trace_id', 'value': trace_id}])
    dupe_rows.append([{'field': 'event_details.trace_id', 'value': 'T4'}])
    mock_aws_clients['logs_client'].get_query_results.return_value = _logs_result(dupe_rows)
    mock_aws_clients['xray_client'].batch_get_traces.return_value = {'Traces': []}
    result = json.loads(
        await query_rum_events(
            action='correlate',
            app_monitor_name='test',
            page_url='/home',
            start_time=START,
            end_time=END,
            max_traces=5,
        )
    )
    assert result.get('trace_ids') == ['T1', 'T2', 'T3', 'T4']


@pytest.mark.asyncio
async def test_slo_health_all_errored_returns_error_status(mock_aws_clients):
    """When every SLO check raises, status should be ERROR — not a false OK."""
    appsig = mock_aws_clients['applicationsignals_client']
    paginator = MagicMock()
    paginator.paginate.return_value = [
        {
            'SloSummaries': [
                {'Name': 'slo-a', 'Arn': 'arn:aws:...slo-a'},
                {'Name': 'slo-b', 'Arn': 'arn:aws:...slo-b'},
            ]
        }
    ]
    appsig.get_paginator.return_value = paginator
    appsig.get_service_level_objective.side_effect = Exception('AccessDenied')
    result = json.loads(
        await query_rum_events(
            action='slo_health', app_monitor_name='test', start_time=START, end_time=END
        )
    )
    assert result['status'] == 'ERROR'
    assert result['errored'] == 2
    assert len(result['errored_slos']) == 2
    # Error entries carry the same keys as breaching entries (for uniform iteration).
    entry = result['errored_slos'][0]
    for key in ('slo_name', 'slo_arn', 'budget_status', 'attainment', 'goal', 'metric', 'error'):
        assert key in entry


@pytest.mark.parametrize(
    'action,extra',
    [
        ('errors', {}),
        ('performance', {}),
        ('page_views', {}),
        ('timeseries', {'metric': 'errors'}),
        ('timeseries', {'metric': 'performance'}),
        ('locations', {}),
        ('http_requests', {}),
        ('resources', {}),
        ('page_flows', {}),
        ('health', {}),
        ('correlate', {'page_url': '/home'}),
    ],
)
@pytest.mark.asyncio
async def test_web_schema_tools_guard_unknown_platform(mock_aws_clients, action, extra):
    """Web-schema tools return the unknown-platform hint on mobile/OTel log groups."""
    _setup_unknown_platform_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action=action, app_monitor_name='test', start_time=START, end_time=END, **extra
        )
    )
    assert result.get('platform') == 'unknown'
    assert 'error' in result
    assert mock_aws_clients['logs_client'].start_query.call_count == 0


@pytest.mark.asyncio
async def test_analyze_paginates_list_anomalies(mock_aws_clients):
    """list_anomalies should loop on nextToken, not just take the first page."""
    _setup_logs_mocks(mock_aws_clients)
    mock_aws_clients['logs_client'].list_log_anomaly_detectors.return_value = {
        'anomalyDetectors': [
            {
                'anomalyDetectorArn': 'arn:det1',
                'detectorName': 'd1',
                'anomalyDetectorStatus': 'ACTIVE',
            }
        ],
    }
    mock_aws_clients['logs_client'].list_anomalies.side_effect = [
        {'anomalies': [{'firstSeen': 0}], 'nextToken': 'tok1'},
        {'anomalies': [{'firstSeen': 0}], 'nextToken': 'tok2'},
        {'anomalies': [{'firstSeen': 0}]},  # terminal page
    ]
    await query_rum_events(
        action='analyze', app_monitor_name='test', start_time=START, end_time=END
    )
    assert mock_aws_clients['logs_client'].list_anomalies.call_count == 3


# --- Round-5 review fixes ---


@pytest.mark.asyncio
async def test_analyze_surfaces_anomaly_truncation(mock_aws_clients):
    """Surface truncated=True when list_anomalies exceeds the per-detector page cap.

    Without this signal the caller's LLM can't tell anomalies were dropped.
    """
    from awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools import _ANOMALY_PAGE_CAP

    _setup_logs_mocks(mock_aws_clients)
    mock_aws_clients['logs_client'].list_log_anomaly_detectors.return_value = {
        'anomalyDetectors': [
            {
                'anomalyDetectorArn': 'arn:det1',
                'detectorName': 'd1',
                'anomalyDetectorStatus': 'ACTIVE',
            }
        ],
    }
    # Every page returns a nextToken -> loop exits via the page cap, not terminal page.
    mock_aws_clients['logs_client'].list_anomalies.return_value = {
        'anomalies': [{'firstSeen': 0}],
        'nextToken': 'more',
    }
    result = json.loads(
        await query_rum_events(
            action='analyze', app_monitor_name='test', start_time=START, end_time=END
        )
    )
    assert result['anomaly_detection']['truncated'] is True
    assert result['anomaly_detection']['page_cap'] == _ANOMALY_PAGE_CAP
    assert mock_aws_clients['logs_client'].list_anomalies.call_count == _ANOMALY_PAGE_CAP


@pytest.mark.asyncio
async def test_analyze_reports_truncated_false_when_no_detectors(mock_aws_clients):
    """Default truncated=False when there are no detectors, do not omit the key."""
    _setup_logs_mocks(mock_aws_clients)
    mock_aws_clients['logs_client'].list_log_anomaly_detectors.return_value = {
        'anomalyDetectors': []
    }
    result = json.loads(
        await query_rum_events(
            action='analyze', app_monitor_name='test', start_time=START, end_time=END
        )
    )
    assert result['anomaly_detection']['truncated'] is False


@pytest.mark.asyncio
async def test_correlate_all_xray_batches_fail(mock_aws_clients):
    """Return service_error when every batch_get_traces call raises.

    An empty success payload would be indistinguishable from 'no backend services'.
    Also pins the shared response-shape keys so future refactors can't
    silently drop them from the error branch (the success and no-traces
    branches rely on these keys being present across all outcomes).
    """
    from awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools import (
        _CORRELATE_MAX_TRACES_CAP,
    )

    _setup_logs_mocks(mock_aws_clients)
    mock_aws_clients['logs_client'].get_query_results.return_value = _logs_result(
        rows=[[{'field': 'event_details.trace_id', 'value': 'T1'}]]
    )
    mock_aws_clients['xray_client'].batch_get_traces.side_effect = Exception('AccessDenied')
    result = json.loads(
        await query_rum_events(
            action='correlate',
            app_monitor_name='test',
            page_url='/home',
            start_time=START,
            end_time=END,
        )
    )
    assert result.get('error_type') == 'service_error'
    assert 'AccessDenied' in result.get('error', '')
    # Shape-key parity with the success and no-traces branches.
    assert result['trace_count'] == 0
    assert result['max_traces_cap'] == _CORRELATE_MAX_TRACES_CAP
    assert result['backend_services'] == {}
    assert 'max_traces' in result


@pytest.mark.asyncio
async def test_correlate_partial_xray_batch_failure(mock_aws_clients):
    """Mixed failures should succeed but surface partial_failure + error count."""
    _setup_logs_mocks(mock_aws_clients)
    # 6 unique trace IDs -> 2 batches of ~5
    rows = [[{'field': 'event_details.trace_id', 'value': f'T{i}'}] for i in range(6)]
    mock_aws_clients['logs_client'].get_query_results.return_value = _logs_result(rows=rows)
    call_count = {'n': 0}

    def _fake_batch(**_kw):
        call_count['n'] += 1
        if call_count['n'] == 1:
            return {
                'Traces': [
                    {
                        'Id': 'T1',
                        'Segments': [
                            {
                                'Document': json.dumps(
                                    {'name': 'svc-a', 'start_time': 1.0, 'end_time': 2.0}
                                )
                            }
                        ],
                    }
                ]
            }
        raise Exception('Throttled')

    mock_aws_clients['xray_client'].batch_get_traces.side_effect = _fake_batch
    result = json.loads(
        await query_rum_events(
            action='correlate',
            app_monitor_name='test',
            page_url='/home',
            start_time=START,
            end_time=END,
            max_traces=6,
        )
    )
    assert result.get('partial_failure') is True
    assert result['batch_error_count'] >= 1
    assert 'svc-a' in result['backend_services']


@pytest.mark.parametrize('bad_platform', ['iOS', 'Android', 'mobile', 'all_mobile', 'web', ''])
@pytest.mark.asyncio
async def test_crashes_rejects_invalid_platform(mock_aws_clients, bad_platform):
    """Invalid platform strings must return bad_request, not a silent empty response."""
    _setup_mobile_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='crashes',
            app_monitor_name='test',
            start_time=START,
            end_time=END,
            platform=bad_platform,
        )
    )
    assert result.get('error_type') == 'bad_request'
    assert mock_aws_clients['logs_client'].start_query.call_count == 0


@pytest.mark.parametrize('bad_platform', ['iOS', 'Android', 'mobile', 'all_mobile', 'web', ''])
@pytest.mark.asyncio
async def test_app_launches_rejects_invalid_platform(mock_aws_clients, bad_platform):
    """App launches rejects invalid platform."""
    _setup_mobile_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='app_launches',
            app_monitor_name='test',
            start_time=START,
            end_time=END,
            platform=bad_platform,
        )
    )
    assert result.get('error_type') == 'bad_request'
    assert mock_aws_clients['logs_client'].start_query.call_count == 0


@pytest.mark.asyncio
async def test_unknown_platform_response_carries_error_type(mock_aws_clients):
    """The unknown-platform guard must emit error_type so LLM retry logic can branch."""
    _setup_unknown_platform_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='errors', app_monitor_name='test', start_time=START, end_time=END
        )
    )
    assert result.get('error_type') == 'bad_request'
    assert result.get('platform') == 'unknown'


# --- Platform detection fallback (_detect_platform_from_logs) ---


def _log_event(message_dict):
    """Wrap a dict as a CW Logs filter_log_events event row."""
    return {'message': json.dumps(message_dict)}


def test_detect_platform_from_logs_mobile_majority(mock_aws_clients):
    """Mixed events with more mobile (resource/scope) markers classify as mobile."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools import (
        _detect_platform_from_logs,
    )

    mock_aws_clients['logs_client'].filter_log_events.return_value = {
        'events': [
            _log_event({'resource': {'attributes': {}}, 'eventName': 'session.start'}),
            _log_event({'scope': {'name': 'io.opentelemetry.crash'}}),
            _log_event({'event_type': 'com.amazon.rum.page_view_event'}),
        ]
    }
    assert _detect_platform_from_logs(LOG_GROUP) == 'mobile'


def test_detect_platform_from_logs_web_majority(mock_aws_clients):
    """Events with only com.amazon.rum.* markers classify as web."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools import (
        _detect_platform_from_logs,
    )

    mock_aws_clients['logs_client'].filter_log_events.return_value = {
        'events': [
            _log_event({'event_type': 'com.amazon.rum.js_error_event'}),
            _log_event({'event_type': 'com.amazon.rum.page_view_event'}),
        ]
    }
    assert _detect_platform_from_logs(LOG_GROUP) == 'web'


def test_detect_platform_from_logs_unparseable_events_return_unknown(mock_aws_clients):
    """Events that fail json.loads must be skipped, not crash; empty signal -> 'unknown'."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools import (
        _detect_platform_from_logs,
    )

    mock_aws_clients['logs_client'].filter_log_events.return_value = {
        'events': [
            {'message': 'not-json-at-all'},
            {'message': '{{malformed'},
            {},  # no message field at all
        ]
    }
    assert _detect_platform_from_logs(LOG_GROUP) == 'unknown'


def test_detect_platform_from_logs_api_error_returns_unknown(mock_aws_clients):
    """An API error on filter_log_events must degrade to 'unknown', not propagate."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools import (
        _detect_platform_from_logs,
    )

    mock_aws_clients['logs_client'].filter_log_events.side_effect = Exception('AccessDenied')
    assert _detect_platform_from_logs(LOG_GROUP) == 'unknown'


# --- Logs Insights poll loop (_run_logs_insights_query_sync) ---


def _query_sync_args():
    from datetime import datetime, timezone

    return {
        'log_group': LOG_GROUP,
        'query_string': 'fields @timestamp',
        'start_time': datetime(2026, 3, 1, tzinfo=timezone.utc),
        'end_time': datetime(2026, 3, 2, tzinfo=timezone.utc),
    }


def test_run_logs_insights_query_sync_polls_until_complete(mock_aws_clients):
    """Runs the poll loop past at least one Running status before returning Complete."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools import (
        _run_logs_insights_query_sync,
    )

    mock_aws_clients['logs_client'].start_query.return_value = {'queryId': 'qid-poll'}
    mock_aws_clients['logs_client'].get_query_results.side_effect = [
        {'status': 'Running', 'results': [], 'statistics': {}},
        {'status': 'Running', 'results': [], 'statistics': {}},
        _logs_result(),
    ]
    result = _run_logs_insights_query_sync(
        **_query_sync_args(), poll_interval=0.1, max_poll_seconds=60
    )
    assert result['status'] == 'Complete'
    # Polled three times (two Running + one Complete) and slept between the first two.
    assert mock_aws_clients['logs_client'].get_query_results.call_count == 3
    assert mock_aws_clients['time'].sleep.call_count >= 2
    # Happy path must NOT issue stop_query — the query completed on its own.
    assert mock_aws_clients['logs_client'].stop_query.call_count == 0


def test_run_logs_insights_query_sync_times_out_and_calls_stop_query(mock_aws_clients):
    """Deadline expires without a terminal status -> Timeout result + stop_query cleanup."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools import (
        _run_logs_insights_query_sync,
    )

    mock_aws_clients['logs_client'].start_query.return_value = {'queryId': 'qid-timeout'}
    # Always Running -> loop only exits via the deadline.
    mock_aws_clients['logs_client'].get_query_results.return_value = {
        'status': 'Running',
        'results': [],
        'statistics': {},
    }
    # mock_time.monotonic returns 0, 1, 2, ... so max_poll_seconds=2 forces exit in ~2 iters.
    result = _run_logs_insights_query_sync(
        **_query_sync_args(), poll_interval=0.1, max_poll_seconds=2
    )
    assert result['status'] == 'Timeout'
    assert result['queryId'] == 'qid-timeout'
    # Cleanup must fire so we don't leak the concurrency slot.
    mock_aws_clients['logs_client'].stop_query.assert_called_once_with(queryId='qid-timeout')


def test_run_logs_insights_query_sync_timeout_stop_query_failure_is_swallowed(
    mock_aws_clients,
):
    """stop_query failure during timeout cleanup must not propagate — return Timeout anyway."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools import (
        _run_logs_insights_query_sync,
    )

    mock_aws_clients['logs_client'].start_query.return_value = {'queryId': 'qid-ts-fail'}
    mock_aws_clients['logs_client'].get_query_results.return_value = {
        'status': 'Running',
        'results': [],
        'statistics': {},
    }
    mock_aws_clients['logs_client'].stop_query.side_effect = Exception('ThrottlingException')
    result = _run_logs_insights_query_sync(
        **_query_sync_args(), poll_interval=0.1, max_poll_seconds=2
    )
    # Caller must still see a structured Timeout; swallowed errors don't corrupt the shape.
    assert result['status'] == 'Timeout'
    assert result['queryId'] == 'qid-ts-fail'


# --- get_metric_data pagination (metrics action) ---


@pytest.mark.asyncio
async def test_metrics_follows_next_token(mock_aws_clients):
    """Pagination must follow NextToken across pages and merge results under the same metric."""
    from datetime import datetime, timezone

    ts1 = datetime(2026, 3, 1, tzinfo=timezone.utc)
    ts2 = datetime(2026, 3, 1, 0, 5, tzinfo=timezone.utc)
    mock_aws_clients['cloudwatch_client'].get_metric_data.side_effect = [
        {
            'MetricDataResults': [
                {
                    'Id': 'm0',
                    'Timestamps': [ts1],
                    'Values': [1.0],
                    'StatusCode': 'Complete',
                }
            ],
            'NextToken': 'page-2',
        },
        {
            'MetricDataResults': [
                {
                    'Id': 'm0',
                    'Timestamps': [ts2],
                    'Values': [2.0],
                    'StatusCode': 'Complete',
                }
            ],
        },
    ]
    result = json.loads(
        await query_rum_events(
            action='metrics',
            app_monitor_name='test',
            metric_names='["JsErrorCount"]',
            start_time=START,
            end_time=END,
        )
    )
    assert result['truncated'] is False
    assert mock_aws_clients['cloudwatch_client'].get_metric_data.call_count == 2
    # Second call must carry the NextToken from the first page.
    second_call_kwargs = mock_aws_clients['cloudwatch_client'].get_metric_data.call_args_list[1]
    assert second_call_kwargs.kwargs['NextToken'] == 'page-2'
    # Values from both pages are preserved.
    assert result['metrics']['JsErrorCount']['values'] == [1.0, 2.0]


@pytest.mark.asyncio
async def test_metrics_truncates_at_page_cap(mock_aws_clients):
    """Infinite NextToken must stop at _METRIC_DATA_PAGE_CAP and surface truncated=True."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools import (
        _METRIC_DATA_PAGE_CAP,
    )

    # Every page returns a NextToken -> only the page cap breaks the loop.
    mock_aws_clients['cloudwatch_client'].get_metric_data.return_value = {
        'MetricDataResults': [
            {'Id': 'm0', 'Timestamps': [], 'Values': [], 'StatusCode': 'Complete'}
        ],
        'NextToken': 'more',
    }
    result = json.loads(
        await query_rum_events(
            action='metrics',
            app_monitor_name='test',
            metric_names='["JsErrorCount"]',
            start_time=START,
            end_time=END,
        )
    )
    assert result['truncated'] is True
    assert result['page_cap'] == _METRIC_DATA_PAGE_CAP
    assert (
        mock_aws_clients['cloudwatch_client'].get_metric_data.call_count == _METRIC_DATA_PAGE_CAP
    )


# --- Defensive bad_request handler coverage (cw_log_disabled -> ValueError path) ---
#
# Every action handler that calls _get_rum_app_info wraps it in `try/except ValueError`
# and returns a structured bad_request. The `query` action is already covered by
# test_query_cw_log_disabled; this parametrized test exercises the same defensive branch
# in every remaining handler, matching the line-coverage gaps codecov flags for
# rum_tools.py (L686-687, L749-750, L778-779, L839-840, L862-863, L888-889, L940-941,
# L972-973, L997-998, L1039-1040, L1062-1063, L1101-1102, L1172-1173, L1230-1231,
# L1321-1322).


_CW_LOG_DISABLED_CASES = [
    # (action, extra_kwargs) — each action accepts app_monitor_name/start_time/end_time by default
    ('health', {}),
    ('errors', {}),
    ('performance', {}),
    ('sessions', {}),
    ('page_views', {}),
    ('timeseries', {}),
    ('locations', {}),
    ('http_requests', {}),
    ('session_detail', {'session_id': 'sid-1'}),
    ('resources', {}),
    ('page_flows', {}),
    ('crashes', {}),
    ('app_launches', {}),
    ('analyze', {}),
    ('correlate', {'page_url': '/home'}),
]


@pytest.mark.parametrize('action,extra_kwargs', _CW_LOG_DISABLED_CASES)
@pytest.mark.asyncio
async def test_action_returns_bad_request_when_cw_logs_disabled(
    mock_aws_clients, action, extra_kwargs
):
    """_get_rum_app_info raises ValueError when CW Logs is disabled; each handler must return bad_request."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response(
        cw_log_enabled=False
    )
    result = json.loads(
        await query_rum_events(
            action=action,
            app_monitor_name='test',
            start_time=START,
            end_time=END,
            **extra_kwargs,
        )
    )
    assert result.get('error_type') == 'bad_request'
    assert 'CloudWatch Logs' in result.get('error', '')
    # Defensive path must not have fired any Logs Insights calls.
    assert mock_aws_clients['logs_client'].start_query.call_count == 0


# --- check_rum_data_access individual-finding branches ---


@pytest.mark.asyncio
async def test_check_data_access_missing_telemetries(mock_aws_clients):
    """Telemetries missing 'http' surfaces a MEDIUM finding with the missing list."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response(
        telemetries=['errors', 'performance']  # 'http' missing
    )
    result = json.loads(
        await query_rum_events(action='check_data_access', app_monitor_name='test')
    )
    missing = [f for f in result['findings'] if 'Missing telemetry' in f['issue']]
    assert len(missing) == 1
    assert 'http' in missing[0]['issue']
    assert missing[0]['severity'] == 'MEDIUM'


@pytest.mark.asyncio
async def test_check_data_access_zero_sample_rate(mock_aws_clients):
    """sample_rate=0 surfaces a HIGH finding."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response(
        sample_rate=0
    )
    result = json.loads(
        await query_rum_events(action='check_data_access', app_monitor_name='test')
    )
    sr_findings = [f for f in result['findings'] if 'sample rate is 0' in f['issue']]
    assert len(sr_findings) == 1
    assert sr_findings[0]['severity'] == 'HIGH'


@pytest.mark.asyncio
async def test_check_data_access_low_sample_rate(mock_aws_clients):
    """0 < sample_rate < 0.1 surfaces a LOW finding (not HIGH)."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response(
        sample_rate=0.05
    )
    result = json.loads(
        await query_rum_events(action='check_data_access', app_monitor_name='test')
    )
    sr_findings = [f for f in result['findings'] if 'Low session sample rate' in f['issue']]
    assert len(sr_findings) == 1
    assert sr_findings[0]['severity'] == 'LOW'
    # Must NOT also fire the sample_rate==0 HIGH branch.
    assert not any('sample rate is 0' in f['issue'] for f in result['findings'])


@pytest.mark.asyncio
async def test_check_data_access_cookies_disabled(mock_aws_clients):
    """allowCookies=false surfaces a LOW finding about session tracking."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response(
        allow_cookies=False
    )
    result = json.loads(
        await query_rum_events(action='check_data_access', app_monitor_name='test')
    )
    cookie_findings = [f for f in result['findings'] if 'Cookies disabled' in f['issue']]
    assert len(cookie_findings) == 1
    assert cookie_findings[0]['severity'] == 'LOW'


# --- Unknown-platform early-bail paths (sessions L843, session_detail L1001) ---


@pytest.mark.asyncio
async def test_sessions_unknown_platform_bails(mock_aws_clients):
    """Sessions on unknown-platform monitor must return the guard, not run a query."""
    _setup_unknown_platform_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='sessions', app_monitor_name='test', start_time=START, end_time=END
        )
    )
    assert result.get('platform') == 'unknown'
    assert 'error' in result
    # Only the platform-detection filter_log_events call should have happened,
    # not a Logs Insights start_query.
    assert mock_aws_clients['logs_client'].start_query.call_count == 0


@pytest.mark.asyncio
async def test_session_detail_unknown_platform_bails(mock_aws_clients):
    """session_detail on unknown-platform monitor must return the guard, not run a query."""
    _setup_unknown_platform_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='session_detail',
            app_monitor_name='test',
            session_id='sid-1',
            start_time=START,
            end_time=END,
        )
    )
    assert result.get('platform') == 'unknown'
    assert 'error' in result
    assert mock_aws_clients['logs_client'].start_query.call_count == 0


# --- Web Vitals 'needs-improvement' bucket + malformed-p90 (performance L814, L818-819) ---


@pytest.mark.asyncio
async def test_performance_vitals_needs_improvement_and_malformed_p90(mock_aws_clients):
    """Middle bucket (p90 between good and poor) -> 'needs-improvement'; non-numeric p90 -> no assessment, no crash."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response()
    mock_aws_clients['logs_client'].start_query.return_value = {'queryId': 'qid'}
    call_count = [0]

    def mock_get_results(**kwargs):
        call_count[0] += 1
        if call_count[0] <= 1:  # nav query
            return _logs_result()
        # vitals query — one needs-improvement LCP, one malformed p90 that must not crash
        return {
            'status': 'Complete',
            'results': [
                [
                    {
                        'field': 'event_type',
                        'value': 'com.amazon.rum.largest_contentful_paint_event',
                    },
                    {'field': 'p90', 'value': '3000'},  # between 2500 (good) and 4000 (poor)
                ],
                [
                    {
                        'field': 'event_type',
                        'value': 'com.amazon.rum.first_input_delay_event',
                    },
                    {'field': 'p90', 'value': 'not-a-number'},
                ],
            ],
            'statistics': {'recordsMatched': 2.0},
        }

    mock_aws_clients['logs_client'].get_query_results.side_effect = mock_get_results
    result = json.loads(
        await query_rum_events(
            action='performance', app_monitor_name='test', start_time=START, end_time=END
        )
    )
    vitals = result['web_vitals']['results']
    lcp = [r for r in vitals if 'largest_contentful_paint' in r.get('event_type', '')][0]
    fid = [r for r in vitals if 'first_input_delay' in r.get('event_type', '')][0]
    assert lcp['assessment'] == 'needs-improvement'
    # Malformed p90 must leave the row intact without an 'assessment' key set.
    assert 'assessment' not in fid


# --- Partition resolution (L202, L204) ---


def test_get_partition_us_gov(mock_aws_clients):
    """us-gov-* regions resolve to the aws-us-gov partition."""
    from awslabs.cloudwatch_applicationsignals_mcp_server import rum_tools as _rt

    with patch.object(_rt, 'AWS_REGION', 'us-gov-west-1'):
        _rt._get_partition.cache_clear()
        try:
            assert _rt._get_partition() == 'aws-us-gov'
        finally:
            _rt._get_partition.cache_clear()


def test_get_partition_cn(mock_aws_clients):
    """cn-* regions resolve to the aws-cn partition."""
    from awslabs.cloudwatch_applicationsignals_mcp_server import rum_tools as _rt

    with patch.object(_rt, 'AWS_REGION', 'cn-north-1'):
        _rt._get_partition.cache_clear()
        try:
            assert _rt._get_partition() == 'aws-cn'
        finally:
            _rt._get_partition.cache_clear()


# --- _get_rum_app_info_confident_cached: missing log group name (L250) ---


def test_get_rum_app_info_missing_log_group_raises(mock_aws_clients):
    """CwLogEnabled=True but no CwLogGroup name must raise ValueError with a clear message."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools import (
        _get_rum_app_info_confident_cached,
    )

    mock_aws_clients['rum_client'].get_app_monitor.return_value = {
        'AppMonitor': {
            'Name': 'test',
            'Platform': 'Web',
            'DataStorage': {'CwLog': {'CwLogEnabled': True}},  # no CwLogGroup
            'AppMonitorConfiguration': {},
        }
    }
    with pytest.raises(ValueError, match='no log group'):
        _get_rum_app_info_confident_cached('test')


# --- _parse_time naive datetime normalization (L428) ---


def test_parse_time_naive_datetime_is_normalized_to_utc():
    """A naive ISO timestamp (no offset) must be attached to UTC rather than rejected."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools import _parse_time

    dt = _parse_time('2026-03-01T00:00:00')  # no 'Z', no offset
    assert dt.tzinfo is not None
    offset = dt.utcoffset()
    assert offset is not None
    assert offset.total_seconds() == 0


# --- Service-error branches for simple RUM get/list actions ---


@pytest.mark.asyncio
async def test_list_tags_service_error(mock_aws_clients):
    """list_tags_for_resource failure surfaces service_error."""
    mock_aws_clients['rum_client'].list_tags_for_resource.side_effect = Exception('boom')
    result = json.loads(
        await query_rum_events(
            action='list_tags', resource_arn='arn:aws:rum:us-east-1:123:appmonitor/t'
        )
    )
    assert result.get('error_type') == 'service_error'


@pytest.mark.asyncio
async def test_get_policy_service_error(mock_aws_clients):
    """get_resource_policy failure surfaces service_error."""
    mock_aws_clients['rum_client'].get_resource_policy.side_effect = Exception('denied')
    result = json.loads(await query_rum_events(action='get_policy', app_monitor_name='test'))
    assert result.get('error_type') == 'service_error'


@pytest.mark.asyncio
async def test_check_data_access_service_error(mock_aws_clients):
    """Non-ResourceNotFound errors on get_app_monitor return service_error."""

    # check_rum_data_access does `except rum_client.exceptions.ResourceNotFoundException`
    # first. On a MagicMock the `.exceptions.*` attribute is itself a MagicMock
    # (not a class), so unless we install a real exception class there, the
    # `except` itself raises TypeError and bubbles up through the dispatcher's
    # bad_request branch rather than the handler's service_error branch.
    class _RNF(Exception):
        pass

    mock_aws_clients['rum_client'].exceptions.ResourceNotFoundException = _RNF
    mock_aws_clients['rum_client'].get_app_monitor.side_effect = Exception('unexpected')
    result = json.loads(
        await query_rum_events(action='check_data_access', app_monitor_name='test')
    )
    assert result.get('error_type') == 'service_error'


@pytest.mark.asyncio
async def test_query_service_error(mock_aws_clients):
    """Logs Insights StartQuery failure surfaces service_error from query action."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response()
    mock_aws_clients['logs_client'].start_query.side_effect = Exception('quota')
    result = json.loads(
        await query_rum_events(
            action='query',
            app_monitor_name='test',
            query_string='fields @timestamp',
            start_time=START,
            end_time=END,
        )
    )
    assert result.get('error_type') == 'service_error'


# --- Dispatcher bad-kwarg TypeError branch (lines 180-181) ---


@pytest.mark.asyncio
async def test_dispatcher_extra_kwarg_returns_bad_request(mock_aws_clients):
    """Passing an action-irrelevant kwarg triggers the TypeError guard, not a 500."""
    # list_tags only accepts resource_arn; supplying app_monitor_name raises
    # TypeError inside the dispatcher's try/except.
    mock_aws_clients['rum_client'].list_tags_for_resource.return_value = {'Tags': {}}
    result = json.loads(
        await query_rum_events(
            action='list_tags',
            resource_arn='arn:aws:rum:us-east-1:123:appmonitor/t',
            app_monitor_name='test',  # extraneous for list_tags
        )
    )
    assert result.get('error_type') == 'bad_request'


# --- Mobile platform dispatch partial branches (crashes 'ios' only path) ---


@pytest.mark.asyncio
async def test_crashes_ios_only_skips_android_query(mock_aws_clients):
    """platform='ios' must dispatch only the iOS queries, not the Android ones."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response(
        platform='iOS'
    )
    mock_aws_clients['logs_client'].start_query.return_value = {'queryId': 'qid'}
    mock_aws_clients['logs_client'].get_query_results.return_value = _logs_result(rows=[])
    result = json.loads(
        await query_rum_events(
            action='crashes',
            app_monitor_name='test',
            start_time=START,
            end_time=END,
            platform='ios',
        )
    )
    assert 'ios_crashes' in result
    assert 'ios_hangs' in result
    assert 'android' not in result
    assert 'android_anrs' not in result


@pytest.mark.asyncio
async def test_crashes_android_only_skips_ios_query(mock_aws_clients):
    """platform='android' must dispatch only the Android queries."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response(
        platform='Android'
    )
    mock_aws_clients['logs_client'].start_query.return_value = {'queryId': 'qid'}
    mock_aws_clients['logs_client'].get_query_results.return_value = _logs_result(rows=[])
    result = json.loads(
        await query_rum_events(
            action='crashes',
            app_monitor_name='test',
            start_time=START,
            end_time=END,
            platform='android',
        )
    )
    assert 'android' in result
    assert 'android_anrs' in result
    assert 'ios_crashes' not in result


@pytest.mark.asyncio
async def test_app_launches_ios_only(mock_aws_clients):
    """platform='ios' for app_launches dispatches only the iOS task."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response(
        platform='iOS'
    )
    mock_aws_clients['logs_client'].start_query.return_value = {'queryId': 'qid'}
    mock_aws_clients['logs_client'].get_query_results.return_value = _logs_result(rows=[])
    result = json.loads(
        await query_rum_events(
            action='app_launches',
            app_monitor_name='test',
            start_time=START,
            end_time=END,
            platform='ios',
        )
    )
    assert 'ios' in result
    assert 'android' not in result


@pytest.mark.asyncio
async def test_crashes_all_on_web_monitor_returns_web_guidance(mock_aws_clients):
    """platform='all' on a web monitor returns a message rather than running queries."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response(
        platform='Web'
    )
    result = json.loads(
        await query_rum_events(
            action='crashes',
            app_monitor_name='test',
            start_time=START,
            end_time=END,
            platform='all',
        )
    )
    assert 'message' in result
    assert result.get('monitor_platform') == 'web'


@pytest.mark.asyncio
async def test_app_launches_all_on_web_monitor_returns_web_guidance(mock_aws_clients):
    """platform='all' on a web monitor for app_launches returns the web-guidance message."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response(
        platform='Web'
    )
    result = json.loads(
        await query_rum_events(
            action='app_launches',
            app_monitor_name='test',
            start_time=START,
            end_time=END,
            platform='all',
        )
    )
    assert 'message' in result
    assert result.get('monitor_platform') == 'web'


# --- correlate bad max_traces (TypeError/ValueError branch 1329-1330) ---


@pytest.mark.asyncio
async def test_correlate_invalid_max_traces_is_bad_request(mock_aws_clients):
    """Non-integer max_traces must return bad_request, not crash."""
    _setup_logs_mocks(mock_aws_clients)
    result = json.loads(
        await query_rum_events(
            action='correlate',
            app_monitor_name='test',
            page_url='/home',
            start_time=START,
            end_time=END,
            max_traces='not-a-number',  # type: ignore[arg-type]
        )
    )
    assert result.get('error_type') == 'bad_request'


# --- correlate malformed segment document (ValueError path in json.loads) ---


@pytest.mark.asyncio
async def test_correlate_malformed_segment_is_skipped(mock_aws_clients):
    """A malformed segment Document must be logged and skipped, not abort the run."""
    _setup_logs_mocks(mock_aws_clients)
    mock_aws_clients['logs_client'].get_query_results.return_value = _logs_result(
        rows=[[{'field': 'event_details.trace_id', 'value': 'T1'}]]
    )
    mock_aws_clients['xray_client'].batch_get_traces.return_value = {
        'Traces': [
            {
                'Id': 'T1',
                'Segments': [
                    {'Document': 'not-json'},  # triggers ValueError
                    {'Document': json.dumps({'name': 'svc', 'start_time': 1.0, 'end_time': 2.0})},
                ],
            }
        ]
    }
    result = json.loads(
        await query_rum_events(
            action='correlate',
            app_monitor_name='test',
            page_url='/home',
            start_time=START,
            end_time=END,
        )
    )
    assert 'svc' in result['backend_services']


# --- correlate segment missing start_time/end_time (line 1413 partial branch) ---


@pytest.mark.asyncio
async def test_correlate_segment_missing_times_is_skipped(mock_aws_clients):
    """Segments without start_time or end_time must be skipped, not counted."""
    _setup_logs_mocks(mock_aws_clients)
    mock_aws_clients['logs_client'].get_query_results.return_value = _logs_result(
        rows=[[{'field': 'event_details.trace_id', 'value': 'T1'}]]
    )
    mock_aws_clients['xray_client'].batch_get_traces.return_value = {
        'Traces': [
            {
                'Id': 'T1',
                'Segments': [
                    {'Document': json.dumps({'name': 'svc', 'start_time': 1.0})},  # no end
                    {
                        'Document': json.dumps(
                            {
                                'name': 'svc',
                                'start_time': 1.0,
                                'end_time': 2.0,
                                'error': True,
                            }
                        )
                    },
                ],
            }
        ]
    }
    result = json.loads(
        await query_rum_events(
            action='correlate',
            app_monitor_name='test',
            page_url='/home',
            start_time=START,
            end_time=END,
        )
    )
    # only one call counted (the complete segment)
    assert result['backend_services']['svc']['calls'] == 1
    assert result['backend_services']['svc']['errors'] == 1


# --- analyze: anomaly pagination error branch (line 1258-1260) ---


@pytest.mark.asyncio
async def test_analyze_anomaly_listing_error_is_swallowed(mock_aws_clients):
    """If list_anomalies fails for a detector, analyze must continue cleanly."""
    _setup_logs_mocks(mock_aws_clients)
    mock_aws_clients['logs_client'].list_log_anomaly_detectors.return_value = {
        'anomalyDetectors': [
            {
                'detectorName': 'd1',
                'anomalyDetectorStatus': 'ACTIVE',
                'anomalyDetectorArn': 'arn:aws:logs:us-east-1:123:anomaly-detector:d1',
            }
        ]
    }
    mock_aws_clients['logs_client'].list_anomalies.side_effect = Exception('denied')
    result = json.loads(
        await query_rum_events(
            action='analyze',
            app_monitor_name='test',
            start_time=START,
            end_time=END,
        )
    )
    # Detector is listed but anomalies list is empty due to swallowed error.
    assert result['anomaly_detection']['anomalies'] == []
    assert any(d['name'] == 'd1' for d in result['anomaly_detection']['detectors'])


# --- analyze: _fetch_anomaly_detectors error branch (line 1241-1242) ---


@pytest.mark.asyncio
async def test_analyze_detector_listing_error_is_surfaced(mock_aws_clients):
    """If list_log_anomaly_detectors fails, analyze must expose an anomaly_detection.error."""
    _setup_logs_mocks(mock_aws_clients)
    mock_aws_clients['logs_client'].list_log_anomaly_detectors.side_effect = Exception('denied')
    result = json.loads(
        await query_rum_events(
            action='analyze',
            app_monitor_name='test',
            start_time=START,
            end_time=END,
        )
    )
    assert 'error' in result['anomaly_detection']


# --- metrics: malformed MetricDataResults payload (line 1536 branch) ---


@pytest.mark.asyncio
async def test_metrics_status_ranks_choose_worst(mock_aws_clients):
    """Subsequent pages with a worse StatusCode must bump the entry status."""
    mock_aws_clients['rum_client'].get_app_monitor.return_value = _app_monitor_response()
    # Two pages: first 'Complete', second 'PartialData' — PartialData must win.
    mock_aws_clients['cloudwatch_client'].get_metric_data.side_effect = [
        {
            'MetricDataResults': [
                {
                    'Id': 'm0',
                    'Label': 'PageLoadTime',
                    'Timestamps': [],
                    'Values': [],
                    'StatusCode': 'Complete',
                }
            ],
            'NextToken': 'tok',
        },
        {
            'MetricDataResults': [
                {
                    'Id': 'm0',
                    'Label': 'PageLoadTime',
                    'Timestamps': [],
                    'Values': [],
                    'StatusCode': 'PartialData',
                }
            ]
        },
    ]
    result = json.loads(
        await query_rum_events(
            action='metrics',
            app_monitor_name='test',
            metric_names='["PageLoadTime"]',
            start_time=START,
            end_time=END,
        )
    )
    assert result['metrics']['PageLoadTime']['status'] == 'PartialData'


# --- slo_health: list_service_level_objectives raises (line 1592-1593) ---


@pytest.mark.asyncio
async def test_slo_health_list_failure_returns_no_slo_with_message(mock_aws_clients):
    """If listing SLOs raises, return NO_SLO with a message rather than crashing."""
    mock_aws_clients['applicationsignals_client'].get_paginator.side_effect = Exception('denied')
    result = json.loads(
        await query_rum_events(
            action='slo_health',
            app_monitor_name='test',
            start_time=START,
            end_time=END,
        )
    )
    assert result['status'] == 'NO_SLO'
    assert 'Could not list SLOs' in result.get('message', '')


# --- _extract_slo_metric_name helper (lines 1707-1721) ---


def test_extract_slo_metric_name_from_good_count_metric():
    """GoodCountMetric path returns the metric name."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools import (
        _extract_slo_metric_name,
    )

    slo = {
        'RequestBasedSli': {
            'RequestBasedSliMetric': {
                'MonitoredRequestCountMetric': {
                    'GoodCountMetric': [
                        {
                            'Id': 'good_1',
                            'MetricStat': {'Metric': {'MetricName': 'Success'}},
                        }
                    ]
                }
            }
        }
    }
    assert _extract_slo_metric_name(slo) == 'Success'


def test_extract_slo_metric_name_from_bad_count_metric():
    """BadCountMetric path (fault_*) also returns a metric name."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools import (
        _extract_slo_metric_name,
    )

    slo = {
        'RequestBasedSli': {
            'RequestBasedSliMetric': {
                'MonitoredRequestCountMetric': {
                    'BadCountMetric': [
                        {
                            'Id': 'fault_1',
                            'MetricStat': {'Metric': {'MetricName': 'Fault'}},
                        }
                    ]
                }
            }
        }
    }
    assert _extract_slo_metric_name(slo) == 'Fault'


def test_extract_slo_metric_name_from_sli_metric_fallback():
    """Falls back to Sli.SliMetric.MetricDataQueries when request-based paths empty."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools import (
        _extract_slo_metric_name,
    )

    slo = {
        'Sli': {
            'SliMetric': {
                'MetricDataQueries': [{'MetricStat': {'Metric': {'MetricName': 'Latency'}}}]
            }
        }
    }
    assert _extract_slo_metric_name(slo) == 'Latency'


def test_extract_slo_metric_name_unknown_when_no_paths_match():
    """Empty SLO returns the sentinel 'unknown' rather than raising."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools import (
        _extract_slo_metric_name,
    )

    assert _extract_slo_metric_name({}) == 'unknown'


def test_extract_slo_metric_name_skips_non_list_count_metrics():
    """GoodCountMetric that isn't a list must be skipped (not crash) and fall through."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools import (
        _extract_slo_metric_name,
    )

    slo = {
        'RequestBasedSli': {
            'RequestBasedSliMetric': {
                'MonitoredRequestCountMetric': {'GoodCountMetric': 'not-a-list'}
            }
        },
        'Sli': {
            'SliMetric': {
                'MetricDataQueries': [{'MetricStat': {'Metric': {'MetricName': 'Fallback'}}}]
            }
        },
    }
    assert _extract_slo_metric_name(slo) == 'Fallback'
