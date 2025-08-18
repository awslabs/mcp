# Reference Architectures for Cell-Based Systems

## Overview

This document provides concrete reference architectures for implementing cell-based systems using AWS services. These architectures are based on real-world implementations and AWS service team patterns.

## E-Commerce Platform Architecture

### Overview
A scalable e-commerce platform using cell-based architecture to handle customer orders, inventory, and payments.

### Architecture Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Route 53 (DNS Routing)                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              API Gateway (Cell Router)                     │
│  • Customer ID extraction                                  │
│  • Cell routing logic                                      │
│  • Rate limiting per cell                                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
┌───────▼──────┐ ┌────▼─────┐ ┌────▼─────┐
│   Cell A     │ │  Cell B  │ │  Cell C  │
│              │ │          │ │          │
│ Lambda       │ │ Lambda   │ │ Lambda   │
│ DynamoDB     │ │ DynamoDB │ │ DynamoDB │
│ S3 Bucket    │ │ S3 Bucket│ │ S3 Bucket│
│ SQS Queue    │ │ SQS Queue│ │ SQS Queue│
└──────────────┘ └──────────┘ └──────────┘
```

### Implementation Details

#### Cell Router (API Gateway + Lambda)
```python
import json
import boto3
import hashlib

def lambda_handler(event, context):
    # Extract customer ID from request
    path_params = event.get('pathParameters', {})
    customer_id = path_params.get('customerId')
    
    if not customer_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Customer ID required'})
        }
    
    # Route to appropriate cell
    cell_id = route_customer_to_cell(customer_id)
    
    # Forward request to cell
    return forward_to_cell(cell_id, event)

def route_customer_to_cell(customer_id):
    # Hash-based routing for even distribution
    hash_value = int(hashlib.md5(customer_id.encode()).hexdigest(), 16)
    cell_number = hash_value % 3  # 3 cells
    return f"cell-{chr(65 + cell_number)}"  # cell-A, cell-B, cell-C

def forward_to_cell(cell_id, event):
    # Get cell-specific endpoint
    cell_endpoint = get_cell_endpoint(cell_id)
    
    # Forward request to cell
    response = invoke_cell_service(cell_endpoint, event)
    return response
```

#### Cell Implementation (Lambda + DynamoDB)
```python
# Cell-specific order processing
import boto3
import json
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')

def process_order(event, context):
    cell_id = os.environ['CELL_ID']
    
    # Parse order request
    order_data = json.loads(event['body'])
    customer_id = order_data['customerId']
    
    # Store order in cell-specific table
    orders_table = dynamodb.Table(f'Orders-{cell_id}')
    
    order_item = {
        'OrderId': generate_order_id(),
        'CustomerId': customer_id,
        'Items': order_data['items'],
        'Total': calculate_total(order_data['items']),
        'Status': 'PENDING',
        'CreatedAt': datetime.utcnow().isoformat(),
        'CellId': cell_id
    }
    
    orders_table.put_item(Item=order_item)
    
    # Queue for async processing
    queue_url = f"https://sqs.us-east-1.amazonaws.com/123456789012/orders-{cell_id}"
    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(order_item)
    )
    
    return {
        'statusCode': 201,
        'body': json.dumps({
            'orderId': order_item['OrderId'],
            'status': 'PENDING',
            'cellId': cell_id
        })
    }
```

### Deployment Configuration
```yaml
# CloudFormation template for e-commerce cells
Parameters:
  CellId:
    Type: String
    Description: Unique identifier for this cell
  
Resources:
  # Cell-specific DynamoDB tables
  OrdersTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub "Orders-${CellId}"
      BillingMode: ON_DEMAND
      AttributeDefinitions:
        - AttributeName: OrderId
          AttributeType: S
        - AttributeName: CustomerId
          AttributeType: S
      KeySchema:
        - AttributeName: OrderId
          KeyType: HASH
      GlobalSecondaryIndexes:
        - IndexName: CustomerIndex
          KeySchema:
            - AttributeName: CustomerId
              KeyType: HASH
          Projection:
            ProjectionType: ALL
  
  # Cell-specific processing queue
  OrderQueue:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: !Sub "orders-${CellId}"
      VisibilityTimeoutSeconds: 300
      MessageRetentionPeriod: 1209600
  
  # Cell processing Lambda
  OrderProcessor:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: !Sub "${CellId}-order-processor"
      Runtime: python3.9
      Handler: index.process_order
      Environment:
        Variables:
          CELL_ID: !Ref CellId
          ORDERS_TABLE: !Ref OrdersTable
          ORDER_QUEUE: !Ref OrderQueue
```

## Multi-Tenant SaaS Architecture

### Overview
A multi-tenant SaaS application using cell-based architecture for tenant isolation and scaling.

### Architecture Components

```
┌─────────────────────────────────────────────────────────────┐
│                CloudFront Distribution                      │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              Application Load Balancer                     │
│  • SSL termination                                         │
│  • Health checks                                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              ECS Service (Cell Router)                     │
│  • Tenant ID extraction                                    │
│  • Cell routing decisions                                  │
│  • Load balancing to cells                                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
┌───────▼──────┐ ┌────▼─────┐ ┌────▼─────┐
│   Cell 1     │ │  Cell 2  │ │  Cell 3  │
│              │ │          │ │          │
│ ECS Tasks    │ │ ECS Tasks│ │ ECS Tasks│
│ RDS Instance │ │ RDS Inst │ │ RDS Inst │
│ ElastiCache  │ │ ElastiC  │ │ ElastiC  │
│ S3 Prefix    │ │ S3 Prefix│ │ S3 Prefix│
└──────────────┘ └──────────┘ └──────────┘
```

### Implementation Details

#### Cell Router (ECS Service)
```python
from flask import Flask, request, jsonify
import requests
import hashlib
import os

app = Flask(__name__)

CELL_ENDPOINTS = {
    'cell-1': 'http://cell-1-alb.internal:8080',
    'cell-2': 'http://cell-2-alb.internal:8080', 
    'cell-3': 'http://cell-3-alb.internal:8080'
}

@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def route_request(path):
    # Extract tenant ID from request
    tenant_id = extract_tenant_id(request)
    
    if not tenant_id:
        return jsonify({'error': 'Tenant ID required'}), 400
    
    # Route to appropriate cell
    cell_id = route_tenant_to_cell(tenant_id)
    
    # Forward request to cell
    return forward_to_cell(cell_id, path, request)

def extract_tenant_id(request):
    # Try multiple methods to extract tenant ID
    
    # 1. From subdomain (tenant.example.com)
    host = request.headers.get('Host', '')
    if '.' in host:
        subdomain = host.split('.')[0]
        if subdomain != 'www' and subdomain != 'api':
            return subdomain
    
    # 2. From path (/tenant/123/api/...)
    path_parts = request.path.split('/')
    if len(path_parts) > 2 and path_parts[1] == 'tenant':
        return path_parts[2]
    
    # 3. From header
    return request.headers.get('X-Tenant-ID')

def route_tenant_to_cell(tenant_id):
    # Consistent hashing for tenant distribution
    hash_value = int(hashlib.md5(tenant_id.encode()).hexdigest(), 16)
    cell_number = (hash_value % 3) + 1
    return f"cell-{cell_number}"

def forward_to_cell(cell_id, path, request):
    cell_endpoint = CELL_ENDPOINTS[cell_id]
    url = f"{cell_endpoint}/{path}"
    
    # Forward request with all headers and data
    response = requests.request(
        method=request.method,
        url=url,
        headers=dict(request.headers),
        data=request.get_data(),
        params=request.args
    )
    
    return response.content, response.status_code, response.headers.items()
```

#### Cell Application (ECS Tasks)
```python
from flask import Flask, request, jsonify
import psycopg2
import redis
import os

app = Flask(__name__)

# Cell-specific configurations
CELL_ID = os.environ['CELL_ID']
DB_HOST = os.environ['DB_HOST']
REDIS_HOST = os.environ['REDIS_HOST']

# Database connection per cell
db_conn = psycopg2.connect(
    host=DB_HOST,
    database=f"saas_cell_{CELL_ID}",
    user=os.environ['DB_USER'],
    password=os.environ['DB_PASSWORD']
)

# Cache connection per cell
cache = redis.Redis(host=REDIS_HOST, port=6379, db=0)

@app.route('/api/users', methods=['GET'])
def get_users():
    tenant_id = request.headers.get('X-Tenant-ID')
    
    # Check cache first
    cache_key = f"users:{tenant_id}"
    cached_users = cache.get(cache_key)
    
    if cached_users:
        return jsonify(json.loads(cached_users))
    
    # Query database
    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE tenant_id = %s",
        (tenant_id,)
    )
    
    users = cursor.fetchall()
    
    # Cache results
    cache.setex(cache_key, 300, json.dumps(users))
    
    return jsonify(users)

@app.route('/api/users', methods=['POST'])
def create_user():
    tenant_id = request.headers.get('X-Tenant-ID')
    user_data = request.json
    
    # Insert into cell-specific database
    cursor = db_conn.cursor()
    cursor.execute(
        """INSERT INTO users (tenant_id, name, email, created_at) 
           VALUES (%s, %s, %s, NOW()) RETURNING id""",
        (tenant_id, user_data['name'], user_data['email'])
    )
    
    user_id = cursor.fetchone()[0]
    db_conn.commit()
    
    # Invalidate cache
    cache.delete(f"users:{tenant_id}")
    
    return jsonify({'id': user_id, 'status': 'created'}), 201
```

## Financial Services Architecture

### Overview
A financial services platform with strict isolation requirements and regulatory compliance.

### Architecture Components

```
┌─────────────────────────────────────────────────────────────┐
│                    WAF + Shield                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              API Gateway (Private)                         │
│  • VPC Endpoint                                            │
│  • Mutual TLS                                              │
│  • Request validation                                      │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              Lambda Authorizer                             │
│  • JWT validation                                          │
│  • Customer routing                                        │
│  • Audit logging                                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
┌───────▼──────┐ ┌────▼─────┐ ┌────▼─────┐
│ Retail Cell  │ │Corp Cell │ │ HNW Cell │
│              │ │          │ │          │
│ Fargate      │ │ Fargate  │ │ Fargate  │
│ Aurora       │ │ Aurora   │ │ Aurora   │
│ KMS Keys     │ │ KMS Keys │ │ KMS Keys │
│ VPC          │ │ VPC      │ │ VPC      │
└──────────────┘ └──────────┘ └──────────┘
```

### Implementation Details

#### Secure Cell Router
```python
import json
import boto3
import jwt
from datetime import datetime

kms = boto3.client('kms')
logs = boto3.client('logs')

def lambda_handler(event, context):
    try:
        # Validate JWT token
        token = extract_token(event)
        claims = validate_jwt_token(token)
        
        # Extract customer information
        customer_id = claims['sub']
        customer_tier = claims.get('tier', 'retail')
        
        # Route based on customer tier
        cell_id = route_by_tier(customer_tier, customer_id)
        
        # Audit log the routing decision
        audit_log_routing(customer_id, cell_id, event)
        
        # Generate policy for API Gateway
        policy = generate_policy(claims, cell_id)
        
        return policy
        
    except Exception as e:
        # Log security event
        log_security_event(str(e), event)
        raise Exception('Unauthorized')

def route_by_tier(customer_tier, customer_id):
    """Route customers based on their tier"""
    if customer_tier == 'high_net_worth':
        return 'hnw-cell'
    elif customer_tier == 'corporate':
        return 'corp-cell'
    else:
        # Hash retail customers across multiple retail cells
        hash_value = hash(customer_id)
        cell_number = (hash_value % 3) + 1
        return f'retail-cell-{cell_number}'

def validate_jwt_token(token):
    """Validate JWT token with KMS"""
    # Decrypt signing key with KMS
    key_response = kms.decrypt(
        CiphertextBlob=base64.b64decode(ENCRYPTED_JWT_KEY)
    )
    
    signing_key = key_response['Plaintext']
    
    # Validate token
    claims = jwt.decode(
        token,
        signing_key,
        algorithms=['HS256'],
        options={'verify_exp': True}
    )
    
    return claims

def audit_log_routing(customer_id, cell_id, event):
    """Log routing decisions for audit"""
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'customer_id': customer_id,
        'cell_id': cell_id,
        'source_ip': event['requestContext']['identity']['sourceIp'],
        'user_agent': event['requestContext']['identity']['userAgent'],
        'request_id': event['requestContext']['requestId']
    }
    
    logs.put_log_events(
        logGroupName='/aws/lambda/financial-routing-audit',
        logStreamName=datetime.utcnow().strftime('%Y/%m/%d'),
        logEvents=[{
            'timestamp': int(datetime.utcnow().timestamp() * 1000),
            'message': json.dumps(log_entry)
        }]
    )
```

#### High Net Worth Cell (Enhanced Security)
```python
import boto3
import psycopg2
from cryptography.fernet import Fernet
import os

class HNWCellService:
    def __init__(self):
        self.cell_id = 'hnw-cell'
        self.kms = boto3.client('kms')
        
        # Dedicated database connection
        self.db = psycopg2.connect(
            host=os.environ['HNW_DB_HOST'],
            database='hnw_banking',
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            sslmode='require'
        )
        
        # Cell-specific encryption key
        self.encryption_key = self.get_cell_encryption_key()
    
    def get_cell_encryption_key(self):
        """Get cell-specific encryption key from KMS"""
        response = self.kms.decrypt(
            CiphertextBlob=base64.b64decode(os.environ['HNW_CELL_KEY'])
        )
        return Fernet(base64.urlsafe_b64encode(response['Plaintext'][:32]))
    
    def get_account_balance(self, customer_id, account_id):
        """Get encrypted account balance"""
        cursor = self.db.cursor()
        
        cursor.execute(
            """SELECT encrypted_balance, last_updated 
               FROM accounts 
               WHERE customer_id = %s AND account_id = %s""",
            (customer_id, account_id)
        )
        
        result = cursor.fetchone()
        if not result:
            return None
        
        # Decrypt balance
        encrypted_balance, last_updated = result
        decrypted_balance = self.encryption_key.decrypt(encrypted_balance)
        
        return {
            'balance': float(decrypted_balance.decode()),
            'last_updated': last_updated.isoformat(),
            'cell_id': self.cell_id
        }
    
    def create_transaction(self, customer_id, transaction_data):
        """Create encrypted transaction record"""
        cursor = self.db.cursor()
        
        # Encrypt sensitive data
        encrypted_amount = self.encryption_key.encrypt(
            str(transaction_data['amount']).encode()
        )
        
        cursor.execute(
            """INSERT INTO transactions 
               (customer_id, account_id, encrypted_amount, description, created_at)
               VALUES (%s, %s, %s, %s, NOW())
               RETURNING transaction_id""",
            (
                customer_id,
                transaction_data['account_id'],
                encrypted_amount,
                transaction_data['description']
            )
        )
        
        transaction_id = cursor.fetchone()[0]
        self.db.commit()
        
        # Audit log
        self.audit_transaction(customer_id, transaction_id, transaction_data)
        
        return {'transaction_id': transaction_id, 'status': 'created'}
```

## Best Practices for Reference Architectures

### Security Considerations
- **Encryption at rest and in transit** - All data encrypted with cell-specific keys
- **Network isolation** - Separate VPCs or subnets per cell
- **Access controls** - Cell-specific IAM roles and policies
- **Audit logging** - Comprehensive audit trails per cell

### Scalability Patterns
- **Auto-scaling** - Cell-specific auto-scaling groups
- **Load balancing** - Distribute load within cells
- **Caching strategies** - Cell-specific caching layers
- **Database scaling** - Read replicas and sharding within cells

### Operational Excellence
- **Monitoring** - Cell-aware metrics and dashboards
- **Alerting** - Cell-specific alert thresholds
- **Deployment** - Automated cell deployment pipelines
- **Disaster recovery** - Cell-specific backup and recovery procedures

### Cost Optimization
- **Resource right-sizing** - Optimize resources per cell
- **Reserved capacity** - Use reserved instances for predictable workloads
- **Spot instances** - Use spot instances for non-critical cell components
- **Storage optimization** - Lifecycle policies for cell data