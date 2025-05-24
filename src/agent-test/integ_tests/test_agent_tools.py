"""Tests for agent tool correctness using DeepEval."""

import os
import pytest
import sys
from awslabs.agent_test.agent_test_dataset import AgentEvaluationDataset, AgentTestCase
from awslabs.agent_test.agent_tool_test import AgentToolTest
from deepeval import assert_test
from deepeval.metrics.tool_correctness.tool_correctness import ToolCorrectnessMetric
from loguru import logger
from pathlib import Path


# Configure logger to make it visible in pytest output
logger.remove()
logger.add(sys.stderr, level='INFO')


# Get MCP settings from environment or use defaults
MCP_ARGS = ['mcp-server-time', '--local-timezone=US/Pacific']

# Find examples directory relative to this file
THIS_DIR = Path(__file__).parent
ROOT_DIR = THIS_DIR.parent
EXAMPLES_DIR = ROOT_DIR / 'examples'
DEFAULT_TEST_DATASET = str(EXAMPLES_DIR / 'agent_test_cases.yaml')

# Get dataset path from environment or use default
AGENT_TEST_DATASET = os.environ.get('AGENT_TEST_DATASET', DEFAULT_TEST_DATASET)


@pytest.fixture
def agent_test():
    """Create an agent test instance."""
    return AgentToolTest(
        mcp_args=MCP_ARGS,
        mcp_env=None,
        model_id=os.environ.get(
            'AGENT_TEST_MODEL_ID', 'us.anthropic.claude-3-7-sonnet-20250219-v1:0'
        ),
        region_name=os.environ.get('AGENT_TEST_REGION', 'us-west-2'),
    )


@pytest.fixture
def test_dataset():
    """Load or create a test dataset."""
    # Load from file if it exists
    dataset_path = os.environ.get('AGENT_TEST_DATASET', DEFAULT_TEST_DATASET)
    logger.info(f'Looking for test dataset at: {dataset_path}')

    if Path(dataset_path).exists():
        logger.info(f'Found test dataset file at: {dataset_path}')
        if dataset_path.endswith('.yaml') or dataset_path.endswith('.yml'):
            logger.info(f'Loading YAML test dataset from: {dataset_path}')
            dataset = AgentEvaluationDataset.from_yaml(dataset_path)
            logger.info(f'Loaded {len(dataset.test_cases)} test cases:')
            for tc in dataset.test_cases:
                logger.info(f'  - {tc.input} (expects: {tc.expected_tools})')
            return dataset
        elif dataset_path.endswith('.json'):
            logger.info(f'Loading JSON test dataset from: {dataset_path}')
            return AgentEvaluationDataset.from_json(dataset_path)
    else:
        logger.warning(f'Dataset file not found at {dataset_path}, using default test cases')

    # Otherwise use some default test cases with time MCP server tools
    logger.info('Creating default test dataset')
    return AgentEvaluationDataset(
        [
            AgentTestCase(
                input="What's the current time in Tokyo?",
                expected_tools=['get_current_time'],
                description='Testing the get_current_time tool',
            ),
            AgentTestCase(
                input='Convert 3:00 PM Los Angeles time to London time',
                expected_tools=['convert_time'],
                description='Testing time conversion between time zones',
            ),
        ]
    )


@pytest.fixture
def yaml_test_cases():
    """Load test cases from YAML file."""
    logger.info(f'Loading test cases from YAML: {DEFAULT_TEST_DATASET}')
    dataset = AgentEvaluationDataset.from_yaml(DEFAULT_TEST_DATASET)
    logger.info(f'Loaded {len(dataset.test_cases)} test cases from YAML')

    # For this test, let's just use the first two test cases from the file
    test_cases = dataset.test_cases
    for tc in test_cases:
        logger.info(f'Using test case: "{tc.input}" (expects: {tc.expected_tools})')

    return test_cases


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'test_case',
    [
        # We'll keep these hardcoded cases to maintain backward compatibility
        AgentTestCase(
            input="What's the current time in Tokyo?",
            expected_tools=['get_current_time'],
            description='Testing the get_current_time tool',
        ),
        AgentTestCase(
            input='Convert 3:00 PM Los Angeles time to London time',
            expected_tools=['convert_time'],
            description='Testing time conversion between time zones',
        ),
    ],
)
async def test_agent_tool_usage(test_case: AgentTestCase, agent_test: AgentToolTest):
    """Test that the agent uses the expected tools for different queries."""
    async with agent_test:
        # Create DeepEval test case by running the agent
        llm_test_case = await agent_test.create_test_case(
            prompt=test_case.input, expected_tools=test_case.expected_tools
        )

        # Define metrics - we use the tool correctness metric
        tool_metric = ToolCorrectnessMetric()

        # Assert using DeepEval's assertion utility
        assert_test(llm_test_case, [tool_metric])


@pytest.mark.asyncio
async def test_yaml_agent_tool_usage(yaml_test_cases, agent_test: AgentToolTest):
    """Test agent tool usage with test cases loaded from YAML file."""
    logger.info(f'Running tests with {len(yaml_test_cases)} test cases from YAML')

    for test_case in yaml_test_cases:
        logger.info(f'Testing case: {test_case.input}')
        async with agent_test:
            # Create DeepEval test case by running the agent
            llm_test_case = await agent_test.create_test_case(
                prompt=test_case.input, expected_tools=test_case.expected_tools
            )

            # Define metrics - we use the tool correctness metric
            tool_metric = ToolCorrectnessMetric()

            # Assert using DeepEval's assertion utility
            assert_test(llm_test_case, [tool_metric])

        logger.info(f'Test passed for: {test_case.input}')

    logger.info('All YAML-based tests passed')
