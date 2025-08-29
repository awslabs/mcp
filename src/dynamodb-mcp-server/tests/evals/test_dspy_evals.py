"""Command-line interface for comprehensive DynamoDB MCP evaluation system.

This module provides a feature-rich CLI for executing end-to-end evaluation of
DynamoDB data modeling guidance quality. It orchestrates the complete evaluation
pipeline from conversational testing through sophisticated quality assessment,
offering both automated benchmarking and detailed analysis capabilities.

System Overview:
    The CLI serves as the primary interface to a comprehensive evaluation ecosystem
    that combines multiple sophisticated technologies:

    1. **Conversational Testing** (Strands + MCP):
       - Realistic user-expert interactions via Strands agents
       - Native MCP integration for authentic DynamoDB tool access
       - Multi-turn conversation simulation with structured scenarios

    2. **Quality Assessment** (DSPy + Expert Knowledge):
       - Dual-pathway evaluation: process quality + design quality
       - Expert knowledge-informed scoring using DSPy signatures
       - 10-dimensional assessment covering methodology and technical excellence

    3. **Performance Benchmarking**:
       - Detailed timing analysis across evaluation pipeline stages
       - Quality level classification with actionable feedback
       - Comprehensive result reporting and analysis

Key Features:
    - **Flexible Model Support**: Works with any Bedrock-compatible model
    - **Scenario-Based Testing**: Multiple predefined scenarios with varied complexity
    - **Comprehensive Reporting**: Separate session and design quality assessments
    - **Performance Monitoring**: Detailed timing and efficiency metrics
    - **Robust Error Handling**: Graceful degradation with meaningful error messages
    - **Development Integration**: Debug mode for detailed pipeline inspection

CLI Capabilities:
    - Default evaluation with optimized model and scenario selection
    - Custom model specification for comparative analysis
    - Scenario selection from predefined complexity levels
    - Scenario listing for evaluation planning
    - Debug output for development and troubleshooting

Usage Patterns:
    # Quick evaluation with defaults
    python test_dspy_evals.py

    # Custom model evaluation
    python test_dspy_evals.py --model "bedrock/claude-3-5-sonnet-20241022-v2:0"

    # Specific scenario testing
    python test_dspy_evals.py --scenario "High-Scale Social Media Platform"

    # Combined custom configuration
    python test_dspy_evals.py --model "custom-model" --scenario "Content Management System"

"""

import argparse
import json
import os
import sys
import time
from multiturn_evaluator import EnhancedMultiTurnEvaluator as MCPToolTester
from scenarios import BASIC_SCENARIOS, get_scenario_by_name
from typing import Any, Dict, Optional


ENHANCED_EVALUATION_AVAILABLE = True

# Set AWS defaults
if not os.environ.get('AWS_DEFAULT_REGION'):
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

DEFAULT_MODEL = 'bedrock/us.anthropic.claude-sonnet-4-20250514-v1:0'


def run_evaluation(
    model_name: str = None,
    scenario_name: str = None,
    verbose: bool = True,
    aws_profile: str = 'Bedrock',
) -> Dict[str, Any]:
    """Primary evaluation orchestrator for comprehensive DynamoDB MCP assessment.

    This function coordinates the complete evaluation pipeline from AWS credential
    validation through conversational testing to sophisticated quality assessment.
    It serves as the main entry point for both CLI and programmatic evaluation usage.

    Args:
        model_name (str, optional): Bedrock model identifier for evaluation.
                                  If None, uses DEFAULT_MODEL for optimal performance.
        scenario_name (str, optional): Evaluation scenario name from BASIC_SCENARIOS.
                                     If None, uses "Simple E-commerce Schema".
        verbose (bool, optional): Enable detailed progress output and error reporting.
                                 Default True for CLI usage, False for programmatic use.
        aws_profile (str, optional): AWS profile name for Bedrock access.
                                   Default 'Bedrock' for model evaluation.

    Returns:
        Dict[str, Any]: Comprehensive evaluation results including:
            - status: "success", "error", or "skipped"
            - session_evaluation: Process quality assessment (if successful)
            - model_evaluation: Design quality assessment (if successful)
            - performance_metadata: Timing breakdown and efficiency metrics
            - quality_assessment: Categorical quality level classifications
            - conversation: Complete conversational exchange data
            - timestamp: ISO timestamp for result tracking

    Evaluation Pipeline:
        1. **Credential Validation**: Verify AWS access for Bedrock and MCP services
        2. **Configuration Setup**: Initialize model and scenario with defaults
        3. **Evaluator Initialization**: Create MCPToolTester with Strands+DSPy integration
        4. **Scenario Loading**: Retrieve structured scenario from predefined set
        5. **Conversation Execution**: Run multi-turn Strands conversation with MCP tools
        6. **Quality Assessment**: Execute dual DSPy evaluation (session + model)
        7. **Result Aggregation**: Combine all results with performance metadata

    Error Handling:
        - AWS Credential Issues: Returns structured skip result with setup guidance
        - Model Configuration Errors: Captures and reports model availability issues
        - Scenario Resolution Failures: Reports invalid scenario names with suggestions
        - Pipeline Execution Errors: Provides detailed error context for debugging
        - Graceful Degradation: Always returns structured result for consistent handling

    Performance Characteristics:
        - Credential check: <100ms (environment variable access)
        - Configuration setup: <1s (object initialization)
        - Conversation phase: 30-60s (Bedrock model dependent)
        - DSPy evaluation: 20-40s (dual pathway assessment)
        - Total pipeline: 50-120s for complete assessment

    Integration Points:
        - AWS credentials via environment variables or AWS_PROFILE
        - Bedrock model access through boto3 with retry configuration
        - MCP server connection via stdio for DynamoDB expert tools
        - DSPy evaluation engine with expert knowledge integration
        - Structured scenario definitions from scenarios.py

    Usage Examples:
        # Default evaluation
        result = run_evaluation()

        # Custom model testing
        result = run_evaluation("bedrock/claude-3-5-sonnet-20241022-v2:0")

        # Specific scenario assessment
        result = run_evaluation(scenario_name="High-Scale Social Media Platform")

        # Silent programmatic usage
        result = run_evaluation(verbose=False)
    """
    # Step 1: Validate AWS credentials for Bedrock and MCP access
    # Both direct credentials and AWS profile configurations are supported
    aws_available = (
        (
            os.getenv('AWS_ACCESS_KEY_ID') is not None
            and os.getenv('AWS_SECRET_ACCESS_KEY') is not None
        )
        or os.getenv('AWS_PROFILE') is not None
        or aws_profile is not None
    )

    # Set AWS profile temporarily if provided
    original_profile = os.environ.get('AWS_PROFILE')
    if aws_profile and not os.environ.get('AWS_PROFILE'):
        os.environ['AWS_PROFILE'] = aws_profile

    # Return structured skip result if credentials unavailable
    if not aws_available:
        return {
            'status': 'skipped',
            'message': 'AWS credentials not available - set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY or AWS_PROFILE',
            'timestamp': time.time(),
            'evaluation_type': 'enhanced' if ENHANCED_EVALUATION_AVAILABLE else 'basic',
        }

    try:
        # Step 2: Configure evaluation parameters with intelligent defaults
        selected_model = model_name or DEFAULT_MODEL  # Optimized Claude 4 Sonnet
        selected_scenario = (
            scenario_name or 'Simple E-commerce Schema'
        )  # Beginner-friendly default

        # Step 3: Initialize the comprehensive evaluation system
        # MCPToolTester orchestrates Strands agents, MCP protocol, and DSPy evaluation
        tester = MCPToolTester(selected_model)

        # Step 4: Load structured scenario with complete requirements specification
        scenario = get_scenario_by_name(selected_scenario)

        # Provide progress feedback for CLI usage
        if verbose:
            print(f'🎯 Testing scenario complexity: {scenario.get("complexity", "unknown")}')

        # Step 5: Execute the complete evaluation pipeline
        # This includes conversation, content extraction, and dual DSPy evaluation
        results = tester.evaluate_scenarios(scenario)

        return results

    except Exception as e:
        # Comprehensive error handling with detailed context for debugging
        if verbose:
            print(f'❌ Enhanced evaluation failed: {e}')
            import traceback

            traceback.print_exc()

        # Return structured error result maintaining consistent interface
        return {
            'status': 'error',
            'message': str(e),
            'timestamp': time.time(),
            'model_used': model_name or DEFAULT_MODEL,
            'scenario_used': scenario_name or 'Simple E-commerce Schema',
            'evaluation_type': 'enhanced' if ENHANCED_EVALUATION_AVAILABLE else 'basic',
        }
    finally:
        # Restore original AWS profile
        if aws_profile and not original_profile:
            os.environ.pop('AWS_PROFILE', None)
        elif original_profile:
            os.environ['AWS_PROFILE'] = original_profile


def sanitize_model_input(model_input: str) -> Optional[str]:
    """Sanitize and validate model input parameter.

    Args:
        model_input: Raw model input string

    Returns:
        Cleaned model string or None if empty/invalid
    """
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
    print(f"⚠️  Warning: Model '{cleaned}' doesn't match expected Bedrock format")
    return cleaned


def sanitize_scenario_input(scenario_input: str) -> Optional[str]:
    """Sanitize and validate scenario input parameter.

    Args:
        scenario_input: Raw scenario input string

    Returns:
        Valid scenario name or None if empty/invalid
    """
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

    # If no match found, raise error with suggestions
    print(f"❌ Error: Scenario '{cleaned}' not found.")
    print('Available scenarios:')
    for scenario in BASIC_SCENARIOS:
        print(f'  • {scenario["name"]} ({scenario["complexity"]})')
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


def run_basic_evaluation(model_name: str = None) -> Dict[str, Any]:
    """Run basic DynamoDB MCP evaluation (backward compatibility).

    Args:
        model_name: Bedrock model ID to use. If None, uses DEFAULT_MODEL

    Returns:
        Dictionary containing evaluation results
    """
    return run_evaluation(model_name, verbose=False)


def display_evaluation_results(result: Dict[str, Any], debug) -> None:
    """Display separate session and model evaluation results."""
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
    session_duration = perf.get('session_evaluation_duration', 0)
    model_duration = perf.get('model_evaluation_duration', 0)

    print(f'⏱️  Total Duration: {total_duration:.2f}s')
    print(f'   • Conversation: {conv_duration:.2f}s')
    print(f'   • Session Evaluation: {session_duration:.2f}s')
    print(f'   • Model Evaluation: {model_duration:.2f}s')
    print()

    # Session Evaluation Results
    session_eval = result.get('session_evaluation')
    if session_eval:
        print('📋 SESSION EVALUATION (Requirements & Methodology)')
        print('-' * 50)
        session_scores = session_eval.get('scores', {})
        overall_session = session_eval.get('overall_score', 0)
        session_quality = session_eval.get('quality_level', 'unknown')

        print(f'🎯 Overall Session Score: {overall_session:.2f} ({session_quality})')
        print()
        print('📊 Detailed Session Scores:')
        print(
            f'   • Requirements Engineering: {session_scores.get("requirements_engineering", 0):.1f}/10'
        )
        print(
            f'   • Access Pattern Analysis: {session_scores.get("access_pattern_analysis", 0):.1f}/10'
        )
        print(
            f'   • Methodology Adherence: {session_scores.get("methodology_adherence", 0):.1f}/10'
        )
        print(f'   • Technical Reasoning: {session_scores.get("technical_reasoning", 0):.1f}/10')
        print(
            f'   • Process Documentation: {session_scores.get("process_documentation", 0):.1f}/10'
        )
        print()
    else:
        print('⚠️  Session evaluation not available')
        print()

    # Model Evaluation Results
    model_eval = result.get('model_evaluation')
    if model_eval:
        print('🏗️  MODEL EVALUATION (Technical Design)')
        print('-' * 50)
        model_scores = model_eval.get('scores', {})
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
    session_quality = quality_assessment.get('session_quality_level', 'unknown')
    model_quality = quality_assessment.get('model_quality_level', 'unknown')

    print('🎖️  QUALITY SUMMARY')
    print('-' * 50)
    print(f'Session Quality: {session_quality}')
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
        default='Bedrock',
        help='AWS profile to use for evaluation (default: Bedrock)',
    )

    args = parser.parse_args()

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
