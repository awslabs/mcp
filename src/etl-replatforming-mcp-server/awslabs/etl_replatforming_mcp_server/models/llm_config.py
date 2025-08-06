#!/usr/bin/env python3

from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class LLMProvider(Enum):
    ANTHROPIC_CLAUDE_3_SONNET = "anthropic.claude-3-sonnet-20240229-v1:0"
    ANTHROPIC_CLAUDE_3_HAIKU = "anthropic.claude-3-haiku-20240307-v1:0"
    ANTHROPIC_CLAUDE_3_OPUS = "anthropic.claude-3-opus-20240229-v1:0"
    ANTHROPIC_CLAUDE_3_5_SONNET = "anthropic.claude-3-5-sonnet-20240620-v1:0"


@dataclass
class LLMConfig:
    """Configuration for LLM model and parameters"""
    
    model_id: str = LLMProvider.ANTHROPIC_CLAUDE_3_SONNET.value
    max_tokens: int = 4000
    temperature: float = 0.1
    top_p: float = 0.9
    region: str = "us-east-1"
    
    # Additional model-specific parameters
    extra_params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.extra_params is None:
            self.extra_params = {}
    
    @classmethod
    def get_default_config(cls) -> 'LLMConfig':
        """Get default LLM configuration"""
        return cls()
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'LLMConfig':
        """Create LLMConfig from dictionary"""
        return cls(
            model_id=config_dict.get('model_id', LLMProvider.ANTHROPIC_CLAUDE_3_SONNET.value),
            max_tokens=config_dict.get('max_tokens', 4000),
            temperature=config_dict.get('temperature', 0.1),
            top_p=config_dict.get('top_p', 0.9),
            region=config_dict.get('region', 'us-east-1'),
            extra_params=config_dict.get('extra_params', {})
        )