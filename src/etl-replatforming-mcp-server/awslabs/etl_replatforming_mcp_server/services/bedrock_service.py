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

import json
import os
import time
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from loguru import logger

from ..constants import (
    BEDROCK_CONNECT_TIMEOUT,
    BEDROCK_FIELD_TIMEOUT,
    BEDROCK_GENERAL_RETRY_DELAY,
    BEDROCK_READ_TIMEOUT,
    BEDROCK_REQUEST_TIMEOUT,
    BEDROCK_RETRY_BASE_DELAY,
    FIELD_TASK_COMMANDS,
    MAX_BEDROCK_RETRIES,
    MAX_TOKENS_SINGLE_FIELD,
    PARSING_METHOD_AI_ENHANCED,
    TASK_TYPE_FOR_EACH,
)
from ..models.llm_config import LLMConfig
from ..utils.bedrock_helpers import BedrockHelpers


class BedrockService:
    """Service for intelligent parsing using AWS Bedrock"""

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        self.config = llm_config or LLMConfig.get_default_config()
        self.client = self._create_client()

    def _create_client(self):
        """Create Bedrock client with credential fallback logic"""
        # Configure timeouts - reduce to prevent hanging
        config = Config(
            read_timeout=BEDROCK_READ_TIMEOUT,
            connect_timeout=BEDROCK_CONNECT_TIMEOUT,
            retries={'max_attempts': 2},
            max_pool_connections=1,
        )

        try:
            # Try default credential chain first
            client = boto3.client('bedrock-runtime', region_name=self.config.region, config=config)
            # Test if credentials work
            sts = boto3.client('sts', region_name=self.config.region)
            sts.get_caller_identity()
            logger.info(f'AWS credentials found via default chain (region: {self.config.region})')
            return client
        except Exception as e:
            logger.info(f'Default credential chain failed: {str(e)}')

            # Fall back to profile-based session for any credential error
            profile_name = os.environ.get('AWS_PROFILE')
            if profile_name:
                try:
                    logger.info(f'Trying AWS profile: {profile_name}')
                    session = boto3.Session(profile_name=profile_name)
                    client = session.client(
                        'bedrock-runtime', region_name=self.config.region, config=config
                    )
                    # Test profile credentials
                    sts = session.client('sts', region_name=self.config.region)
                    identity = sts.get_caller_identity()
                    logger.info(
                        f"AWS profile '{profile_name}' credentials working (Account: {identity.get('Account', 'unknown')})"
                    )
                    return client
                except Exception as profile_error:
                    logger.warning(f"AWS profile '{profile_name}' failed: {str(profile_error)}")
            else:
                logger.info('No AWS_PROFILE environment variable set')

            # Re-raise original error with helpful context
            raise Exception(
                f'Unable to locate credentials. Original error: {str(e)}. Set AWS_PROFILE environment variable or configure default credentials.'
            ) from e

    def enhance_flex_workflow(
        self,
        incomplete_workflow: Dict[str, Any],
        input_code: str,
        source_framework: str,
        custom_config: Optional[Dict[str, Any]] = None,
        context_document: Optional[str] = None,
        missing_fields: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Use Bedrock to intelligently fill missing FLEX workflow elements"""

        workflow_name = incomplete_workflow.get('name', 'unknown')
        logger.info(
            f'Starting targeted Bedrock enhancement for workflow: {workflow_name} ({source_framework})'
        )

        # Use custom config if provided
        config = self.config
        if custom_config:
            config = LLMConfig.from_dict({**self.config.__dict__, **custom_config})

        # Use provided missing fields or get from parsing info
        if missing_fields is None:
            missing_fields = incomplete_workflow.get('parsing_info', {}).get('missing_fields', [])

        # If no missing fields but parsing is incomplete, add quality improvement fields
        parsing_completeness = incomplete_workflow.get('parsing_info', {}).get(
            'parsing_completeness', 1.0
        )
        if not missing_fields and parsing_completeness < 1.0:
            # AI was triggered for quality issues, not missing mandatory fields
            missing_fields = [FIELD_TASK_COMMANDS]  # Always try to improve task commands
            logger.info(
                f'No mandatory fields missing, but parsing incomplete ({parsing_completeness:.1%}). Targeting quality improvements for {workflow_name}'
            )
        elif not missing_fields:
            logger.info(f'No missing fields identified for {workflow_name}')
            return incomplete_workflow

        logger.info(f'Targeting specific missing fields: {missing_fields}')

        # Extract only missing fields using targeted prompts
        enhancements = self._extract_missing_fields(
            missing_fields, input_code, source_framework, config, context_document
        )

        if not enhancements:
            logger.warning(f'No enhancements extracted for {workflow_name}')
            return incomplete_workflow

        # Merge enhancements into original workflow
        enhanced_workflow = incomplete_workflow.copy()
        confidence_scores = []
        enhancement_list = []

        for field, (value, confidence) in enhancements.items():
            if value:
                if field == 'task_commands':
                    # Handle both task command enhancements and dynamic task creation
                    self._apply_task_command_enhancements(enhanced_workflow, value, confidence)
                    self._apply_dynamic_task_enhancements(enhanced_workflow, value, confidence)
                    enhancement_list.append('Enhanced task commands and dynamic patterns')
                else:
                    enhanced_workflow[field] = value
                    enhancement_list.append(f'Added {field}')

                confidence_scores.append(confidence)
                logger.info(f"Enhanced field '{field}' with confidence {confidence:.2f}")

        # Update parsing info
        if 'parsing_info' not in enhanced_workflow:
            enhanced_workflow['parsing_info'] = {}

        avg_confidence = (
            sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        )
        enhanced_workflow['parsing_info']['llm_confidence'] = avg_confidence
        enhanced_workflow['parsing_info']['parsing_method'] = PARSING_METHOD_AI_ENHANCED
        enhanced_workflow['parsing_info']['llm_enhancements'] = enhancement_list

        logger.info(
            f'Targeted enhancement successful for {workflow_name} (avg confidence: {avg_confidence:.2f})'
        )
        logger.info(f'Enhanced fields: {list(enhancements.keys())}')

        return enhanced_workflow

    def _extract_missing_fields(
        self,
        missing_fields: List[str],
        input_code: str,
        source_framework: str,
        config: LLMConfig,
        context_document: Optional[str] = None,
    ) -> Dict[str, tuple[Any, float]]:
        """Extract specific missing fields using targeted prompts"""
        field_prompts = BedrockHelpers.create_field_prompts(
            source_framework, input_code, context_document
        )

        enhancements = {}

        for field in missing_fields:
            if field not in field_prompts:
                continue

            try:
                logger.info(f'Extracting missing field: {field}')
                prompt = field_prompts[field]
                response = self._invoke_bedrock_with_timeout(prompt, config, field)

                if response:
                    value, confidence = self._parse_field_response(response, field)
                    if value:
                        enhancements[field] = (value, confidence)
                        logger.info(f'Extracted {field} with confidence {confidence:.2f}')
                    else:
                        logger.warning(f'Failed to parse {field} from response')
                else:
                    logger.warning(f'No response for field {field}')

            except Exception as e:
                logger.error(f'Error extracting {field}: {str(e)}')
                continue

        return enhancements

    def _apply_task_command_enhancements(
        self,
        workflow: Dict[str, Any],
        enhancements: Dict[str, Any],
        avg_confidence: float,
    ):
        """Apply AI enhancements to individual task commands"""
        enhanced_tasks = enhancements.get('enhanced_tasks', [])

        for task_enhancement in enhanced_tasks:
            task_id = task_enhancement.get('task_id')
            new_command = task_enhancement.get('command')
            task_confidence = task_enhancement.get('confidence', avg_confidence)

            if not task_id or not new_command:
                continue

            # Skip dynamic tasks - they're handled separately
            if task_enhancement.get('type') == TASK_TYPE_FOR_EACH:
                continue

            # Find and update the task
            for task in workflow.get('tasks', []):
                if task.get('id') == task_id:
                    task['command'] = new_command
                    task['ai_generated'] = True
                    task['ai_confidence'] = task_confidence
                    logger.info(
                        f"Enhanced task '{task_id}' command with confidence {task_confidence:.2f}"
                    )
                    break

    def _apply_dynamic_task_enhancements(
        self,
        workflow: Dict[str, Any],
        enhancements: Dict[str, Any],
        avg_confidence: float,
    ):
        """Apply AI-detected dynamic task creation patterns"""
        enhanced_tasks = enhancements.get('enhanced_tasks', [])

        for task_enhancement in enhanced_tasks:
            if task_enhancement.get('type') != TASK_TYPE_FOR_EACH:
                continue

            task_id = task_enhancement.get('task_id')
            command = task_enhancement.get('command')
            parameters = task_enhancement.get('parameters', {})
            task_confidence = task_enhancement.get('confidence', avg_confidence)

            if not task_id or not command:
                continue

            # Create new for_each task from AI detection
            dynamic_task = {
                'id': task_id,
                'name': 'Dynamic Tasks (AI-detected)',
                'type': TASK_TYPE_FOR_EACH,
                'command': command,
                'parameters': parameters,
                'retries': 0,
                'ai_generated': True,
                'ai_confidence': task_confidence,
                'depends_on': [],
            }

            # Add to workflow tasks
            if 'tasks' not in workflow:
                workflow['tasks'] = []
            workflow['tasks'].append(dynamic_task)

            logger.info(
                f"Added AI-detected dynamic task '{task_id}' with confidence {task_confidence:.2f}"
            )
            logger.info(f'Loop parameters: {parameters}')

    def _invoke_bedrock_with_timeout(
        self, prompt: str, config: LLMConfig, field_name: str
    ) -> Optional[str]:
        """Invoke Bedrock with timeout for specific field extraction"""

        import queue
        import threading

        result_queue = queue.Queue()
        exception_queue = queue.Queue()

        def bedrock_call(result_q=result_queue, exception_q=exception_queue):
            try:
                response = self._invoke_bedrock(prompt, config)
                result_q.put(response)
            except Exception as e:
                exception_q.put(e)

        thread = threading.Thread(target=bedrock_call)
        thread.daemon = True
        thread.start()
        thread.join(timeout=BEDROCK_FIELD_TIMEOUT)

        if thread.is_alive():
            logger.error(
                f'Bedrock request timed out for field {field_name} after {BEDROCK_FIELD_TIMEOUT}s'
            )
            return None

        if not exception_queue.empty():
            e = exception_queue.get()
            logger.error(f'Bedrock error for field {field_name}: {str(e)}')
            return None

        if not result_queue.empty():
            return result_queue.get()

        return None

    def _invoke_bedrock(self, prompt: str, config: LLMConfig) -> str:
        """Invoke Bedrock model with the prompt"""

        # Use inference profiles for newer Claude models
        model_id = BedrockHelpers.get_inference_profile_model_id(config.model_id)
        if model_id != config.model_id:
            logger.info(f'Using inference profile: {model_id}')

        # Log the prompt being sent to Bedrock
        logger.info(f'Bedrock Request - Model: {model_id}')
        logger.info(f'Bedrock Prompt (targeted): {prompt[:300]}...')

        body = {
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': min(config.max_tokens, MAX_TOKENS_SINGLE_FIELD),
            'temperature': config.temperature,
            'top_p': config.top_p,
            'messages': [{'role': 'user', 'content': prompt}],
        }

        # Add any extra parameters
        if config.extra_params:
            body.update(config.extra_params)

        # Retry logic for throttling with timeout
        max_retries = MAX_BEDROCK_RETRIES
        response = None

        for attempt in range(max_retries):
            try:
                logger.info(f'Invoking Bedrock model (attempt {attempt + 1}/{max_retries})...')

                # Use threading-based timeout (more reliable than signals)
                import queue
                import threading

                result_queue = queue.Queue()
                exception_queue = queue.Queue()

                def bedrock_call(result_q=result_queue, exception_q=exception_queue):
                    try:
                        response = self.client.invoke_model(
                            modelId=model_id, body=json.dumps(body)
                        )
                        result_q.put(response)
                    except Exception as e:
                        exception_q.put(e)

                thread = threading.Thread(target=bedrock_call)
                thread.daemon = True
                thread.start()
                thread.join(timeout=BEDROCK_REQUEST_TIMEOUT)

                if thread.is_alive():
                    logger.error(
                        f'Bedrock request timed out after {BEDROCK_REQUEST_TIMEOUT} seconds'
                    )
                    raise TimeoutError(
                        f'Bedrock request timed out after {BEDROCK_REQUEST_TIMEOUT} seconds'
                    )

                if not exception_queue.empty():
                    raise exception_queue.get()

                if not result_queue.empty():
                    response = result_queue.get()
                    logger.info('Bedrock response received successfully')
                    break
                else:
                    raise Exception('No response received from Bedrock')

            except Exception as e:
                error_str = str(e)
                logger.error(f'Bedrock invocation failed (attempt {attempt + 1}): {error_str}')

                if 'ThrottlingException' in error_str and attempt < max_retries - 1:
                    wait_time = (2**attempt) * BEDROCK_RETRY_BASE_DELAY  # Exponential backoff
                    logger.warning(
                        f'Throttling detected, waiting {wait_time}s before retry {attempt + 1}/{max_retries}'
                    )
                    time.sleep(wait_time)
                elif 'TimeoutError' in error_str or 'ReadTimeoutError' in error_str:
                    logger.error('Timeout error - Bedrock request took too long')
                    raise Exception(f'Bedrock request timeout: {error_str}') from None
                elif 'ValidationException' in error_str:
                    logger.error(f'Validation error - check model ID and permissions: {error_str}')
                    raise
                elif attempt < max_retries - 1:
                    logger.warning(f'Retrying after error: {error_str}')
                    time.sleep(BEDROCK_GENERAL_RETRY_DELAY)
                else:
                    raise

        # Check if we got a response after all retries
        if response is None:
            raise Exception('Max retries exceeded for Bedrock invocation')

        # Parse the response
        try:
            response_body = json.loads(response['body'].read())
            response_text = response_body['content'][0]['text']

            # Log the response received from Bedrock
            logger.info(f'Bedrock Response received - Length: {len(response_text)} chars')
            logger.info(f'Bedrock Response (full): {response_text}')

            return response_text
        except Exception as e:
            logger.error(f'Failed to parse Bedrock response: {str(e)}')
            logger.error(f'Raw response: {response if response else "No response"}')
            raise Exception(f'Failed to parse Bedrock response: {str(e)}') from e

    def _parse_field_response(self, response: str, field_name: str) -> tuple[Optional[Any], float]:
        """Parse Bedrock response for specific field"""

        try:
            # Extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1

            if start == -1 or end == 0:
                return None, 0.0

            json_str = response[start:end]
            field_value = json.loads(json_str)

            # Calculate confidence using helper
            confidence = BedrockHelpers.calculate_field_confidence(
                response, field_name, field_value
            )
            return field_value, confidence

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f'Failed to parse {field_name} response: {str(e)}')
            return None, 0.0
