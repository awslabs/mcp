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

"""One stored format for Cost Explorer time periods.

getCostAndUsage returns DAILY and MONTHLY periods as ``YYYY-MM-DD``, while
getCostAndUsageWithResources returns the same periods as
``YYYY-MM-DDT00:00:00Z``. SQLite compares TEXT byte by byte, so with both
stored verbatim a date-literal ``BETWEEN`` drops the last day of the timestamp
table and a JOIN on ``time_period_start`` across the two matches nothing.
"""

import pytest
import sqlite3
from awslabs.billing_cost_management_mcp_server.utilities import sql_utils
from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
    convert_api_response_to_table,
)
from fastmcp import Context
from unittest.mock import MagicMock, patch


DAYS = [
    '2026-10-05',
    '2026-10-06',
    '2026-10-07',
    '2026-10-08',
    '2026-10-09',
    '2026-10-10',
    '2026-10-11',
]


class _KeepOpenConnection(sqlite3.Connection):
    """An in-memory connection that survives the converter closing it."""

    def close(self):
        pass


def in_memory_session_db():
    """An in-memory session database with the schema_info bookkeeping table."""
    conn = sqlite3.connect(':memory:', factory=_KeepOpenConnection)
    conn.execute(
        'CREATE TABLE IF NOT EXISTS schema_info '
        '(table_name TEXT PRIMARY KEY, created_at TEXT, operation TEXT, '
        'query TEXT, row_count INTEGER)'
    )
    return conn


def _ce_response(fmt):
    """One DAILY week, one group, $1 a day; ``fmt`` renders a ``YYYY-MM-DD`` day."""
    results = []
    for i, day in enumerate(DAYS):
        nxt = DAYS[i + 1] if i + 1 < len(DAYS) else '2026-10-12'
        results.append(
            {
                'TimePeriod': {'Start': fmt(day), 'End': fmt(nxt)},
                'Estimated': False,
                'Total': {},
                'Groups': [
                    {
                        'Keys': ['i-0abc'],
                        'Metrics': {'UnblendedCost': {'Amount': '1.0', 'Unit': 'USD'}},
                    }
                ],
            }
        )
    return {'ResultsByTime': results}


def _hourly_response():
    """Two HOURLY periods starting at midnight, $1 each."""
    starts = ['2026-10-05T00:00:00Z', '2026-10-05T01:00:00Z', '2026-10-05T02:00:00Z']
    return {
        'ResultsByTime': [
            {
                'TimePeriod': {'Start': starts[i], 'End': starts[i + 1]},
                'Estimated': False,
                'Total': {'UnblendedCost': {'Amount': '1.0', 'Unit': 'USD'}},
                'Groups': [],
            }
            for i in range(2)
        ]
    }


def _forecast_response(start, end):
    return {
        'Total': {'Amount': '30.0', 'Unit': 'USD'},
        'ForecastResultsByTime': [
            {'TimePeriod': {'Start': start, 'End': end}, 'MeanValue': '30.0'}
        ],
    }


async def _store(conn, response, op):
    with patch.object(sql_utils, 'get_db_connection', return_value=(conn, conn.cursor())):
        return await convert_api_response_to_table(MagicMock(spec=Context), response, op)


def _periods(conn, table):
    return conn.execute(
        f'SELECT DISTINCT time_period_start, time_period_end FROM {table} ORDER BY 1'
    ).fetchall()


@pytest.fixture
async def tables():
    """The same DAILY week stored from getCostAndUsage and from WithResources."""
    conn = in_memory_session_db()
    plain = await _store(conn, _ce_response(lambda d: d), 'cost_explorer_get_cost_and_usage')
    with_res = await _store(
        conn,
        _ce_response(lambda d: f'{d}T00:00:00Z'),
        'cost_explorer_get_cost_and_usage_with_resources',
    )
    return conn, plain['table_name'], with_res['table_name']


@pytest.mark.asyncio
async def test_both_cost_tables_store_dates(tables):
    """A midnight DAILY timestamp is stored as the date getCostAndUsage returns."""
    conn, plain, with_res = tables
    expected = [(d, n) for d, n in zip(DAYS, DAYS[1:] + ['2026-10-12'])]
    assert _periods(conn, plain) == expected
    assert _periods(conn, with_res) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'where',
    [
        "time_period_start BETWEEN '2026-10-05' AND '2026-10-11'",
        "time_period_start >= '2026-10-05' AND time_period_start <= '2026-10-11'",
    ],
)
async def test_date_filter_keeps_the_end_day(tables, where):
    """The same date filter sums all 7 days in both tables."""
    conn, plain, with_res = tables
    for table in (plain, with_res):
        got = conn.execute(
            f'SELECT SUM(amount), COUNT(DISTINCT time_period_start) FROM {table} WHERE {where}'
        ).fetchone()
        assert got == (7.0, 7), table


@pytest.mark.asyncio
async def test_join_on_time_period_start_matches_every_day(tables):
    """Joining the two cost tables by day matches all 7 days."""
    conn, plain, with_res = tables
    n = conn.execute(
        f'SELECT COUNT(*) FROM {plain} a JOIN {with_res} b '
        'ON a.time_period_start = b.time_period_start'
    ).fetchone()[0]
    assert n == 7


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'suffix',
    ['T00:00:00Z', 'T00:00:00.000Z', 'T00:00:00+00:00', 'T00:00:00+0000', 'T00:00Z', 'T00:00:00'],
)
async def test_midnight_spellings_become_dates(suffix):
    """Every spelling of UTC midnight is stored as the bare date."""
    conn = in_memory_session_db()
    handle = await _store(
        conn,
        _ce_response(lambda d: f'{d}{suffix}'),
        'cost_explorer_get_cost_and_usage_with_resources',
    )
    assert _periods(conn, handle['table_name'])[0] == ('2026-10-05', '2026-10-06')


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'op', ['cost_explorer_get_cost_and_usage', 'cost_explorer_get_cost_and_usage_with_resources']
)
async def test_hourly_keeps_its_timestamps(op):
    """HOURLY keeps the timestamp on every row, the midnight one included."""
    conn = in_memory_session_db()
    handle = await _store(conn, _hourly_response(), op)
    assert _periods(conn, handle['table_name']) == [
        ('2026-10-05T00:00:00Z', '2026-10-05T01:00:00Z'),
        ('2026-10-05T01:00:00Z', '2026-10-05T02:00:00Z'),
    ]


@pytest.mark.asyncio
async def test_non_utc_offset_is_not_treated_as_midnight():
    """Midnight in another offset is not a UTC day boundary, so the table keeps the values."""
    conn = in_memory_session_db()
    handle = await _store(
        conn,
        _ce_response(lambda d: f'{d}T00:00:00+05:00'),
        'cost_explorer_get_cost_and_usage_with_resources',
    )
    assert _periods(conn, handle['table_name'])[0] == (
        '2026-10-05T00:00:00+05:00',
        '2026-10-06T00:00:00+05:00',
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'odd',
    [
        '2026-10-05\n',
        '2026-10-05T00:00:00Z\n',
        '\u0662026-10-05',
        '2026-10-05T00:00:00-00:00',
        '2026-13-45T00:00:00Z',
        '2026-02-30',
    ],
)
async def test_near_dates_are_not_normalized(odd):
    """A value that is not exactly a date or UTC midnight is kept, with the whole response.

    Covers a trailing newline, a non-ASCII digit, the unknown offset ``-00:00`` and
    impossible dates, as a timestamp and as a bare date.
    """
    conn = in_memory_session_db()
    response = _ce_response(lambda d: f'{d}T00:00:00Z')
    response['ResultsByTime'][0]['TimePeriod']['Start'] = odd
    handle = await _store(conn, response, 'cost_explorer_get_cost_and_usage_with_resources')
    periods = _periods(conn, handle['table_name'])
    assert (odd, '2026-10-06T00:00:00Z') in periods
    assert ('2026-10-06T00:00:00Z', '2026-10-07T00:00:00Z') in periods
    assert handle['column_formats']['time_period_start'].startswith('TEXT as the API returned it')


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'op', ['cost_explorer_get_cost_forecast', 'cost_explorer_get_usage_forecast']
)
async def test_forecast_midnight_timestamps_become_dates(op):
    """Forecast tables get the same normalization as the cost tables."""
    conn = in_memory_session_db()
    handle = await _store(
        conn, _forecast_response('2026-11-01T00:00:00Z', '2026-12-01T00:00:00Z'), op
    )
    assert _periods(conn, handle['table_name']) == [('2026-11-01', '2026-12-01')]


@pytest.mark.asyncio
async def test_missing_period_values_are_stored_as_null():
    """A period without Start or End still stores, with NULL for the missing value."""
    conn = in_memory_session_db()
    response = _ce_response(lambda d: f'{d}T00:00:00Z')
    del response['ResultsByTime'][0]['TimePeriod']['End']
    handle = await _store(conn, response, 'cost_explorer_get_cost_and_usage_with_resources')
    assert _periods(conn, handle['table_name'])[0] == ('2026-10-05', None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'op',
    [
        'cost_explorer_get_cost_and_usage',
        'cost_explorer_get_cost_and_usage_with_resources',
        'cost_explorer_get_cost_forecast',
    ],
)
async def test_handle_states_the_time_format(op):
    """The handle and the time-ordered sample query say how periods are stored."""
    conn = in_memory_session_db()
    if 'forecast' in op:
        response = _forecast_response('2026-11-01', '2026-12-01')
    elif 'with_resources' in op:
        # Converted from timestamps: the handle describes the stored dates.
        response = _ce_response(lambda d: f'{d}T00:00:00Z')
    else:
        response = _ce_response(lambda d: d)
    handle = await _store(conn, response, op)
    formats = handle['column_formats']
    assert set(formats) == {'time_period_start', 'time_period_end'}
    assert formats['time_period_start'].startswith("TEXT 'YYYY-MM-DD' (UTC date)")
    assert formats['time_period_end'].startswith("TEXT 'YYYY-MM-DD' (UTC date)")
    assert 'exclusive' in formats['time_period_end']
    by_time = [q for q in handle['sample_queries'] if 'ORDER BY time_period_start' in q['sql']]
    assert by_time
    assert all(q['description'].endswith("time_period_start is 'YYYY-MM-DD'") for q in by_time)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'response',
    [_hourly_response(), _ce_response(lambda d: f'{d}T00:00:00+05:00')],
    ids=['hourly', 'non-utc-offset'],
)
async def test_handle_does_not_claim_dates_for_kept_timestamps(response):
    """When the bounds are kept as returned, the handle says so instead of promising dates."""
    conn = in_memory_session_db()
    handle = await _store(conn, response, 'cost_explorer_get_cost_and_usage_with_resources')
    start = handle['column_formats']['time_period_start']
    assert start.startswith('TEXT as the API returned it')
    assert '(UTC date)' not in start
    assert handle['column_formats']['time_period_end'].startswith('TEXT as the API returned it')
    by_time = [q for q in handle['sample_queries'] if 'ORDER BY time_period_start' in q['sql']]
    assert by_time and all('as the API returned it' in q['description'] for q in by_time)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'op,response',
    [
        ('cost_explorer_get_cost_and_usage', {'ResultsByTime': []}),
        ('cost_explorer_get_cost_and_usage', {'ResultsByTime': [{'TimePeriod': None}]}),
        ('cost_explorer_get_cost_forecast', {'ForecastResultsByTime': []}),
    ],
    ids=['no-results', 'no-bounds', 'no-forecasts'],
)
async def test_no_time_format_without_bounds(op, response):
    """With no period bound to describe, the handle makes no claim about the format."""
    conn = in_memory_session_db()
    handle = await _store(conn, response, op)
    assert 'column_formats' not in handle
    by_time = [q for q in handle['sample_queries'] if 'ORDER BY time_period_start' in q['sql']]
    assert all('time_period_start is' not in q['description'] for q in by_time)


@pytest.mark.asyncio
async def test_other_tables_carry_no_time_format():
    """Tables without CE time periods do not get the note."""
    conn = in_memory_session_db()
    handle = await _store(
        conn,
        {'DimensionValues': [{'Value': 'Amazon S3', 'Attributes': {}}]},
        'cost_explorer_get_dimension_values',
    )
    assert 'column_formats' not in handle
