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

"""
AWS Mocking Framework for CloudWAN MCP Server Tests.

This package provides hierarchical mocking utilities for AWS services,
enabling comprehensive and maintainable test fixtures.
"""

from .aws import AWSErrorCatalog, AWSServiceMocker, create_error_fixture, create_service_mocker

__all__ = ["AWSServiceMocker", "AWSErrorCatalog", "create_service_mocker", "create_error_fixture"]
