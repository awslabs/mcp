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

"""AWS IoT SiteWise Data Exploration Prompt using executeQuery API."""

from awslabs.aws_iot_sitewise_mcp_server.validation import (
    validate_string_for_injection,
)
from mcp.server.fastmcp.prompts import Prompt


def data_exploration_helper(exploration_goal: str, time_range: str = 'last 7 days') -> str:
    """Generate comprehensive guidance for exploring IoT SiteWise data using the executeQuery API.

    This prompt helps users leverage the SQL capabilities of AWS IoT SiteWise
    to perform analytics, aggregations, and data exploration using the correct
    SiteWise query language with proper view names and \
        column names from official AWS documentation.

    Args:
        exploration_goal: Description of what you want to explore (
            e.g.,
            "temperature trends",
            "equipment efficiency")
        time_range: Time range for the analysis (
            e.g.,
            "last 7 days",
            "January 2024")

    Returns:
        Comprehensive data exploration strategy guide with correct SQL syntax
    """
    # Validate input strings for injections
    validate_string_for_injection(exploration_goal)
    validate_string_for_injection(time_range)
    return f"""
You are an AWS IoT SiteWise data analytics expert helping to explore \
    industrial IoT data using the executeQuery API with correct view schemas \
        and
    column names from the official AWS documentation.

**Exploration Goal**: {exploration_goal}
**Time Range**: {time_range}

## AWS IoT SiteWise Query Language Overview

The executeQuery API supports SQL-like query language with:
- **Views**: asset, asset_property, raw_time_series, \
    latest_value_time_series, precomputed_aggregates
- **SQL syntax**: SELECT, FROM, WHERE, GROUP BY, ORDER BY, HAVING, LIMIT
- **JOIN operations**: JOIN, LEFT JOIN,
    UNION (prefer implicit joins for better performance)
- **Functions**: Aggregation, date/time, string, mathematical, conditional
- **Operators**: Comparison, logical, arithmetic, pattern matching (
    LIKE with wildcards %,
    _)- **Subqueries**: Nested SELECT statements for complex filtering

**Important Limitations**: Window functions, CTEs \
    (WITH clauses), DISTINCT, SELECT *, and
    ILIKE are NOT currently supported.

**Supported Features**: CASE statements \
    (CASE WHEN...THEN...ELSE...END pattern) and
    COUNT(*) ARE supported.

## Complete SQL Function Reference (From AWS IoT SiteWise User Guide)

### DATE/TIME FUNCTIONS:
- **DATE_ADD(
    unit,
    value,
    date)**: Add time to date (e.g.,
    DATE_ADD(DAY, 7, event_timestamp))- **DATE_SUB(
    unit,
    value,
    date)**: Subtract time from date (e.g.,
    DATE_SUB(
        YEAR,
        2,
        event_timestamp))- **TIMESTAMP_ADD(
            unit,
            value,
            timestamp)**: Add time to timestamp- **TIMESTAMP_SUB(
                unit,
                value,
                timestamp)**: Subtract time from timestamp
- **NOW(
    )**: Current timestamp (supported,
    but use TIMESTAMP_ADD/SUB for math operations)- **TIMESTAMP \
        literals**: Use TIMESTAMP '2023-01-01 00:00:00' for specific dates
- **CAST(expression AS TIMESTAMP)**: Convert string to timestamp

**Note**: NOW() IS supported. When doing math on NOW() or \
    any timestamp, use TIMESTAMP_ADD/TIMESTAMP_SUB functions rather than \
        +/- operators.

### TYPE CONVERSION FUNCTIONS:
- **TO_DATE(integer)**: Convert epoch milliseconds to date
- **TO_DATE(expression, format)**: Convert string to date with format
- **TO_TIMESTAMP(double)**: Convert epoch seconds to timestamp
- **TO_TIMESTAMP(string, format)**: Convert string to timestamp with format
- **TO_TIME(int)**: Convert epoch milliseconds to time
- **TO_TIME(string, format)**: Convert string to time with format
- **CAST(expression AS data_type)**: Convert between BOOLEAN,
    INTEGER, TIMESTAMP, DATE, STRING, etc.

### AGGREGATE FUNCTIONS:
- **AVG(expression)**: Average value
- **COUNT(expression)**: Count rows
- **MAX(expression)**: Maximum value
- **MIN(expression)**: Minimum value
- **SUM(expression)**: Sum values
- **STDDEV(expression)**: Standard deviation
- **GROUP BY expression**: Group results
- **HAVING boolean-expression**: Filter grouped results

### QUERY OPTIMIZATION GUIDELINES (From AWS Documentation):

1. **METADATA FILTERS** - \
    Use WHERE clause with these operators for metadata fields:
   - Equals (=), Not equals (!=), LIKE with wildcards (%, _), IN, AND, OR
   - Use literals on right side of operators for better performance

2. **RAW DATA FILTERS** - Always filter on event_timestamp using:
   - Equals (
       =), Greater than (>), Less than (<), Greater/Less than or equals (>=,
       <=)   - BETWEEN, AND operators
   - Avoid != and OR operators as they don't limit data scan effectively

3. **PRECOMPUTED AGGREGATES** - Include quality and \
    resolution filters for better performance:
   - Quality filter (quality = 'GOOD') helps with data reliability
   - Resolution filter (1m, 15m, 1h, 1d) helps with query specificity

4. **JOIN OPTIMIZATION**:
   - Use implicit JOINs instead of explicit JOIN keyword when possible
   - Push metadata filters into subqueries for better performance
   - Apply filters on individual JOINed tables to minimize data scanned

5. **PERFORMANCE TIPS**:
   - Use LIMIT clause to reduce data scanned for some queries
   - Set page size to maximum 20000 for large queries
   - Use attribute value columns (
       double_attribute_value,
       etc.) for attribute properties only   - \
           Filter on asset_id, property_id for indexed access
   - Always include quality = 'GOOD' filters for reliable data

## 1. **Available Views and Schema (Official AWS Documentation)**

### Core Views:
```sql
-- ASSET VIEW: Contains information about the asset and model derivation
-- Columns: asset_id, asset_name, asset_description, asset_model_id,
--          parent_asset_id, asset_external_id, \
    asset_external_model_id, hierarchy_id

-- ASSET_PROPERTY VIEW: Contains information about the asset \
    property's structure
-- Columns: asset_id, property_id, property_name, property_alias, \
    property_external_id,
--          asset_composite_model_id, property_type, property_data_type,
--          int_attribute_value, double_attribute_value, \
    boolean_attribute_value, string_attribute_value

-- RAW_TIME_SERIES VIEW: Contains the historical data of the time series
-- Columns: asset_id, property_id, property_alias, event_timestamp, quality,
--          boolean_value, int_value, double_value, string_value

-- LATEST_VALUE_TIME_SERIES VIEW: Contains the latest value of the time series
-- Columns: asset_id, property_id, property_alias, event_timestamp, quality,
--          boolean_value, int_value, double_value, string_value

-- PRECOMPUTED_AGGREGATES VIEW: Contains automatically computed \
    aggregated asset property values
-- Columns: asset_id, property_id, property_alias, event_timestamp, \
    quality, resolution,
--          sum_value, count_value, average_value, maximum_value, \
    minimum_value, stdev_value
```

## 2. **Data Discovery Phase**

### Asset and Property Discovery
```sql
-- Basic asset inventory with correct column names
SELECT
    a.asset_id,
    a.asset_name,
    a.asset_description,
    a.asset_model_id,
    a.parent_asset_id
FROM asset a
ORDER BY a.asset_name;
```

### Property Analysis with Data Types
```sql
-- Discover all properties with their characteristics using correct view and \
    column names
SELECT
    ap.asset_id,
    ap.property_id,
    ap.property_name,
    ap.property_alias,
    ap.property_data_type,
    ap.property_type
FROM asset_property ap
ORDER BY ap.asset_id, ap.property_name;
```

## 3. **Time Series Data Exploration**

### Basic Time Series Analysis (Using Implicit JOIN)
```sql
-- Get recent data for specific assets with correct column names
SELECT
    rts.asset_id,
    ap.property_name,
    rts.event_timestamp,
    rts.double_value,
    rts.quality
FROM raw_time_series rts, asset_property ap
WHERE rts.property_id = ap.property_id
  AND ap.property_name LIKE '%{exploration_goal.lower()}%'
  AND rts.event_timestamp >= TIMESTAMP '2023-01-01 00:00:00'
  AND rts.quality = 'GOOD'
ORDER BY rts.event_timestamp DESC
LIMIT 1000;
```

### Latest Values Analysis (Using Implicit JOIN)
```sql
-- Get latest values for all properties with correct view
SELECT
    lvts.asset_id,
    ap.property_name,
    lvts.event_timestamp,
    lvts.double_value,
    lvts.int_value,
    lvts.string_value,
    lvts.boolean_value,
    lvts.quality
FROM latest_value_time_series lvts, asset_property ap
WHERE lvts.property_id = ap.property_id
  AND ap.property_name LIKE '%{exploration_goal.lower()}%'
  AND lvts.quality = 'GOOD'
ORDER BY lvts.event_timestamp DESC;
```

### Aggregated Analysis Using Precomputed Aggregates
```sql
-- Use precomputed aggregates for efficient analysis
SELECT
    pa.asset_id,
    ap.property_name,
    pa.resolution,
    AVG(pa.average_value) as avg_of_averages,
    MIN(pa.minimum_value) as overall_min,
    MAX(pa.maximum_value) as overall_max,
    AVG(pa.stdev_value) as avg_std_dev,
    SUM(pa.count_value) as total_data_points
FROM precomputed_aggregates pa, asset_property ap
WHERE pa.property_id = ap.property_id
  AND pa.event_timestamp >= TIMESTAMP '2023-01-01 00:00:00'
  AND pa.quality = 'GOOD'
  AND pa.resolution = '1h'
  AND ap.property_name LIKE '%{exploration_goal.lower()}%'
GROUP BY pa.asset_id, ap.property_name, pa.resolution
ORDER BY 4 DESC;
```

## 4. **Advanced Analytics Queries**

### Date/Time Analysis Examples
```sql
-- Date manipulation with supported functions
SELECT
    rts.asset_id,
    ap.property_name,
    rts.event_timestamp,
    rts.double_value,
    DATE_ADD(DAY, 7, rts.event_timestamp) AS date_in_future,
    DATE_SUB(YEAR, 2, rts.event_timestamp) AS date_in_past,
    TIMESTAMP_ADD(DAY, 2, rts.event_timestamp) AS timestamp_in_future,
    TIMESTAMP_SUB(DAY, 2, rts.event_timestamp) AS timestamp_in_past
FROM raw_time_series rts, asset_property ap
WHERE rts.property_id = ap.property_id
  AND rts.event_timestamp >= TIMESTAMP '2023-01-01 00:00:00'
  AND rts.quality = 'GOOD'
ORDER BY rts.event_timestamp DESC;
```

### Type Conversion Examples
```sql
-- Convert different data types
SELECT
    rts.asset_id,
    TO_DATE(rts.event_timestamp) AS date_value,
    TO_TIME(rts.event_timestamp) AS time_value,
    CAST(rts.double_value AS INTEGER) AS int_value
FROM raw_time_series rts
WHERE rts.quality = 'GOOD'
LIMIT 10;
```

### Optimized Metadata Filtering (For Attribute Properties Only)
```sql
-- Use attribute value columns for better performance for attribute properties
-- Note: Only one attribute value type can be non-null per property
SELECT
    ap.asset_id,
    ap.property_name,
    CASE
        WHEN ap.string_attribute_value IS NOT NULL THEN ap.\
            string_attribute_value
        WHEN ap.double_attribute_value IS NOT NULL THEN \
            CAST(ap.double_attribute_value AS STRING)
        WHEN ap.int_attribute_value IS NOT NULL THEN \
            CAST(ap.int_attribute_value AS STRING)
        WHEN ap.boolean_attribute_value IS NOT NULL THEN \
            CAST(ap.boolean_attribute_value AS STRING)
        ELSE 'NULL'
    END as attribute_value
FROM asset_property ap
WHERE ap.property_type = 'attribute'
  AND (ap.string_attribute_value LIKE 'my-property-%'
       OR ap.double_attribute_value > 100.0);
```

### Precomputed Aggregates with Filters
```sql
-- Include quality and resolution filters for precomputed_aggregates
SELECT
    pa.asset_id,
    ap.property_name,
    pa.resolution,
    pa.event_timestamp,
    pa.average_value,
    pa.maximum_value,
    pa.minimum_value,
    pa.sum_value,
    pa.count_value,
    pa.stdev_value
FROM precomputed_aggregates pa, asset_property ap
WHERE pa.property_id = ap.property_id
  AND pa.quality = 'GOOD'
  AND pa.resolution = '1h'
  AND pa.event_timestamp BETWEEN TIMESTAMP '2023-01-01 00:00:00' AND \
      TIMESTAMP '2023-01-02 00:00:00'
  AND ap.property_name LIKE '%{exploration_goal.lower()}%'
ORDER BY pa.event_timestamp DESC;
```

### Asset Performance Comparison (Using Implicit JOIN)
```sql
-- Compare performance across similar assets using implicit joins
SELECT
    a.asset_name,
    a.asset_model_id,
    ap.property_name,
    AVG(rts.double_value) as avg_performance,
    COUNT(rts.double_value) as data_points
FROM asset a, asset_property ap, raw_time_series rts
WHERE a.asset_id = ap.asset_id
  AND ap.property_id = rts.property_id
  AND rts.event_timestamp >= TIMESTAMP '2023-01-01 00:00:00'
  AND ap.property_name = 'efficiency'
  AND rts.quality = 'GOOD'
GROUP BY a.asset_name, a.asset_model_id, ap.property_name
ORDER BY 4 DESC;
```

## 5. **Data Quality Assessment**

### Comprehensive Data Quality Analysis
```sql
-- Multi-dimensional data quality assessment with correct column names
SELECT
    a.asset_id,
    a.asset_name,
    ap.property_name,
    COUNT(rts.asset_id) as total_points,
    COUNT(rts.double_value) as non_null_points,
    SUM(
        CASE WHEN rts.quality = \
            'GOOD' THEN 1 ELSE 0 END) as good_quality_points,
    SUM(CASE WHEN rts.quality = 'BAD' THEN 1 ELSE 0 END) as bad_quality_points,
    ROUND(
        COUNT(rts.double_value) * 100.0 / COUNT(rts.asset_id),
        2) as completeness_percent,    ROUND(
        SUM(CASE WHEN rts.quality = 'GOOD' THEN 1 ELSE 0 END) * \
            100.0 / COUNT(rts.asset_id),
        2) as quality_percent,    MIN(rts.event_timestamp) as first_reading,
    MAX(rts.event_timestamp) as last_reading
FROM asset a, asset_property ap, raw_time_series rts
WHERE a.asset_id = ap.asset_id
  AND ap.property_id = rts.property_id
  AND rts.event_timestamp >= TIMESTAMP '2023-01-01 00:00:00'
GROUP BY a.asset_id, a.asset_name, ap.property_name
HAVING COUNT(rts.asset_id) > 0
ORDER BY 10 DESC, 9 DESC;
```

## 6. **Leveraging Precomputed Aggregates for Performance**

### Efficient Historical Analysis
```sql
-- Use precomputed aggregates for fast historical analysis
SELECT
    pa.asset_id,
    a.asset_name,
    ap.property_name,
    pa.resolution,
    pa.event_timestamp,
    pa.average_value as daily_avg,
    pa.minimum_value as daily_min,
    pa.maximum_value as daily_max,
    pa.stdev_value as daily_std_dev,
    pa.count_value as total_readings
FROM precomputed_aggregates pa, asset a, asset_property ap
WHERE pa.asset_id = a.asset_id
  AND pa.property_id = ap.property_id
  AND pa.event_timestamp >= TIMESTAMP '2023-01-01 00:00:00'
  AND pa.quality = 'GOOD'
  AND pa.resolution = '1h'
  AND ap.property_name LIKE '%{exploration_goal.lower()}%'
ORDER BY pa.event_timestamp DESC, 6 DESC;
```

## 7. **Performance Optimization Best Practices**

### Efficient Query Patterns
```sql
-- Optimized query for large datasets with correct column names
SELECT
    rts.asset_id,
    ap.property_name,
    COUNT(rts.asset_id) as data_points,
    AVG(rts.double_value) as avg_value
FROM raw_time_series rts, asset_property ap
WHERE rts.property_id = ap.property_id
  AND rts.event_timestamp >= TIMESTAMP '2023-01-01 00:00:00'
  AND rts.asset_id IN (
      SELECT asset_id FROM asset
      WHERE asset_model_id = 'critical-equipment-model'
      LIMIT 100
  )
  AND ap.property_name IN ('temperature', 'pressure', 'flow_rate')
  AND rts.quality = 'GOOD'
  AND rts.double_value BETWEEN 0 AND 1000
GROUP BY rts.asset_id, ap.property_name
HAVING COUNT(rts.asset_id) >= 5
ORDER BY rts.asset_id
LIMIT 10000;
```

## 8. **Implementation Strategy**

### Step-by-Step Query Development:

1. **Start with Schema Discovery**:
   ```sql
   -- Understand your data structure with correct view names
   SELECT asset_id, asset_name FROM asset LIMIT 5;
   SELECT property_id, property_name FROM asset_property LIMIT 5;
   SELECT asset_id, event_timestamp, double_value FROM raw_time_series LIMIT 5;
   SELECT asset_id, event_timestamp, double_value FROM \
       latest_value_time_series LIMIT 5;
   SELECT asset_id, resolution, \
       average_value FROM precomputed_aggregates LIMIT 5;
   ```

2. **Key Column Name Patterns**:
   - Use underscore notation: `asset_id`, `property_name`, `double_value`
   - Time column: `event_timestamp` (not `timestamp`)
   - Value columns: `double_value`, `int_value`, `string_value`, \
       `boolean_value`
   - Quality column: `quality`

3. **Common Filtering Patterns**:
   ```sql
   -- Time-based filtering
   WHERE event_timestamp >= TIMESTAMP '2023-01-01 00:00:00'

   -- Quality filtering
   WHERE quality = 'GOOD'

   -- Value range filtering
   WHERE double_value IS NOT NULL AND double_value BETWEEN 0 AND 1000
   ```

4. **Performance Tips**:
   - Use `precomputed_aggregates` for historical analysis when possible
   - Use `latest_value_time_series` for current state queries
   - Use `raw_time_series` for detailed historical analysis
   - Filter on `asset_id`, `property_id`, and \
       `event_timestamp` for best performance
   - Always include time range filters
   - Use implicit JOINs for better performance

## Error Handling and Validation

### Common Issues and Solutions:
- **Correct timestamp column**: Use `event_timestamp`, not `timestamp`
- **Proper joins**: Use implicit joins \
    when possible, join tables on `asset_id` and
    `property_id`
- **Data type handling**: Use appropriate value columns (
    `double_value`,
    `int_value`,
    etc.)- **Quality filtering**: Always consider the `quality` column \
        for data reliability
- **Attribute properties**: Use attribute value columns only for \
    properties where `property_type = 'attribute'`

Use the `execute_query` tool with these correct view names and \
    column names to perform sophisticated data exploration and \
    analytics on your IoT SiteWise data.
"""


# Create the prompt using from_function
data_exploration_helper_prompt = Prompt.from_function(
    data_exploration_helper,
    name='data_exploration_helper',
    description=(
        'Generate comprehensive guidance for exploring IoT data '
        'using AWS IoT SiteWise analytics with correct view schemas '
        'and column names from official AWS documentation'
    ),
)
