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
particularly focusing on CSV file handling and import capabilities.
"""

import pyarrow.csv as pc
from .utils import import_file_to_table


async def import_csv_to_table(
    warehouse: str,
    region: str,
    namespace: str,
    table_name: str,
    s3_url: str,
    uri: str,
    catalog_name: str = 's3tablescatalog',
    rest_signing_name: str = 's3tables',
    rest_sigv4_enabled: str = 'true',
    preserve_case: bool = False,
):
    """Import a CSV file into an S3 table using PyArrow."""
    return await import_file_to_table(
        warehouse=warehouse,
        region=region,
        namespace=namespace,
        table_name=table_name,
        s3_url=s3_url,
        uri=uri,
        create_pyarrow_table=pc.read_csv,
        catalog_name=catalog_name,
        rest_signing_name=rest_signing_name,
        rest_sigv4_enabled=rest_sigv4_enabled,
        preserve_case=preserve_case,
    )
