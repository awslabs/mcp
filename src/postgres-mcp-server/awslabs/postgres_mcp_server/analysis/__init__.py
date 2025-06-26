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

"""Analysis tools package for PostgreSQL MCP Server."""

from .structure import analyze_database_structure
from .performance import analyze_query_performance
from .indexes import recommend_indexes
from .fragmentation import analyze_table_fragmentation
from .vacuum import analyze_vacuum_stats
from .slow_queries import identify_slow_queries
from .settings import show_postgresql_settings
from .schema import get_table_schema

__all__ = [
    'analyze_database_structure',
    'analyze_query_performance', 
    'recommend_indexes',
    'analyze_table_fragmentation',
    'analyze_vacuum_stats',
    'identify_slow_queries',
    'show_postgresql_settings',
    'get_table_schema'
]
