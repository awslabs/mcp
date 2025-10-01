"""Database analyzer classes for source database analysis."""

import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Any
from loguru import logger

from awslabs.dynamodb_mcp_server.database_analysis_queries import get_query_resource
from awslabs.mysql_mcp_server.server import DBConnectionSingleton, DummyCtx
from awslabs.mysql_mcp_server.server import run_query as mysql_query


class DatabaseAnalyzer:
    """Base class for database analyzers."""
    
    @staticmethod
    def build_connection_params(source_db_type, **kwargs):
        """Build connection parameters for database analysis."""
        if source_db_type == 'mysql':
            return {
                'cluster_arn': kwargs.get('aws_cluster_arn') or os.getenv('MYSQL_CLUSTER_ARN'),
                'secret_arn': kwargs.get('aws_secret_arn') or os.getenv('MYSQL_SECRET_ARN'),
                'database': kwargs.get('database_name') or os.getenv('MYSQL_DATABASE'),
                'region': kwargs.get('aws_region') or os.getenv('AWS_REGION'),
                'max_results': kwargs.get('max_query_results') or int(os.getenv('MYSQL_MAX_QUERY_RESULTS', '500')),
                'analysis_days': kwargs.get('analysis_days', 30)
            }
        else:
            raise ValueError(f"Unsupported database type: {source_db_type}")
    
    @staticmethod
    def validate_connection_params(source_db_type, connection_params):
        """Validate connection parameters for database type."""
        if source_db_type == 'mysql':
            required_params = ['cluster_arn', 'secret_arn', 'database', 'region']
            missing_params = [param for param in required_params 
                            if not connection_params.get(param) or connection_params[param].strip() == '']
            
            param_descriptions = {
                'cluster_arn': 'AWS cluster ARN',
                'secret_arn': 'AWS secret ARN', 
                'database': 'Database name',
                'region': 'AWS region'
            }
            return missing_params, param_descriptions
        else:
            return [], {}
    
    @staticmethod
    def save_analysis_files(results, source_db_type, database, analysis_days, max_results):
        """Save analysis results to files."""
        saved_files = []
        save_errors = []
        
        logger.info(f"save_analysis_files called with {len(results) if results else 0} results")
        
        if not results:
            logger.warning("No results to save - returning empty lists")
            return saved_files, save_errors
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        analysis_folder = f"database_analysis_{timestamp}"
        logger.info(f"Creating analysis folder: {analysis_folder}")
        
        os.makedirs(analysis_folder, exist_ok=True)
        logger.info(f"Created folder at: {analysis_folder}")
        
        for query_name, query_result in results.items():
            filename = f"{analysis_folder}/{query_name}_results.json"
            
            analysis_data = query_result['data']
            if query_name == 'pattern_analysis':
                analysis_data = DatabaseAnalyzer.filter_pattern_data(analysis_data, analysis_days)
            
            try:
                with open(filename, 'w') as f:
                    json.dump({
                        'query_name': query_name,
                        'description': query_result['description'],
                        'source_db_type': source_db_type,
                        'database': database,
                        'analysis_days': analysis_days,
                        'max_query_results': max_results,
                        'data': analysis_data
                    }, f, indent=2, default=str)
                saved_files.append(filename)
                logger.info(f"Saved {query_name} results to {filename}")
            except Exception as e:
                logger.error(f"Failed to save {query_name}: {str(e)}")
                save_errors.append(f"Failed to save {query_name}: {str(e)}")
        
        return saved_files, save_errors
    
    @staticmethod
    def filter_pattern_data(data, analysis_days):
        """Filter pattern analysis data to exclude DDL statements and add RPS calculations."""
        if not data:
            return data
            
        total_seconds = (analysis_days or 30) * 24 * 3600
        filtered_patterns = []
        
        for pattern in data:
            digest = pattern.get('DIGEST_TEXT', '')
            if not any(digest.upper().startswith(prefix) 
                      for prefix in ['CREATE ', 'DROP ', 'ALTER ', 'TRUNCATE ']):
                pattern_with_rps = pattern.copy()
                count = pattern.get('COUNT_STAR', 0)
                pattern_with_rps['calculated_rps'] = (
                    round(count / total_seconds, 6) if total_seconds > 0 else 0
                )
                filtered_patterns.append(pattern_with_rps)
        
        return filtered_patterns
    


class MySQLAnalyzer(DatabaseAnalyzer):
    """MySQL-specific database analyzer."""
    
    SCHEMA_QUERIES = ['table_analysis', 'column_analysis', 'foreign_key_analysis', 'index_analysis']
    ACCESS_PATTERN_QUERIES = ['performance_schema_check', 'pattern_analysis']
    
    @staticmethod
    def check_performance_schema(result):
        """Check if MySQL performance schema is enabled from query result."""
        if result and len(result) > 0:
            perf_value = str(result[0].get('', '0'))  # Key is empty string by mysql package design, so checking only value here
            return perf_value == '1'
        return False
    
    def __init__(self, connection_params):
        """Initialize MySQL analyzer with connection parameters."""
        self.cluster_arn = connection_params['cluster_arn']
        self.secret_arn = connection_params['secret_arn']
        self.database = connection_params['database']
        self.region = connection_params['region']
        self.max_results = connection_params['max_results']
        self.analysis_days = connection_params['analysis_days']
    
    async def _run_query(self, sql, query_parameters=None):
        """Internal method to run SQL queries against MySQL database."""
        try:
            # Only reset DBConnectionSingleton instance if connection parameters changed
            current_params = getattr(DBConnectionSingleton, '_last_params', None)
            new_params = (self.cluster_arn, self.secret_arn, self.database, self.region)
            
            if current_params != new_params:
                DBConnectionSingleton._instance = None
                setattr(DBConnectionSingleton, '_last_params', new_params)
            
            DBConnectionSingleton.initialize(self.cluster_arn, self.secret_arn, self.database, self.region, 'true')
        except Exception as e:
            logger.error(f'MySQL initialization failed - {type(e).__name__}: {str(e)}')
            return [{'error': f'MySQL initialization failed: {str(e)}'}]

        try:
            result = await mysql_query(sql, DummyCtx(), None, query_parameters)
            return result
        except Exception as e:
            logger.error(f'MySQL query execution failed - {type(e).__name__}: {str(e)}')
            return [{'error': f'MySQL query failed: {str(e)}'}]
    
    async def execute_query_batch(self, query_names, analysis_days=None):
        """Execute a batch of analysis queries."""
        results = {}
        errors = []
        
        for query_name in query_names:
            try:
                # Get query with appropriate parameters
                if query_name == 'pattern_analysis' and analysis_days:
                    query = get_query_resource(
                        query_name, max_query_results=self.max_results, 
                        target_database=self.database, analysis_days=analysis_days
                    )
                else:
                    query = get_query_resource(
                        query_name, max_query_results=self.max_results, target_database=self.database
                    )
                
                result = await self._run_query(query['sql'])
                
                if result and isinstance(result, list) and len(result) > 0:
                    if 'error' in result[0]:
                        errors.append(f'{query_name}: {result[0]["error"]}')
                    else:
                        results[query_name] = {
                            'description': query['description'],
                            'data': result,
                        }
                else:
                    # Handle empty results
                    results[query_name] = {
                        'description': query['description'],
                        'data': [],
                    }
                    
            except Exception as e:
                errors.append(f'{query_name}: {str(e)}')
        
        return results, errors
    
    @classmethod
    async def analyze(cls, connection_params):
        """Execute MySQL-specific analysis workflow."""
        analyzer = cls(connection_params)
        
        # Execute schema analysis
        schema_results, schema_errors = await analyzer.execute_query_batch(cls.SCHEMA_QUERIES)

        # Execute performance schema check
        perf_check_results, perf_check_errors = await analyzer.execute_query_batch(['performance_schema_check'])
        
        performance_enabled = False
        all_results = {**schema_results}
        all_errors = schema_errors + perf_check_errors
        
        # Check performance schema status and run pattern analysis if enabled
        if 'performance_schema_check' in perf_check_results:
            performance_enabled = cls.check_performance_schema(
                perf_check_results['performance_schema_check']['data']
            )
            
            if performance_enabled:
                pattern_results, pattern_errors = await analyzer.execute_query_batch(
                    ['pattern_analysis'], analyzer.analysis_days
                )
                all_results.update(pattern_results)
                all_errors.extend(pattern_errors)
            else:
                all_errors.append("Performance Schema disabled - skipping pattern_analysis")
        
        return {
            'results': all_results,
            'errors': all_errors,
            'performance_enabled': performance_enabled,
            'performance_feature': 'Performance Schema'
        }


class DatabaseAnalyzerRegistry:
    """Registry for database-specific analyzers."""
    
    _analyzers = {
        'mysql': MySQLAnalyzer,
    }
    
    @classmethod
    def get_analyzer(cls, source_db_type: str):
        """Get the appropriate analyzer class for the database type."""
        analyzer = cls._analyzers.get(source_db_type.lower())
        if not analyzer:
            raise ValueError(f"Unsupported database type: {source_db_type}")
        return analyzer
    
    @classmethod
    def get_supported_types(cls) -> List[str]:
        """Get list of supported database types."""
        return list(cls._analyzers.keys())
