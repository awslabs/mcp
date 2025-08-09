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
from typing import Any, Dict, Optional

__all__ = ["AWSConfigManager"]

# Global configuration instance
_aws_config_instance = None

def get_aws_config() -> Optional['AWSConfigManager']:
    """Get AWS config instance with error handling.
    
    Returns a simple config object without dependencies on server module.
    """
    global _aws_config_instance
    if '_aws_config_instance' not in globals():
        # Create a minimal config manager without server dependencies
        class MinimalAWSConfigManager:
            @property
            def profile(self) -> Optional[str]:
                import os
                return os.environ.get("AWS_PROFILE")
            
            @property
            def default_region(self) -> str:
                import os
                return os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        
        _aws_config_instance = MinimalAWSConfigManager()
    return _aws_config_instance

def get_aws_client(service: str, region: str | None = None):
    """Get AWS client using the cached function."""
    return _create_client(service, region or "us-east-1")

def safe_json_dumps(data: Dict[str, Any], indent: int = 2) -> str:
    """Safe JSON serialization."""
    try:
        return json.dumps(data, indent=indent, default=str)
    except (TypeError, ValueError) as e:
        return json.dumps({"error": f"JSON serialization failed: {str(e)}"}, indent=indent)

class AWSConfigManager:
    """AWS configuration manager class."""
    
    async def aws_config_manager(operation: str, profile: str | None = None, region: str | None = None) -> str:
        try:
            global _client_cache
            _client_cache = _create_client.cache_info()  # Initialize cache reference
            aws_config = get_aws_config()  # Get the config instance

            if operation == "get_current":
                current_profile = aws_config.profile or "default"
                current_region = aws_config.region or "us-east-1"

                # Test current configuration
                try:
                    test_client = get_aws_client("sts", current_region)
                    identity = test_client.get_caller_identity()
                    config_valid = True
                    identity_info = {
                        "account": identity.get("Account"),
                        "user_id": identity.get("UserId"),
                        "arn": identity.get("Arn"),
                    }
                except Exception as e:
                    config_valid = False
                    identity_info = {"error": str(e)}

                result = {
                    "success": True,
                    "operation": operation,
                    "current_configuration": {
                        "aws_profile": current_profile,
                        "aws_region": current_region,
                        "configuration_valid": config_valid,
                        "identity": identity_info,
                        "cache_entries": len(_client_cache),
                    },
                }

            # ... existing code ...
            return safe_json_dumps(result, indent=2)

        except Exception as e:
            # Enhanced generic exception handling
            error_details = {
                "success": False,
                "operation": operation,
                "error": f"Unexpected error during configuration management: {str(e)}",
                "error_code": "UnknownError",
                "http_status_code": 500,
                "suggestion": "Review system configuration and AWS credentials",
            }

            # Use safe_json_dumps for consistent serialization
            return safe_json_dumps(error_details, indent=2)
