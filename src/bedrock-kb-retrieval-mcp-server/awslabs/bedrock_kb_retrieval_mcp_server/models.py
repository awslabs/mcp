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
from typing import Dict, List, TypeAlias, TypedDict


class DataSource(TypedDict):
    """A data source for a knowledge base."""

    id: str
    name: str


class KnowledgeBase(TypedDict):
    """A knowledge base."""

    name: str
    data_sources: List[DataSource]


KnowledgeBaseMapping: TypeAlias = Dict[str, KnowledgeBase]
