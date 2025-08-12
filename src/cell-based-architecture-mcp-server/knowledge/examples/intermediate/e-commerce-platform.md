# Intermediate Example: E-Commerce Platform with Cell-Based Architecture

## Overview

This intermediate example demonstrates a more complex cell-based architecture for an e-commerce platform. It includes multiple services, data relationships, and advanced patterns like event-driven communication and cell migration.

## System Requirements

The e-commerce platform includes:
- Customer management and authentication
- Product catalog and inventory
- Shopping cart and order processing
- Payment processing
- Order fulfillment and shipping
- Customer support and reviews

## Architecture Design

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CloudFront CDN                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              Application Load Balancer                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              API Gateway (Cell Router)                     │
│  • Customer-based routing                                  │
│  • Rate limiting per cell                                  │
│  • Authentication integration                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
┌───────▼──────┐ ┌────▼─────┐ ┌────▼─────┐
│   Cell A     │ │  Cell B  │ │  Cell C  │
│              │ │          │ │          │
│ • ECS Tasks  │ │• ECS Tasks│ │• ECS Tasks│
│ • RDS        │ │• RDS     │ │• RDS     │
│ • ElastiCache│ │• ElastiC │ │• ElastiC │
│ • SQS Queues │ │• SQS Q   │ │• SQS Q   │
│ • S3 Prefix  │ │• S3 Prefix│ │• S3 Prefix│
└──────────────┘ └──────────┘ └──────────┘
```

### Cell Internal Architecture

Each cell contains:
- **Web Service** - REST API for customer interactions
- **Order Service** - Order processing and management
- **Inventory Service** - Product availability and reservations
- **Payment Service** - Payment processing
- **Notification Service** - Email and SMS notifications

## Implementation

### Cell Router with Advanced Features

```python
# advanced_cell_router.py
import json
import hashlib
import boto3
from flask import Flask, request, jsonify
from functools import wraps
import jwt
import time
from collections import defaultdict

app = Flask(__name__)

class AdvancedCellRouter:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.cloudwatch = boto3.client('cloudwatch')
        self.routing_table = self.dynamodb.Table('CustomerCellMapping')
        
        # Cell configuration
        self.cells = {
            'cell-a': {
                'endpoint': 'http://cell-a-alb.internal',
                'capacity': 1000,
                'current_load': 0,
                'health_status': 'healthy'
            },
            'cell-b': {
                'endpoint': 'http://cell-b-alb.internal',
                'capacity': 1000,
                'current_load': 0,
                'health_status': 'healthy'
            },
            'cell-c': {
                'endpoint': 'http://cell-c-alb.internal',
                'capacity': 1000,
                'current_load': 0,
                'health_status': 'healthy'
            }
        }
        
        # Rate limiting
        self.rate_limits = defaultdict(list)
        
    def authenticate_request(self, token):
        """Authenticate JWT token and extract customer info"""
        try:
            payload = jwt.decode(token, 'your-secret-key', algorithms=['HS256'])
            return payload
        except jwt.InvalidTokenError:
            return None
    
    def get_customer_cell(self, customer_id):
        """Get cell assignment for customer with fallback"""
        try:
            # Try to get from DynamoDB first
            response = self.routing_table.get_item(
                Key={'customer_id': customer_id}
            )
            
            if 'Item' in response:
                return response['Item']['cell_id']
            
        except Exception as e:
            print(f"DynamoDB lookup failed: {e}")
        
        # Fallback to hash-based routing
        return self.hash_based_routing(customer_id)
    
    def hash_based_routing(self, customer_id):
        """Fallback hash-based routing"""
        hash_value = int(hashlib.md5(customer_id.encode()).hexdigest(), 16)
        healthy_cells = [
            cell_id for cell_id, config in self.cells.items()
            if config['health_status'] == 'healthy'
        ]
        
        if not healthy_cells:
            raise Exception("No healthy cells available")
        
        cell_index = hash_value % len(healthy_cells)
        return healthy_cells[cell_index]
    
    def check_rate_limit(self, customer_id, limit=100, window=60):
        """Check rate limiting for customer"""
        now = time.time()
        
        # Clean old entries
        self.rate_limits[customer_id] = [
            timestamp for timestamp in self.rate_limits[customer_id]
            if now - timestamp < window
        ]
        
        # Check limit
        if len(self.rate_limits[customer_id]) >= limit:
            return False
        
        # Add current request
        self.rate_limits[customer_id].append(now)
        return True
    
    def route_request(self, customer_id, path, method, headers, data):
        """Route request to appropriate cell"""
        
        # Get target cell
        target_cell = self.get_customer_cell(customer_id)
        target_endpoint = self.cells[target_cell]['endpoint']
        
        # Update load metrics
        self.cells[target_cell]['current_load'] += 1
        
        try:
            # Forward request
            import requests
            response = requests.request(
                method=method,
                url=f"{target_endpoint}{path}",
                headers=headers,
                data=data,
                timeout=30
            )
            
            # Emit metrics
            self.emit_routing_metrics(customer_id, target_cell, response.status_code)
            
            return response
            
        except Exception as e:
            # Handle cell failure
            self.handle_cell_failure(target_cell, str(e))
            raise
        
        finally:
            # Update load metrics
            self.cells[target_cell]['current_load'] -= 1
    
    def emit_routing_metrics(self, customer_id, cell_id, status_code):
        """Emit routing metrics to CloudWatch"""
        try:
            self.cloudwatch.put_metric_data(
                Namespace='ECommerce/CellRouter',
                MetricData=[
                    {
                        'MetricName': 'RequestCount',
                        'Dimensions': [
                            {'Name': 'CellId', 'Value': cell_id}
                        ],
                        'Value': 1,
                        'Unit': 'Count'
                    },
                    {
                        'MetricName': 'ResponseCode',
                        'Dimensions': [
                            {'Name': 'CellId', 'Value': cell_id},
                            {'Name': 'StatusCode', 'Value': str(status_code)}
                        ],
                        'Value': 1,
                        'Unit': 'Count'
                    }
                ]
            )
        except Exception as e:
            print(f"Failed to emit metrics: {e}")

# Initialize router
router = AdvancedCellRouter()

def require_auth(f):
    """Authentication decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'No authorization token provided'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        user_info = router.authenticate_request(token)
        if not user_info:
            return jsonify({'error': 'Invalid token'}), 401
        
        request.user_info = user_info
        return f(*args, **kwargs)
    
    return decorated_function

@app.route('/api/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@require_auth
def route_api_request(path):
    """Route API requests to appropriate cell"""
    
    customer_id = request.user_info.get('customer_id')
    if not customer_id:
        return jsonify({'error': 'Customer ID not found in token'}), 400
    
    # Check rate limiting
    if not router.check_rate_limit(customer_id):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    
    try:
        response = router.route_request(
            customer_id=customer_id,
            path=f"/api/{path}",
            method=request.method,
            headers=dict(request.headers),
            data=request.get_data()
        )
        
        return response.content, response.status_code, response.headers.items()
        
    except Exception as e:
        return jsonify({'error': 'Service unavailable', 'details': str(e)}), 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

### Cell Application with Microservices

```python
# cell_application.py
import os
import json
import boto3
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import redis
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid

app = Flask(__name__)

class CellApplication:
    def __init__(self):
        self.cell_id = os.environ.get('CELL_ID', 'cell-unknown')
        
        # Database connection
        self.db_config = {
            'host': os.environ.get('DB_HOST'),
            'database': f'ecommerce_{self.cell_id.replace("-", "_")}',
            'user': os.environ.get('DB_USER'),
            'password': os.environ.get('DB_PASSWORD')
        }
        
        # Redis cache
        self.cache = redis.Redis(
            host=os.environ.get('REDIS_HOST'),
            port=6379,
            db=0,
            decode_responses=True
        )
        
        # SQS for async processing
        self.sqs = boto3.client('sqs')
        self.order_queue_url = os.environ.get('ORDER_QUEUE_URL')
        
        # S3 for file storage
        self.s3 = boto3.client('s3')
        self.bucket_name = f'ecommerce-{self.cell_id}'
        
        self.init_database()
    
    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)
    
    def init_database(self):
        """Initialize database schema"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Customers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                customer_id VARCHAR(50) PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                address JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cell_id VARCHAR(50) NOT NULL
            )
        ''')
        
        # Products table (replicated in each cell)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                product_id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                price DECIMAL(10,2) NOT NULL,
                inventory_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Orders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                order_id VARCHAR(50) PRIMARY KEY,
                customer_id VARCHAR(50) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                total_amount DECIMAL(10,2) NOT NULL,
                items JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cell_id VARCHAR(50) NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
            )
        ''')
        
        # Shopping cart table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shopping_carts (
                customer_id VARCHAR(50) PRIMARY KEY,
                items JSONB NOT NULL DEFAULT '[]',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
            )
        ''')
        
        conn.commit()
        conn.close()

# Initialize cell application
cell_app = CellApplication()

# Customer Management Endpoints
@app.route('/api/customers/<customer_id>', methods=['GET'])
def get_customer(customer_id):
    """Get customer information"""
    
    # Try cache first
    cached_customer = cell_app.cache.get(f"customer:{customer_id}")
    if cached_customer:
        return jsonify(json.loads(cached_customer))
    
    # Query database
    conn = cell_app.get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute(
        'SELECT * FROM customers WHERE customer_id = %s',
        (customer_id,)
    )
    
    customer = cursor.fetchone()
    conn.close()
    
    if customer:
        customer_data = dict(customer)
        customer_data['created_at'] = customer_data['created_at'].isoformat()
        
        # Cache for 5 minutes
        cell_app.cache.setex(
            f"customer:{customer_id}",
            300,
            json.dumps(customer_data)
        )
        
        return jsonify(customer_data)
    else:
        return jsonify({'error': 'Customer not found'}), 404

@app.route('/api/customers/<customer_id>', methods=['PUT'])
def update_customer(customer_id):
    """Update customer information"""
    
    data = request.get_json()
    
    conn = cell_app.get_db_connection()
    cursor = conn.cursor()
    
    # Update customer
    update_fields = []
    update_values = []
    
    if 'name' in data:
        update_fields.append('name = %s')
        update_values.append(data['name'])
    
    if 'email' in data:
        update_fields.append('email = %s')
        update_values.append(data['email'])
    
    if 'address' in data:
        update_fields.append('address = %s')
        update_values.append(json.dumps(data['address']))
    
    if update_fields:
        update_fields.append('updated_at = CURRENT_TIMESTAMP')
        update_values.append(customer_id)
        
        cursor.execute(
            f'UPDATE customers SET {", ".join(update_fields)} WHERE customer_id = %s',
            update_values
        )
        conn.commit()
        
        # Invalidate cache
        cell_app.cache.delete(f"customer:{customer_id}")
    
    conn.close()
    
    return jsonify({'status': 'updated', 'customer_id': customer_id})

# Shopping Cart Endpoints
@app.route('/api/customers/<customer_id>/cart', methods=['GET'])
def get_cart(customer_id):
    """Get customer's shopping cart"""
    
    conn = cell_app.get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute(
        'SELECT items FROM shopping_carts WHERE customer_id = %s',
        (customer_id,)
    )
    
    cart = cursor.fetchone()
    conn.close()
    
    if cart:
        return jsonify({
            'customer_id': customer_id,
            'items': cart['items'],
            'cell_id': cell_app.cell_id
        })
    else:
        return jsonify({
            'customer_id': customer_id,
            'items': [],
            'cell_id': cell_app.cell_id
        })

@app.route('/api/customers/<customer_id>/cart/items', methods=['POST'])
def add_to_cart(customer_id):
    """Add item to shopping cart"""
    
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    
    if not product_id:
        return jsonify({'error': 'Product ID required'}), 400
    
    conn = cell_app.get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get current cart
    cursor.execute(
        'SELECT items FROM shopping_carts WHERE customer_id = %s',
        (customer_id,)
    )
    
    cart = cursor.fetchone()
    items = cart['items'] if cart else []
    
    # Add or update item
    item_found = False
    for item in items:
        if item['product_id'] == product_id:
            item['quantity'] += quantity
            item_found = True
            break
    
    if not item_found:
        items.append({
            'product_id': product_id,
            'quantity': quantity,
            'added_at': datetime.utcnow().isoformat()
        })
    
    # Update cart
    cursor.execute('''
        INSERT INTO shopping_carts (customer_id, items, updated_at)
        VALUES (%s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (customer_id)
        DO UPDATE SET items = %s, updated_at = CURRENT_TIMESTAMP
    ''', (customer_id, json.dumps(items), json.dumps(items)))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'status': 'added',
        'customer_id': customer_id,
        'items': items
    })

# Order Processing Endpoints
@app.route('/api/customers/<customer_id>/orders', methods=['POST'])
def create_order(customer_id):
    """Create order from shopping cart"""
    
    conn = cell_app.get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get cart items
    cursor.execute(
        'SELECT items FROM shopping_carts WHERE customer_id = %s',
        (customer_id,)
    )
    
    cart = cursor.fetchone()
    if not cart or not cart['items']:
        return jsonify({'error': 'Cart is empty'}), 400
    
    # Calculate total (simplified - in real system, get current prices)
    total_amount = 0
    for item in cart['items']:
        # Get product price
        cursor.execute(
            'SELECT price FROM products WHERE product_id = %s',
            (item['product_id'],)
        )
        product = cursor.fetchone()
        if product:
            total_amount += float(product['price']) * item['quantity']
    
    # Create order
    order_id = str(uuid.uuid4())
    
    cursor.execute('''
        INSERT INTO orders (order_id, customer_id, status, total_amount, items, cell_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    ''', (
        order_id,
        customer_id,
        'pending',
        total_amount,
        json.dumps(cart['items']),
        cell_app.cell_id
    ))
    
    # Clear cart
    cursor.execute(
        'DELETE FROM shopping_carts WHERE customer_id = %s',
        (customer_id,)
    )
    
    conn.commit()
    conn.close()
    
    # Send order to processing queue
    cell_app.sqs.send_message(
        QueueUrl=cell_app.order_queue_url,
        MessageBody=json.dumps({
            'order_id': order_id,
            'customer_id': customer_id,
            'cell_id': cell_app.cell_id,
            'action': 'process_order'
        })
    )
    
    return jsonify({
        'order_id': order_id,
        'status': 'pending',
        'total_amount': total_amount,
        'cell_id': cell_app.cell_id
    }), 201

@app.route('/api/customers/<customer_id>/orders', methods=['GET'])
def get_customer_orders(customer_id):
    """Get customer's orders"""
    
    conn = cell_app.get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute(
        'SELECT * FROM orders WHERE customer_id = %s ORDER BY created_at DESC',
        (customer_id,)
    )
    
    orders = cursor.fetchall()
    conn.close()
    
    # Convert to JSON serializable format
    orders_data = []
    for order in orders:
        order_data = dict(order)
        order_data['created_at'] = order_data['created_at'].isoformat()
        order_data['updated_at'] = order_data['updated_at'].isoformat()
        orders_data.append(order_data)
    
    return jsonify({
        'customer_id': customer_id,
        'orders': orders_data,
        'cell_id': cell_app.cell_id
    })

# Health and Metrics Endpoints
@app.route('/health')
def health_check():
    """Comprehensive health check"""
    
    health_status = {
        'cell_id': cell_app.cell_id,
        'status': 'healthy',
        'checks': {}
    }
    
    # Database check
    try:
        conn = cell_app.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        conn.close()
        health_status['checks']['database'] = 'healthy'
    except Exception as e:
        health_status['checks']['database'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Cache check
    try:
        cell_app.cache.ping()
        health_status['checks']['cache'] = 'healthy'
    except Exception as e:
        health_status['checks']['cache'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Queue check
    try:
        cell_app.sqs.get_queue_attributes(
            QueueUrl=cell_app.order_queue_url,
            AttributeNames=['ApproximateNumberOfMessages']
        )
        health_status['checks']['queue'] = 'healthy'
    except Exception as e:
        health_status['checks']['queue'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return jsonify(health_status), status_code

@app.route('/metrics')
def metrics():
    """Cell metrics endpoint"""
    
    conn = cell_app.get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get customer count
    cursor.execute('SELECT COUNT(*) as count FROM customers')
    customer_count = cursor.fetchone()['count']
    
    # Get order count (last 24 hours)
    cursor.execute('''
        SELECT COUNT(*) as count FROM orders 
        WHERE created_at > %s
    ''', (datetime.utcnow() - timedelta(hours=24),))
    recent_orders = cursor.fetchone()['count']
    
    # Get pending orders
    cursor.execute('SELECT COUNT(*) as count FROM orders WHERE status = %s', ('pending',))
    pending_orders = cursor.fetchone()['count']
    
    conn.close()
    
    return jsonify({
        'cell_id': cell_app.cell_id,
        'customer_count': customer_count,
        'recent_orders_24h': recent_orders,
        'pending_orders': pending_orders,
        'timestamp': datetime.utcnow().isoformat()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

## Key Features Demonstrated

### 1. Advanced Routing
- JWT-based authentication
- Rate limiting per customer
- Fallback routing mechanisms
- Health-aware routing

### 2. Microservices Architecture
- Separate services within each cell
- Event-driven communication via SQS
- Caching with Redis
- File storage with S3

### 3. Data Management
- PostgreSQL for transactional data
- JSON columns for flexible data
- Caching strategies
- Data consistency within cells

### 4. Operational Excellence
- Comprehensive health checks
- Metrics collection
- Error handling and fallbacks
- Monitoring integration

### 5. Scalability Patterns
- Horizontal scaling through cells
- Async processing with queues
- Caching for performance
- Database per cell isolation

This intermediate example shows how cell-based architecture can be applied to complex, real-world applications while maintaining the core principles of isolation, scalability, and resilience.