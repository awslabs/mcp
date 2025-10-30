"""Validation utilities for MCP tool evaluation.

Provides LLM-as-judge validation and build verification.
"""

import subprocess
import time
from .constants import DEFAULT_MODEL_ID, DEFAULT_TEMPERATURE, LLM_JUDGE_VALIDATION_PROMPT
from loguru import logger
from pathlib import Path
from typing import Any, Dict, List, Optional


async def run_build_validation(
    command: str,
    working_dir: Path,
    install_command: Optional[str] = None,
    timeout: int = 120,
) -> Dict[str, Any]:
    """Run build validation by executing a shell command.

    Args:
        command: Build command to execute (e.g., 'npm run build')
        working_dir: Directory to run the command in
        install_command: Optional install command to run first (e.g., 'npm install')
        timeout: Command timeout in seconds

    Returns:
        Dictionary with build result including exit_code, stdout, stderr, and success flag
    """
    # Install dependencies if specified
    if install_command:
        # Check if installation is needed (e.g., node_modules doesn't exist)
        should_install = False
        if 'npm' in install_command and not (working_dir / 'node_modules').exists():
            should_install = True

        if should_install:
            logger.info(f'Running install command: {install_command}')
            try:
                install_result = subprocess.run(
                    install_command.split(),
                    cwd=working_dir,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                if install_result.returncode != 0:
                    logger.error(f'Install failed: {install_result.stderr}')
            except Exception as e:
                logger.error(f'Failed to run install command: {e}')

    # Run build command
    logger.info(f'Running build command: {command}')
    try:
        build_result = subprocess.run(
            command.split(),
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        result = {
            'exit_code': build_result.returncode,
            'stdout': build_result.stdout,
            'stderr': build_result.stderr,
            'success': build_result.returncode == 0,
        }

        if result['success']:
            logger.info('✓ Build succeeded')
        else:
            logger.error(f'✗ Build failed with exit code {build_result.returncode}')

        return result
    except Exception as e:
        logger.error(f'Build validation error: {e}')
        return {'exit_code': -1, 'stdout': '', 'stderr': str(e), 'success': False}


async def validate_with_llm(
    bedrock_client,
    validation_rubric: List[str],
    git_diff: str,
    build_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Use LLM to validate changes against rubric.

    Args:
        bedrock_client: Boto3 Bedrock Runtime client
        validation_rubric: List of validation criteria
        git_diff: Git diff of changes
        build_result: Optional build validation result

    Returns:
        Dictionary with validation results including overall_pass and criteria_results
    """
    logger.info('Running LLM-as-judge validation...')

    if not git_diff.strip():
        logger.warning('No git diff found - no changes were made')
        return {
            'overall_pass': False,
            'error': 'No changes detected',
            'criteria_results': [],
            'git_diff': '',
        }

    rubric_items = '\n'.join(
        [f'{i + 1}. {criterion}' for i, criterion in enumerate(validation_rubric)]
    )

    # Format build result if provided
    build_info = ''
    if build_result:
        if build_result['success']:
            build_info = '\n**Build Validation:**\n✓ Build succeeded (exit code 0)\n'
        else:
            stderr_preview = build_result['stderr'][:500]
            build_info = f'\n**Build Validation:**\n✗ Build FAILED (exit code {build_result["exit_code"]})\n\nBuild errors:\n{stderr_preview}\n'

    prompt = LLM_JUDGE_VALIDATION_PROMPT.format(
        rubric_items=rubric_items,
        build_info=build_info,
        git_diff=git_diff,
        num_criteria=len(validation_rubric),
    )

    try:
        start = time.time()

        response = bedrock_client.converse(
            modelId=DEFAULT_MODEL_ID,
            messages=[{'role': 'user', 'content': [{'text': prompt}]}],
            inferenceConfig={'temperature': DEFAULT_TEMPERATURE},
        )

        elapsed = time.time() - start
        logger.debug(f'LLM validation took {elapsed:.2f}s')

        response_text = response['output']['message']['content'][0]['text']
        logger.debug(f'LLM response:\n{response_text}')

        criteria_results = []
        for line in response_text.strip().split('\n'):
            if not line.strip():
                continue

            if '[PASS]' in line.upper():
                status = 'PASS'
                reasoning = line.split('[PASS]', 1)[1].strip() if '[PASS]' in line else line
            elif '[FAIL]' in line.upper():
                status = 'FAIL'
                reasoning = line.split('[FAIL]', 1)[1].strip() if '[FAIL]' in line else line
            else:
                continue

            if len(criteria_results) < len(validation_rubric):
                criteria_results.append(
                    {
                        'criterion': validation_rubric[len(criteria_results)],
                        'status': status,
                        'reasoning': reasoning,
                    }
                )

        overall_pass = all(r['status'] == 'PASS' for r in criteria_results)

        return {
            'overall_pass': overall_pass,
            'criteria_results': criteria_results,
            'raw_response': response_text,
            'git_diff': git_diff,
        }
    except Exception as e:
        logger.error(f'LLM validation failed: {e}')
        return {
            'overall_pass': False,
            'error': f'Validation error: {str(e)}',
            'criteria_results': [],
            'git_diff': git_diff,
        }
