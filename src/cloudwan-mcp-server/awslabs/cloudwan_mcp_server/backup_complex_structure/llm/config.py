"""
LLM Configuration for CloudWAN MCP Server.

This module defines configuration options for LLM integration across
network analysis and validation tools.
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers for validation."""
    NONE = "none"                    # No LLM validation
    AMAZON_Q_DEV_CLI = "amazon_q"    # Amazon Q Developer CLI
    OLLAMA = "ollama"                # Local Ollama deployment
    LLAMA_CPP = "llama_cpp"          # Local llama.cpp deployment
    AMAZON_BEDROCK = "bedrock"       # AWS Bedrock


@dataclass
class LLMConfig:
    """Configuration for LLM integration."""
    
    provider: LLMProvider = LLMProvider.NONE
    
    # Amazon Q Developer CLI settings
    amazon_q_cli_path: Optional[str] = None
    amazon_q_timeout: int = 30
    
    # Ollama settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:latest"
    ollama_timeout: int = 60
    
    # llama.cpp settings
    llama_cpp_model_path: Optional[str] = None
    llama_cpp_binary_path: Optional[str] = None
    llama_cpp_context_size: int = 4096
    llama_cpp_threads: int = 4
    
    # Amazon Bedrock settings
    bedrock_region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    bedrock_max_tokens: int = 4000
    bedrock_temperature: float = 0.1
    
    # General settings
    validation_enabled: bool = True
    fallback_to_heuristics: bool = True
    cache_llm_responses: bool = True
    cache_ttl_minutes: int = 60
    max_retries: int = 3
    
    # Tool-specific settings
    firewall_validation_enabled: bool = True
    core_network_validation_enabled: bool = True
    nfg_validation_enabled: bool = True
    connectivity_validation_enabled: bool = True
    
    def __post_init__(self):
        """Validate configuration and set defaults."""
        if self.provider == LLMProvider.AMAZON_Q_DEV_CLI:
            if not self.amazon_q_cli_path:
                self.amazon_q_cli_path = self._find_amazon_q_cli()
                
        elif self.provider == LLMProvider.LLAMA_CPP:
            if not self.llama_cpp_binary_path:
                self.llama_cpp_binary_path = self._find_llama_cpp_binary()
                
        # Auto-detect available providers if none specified
        if self.provider == LLMProvider.NONE and self.validation_enabled:
            self.provider = self._auto_detect_provider()
    
    def _find_amazon_q_cli(self) -> Optional[str]:
        """Auto-detect Amazon Q Developer CLI installation."""
        possible_paths = [
            "/usr/local/bin/q",
            "/opt/homebrew/bin/q",
            os.path.expanduser("~/.local/bin/q"),
            "q"  # In PATH
        ]
        
        import shutil
        for path in possible_paths:
            if shutil.which(path):
                logger.info(f"Found Amazon Q CLI at: {path}")
                return path
        
        logger.warning("Amazon Q CLI not found in standard locations")
        return None
    
    def _find_llama_cpp_binary(self) -> Optional[str]:
        """Auto-detect llama.cpp binary installation."""
        possible_names = ["llama-cpp-server", "llama.cpp", "main"]
        
        import shutil
        for name in possible_names:
            if shutil.which(name):
                logger.info(f"Found llama.cpp binary: {name}")
                return name
        
        # Check common installation directories
        possible_paths = [
            "/usr/local/bin/llama-cpp-server",
            "/opt/homebrew/bin/llama-cpp-server",
            os.path.expanduser("~/llama.cpp/main"),
            os.path.expanduser("~/llama.cpp/llama-cpp-server")
        ]
        
        for path in possible_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                logger.info(f"Found llama.cpp at: {path}")
                return path
        
        logger.warning("llama.cpp binary not found")
        return None
    
    def _auto_detect_provider(self) -> LLMProvider:
        """Auto-detect the best available LLM provider."""
        
        # Check Amazon Q CLI first (lowest latency for AWS environments)
        if self._find_amazon_q_cli():
            logger.info("Auto-detected Amazon Q CLI")
            return LLMProvider.AMAZON_Q_DEV_CLI
        
        # Check Ollama availability
        try:
            import requests
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                logger.info("Auto-detected Ollama")
                return LLMProvider.OLLAMA
        except Exception:
            pass
        
        # Check llama.cpp
        if self._find_llama_cpp_binary():
            logger.info("Auto-detected llama.cpp")
            return LLMProvider.LLAMA_CPP
        
        # Check Bedrock credentials
        try:
            import boto3
            session = boto3.Session()
            session.client('bedrock-runtime', region_name=self.bedrock_region)
            logger.info("Auto-detected Amazon Bedrock")
            return LLMProvider.AMAZON_BEDROCK
        except Exception:
            pass
        
        logger.warning("No LLM provider auto-detected, validation disabled")
        return LLMProvider.NONE
    
    def is_provider_available(self) -> bool:
        """Check if the configured provider is available."""
        try:
            if self.provider == LLMProvider.NONE:
                return True
            elif self.provider == LLMProvider.AMAZON_Q_DEV_CLI:
                return self.amazon_q_cli_path is not None
            elif self.provider == LLMProvider.OLLAMA:
                import requests
                response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
                return response.status_code == 200
            elif self.provider == LLMProvider.LLAMA_CPP:
                return self.llama_cpp_binary_path is not None
            elif self.provider == LLMProvider.AMAZON_BEDROCK:
                import boto3
                session = boto3.Session()
                session.client('bedrock-runtime', region_name=self.bedrock_region)
                return True
        except Exception as e:
            logger.error(f"Provider availability check failed: {e}")
            return False
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'LLMConfig':
        """Create LLMConfig from configuration dictionary."""
        
        # Map provider string to enum
        provider_str = config_dict.get('provider', 'none')
        try:
            provider = LLMProvider(provider_str.lower())
        except ValueError:
            logger.warning(f"Unknown LLM provider: {provider_str}, using NONE")
            provider = LLMProvider.NONE
        
        return cls(
            provider=provider,
            
            # Amazon Q settings
            amazon_q_cli_path=config_dict.get('amazon_q_cli_path'),
            amazon_q_timeout=config_dict.get('amazon_q_timeout', 30),
            
            # Ollama settings
            ollama_base_url=config_dict.get('ollama_base_url', 'http://localhost:11434'),
            ollama_model=config_dict.get('ollama_model', 'llama3.2:latest'),
            ollama_timeout=config_dict.get('ollama_timeout', 60),
            
            # llama.cpp settings
            llama_cpp_model_path=config_dict.get('llama_cpp_model_path'),
            llama_cpp_binary_path=config_dict.get('llama_cpp_binary_path'),
            llama_cpp_context_size=config_dict.get('llama_cpp_context_size', 4096),
            llama_cpp_threads=config_dict.get('llama_cpp_threads', 4),
            
            # Bedrock settings
            bedrock_region=config_dict.get('bedrock_region', 'us-east-1'),
            bedrock_model_id=config_dict.get('bedrock_model_id', 'anthropic.claude-3-5-sonnet-20241022-v2:0'),
            bedrock_max_tokens=config_dict.get('bedrock_max_tokens', 4000),
            bedrock_temperature=config_dict.get('bedrock_temperature', 0.1),
            
            # General settings
            validation_enabled=config_dict.get('validation_enabled', True),
            fallback_to_heuristics=config_dict.get('fallback_to_heuristics', True),
            cache_llm_responses=config_dict.get('cache_llm_responses', True),
            cache_ttl_minutes=config_dict.get('cache_ttl_minutes', 60),
            max_retries=config_dict.get('max_retries', 3),
            
            # Tool-specific settings
            firewall_validation_enabled=config_dict.get('firewall_validation_enabled', True),
            core_network_validation_enabled=config_dict.get('core_network_validation_enabled', True),
            nfg_validation_enabled=config_dict.get('nfg_validation_enabled', True),
            connectivity_validation_enabled=config_dict.get('connectivity_validation_enabled', True),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert LLMConfig to dictionary for serialization."""
        return {
            'provider': self.provider.value,
            
            # Amazon Q settings
            'amazon_q_cli_path': self.amazon_q_cli_path,
            'amazon_q_timeout': self.amazon_q_timeout,
            
            # Ollama settings
            'ollama_base_url': self.ollama_base_url,
            'ollama_model': self.ollama_model,
            'ollama_timeout': self.ollama_timeout,
            
            # llama.cpp settings
            'llama_cpp_model_path': self.llama_cpp_model_path,
            'llama_cpp_binary_path': self.llama_cpp_binary_path,
            'llama_cpp_context_size': self.llama_cpp_context_size,
            'llama_cpp_threads': self.llama_cpp_threads,
            
            # Bedrock settings
            'bedrock_region': self.bedrock_region,
            'bedrock_model_id': self.bedrock_model_id,
            'bedrock_max_tokens': self.bedrock_max_tokens,
            'bedrock_temperature': self.bedrock_temperature,
            
            # General settings
            'validation_enabled': self.validation_enabled,
            'fallback_to_heuristics': self.fallback_to_heuristics,
            'cache_llm_responses': self.cache_llm_responses,
            'cache_ttl_minutes': self.cache_ttl_minutes,
            'max_retries': self.max_retries,
            
            # Tool-specific settings
            'firewall_validation_enabled': self.firewall_validation_enabled,
            'core_network_validation_enabled': self.core_network_validation_enabled,
            'nfg_validation_enabled': self.nfg_validation_enabled,
            'connectivity_validation_enabled': self.connectivity_validation_enabled,
        }