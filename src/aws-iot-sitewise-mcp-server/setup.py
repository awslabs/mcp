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

#!/usr/bin/env python

from setuptools import find_namespace_packages, setup


if __name__ == '__main__':
    setup(
        name='awslabs-aws-iot-sitewise-mcp-server',
        version='0.1.0',
        description='An AWS Labs Model Context Protocol (MCP) server for '
        'AWS IoT SiteWise API integration',
        packages=find_namespace_packages(include=['awslabs.*']),
        entry_points={
            'console_scripts': [
                'awslabs-aws-iot-sitewise-mcp-server='
                'awslabs.aws_iot_sitewise_mcp_server.server:main',
            ],
        },
    )
