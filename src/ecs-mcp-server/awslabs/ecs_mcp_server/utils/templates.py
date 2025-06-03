# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""
Template utilities for the ECS MCP Server.
"""

import logging
import os

logger = logging.getLogger(__name__)


def get_templates_dir() -> str:
    """
    Gets the path to the templates directory.

    Returns:
        Path to the templates directory
    """
    templates_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates"
    )

    if not os.path.isdir(templates_dir):
        logger.error(f"Templates directory not found at {templates_dir}")
        raise FileNotFoundError(f"Templates directory not found at {templates_dir}")

    return templates_dir
