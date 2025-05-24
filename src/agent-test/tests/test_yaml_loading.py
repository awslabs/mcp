"""Tests for YAML loading in agent test dataset."""

import sys
from awslabs.agent_test.agent_test_dataset import AgentEvaluationDataset
from loguru import logger
from pathlib import Path


# Configure logger to make it visible in pytest output
logger.remove()
logger.add(sys.stderr, level='INFO')


# Find examples directory relative to this file
THIS_DIR = Path(__file__).parent
ROOT_DIR = THIS_DIR.parent
EXAMPLES_DIR = ROOT_DIR / 'examples'
DEFAULT_TEST_DATASET = str(EXAMPLES_DIR / 'agent_test_cases.yaml')


def test_yaml_file_exists():
    """Test that the YAML file exists."""
    logger.info(f'Checking if file exists: {DEFAULT_TEST_DATASET}')
    assert Path(DEFAULT_TEST_DATASET).exists()
    logger.info('YAML file exists')


def test_yaml_loading():
    """Test that the YAML file can be loaded."""
    logger.info(f'Loading YAML file: {DEFAULT_TEST_DATASET}')
    dataset = AgentEvaluationDataset.from_yaml(DEFAULT_TEST_DATASET)
    logger.info(f'Loaded {len(dataset.test_cases)} test cases')

    # Verify we have the expected test cases
    assert len(dataset.test_cases) == 5

    # Log all test cases
    for tc in dataset.test_cases:
        logger.info(f'Test case: {tc.input} (expects: {tc.expected_tools})')

    # Verify specific test case content
    assert dataset.test_cases[0].input == "What's the current time in Tokyo?"
    assert dataset.test_cases[0].expected_tools == ['get_current_time']

    assert (
        dataset.test_cases[2].input
        == "When it's 3:00 PM in Los Angeles, what time is it in London?"
    )
    assert dataset.test_cases[2].expected_tools == ['convert_time']
