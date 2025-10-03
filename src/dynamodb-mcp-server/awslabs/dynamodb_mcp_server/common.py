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

import os
from functools import wraps
from typing import Callable


def handle_exceptions(func: Callable) -> Callable:
    """Decorator to handle exceptions in DynamoDB operations.

    Wraps the function in a try-catch block and returns any exceptions
    in a standardized error format.

    Args:
        func: The function to wrap

    Returns:
        The wrapped function that handles exceptions
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return {'error': str(e)}

    return wrapper


def mutation_check(func):
    """Decorator to block mutations if DDB-MCP-READONLY is set to true."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        readonly = os.environ.get('DDB-MCP-READONLY', '').lower()
        if readonly in ('true', '1', 'yes'):  # treat these as true
            return {'error': 'Mutation not allowed: DDB-MCP-READONLY is set to true.'}
        return await func(*args, **kwargs)

    return wrapper
