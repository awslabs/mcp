"""Command-line interface for DynamoDB MCP evaluation system."""

import argparse
import json
import os
import sys
import time
from logging_config import get_logger, setup_evaluation_logging
from multiturn_evaluator import EnhancedMultiTurnEvaluator as MCPToolTester
from scenarios import BASIC_SCENARIOS, get_scenario_by_name
from typing import Any, Dict, Optional


# Initialize logger for this module
logger = get_logger(__name__)


ENHANCED_EVALUATION_AVAILABLE = True

# Set AWS defaults
if not os.environ.get('AWS_DEFAULT_REGION'):
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

DEFAULT_MODEL = 'bedrock/us.anthropic.claude-sonnet-4-20250514-v1:0'


def run_evaluation(
    model_name: str = None,
    scenario_name: str = None,
    aws_profile: str = 'bedrock',
) -> Dict[str, Any]:
    """Run DynamoDB MCP evaluation with specified model and scenario."""
    aws_available = (
        (
            os.getenv('AWS_ACCESS_KEY_ID') is not None
            and os.getenv('AWS_SECRET_ACCESS_KEY') is not None
        )
        or os.getenv('AWS_PROFILE') is not None
        or aws_profile is not None
    )

    original_profile = os.environ.get('AWS_PROFILE')
    if aws_profile and not os.environ.get('AWS_PROFILE'):
        os.environ['AWS_PROFILE'] = aws_profile

    if not aws_available:
        return {
            'status': 'skipped',
            'message': 'AWS credentials not available - set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY or AWS_PROFILE',
            'timestamp': time.time(),
            'evaluation_type': 'enhanced' if ENHANCED_EVALUATION_AVAILABLE else 'basic',
        }

    try:
        selected_model = model_name or DEFAULT_MODEL
        selected_scenario = scenario_name or 'Simple E-commerce Schema'

        tester = MCPToolTester(selected_model)
        scenario = get_scenario_by_name(selected_scenario)
        results = tester.evaluate_scenarios(scenario)

        return results

    except Exception as e:
        logger.error(f'❌ Enhanced evaluation failed: {e}')
        import traceback

        traceback.print_exc()

        return {
            'status': 'error',
            'message': str(e),
            'timestamp': time.time(),
            'model_used': model_name or DEFAULT_MODEL,
            'scenario_used': scenario_name or 'Simple E-commerce Schema',
            'evaluation_type': 'enhanced' if ENHANCED_EVALUATION_AVAILABLE else 'basic',
        }
    finally:
        if aws_profile and not original_profile:
            os.environ.pop('AWS_PROFILE', None)
        elif original_profile:
            os.environ['AWS_PROFILE'] = original_profile


def sanitize_model_input(model_input: str) -> Optional[str]:
    """Sanitize and validate model input parameter."""
    if not model_input or not model_input.strip():
        return None

    # Clean whitespace
    cleaned = model_input.strip()

    # Basic validation - must contain some expected patterns for Bedrock models
    if any(
        pattern in cleaned.lower()
        for pattern in ['bedrock/', 'anthropic', 'claude', 'titan', 'cohere', 'ai21']
    ):
        return cleaned

    # If it doesn't match expected patterns, still return it but warn
    logger.warning(f"⚠️  Warning: Model '{cleaned}' doesn't match expected Bedrock format")
    return cleaned


def sanitize_scenario_input(scenario_input: str) -> Optional[str]:
    """Sanitize and validate scenario input parameter."""
    if not scenario_input or not scenario_input.strip():
        return None

    # Clean whitespace
    cleaned = scenario_input.strip()

    # Check if it matches any available scenario exactly
    available_scenarios = [s['name'] for s in BASIC_SCENARIOS]
    if cleaned in available_scenarios:
        return cleaned

    # Case-insensitive match
    for scenario_name in available_scenarios:
        if cleaned.lower() == scenario_name.lower():
            return scenario_name

    # If no match found, log error with suggestions
    logger.error(f"❌ Error: Scenario '{cleaned}' not found.")
    logger.info('Available scenarios:')
    for scenario in BASIC_SCENARIOS:
        logger.info(f'  • {scenario["name"]} ({scenario["complexity"]})')
    return None


def list_available_scenarios():
    """List all available evaluation scenarios."""
    print('Available Evaluation Scenarios:')
    print('=' * 40)
    for scenario in BASIC_SCENARIOS:
        print(f'📋 {scenario["name"]}')
        print(f'   Complexity: {scenario["complexity"]}')
        print(f'   Description: {scenario["description"]}')
        print()


def display_evaluation_results(result: Dict[str, Any], debug) -> None:
    """Display separate requirement and model evaluation results."""
    print('\n' + '=' * 60)
    print('COMPREHENSIVE EVALUATION RESULTS')
    print('=' * 60)

    if debug:
        print('Full Evaluation Result:')
        print(json.dumps(result, indent=4, sort_keys=False))

    if result.get('status') != 'success':
        print(f'❌ Evaluation Status: {result.get("status")}')
        print(f'📄 Message: {result.get("message", "Unknown error")}')
        return

    # Performance Summary
    perf = result.get('performance_metadata', {})
    total_duration = perf.get('total_duration', 0)
    conv_duration = perf.get('conversation_duration', 0)
    requirement_duration = perf.get('requirement_evaluation_duration', 0)
    model_duration = perf.get('model_evaluation_duration', 0)

    print(f'⏱️  Total Duration: {total_duration:.2f}s')
    print(f'   • Conversation: {conv_duration:.2f}s')
    print(f'   • Requirement Evaluation: {requirement_duration:.2f}s')
    print(f'   • Model Evaluation: {model_duration:.2f}s')
    print()

    # Requirements Evaluation Results
    requirements_eval = result.get('requirement_evaluation')
    if requirements_eval:
        print('📋 REQUIREMENTS EVALUATION (Requirements & Methodology)')
        print('-' * 50)
        requirements_scores = requirements_eval
        overall_requirements = requirements_eval.get('overall_score', 0)
        requirement_quality = requirements_eval.get('quality_level', 'unknown')

        print(f'🎯 Overall Requirements Score: {overall_requirements:.2f} ({requirement_quality})')
        print()
        print('📊 Detailed Requirements Scores:')
        print(
            f'   • Requirements Engineering: {requirements_scores.get("requirements_engineering", 0):.1f}/10'
        )
        print(
            f'   • Access Pattern Analysis: {requirements_scores.get("access_pattern_analysis", 0):.1f}/10'
        )
        print(
            f'   • Methodology Adherence: {requirements_scores.get("methodology_adherence", 0):.1f}/10'
        )
        print(
            f'   • Technical Reasoning: {requirements_scores.get("technical_reasoning", 0):.1f}/10'
        )
        print(
            f'   • Process Documentation: {requirements_scores.get("process_documentation", 0):.1f}/10'
        )
        print()
    else:
        print('⚠️  Requirements evaluation not available')
        print()

    # Model Evaluation Results
    model_eval = result.get('model_evaluation')
    if model_eval:
        print('🏗️  MODEL EVALUATION (Technical Design)')
        print('-' * 50)
        model_scores = model_eval
        overall_model = model_eval.get('overall_score', 0)
        model_quality = model_eval.get('quality_level', 'unknown')

        print(f'🎯 Overall Model Score: {overall_model:.2f} ({model_quality})')
        print()
        print('📊 Detailed Model Scores:')
        print(f'   • Completeness: {model_scores.get("completeness", 0):.1f}/10')
        print(f'   • Technical Accuracy: {model_scores.get("technical_accuracy", 0):.1f}/10')
        print(
            f'   • Access Pattern Coverage: {model_scores.get("access_pattern_coverage", 0):.1f}/10'
        )
        print(
            f'   • Scalability Considerations: {model_scores.get("scalability_considerations", 0):.1f}/10'
        )
        print(f'   • Cost Optimization: {model_scores.get("cost_optimization", 0):.1f}/10')
        print()
    else:
        print('⚠️  Model evaluation not available')
        print()

    # Quality Assessment Summary
    quality_assessment = result.get('quality_assessment', {})
    requirement_quality = quality_assessment.get('requirement_quality_level', 'unknown')
    model_quality = quality_assessment.get('model_quality_level', 'unknown')

    print('🎖️  QUALITY SUMMARY')
    print('-' * 50)
    print(f'Requirement Quality: {requirement_quality}')
    print(f'Model Quality: {model_quality}')
    print()

    # Show timestamp
    timestamp = result.get('timestamp', 'unknown')
    print(f'📅 Evaluation Timestamp: {timestamp}')


if __name__ == '__main__':
    """Enhanced command line interface for DynamoDB MCP evaluation."""

    parser = argparse.ArgumentParser(
        description='Enhanced DynamoDB MCP evaluation with comprehensive DSPy assessment',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_dspy_evals.py
    # Run with default model and scenario

  python test_dspy_evals.py --model "bedrock/us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    # Run with specific model

  python test_dspy_evals.py --scenario "High-Scale Social Media Platform"
    # Run with specific scenario

  python test_dspy_evals.py --model "bedrock/us.anthropic.claude-3-5-sonnet-20241022-v2:0" --scenario "Content Management System"
    # Run with both custom model and scenario

  python test_dspy_evals.py --list-scenarios
    # Show all available scenarios
        """,
    )

    parser.add_argument(
        '--model',
        type=str,
        help=f'Bedrock model ID to use for evaluation (default: {DEFAULT_MODEL})',
    )

    parser.add_argument(
        '--scenario',
        type=str,
        help="Evaluation scenario to test (default: 'Simple E-commerce Schema'). Use --list-scenarios to see options",
    )

    parser.add_argument(
        '--list-scenarios',
        action='store_true',
        help='List all available evaluation scenarios and exit',
    )

    parser.add_argument('--debug', action='store_true', help='Show raw JSON output for debugging')

    parser.add_argument(
        '--aws-profile',
        type=str,
        default='bedrock',
        help='AWS profile to use for evaluation (default: bedrock)',
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level (default: INFO)',
    )

    args = parser.parse_args()

    # Setup logging based on CLI arguments
    setup_evaluation_logging(level=args.log_level)

    # Handle list scenarios request
    if args.list_scenarios:
        list_available_scenarios()
        sys.exit(0)

    # Sanitize inputs with fallback to defaults
    model_name = sanitize_model_input(args.model) or DEFAULT_MODEL
    scenario_name = sanitize_scenario_input(args.scenario) or 'Simple E-commerce Schema'

    # If scenario validation failed, exit
    if args.scenario and not sanitize_scenario_input(args.scenario):
        sys.exit(1)

    # Show evaluation configuration
    print('🔧 EVALUATION CONFIGURATION')
    print('=' * 30)
    print(f'Model: {model_name}')
    print(f'Scenario: {scenario_name}')
    print()

    # Run evaluation
    result = run_evaluation(model_name, scenario_name, aws_profile=args.aws_profile)

    # Show raw JSON for debugging if requested
    if args.debug:
        print('\n' + '=' * 60)
        print('RAW JSON OUTPUT (DEBUG)')
        display_evaluation_results(result, debug=True)
        print('=' * 60)
    else:
        display_evaluation_results(result, debug=False)
