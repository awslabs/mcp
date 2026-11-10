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

"""Tests for how make_request handles HTTP error responses."""

import asyncio
import json
import pytest
import threading
import time
from awslabs.prometheus_mcp_server.server import PrometheusClient
from http.server import BaseHTTPRequestHandler, HTTPServer


@pytest.fixture
def prometheus_stub(monkeypatch):
    """Serve a fixed status and body, and record each request."""
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'AKIAEXAMPLE')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'secret')
    monkeypatch.delenv('AWS_PROFILE', raising=False)
    state = {'status': 200, 'body': {}, 'hits': 0}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            state['hits'] += 1
            body = json.dumps(state['body']).encode()
            self.send_response(state['status'])
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    server = HTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    state['url'] = f'http://127.0.0.1:{server.server_port}/workspaces/ws-1'
    yield state
    server.shutdown()


@pytest.mark.asyncio
async def test_bad_query_is_not_retried_and_keeps_the_parser_message(prometheus_stub):
    """A 400 for bad PromQL is final, and its error text reaches the caller."""
    prometheus_stub['status'] = 400
    prometheus_stub['body'] = {
        'status': 'error',
        'errorType': 'bad_data',
        'error': "1:5: parse error: unexpected right parenthesis ')'",
    }

    with pytest.raises(RuntimeError, match='parse error: unexpected right parenthesis'):
        await PrometheusClient.make_request(
            prometheus_stub['url'],
            'query',
            {'query': 'rate(up[5m]))'},
            region='us-east-1',
            retry_delay=0,
        )

    assert prometheus_stub['hits'] == 1


@pytest.mark.asyncio
async def test_server_error_is_retried_without_blocking_the_event_loop(prometheus_stub):
    """A 503 is retried, and the wait between attempts lets other tasks run."""
    prometheus_stub['status'] = 503
    ticks = []

    async def ticker():
        while True:
            ticks.append(time.monotonic())
            await asyncio.sleep(0.02)

    task = asyncio.create_task(ticker())
    await asyncio.sleep(0)
    try:
        with pytest.raises(Exception, match='503'):
            await PrometheusClient.make_request(
                prometheus_stub['url'],
                'query',
                {'query': 'up'},
                region='us-east-1',
                max_retries=2,
                retry_delay=1,
            )
    finally:
        task.cancel()

    assert prometheus_stub['hits'] == 2
    # About 50 ticks fit in the one-second wait; a blocking sleep allows one.
    assert len(ticks) > 10
