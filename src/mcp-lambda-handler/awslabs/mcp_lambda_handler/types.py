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

"""Type definitions for MCP protocol."""

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class JSONRPCError:
    code: int
    message: str
    data: Optional[Any] = None

    def model_dump_json(self) -> str:
        import json

        return json.dumps(
            {
                'code': self.code,
                'message': self.message,
                **({'data': self.data} if self.data is not None else {}),
            }
        )


@dataclass
class JSONRPCResponse:
    jsonrpc: str
    id: Optional[str]
    result: Optional[Any] = None
    error: Optional[JSONRPCError] = None
    errorContent: Optional[List[Dict]] = None

    def model_dump_json(self) -> str:
        import json

        data = {'jsonrpc': self.jsonrpc, 'id': self.id}
        if self.result is not None:
            data['result'] = self.result
        if self.error is not None:
            data['error'] = json.loads(self.error.model_dump_json())
        if self.errorContent is not None:
            data['errorContent'] = self.errorContent
        return json.dumps(data)


@dataclass
class ServerInfo:
    name: str
    version: str

    def model_dump(self) -> Dict:
        return {'name': self.name, 'version': self.version}


@dataclass
class Capabilities:
    tools: Dict[str, bool]
    resources: Optional[Dict[str, bool]] = None

    def model_dump(self) -> Dict:
        data = {'tools': self.tools}
        if self.resources:
            data['resources'] = self.resources
        return data


@dataclass
class InitializeResult:
    protocolVersion: str
    serverInfo: ServerInfo
    capabilities: Capabilities

    def model_dump(self) -> Dict:
        return {
            'protocolVersion': self.protocolVersion,
            'serverInfo': self.serverInfo.model_dump(),
            'capabilities': self.capabilities.model_dump(),
        }

    def model_dump_json(self) -> str:
        import json

        return json.dumps(self.model_dump())


@dataclass
class JSONRPCRequest:
    jsonrpc: str
    id: Optional[str]
    method: str
    params: Optional[Dict] = None

    @classmethod
    def model_validate(cls, data: Dict) -> 'JSONRPCRequest':
        return cls(
            jsonrpc=data['jsonrpc'],
            id=data.get('id'),
            method=data['method'],
            params=data.get('params'),
        )


@dataclass
class TextContent:
    text: str
    type: str = 'text'

    def model_dump(self) -> Dict:
        return {'type': self.type, 'text': self.text}

    def model_dump_json(self) -> str:
        import json

        return json.dumps(self.model_dump())


@dataclass
class ErrorContent:
    text: str
    type: str = 'error'

    def model_dump(self) -> Dict:
        return {'type': self.type, 'text': self.text}

    def model_dump_json(self) -> str:
        import json

        return json.dumps(self.model_dump())


@dataclass
class ImageContent:
    data: str
    mimeType: str
    type: str = 'image'

    def model_dump(self) -> Dict:
        return {'type': self.type, 'data': self.data, 'mimeType': self.mimeType}

    def model_dump_json(self) -> str:
        import json

        return json.dumps(self.model_dump())


@dataclass
class ResourceContent:
    uri: str
    mimeType: Optional[str] = None
    text: Optional[str] = None
    blob: Optional[str] = None  # base64 encoded binary data

    def model_dump(self) -> Dict:
        data = {'uri': self.uri}
        if self.mimeType:
            data['mimeType'] = self.mimeType
        if self.text is not None:
            data['text'] = self.text
        if self.blob is not None:
            data['blob'] = self.blob
        return data


@dataclass
class Resource:
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None

    def __post_init__(self):
        """Initialize optional attributes for subclass compatibility."""
        if not hasattr(self, '_content_func'):
            self._content_func: Optional[Any] = None

    def model_dump(self) -> Dict:
        data = {'uri': self.uri, 'name': self.name}
        if self.description:
            data['description'] = self.description
        if self.mimeType:
            data['mimeType'] = self.mimeType
        return data

    def read_content(self) -> 'ResourceContent':
        """Default implementation - should be overridden by subclasses."""
        raise NotImplementedError('Subclasses must implement read_content method')


class FileResource(Resource):
    def __init__(
        self,
        uri: str,
        path: str,
        name: str,
        description: Optional[str] = None,
        mime_type: Optional[str] = None,
    ):
        """Initialize a FileResource.

        Args:
            uri: The URI identifier for this resource
            path: The file system path to the resource file
            name: The display name for this resource
            description: Optional description of the resource
            mime_type: Optional MIME type override (auto-detected if not provided)
        """
        super().__init__(uri, name, description, mime_type)
        self.path = path

    def read_content(self) -> ResourceContent:
        if not os.path.exists(self.path):
            raise FileNotFoundError(f'Resource file not found: {self.path}')

        # Determine MIME type if not specified
        mime_type = self.mimeType
        if not mime_type:
            if self.path.endswith('.json'):
                mime_type = 'application/json'
            elif self.path.endswith('.yaml') or self.path.endswith('.yml'):
                mime_type = 'application/yaml'
            elif self.path.endswith('.txt'):
                mime_type = 'text/plain'
            else:
                mime_type = 'text/plain'

        try:
            # Try to read as text first
            with open(self.path, 'r', encoding='utf-8') as f:
                content = f.read()
            return ResourceContent(uri=self.uri, mimeType=mime_type, text=content)
        except UnicodeDecodeError:
            # If text reading fails, read as binary and base64 encode
            import base64

            with open(self.path, 'rb') as f:
                content = f.read()
            blob_data = base64.b64encode(content).decode('utf-8')
            return ResourceContent(
                uri=self.uri, mimeType=mime_type or 'application/octet-stream', blob=blob_data
            )


class StaticResource(Resource):
    def __init__(
        self,
        uri: str,
        name: str,
        content: str,
        description: Optional[str] = None,
        mime_type: str = 'text/plain',
    ):
        """Initialize a StaticResource.

        Args:
            uri: The URI identifier for this resource
            name: The display name for this resource
            content: The static content to serve
            description: Optional description of the resource
            mime_type: MIME type of the content (defaults to 'text/plain')
        """
        super().__init__(uri, name, description, mime_type)
        self.content = content
        self._content_func: Optional[Any] = None  # For decorator support

    def read_content(self) -> ResourceContent:
        return ResourceContent(uri=self.uri, mimeType=self.mimeType, text=self.content)
