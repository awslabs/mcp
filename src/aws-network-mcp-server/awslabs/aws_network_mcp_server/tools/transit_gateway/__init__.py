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

from .detect_transit_gateway_inspection import detect_tgw_inspection
from .get_all_transit_gateway_routes import get_all_tgw_routes
from .get_transit_gateway_details import get_tgw
from .get_transit_gateway_routes import get_tgw_routes
from .get_transit_gateway_flow_logs import get_tgw_flow_logs
from .list_transit_gateway_peerings import list_tgw_peerings
from .list_transit_gateways import list_transit_gateways

__all__ = [
    'detect_tgw_inspection',
    'get_all_tgw_routes',
    'get_tgw',
    'get_tgw_routes',
    'get_tgw_flow_logs',
    'list_tgw_peerings',
    'list_transit_gateways',
]
