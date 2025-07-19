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

from typing import Any, Callable, Protocol, Set, TypeVar, cast


# Define a Protocol for functions with prompt attributes
class PromptFunction(Protocol):
    """Protocol for functions decorated with @finops_prompt."""

    _finops_prompt: bool
    _prompt_name: str
    _prompt_description: str
    _prompt_tags: Set[str]

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Call the function with the given arguments."""
        ...


# Type variable for functions that can be decorated
F = TypeVar('F', bound=Callable[..., Any])


def is_prompt_function(func: Callable[..., Any]) -> bool:
    """Check if a function has been decorated with @finops_prompt."""
    return hasattr(func, '_finops_prompt')


def as_prompt_function(func: Callable[..., Any]) -> PromptFunction:
    """Cast a function to PromptFunction type for type checking."""
    return cast(PromptFunction, func)
