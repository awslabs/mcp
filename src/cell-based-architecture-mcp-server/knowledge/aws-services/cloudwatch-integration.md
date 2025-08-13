# CloudWatch Integration with Cell-Based Architecture

## Overview

Amazon CloudWatch is essential for monitoring cell-based architectures, providing metrics, logs, and alarms that need to be cell-aware to effectively observe and operate distributed cell systems.

## Cell-Aware Metrics

### Custom Metrics per Cell
Create custom metrics with cell dimensions:

```python
import boto3
from datetime import datetime

cloudwatch = boto3.client('cloudwatch')

def put_cell_metric(cell_id, metric_name, value, unit='Count', namespace='CellBasedArchitecture'):
    cloudwatch.put_metric_data(
        Namespace=namespace,
        MetricData=[
            {
                'MetricName': metric_name,
                'Dimensions': [
                    {
                        'Name': 'CellId',
                        'Value': cell_id
                    }
                ],
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.utcnow()
            }
        ]
    )

# Example usage
put_cell_metric('cell-us-east-1-001', 'RequestCount', 150)
put_cell_metric('cell-us-east-1-001', 'ResponseTime', 250, 'Milliseconds')
put_cell_metric('cell-us-east-1-001', 'ErrorRate', 0.5, 'Percent')
```

### Multi-Dimensional Metrics
Add multiple dimensions for detailed analysis:

```python
def put_detailed_cell_metric(cell_id, customer_id, service_name, metric_name, value):
    cloudwatch.put_metric_data(
        Namespace='CellBasedArchitecture/Detailed',
        MetricData=[
            {
                'MetricName': metric_name,
                'Dimensions': [
                    {'Name': 'CellId', 'Value': cell_id},
                    {'Name': 'CustomerId', 'Value': customer_id},
                    {'Name': 'ServiceName', 'Value': service_name}
                ],
                'Value': value,
                'Unit': 'Count'
            }
        ]
    )
```

## Cell-Specific Dashboards

### Individual Cell Dashboard
Create dashboards for monitoring individual cells:

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["CellBasedArchitecture", "RequestCount", "CellId", "cell-us-east-1-001"],
          [".", "ErrorCount", ".", "."],
          [".", "ResponseTime", ".", "."]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Cell Performance Metrics"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Lambda", "Duration", "FunctionName", "cell-us-east-1-001-processor"],
          [".", "Errors", ".", "."],
          [".", "Invocations", ".", "."]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Lambda Metrics"
      }
    }
  ]
}
```

### System-Wide Dashboard
Create aggregated views across all cells:

```python
def create_system_dashboard():
    dashboard_body = {
        "widgets": [
            {
                "type": "metric",
                "properties": {
                    "metrics": [],
                    "period": 300,
                    "stat": "Sum",
                    "region": "us-east-1",
                    "title": "Total System Requests"
                }
            }
        ]
    }
    
    # Add metrics for each cell
    cells = get_active_cells()
    for cell_id in cells:
        dashboard_body["widgets"][0]["properties"]["metrics"].append([
            "CellBasedArchitecture", "RequestCount", "CellId", cell_id
        ])
    
    cloudwatch.put_dashboard(
        DashboardName='CellBasedArchitecture-System',
        DashboardBody=json.dumps(dashboard_body)
    )
```

## Cell-Aware Logging

### Structured Logging with Cell Context
Implement structured logging that includes cell information:

```python
import json
import logging
from datetime import datetime

class CellAwareFormatter(logging.Formatter):
    def __init__(self, cell_id):
        self.cell_id = cell_id
        super().__init__()
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'cell_id': self.cell_id,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add custom fields if present
        if hasattr(record, 'customer_id'):
            log_entry['customer_id'] = record.customer_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
            
        return json.dumps(log_entry)

# Usage
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(CellAwareFormatter('cell-us-east-1-001'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Log with additional context
logger.info("Processing customer request", extra={
    'customer_id': 'customer-12345',
    'request_id': 'req-abcd-1234'
})
```

### Log Groups per Cell
Create separate log groups for each cell:

```yaml
# CloudFormation template
CellLogGroup:
  Type: AWS::Logs::LogGroup
  Properties:
    LogGroupName: !Sub "/aws/cell/${CellId}"
    RetentionInDays: 30
    Tags:
      - Key: CellId
        Value: !Ref CellId
      - Key: Environment
        Value: !Ref Environment

CellLogStream:
  Type: AWS::Logs::LogStream
  Properties:
    LogGroupName: !Ref CellLogGroup
    LogStreamName: !Sub "${CellId}-application"
```

## Alarms and Alerting

### Cell-Specific Alarms
Create alarms for individual cell health:

```python
def create_cell_alarms(cell_id):
    # High error rate alarm
    cloudwatch.put_metric_alarm(
        AlarmName=f'{cell_id}-HighErrorRate',
        ComparisonOperator='GreaterThanThreshold',
        EvaluationPeriods=2,
        MetricName='ErrorRate',
        Namespace='CellBasedArchitecture',
        Period=300,
        Statistic='Average',
        Threshold=5.0,
        ActionsEnabled=True,
        AlarmActions=[
            f'arn:aws:sns:us-east-1:123456789012:cell-alerts'
        ],
        AlarmDescription=f'High error rate in {cell_id}',
        Dimensions=[
            {
                'Name': 'CellId',
                'Value': cell_id
            }
        ]
    )
    
    # High response time alarm
    cloudwatch.put_metric_alarm(
        AlarmName=f'{cell_id}-HighResponseTime',
        ComparisonOperator='GreaterThanThreshold',
        EvaluationPeriods=3,
        MetricName='ResponseTime',
        Namespace='CellBasedArchitecture',
        Period=300,
        Statistic='Average',
        Threshold=1000.0,
        ActionsEnabled=True,
        AlarmActions=[
            f'arn:aws:sns:us-east-1:123456789012:cell-alerts'
        ],
        AlarmDescription=f'High response time in {cell_id}',
        Dimensions=[
            {
                'Name': 'CellId',
                'Value': cell_id
            }
        ]
    )
```

### Composite Alarms
Create composite alarms for system-wide issues:

```python
def create_system_composite_alarm():
    # Get all cell alarm ARNs
    cell_alarms = []
    cells = get_active_cells()
    
    for cell_id in cells:
        cell_alarms.append(f'arn:aws:cloudwatch:us-east-1:123456789012:alarm:{cell_id}-HighErrorRate')
    
    # Create composite alarm that triggers if multiple cells have issues
    cloudwatch.put_composite_alarm(
        AlarmName='SystemWideIssue',
        AlarmRule=f"ALARM({') OR ALARM('.join(cell_alarms)})",
        ActionsEnabled=True,
        AlarmActions=[
            'arn:aws:sns:us-east-1:123456789012:system-critical-alerts'
        ],
        AlarmDescription='Multiple cells experiencing issues'
    )
```

## Log Insights Queries

### Cell-Specific Queries
Create Log Insights queries for cell analysis:

```python
def query_cell_errors(cell_id, start_time, end_time):
    logs_client = boto3.client('logs')
    
    query = f"""
    fields @timestamp, @message, level, customer_id, request_id
    | filter cell_id = "{cell_id}"
    | filter level = "ERROR"
    | sort @timestamp desc
    | limit 100
    """
    
    response = logs_client.start_query(
        logGroupName=f'/aws/cell/{cell_id}',
        startTime=int(start_time.timestamp()),
        endTime=int(end_time.timestamp()),
        queryString=query
    )
    
    return response['queryId']

def query_cell_performance(cell_id, start_time, end_time):
    query = f"""
    fields @timestamp, @message, response_time_ms
    | filter cell_id = "{cell_id}"
    | filter ispresent(response_time_ms)
    | stats avg(response_time_ms), max(response_time_ms), min(response_time_ms) by bin(5m)
    """
    
    response = logs_client.start_query(
        logGroupName=f'/aws/cell/{cell_id}',
        startTime=int(start_time.timestamp()),
        endTime=int(end_time.timestamp()),
        queryString=query
    )
    
    return response['queryId']
```

### Cross-Cell Analysis
Query across multiple cells for system-wide analysis:

```python
def query_system_wide_patterns():
    query = """
    fields @timestamp, cell_id, level, @message
    | filter level = "ERROR"
    | stats count() by cell_id, bin(5m)
    | sort @timestamp desc
    """
    
    # Query all cell log groups
    log_groups = [f'/aws/cell/{cell_id}' for cell_id in get_active_cells()]
    
    response = logs_client.start_query(
        logGroupNames=log_groups,
        startTime=int((datetime.utcnow() - timedelta(hours=1)).timestamp()),
        endTime=int(datetime.utcnow().timestamp()),
        queryString=query
    )
    
    return response['queryId']
```

## Automated Responses

### Auto-Scaling Based on Metrics
Implement auto-scaling responses to cell metrics:

```python
def check_cell_capacity_and_scale():
    cells = get_active_cells()
    
    for cell_id in cells:
        # Get current metrics
        response = cloudwatch.get_metric_statistics(
            Namespace='CellBasedArchitecture',
            MetricName='RequestCount',
            Dimensions=[{'Name': 'CellId', 'Value': cell_id}],
            StartTime=datetime.utcnow() - timedelta(minutes=10),
            EndTime=datetime.utcnow(),
            Period=300,
            Statistics=['Average']
        )
        
        if response['Datapoints']:
            avg_requests = response['Datapoints'][-1]['Average']
            
            # Check if cell is approaching capacity
            if avg_requests > CELL_CAPACITY_THRESHOLD:
                trigger_cell_scaling(cell_id)
                
def trigger_cell_scaling(cell_id):
    # Trigger auto-scaling group scaling
    autoscaling = boto3.client('autoscaling')
    
    autoscaling.set_desired_capacity(
        AutoScalingGroupName=f'{cell_id}-asg',
        DesiredCapacity=get_current_capacity(cell_id) + 1,
        HonorCooldown=True
    )
```

### Automated Cell Migration
Trigger cell migration based on performance metrics:

```python
def monitor_and_migrate_overloaded_cells():
    cells = get_active_cells()
    
    for cell_id in cells:
        utilization = get_cell_utilization(cell_id)
        
        if utilization > MIGRATION_THRESHOLD:
            # Find customers to migrate
            customers_to_migrate = identify_migration_candidates(cell_id)
            
            for customer_id in customers_to_migrate:
                target_cell = find_optimal_target_cell(customer_id)
                if target_cell:
                    initiate_customer_migration(customer_id, cell_id, target_cell)
```

## Best Practices

### Metric Organization
- **Consistent naming** - Use standardized metric names across cells
- **Appropriate dimensions** - Include cell_id in all custom metrics
- **Namespace organization** - Use hierarchical namespaces for different metric types
- **Retention policies** - Set appropriate retention for different metric types

### Dashboard Design
- **Cell-specific views** - Individual dashboards for each cell
- **System overview** - Aggregated views for system-wide monitoring
- **Drill-down capability** - Easy navigation from system to cell level
- **Real-time updates** - Use appropriate refresh intervals

### Alerting Strategy
- **Tiered alerting** - Different alert levels for different severity
- **Noise reduction** - Avoid alert fatigue with appropriate thresholds
- **Escalation procedures** - Clear escalation paths for different alert types
- **Documentation** - Well-documented runbooks for alert responses

### Cost Optimization
- **Metric filtering** - Only collect necessary metrics
- **Log retention** - Appropriate retention periods for different log types
- **Dashboard optimization** - Optimize dashboard queries for cost
- **Alarm consolidation** - Use composite alarms to reduce alarm count