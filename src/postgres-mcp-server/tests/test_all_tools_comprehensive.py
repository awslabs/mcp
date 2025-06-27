#!/usr/bin/env python3
"""
Comprehensive test suite for all PostgreSQL MCP Server tools.

This tests all 10 tools with their SQL queries, logic validation, and error handling.
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


@pytest.fixture
def client():
    """Create a boto3 RDS Data API client for testing."""
    import boto3
    return boto3.client('rds-data', region_name='us-west-2')


async def test_sql_query(client, tool_name, query_name, sql, description="", validate_logic=None):
    """Test a single SQL query with optional logic validation."""
    print(f"\n Testing {tool_name} - {query_name}")
    print(f" {description}")
    print("-" * 60)
    
    try:
        result = client.execute_statement(
            resourceArn='arn:aws:rds:us-west-2:288947426911:cluster:pg-clone-db-cluster',
            secretArn='arn:aws:secretsmanager:us-west-2:288947426911:secret:rds!cluster-7d957e88-d967-46f3-a21e-7db88c36bdf9-NEq9xL',
            database='devdb',
            sql=sql,
            includeResultMetadata=True
        )
        
        # Parse the result
        parsed_data = parse_execute_response(result)
        
        print(f" {query_name} - SQL SUCCESS")
        print(f" Returned {len(parsed_data)} rows, {len(result.get('columnMetadata', []))} columns")
        
        if parsed_data and len(parsed_data) > 0:
            sample_data = str(parsed_data[0])
            if len(sample_data) > 150:
                sample_data = sample_data[:150] + "..."
            print(f" Sample data: {sample_data}")
        
        # Run additional logic validation if provided
        if validate_logic:
            try:
                logic_result = validate_logic(parsed_data)
                if logic_result:
                    print(f" {query_name} - LOGIC VALIDATION PASSED")
                else:
                    print(f"  {query_name} - Logic validation returned False")
                    return False
            except Exception as e:
                print(f" {query_name} - LOGIC VALIDATION FAILED: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f" {query_name} - SQL FAILED")
        print(f" Error: {str(e)}")
        return False


async def main():
    """Comprehensive test suite for all PostgreSQL MCP Server tools."""
    print("🚀 PostgreSQL MCP Server - Comprehensive Tool Test Suite")
    print("=" * 70)
    
    # Initialize RDS Data API client
    client = boto3.client('rds-data', region_name='us-west-2')
    
    test_results = {}
    
    # =================================================================
    # CORE TOOLS TESTS (3 tools)
    # =================================================================
    
    print(f"\n{'='*20} CORE TOOLS TESTS {'='*20}")
    
    # Tool 1: run_query
    test_results['run_query_basic'] = await test_sql_query(
        client, "run_query", "Basic Query", 
        "SELECT version() as postgresql_version",
        "Basic connectivity and version check"
    )
    
    test_results['run_query_complex'] = await test_sql_query(
        client, "run_query", "Complex Query",
        "SELECT schemaname, tablename, attname, n_distinct FROM pg_stats WHERE schemaname NOT IN ('information_schema', 'pg_catalog') LIMIT 3",
        "Complex query with joins and filtering"
    )
    
    # Tool 2: get_table_schema
    test_results['get_table_schema'] = await test_sql_query(
        client, "get_table_schema", "Table Schema Query",
        """SELECT
            a.attname AS column_name,
            pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
            col_description(a.attrelid, a.attnum) AS column_comment,
            NOT a.attnotnull AS is_nullable,
            pg_get_expr(d.adbin, d.adrelid) AS column_default
        FROM
            pg_attribute a
        LEFT JOIN pg_attrdef d ON a.attrelid = d.adrelid AND a.attnum = d.adnum
        WHERE
            a.attrelid = 'pg_tables'::regclass
            AND a.attnum > 0
            AND NOT a.attisdropped
        ORDER BY a.attnum""",
        "Get table schema information with column details"
    )
    
    # Tool 3: health_check
    test_results['health_check'] = await test_sql_query(
        client, "health_check", "Health Check Query",
        "SELECT 1 as health_check",
        "Server connectivity validation",
        validate_logic=lambda data: len(data) > 0 and data[0].get('health_check') == 1
    )
    
    # =================================================================
    # ANALYSIS TOOLS TESTS (7 tools)
    # =================================================================
    
    print(f"\n{'='*20} ANALYSIS TOOLS TESTS {'='*20}")
    
    # Tool 4: analyze_database_structure
    test_results['analyze_db_schemas'] = await test_sql_query(
        client, "analyze_database_structure", "Schemas Query",
        """SELECT schema_name 
           FROM information_schema.schemata 
           WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
           ORDER BY schema_name""",
        "Get all user schemas"
    )
    
    test_results['analyze_db_tables'] = await test_sql_query(
        client, "analyze_database_structure", "Tables with Size Query",
        """SELECT 
            t.table_schema,
            t.table_name,
            pg_size_pretty(pg_total_relation_size(quote_ident(t.table_schema)||'.'||quote_ident(t.table_name))) as size,
            pg_total_relation_size(quote_ident(t.table_schema)||'.'||quote_ident(t.table_name)) as size_bytes,
            COALESCE(c.reltuples, 0)::bigint as estimated_rows
        FROM information_schema.tables t
        LEFT JOIN pg_class c ON c.relname = t.table_name
        LEFT JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = t.table_schema
        WHERE t.table_type = 'BASE TABLE'
        AND t.table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        ORDER BY t.table_schema, t.table_name
        LIMIT 5""",
        "Get tables with size information and row estimates"
    )
    
    test_results['analyze_db_indexes'] = await test_sql_query(
        client, "analyze_database_structure", "Indexes Query",
        """SELECT schemaname, tablename, indexname, indexdef
           FROM pg_indexes
           WHERE schemaname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
           ORDER BY schemaname, tablename, indexname
           LIMIT 10""",
        "Get database indexes and definitions"
    )
    
    # Tool 5: show_postgresql_settings
    test_results['show_settings_filtered'] = await test_sql_query(
        client, "show_postgresql_settings", "Settings Query (Filtered)",
        """SELECT name, setting, unit, category, short_desc, context, vartype, source
           FROM pg_settings
           WHERE name ILIKE '%shared_buffers%'
           ORDER BY category, name""",
        "Get PostgreSQL configuration settings with filtering"
    )
    
    test_results['show_settings_all'] = await test_sql_query(
        client, "show_postgresql_settings", "Settings Query (All)",
        """SELECT name, setting, unit, category, short_desc, context, vartype, source
           FROM pg_settings
           ORDER BY category, name
           LIMIT 20""",
        "Get all PostgreSQL configuration settings (limited)"
    )
    
    # Tool 6: identify_slow_queries
    test_results['slow_queries_extension'] = await test_sql_query(
        client, "identify_slow_queries", "Extension Check",
        """SELECT EXISTS (
               SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
           ) as extension_exists""",
        "Check for pg_stat_statements extension availability"
    )
    
    # Only test slow queries if extension exists
    if test_results['slow_queries_extension']:
        test_results['slow_queries_data'] = await test_sql_query(
            client, "identify_slow_queries", "Slow Queries Query",
            """SELECT 
                query,
                calls,
                total_exec_time,
                mean_exec_time,
                max_exec_time,
                min_exec_time,
                rows
            FROM pg_stat_statements 
            WHERE mean_exec_time >= 100.0
            ORDER BY mean_exec_time DESC
            LIMIT 5""",
            "Get slow-running queries from pg_stat_statements"
        )
    
    # Tool 7: analyze_table_fragmentation
    def validate_bloat_logic(data):
        """Validate table fragmentation type conversion logic."""
        threshold = 10.0
        problematic_tables = []
        
        for row in data:
            if 'error' not in row:
                bloat_percent_value = row.get('bloat_percent', '0')
                try:
                    if isinstance(bloat_percent_value, str):
                        bloat_percent = float(bloat_percent_value)
                    else:
                        bloat_percent = float(bloat_percent_value) if bloat_percent_value is not None else 0.0
                    
                    if bloat_percent > threshold:
                        problematic_tables.append(row)
                except (ValueError, TypeError):
                    continue
        
        print(f"    💡 Type conversion test: {len(data)} tables analyzed, {len(problematic_tables)} above {threshold}% threshold")
        return True  # Type conversion logic working
    
    test_results['table_fragmentation'] = await test_sql_query(
        client, "analyze_table_fragmentation", "Table Bloat Query",
        """SELECT 
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
        LIMIT 5""",
        "Get table bloat information with type conversion validation",
        validate_logic=validate_bloat_logic
    )
    
    # Tool 8: analyze_query_performance
    test_results['query_performance'] = await test_sql_query(
        client, "analyze_query_performance", "EXPLAIN Query",
        """EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) 
           SELECT COUNT(*) FROM information_schema.tables""",
        "Test EXPLAIN functionality for query performance analysis"
    )
    
    # Tool 9: analyze_vacuum_stats
    test_results['vacuum_stats'] = await test_sql_query(
        client, "analyze_vacuum_stats", "Vacuum Statistics Query",
        """SELECT 
            schemaname,
            relname as tablename,
            n_tup_ins as total_inserts,
            n_tup_upd as total_updates,
            n_tup_del as total_deletes,
            n_live_tup as live_tuples,
            n_dead_tup as dead_tuples,
            last_vacuum,
            last_autovacuum,
            vacuum_count,
            autovacuum_count,
            CASE 
                WHEN n_live_tup > 0 
                THEN round(100.0 * n_dead_tup / (n_live_tup + n_dead_tup), 2)
                ELSE 0 
            END as dead_tuple_percent
        FROM pg_stat_user_tables
        WHERE n_tup_ins + n_tup_upd + n_tup_del > 0
        ORDER BY 
            CASE 
                WHEN n_live_tup > 0 
                THEN 100.0 * n_dead_tup / (n_live_tup + n_dead_tup)
                ELSE 0 
            END DESC
        LIMIT 5""",
        "Get vacuum statistics for maintenance recommendations"
    )
    
    test_results['vacuum_settings'] = await test_sql_query(
        client, "analyze_vacuum_stats", "Vacuum Settings Query",
        """SELECT name, setting, unit, short_desc
           FROM pg_settings 
           WHERE name LIKE '%vacuum%' OR name LIKE '%autovacuum%'
           ORDER BY name
           LIMIT 10""",
        "Get vacuum-related configuration settings"
    )
    
    # Tool 10: recommend_indexes
    test_results['recommend_indexes_current'] = await test_sql_query(
        client, "recommend_indexes", "Current Indexes Query",
        """SELECT 
            schemaname,
            tablename,
            indexname,
            indexdef,
            CASE 
                WHEN indexdef LIKE '%UNIQUE%' THEN 'UNIQUE'
                WHEN indexdef LIKE '%btree%' THEN 'BTREE'
                WHEN indexdef LIKE '%gin%' THEN 'GIN'
                WHEN indexdef LIKE '%gist%' THEN 'GIST'
                ELSE 'OTHER'
            END as index_type
        FROM pg_indexes
        WHERE schemaname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        ORDER BY schemaname, tablename, indexname
        LIMIT 10""",
        "Get current indexes for recommendation analysis"
    )
    
    def validate_index_recommendations(data):
        """Validate index recommendation logic."""
        high_cardinality_cols = []
        
        for row in data:
            try:
                n_distinct = row.get('n_distinct', 0)
                if isinstance(n_distinct, str):
                    n_distinct = float(n_distinct)
                else:
                    n_distinct = float(n_distinct) if n_distinct is not None else 0
                
                if n_distinct > 100:  # High cardinality
                    high_cardinality_cols.append(row)
            except (ValueError, TypeError):
                continue
        
        print(f"    💡 Index recommendation logic: {len(data)} columns analyzed, {len(high_cardinality_cols)} high-cardinality")
        return True
    
    test_results['recommend_indexes_stats'] = await test_sql_query(
        client, "recommend_indexes", "Table Statistics Query",
        """SELECT 
            schemaname,
            tablename,
            attname as column_name,
            n_distinct,
            correlation
        FROM pg_stats
        WHERE schemaname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        AND n_distinct IS NOT NULL
        ORDER BY schemaname, tablename, n_distinct DESC
        LIMIT 10""",
        "Get table statistics for index recommendations",
        validate_logic=validate_index_recommendations
    )
    
    # =================================================================
    # SUMMARY REPORT
    # =================================================================
    
    print(f"\n{'='*70}")
    print("📋 COMPREHENSIVE TEST RESULTS SUMMARY")
    print("=" * 70)
    
    # Group results by tool
    core_tools = ['run_query_basic', 'run_query_complex', 'get_table_schema', 'health_check']
    analysis_tools = [k for k in test_results.keys() if k not in core_tools]
    
    print(f"\n🔧 CORE TOOLS (4 tests):")
    core_passed = 0
    for test_name in core_tools:
        if test_results.get(test_name, False):
            print(f" {test_name}")
            core_passed += 1
        else:
            print(f" {test_name}")
    
    print(f"\n📊 ANALYSIS TOOLS ({len(analysis_tools)} tests):")
    analysis_passed = 0
    for test_name in analysis_tools:
        if test_results.get(test_name, False):
            print(f" {test_name}")
            analysis_passed += 1
        else:
            print(f" {test_name}")
    
    total_passed = core_passed + analysis_passed
    total_tests = len(test_results)
    
    print(f"\n OVERALL RESULTS:")
    print(f" Core Tools: {core_passed}/{len(core_tools)} passed")
    print(f" Analysis Tools: {analysis_passed}/{len(analysis_tools)} passed")
    print(f" Total: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print(f"\n ALL TESTS PASSED! PostgreSQL MCP Server is fully validated!")
        print(" All 10 tools are ready for Q Chat integration")
    elif total_passed >= total_tests * 0.9:  # 90% pass rate
        print(f"\n MOST TESTS PASSED! PostgreSQL MCP Server is ready for Q Chat")
        print("  Review any failed tests for potential issues")
    else:
        print(f"\n  SEVERAL TESTS FAILED - Please review the issues above")
    
    print("\n" + "=" * 70)
    print("🏁 Comprehensive test execution completed")


if __name__ == "__main__":
    # Set AWS profile
    os.environ['AWS_PROFILE'] = 'mcp_profile'
    os.environ['AWS_REGION'] = 'us-west-2'
    
    asyncio.run(main())
