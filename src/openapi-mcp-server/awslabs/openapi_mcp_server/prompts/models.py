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
"""Data models for MCP prompts."""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional, Union


class PromptArgument(BaseModel):
    """Argument for an MCP prompt."""

    name: str = Field(..., description='Unique identifier for the argument')
    description: Optional[str] = Field(None, description='Human-readable description')
    required: bool = Field(False, description='Whether the argument is required')

    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {'name': self.name, 'required': self.required}
        if self.description:
            result['description'] = self.description
        return result


class ResourceContent(BaseModel):
    """Content for a resource message."""

    uri: str = Field(..., description='URI of the resource')
    mimeType: str = Field('application/json', description='MIME type of the resource')
    text: Optional[str] = Field(None, description='Text content of the resource')


class TextMessage(BaseModel):
    """Text message content."""

    type: Literal['text'] = Field('text', description='Type of message content')
    text: str = Field(..., description='Text content')


class ResourceMessage(BaseModel):
    """Resource message content."""

    type: Literal['resource'] = Field('resource', description='Type of message content')
    resource: ResourceContent = Field(..., description='Resource content')


class PromptMessage(BaseModel):
    """Message in an MCP prompt."""

    role: str = Field(..., description='Role of the message sender')
    content: Union[TextMessage, ResourceMessage] = Field(..., description='Content of the message')


class MCPPrompt(BaseModel):
    """MCP-compliant prompt definition."""

    name: str = Field(..., description='Unique identifier for the prompt')
    description: Optional[str] = Field(None, description='Human-readable description')
    arguments: Optional[List[PromptArgument]] = Field(None, description='Arguments for the prompt')
    messages: Optional[List[PromptMessage]] = Field(None, description='Messages in the prompt')
