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

"""Agent-driven end-to-end tests for the Redshift MCP server.

The tests are not written here. They are written by an agent, at run time, against live
warehouses: the harness provisions the AWS resources, hands an agent the server under test
over MCP, gives it a scenario in prose, and records what it did and concluded.

See README.md for the commands and what a run costs.
"""
