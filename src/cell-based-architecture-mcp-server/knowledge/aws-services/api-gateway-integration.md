# API Gateway Integration with Cell-Based Architecture

## Overview

Amazon API Gateway is well-suited for cell-based architectures as a cell router, providing serverless HTTP routing with extensive features like caching, throttling, and native AWS service integration.

## API Gateway as Cell Router

### Basic Routing Architecture
```
Client → API Gateway → Lambda/DynamoDB Lookup → Target Cell
```

### Implementation Pattern
```yaml
# OpenAPI specification for cell routing
openapi: 3.0.0
info:
  title: Cell Router API
  version: 1.0.0

paths:
  /api/{customerId}/{proxy+}:
    x-amazon-apigateway-any-method:
      parameters:
        - name: customerId
          in: path
          required: true
          schema:
            type: string
        - name: proxy
          in: path
          required: true
          schema:
            type: string
      x-amazon-apigateway-integration:
        type: aws_proxy
        httpMethod: POST
        uri: arn:aws:apigateway:region:lambda:path/2015-03-31/functions/arn:aws:lambda:region:account:function:CellRouter/invocations
```

### Lambda Router Function
```python
import json
import boto3
import hashlib

dynamodb = boto3.resource('dynamodb')
mapping_table = dynamodb.Table('CellMappings')

def lambda_handler(event, context):
    # Extract customer ID from path
    customer_id = event['pathParameters']['customerId']
    proxy_path = event['pathParameters']['proxy']
    
    # Get cell assignment
    cell_id = get_cell_for_customer(customer_id)
    
    # Build target URL
    target_url = f"https://{cell_id}.internal.example.com/{proxy_path}"
    
    # Forward request to cell
    response = forward_to_cell(target_url, event)
    
    return response

def get_cell_for_customer(customer_id):
    try:
        response = mapping_table.get_item(Key={'CustomerId': customer_id})
        if 'Item' in response:
            return response['Item']['CellId']
        else:
            # Assign new customer to cell
            return assign_customer_to_cell(customer_id)
    except Exception as e:
        # Fallback to hash-based routing
        return hash_based_routing(customer_id)
```

## Advanced Routing Features

### Request Transformation
Transform requests before routing to cells:

```yaml
x-amazon-apigateway-integration:
  type: aws_proxy
  httpMethod: POST
  uri: arn:aws:apigateway:region:lambda:path/2015-03-31/functions/CellRouter/invocations
  requestTemplates:
    application/json: |
      {
        "customerId": "$input.params('customerId')",
        "cellId": "$stageVariables.defaultCell",
        "originalRequest": $input.json('$'),
        "headers": {
          #foreach($header in $input.params().header.keySet())
          "$header": "$util.escapeJavaScript($input.params().header.get($header))"
          #if($foreach.hasNext),#end
          #end
        }
      }
```

### Response Caching
Enable caching for routing decisions:

```yaml
# Cache routing responses for 5 minutes
x-amazon-apigateway-integration:
  cacheKeyParameters:
    - method.request.path.customerId
  cacheNamespace: "cell-routing"
  requestParameters:
    integration.request.path.customerId: method.request.path.customerId
```

### Throttling per Cell
Implement cell-aware throttling:

```python
def lambda_handler(event, context):
    customer_id = event['pathParameters']['customerId']
    cell_id = get_cell_for_customer(customer_id)
    
    # Check cell capacity
    if is_cell_at_capacity(cell_id):
        return {
            'statusCode': 429,
            'body': json.dumps({
                'error': 'Cell at capacity',
                'cellId': cell_id,
                'retryAfter': 60
            }),
            'headers': {
                'Retry-After': '60'
            }
        }
    
    # Route to cell
    return route_to_cell(cell_id, event)
```

## Cell-Specific API Gateways

### Dedicated API Gateway per Cell
Deploy separate API Gateways for each cell:

```yaml
# CloudFormation template
CellApiGateway:
  Type: AWS::ApiGateway::RestApi
  Properties:
    Name: !Sub "${CellId}-api"
    Description: !Sub "API Gateway for ${CellId}"
    EndpointConfiguration:
      Types:
        - REGIONAL
    Tags:
      - Key: CellId
        Value: !Ref CellId
      - Key: Environment
        Value: !Ref Environment
```

### Benefits
- **Complete isolation** - Each cell has independent API Gateway
- **Cell-specific configuration** - Different settings per cell
- **Independent scaling** - Each API Gateway scales independently
- **Blast radius containment** - Issues affect only one cell

### Considerations
- **Management overhead** - More API Gateways to manage
- **Cost implications** - Multiple API Gateway instances
- **DNS management** - Need cell-specific endpoints
- **Certificate management** - SSL certificates per cell

## Integration Patterns

### Direct Service Integration
Integrate API Gateway directly with AWS services:

```yaml
# Direct DynamoDB integration for cell routing
x-amazon-apigateway-integration:
  type: aws
  httpMethod: POST
  uri: arn:aws:apigateway:region:dynamodb:action/GetItem
  credentials: arn:aws:iam::account:role/ApiGatewayDynamoDBRole
  requestTemplates:
    application/json: |
      {
        "TableName": "CellMappings",
        "Key": {
          "CustomerId": {
            "S": "$input.params('customerId')"
          }
        }
      }
  responses:
    default:
      statusCode: 200
      responseTemplates:
        application/json: |
          #set($item = $input.path('$.Item'))
          #if($item)
          {
            "cellId": "$item.CellId.S",
            "customerId": "$item.CustomerId.S"
          }
          #else
          {
            "error": "Customer not found"
          }
          #end
```

### WebSocket Support
Handle WebSocket connections in cell-based architecture:

```python
import boto3

dynamodb = boto3.resource('dynamodb')
connections_table = dynamodb.Table('WebSocketConnections')

def connect_handler(event, context):
    connection_id = event['requestContext']['connectionId']
    customer_id = event['queryStringParameters']['customerId']
    
    # Determine cell for customer
    cell_id = get_cell_for_customer(customer_id)
    
    # Store connection with cell information
    connections_table.put_item(
        Item={
            'ConnectionId': connection_id,
            'CustomerId': customer_id,
            'CellId': cell_id,
            'ConnectedAt': datetime.utcnow().isoformat()
        }
    )
    
    return {'statusCode': 200}

def message_handler(event, context):
    connection_id = event['requestContext']['connectionId']
    
    # Get cell for this connection
    connection = connections_table.get_item(
        Key={'ConnectionId': connection_id}
    )
    
    if 'Item' in connection:
        cell_id = connection['Item']['CellId']
        # Route message to appropriate cell
        return route_websocket_message(cell_id, event)
    
    return {'statusCode': 404}
```

## Monitoring and Observability

### CloudWatch Integration
Monitor API Gateway metrics per cell:

```python
import boto3

cloudwatch = boto3.client('cloudwatch')

def put_cell_api_metrics(cell_id, request_count, latency, error_count):
    cloudwatch.put_metric_data(
        Namespace='CellBasedArchitecture/ApiGateway',
        MetricData=[
            {
                'MetricName': 'RequestCount',
                'Dimensions': [
                    {'Name': 'CellId', 'Value': cell_id}
                ],
                'Value': request_count,
                'Unit': 'Count'
            },
            {
                'MetricName': 'Latency',
                'Dimensions': [
                    {'Name': 'CellId', 'Value': cell_id}
                ],
                'Value': latency,
                'Unit': 'Milliseconds'
            },
            {
                'MetricName': 'ErrorCount',
                'Dimensions': [
                    {'Name': 'CellId', 'Value': cell_id}
                ],
                'Value': error_count,
                'Unit': 'Count'
            }
        ]
    )
```

### X-Ray Tracing
Enable distributed tracing for API Gateway:

```yaml
# Enable X-Ray tracing
ApiGatewayStage:
  Type: AWS::ApiGateway::Stage
  Properties:
    TracingEnabled: true
    Variables:
      cellId: !Ref CellId
```

### Access Logging
Configure cell-aware access logging:

```yaml
ApiGatewayStage:
  Type: AWS::ApiGateway::Stage
  Properties:
    AccessLogSetting:
      DestinationArn: !GetAtt ApiGatewayLogGroup.Arn
      Format: |
        {
          "requestId": "$context.requestId",
          "customerId": "$context.path.customerId",
          "cellId": "$context.stage.cellId",
          "ip": "$context.identity.sourceIp",
          "requestTime": "$context.requestTime",
          "httpMethod": "$context.httpMethod",
          "resourcePath": "$context.resourcePath",
          "status": "$context.status",
          "responseLength": "$context.responseLength",
          "responseTime": "$context.responseTime"
        }
```

## Security Considerations

### Authentication and Authorization
Implement cell-aware security:

```python
def authorizer_handler(event, context):
    token = event['authorizationToken']
    method_arn = event['methodArn']
    
    # Validate token and extract customer info
    customer_info = validate_token(token)
    if not customer_info:
        raise Exception('Unauthorized')
    
    # Get customer's cell
    cell_id = get_cell_for_customer(customer_info['customerId'])
    
    # Generate policy with cell context
    policy = generate_policy(
        customer_info['customerId'],
        'Allow',
        method_arn,
        {
            'customerId': customer_info['customerId'],
            'cellId': cell_id
        }
    )
    
    return policy
```

### WAF Integration
Configure AWS WAF for cell protection:

```yaml
WebACL:
  Type: AWS::WAFv2::WebACL
  Properties:
    Name: !Sub "${CellId}-waf"
    Scope: REGIONAL
    DefaultAction:
      Allow: {}
    Rules:
      - Name: RateLimitRule
        Priority: 1
        Statement:
          RateBasedStatement:
            Limit: 2000
            AggregateKeyType: IP
        Action:
          Block: {}
        VisibilityConfig:
          SampledRequestsEnabled: true
          CloudWatchMetricsEnabled: true
          MetricName: !Sub "${CellId}-RateLimit"
```

## Best Practices

### Performance Optimization
- **Enable caching** - Cache routing decisions and responses
- **Use regional endpoints** - Deploy close to users
- **Optimize Lambda cold starts** - Use provisioned concurrency
- **Connection pooling** - Reuse connections to backend services

### Cost Management
- **Monitor usage** - Track API calls per cell
- **Optimize caching** - Reduce backend calls with effective caching
- **Right-size integrations** - Choose appropriate integration types
- **Use compression** - Enable response compression

### Reliability
- **Circuit breakers** - Implement circuit breaker patterns
- **Retry logic** - Configure appropriate retry policies
- **Health checks** - Monitor cell health through API Gateway
- **Graceful degradation** - Handle cell failures gracefully

### Security
- **API keys** - Use API keys for client identification
- **Throttling** - Implement rate limiting per cell
- **CORS configuration** - Configure CORS appropriately
- **Input validation** - Validate all input parameters