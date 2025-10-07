"""
Custom exceptions for AWS DMS MCP Server.

Provides a hierarchy of exceptions for proper error handling and reporting.
"""

from .dms_exceptions import (
    DMSMCPException,
    DMSResourceNotFoundException,
    DMSInvalidParameterException,
    DMSAccessDeniedException,
    DMSResourceInUseException,
    DMSConnectionTestException,
    DMSReadOnlyModeException,
    DMSValidationException,
    AWS_ERROR_MAP,
)

__all__ = [
    'DMSMCPException',
    'DMSResourceNotFoundException',
    'DMSInvalidParameterException',
    'DMSAccessDeniedException',
    'DMSResourceInUseException',
    'DMSConnectionTestException',
    'DMSReadOnlyModeException',
    'DMSValidationException',
    'AWS_ERROR_MAP',
]
