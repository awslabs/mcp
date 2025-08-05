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

from ..config_manager import AWSConfigManager

__all__ = ["AWSConfigManager"]


class AWSConfigManager:
    """AWS configuration manager class."""
    
    async def aws_config_manager(operation: str, profile: str | None = None, region: str | None = None) -> str:
        try:
            global _client_cache
            _client_cache = _create_client.cache_info()  # Initialize cache reference

            if operation == "get_current":
                current_profile = aws_config.profile or "default"
                current_region = aws_config.default_region

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
