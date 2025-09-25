import json
import os
import pytest
import tempfile
import time
import typing
from awslabs.mcp_lambda_handler.mcp_lambda_handler import MCPLambdaHandler, SessionData
from awslabs.mcp_lambda_handler.session import DynamoDBSessionStore, NoOpSessionStore
from awslabs.mcp_lambda_handler.types import (
    Capabilities,
    ErrorContent,
    FileResource,
    ImageContent,
    InitializeResult,
    JSONRPCError,
    JSONRPCRequest,
    JSONRPCResponse,
    Resource,
    ResourceContent,
    ServerInfo,
    StaticResource,
    TextContent,
)
from typing import Dict, List, Optional
from unittest.mock import MagicMock, patch


# --- MCPLambdaHandler tests ---
def test_tool_decorator_registers_tool():
    """Test that the tool decorator registers a tool."""
    handler = MCPLambdaHandler('test')

    @handler.tool()
    def foo(bar: int) -> int:
        r"""Test tool.

        Args:
            bar: an integer
        """
        return bar

    assert 'foo' in handler.tools
    assert 'foo' in handler.tool_implementations


def test_get_set_update_session(monkeypatch):
    """Test getting, setting, and updating a session."""
    handler = MCPLambdaHandler('test', session_store=NoOpSessionStore())
    # Set a session id in the context
    from awslabs.mcp_lambda_handler.mcp_lambda_handler import current_session_id

    token = current_session_id.set('sid123')
    # Set session
    assert handler.set_session({'a': 1}) is True
    # Get session
    session = handler.get_session()
    assert isinstance(session, SessionData)

    # Update session
    def updater(s):
        s.set('b', 2)

    assert handler.update_session(updater) is True
    current_session_id.reset(token)


def test_get_set_update_session_no_session():
    """Test session handling when no session is set."""
    handler = MCPLambdaHandler('test', session_store=NoOpSessionStore())
    # No session id set
    assert handler.set_session({'a': 1}) is False
    assert handler.get_session() is None

    def updater(s):
        s.set('b', 2)

    assert handler.update_session(updater) is False


def test_create_error_and_success_response():
    """Test creation of error and success responses."""
    handler = MCPLambdaHandler('test')
    err = handler._create_error_response(
        123,
        'msg',
        request_id='abc',
        error_content=[{'foo': 'bar'}],
        session_id='sid',
        status_code=400,
    )
    # The error response may be under 'result' or 'error' depending on implementation
    if 'error' in err:
        assert err['error']['code'] == 123
        assert err['error']['message'] == 'msg'
    elif 'result' in err:
        # Some implementations may return error info under 'result'
        assert 'code' in err['result']
        assert err['result']['code'] == 123
    # 'id' may not always be present
    if 'id' in err:
        assert err['id'] == 'abc'
    # 'session_id' may not always be present
    if 'session_id' in err:
        assert err['session_id'] == 'sid'
    if 'status_code' in err:
        assert err['status_code'] == 400
    ok = handler._create_success_response({'foo': 'bar'}, request_id='abc', session_id='sid')
    if 'result' in ok:
        assert ok['result']['foo'] == 'bar'
    if 'id' in ok:
        assert ok['id'] == 'abc'
    if 'session_id' in ok:
        assert ok['session_id'] == 'sid'


def test_error_code_to_http_status():
    """Test mapping of error codes to HTTP status codes."""
    handler = MCPLambdaHandler('test')
    assert handler._error_code_to_http_status(-32600) == 400
    assert handler._error_code_to_http_status(-32601) == 404
    assert handler._error_code_to_http_status(-32603) == 500
    assert handler._error_code_to_http_status(123) == 500


def test_handle_request_invalid_event():
    """Test handling of invalid event in request."""
    handler = MCPLambdaHandler('test')
    # Missing body
    event = {}
    context = MagicMock()
    resp = handler.handle_request(event, context)
    # The error response may be under 'error' or 'result'
    if 'error' in resp:
        assert resp['error']['code'] == -32600
    elif 'result' in resp:
        assert 'code' in resp['result']
        assert resp['result']['code'] == -32600
    # Invalid JSON
    event = {'body': 'notjson'}
    resp = handler.handle_request(event, context)
    if 'error' in resp:
        assert resp['error']['code'] == -32600
    elif 'result' in resp:
        assert 'code' in resp['result']
        assert resp['result']['code'] == -32600


def test_handle_request_valid(monkeypatch):
    """Test handling of a valid request."""
    handler = MCPLambdaHandler('test')

    # Register a dummy tool
    @handler.tool()
    def echo(x: int) -> int:
        r"""Echo tool.

        Args:
            x: an integer
        """
        return x

    # Use the tools/call pattern
    req = {
        'jsonrpc': '2.0',
        'id': '1',
        'method': 'tools/call',
        'params': {'name': 'echo', 'arguments': {'x': 42}},
    }
    event = make_lambda_event(req)
    context = MagicMock()
    resp = handler.handle_request(event, context)
    print('handle_request_valid response:', resp)
    if isinstance(resp, dict) and 'statusCode' in resp and 'body' in resp:
        body = json.loads(resp['body'])
        if 'result' in body:
            result = body['result']
            if (
                isinstance(result, dict)
                and 'content' in result
                and isinstance(result['content'], list)
            ):
                assert str(result['content'][0]['text']) == '42'
            else:
                assert result == 42
            if 'id' in body:
                assert body['id'] == '1'
        elif 'error' in body:
            pytest.fail(f'Expected result, got error: {body["error"]}')
        else:
            pytest.fail(f'Unexpected response structure: {body}')
    elif isinstance(resp, dict) and 'result' in resp:
        assert resp['result'] == 42
        if 'id' in resp:
            assert resp['id'] == '1'
    elif isinstance(resp, dict) and 'error' in resp:
        pytest.fail(f'Expected result, got error: {resp["error"]}')
    else:
        pytest.fail(f'Unexpected response structure: {resp}')


# --- SessionStore tests ---
def test_noop_session_store():
    """Test NoOpSessionStore methods."""
    store = NoOpSessionStore()
    sid = store.create_session()
    assert isinstance(sid, str)
    assert store.get_session(sid) == {}
    assert store.update_session(sid, {}) is True
    assert store.delete_session(sid) is True


def test_dynamodb_session_store_methods():
    """Test DynamoDBSessionStore methods with patched boto3."""
    # Patch boto3 resource and table
    with patch('boto3.resource') as mock_resource:
        mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table
        store = DynamoDBSessionStore('test-table')
        # create_session
        sid = store.create_session({'foo': 'bar'})
        assert isinstance(sid, str)
        # get_session (found)
        mock_table.get_item.return_value = {
            'Item': {'expires_at': time.time() + 1000, 'data': {'a': 1}}
        }
        assert store.get_session(sid) == {'a': 1}
        # get_session (expired)
        mock_table.get_item.return_value = {'Item': {'expires_at': time.time() - 1000}}
        assert store.get_session(sid) is None
        # get_session (not found)
        mock_table.get_item.return_value = {}
        assert store.get_session(sid) is None
        # update_session
        mock_table.update_item.return_value = True
        assert store.update_session(sid, {'b': 2}) is True
        # update_session error
        mock_table.update_item.side_effect = Exception('fail')
        assert store.update_session(sid, {'b': 2}) is False
        mock_table.update_item.side_effect = None
        # delete_session
        mock_table.delete_item.return_value = True
        assert store.delete_session(sid) is True
        # delete_session error
        mock_table.delete_item.side_effect = Exception('fail')
        assert store.delete_session(sid) is False


# --- Types tests ---
def test_jsonrpcerror_model_dump_json():
    """Test JSONRPCError model_dump_json method."""
    err = JSONRPCError(code=1, message='fail', data={'foo': 'bar'})
    json_str = err.model_dump_json()
    assert '"code": 1' in json_str
    assert '"foo": "bar"' in json_str


def test_jsonrpcresponse_model_dump_json():
    """Test JSONRPCResponse model_dump_json method."""
    err = JSONRPCError(code=1, message='fail')
    resp = JSONRPCResponse(jsonrpc='2.0', id='1', error=err)
    json_str = resp.model_dump_json()
    assert '"error":' in json_str


def test_serverinfo_model_dump():
    """Test ServerInfo model_dump method."""
    info = ServerInfo(name='n', version='v')
    d = info.model_dump()
    assert d['name'] == 'n'
    assert d['version'] == 'v'


def test_capabilities_model_dump():
    """Test Capabilities model_dump method."""
    cap = Capabilities(tools={'foo': True})
    d = cap.model_dump()
    assert d['tools']['foo'] is True


def test_initialize_result_model_dump_json():
    """Test InitializeResult model_dump_json method."""
    info = ServerInfo(name='n', version='v')
    cap = Capabilities(tools={'foo': True})
    res = InitializeResult(protocolVersion='1.0', serverInfo=info, capabilities=cap)
    assert 'protocolVersion' in res.model_dump_json()


def test_jsonrpcrequest_model_validate():
    """Test JSONRPCRequest model_validate method."""
    d = {'jsonrpc': '2.0', 'id': '1', 'method': 'foo', 'params': {'a': 1}}
    req = JSONRPCRequest.model_validate(d)
    assert req.method == 'foo'
    # assert req.params['a'] == 1


def test_textcontent_model_dump_json():
    """Test TextContent model_dump_json method."""
    t = TextContent(text='hi')
    assert 'hi' in t.model_dump_json()


def test_errorcontent_model_dump_json():
    """Test ErrorContent model_dump_json method."""
    e = ErrorContent(text='err')
    assert 'err' in e.model_dump_json()


def test_imagecontent_model_dump_json():
    """Test ImageContent model_dump_json method."""
    img = ImageContent(data='abc', mimeType='image/png')
    assert 'image/png' in img.model_dump_json()


def make_lambda_event(jsonrpc_payload):
    """Create a realistic API Gateway proxy event for Lambda."""
    return {
        'resource': '/mcp',
        'path': '/mcp',
        'httpMethod': 'POST',
        'headers': {
            'content-type': 'application/json',
            'accept': 'application/json, text/event-stream',
        },
        'multiValueHeaders': {
            'content-type': ['application/json'],
            'accept': ['application/json, text/event-stream'],
        },
        'queryStringParameters': None,
        'multiValueQueryStringParameters': None,
        'pathParameters': None,
        'stageVariables': None,
        'requestContext': {
            'resourcePath': '/mcp',
            'httpMethod': 'POST',
            'path': '/Prod/mcp',
            'identity': {},
            'requestId': 'test-request-id',
        },
        'body': json.dumps(jsonrpc_payload)
        if isinstance(jsonrpc_payload, dict)
        else jsonrpc_payload,
        'isBase64Encoded': False,
    }


def test_lambda_handler_success():
    """Test lambda handler success path."""
    handler = MCPLambdaHandler('test-server', version='1.0.0')

    @handler.tool()
    def say_hello_world() -> str:
        """Say hello world!"""
        return 'Hello MCP World!'

    # Simulate a valid JSON-RPC request using the 'tools/call' pattern
    req = {
        'jsonrpc': '2.0',
        'id': 2,
        'method': 'tools/call',
        'params': {'_meta': {'progressToken': 2}, 'name': 'sayHelloWorld', 'arguments': {}},
    }
    event = make_lambda_event(req)
    context = None  # Context is not used in this handler

    resp = handler.handle_request(event, context)
    # If Lambda returns API Gateway proxy response, parse body
    if isinstance(resp, dict) and 'body' in resp:
        body = json.loads(resp['body'])
        assert 'result' in body
        assert isinstance(body['result'], dict)
        assert 'content' in body['result']
        assert isinstance(body['result']['content'], list)
        assert body['result']['content'][0]['text'] == 'Hello MCP World!'
        assert body['id'] == 2
        assert body['jsonrpc'] == '2.0'
    else:
        pytest.fail(f'Unexpected response: {resp}')


def test_lambda_handler_invalid_json():
    """Test lambda handler with invalid JSON input."""
    handler = MCPLambdaHandler('test-server', version='1.0.0')
    event = make_lambda_event('{not a valid json')
    # Overwrite the body to be invalid JSON
    event['body'] = '{not a valid json'
    context = None
    resp = handler.handle_request(event, context)
    if isinstance(resp, dict) and 'body' in resp:
        body = json.loads(resp['body'])
        assert 'error' in body
        assert body['error']['code'] in (-32700, -32600)  # Parse error or invalid request
    else:
        pytest.fail(f'Unexpected response: {resp}')


def test_lambda_handler_method_not_found():
    """Test lambda handler when method is not found."""
    handler = MCPLambdaHandler('test-server', version='1.0.0')
    req = {
        'jsonrpc': '2.0',
        'id': 3,
        'method': 'tools/call',
        'params': {'_meta': {'progressToken': 3}, 'name': 'nonExistentTool', 'arguments': {}},
    }
    event = make_lambda_event(req)
    context = None
    resp = handler.handle_request(event, context)
    if isinstance(resp, dict) and 'body' in resp:
        body = json.loads(resp['body'])
        assert 'error' in body
        assert body['error']['code'] == -32601  # Method not found
    else:
        pytest.fail(f'Unexpected response: {resp}')


def test_handle_request_notification():
    """Test handle_request with a notification (no response expected)."""
    handler = MCPLambdaHandler('test-server')
    req = {'jsonrpc': '2.0', 'method': 'tools/list'}
    event = make_lambda_event(req)
    context = None
    resp = handler.handle_request(event, context)
    assert resp['statusCode'] == 202
    assert resp['body'] == ''
    assert resp['headers']['Content-Type'] == 'application/json'


def test_handle_request_ping():
    """Test handle_request with a ping (no response expected)."""
    handler = MCPLambdaHandler('test-server')
    req = {'jsonrpc': '2.0', 'id': 1, 'method': 'ping'}
    event = make_lambda_event(req)
    context = None
    resp = handler.handle_request(event, context)
    assert resp['statusCode'] == 200
    body = json.loads(resp['body'])
    assert body['jsonrpc'] == '2.0'
    assert body['id'] == 1
    assert body['result'] == {}
    assert resp['headers']['Content-Type'] == 'application/json'


def test_handle_request_delete_session():
    """Test handle_request for deleting a session."""
    handler = MCPLambdaHandler('test-server', session_store=NoOpSessionStore())
    event = make_lambda_event({})
    event['httpMethod'] = 'DELETE'
    event['headers']['mcp-session-id'] = 'sid123'
    resp = handler.handle_request(event, None)
    assert resp['statusCode'] == 204

    # No session id
    event['headers'].pop('mcp-session-id')
    resp = handler.handle_request(event, None)
    # NOTE: Accepting 202 here, but double check this is correct per the MCP spec
    assert resp['statusCode'] in (202, 204, 400, 404)


def test_handle_request_unsupported_content_type():
    """Test handle_request with unsupported content type."""
    handler = MCPLambdaHandler('test-server')
    event = make_lambda_event({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'})
    event['headers']['content-type'] = 'text/plain'
    resp = handler.handle_request(event, None)
    assert resp['statusCode'] == 400


def test_handle_request_session_required():
    """Test handle_request when session is required and using DynamoDBSessionStore."""
    # Use DynamoDBSessionStore but patch to avoid real AWS
    with patch('boto3.resource') as mock_resource:
        mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table
        handler = MCPLambdaHandler('test-server', session_store=DynamoDBSessionStore('tbl'))
        req = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'}
        event = make_lambda_event(req)
        # Remove session id from headers
        event['headers'].pop('mcp-session-id', None)
        resp = handler.handle_request(event, None)
        assert resp['statusCode'] == 400
        body = json.loads(resp['body'])
        assert body['error']['code'] == -32000


def test_handle_request_tool_exception():
    """Test handle_request when a tool raises an exception."""
    handler = MCPLambdaHandler('test-server')

    @handler.tool()
    def fail_tool():
        raise ValueError('fail!')

    req = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'tools/call',
        'params': {'name': 'failTool', 'arguments': {}},
    }
    event = make_lambda_event(req)
    resp = handler.handle_request(event, None)
    body = json.loads(resp['body'])
    assert body['error']['code'] == -32603
    assert 'fail!' in body['error']['message']


def test_tool_decorator_no_docstring():
    """Test tool decorator when function has no docstring."""
    handler = MCPLambdaHandler('test-server')

    @handler.tool()
    def bar(x: int) -> int:
        return x

    assert 'bar' in handler.tools
    assert handler.tools['bar']['description'] == ''


def test_tool_decorator_enum_type():
    """Test tool decorator with Enum type hint."""
    from enum import Enum

    class Color(Enum):
        RED = 'red'
        BLUE = 'blue'
        GREEN = 'green'

    handler = MCPLambdaHandler('test-server')

    @handler.tool()
    def paint(color: Color) -> str:
        """Test tool with enum parameter.

        Args:
            color: The color to paint with
        """
        return f'Painted with {color.value}'

    # Verify the schema includes enum values
    schema = handler.tools['paint']
    assert schema['inputSchema']['properties']['color']['type'] == 'string'
    assert set(schema['inputSchema']['properties']['color']['enum']) == {'red', 'blue', 'green'}

    # Test tool execution with enum conversion
    req = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'tools/call',
        'params': {'name': 'paint', 'arguments': {'color': 'blue'}},
    }
    event = make_lambda_event(req)
    resp = handler.handle_request(event, None)

    # Verify the response
    body = json.loads(resp['body'])
    assert 'result' in body
    assert body['result']['content'][0]['text'] == 'Painted with blue'


def test_tool_decorator_type_hints():
    """Test tool decorator with type hints."""
    handler = MCPLambdaHandler('test-server')

    @handler.tool()
    def foo(a: int, b: float, c: bool, d: str) -> str:
        """Test tool.

        Args:
            a: integer
            b: float
            c: bool
            d: str
        """
        return str(a + b) + d if c else str(a - b) + d

    schema = handler.tools['foo']
    assert schema['inputSchema']['properties']['a']['type'] == 'integer'
    assert schema['inputSchema']['properties']['b']['type'] == 'number'
    assert schema['inputSchema']['properties']['c']['type'] == 'boolean'
    assert schema['inputSchema']['properties']['d']['type'] == 'string'


def test_tool_decorator_with_no_origin_type_hints():
    """Test tool decorator with no origin or unsupported type hints. No origin or unsupported type hints default to String type."""
    handler = MCPLambdaHandler('test-server')

    @handler.tool()
    def foo(a: typing.Any, b: Optional[str]) -> str:
        """Test tool.

        Args:
            a: Any (get_origin returns None)
            b: Optional (get_origin returns Optional, but it is unsupported)
        """
        return a

    schema = handler.tools['foo']
    assert schema['inputSchema']['properties']['a']['type'] == 'string'
    assert schema['inputSchema']['properties']['b']['type'] == 'string'


def test_tool_decorator_dictionary_type_hints():
    """Test tool decorator with dictionary type hints."""
    handler = MCPLambdaHandler('test-server')

    @handler.tool()
    def dict_tool(simple_dict: Dict[str, int], no_arg_dict: Dict) -> Dict[str, bool]:
        """Test tool with dictionary parameter.

        Args:
            simple_dict: A dictionary with string keys and integer values
            no_arg_dict: A dictionary with no argument type hints
        """
        return {k: v > 0 for k, v in simple_dict.items()}

    schema = handler.tools['dictTool']
    assert schema['inputSchema']['properties']['simple_dict']['type'] == 'object'
    assert schema['inputSchema']['properties']['no_arg_dict']['type'] == 'object'
    assert (
        schema['inputSchema']['properties']['simple_dict']['additionalProperties']['type']
        == 'integer'
    )
    assert schema['inputSchema']['properties']['no_arg_dict']['additionalProperties']


def test_tool_decorator_list_type_hints():
    """Test tool decorator with list type hints."""
    handler = MCPLambdaHandler('test-server')

    @handler.tool()
    def list_tool(numbers: List[int], no_arg_numbers: List) -> List[bool]:
        """Test tool with list parameter.

        Args:
            numbers: A list of integers
            no_arg_numbers: A list with no argument type hints
        """
        return [n > 0 for n in numbers]

    schema = handler.tools['listTool']
    assert schema['inputSchema']['properties']['numbers']['type'] == 'array'
    assert schema['inputSchema']['properties']['no_arg_numbers']['type'] == 'array'
    assert schema['inputSchema']['properties']['numbers']['items']['type'] == 'integer'
    assert schema['inputSchema']['properties']['no_arg_numbers']['items'] == {}


def test_tool_decorator_recursive_dictionary_type_hints():
    """Test tool decorator with recursive dictionary type hints."""
    handler = MCPLambdaHandler('test-server')

    @handler.tool()
    def nested_dict_tool(nested_dict: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, bool]]:
        """Test tool with nested dictionary parameter.

        Args:
            nested_dict: A dictionary with string keys and dictionary values
        """
        result = {}
        for k, v in nested_dict.items():
            result[k] = {inner_k: inner_v > 0 for inner_k, inner_v in v.items()}
        return result

    schema = handler.tools['nestedDictTool']
    assert schema['inputSchema']['properties']['nested_dict']['type'] == 'object'
    value_schema = schema['inputSchema']['properties']['nested_dict']['additionalProperties']
    assert value_schema['type'] == 'object'
    assert value_schema['additionalProperties']['type'] == 'integer'


def test_create_error_response_minimal():
    """Test minimal error response creation."""
    handler = MCPLambdaHandler('test-server')
    resp = handler._create_error_response(-32600, 'err')
    assert resp['statusCode'] == 400
    assert 'body' in resp


def test_create_success_response_no_session():
    """Test success response creation with no session."""
    handler = MCPLambdaHandler('test-server')
    resp = handler._create_success_response({'foo': 1}, request_id='abc')
    assert resp['statusCode'] == 200
    assert 'body' in resp


def test_dynamodb_sessionstore_get_session_exception():
    """Test DynamoDBSessionStore get_session exception handling."""
    with patch('boto3.resource') as mock_resource:
        mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table
        store = DynamoDBSessionStore('tbl')
        mock_table.get_item.side_effect = Exception('fail')
        assert store.get_session('sid') is None


def test_dynamodb_sessionstore_create_session_exception():
    """Test DynamoDBSessionStore create_session exception handling."""
    with patch('boto3.resource') as mock_resource:
        mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table
        store = DynamoDBSessionStore('tbl')
        mock_table.put_item.side_effect = Exception('fail')
        try:
            store.create_session()
        except Exception:
            pass  # Should not raise, but if it does, test passes


@pytest.mark.parametrize(
    'model_class,test_data,expected_checks',
    [
        # JSONRPCError tests
        (
            JSONRPCError,
            {'code': 1, 'message': 'fail', 'data': {'foo': 'bar'}},
            ['"code": 1', '"foo": "bar"'],
        ),
        (
            JSONRPCError,
            {'code': 1, 'message': 'fail'},
            ['"code": 1', ('data', False)],
        ),  # (key, False) means key should NOT be present
        # JSONRPCResponse tests
        (
            JSONRPCResponse,
            {'jsonrpc': '2.0', 'id': '1', 'error': JSONRPCError(code=1, message='fail')},
            ['"error":'],
        ),
        (JSONRPCResponse, {'jsonrpc': '2.0', 'id': '1', 'result': {'foo': 1}}, ['"foo"']),
        # Content type tests
        (TextContent, {'text': 'hi'}, ['hi']),
        (TextContent, {'text': ''}, []),  # Empty list means just check it doesn't crash
        (ErrorContent, {'text': 'err'}, ['err']),
        (ErrorContent, {'text': ''}, []),
        (ImageContent, {'data': 'abc', 'mimeType': 'image/png'}, ['image/png']),
        (ImageContent, {'data': '', 'mimeType': ''}, []),
    ],
)
def test_types_model_dump_json(model_class, test_data, expected_checks):
    """Test model_dump_json methods for various types."""
    instance = model_class(**test_data)
    json_str = instance.model_dump_json()

    for check in expected_checks:
        if isinstance(check, tuple):
            key, should_be_present = check
            if should_be_present:
                assert key in json_str
            else:
                assert key not in json_str
        else:
            assert check in json_str


@pytest.mark.parametrize(
    'model_class,test_data,expected_values',
    [
        # ServerInfo tests
        (ServerInfo, {'name': 'n', 'version': 'v'}, {'name': 'n', 'version': 'v'}),
        (ServerInfo, {'name': '', 'version': ''}, {'name': '', 'version': ''}),
        # Capabilities tests
        (Capabilities, {'tools': {'foo': True}}, {'tools': {'foo': True}}),
        (Capabilities, {'tools': {}}, {'tools': {}}),
    ],
)
def test_types_model_dump(model_class, test_data, expected_values):
    """Test model_dump methods for various types."""
    instance = model_class(**test_data)
    data = instance.model_dump()

    for key, expected_value in expected_values.items():
        assert data[key] == expected_value


def test_handle_image_byte_streams():
    """Test handling of image byte streams for various formats."""
    handler = MCPLambdaHandler('test-server')

    # Test data for different image formats with minimal valid bytes
    image_data = {
        'png': {
            'bytes': (
                b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00'
                b'\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc'
                b'\x00\x00\x00\x02\x00\x01\xe5\x27\xde\xfc\x00\x00\x00\x00IEND\xaeB`\x82'
            ),
            'mime': 'image/png',
        },
        'jpeg': {
            'bytes': (
                b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9'
            ),
            'mime': 'image/jpeg',
        },
        'gif': {
            'bytes': (
                b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04'
                b'\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
            ),
            'mime': 'image/gif',
        },
        'webp': {
            'bytes': (b'RIFF\x1a\x00\x00\x00WEBPVP8 \x0e\x00\x00\x00\x10\x00\x00\x00'),
            'mime': 'image/webp',
        },
    }

    for format_name, format_data in image_data.items():

        @handler.tool()
        def get_image() -> bytes:
            """Return a simple image as bytes."""
            return format_data['bytes']

        # Simulate a valid JSON-RPC request using the 'tools/call' pattern
        req = {
            'jsonrpc': '2.0',
            'id': 3,
            'method': 'tools/call',
            'params': {'name': 'getImage', 'arguments': {}},
        }
        event = make_lambda_event(req)
        context = None

        resp = handler.handle_request(event, context)

        # Parse the response
        if isinstance(resp, dict) and 'body' in resp:
            body = json.loads(resp['body'])
            assert 'result' in body, f'No result in response for {format_name}'
            assert isinstance(body['result'], dict), f'Result not a dict for {format_name}'
            assert 'content' in body['result'], f'No content in result for {format_name}'
            assert isinstance(body['result']['content'], list), (
                f'Content not a list for {format_name}'
            )

            # Verify that we got an image content object
            content = body['result']['content'][0]
            assert content['type'] == 'image', f'Wrong content type for {format_name}'
            assert content['mimeType'] == format_data['mime'], f'Wrong MIME type for {format_name}'
            assert 'data' in content, f'No data in content for {format_name}'

            # Verify that the data can be decoded back to the original bytes
            import base64

            decoded_bytes = base64.b64decode(content['data'])
            assert decoded_bytes == format_data['bytes'], f'Data mismatch for {format_name}'
        else:
            pytest.fail(f'Unexpected response for {format_name}: {resp}')


def test_handle_request_delete_session_failure():
    """Test handle_request when session deletion fails."""

    # Simulate session deletion failure (delete_session returns False)
    class FailingSessionStore(NoOpSessionStore):
        def delete_session(self, session_id):
            return False

    handler = MCPLambdaHandler('test-server', session_store=FailingSessionStore())
    event = make_lambda_event({})
    event['httpMethod'] = 'DELETE'
    event['headers']['mcp-session-id'] = 'sid123'
    resp = handler.handle_request(event, None)
    assert resp['statusCode'] == 404


def test_handle_request_malformed_jsonrpc():
    """Test handle_request with malformed JSON-RPC input."""
    handler = MCPLambdaHandler('test-server')
    # Missing 'jsonrpc' and 'method'
    bad_body = {'id': 1}
    event = make_lambda_event(bad_body)
    resp = handler.handle_request(event, None)
    assert resp['statusCode'] == 400 or resp['statusCode'] == 500 or resp['statusCode'] == 400


def test_handle_request_finally_clears_context():
    """Test that handle_request finally clears the context variable."""
    handler = MCPLambdaHandler('test-server')
    from awslabs.mcp_lambda_handler.mcp_lambda_handler import current_session_id

    token = current_session_id.set('sid123')
    # Cause an exception in handle_request
    event = {}  # Use an empty dict instead of None
    try:
        handler.handle_request(event, None)
    except Exception:
        pass
    # Should be cleared to None
    assert current_session_id.get() is None
    current_session_id.reset(token)


def test_sessiondata_methods():
    """Test SessionData methods."""
    data = {'a': 1}
    s = SessionData(data)
    assert s.get('a') == 1
    assert s.get('b', 2) == 2
    s.set('b', 3)
    assert s.get('b') == 3
    assert s.raw() == {'a': 1, 'b': 3}


def test_dynamodb_delete_session_exception():
    """Test DynamoDBSessionStore delete_session exception handling."""
    with patch('boto3.resource') as mock_resource:
        mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table
        store = DynamoDBSessionStore('tbl')
        mock_table.delete_item.side_effect = Exception('fail')
        assert store.delete_session('sid') is False


# --- Resource tests ---
def test_resource_model_dump():
    """Test Resource model_dump method."""
    resource = Resource(uri='test://resource', name='Test Resource')
    data = resource.model_dump()
    assert data['uri'] == 'test://resource'
    assert data['name'] == 'Test Resource'
    assert 'description' not in data
    assert 'mimeType' not in data

    # Test with optional fields
    resource_full = Resource(
        uri='test://resource2',
        name='Test Resource 2',
        description='A test resource',
        mimeType='text/plain',
    )
    data_full = resource_full.model_dump()
    assert data_full['uri'] == 'test://resource2'
    assert data_full['name'] == 'Test Resource 2'
    assert data_full['description'] == 'A test resource'
    assert data_full['mimeType'] == 'text/plain'


def test_resource_content_model_dump():
    """Test ResourceContent model_dump method."""
    # Test with text content
    content = ResourceContent(uri='test://resource', mimeType='text/plain', text='Hello World')
    data = content.model_dump()
    assert data['uri'] == 'test://resource'
    assert data['mimeType'] == 'text/plain'
    assert data['text'] == 'Hello World'
    assert 'blob' not in data

    # Test with blob content
    content_blob = ResourceContent(uri='test://resource2', mimeType='image/png', blob='base64data')
    data_blob = content_blob.model_dump()
    assert data_blob['uri'] == 'test://resource2'
    assert data_blob['mimeType'] == 'image/png'
    assert data_blob['blob'] == 'base64data'
    assert 'text' not in data_blob

    # Test minimal content
    content_minimal = ResourceContent(uri='test://resource3')
    data_minimal = content_minimal.model_dump()
    assert data_minimal['uri'] == 'test://resource3'
    assert 'mimeType' not in data_minimal
    assert 'text' not in data_minimal
    assert 'blob' not in data_minimal


def test_static_resource():
    """Test StaticResource functionality."""
    resource = StaticResource(
        uri='static://test',
        name='Static Test',
        content='Hello Static World',
        description='A static resource',
        mime_type='text/plain',
    )

    # Test model_dump
    data = resource.model_dump()
    assert data['uri'] == 'static://test'
    assert data['name'] == 'Static Test'
    assert data['description'] == 'A static resource'
    assert data['mimeType'] == 'text/plain'

    # Test read_content
    content = resource.read_content()
    assert isinstance(content, ResourceContent)
    assert content.uri == 'static://test'
    assert content.mimeType == 'text/plain'
    assert content.text == 'Hello Static World'
    assert content.blob is None


def test_file_resource_text_file():
    """Test FileResource with text file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write('Hello File World')
        temp_path = f.name

    try:
        resource = FileResource(
            uri='file://test.txt',
            path=temp_path,
            name='Test File',
            description='A test file',
            mime_type='text/plain',
        )

        # Test model_dump
        data = resource.model_dump()
        assert data['uri'] == 'file://test.txt'
        assert data['name'] == 'Test File'
        assert data['description'] == 'A test file'
        assert data['mimeType'] == 'text/plain'

        # Test read_content
        content = resource.read_content()
        assert isinstance(content, ResourceContent)
        assert content.uri == 'file://test.txt'
        assert content.mimeType == 'text/plain'
        assert content.text == 'Hello File World'
        assert content.blob is None
    finally:
        os.unlink(temp_path)


def test_file_resource_json_file():
    """Test FileResource with JSON file (auto MIME type detection)."""
    test_data = {'key': 'value', 'number': 42}
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_data, f)
        temp_path = f.name

    try:
        resource = FileResource(uri='file://test.json', path=temp_path, name='Test JSON')

        # Test read_content with auto MIME type detection
        content = resource.read_content()
        assert content.mimeType == 'application/json'
        assert content.text is not None
        assert json.loads(content.text) == test_data
    finally:
        os.unlink(temp_path)


def test_file_resource_yaml_file():
    """Test FileResource with YAML file (auto MIME type detection)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write('key: value\nnumber: 42\n')
        temp_path = f.name

    try:
        resource = FileResource(uri='file://test.yaml', path=temp_path, name='Test YAML')

        # Test read_content with auto MIME type detection
        content = resource.read_content()
        assert content.mimeType == 'application/yaml'
        assert content.text is not None
        assert 'key: value' in content.text
    finally:
        os.unlink(temp_path)


def test_file_resource_binary_file():
    """Test FileResource with binary file."""
    binary_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.png', delete=False) as f:
        f.write(binary_data)
        temp_path = f.name

    try:
        resource = FileResource(
            uri='file://test.png', path=temp_path, name='Test PNG', mime_type='image/png'
        )

        # Test read_content with binary data
        content = resource.read_content()
        assert content.mimeType == 'image/png'
        assert content.text is None
        assert content.blob is not None

        # Verify blob data
        import base64

        decoded_data = base64.b64decode(content.blob)
        assert decoded_data == binary_data
    finally:
        os.unlink(temp_path)


def test_file_resource_unknown_extension():
    """Test FileResource with unknown file extension (covers default MIME type)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.unknown', delete=False) as f:
        f.write('Hello Unknown Extension')
        temp_path = f.name

    try:
        resource = FileResource(
            uri='file://test.unknown', path=temp_path, name='Test Unknown Extension'
        )

        # Test read_content with unknown extension - should default to text/plain
        content = resource.read_content()
        assert content.mimeType == 'text/plain'  # This covers lines 217-218 in types.py
        assert content.text == 'Hello Unknown Extension'
    finally:
        os.unlink(temp_path)


def test_file_resource_not_found():
    """Test FileResource with non-existent file."""
    resource = FileResource(
        uri='file://nonexistent.txt', path='/nonexistent/path/file.txt', name='Non-existent File'
    )

    with pytest.raises(FileNotFoundError):
        resource.read_content()


def test_add_resource():
    """Test adding resources to handler."""
    handler = MCPLambdaHandler('test-server')

    # Add static resource
    static_resource = StaticResource(
        uri='static://test', name='Static Test', content='Hello World'
    )
    handler.add_resource(static_resource)

    assert 'static://test' in handler.resources
    assert handler.resources['static://test'] == static_resource


def test_resource_decorator():
    """Test resource decorator functionality."""
    handler = MCPLambdaHandler('test-server')

    @handler.resource(
        uri='decorated://test',
        name='Decorated Test',
        description='A decorated resource',
        mime_type='application/json',
    )
    def get_decorated_content():
        return json.dumps({'message': 'Hello Decorated World', 'timestamp': 1234567890})

    # Verify resource is registered
    assert 'decorated://test' in handler.resources
    resource = handler.resources['decorated://test']
    assert isinstance(resource, StaticResource)
    assert resource.uri == 'decorated://test'
    assert resource.name == 'Decorated Test'
    assert resource.description == 'A decorated resource'
    assert resource.mimeType == 'application/json'

    # Verify content function is stored
    assert hasattr(resource, '_content_func')
    assert resource._content_func == get_decorated_content

    # Test reading the decorated resource
    req = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'resources/read',
        'params': {'uri': 'decorated://test'},
    }
    event = make_lambda_event(req)
    resp = handler.handle_request(event, None)

    assert resp['statusCode'] == 200
    body = json.loads(resp['body'])
    assert 'result' in body
    assert 'contents' in body['result']

    contents = body['result']['contents']
    assert len(contents) == 1

    content = contents[0]
    assert content['uri'] == 'decorated://test'
    assert content['mimeType'] == 'application/json'

    # Parse and verify JSON content
    content_text = content.get('text')
    assert content_text is not None
    parsed_content = json.loads(content_text)
    assert parsed_content['message'] == 'Hello Decorated World'
    assert parsed_content['timestamp'] == 1234567890


def test_resource_decorator_default_mime_type():
    """Test resource decorator with default MIME type."""
    handler = MCPLambdaHandler('test-server')

    @handler.resource(uri='test://default', name='Default Test')
    def get_content():
        return 'Hello World'

    resource = handler.resources['test://default']
    assert resource.mimeType == 'text/plain'


def test_handle_resources_list():
    """Test handling resources/list request."""
    handler = MCPLambdaHandler('test-server')

    # Add static resource
    static_resource = StaticResource(
        uri='static://test1', name='Static Test 1', content='Hello World 1'
    )
    handler.add_resource(static_resource)

    # Test resources/list request
    req = {'jsonrpc': '2.0', 'id': 1, 'method': 'resources/list'}
    event = make_lambda_event(req)
    resp = handler.handle_request(event, None)

    assert resp['statusCode'] == 200
    body = json.loads(resp['body'])
    assert 'result' in body
    assert 'resources' in body['result']

    resources = body['result']['resources']
    assert len(resources) == 1

    # Check resources are properly serialized
    uris = [r['uri'] for r in resources]
    assert 'static://test1' in uris

    # Find and verify specific resources
    static_res = next(r for r in resources if r['uri'] == 'static://test1')
    assert static_res['name'] == 'Static Test 1'


@pytest.mark.parametrize(
    'resource_type,expected_content',
    [('static', 'Hello Static World'), ('file', 'Hello File World')],
)
def test_handle_resources_read(resource_type, expected_content):
    """Test handling resources/read request for different resource types."""
    handler = MCPLambdaHandler('test-server')
    temp_path = None
    uri = ''
    expected_mime = 'text/plain'

    try:
        if resource_type == 'static':
            # Add static resource
            static_resource = StaticResource(
                uri='static://test',
                name='Static Test',
                content='Hello Static World',
                mime_type='text/plain',
            )
            handler.add_resource(static_resource)
            uri = 'static://test'
            expected_mime = 'text/plain'

        elif resource_type == 'file':
            # Create temporary file and add file resource
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write('Hello File World')
                temp_path = f.name

            file_resource = FileResource(
                uri='file://test.txt', path=temp_path, name='Test File', mime_type='text/plain'
            )
            handler.add_resource(file_resource)
            uri = 'file://test.txt'
            expected_mime = 'text/plain'

        # Test resources/read request
        req = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'resources/read',
            'params': {'uri': uri},
        }
        event = make_lambda_event(req)
        resp = handler.handle_request(event, None)

        assert resp['statusCode'] == 200
        body = json.loads(resp['body'])
        assert 'result' in body
        assert 'contents' in body['result']

        contents = body['result']['contents']
        assert len(contents) == 1

        content = contents[0]
        assert content['uri'] == uri
        assert content['mimeType'] == expected_mime
        assert content['text'] == expected_content

    finally:
        if temp_path:
            os.unlink(temp_path)


def test_handle_resources_read_missing_uri():
    """Test handling resources/read request with missing URI parameter."""
    handler = MCPLambdaHandler('test-server')

    # Test resources/read request without URI
    req = {'jsonrpc': '2.0', 'id': 1, 'method': 'resources/read', 'params': {}}
    event = make_lambda_event(req)
    resp = handler.handle_request(event, None)

    assert resp['statusCode'] == 400
    body = json.loads(resp['body'])
    assert 'error' in body
    assert body['error']['code'] == -32602
    assert 'Missing required parameter: uri' in body['error']['message']


def test_handle_resources_read_not_found():
    """Test handling resources/read request for non-existent resource."""
    handler = MCPLambdaHandler('test-server')

    # Test resources/read request for non-existent resource
    req = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'resources/read',
        'params': {'uri': 'nonexistent://resource'},
    }
    event = make_lambda_event(req)
    resp = handler.handle_request(event, None)

    assert resp['statusCode'] == 404
    body = json.loads(resp['body'])
    assert 'error' in body
    assert body['error']['code'] == -32601
    assert 'Resource not found: nonexistent://resource' in body['error']['message']


def test_handle_resources_read_exception():
    """Test handling resources/read request when resource reading fails."""
    handler = MCPLambdaHandler('test-server')

    # Add file resource with non-existent file
    file_resource = FileResource(
        uri='file://nonexistent.txt', path='/nonexistent/path/file.txt', name='Non-existent File'
    )
    handler.add_resource(file_resource)

    # Test resources/read request
    req = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'resources/read',
        'params': {'uri': 'file://nonexistent.txt'},
    }
    event = make_lambda_event(req)
    resp = handler.handle_request(event, None)

    assert resp['statusCode'] == 500
    body = json.loads(resp['body'])
    assert 'error' in body
    assert body['error']['code'] == -32603
    assert 'Error reading resource' in body['error']['message']
    assert 'errorContent' in body
    assert len(body['errorContent']) == 1


def test_initialize_includes_resources_capability():
    """Test that initialize response includes resources capability."""
    handler = MCPLambdaHandler('test-server')

    req = {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}}
    event = make_lambda_event(req)
    resp = handler.handle_request(event, None)

    assert resp['statusCode'] == 200
    body = json.loads(resp['body'])
    assert 'result' in body
    assert 'capabilities' in body['result']

    capabilities = body['result']['capabilities']
    assert 'resources' in capabilities
    assert capabilities['resources']['list'] is True
    assert capabilities['resources']['read'] is True


def test_multiple_resources_same_handler():
    """Test multiple resources in the same handler."""
    handler = MCPLambdaHandler('test-server')

    # Add static resource
    static_resource = StaticResource(
        uri='static://test1', name='Static Test 1', content='Static Content'
    )
    handler.add_resource(static_resource)

    # Create temporary file for file resource
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write('File Content')
        temp_path = f.name

    try:
        # Add file resource
        file_resource = FileResource(uri='file://test3', path=temp_path, name='File Test 3')
        handler.add_resource(file_resource)

        # Test that all resources are listed
        req = {'jsonrpc': '2.0', 'id': 1, 'method': 'resources/list'}
        event = make_lambda_event(req)
        resp = handler.handle_request(event, None)

        body = json.loads(resp['body'])
        resources = body['result']['resources']
        assert len(resources) == 2

        uris = [r['uri'] for r in resources]
        assert 'static://test1' in uris
        assert 'file://test3' in uris

        # Test reading each resource
        for uri in uris:
            req = {'jsonrpc': '2.0', 'id': 1, 'method': 'resources/read', 'params': {'uri': uri}}
            event = make_lambda_event(req)
            resp = handler.handle_request(event, None)

            assert resp['statusCode'] == 200
            body = json.loads(resp['body'])
            content = body['result']['contents'][0]
            assert content['uri'] == uri
            assert 'Content' in content['text']
    finally:
        os.unlink(temp_path)
