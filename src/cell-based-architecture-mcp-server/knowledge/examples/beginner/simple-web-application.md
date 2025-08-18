# Beginner Example: Simple Web Application with Cell-Based Architecture

## Overview

This example demonstrates how to implement a basic cell-based architecture for a simple web application. It's designed for beginners who are new to cell-based concepts and want to understand the fundamentals.

## Application Description

We'll build a simple customer management web application with the following features:
- Customer registration and login
- Customer profile management
- Basic CRUD operations
- Simple reporting

## Traditional vs Cell-Based Approach

### Traditional Monolithic Approach
```
┌─────────────────────────────────────┐
│            Load Balancer            │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│         Web Application             │
│  • All customers in one instance    │
│  • Single database                  │
│  • Shared resources                 │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│         Single Database             │
│  • All customer data together       │
└─────────────────────────────────────┘
```

### Cell-Based Approach
```
┌─────────────────────────────────────┐
│            Load Balancer            │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│           Cell Router               │
│  • Routes by customer ID            │
│  • Simple hash-based routing        │
└─────┬───────────┬───────────────────┘
      │           │
┌─────▼─────┐ ┌───▼─────┐ ┌───────────┐
│  Cell A   │ │ Cell B  │ │  Cell C   │
│ Web App   │ │ Web App │ │ Web App   │
│ Database  │ │Database │ │ Database  │
└───────────┘ └─────────┘ └───────────┘
```

## Implementation Steps

### Step 1: Design the Cell Router

The cell router is the entry point that decides which cell should handle each request.

```python
# cell_router.py
import hashlib
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuration
CELL_ENDPOINTS = {
    'cell-a': 'http://cell-a.internal:8080',
    'cell-b': 'http://cell-b.internal:8080',
    'cell-c': 'http://cell-c.internal:8080'
}

def route_customer_to_cell(customer_id):
    """Simple hash-based routing to determine which cell handles the customer"""
    # Use MD5 hash for simplicity (in production, consider more robust methods)
    hash_value = int(hashlib.md5(customer_id.encode()).hexdigest(), 16)
    cell_number = hash_value % len(CELL_ENDPOINTS)
    cell_names = list(CELL_ENDPOINTS.keys())
    return cell_names[cell_number]

@app.route('/api/customers/<customer_id>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def route_customer_request(customer_id):
    """Route customer requests to appropriate cell"""
    
    # Determine which cell should handle this customer
    target_cell = route_customer_to_cell(customer_id)
    target_url = CELL_ENDPOINTS[target_cell]
    
    # Forward the request to the appropriate cell
    try:
        response = requests.request(
            method=request.method,
            url=f"{target_url}/api/customers/{customer_id}",
            headers=dict(request.headers),
            data=request.get_data(),
            params=request.args
        )
        
        return response.content, response.status_code, response.headers.items()
        
    except requests.RequestException as e:
        return jsonify({'error': 'Cell unavailable', 'details': str(e)}), 503

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'cell-router'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

### Step 2: Implement Individual Cells

Each cell is a complete, independent instance of the application.

```python
# cell_application.py
import os
import sqlite3
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Cell configuration
CELL_ID = os.environ.get('CELL_ID', 'cell-unknown')
DATABASE_PATH = f'/data/{CELL_ID}.db'

def init_database():
    """Initialize the cell-specific database"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            created_at TEXT NOT NULL,
            cell_id TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Get database connection for this cell"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/customers/<customer_id>', methods=['GET'])
def get_customer(customer_id):
    """Get customer information"""
    
    conn = get_db_connection()
    customer = conn.execute(
        'SELECT * FROM customers WHERE customer_id = ?',
        (customer_id,)
    ).fetchone()
    conn.close()
    
    if customer:
        return jsonify({
            'customer_id': customer['customer_id'],
            'name': customer['name'],
            'email': customer['email'],
            'created_at': customer['created_at'],
            'cell_id': customer['cell_id']
        })
    else:
        return jsonify({'error': 'Customer not found'}), 404

@app.route('/api/customers/<customer_id>', methods=['POST'])
def create_customer(customer_id):
    """Create a new customer"""
    
    data = request.get_json()
    
    if not data or 'name' not in data or 'email' not in data:
        return jsonify({'error': 'Name and email are required'}), 400
    
    conn = get_db_connection()
    
    try:
        conn.execute(
            'INSERT INTO customers (customer_id, name, email, created_at, cell_id) VALUES (?, ?, ?, ?, ?)',
            (customer_id, data['name'], data['email'], datetime.utcnow().isoformat(), CELL_ID)
        )
        conn.commit()
        conn.close()
        
        return jsonify({
            'customer_id': customer_id,
            'name': data['name'],
            'email': data['email'],
            'cell_id': CELL_ID,
            'status': 'created'
        }), 201
        
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'Customer already exists'}), 409

@app.route('/api/customers/<customer_id>', methods=['PUT'])
def update_customer(customer_id):
    """Update customer information"""
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    conn = get_db_connection()
    
    # Check if customer exists
    existing = conn.execute(
        'SELECT customer_id FROM customers WHERE customer_id = ?',
        (customer_id,)
    ).fetchone()
    
    if not existing:
        conn.close()
        return jsonify({'error': 'Customer not found'}), 404
    
    # Update customer
    update_fields = []
    update_values = []
    
    if 'name' in data:
        update_fields.append('name = ?')
        update_values.append(data['name'])
    
    if 'email' in data:
        update_fields.append('email = ?')
        update_values.append(data['email'])
    
    if update_fields:
        update_values.append(customer_id)
        conn.execute(
            f'UPDATE customers SET {", ".join(update_fields)} WHERE customer_id = ?',
            update_values
        )
        conn.commit()
    
    # Get updated customer
    updated_customer = conn.execute(
        'SELECT * FROM customers WHERE customer_id = ?',
        (customer_id,)
    ).fetchone()
    
    conn.close()
    
    return jsonify({
        'customer_id': updated_customer['customer_id'],
        'name': updated_customer['name'],
        'email': updated_customer['email'],
        'created_at': updated_customer['created_at'],
        'cell_id': updated_customer['cell_id']
    })

@app.route('/health')
def health_check():
    """Health check endpoint"""
    
    # Check database connectivity
    try:
        conn = get_db_connection()
        conn.execute('SELECT 1')
        conn.close()
        db_status = 'healthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'
    
    return jsonify({
        'status': 'healthy' if db_status == 'healthy' else 'unhealthy',
        'cell_id': CELL_ID,
        'database': db_status
    })

@app.route('/metrics')
def metrics():
    """Basic metrics endpoint"""
    
    conn = get_db_connection()
    customer_count = conn.execute('SELECT COUNT(*) as count FROM customers').fetchone()['count']
    conn.close()
    
    return jsonify({
        'cell_id': CELL_ID,
        'customer_count': customer_count,
        'timestamp': datetime.utcnow().isoformat()
    })

if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=8080)
```

### Step 3: Docker Configuration

Create Docker containers for easy deployment:

```dockerfile
# Dockerfile.router
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY cell_router.py .

EXPOSE 8000

CMD ["python", "cell_router.py"]
```

```dockerfile
# Dockerfile.cell
FROM python:3.9-slim

WORKDIR /app

# Create data directory for SQLite databases
RUN mkdir -p /data

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY cell_application.py .

EXPOSE 8080

CMD ["python", "cell_application.py"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  cell-router:
    build:
      context: .
      dockerfile: Dockerfile.router
    ports:
      - "8000:8000"
    depends_on:
      - cell-a
      - cell-b
      - cell-c
    networks:
      - cell-network

  cell-a:
    build:
      context: .
      dockerfile: Dockerfile.cell
    environment:
      - CELL_ID=cell-a
    volumes:
      - cell-a-data:/data
    networks:
      - cell-network

  cell-b:
    build:
      context: .
      dockerfile: Dockerfile.cell
    environment:
      - CELL_ID=cell-b
    volumes:
      - cell-b-data:/data
    networks:
      - cell-network

  cell-c:
    build:
      context: .
      dockerfile: Dockerfile.cell
    environment:
      - CELL_ID=cell-c
    volumes:
      - cell-c-data:/data
    networks:
      - cell-network

volumes:
  cell-a-data:
  cell-b-data:
  cell-c-data:

networks:
  cell-network:
    driver: bridge
```

### Step 4: Testing the Implementation

Create simple tests to verify the cell-based architecture works:

```python
# test_cell_architecture.py
import requests
import json
import time

# Configuration
ROUTER_URL = 'http://localhost:8000'

def test_customer_operations():
    """Test basic customer operations across cells"""
    
    # Test data
    customers = [
        {'id': 'customer-001', 'name': 'Alice Johnson', 'email': 'alice@example.com'},
        {'id': 'customer-002', 'name': 'Bob Smith', 'email': 'bob@example.com'},
        {'id': 'customer-003', 'name': 'Carol Davis', 'email': 'carol@example.com'},
    ]
    
    print("Testing Cell-Based Customer Management System")
    print("=" * 50)
    
    # Create customers
    for customer in customers:
        print(f"\nCreating customer: {customer['id']}")
        
        response = requests.post(
            f"{ROUTER_URL}/api/customers/{customer['id']}",
            json={'name': customer['name'], 'email': customer['email']}
        )
        
        if response.status_code == 201:
            result = response.json()
            print(f"✓ Customer created in {result['cell_id']}")
        else:
            print(f"✗ Failed to create customer: {response.text}")
    
    # Retrieve customers
    print("\n" + "=" * 50)
    print("Retrieving customers:")
    
    for customer in customers:
        print(f"\nRetrieving customer: {customer['id']}")
        
        response = requests.get(f"{ROUTER_URL}/api/customers/{customer['id']}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Customer found in {result['cell_id']}: {result['name']}")
        else:
            print(f"✗ Failed to retrieve customer: {response.text}")
    
    # Update a customer
    print("\n" + "=" * 50)
    print("Updating customer:")
    
    update_data = {'name': 'Alice Johnson-Updated', 'email': 'alice.updated@example.com'}
    response = requests.put(
        f"{ROUTER_URL}/api/customers/customer-001",
        json=update_data
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Customer updated in {result['cell_id']}: {result['name']}")
    else:
        print(f"✗ Failed to update customer: {response.text}")

def test_cell_isolation():
    """Test that cells are properly isolated"""
    
    print("\n" + "=" * 50)
    print("Testing Cell Isolation:")
    
    # Create customers and track which cells they go to
    cell_distribution = {}
    
    for i in range(10):
        customer_id = f"test-customer-{i:03d}"
        
        response = requests.post(
            f"{ROUTER_URL}/api/customers/{customer_id}",
            json={'name': f'Test Customer {i}', 'email': f'test{i}@example.com'}
        )
        
        if response.status_code == 201:
            result = response.json()
            cell_id = result['cell_id']
            
            if cell_id not in cell_distribution:
                cell_distribution[cell_id] = 0
            cell_distribution[cell_id] += 1
    
    print("\nCustomer distribution across cells:")
    for cell_id, count in cell_distribution.items():
        print(f"  {cell_id}: {count} customers")
    
    # Verify customers are consistently routed to the same cell
    print("\nTesting routing consistency:")
    for i in range(3):
        customer_id = "test-customer-001"
        response = requests.get(f"{ROUTER_URL}/api/customers/{customer_id}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"  Attempt {i+1}: Customer routed to {result['cell_id']}")

def test_cell_health():
    """Test cell health endpoints"""
    
    print("\n" + "=" * 50)
    print("Testing Cell Health:")
    
    # Test router health
    response = requests.get(f"{ROUTER_URL}/health")
    if response.status_code == 200:
        print("✓ Router is healthy")
    else:
        print("✗ Router health check failed")
    
    # We can't directly access individual cells in this setup,
    # but in a real deployment you would test each cell's health endpoint

if __name__ == '__main__':
    print("Starting Cell-Based Architecture Tests")
    print("Make sure the system is running with: docker-compose up")
    
    # Wait a moment for services to start
    time.sleep(2)
    
    try:
        test_customer_operations()
        test_cell_isolation()
        test_cell_health()
        
        print("\n" + "=" * 50)
        print("All tests completed!")
        
    except requests.ConnectionError:
        print("Error: Could not connect to the system. Make sure it's running.")
    except Exception as e:
        print(f"Error during testing: {str(e)}")
```

## Running the Example

### Prerequisites
- Docker and Docker Compose installed
- Python 3.9+ (for testing)

### Steps to Run

1. **Create the project structure:**
```bash
mkdir cell-based-web-app
cd cell-based-web-app
```

2. **Create the requirements file:**
```txt
# requirements.txt
Flask==2.3.3
requests==2.31.0
```

3. **Save all the Python files** (cell_router.py, cell_application.py, test_cell_architecture.py)

4. **Save the Docker files** (Dockerfile.router, Dockerfile.cell, docker-compose.yml)

5. **Start the system:**
```bash
docker-compose up --build
```

6. **Run the tests** (in a new terminal):
```bash
pip install requests
python test_cell_architecture.py
```

## Key Learning Points

### 1. Cell Isolation
- Each cell has its own database and application instance
- Customers are consistently routed to the same cell
- Failure in one cell doesn't affect others

### 2. Simple Routing
- Hash-based routing ensures even distribution
- Stateless routing is simple and reliable
- Customer ID determines cell assignment

### 3. Independent Scaling
- Each cell can be scaled independently
- New cells can be added easily
- Load is distributed automatically

### 4. Operational Benefits
- Easy to test individual cells
- Clear blast radius for issues
- Simple monitoring per cell

## Next Steps

After understanding this basic example, you can:

1. **Add monitoring** - Implement health checks and metrics
2. **Improve routing** - Add more sophisticated routing logic
3. **Add persistence** - Use proper databases instead of SQLite
4. **Implement migration** - Add customer migration between cells
5. **Add security** - Implement authentication and authorization
6. **Scale up** - Deploy to cloud infrastructure

This example provides a solid foundation for understanding cell-based architecture principles in a simple, practical way.