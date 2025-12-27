# Architecture

## Overview

The AWS HealthImaging MCP Server is built using the Model Context Protocol (MCP) to enable AI assistants to interact with AWS HealthImaging services.

## Components

### 1. MCP Server (`server.py`)

The main server component that:
- Initializes the MCP server instance
- Registers tools with the MCP framework
- Handles stdio communication with MCP clients
- Manages the server lifecycle

```
┌─────────────────┐
│   MCP Client    │ (Claude Desktop, Cline, etc.)
│  (AI Assistant) │
└────────┬────────┘
         │ stdio
         │
┌────────▼────────┐
│   MCP Server    │
│   (server.py)   │
└────────┬────────┘
         │
         │ registers
         │
┌────────▼────────┐
│     Tools       │
│   (tools.py)    │
└────────┬────────┘
         │
         │ boto3
         │
┌────────▼────────┐
│ AWS HealthImaging│
│      API        │
└─────────────────┘
```

### 2. Tools Module (`tools.py`)

Implements the actual HealthImaging operations:
- Data store management
- Image set operations
- Metadata retrieval
- Frame access

Each tool:
- Is decorated with `@server.tool()`
- Has a clear docstring describing its purpose
- Accepts typed parameters
- Returns JSON-formatted responses
- Handles errors gracefully

### 3. AWS Integration

Uses boto3 to interact with AWS HealthImaging:
- Client initialization with credential resolution
- API calls to HealthImaging service
- Error handling for AWS-specific exceptions
- Response formatting

## Data Flow

### Tool Invocation Flow

1. **Client Request**: AI assistant sends tool invocation request via MCP
2. **Server Routing**: MCP server routes to appropriate tool handler
3. **Parameter Validation**: Tool validates input parameters
4. **AWS API Call**: Tool uses boto3 to call HealthImaging API
5. **Response Processing**: Tool formats AWS response as JSON
6. **Error Handling**: Catches and formats any errors
7. **Client Response**: Returns formatted response to AI assistant

### Example: Listing Data Stores

```
AI Assistant: "List all HealthImaging data stores"
     │
     ▼
MCP Client: Invokes list_datastores tool
     │
     ▼
MCP Server: Routes to list_datastores handler
     │
     ▼
Tool: Calls boto3 client.list_datastores()
     │
     ▼
AWS API: Returns data store list
     │
     ▼
Tool: Formats response as JSON
     │
     ▼
MCP Server: Returns to client
     │
     ▼
AI Assistant: Processes and presents results
```

## Security Architecture

### Credential Management

```
┌─────────────────────────────────────┐
│     Credential Resolution Order     │
├─────────────────────────────────────┤
│ 1. Environment Variables            │
│    - AWS_ACCESS_KEY_ID              │
│    - AWS_SECRET_ACCESS_KEY          │
│    - AWS_SESSION_TOKEN              │
├─────────────────────────────────────┤
│ 2. AWS Credentials File             │
│    - ~/.aws/credentials             │
│    - Profile-based                  │
├─────────────────────────────────────┤
│ 3. IAM Role (EC2, ECS, Lambda)      │
│    - Instance metadata              │
│    - Container credentials          │
└─────────────────────────────────────┘
```

### IAM Permissions

The server requires specific IAM permissions:
- `medical-imaging:ListDatastores`
- `medical-imaging:GetDatastore`
- `medical-imaging:SearchImageSets`
- `medical-imaging:GetImageSet`
- `medical-imaging:GetImageSetMetadata`
- `medical-imaging:GetImageFrame`

## Error Handling

### Error Flow

```
Tool Execution
     │
     ├─ Success ──────────────────────┐
     │                                 │
     └─ Error                          │
          │                            │
          ├─ ClientError (boto3)       │
          │    │                       │
          │    └─ Log error            │
          │    └─ Return error JSON    │
          │                            │
          ├─ ValidationError           │
          │    │                       │
          │    └─ Return error JSON    │
          │                            │
          └─ Unexpected Error          │
               │                       │
               └─ Log error            │
               └─ Return error JSON    │
                                       │
                                       ▼
                              Return to Client
```

## Scalability Considerations

### Pagination

Tools support pagination parameters:
- `max_results`: Limit number of results
- `next_token`: For paginated responses (future enhancement)

### Caching

Future enhancements may include:
- Metadata caching for frequently accessed image sets
- Data store information caching
- TTL-based cache invalidation

### Rate Limiting

AWS HealthImaging has API rate limits:
- Tools should be used judiciously
- Consider implementing client-side rate limiting
- Monitor CloudWatch metrics for throttling

## Testing Architecture

### Test Structure

```
tests/
├── conftest.py          # Shared fixtures
├── test_server.py       # Server initialization tests
└── test_tools.py        # Tool functionality tests
```

### Mocking Strategy

- Mock boto3 clients to avoid AWS API calls
- Use fixtures for sample data
- Test both success and error paths
- Verify tool registration

## Deployment Models

### 1. Local Development

```
Developer Machine
├── Python environment
├── AWS credentials configured
└── MCP client (Claude Desktop)
```

### 2. Container Deployment

```
Docker Container
├── Python runtime
├── MCP server
├── AWS credentials (via env or IAM role)
└── Exposed stdio interface
```

### 3. Cloud Deployment

```
AWS Environment
├── EC2/ECS/Lambda
├── IAM role for HealthImaging access
├── VPC endpoint for HealthImaging
└── MCP client integration
```

## Future Enhancements

### Planned Features

1. **Streaming Support**: Handle large image frame data
2. **Batch Operations**: Process multiple image sets
3. **Advanced Search**: Complex DICOM query support
4. **Caching Layer**: Reduce API calls
5. **Metrics**: CloudWatch integration
6. **Async Optimization**: Parallel API calls

### Extension Points

- Custom tool implementations
- Additional AWS service integrations
- Enhanced error handling
- Performance monitoring
- Custom authentication mechanisms

## Performance Considerations

### Optimization Strategies

1. **Connection Pooling**: Reuse boto3 clients
2. **Lazy Loading**: Initialize resources on demand
3. **Parallel Requests**: Use asyncio for concurrent operations
4. **Response Streaming**: Handle large payloads efficiently
5. **Metadata Caching**: Cache frequently accessed data

### Monitoring

Key metrics to monitor:
- Tool invocation latency
- AWS API call duration
- Error rates
- Throttling events
- Memory usage

## References

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [AWS HealthImaging Documentation](https://docs.aws.amazon.com/healthimaging/)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
