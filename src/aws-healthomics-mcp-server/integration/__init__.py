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


"""Remote-deployment integration test harness for the AWS HealthOmics MCP Server.

This package is opt-in and entirely separate from the offline test suite under
``tests/``. It is skipped by default and only exercises live AWS resources when the
``RUN_REMOTE_INTEGRATION_TESTS`` signal is present. No module under ``tests/`` imports
from this package.
"""
