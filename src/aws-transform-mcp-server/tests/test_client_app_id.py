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

from awslabs.aws_transform_mcp_server.consts import CLIENT_APP_ID, HEADER_CLIENT_APP_ID
from awslabs.aws_transform_mcp_server.transform_api_client import _create_unsigned_client


class TestClientAppIdHeader:  # noqa: D101
    def test_unsigned_client_injects_client_app_id(self):
        """Verify _create_unsigned_client registers clientAppId on all requests."""
        client = _create_unsigned_client('https://fake.endpoint.com')

        captured = {}

        def capture_request(request, **kwargs):
            captured.update(
                {k: v.decode() if isinstance(v, bytes) else v for k, v in request.headers.items()}
            )

        client.meta.events.register('before-send', capture_request)

        try:
            client.list_workspaces()
        except Exception:
            pass

        assert captured.get(HEADER_CLIENT_APP_ID) == CLIENT_APP_ID
