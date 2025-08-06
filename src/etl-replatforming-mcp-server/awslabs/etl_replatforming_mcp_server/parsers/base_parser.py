#!/usr/bin/env python3

from abc import ABC, abstractmethod
from typing import Dict, Any
from ..models.flex_workflow import FlexWorkflow


class WorkflowParser(ABC):
    """Abstract base class for workflow parsers"""
    
    @abstractmethod
    def parse(self, source_data: Dict[str, Any]) -> FlexWorkflow:
        """Parse source data to FLEX workflow format
        
        Args:
            source_data: Framework-specific source data
            
        Returns:
            FlexWorkflow representation
            
        Raises:
            ParsingError: If parsing fails
        """
        pass
    
    @abstractmethod
    def parse_code(self, input_code: str) -> FlexWorkflow:
        """Parse raw input code to FLEX workflow format
        
        Intelligently extracts framework components from raw code/configuration
        and converts to FLEX format, leaving placeholders for missing data.
        
        Args:
            input_code: Raw code/configuration string
            
        Returns:
            FlexWorkflow with parsed information and placeholders
            
        Raises:
            ParsingError: If parsing fails
        """
        pass
    
    @abstractmethod
    def can_parse(self, source_data: Dict[str, Any]) -> bool:
        """Check if this parser can handle the source data
        
        Args:
            source_data: Source data to check
            
        Returns:
            True if parser can handle this data
        """
        pass
    
    @property
    @abstractmethod
    def framework_name(self) -> str:
        """Return the framework name this parser handles"""
        pass