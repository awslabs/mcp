"""
AWS integration module for CloudWAN MCP Server.

This module provides AWS service clients, session management, and 
multi-region operational capabilities for CloudWAN operations.
"""

from .client_manager import AWSClientManager

__all__ = ["AWSClientManager"]
