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

"""AWS configuration manager utilities."""

import json
import os
from typing import Any, Dict, Optional


class AWSConfigManager:
    """Basic AWS configuration manager."""
    
    def __init__(self):
        """Initialize AWS config manager."""
        pass
    
    @property
    def profile(self) -> Optional[str]:
        """Get current AWS profile."""
        return os.environ.get("AWS_PROFILE")
    
    @property
    def default_region(self) -> str:
        """Get current AWS region."""
        return os.environ.get("AWS_DEFAULT_REGION", "us-east-1")


def get_aws_config() -> AWSConfigManager:
    """Get AWS config instance."""
    global _aws_config_instance
    if '_aws_config_instance' not in globals():
        _aws_config_instance = AWSConfigManager()
    return _aws_config_instance


def safe_json_dumps(data: Dict[str, Any], indent: int = 2) -> str:
    """Safe JSON serialization with error handling."""
    try:
        return json.dumps(data, indent=indent, default=str)
    except (TypeError, ValueError) as e:
        return json.dumps({
            "error": f"JSON serialization failed: {str(e)}",
            "success": False
        }, indent=indent)


# Re-export for test compatibility
__all__ = ['AWSConfigManager', 'get_aws_config', 'safe_json_dumps']