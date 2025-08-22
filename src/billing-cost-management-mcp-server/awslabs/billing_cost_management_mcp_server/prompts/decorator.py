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

import functools
from typing import Any, Callable, Optional, Set, TypeVar, cast


# Type variable for functions that can be decorated
F = TypeVar('F', bound=Callable[..., Any])


def finops_prompt(
    name: Optional[str] = None, description: Optional[str] = None, tags: Optional[Set[str]] = None
):
    """Decorator to mark a function as a FinOps prompt.

    Args:
        name: Optional name for the prompt (defaults to function name)
        description: Optional description (defaults to function docstring)
        tags: Optional set of tags (defaults to {"finops"})

    Returns:
        Callable: Decorated function with prompt metadata
    """

    def decorator(func: F) -> F:
        # Store metadata on the function
        setattr(func, '_finops_prompt', True)
        setattr(func, '_prompt_name', name or func.__name__)
        setattr(func, '_prompt_description', description or func.__doc__ or '')
        setattr(func, '_prompt_tags', tags or {'finops'})

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        # Transfer attributes to the wrapper
        setattr(wrapper, '_finops_prompt', True)
        setattr(wrapper, '_prompt_name', name or func.__name__)
        setattr(wrapper, '_prompt_description', description or func.__doc__ or '')
        setattr(wrapper, '_prompt_tags', tags or {'finops'})

        return cast(F, wrapper)

    return decorator
