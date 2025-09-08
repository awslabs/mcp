"""Multi-turn conversation evaluator using Strands agents."""

import ast
import asyncio
import dspy
import json
import os
import time
from botocore.config import Config as BotocoreConfig
from dataclasses import dataclass
from dynamic_evaluators import dynamic_engine
from logging_config import get_logger
from mcp import StdioServerParameters, stdio_client
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from typing import Any, Dict, List, Optional


# Initialize logger for this module
logger = get_logger(__name__)


@dataclass
class ConversationTurn:
    """Single turn in a multi-turn conversation."""

    role: str
    content: str
    turn_number: int
    timestamp: float


@dataclass
class ConversationResult:
    """Container for conversation evaluation results."""

    turns: List[ConversationTurn]


def _to_text(x) -> str:
    """Extract text from varied Strands agent response formats."""
    if isinstance(x, str):
        return x

    for attr in ('message', 'text', 'content'):
        v = getattr(x, attr, None)
        if isinstance(v, str):
            return v

    try:
        return str(x)
    except Exception:
        return ''


def extract_requirements_guidance_sections(final_guidance):
    """Extract DynamoDB modeling requirement and data model sections from agent response."""
    try:
        response_data = ast.literal_eval(final_guidance)
        markdown_content = response_data['content'][0]['text']
        markdown_content = markdown_content.replace('\\n', '\n')
        markdown_blocks = markdown_content.split('```markdown\n')

        if len(markdown_blocks) < 3:
            logger.error('Error: Expected at least 2 markdown sections')
            return None, None

        dynamodb_modeling_requirement = markdown_blocks[1].split('```')[0].strip()
        dynamodb_data_model = markdown_blocks[2].split('```')[0].strip()
        return dynamodb_modeling_requirement, dynamodb_data_model

    except (ValueError, SyntaxError, KeyError, IndexError) as e:
        logger.error(f'Error parsing guidance: {e}')
        return None, None


class StrandsConversationHandler:
    """Handles conversational interactions using Strands agents with MCP tools."""

    def __init__(self, model_id: str = ''):
        """Initialize with Bedrock model configuration."""
        normalized = model_id
        if normalized.startswith('bedrock/'):
            normalized = normalized.split('/', 1)[1]
        self.model_id = normalized
        boto_config = BotocoreConfig(
            retries={'max_attempts': 3, 'mode': 'standard'}, connect_timeout=5, read_timeout=3600
        )
        self.bedrock_model = BedrockModel(
            model_id=self.model_id,
            temperature=0.3,
            streaming=False,
            boto_client_config=boto_config,
        )

    def _setup_mcp_client(self):
        """Set up the DynamoDB MCP client."""
        return MCPClient(
            lambda: stdio_client(
                StdioServerParameters(
                    command='uvx',
                    args=['awslabs.dynamodb-mcp-server@latest'],
                )
            )
        )

    def _build_scenario(self, scenario: Dict[str, Any]) -> str:
        # Convert scenario to clean JSON representation
        scenario_json = json.dumps(scenario, indent=2)

        # Simple message with minimal formatting
        message = f"""Here are my complete requirements:

        {scenario_json}

        INSTRUCTIONS:
        Provide complete DynamoDB guidance now. Output exactly two blocks:
        1) ```markdown
        # DynamoDB Modeling Requirement (dynamodb_requirement.md)
        ...content...
        ```
        2) ```markdown
        # DynamoDB Data Model (dynamodb_data_model.md)
        ...content...
        ```

        Do not ask additional questions - provide complete guidance now."""

        return message

    async def simulate_conversation(
        self, scenario: Dict[str, Any]
    ) -> tuple[str, List[ConversationTurn]]:
        """Simulate a 2-turn conversation using Strands agent with MCP integration.

        Returns:
            tuple: (final_guidance, conversation_turns)
        """
        conversation = []

        try:
            # Set up MCP client for DynamoDB expert system
            dynamodb_mcp_client = self._setup_mcp_client()

            with dynamodb_mcp_client:
                # Get available tools from MCP server
                tools = dynamodb_mcp_client.list_tools_sync()

                # Create Strands agent with DynamoDB MCP tools
                agent = Agent(model=self.bedrock_model, tools=tools)

                # Turn 1: Initial engagement
                turn1_message = 'I need help designing a DynamoDB schema. Can you help me understand your approach?'

                conversation.append(
                    ConversationTurn(
                        role='user', content=turn1_message, turn_number=1, timestamp=time.time()
                    )
                )

                turn1_response = agent(turn1_message)
                turn1_text = _to_text(turn1_response)

                conversation.append(
                    ConversationTurn(
                        role='assistant', content=turn1_text, turn_number=2, timestamp=time.time()
                    )
                )

                # Turn 2: Simplified scenario with structured data
                comprehensive_message = self._build_scenario(scenario)

                conversation.append(
                    ConversationTurn(
                        role='user',
                        content=comprehensive_message,
                        turn_number=3,
                        timestamp=time.time(),
                    )
                )

                turn2_response = agent(comprehensive_message).message

                conversation.append(
                    ConversationTurn(
                        role='assistant',
                        content=_to_text(turn2_response),
                        turn_number=4,
                        timestamp=time.time(),
                    )
                )

                return _to_text(turn2_response), conversation

        except Exception as e:
            logger.error(f'❌ Error during Strands conversation: {e}')
            import traceback

            traceback.print_exc()
            return f'Error during conversation: {str(e)}', conversation


@dataclass
class ComprehensiveEvaluationResult:
    """Enhanced result structure with complete evaluation data."""

    # Content sections
    modeling_requirement: str
    data_model: str
    conversation: List[ConversationTurn]

    # Separate evaluation results - now using dynamic objects
    requirement_evaluation: Optional[Any] = None
    model_evaluation: Optional[Any] = None

    # Performance metadata
    conversation_duration: float = 0.0
    requirement_evaluation_duration: float = 0.0
    model_evaluation_duration: float = 0.0
    timestamp: str = ''

    # Separate quality assessments
    requirement_quality_level: str = 'unknown'
    model_quality_level: str = 'unknown'


class EnhancedMultiTurnEvaluator:
    """Enhanced evaluator combining conversation collection with DSPy evaluation."""

    def __init__(self, lm_model: str = ''):
        """Initialize the enhanced multi-turn evaluator."""
        try:
            # Use Strands for conversation handling
            self.conversation_handler = StrandsConversationHandler(lm_model)

            # Initialize evaluation components - use direct engine
            self.dspy_engine = dynamic_engine
            if not os.environ.get('AWS_DEFAULT_REGION'):
                os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

            # Ensure DSPy uses the same model as Strands
            dspy_model = lm_model
            if not dspy_model.startswith('bedrock/'):
                dspy_model = f'bedrock/{dspy_model}'

            dspy.configure(lm=dspy.LM(dspy_model, max_tokens=8192, temperature=0.1))

        except Exception as e:
            logger.warning(f'Warning: Could not configure EnhancedMultiTurnEvaluator: {e}')

    async def evaluate_with_conversation(
        self, scenario: Dict[str, Any]
    ) -> Optional[ComprehensiveEvaluationResult]:
        """Enhanced evaluation with comprehensive DSPy scoring and analysis."""
        start_time = time.time()

        try:
            # Step 1: Run conversation collection
            print(f'🔄 Running conversation for scenario: {scenario.get("name", "Unknown")}')
            conversation_start = time.time()

            final_guidance, conversation = await self.conversation_handler.simulate_conversation(
                scenario
            )
            conversation_duration = time.time() - conversation_start
            dynamodb_modeling_requirements, dynamodb_data_model_guidance = (
                extract_requirements_guidance_sections(final_guidance)
            )

            # Step 2: Run comprehensive evaluations if available
            requirement_evaluation_result = None
            model_evaluation_result = None
            requirement_eval_duration = 0.0
            model_eval_duration = 0.0

            if dynamodb_modeling_requirements and dynamodb_data_model_guidance:
                # Run Requirement evaluation
                print('🔄 Running DSPy evaluation on requirement')
                requirement_eval_start = time.time()

                requirement_evaluation_result = self.dspy_engine.evaluate(
                    'requirement_evaluation', scenario, dynamodb_modeling_requirements
                )
                requirement_eval_duration = time.time() - requirement_eval_start

                # Run model evaluation
                print('🔄 Running DSPy evaluation on data model')
                model_eval_start = time.time()

                model_evaluation_result = self.dspy_engine.evaluate(
                    'model_evaluation', scenario, dynamodb_data_model_guidance
                )
                model_eval_duration = time.time() - model_eval_start

            # Step 3: Create comprehensive result with separate evaluations
            result = ComprehensiveEvaluationResult(
                modeling_requirement=dynamodb_modeling_requirements or '',
                data_model=dynamodb_data_model_guidance or '',
                conversation=conversation,
                requirement_evaluation=requirement_evaluation_result,
                model_evaluation=model_evaluation_result,
                conversation_duration=conversation_duration,
                requirement_evaluation_duration=requirement_eval_duration,
                model_evaluation_duration=model_eval_duration,
                timestamp=self._get_timestamp(),
                requirement_quality_level=requirement_evaluation_result.quality_level
                if requirement_evaluation_result
                else 'unknown',
                model_quality_level=model_evaluation_result.quality_level
                if model_evaluation_result
                else 'unknown',
            )

            total_duration = time.time() - start_time
            print(f'🎯 Complete evaluation finished in {total_duration:.2f}s')

            return result

        except Exception as e:
            logger.error(f'❌ Error during enhanced evaluation: {e}')
            import traceback

            traceback.print_exc()
            return None

    def evaluate_scenarios(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate scenario with separate requirement and model assessments."""
        result = asyncio.run(self.evaluate_with_conversation(scenario))

        if not result:
            return {
                'status': 'error',
                'message': 'Evaluation failed',
                'timestamp': self._get_timestamp(),
            }

        return {
            'status': 'success',
            'conversation': [
                {
                    'role': turn.role,
                    'content': turn.content,
                    'turn_number': turn.turn_number,
                    'timestamp': turn.timestamp,
                }
                for turn in result.conversation
            ],
            'modeling_requirement': result.modeling_requirement,
            'data_model': result.data_model,
            'requirement_evaluation': result.requirement_evaluation.to_dict()
            if result.requirement_evaluation
            else None,
            'model_evaluation': result.model_evaluation.to_dict()
            if result.model_evaluation
            else None,
            'quality_assessment': {
                'requirement_quality_level': result.requirement_quality_level,
                'model_quality_level': result.model_quality_level,
            },
            'performance_metadata': {
                'conversation_duration': result.conversation_duration,
                'requirement_evaluation_duration': result.requirement_evaluation_duration,
                'model_evaluation_duration': result.model_evaluation_duration,
                'total_duration': result.conversation_duration
                + result.requirement_evaluation_duration
                + result.model_evaluation_duration,
            },
            'timestamp': result.timestamp,
        }

    def _get_timestamp(self) -> str:
        """Get current timestamp for tracking."""
        import datetime

        return datetime.datetime.now().isoformat()
