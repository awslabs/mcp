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

"""AWS S3 Tables MCP Server file processing module.

This module provides functionality for processing and analyzing uploaded files,
particularly focusing on CSV and Parquet file handling and import capabilities.
"""

from .csv import import_csv_to_table
from .parquet import import_parquet_to_table

__all__ = ['import_csv_to_table', 'import_parquet_to_table']
