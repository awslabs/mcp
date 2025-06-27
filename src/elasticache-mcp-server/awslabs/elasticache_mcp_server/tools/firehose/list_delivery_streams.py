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

"""Tool for listing Kinesis Firehose delivery streams."""

from __future__ import annotations

from ...common.connection import FirehoseConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from typing import Any, Dict


@mcp.tool(name='list-delivery-streams')
@handle_exceptions
async def list_delivery_streams(
    limit: Any = None,
    delivery_stream_type: Any = None,
    exclusive_start_delivery_stream_name: Any = None,
) -> Dict[str, Any]:
    """List your delivery streams.

    Args:
        limit: The maximum number of delivery streams to list
        delivery_stream_type: The delivery stream type. This can be one of the following values:
            DirectPut - Provider data is sent directly to the Firehose stream
            KinesisStreamAsSource - Data is sourced from an existing Kinesis stream
        exclusive_start_delivery_stream_name: The name of the delivery stream to start the list after

    Returns:
        Dict containing the list of delivery streams and whether there are more streams available
    """
    client = FirehoseConnectionManager.get_connection()

    # Build request parameters
    params: Dict[str, Any] = {}
    if limit is not None:
        params['Limit'] = limit
    if delivery_stream_type is not None:
        params['DeliveryStreamType'] = delivery_stream_type
    if exclusive_start_delivery_stream_name is not None:
        params['ExclusiveStartDeliveryStreamName'] = exclusive_start_delivery_stream_name

    # Make API call
    try:
        response = client.list_delivery_streams(**params)
        return {
            'DeliveryStreamNames': response.get('DeliveryStreamNames', []),
            'HasMoreDeliveryStreams': response.get('HasMoreDeliveryStreams', False),
        }
    except Exception as e:
        return {'error': str(e)}
