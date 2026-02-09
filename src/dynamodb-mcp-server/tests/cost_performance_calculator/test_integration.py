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

"""Integration test for cost_performance_calculator module.

Validates the full workflow: DataModel → CostCalculator → ReportGenerator → File I/O
by invoking run_cost_calculator and checking the written output.
"""

from awslabs.dynamodb_mcp_server.cost_performance_calculator.calculator_runner import (
    run_cost_calculator,
)
from awslabs.dynamodb_mcp_server.cost_performance_calculator.data_model import (
    GSI,
    DataModel,
    GetItemAccessPattern,
    PutItemAccessPattern,
    QueryAccessPattern,
    Table,
    UpdateItemAccessPattern,
)


def test_run_cost_calculator_produces_expected_report(tmp_path):
    """run_cost_calculator appends the correct report for a comprehensive scenario.

    Covers:
    - 3 tables: Users (with GSI), Orders (with 2 GSIs), Sessions (no GSI)
    - GetItem on base table (eventually consistent read)
    - Query on GSI (GSI read)
    - Query on base table (strongly consistent read)
    - PutItem with single GSI write amplification
    - PutItem with multiple GSI write amplification
    - UpdateItem with single GSI write amplification
    - GetItem on table without GSIs (Sessions)
    - PutItem without write amplification (Sessions)
    - Realistic item counts producing meaningful storage costs
    - Append behaviour: pre-existing file content is preserved
    """
    # Pre-populate the file to verify append behaviour
    file_path = tmp_path / 'dynamodb_data_model.md'
    file_path.write_text('# DynamoDB Data Model\n', encoding='utf-8')

    data_model = DataModel(
        table_list=[
            Table(
                name='Users',
                item_size_bytes=200,
                item_count=50_000_000,
                gsi_list=[
                    GSI(name='email-index', item_size_bytes=100, item_count=50_000_000),
                ],
            ),
            Table(
                name='Orders',
                item_size_bytes=500,
                item_count=200_000_000,
                gsi_list=[
                    GSI(name='status-index', item_size_bytes=150, item_count=200_000_000),
                    GSI(name='date-index', item_size_bytes=200, item_count=200_000_000),
                ],
            ),
            Table(
                name='Sessions',
                item_size_bytes=300,
                item_count=10_000_000,
                gsi_list=[],
            ),
        ],
        access_pattern_list=[
            GetItemAccessPattern(
                pattern='get-user-by-id',
                description='Get user by primary key',
                table='Users',
                rps=100,
                item_size_bytes=200,
                strongly_consistent=False,
            ),
            QueryAccessPattern(
                pattern='get-user-by-email',
                description='Query user by email GSI',
                table='Users',
                rps=50,
                item_size_bytes=100,
                item_count=1,
                gsi='email-index',
                strongly_consistent=False,
            ),
            PutItemAccessPattern(
                pattern='create-user',
                description='Create a new user',
                table='Users',
                rps=20,
                item_size_bytes=200,
                gsi_list=['email-index'],
            ),
            QueryAccessPattern(
                pattern='get-orders-by-user',
                description='Query orders by user',
                table='Orders',
                rps=80,
                item_size_bytes=500,
                item_count=5,
                strongly_consistent=True,
            ),
            QueryAccessPattern(
                pattern='get-orders-by-status',
                description='Query orders by status GSI',
                table='Orders',
                rps=60,
                item_size_bytes=150,
                item_count=10,
                gsi='status-index',
                strongly_consistent=False,
            ),
            PutItemAccessPattern(
                pattern='create-order',
                description='Create a new order',
                table='Orders',
                rps=40,
                item_size_bytes=500,
                gsi_list=['status-index', 'date-index'],
            ),
            UpdateItemAccessPattern(
                pattern='update-order-status',
                description='Update order status',
                table='Orders',
                rps=30,
                item_size_bytes=150,
                gsi_list=['status-index'],
            ),
            GetItemAccessPattern(
                pattern='get-session',
                description='Get session by ID',
                table='Sessions',
                rps=150,
                item_size_bytes=300,
                strongly_consistent=False,
            ),
            PutItemAccessPattern(
                pattern='create-session',
                description='Create a new session',
                table='Sessions',
                rps=200,
                item_size_bytes=300,
            ),
        ],
    )

    result = run_cost_calculator(data_model, workspace_dir=str(tmp_path))

    # Verify return message
    assert result == (
        'Cost analysis complete. Analyzed 9 access patterns '
        'across 3 tables. Report written to dynamodb_data_model.md'
    )

    # Verify file content: original content + appended report
    content = file_path.read_text(encoding='utf-8')

    expected = """\
# DynamoDB Data Model


## Cost Report

> **Disclaimer:** This report provides cost estimates based on DynamoDB on-demand pricing for the
> **US East (N. Virginia) / us-east-1** region. Prices were last verified in **January 2025**.
> Actual costs may vary based on your AWS region, pricing model (on-demand vs. provisioned),
> reserved capacity, and real-world traffic patterns. This report assumes constant RPS average
> item sizes, and may not cover all cost scenarios. For the most current pricing, refer to the
> [Amazon DynamoDB Pricing](https://aws.amazon.com/dynamodb/pricing/) page.

### Access Pattern Costs

#### Users

| Pattern        | Operation | RPS   | RRU / WRU | Monthly Cost |
| -------------- | --------- | ----- | --------- | ------------ |
| get-user-by-id | GetItem   | 100.0 | 0.50      | $16.47       |
| create-user    | PutItem   | 20.0  | 1.00      | $32.94       |

**Users Table Cost:** $49.41

##### email-index

| Pattern           | Operation | RPS  | RRU / WRU | Monthly Cost |
| ----------------- | --------- | ---- | --------- | ------------ |
| get-user-by-email | Query     | 50.0 | 0.50      | $8.23        |
| create-user¹      | PutItem   | 20.0 | 1.00      | $32.94       |

**email-index Cost:** $41.18

**Users Total Cost:** $90.59

#### Orders

| Pattern             | Operation  | RPS  | RRU / WRU | Monthly Cost |
| ------------------- | ---------- | ---- | --------- | ------------ |
| get-orders-by-user  | Query      | 80.0 | 1.00      | $26.35       |
| create-order        | PutItem    | 40.0 | 1.00      | $65.88       |
| update-order-status | UpdateItem | 30.0 | 1.00      | $49.41       |

**Orders Table Cost:** $141.64

##### status-index

| Pattern              | Operation  | RPS  | RRU / WRU | Monthly Cost |
| -------------------- | ---------- | ---- | --------- | ------------ |
| get-orders-by-status | Query      | 60.0 | 0.50      | $9.88        |
| create-order¹        | PutItem    | 40.0 | 1.00      | $65.88       |
| update-order-status¹ | UpdateItem | 30.0 | 1.00      | $49.41       |

**status-index Cost:** $125.17

##### date-index

| Pattern       | Operation | RPS  | RRU / WRU | Monthly Cost |
| ------------- | --------- | ---- | --------- | ------------ |
| create-order¹ | PutItem   | 40.0 | 1.00      | $65.88       |

**date-index Cost:** $65.88

**Orders Total Cost:** $332.69

#### Sessions

| Pattern        | Operation | RPS   | RRU / WRU | Monthly Cost |
| -------------- | --------- | ----- | --------- | ------------ |
| get-session    | GetItem   | 150.0 | 0.50      | $24.70       |
| create-session | PutItem   | 200.0 | 1.00      | $329.40      |

**Sessions Table Cost:** $354.11

**Sessions Total Cost:** $354.11

**Total Access Pattern Cost:** $777.38

### Storage Costs

| Resource     | Type  | Storage (GB) | Monthly Cost |
| ------------ | ----- | ------------ | ------------ |
| Users        | Table | 13.97        | $3.49        |
| email-index  | GSI   | 9.31         | $2.33        |
| Orders       | Table | 111.76       | $27.94       |
| status-index | GSI   | 46.57        | $11.64       |
| date-index   | GSI   | 55.88        | $13.97       |
| Sessions     | Table | 3.73         | $0.93        |

**Total Storage Cost:** $60.30

¹ **GSI write amplification** — When a table write changes attributes projected into a GSI, DynamoDB performs an additional write to that index, incurring extra WRUs. [Learn more](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GSI.html#GSI.ThroughputConsiderations.Writes)

<!-- end-cost-report -->"""

    assert content == expected
