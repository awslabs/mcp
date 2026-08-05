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

"""Shared fixtures and sample data for all test files.

Run all tests: uv run python -m pytest tests/ -v
"""

import awslabs.roda_mcp_server.server as server_module
import pytest
from awslabs.roda_mcp_server.knowledge_base import DatasetKnowledgeBase
from unittest.mock import AsyncMock, patch


# Sample datasets used across multiple test files.
# Covers different orgs, tags, licenses, and access types.
SAMPLE_DATASETS = [
    {
        'Slug': 'nasa-nex',
        'Name': 'NASA NEX Climate Data',
        'Description': 'NASA Earth Exchange downscaled climate projections for impact assessment',
        'ManagedBy': '[NASA](https://www.nasa.gov/)',
        'License': 'Creative Commons Attribution 4.0',
        'Tags': ['climate', 'earth observation', 'satellite'],
        'Resources': [{'Type': 'S3 Bucket', 'ARN': 'arn:aws:s3:::nasanex', 'Region': 'us-west-2'}],
        'Documentation': 'https://example.com/docs',
    },
    {
        'Slug': 'noaa-ghcn',
        'Name': 'NOAA Global Historical Climatology Network',
        'Description': 'Daily climate summaries from land surface stations worldwide',
        'ManagedBy': '[NOAA](https://www.noaa.gov/)',
        'License': 'Public Domain',
        'Tags': ['climate', 'weather', 'historical'],
        'Resources': [
            {
                'Type': 'S3 Bucket',
                'ARN': 'arn:aws:s3:::noaa-ghcn',
                'Region': 'us-east-1',
            }
        ],
        'Documentation': 'https://example.com/noaa',
    },
    {
        'Slug': 'genomics-data',
        'Name': 'Human Genome Reference',
        'Description': 'Complete human genome sequencing reference data',
        'ManagedBy': '[NIH](https://www.nih.gov/)',
        'License': 'MIT License',
        'Tags': ['genomics', 'health', 'biology'],
        'Resources': [
            {'Type': 'S3 Bucket', 'ARN': 'arn:aws:s3:::genomics', 'Region': 'us-east-1'}
        ],
    },
    {
        'Slug': 'landsat-8',
        'Name': 'Landsat 8 Imagery',
        'Description': 'Satellite imagery from the Landsat 8 mission',
        'ManagedBy': '[NASA](https://www.nasa.gov/)',
        'License': 'Public Domain',
        'Tags': ['satellite', 'earth observation', 'imagery'],
        'Resources': [
            {
                'Type': 'S3 Bucket',
                'ARN': 'arn:aws:s3:::landsat-8',
                'Region': 'us-west-2',
            }
        ],
    },
]


@pytest.fixture
def sample_datasets():
    """Provide sample datasets to tests that need them."""
    return SAMPLE_DATASETS


@pytest.fixture
def setup_server(sample_datasets):
    """Pre-populate the server cache and knowledge base with sample data."""
    server_module._datasets_cache = sample_datasets
    server_module._knowledge_base = DatasetKnowledgeBase()
    server_module._knowledge_base.build_indexes(sample_datasets)
    yield
    server_module._datasets_cache = None
    server_module._cache_timestamp = None


@pytest.fixture
def patch_fetch(sample_datasets):
    """Mock fetch_datasets to return sample data without network calls."""
    with patch('awslabs.roda_mcp_server.server.fetch_datasets', new_callable=AsyncMock) as mock:
        mock.return_value = sample_datasets
        yield mock
