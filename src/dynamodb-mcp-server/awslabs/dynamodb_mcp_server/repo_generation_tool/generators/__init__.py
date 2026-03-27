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

"""Code generators for DynamoDB repository generation."""

from awslabs.dynamodb_mcp_server.repo_generation_tool.generators.jinja2_generator import (
    Jinja2Generator,
)


def create_generator(
    generator_type: str,
    schema_path: str,
    language: str = 'python',
    templates_dir: str = None,
    usage_data_path: str = None,
):
    """Factory function to create a generator instance."""
    if generator_type == 'jinja2':
        return Jinja2Generator(schema_path, templates_dir, language, usage_data_path)
    else:
        raise ValueError(f'Unknown generator type: {generator_type}')


__all__ = [
    'Jinja2Generator',
    'create_generator',
]
