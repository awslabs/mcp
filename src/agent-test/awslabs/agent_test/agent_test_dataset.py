"""Dataset utilities for agent testing.

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""

import json
import yaml
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class AgentTestCase:
    """Test case for agent tool testing."""

    input: str
    expected_tools: List[str]
    description: Optional[str] = None


class AgentEvaluationDataset:
    """Dataset for agent evaluation."""

    def __init__(self, test_cases: List[AgentTestCase]):
        """Initialize with a list of test cases."""
        self.test_cases = test_cases

    def __iter__(self):
        """Make the dataset iterable for pytest parametrization."""
        for test_case in self.test_cases:
            yield test_case

    @classmethod
    def from_yaml(cls, path: str) -> 'AgentEvaluationDataset':
        """Load test cases from a YAML file.

        Expected format:
        ```yaml
        - input: "What's the weather in Seattle?"
          expected_tools: ["get_weather"]
          description: "Weather query test"
        ```
        """
        with open(path, 'r') as f:
            data = yaml.safe_load(f)

        test_cases = [AgentTestCase(**item) for item in data]
        return cls(test_cases)

    @classmethod
    def from_json(cls, path: str) -> 'AgentEvaluationDataset':
        """Load test cases from a JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)

        test_cases = [AgentTestCase(**item) for item in data]
        return cls(test_cases)
