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

"""Response formatting utilities following AWS Labs patterns."""

import json
from typing import Any, Dict


def format_error_response(error: str, error_code: str) -> Dict[str, Any]:
    """Format error response following AWS Labs standards.
    
    Args:
        error: Error message
        error_code: Error code for categorization
        
    Returns:
        Standardized error response dictionary
    """
    return {
        "success": False,
        "error": error,
        "error_code": error_code
    }


def format_success_response(data: Any) -> Dict[str, Any]:
    """Format success response following AWS Labs standards.
    
    Args:
        data: Response data
        
    Returns:
        Standardized success response dictionary
    """
    return {
        "success": True,
        "data": data
    }


def safe_json_dumps(data: Any, **kwargs) -> str:
    """Safely serialize data to JSON string.
    
    Args:
        data: Data to serialize
        **kwargs: Additional arguments for json.dumps
        
    Returns:
        JSON string representation
    """
    try:
        return json.dumps(data, **kwargs)
    except TypeError:
        # Handle non-serializable objects
        return json.dumps(str(data), **kwargs)
