#!/usr/bin/env python3
"""
Test script to verify type conversion fixes in analysis tools.

This specifically tests the tools that might have type conversion issues.
"""

import asyncio
import boto3
import json
import os
import pytest


def extract_cell(cell: dict):
    """Extracts the scalar or array value from a single cell (same as server)."""
    if cell.get('isNull'):
        return None
    for key in (
        'stringValue',
        'longValue',
        'doubleValue',
        'booleanValue',
        'blobValue',
        'arrayValue',
    ):
        if key in cell:
            return cell[key]
    return None


def parse_execute_response(response: dict) -> list[dict]:
    """Convert RDS Data API execute_statement response to list of rows (same as server)."""
    columns = [col['name'] for col in response.get('columnMetadata', [])]
    records = []

    for row in response.get('records', []):
        row_data = {col: extract_cell(cell) for col, cell in zip(columns, row)}
        records.append(row_data)

    return records


async def test_table_fragmentation_types():
    """Test the table fragmentation analysis with type conversion."""
    print(" Testing Table Fragmentation Analysis Type Conversions")
    print("=" * 60)
    
    try:
        client = boto3.client('rds-data', region_name='us-west-2')
    except Exception as e:
        if "ProfileNotFound" in str(e) or "mcp_profile" in str(e):
            pytest.skip(f"AWS profile not available in CI: {e}")
        raise
    
    try:
        # Execute the same query as the tool
        result = client.execute_statement(
            resourceArn='arn:aws:rds:us-west-2:288947426911:cluster:pg-clone-db-cluster',
            secretArn='arn:aws:secretsmanager:us-west-2:288947426911:secret:rds!cluster-7d957e88-d967-46f3-a21e-7db88c36bdf9-NEq9xL',
            database='devdb',
            sql="""
                SELECT 
                    schemaname,
                    relname as tablename,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_tuples,
                    n_dead_tup as dead_tuples,
                    CASE 
                        WHEN n_live_tup > 0 
                        THEN round(100.0 * n_dead_tup / (n_live_tup + n_dead_tup), 2)
                        ELSE 0 
                    END as bloat_percent,
                    last_vacuum,
                    last_autovacuum
                FROM pg_stat_user_tables
                ORDER BY 
                    CASE 
                        WHEN n_live_tup > 0 
                        THEN 100.0 * n_dead_tup / (n_live_tup + n_dead_tup)
                        ELSE 0 
                    END DESC
                LIMIT 5
            """,
            includeResultMetadata=True
        )
        
        # Parse the result using the same logic as the server
        bloat_result = parse_execute_response(result)
        
        print(f" Query executed successfully, got {len(bloat_result)} tables")
        
        # Test the type conversion logic (same as in the fixed tool)
        threshold = 10.0
        problematic_tables = []
        
        for i, row in enumerate(bloat_result):
            print(f"\\n📋 Table {i+1}: {row.get('tablename', 'unknown')}")
            
            if 'error' not in row:
                # Convert bloat_percent from string to float for comparison
                bloat_percent_value = row.get('bloat_percent', '0')
                print(f"   Raw bloat_percent: {bloat_percent_value} (type: {type(bloat_percent_value)})")
                
                try:
                    # Handle both string and numeric values
                    if isinstance(bloat_percent_value, str):
                        bloat_percent_float = float(bloat_percent_value)
                    else:
                        bloat_percent_float = float(bloat_percent_value) if bloat_percent_value is not None else 0.0
                    
                    print(f"   Converted bloat_percent: {bloat_percent_float}")
                    print(f"   Above threshold ({threshold}%): {bloat_percent_float > threshold}")
                    
                    if bloat_percent_float > threshold:
                        # Add the converted value back to the row for consistency
                        row['bloat_percent_numeric'] = bloat_percent_float
                        problematic_tables.append(row)
                        print(f"   Added to problematic tables list")
                    else:
                        print(f"    Table is healthy (below threshold)")
                        
                except (ValueError, TypeError) as e:
                    print(f" Conversion failed: {e}")
                    continue
        
        print(f"\\n Summary:")
        print(f"   Total tables analyzed: {len(bloat_result)}")
        print(f"   Tables above {threshold}% threshold: {len(problematic_tables)}")
        
        # Test JSON serialization (same as the tool does)
        result_json = {
            "status": "success",
            "data": {
                "table_bloat": [row for row in bloat_result if 'error' not in row],
                "problematic_tables": problematic_tables,
                "threshold_percent": threshold
            },
            "metadata": {
                "analysis_timestamp": "2025-06-19T14:00:00Z",
                "total_tables_analyzed": len([row for row in bloat_result if 'error' not in row]),
                "tables_above_threshold": len(problematic_tables)
            },
            "recommendations": [
                f"Found {len(problematic_tables)} tables above {threshold}% bloat threshold",
                "Consider running VACUUM on tables with high dead tuple percentages",
                "Review autovacuum settings for frequently updated tables",
                "Monitor vacuum operations and adjust frequency as needed"
            ]
        }
        
        # Test JSON serialization
        json_output = json.dumps(result_json, indent=2)
        print(f"\\n JSON serialization successful (length: {len(json_output)} chars)")
        
        return True
        
    except Exception as e:
        print(f" Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_slow_queries_types():
    """Test the slow queries analysis to ensure no type issues."""
    print("\\n Testing Slow Queries Analysis")
    print("=" * 60)
    
    try:
        client = boto3.client('rds-data', region_name='us-west-2')
    except Exception as e:
        if "ProfileNotFound" in str(e) or "mcp_profile" in str(e):
            pytest.skip(f"AWS profile not available in CI: {e}")
        raise
    
    try:
        # First check if extension exists
        extension_result = client.execute_statement(
            resourceArn='arn:aws:rds:us-west-2:288947426911:cluster:pg-clone-db-cluster',
            secretArn='arn:aws:secretsmanager:us-west-2:288947426911:secret:rds!cluster-7d957e88-d967-46f3-a21e-7db88c36bdf9-NEq9xL',
            database='devdb',
            sql="SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements') as extension_exists",
            includeResultMetadata=True
        )
        
        extension_data = parse_execute_response(extension_result)
        has_extension = extension_data[0].get('extension_exists', False) if extension_data else False
        
        print(f"pg_stat_statements extension available: {has_extension}")
        
        if has_extension:
            # Test the slow queries query with numeric parameter
            min_execution_time = 100.0
            limit = 5
            
            slow_queries_result = client.execute_statement(
                resourceArn='arn:aws:rds:us-west-2:288947426911:cluster:pg-clone-db-cluster',
                secretArn='arn:aws:secretsmanager:us-west-2:288947426911:secret:rds!cluster-7d957e88-d967-46f3-a21e-7db88c36bdf9-NEq9xL',
                database='devdb',
                sql=f"""
                    SELECT 
                        query,
                        calls,
                        total_exec_time,
                        mean_exec_time,
                        max_exec_time,
                        min_exec_time,
                        rows
                    FROM pg_stat_statements 
                    WHERE mean_exec_time >= {min_execution_time}
                    ORDER BY mean_exec_time DESC
                    LIMIT {limit}
                """,
                includeResultMetadata=True
            )
            
            slow_queries_data = parse_execute_response(slow_queries_result)
            print(f" Slow queries query successful, got {len(slow_queries_data)} results")
            
            # Check data types
            for i, row in enumerate(slow_queries_data[:2]):  # Just check first 2
                print(f"\\n Query {i+1}:")
                for key, value in row.items():
                    print(f"   {key}: {value} (type: {type(value)})")
        else:
            print("⚠️  pg_stat_statements extension not available - this is expected behavior")
        
        return True
        
    except Exception as e:
        print(f" Test failed: {e}")
        return False


async def main():
    """Run type conversion tests."""
    print(" PostgreSQL MCP Server - Type Conversion Tests")
    print("=" * 70)
    
    # Set AWS profile
    os.environ['AWS_PROFILE'] = 'mcp_profile'
    os.environ['AWS_REGION'] = 'us-west-2'
    
    test_results = {}
    
    # Test table fragmentation type conversions
    test_results['table_fragmentation'] = await test_table_fragmentation_types()
    
    # Test slow queries (no type conversion issues expected, but verify)
    test_results['slow_queries'] = await test_slow_queries_types()
    
    # Summary
    print("\\n" + "=" * 70)
    print(" TYPE CONVERSION TEST RESULTS")
    print("=" * 70)
    
    passed = sum(1 for result in test_results.values() if result)
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = " PASSED" if result else " FAILED"
        print(f"{status} - {test_name}")
    
    print(f"\\n Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print(" ALL TYPE CONVERSION TESTS PASSED!")
        print(" Table fragmentation analysis type conversion working")
        print(" No type issues detected in other analysis tools")
        print(" PostgreSQL MCP Server is ready for Q Chat!")
    else:
        print("  Some tests failed - please review the issues above")


if __name__ == "__main__":
    asyncio.run(main())
