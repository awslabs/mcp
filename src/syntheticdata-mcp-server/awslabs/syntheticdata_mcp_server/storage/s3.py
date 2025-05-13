"""S3 storage target implementation."""

import asyncio
import boto3
import os
import pandas as pd
from .base import DataTarget
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional


class S3Target(DataTarget):
    """AWS S3 storage target implementation."""

    def __init__(self):
        """Initialize S3 target with boto3 client."""
        session = boto3.Session(profile_name=os.environ.get('AWS_PROFILE'))
        self.s3_client = session.client('s3')
        self.supported_formats = ['csv', 'json', 'parquet']
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def validate(self, data: Dict[str, List[Dict]], config: Dict[str, Any]) -> bool:
        """Validate data and S3 configuration.

        Args:
            data: Dictionary mapping table names to lists of records
            config: S3 configuration including bucket, prefix, format, etc.

        Returns:
            True if validation passes, False otherwise
        """
        try:
            # Check required config
            required_fields = ['bucket', 'prefix', 'format']
            if not all(field in config for field in required_fields):
                return False

            # Validate format
            if config['format'] not in self.supported_formats:
                return False

            # Validate data
            if not data or not all(isinstance(records, list) for records in data.values()):
                return False

            # Check S3 access
            try:
                self.s3_client.head_bucket(Bucket=config['bucket'])
            except Exception:
                return False

            return True

        except Exception:
            return False

    async def load(self, data: Dict[str, List[Dict]], config: Dict[str, Any]) -> Dict:
        """Load data to S3 with specified configuration.

        Args:
            data: Dictionary mapping table names to lists of records
            config: S3 configuration including:
                - bucket: S3 bucket name
                - prefix: Key prefix for S3 objects
                - format: Output format (csv, json, parquet)
                - partitioning: Optional partitioning configuration
                - storage: Optional storage class and encryption settings
                - metadata: Optional object metadata

        Returns:
            Dictionary containing load results
        """
        try:
            # Convert to DataFrames
            dataframes = {name: pd.DataFrame(records) for name, records in data.items()}

            # Apply partitioning if enabled
            if config.get('partitioning', {}).get('enabled'):
                partitioned_data = self._apply_partitioning(dataframes, config['partitioning'])
            else:
                partitioned_data = {name: {'': df} for name, df in dataframes.items()}

            # Process each table and partition
            upload_tasks = []
            for table_name, partitions in partitioned_data.items():
                for partition_key, df in partitions.items():
                    # Construct S3 key
                    partition_path = f'{partition_key}/' if partition_key else ''
                    key = f'{config["prefix"]}{table_name}/{partition_path}{table_name}.{config["format"]}'

                    # Convert to specified format
                    content = self._convert_format(df, config['format'], config.get('compression'))

                    # Create upload task
                    task = self._upload_to_s3(
                        content,
                        config['bucket'],
                        key,
                        config.get('storage', {}),
                        config.get('metadata', {}),
                    )
                    upload_tasks.append(task)

            # Execute uploads in parallel
            results = await asyncio.gather(*upload_tasks)

            return {
                'success': True,
                'uploaded_files': results,
                'total_records': sum(len(df) for df in dataframes.values()),
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _convert_format(
        self, df: pd.DataFrame, format: str, compression: Optional[str] = None
    ) -> bytes:
        """Convert DataFrame to specified format.

        Args:
            df: pandas DataFrame to convert
            format: Target format (csv, json, parquet)
            compression: Optional compression type

        Returns:
            Bytes containing the converted data
        """
        if format == 'parquet':
            return df.to_parquet(compression=compression)
        elif format == 'csv':
            csv_data = df.to_csv(index=False)
            return csv_data.encode() if csv_data is not None else b''
        elif format == 'json':
            json_data = df.to_json(orient='records')
            return json_data.encode() if json_data is not None else b''
        else:
            raise ValueError(f'Unsupported format: {format}')

    def _apply_partitioning(
        self, dataframes: Dict[str, pd.DataFrame], partition_config: Dict[str, Any]
    ) -> Dict[str, Dict[str, pd.DataFrame]]:
        """Apply partitioning to DataFrames.

        Args:
            dataframes: Dictionary of table name to DataFrame
            partition_config: Partitioning configuration

        Returns:
            Dictionary mapping table names to dictionaries of partition key to DataFrame
        """
        partitioned_data = {}
        partition_cols = partition_config['columns']

        for table_name, df in dataframes.items():
            # Skip if partition columns don't exist
            if not all(col in df.columns for col in partition_cols):
                partitioned_data[table_name] = {'': df}
                continue

            # Group by partition columns
            grouped = df.groupby(partition_cols)
            partitions = {}

            for group_key, group_df in grouped:
                # Create partition key
                if isinstance(group_key, tuple):
                    partition_key = '/'.join(str(k) for k in group_key)
                else:
                    partition_key = str(group_key)

                # Remove partition columns if specified
                if partition_config.get('drop_columns', False):
                    group_df = group_df.drop(columns=partition_cols)

                partitions[partition_key] = group_df

            partitioned_data[table_name] = partitions

        return partitioned_data

    async def _upload_to_s3(
        self, content: bytes, bucket: str, key: str, storage_config: Dict, metadata: Dict
    ) -> Dict:
        """Upload content to S3 with specified configuration.

        Args:
            content: Bytes to upload
            bucket: S3 bucket name
            key: S3 object key
            storage_config: Storage class and encryption settings
            metadata: Object metadata

        Returns:
            Dictionary containing upload details
        """
        try:
            # Run S3 upload in thread pool
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.s3_client.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=content,
                    StorageClass=storage_config.get('class', 'STANDARD'),
                    Metadata=metadata,
                    **(
                        {'ServerSideEncryption': storage_config['encryption']}
                        if storage_config.get('encryption')
                        else {}
                    ),
                ),
            )

            return {'bucket': bucket, 'key': key, 'size': len(content), 'metadata': metadata}

        except Exception as e:
            raise Exception(f'Failed to upload to S3: {str(e)}')
