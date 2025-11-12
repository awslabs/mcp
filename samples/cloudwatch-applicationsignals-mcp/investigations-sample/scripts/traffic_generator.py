#!/usr/bin/env python3
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
"""Traffic generator for Document Manager API.

Simulates multiple customers using the service concurrently.
"""

import concurrent.futures
import io
import random
import requests
import time
from datetime import datetime
from typing import Dict, List


API_BASE = 'http://localhost:8000'

# Sample data
DOCUMENT_TITLES = [
    'Q1 2024 Financial Report',
    'Project Proposal - Cloud Migration',
    'Employee Handbook 2024',
    'Product Roadmap',
    'Meeting Notes - Strategy Session',
    'Architecture Design Document',
    'User Research Findings',
    'Marketing Campaign Brief',
    'Technical Specification',
    'Budget Allocation Spreadsheet',
]

TAGS_POOL = [
    ['q1'],
    ['infrastructure'],
    ['strategy'],
    ['technical'],
    ['finance', '2024'],
    ['strategy', 'infrastructure'],
    ['employee', 'planning'],
    ['ux', 'design'],
    ['finance', 'q1', '2024'],
    ['project', 'cloud', 'infrastructure'],
    ['hr', 'policy', 'employee'],
    ['product', 'roadmap', 'planning'],
    ['meeting', 'strategy', 'notes'],
    ['architecture', 'technical', 'design'],
    ['research', 'user', 'ux'],
    ['marketing', 'campaign', '2024'],
    ['technical', 'spec', 'documentation'],
    ['finance', 'budget', 'planning'],
    [
        '2024',
        'architecture',
        'budget',
        'campaign',
        'cloud',
        'design',
        'documentation',
        'employee',
        'finance',
        'hr',
        'infrastructure',
        'marketing',
        'meeting',
        'notes',
        'planning',
        'policy',
        'product',
        'project',
        'q1',
        'research',
        'roadmap',
        'spec',
        'strategy',
        'technical',
        'user',
        'ux',
    ],
]

FILE_TYPES = [
    ('application/pdf', '.pdf'),
    ('text/plain', '.txt'),
    ('image/jpeg', '.jpg'),
]


def generate_file_content(file_type: str) -> bytes:
    """Generate random file content - sometimes large to trigger scanning bug."""
    # 1% chance: large multiplier (15000-30000) = 250-500KB
    # 99% chance: small multiplier (50-100) = 2-5KB
    multiplier = (
        random.randint(15000, 30000) if random.random() < 0.01 else random.randint(50, 100)
    )

    if file_type == 'application/pdf':
        return (
            b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n'
            + b'Sample content ' * multiplier
        )
    elif file_type == 'text/plain':
        return f'Sample document content generated at {datetime.now()}\n'.encode() * multiplier
    elif file_type == 'image/jpeg':
        return b'\xff\xd8\xff\xe0\x00\x10JFIF' + b'\x00' * multiplier
    return b'Generic content'


class Customer:
    """Simulates a customer interacting with the API."""

    def __init__(self, customer_id: int):
        """Initialize Customer with ID and tracking."""
        self.customer_id = customer_id
        self.uploaded_docs: List[str] = []
        self.name = f'Customer-{customer_id}'

    def upload_document(self) -> bool:
        """Upload a random document."""
        title = random.choice(DOCUMENT_TITLES)
        tags = ','.join(random.choice(TAGS_POOL))
        content_type, extension = random.choice(FILE_TYPES)

        filename = f'doc_{self.customer_id}_{int(time.time())}{extension}'
        file_content = generate_file_content(content_type)

        try:
            response = requests.post(
                f'{API_BASE}/documents',
                files={'file': (filename, io.BytesIO(file_content), content_type)},
                data={'title': title, 'tags': tags},
                timeout=10,
            )

            if response.status_code == 201:
                doc_id = response.json()['document_id']
                self.uploaded_docs.append(doc_id)
                print(f"✓ {self.name}: Uploaded '{title}' (ID: {doc_id[:8]}...)")
                return True
            else:
                print(f'✗ {self.name}: Upload failed - {response.status_code}')
                return False
        except Exception as e:
            print(f'✗ {self.name}: Upload error - {str(e)}')
            return False

    def get_document(self) -> bool:
        """Retrieve a random document."""
        if not self.uploaded_docs:
            return False

        # 10% chance: use very long document ID to trigger retry bug (exceeds DynamoDB 2KB limit)
        if random.random() < 0.1:
            doc_id = 'x' * 3000  # 3KB - exceeds DynamoDB key size limit
        else:
            doc_id = random.choice(self.uploaded_docs)

        try:
            response = requests.get(f'{API_BASE}/documents/{doc_id}', timeout=10)
            if response.status_code == 200:
                doc = response.json()
                print(f"✓ {self.name}: Retrieved '{doc['title']}'")
                return True
            else:
                print(f'✗ {self.name}: Get failed - {response.status_code}')
                return False
        except Exception as e:
            print(f'✗ {self.name}: Get error - {str(e)}')
            return False

    def list_documents(self) -> bool:
        """List documents with optional filters."""
        params = {}

        # Randomly apply filters
        if random.random() > 0.5:
            # Use all tags from a randomly selected tag set
            tag_set = random.choice(TAGS_POOL)
            params['tags'] = tag_set

        try:
            response = requests.get(f'{API_BASE}/documents', params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                filter_info = f' (tags={",".join(params["tags"])})' if params else ''
                print(f'✓ {self.name}: Listed {data["total"]} documents{filter_info}')
                return True
            else:
                print(f'✗ {self.name}: List failed - {response.status_code}')
                return False
        except Exception as e:
            print(f'✗ {self.name}: List error - {str(e)}')
            return False

    def download_document(self) -> bool:
        """Get download URL for a document."""
        if not self.uploaded_docs:
            return False

        doc_id = random.choice(self.uploaded_docs)

        try:
            response = requests.get(f'{API_BASE}/documents/{doc_id}/download', timeout=5)
            if response.status_code == 200:
                print(f'✓ {self.name}: Got download URL for doc {doc_id[:8]}...')
                return True
            else:
                print(f'✗ {self.name}: Download URL failed - {response.status_code}')
                return False
        except Exception as e:
            print(f'✗ {self.name}: Download URL error - {str(e)}')
            return False

    def perform_random_action(self, distribution=None):
        """Perform a random API action."""
        if distribution is None:
            distribution = [1, 33, 33, 33]  # Default: upload, get, list, download

        actions = [
            (self.upload_document, distribution[0] / 100),
            (self.get_document, distribution[1] / 100),
            (self.list_documents, distribution[2] / 100),
            (self.download_document, distribution[3] / 100),
        ]

        # Weighted random choice
        rand = random.random()
        cumulative = 0
        for action, weight in actions:
            cumulative += weight
            if rand <= cumulative:
                action()
                break

        # Random delay between actions (0.5-3 seconds)
        time.sleep(random.uniform(0.5, 3.0))


def customer_session(customer_id: int, duration_seconds: int, stats: Dict, distribution=None):
    """Run a customer session for the specified duration."""
    customer = Customer(customer_id)
    start_time = time.time()
    actions = 0

    # Start with some uploads
    for _ in range(random.randint(50, 100)):
        customer.upload_document()
        time.sleep(0.1)

    # Perform random actions
    while time.time() - start_time < duration_seconds:
        customer.perform_random_action(distribution)
        actions += 1

    stats[customer_id] = {'actions': actions, 'documents': len(customer.uploaded_docs)}


def run_traffic_generator(num_customers: int = 5, duration_seconds: int = 30, distribution=None):
    """Run traffic generator with multiple concurrent customers."""
    print('\n' + '=' * 60)
    print('Document Manager Traffic Generator')
    print('=' * 60)
    print(f'Customers: {num_customers}')
    print(f'Duration: {duration_seconds}s')
    print(f'API: {API_BASE}')
    print('=' * 60 + '\n')

    # Check if API is available
    try:
        response = requests.get(f'{API_BASE}/health', timeout=5)
        if response.status_code != 200:
            print('❌ API is not responding. Is it running?')
            print('   Run: ./manage.sh setup')
            return
    except Exception as e:
        print(f'❌ Cannot connect to API: {e}')
        print('   Run: ./manage.sh setup')
        return

    print('✓ API is ready\n')

    # Run customer sessions concurrently
    stats = {}
    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_customers) as executor:
        futures = [
            executor.submit(customer_session, i, duration_seconds, stats, distribution)
            for i in range(1, num_customers + 1)
        ]
        concurrent.futures.wait(futures)

    elapsed = time.time() - start_time

    # Print statistics
    print('\n' + '=' * 60)
    print('Traffic Generation Complete')
    print('=' * 60)
    print(f'Duration: {elapsed:.1f}s')
    print(f'Customers: {num_customers}')

    total_actions = sum(s['actions'] for s in stats.values())
    total_docs = sum(s['documents'] for s in stats.values())

    print(f'Total Actions: {total_actions}')
    print(f'Total Documents: {total_docs}')
    print(f'Actions/sec: {total_actions / elapsed:.1f}')
    print('=' * 60 + '\n')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Generate traffic for Document Manager API')
    parser.add_argument(
        '-c',
        '--customers',
        type=int,
        default=5,
        help='Number of concurrent customers (default: 5)',
    )
    parser.add_argument(
        '-d', '--duration', type=int, default=30, help='Duration in seconds (default: 30)'
    )
    parser.add_argument(
        '-u',
        '--url',
        type=str,
        default='http://localhost:8000',
        help='API base URL (default: http://localhost:8000)',
    )
    parser.add_argument(
        '-a',
        '--actions',
        type=int,
        nargs=4,
        metavar=('UPLOAD', 'GET', 'LIST', 'DOWNLOAD'),
        help='Action distribution percentages (must sum to 100, e.g., 2 33 33 32)',
    )

    args = parser.parse_args()

    # Validate action distribution
    distribution = None
    if args.actions:
        if sum(args.actions) != 100:
            parser.error(f'Action percentages must sum to 100, got {sum(args.actions)}')
        distribution = args.actions
    API_BASE = args.url

    try:
        run_traffic_generator(args.customers, args.duration, distribution)
    except KeyboardInterrupt:
        print('\n\n⚠️  Traffic generation interrupted by user')
