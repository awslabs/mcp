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

"""Constants for the Beanstalk MCP Server."""

# Default configuration values
DEFAULT_REGION = 'us-east-1'
DEFAULT_MAX_RECORDS = 100

# API configuration
USER_AGENT_EXTRA = 'MCP/BeanstalkServer'

# Documentation content
BEANSTALK_INSTRUCTIONS = """
# AWS Elastic Beanstalk MCP Server

This MCP server allows you to:
1. Describe your AWS Elastic Beanstalk environments
2. Describe your applications running on Elastic Beanstalk
3. Explore your environment's configuration settings
4. Describe your environment's events, including different levels of messages.
"""
