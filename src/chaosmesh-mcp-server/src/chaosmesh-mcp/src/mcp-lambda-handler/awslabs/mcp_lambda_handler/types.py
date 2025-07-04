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

    def model_dump(self) -> Dict:
        return {'tools': self.tools}


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
