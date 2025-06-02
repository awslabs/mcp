"""Test fixtures for the cost-explorer-mcp-server tests."""

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_context():
    """Create a mock MCP context for testing."""
    context = MagicMock()
    return context


@pytest.fixture
def sample_cost_explorer_response():
    """Create a sample AWS Cost Explorer API response."""
    return {
        "GroupDefinitions": [{"Type": "DIMENSION", "Key": "SERVICE"}],
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2025-05-01", "End": "2025-06-01"},
                "Total": {},
                "Groups": [
                    {
                        "Keys": ["Amazon Elastic Compute Cloud - Compute"],
                        "Metrics": {
                            "UnblendedCost": {"Amount": "100.0", "Unit": "USD"}
                        },
                    },
                    {
                        "Keys": ["Amazon Simple Storage Service"],
                        "Metrics": {"UnblendedCost": {"Amount": "50.0", "Unit": "USD"}},
                    },
                    {
                        "Keys": ["Amazon Relational Database Service"],
                        "Metrics": {
                            "UnblendedCost": {"Amount": "200.0", "Unit": "USD"}
                        },
                    },
                ],
            }
        ],
    }


@pytest.fixture
def sample_dimension_values_response():
    """Create a sample AWS Cost Explorer dimension values response."""
    return {
        "DimensionValues": [
            {"Value": "Amazon Elastic Compute Cloud - Compute", "Attributes": {}},
            {"Value": "Amazon Simple Storage Service", "Attributes": {}},
            {"Value": "Amazon Relational Database Service", "Attributes": {}},
            {"Value": "AWS Lambda", "Attributes": {}},
            {"Value": "Amazon DynamoDB", "Attributes": {}},
        ],
        "ReturnSize": 5,
        "TotalSize": 5,
    }


@pytest.fixture
def sample_tag_values_response():
    """Create a sample AWS Cost Explorer tag values response."""
    return {"Tags": ["dev", "prod", "test", "staging"], "ReturnSize": 4, "TotalSize": 4}


@pytest.fixture
def sample_usage_quantity_response():
    """Create a sample AWS Cost Explorer usage quantity response."""
    return {
        "GroupDefinitions": [{"Type": "DIMENSION", "Key": "SERVICE"}],
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2025-05-01", "End": "2025-06-01"},
                "Total": {},
                "Groups": [
                    {
                        "Keys": ["Amazon Elastic Compute Cloud - Compute"],
                        "Metrics": {
                            "UsageQuantity": {"Amount": "730.0", "Unit": "Hrs"}
                        },
                    },
                    {
                        "Keys": ["Amazon Simple Storage Service"],
                        "Metrics": {
                            "UsageQuantity": {"Amount": "1024.0", "Unit": "GB"}
                        },
                    },
                ],
            }
        ],
    }
