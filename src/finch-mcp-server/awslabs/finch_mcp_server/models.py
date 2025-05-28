"""Pydantic models for the Finch MCP server.

This module defines the data models used for request and response validation
in the Finch MCP server tools.
"""

from pydantic import BaseModel, Field


class Result(BaseModel):
    """Base model for operation results.

    This model only includes status and message fields, regardless of what additional
    fields might be present in the input dictionary. This ensures that only these two
    fields are returned to the user.
    """

    status: str = Field(..., description="Status of the operation ('success', 'error', etc.)")
    message: str = Field(..., description='Descriptive message about the result of the operation')
