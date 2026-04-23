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

"""Auto-generated waiter configuration from botocore waiter model.

DO NOT EDIT — this file is auto-generated from the botocore service model.
"""

WAITER_REGISTRY: dict[str, dict] = {
    'channel_created': {
        'boto3_waiter_name': 'channel_created',
        'description': 'Wait until a channel has been created (polls DescribeChannel)',
        'delay': 3,
        'max_attempts': 5,
    },
    'channel_running': {
        'boto3_waiter_name': 'channel_running',
        'description': 'Wait until a channel is running (polls DescribeChannel)',
        'delay': 5,
        'max_attempts': 120,
    },
    'channel_stopped': {
        'boto3_waiter_name': 'channel_stopped',
        'description': 'Wait until a channel has is stopped (polls DescribeChannel)',
        'delay': 5,
        'max_attempts': 60,
    },
    'channel_deleted': {
        'boto3_waiter_name': 'channel_deleted',
        'description': 'Wait until a channel has been deleted (polls DescribeChannel)',
        'delay': 5,
        'max_attempts': 84,
    },
    'input_attached': {
        'boto3_waiter_name': 'input_attached',
        'description': 'Wait until an input has been attached (polls DescribeInput)',
        'delay': 5,
        'max_attempts': 20,
    },
    'input_detached': {
        'boto3_waiter_name': 'input_detached',
        'description': 'Wait until an input has been detached (polls DescribeInput)',
        'delay': 5,
        'max_attempts': 84,
    },
    'input_deleted': {
        'boto3_waiter_name': 'input_deleted',
        'description': 'Wait until an input has been deleted (polls DescribeInput)',
        'delay': 5,
        'max_attempts': 20,
    },
    'multiplex_created': {
        'boto3_waiter_name': 'multiplex_created',
        'description': 'Wait until a multiplex has been created (polls DescribeMultiplex)',
        'delay': 3,
        'max_attempts': 5,
    },
    'multiplex_running': {
        'boto3_waiter_name': 'multiplex_running',
        'description': 'Wait until a multiplex is running (polls DescribeMultiplex)',
        'delay': 5,
        'max_attempts': 120,
    },
    'multiplex_stopped': {
        'boto3_waiter_name': 'multiplex_stopped',
        'description': 'Wait until a multiplex has is stopped (polls DescribeMultiplex)',
        'delay': 5,
        'max_attempts': 28,
    },
    'multiplex_deleted': {
        'boto3_waiter_name': 'multiplex_deleted',
        'description': 'Wait until a multiplex has been deleted (polls DescribeMultiplex)',
        'delay': 5,
        'max_attempts': 20,
    },
    'signal_map_created': {
        'boto3_waiter_name': 'signal_map_created',
        'description': 'Wait until a signal map has been created (polls GetSignalMap)',
        'delay': 5,
        'max_attempts': 60,
    },
    'signal_map_monitor_deleted': {
        'boto3_waiter_name': 'signal_map_monitor_deleted',
        'description': 'Wait until a signal map\u0027s monitor has been deleted (polls GetSignalMap)',
        'delay': 5,
        'max_attempts': 120,
    },
    'signal_map_monitor_deployed': {
        'boto3_waiter_name': 'signal_map_monitor_deployed',
        'description': 'Wait until a signal map\u0027s monitor has been deployed (polls GetSignalMap)',
        'delay': 5,
        'max_attempts': 120,
    },
    'signal_map_updated': {
        'boto3_waiter_name': 'signal_map_updated',
        'description': 'Wait until a signal map has been updated (polls GetSignalMap)',
        'delay': 5,
        'max_attempts': 60,
    },
    'cluster_created': {
        'boto3_waiter_name': 'cluster_created',
        'description': 'Wait until a cluster has been created (polls DescribeCluster)',
        'delay': 3,
        'max_attempts': 5,
    },
    'cluster_deleted': {
        'boto3_waiter_name': 'cluster_deleted',
        'description': 'Wait until a cluster has been deleted (polls DescribeCluster)',
        'delay': 5,
        'max_attempts': 20,
    },
    'node_registered': {
        'boto3_waiter_name': 'node_registered',
        'description': 'Wait until a node has been registered (polls DescribeNode)',
        'delay': 3,
        'max_attempts': 5,
    },
    'node_deregistered': {
        'boto3_waiter_name': 'node_deregistered',
        'description': 'Wait until a node has been deregistered (polls DescribeNode)',
        'delay': 5,
        'max_attempts': 20,
    },
    'channel_placement_group_assigned': {
        'boto3_waiter_name': 'channel_placement_group_assigned',
        'description': 'Wait until the channel placement group has been assigned (polls DescribeChannelPlacementGroup)',
        'delay': 3,
        'max_attempts': 5,
    },
    'channel_placement_group_unassigned': {
        'boto3_waiter_name': 'channel_placement_group_unassigned',
        'description': 'Wait until the channel placement group has been unassigned (polls DescribeChannelPlacementGroup)',
        'delay': 5,
        'max_attempts': 20,
    },
    'channel_placement_group_deleted': {
        'boto3_waiter_name': 'channel_placement_group_deleted',
        'description': 'Wait until the channel placement group has been deleted (polls DescribeChannelPlacementGroup)',
        'delay': 5,
        'max_attempts': 20,
    },
}
