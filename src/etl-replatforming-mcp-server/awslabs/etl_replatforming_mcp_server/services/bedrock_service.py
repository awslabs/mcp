#!/usr/bin/env python3

import json
import boto3
import os
from typing import Dict, Any, Optional
from loguru import logger
from ..models.llm_config import LLMConfig


class BedrockService:
    """Service for intelligent parsing using AWS Bedrock"""
    
    def __init__(self, llm_config: Optional[LLMConfig] = None):
        self.config = llm_config or LLMConfig.get_default_config()
        self.client = self._create_client()
    
    def _create_client(self):
        """Create Bedrock client with credential fallback logic"""
        try:
            # Try default credential chain first
            client = boto3.client('bedrock-runtime', region_name=self.config.region)
            # Test if credentials work
            sts = boto3.client('sts', region_name=self.config.region)
            sts.get_caller_identity()
            return client
        except Exception as e:
            if 'ExpiredToken' in str(e):
                logger.info("Environment credentials expired, trying AWS profile...")
                # Fall back to profile-based session
                profile_name = os.environ.get('AWS_PROFILE')
                if profile_name:
                    session = boto3.Session(profile_name=profile_name)
                    return session.client('bedrock-runtime', region_name=self.config.region)
            raise e
    
    def enhance_flex_workflow(self, incomplete_workflow: Dict[str, Any], input_code: str, source_framework: str, custom_config: Optional[Dict[str, Any]] = None, target_framework: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Use Bedrock to intelligently fill missing FLEX workflow elements"""
        
        # Use custom config if provided
        config = self.config
        if custom_config:
            config = LLMConfig.from_dict({**self.config.__dict__, **custom_config})
        
        prompt = self._build_enhancement_prompt(incomplete_workflow, input_code, source_framework, target_framework)
        
        try:
            response = self._invoke_bedrock(prompt, config)
            enhanced_workflow = self._parse_bedrock_response(response)
            return enhanced_workflow
        except Exception as e:
            logger.warning(f"Bedrock enhancement failed: {str(e)}")
            return None
    
    def _build_enhancement_prompt(self, incomplete_workflow: Dict[str, Any], input_code: str, source_framework: str, target_framework: Optional[str] = None) -> str:
        """Build prompt for Bedrock to enhance incomplete workflow"""
        
        target_context = ""
        if target_framework:
            target_context = f"""

Target Framework: {target_framework}
When generating task types, use appropriate types for {target_framework}:
- For Airflow: Use operator names like "PostgreSQLOperator", "PythonOperator", "BashOperator"
- For Step Functions: Use resource types like "lambda_invoke", "redshift_query", "batch_job"
- For Azure Data Factory: Use activity types like "Copy", "SqlServerStoredProcedure", "HDInsightHive"
"""
        
        return f"""You are an expert ETL workflow analyst. Analyze the following {source_framework} code and enhance the incomplete FLEX workflow.

Original {source_framework} Code:
```
{input_code[:2000]}
```

Incomplete FLEX Workflow:
```json
{json.dumps(incomplete_workflow, indent=2)}
```{target_context}

Your task:
1. Analyze the original code to extract missing information
2. Fill in missing fields in the FLEX workflow
3. Infer reasonable defaults for unclear elements
4. Use appropriate task types for the target framework if specified
5. Return ONLY a valid JSON object with the enhanced FLEX workflow

Focus on:
- Missing task commands/scripts
- Incomplete schedule expressions
- Missing task dependencies
- Appropriate task types for target framework
- Missing error handling

Return the enhanced FLEX workflow as valid JSON:"""

    def _invoke_bedrock(self, prompt: str, config: LLMConfig) -> str:
        """Invoke Bedrock model with the prompt"""
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        # Add any extra parameters
        body.update(config.extra_params)
        
        response = self.client.invoke_model(
            modelId=config.model_id,
            body=json.dumps(body)
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
    
    def _parse_bedrock_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse Bedrock response to extract enhanced workflow"""
        
        try:
            # Extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start == -1 or end == 0:
                return None
                
            json_str = response[start:end]
            workflow = json.loads(json_str)
            
            # Validate dependencies structure
            if 'dependencies' in workflow:
                valid_deps = []
                for dep in workflow['dependencies']:
                    if isinstance(dep, dict) and 'upstream_task' in dep and 'downstream_task' in dep:
                        valid_deps.append(dep)
                    else:
                        logger.warning(f"Skipping invalid dependency: {dep}")
                workflow['dependencies'] = valid_deps
            
            return workflow
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse Bedrock response: {str(e)}")
            return None