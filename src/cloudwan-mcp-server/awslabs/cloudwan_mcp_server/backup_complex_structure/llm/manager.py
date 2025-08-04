"""
LLM Manager for CloudWAN MCP Server.

This module provides the central management interface for LLM providers,
handling requests, caching, and fallback logic for network analysis validation.
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Tuple
import aiohttp
import boto3
from botocore.exceptions import ClientError

from .config import LLMConfig, LLMProvider

logger = logging.getLogger(__name__)


class LLMValidationError(Exception):
    """Exception raised when LLM validation fails."""
    pass


class LLMManager:
    """Central manager for LLM validation across CloudWAN tools."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.LLMManager")
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._bedrock_client = None
        
        # Initialize provider-specific clients
        if config.provider == LLMProvider.AMAZON_BEDROCK:
            self._initialize_bedrock()
    
    def _initialize_bedrock(self):
        """Initialize Amazon Bedrock client."""
        try:
            self._bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=self.config.bedrock_region
            )
            self.logger.info("Bedrock client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Bedrock client: {e}")
            raise
    
    def _get_cache_key(self, prompt: str, context: Dict[str, Any]) -> str:
        """Generate cache key for LLM request."""
        content = json.dumps({'prompt': prompt, 'context': context}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _is_cache_valid(self, timestamp: datetime) -> bool:
        """Check if cached response is still valid."""
        ttl = timedelta(minutes=self.config.cache_ttl_minutes)
        return datetime.now() - timestamp < ttl
    
    async def validate_with_llm(
        self,
        validation_type: str,
        prompt: str,
        context: Dict[str, Any],
        structured_output: bool = True
    ) -> Dict[str, Any]:
        """
        Validate network configuration using configured LLM provider.
        
        Args:
            validation_type: Type of validation (firewall, core_network, nfg, connectivity)
            prompt: Validation prompt for the LLM
            context: Context data for validation
            structured_output: Whether to expect structured JSON response
            
        Returns:
            Validation result dictionary
        """
        
        if not self.config.validation_enabled:
            return self._heuristic_fallback(validation_type, context)
        
        # Check cache first
        if self.config.cache_llm_responses:
            cache_key = self._get_cache_key(prompt, context)
            if cache_key in self._cache:
                result, timestamp = self._cache[cache_key]
                if self._is_cache_valid(timestamp):
                    self.logger.debug(f"Cache hit for {validation_type} validation")
                    return result
        
        # Try validation with configured provider
        for attempt in range(self.config.max_retries):
            try:
                result = await self._call_llm_provider(prompt, context, structured_output)
                
                # Cache successful result
                if self.config.cache_llm_responses:
                    self._cache[cache_key] = (result, datetime.now())
                
                return result
                
            except Exception as e:
                self.logger.warning(f"LLM validation attempt {attempt + 1} failed: {e}")
                if attempt == self.config.max_retries - 1:
                    if self.config.fallback_to_heuristics:
                        self.logger.info(f"Falling back to heuristic validation for {validation_type}")
                        return self._heuristic_fallback(validation_type, context)
                    else:
                        raise LLMValidationError(f"LLM validation failed after {self.config.max_retries} attempts")
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
    
    async def _call_llm_provider(
        self,
        prompt: str,
        context: Dict[str, Any],
        structured_output: bool
    ) -> Dict[str, Any]:
        """Call the configured LLM provider."""
        
        if self.config.provider == LLMProvider.AMAZON_Q_DEV_CLI:
            return await self._call_amazon_q_cli(prompt, context, structured_output)
        elif self.config.provider == LLMProvider.OLLAMA:
            return await self._call_ollama(prompt, context, structured_output)
        elif self.config.provider == LLMProvider.LLAMA_CPP:
            return await self._call_llama_cpp(prompt, context, structured_output)
        elif self.config.provider == LLMProvider.AMAZON_BEDROCK:
            return await self._call_bedrock(prompt, context, structured_output)
        else:
            raise LLMValidationError(f"Unsupported LLM provider: {self.config.provider}")
    
    async def _call_amazon_q_cli(
        self,
        prompt: str,
        context: Dict[str, Any],
        structured_output: bool
    ) -> Dict[str, Any]:
        """Call Amazon Q Developer CLI for validation."""
        
        if not self.config.amazon_q_cli_path:
            raise LLMValidationError("Amazon Q CLI path not configured")
        
        # Prepare the command
        cmd = [
            self.config.amazon_q_cli_path,
            "ask",
            "--no-interactive",
            "--format", "json" if structured_output else "text"
        ]
        
        # Combine prompt and context
        full_prompt = f"{prompt}\n\nContext:\n{json.dumps(context, indent=2)}"
        
        try:
            # Run Q CLI command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                input=full_prompt.encode(),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                timeout=self.config.amazon_q_timeout
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise LLMValidationError(f"Q CLI failed: {stderr.decode()}")
            
            response = stdout.decode().strip()
            
            if structured_output:
                try:
                    return json.loads(response)
                except json.JSONDecodeError:
                    # If JSON parsing fails, wrap in structure
                    return {"validation_result": response, "provider": "amazon_q"}
            else:
                return {"validation_result": response, "provider": "amazon_q"}
                
        except asyncio.TimeoutError:
            raise LLMValidationError("Amazon Q CLI request timed out")
        except Exception as e:
            raise LLMValidationError(f"Amazon Q CLI error: {e}")
    
    async def _call_ollama(
        self,
        prompt: str,
        context: Dict[str, Any],
        structured_output: bool
    ) -> Dict[str, Any]:
        """Call Ollama for validation."""
        
        # Prepare request
        full_prompt = f"{prompt}\n\nContext:\n{json.dumps(context, indent=2)}"
        
        if structured_output:
            full_prompt += "\n\nPlease respond with valid JSON only."
        
        request_data = {
            "model": self.config.ollama_model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 1000
            }
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.ollama_timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.config.ollama_base_url}/api/generate",
                    json=request_data
                ) as response:
                    if response.status != 200:
                        raise LLMValidationError(f"Ollama API error: {response.status}")
                    
                    result = await response.json()
                    response_text = result.get('response', '').strip()
                    
                    if structured_output:
                        try:
                            return json.loads(response_text)
                        except json.JSONDecodeError:
                            return {"validation_result": response_text, "provider": "ollama"}
                    else:
                        return {"validation_result": response_text, "provider": "ollama"}
                        
        except asyncio.TimeoutError:
            raise LLMValidationError("Ollama request timed out")
        except Exception as e:
            raise LLMValidationError(f"Ollama error: {e}")
    
    async def _call_llama_cpp(
        self,
        prompt: str,
        context: Dict[str, Any],
        structured_output: bool
    ) -> Dict[str, Any]:
        """Call llama.cpp for validation."""
        
        if not self.config.llama_cpp_model_path or not self.config.llama_cpp_binary_path:
            raise LLMValidationError("llama.cpp model or binary path not configured")
        
        # Prepare command
        full_prompt = f"{prompt}\n\nContext:\n{json.dumps(context, indent=2)}"
        
        if structured_output:
            full_prompt += "\n\nPlease respond with valid JSON only."
        
        cmd = [
            self.config.llama_cpp_binary_path,
            "-m", self.config.llama_cpp_model_path,
            "-c", str(self.config.llama_cpp_context_size),
            "-t", str(self.config.llama_cpp_threads),
            "-p", full_prompt,
            "--no-display-prompt"
        ]
        
        try:
            # Run llama.cpp
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                timeout=120  # 2 minute timeout for local inference
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise LLMValidationError(f"llama.cpp failed: {stderr.decode()}")
            
            response = stdout.decode().strip()
            
            if structured_output:
                try:
                    return json.loads(response)
                except json.JSONDecodeError:
                    return {"validation_result": response, "provider": "llama_cpp"}
            else:
                return {"validation_result": response, "provider": "llama_cpp"}
                
        except asyncio.TimeoutError:
            raise LLMValidationError("llama.cpp inference timed out")
        except Exception as e:
            raise LLMValidationError(f"llama.cpp error: {e}")
    
    async def _call_bedrock(
        self,
        prompt: str,
        context: Dict[str, Any],
        structured_output: bool
    ) -> Dict[str, Any]:
        """Call Amazon Bedrock for validation."""
        
        if not self._bedrock_client:
            raise LLMValidationError("Bedrock client not initialized")
        
        # Prepare request
        full_prompt = f"{prompt}\n\nContext:\n{json.dumps(context, indent=2)}"
        
        if structured_output:
            full_prompt += "\n\nPlease respond with valid JSON only."
        
        # Claude-specific message format
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.config.bedrock_max_tokens,
            "temperature": self.config.bedrock_temperature,
            "messages": [
                {
                    "role": "user",
                    "content": full_prompt
                }
            ]
        }
        
        try:
            response = self._bedrock_client.invoke_model(
                modelId=self.config.bedrock_model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            response_text = response_body['content'][0]['text'].strip()
            
            if structured_output:
                try:
                    return json.loads(response_text)
                except json.JSONDecodeError:
                    return {"validation_result": response_text, "provider": "bedrock"}
            else:
                return {"validation_result": response_text, "provider": "bedrock"}
                
        except ClientError as e:
            raise LLMValidationError(f"Bedrock API error: {e}")
        except Exception as e:
            raise LLMValidationError(f"Bedrock error: {e}")
    
    def _heuristic_fallback(self, validation_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Provide heuristic validation when LLM is unavailable."""
        
        self.logger.info(f"Using heuristic fallback for {validation_type} validation")
        
        if validation_type == "firewall":
            return self._firewall_heuristic_validation(context)
        elif validation_type == "core_network":
            return self._core_network_heuristic_validation(context)
        elif validation_type == "nfg":
            return self._nfg_heuristic_validation(context)
        elif validation_type == "connectivity":
            return self._connectivity_heuristic_validation(context)
        else:
            return {
                "validation_result": "heuristic_fallback",
                "confidence": "low",
                "recommendations": ["Consider configuring LLM validation for better analysis"],
                "provider": "heuristic"
            }
    
    def _firewall_heuristic_validation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Heuristic firewall policy validation."""
        
        rules = context.get('rules', [])
        blocking_rules = len([r for r in rules if r.get('action') in ['drop', 'reject']])
        total_rules = len(rules)
        
        if total_rules == 0:
            risk_level = "critical"
            message = "No firewall rules found"
        elif blocking_rules == 0:
            risk_level = "critical"
            message = "No blocking rules found - policy allows all traffic"
        elif blocking_rules < total_rules * 0.1:
            risk_level = "high"
            message = f"Only {blocking_rules}/{total_rules} rules block traffic"
        else:
            risk_level = "medium"
            message = f"Policy has {blocking_rules} blocking rules"
        
        return {
            "validation_result": {
                "risk_level": risk_level,
                "message": message,
                "blocking_rules": blocking_rules,
                "total_rules": total_rules
            },
            "confidence": "medium",
            "provider": "heuristic"
        }
    
    def _core_network_heuristic_validation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Heuristic core network policy validation."""
        
        policy = context.get('policy_document', {})
        segments = policy.get('segments', [])
        segment_actions = policy.get('segment-actions', [])
        
        return {
            "validation_result": {
                "segments_count": len(segments),
                "segment_actions_count": len(segment_actions),
                "has_default_route": any('default-route-table' in str(sa) for sa in segment_actions),
                "validation_status": "basic_structure_valid"
            },
            "confidence": "medium",
            "provider": "heuristic"
        }
    
    def _nfg_heuristic_validation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Heuristic NFG policy validation."""
        
        nfgs = context.get('network_function_groups', [])
        
        return {
            "validation_result": {
                "nfg_count": len(nfgs),
                "has_send_to": any(nfg.get('send_to_targets') for nfg in nfgs),
                "has_send_via": any(nfg.get('send_via_targets') for nfg in nfgs),
                "validation_status": "basic_nfg_config_present"
            },
            "confidence": "medium",
            "provider": "heuristic"
        }
    
    def _connectivity_heuristic_validation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Heuristic connectivity validation."""
        
        source = context.get('source', {})
        destination = context.get('destination', {})
        
        return {
            "validation_result": {
                "source_defined": bool(source),
                "destination_defined": bool(destination),
                "has_route_tables": context.get('route_tables') is not None,
                "has_security_groups": context.get('security_groups') is not None,
                "validation_status": "basic_connectivity_components_present"
            },
            "confidence": "low",
            "provider": "heuristic"
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of configured LLM provider."""
        
        if self.config.provider == LLMProvider.NONE:
            return {"status": "disabled", "provider": "none"}
        
        try:
            test_prompt = "Test connection"
            test_context = {"test": "health_check"}
            
            result = await self._call_llm_provider(test_prompt, test_context, False)
            
            return {
                "status": "healthy",
                "provider": self.config.provider.value,
                "response_received": bool(result)
            }
            
        except Exception as e:
            return {
                "status": "unhealthy", 
                "provider": self.config.provider.value,
                "error": str(e)
            }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        
        if not self.config.cache_llm_responses:
            return {"caching": "disabled"}
        
        total_entries = len(self._cache)
        valid_entries = sum(1 for _, timestamp in self._cache.values() 
                           if self._is_cache_valid(timestamp))
        
        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "expired_entries": total_entries - valid_entries,
            "cache_ttl_minutes": self.config.cache_ttl_minutes
        }