#!/usr/bin/env python3

from typing import Dict, Any


class ConversionError(Exception):
    """Base exception for conversion errors with context"""
    def __init__(self, message: str, context: Dict[str, Any] = None):
        self.context = context or {}
        super().__init__(message)


class ParsingError(ConversionError):
    """Parser-specific errors"""
    pass