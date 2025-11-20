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

from .knowledge_models import CDKToolResponse, KnowledgeResponse
from functools import wraps
from typing import Callable


def handle_cdk_tool_errors(error_prefix: str) -> Callable:
    """Decorator to handle errors in CDK tools.
    
    Args:
        error_prefix: Prefix to add to error messages.
        
    Returns:
        Decorator function.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> CDKToolResponse:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                return CDKToolResponse(
                    knowledge_response=KnowledgeResponse(
                        error=f'{error_prefix}: {str(e)}', results=[]
                    ),
                    next_step_guidance='Tool call failed, read the error provided in the knowledge_response field',
                )

        return wrapper

    return decorator
