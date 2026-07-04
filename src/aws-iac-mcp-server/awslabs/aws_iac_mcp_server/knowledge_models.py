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

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class KnowledgeResult:
    """Represents a single knowledge search result.

    The AWS Knowledge MCP endpoint returns two shapes in the same result list:
    - Document results carry a `url` pointing at the doc page.
    - Skill results carry no `url`; their content is a skill descriptor.

    `url` is therefore optional so both shapes can be represented.
    """

    rank: int
    title: str
    context: str
    url: Optional[str] = None


@dataclass
class CDKToolResponse:
    """Response from CDK tools containing knowledge and guidance."""

    knowledge_response: List[KnowledgeResult]
    next_step_guidance: Optional[str]
