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

"""HealthOmics search engine for genomics files in sequence and reference stores."""

import asyncio
from awslabs.aws_healthomics_mcp_server.models import GenomicsFile, GenomicsFileType, SearchConfig
from awslabs.aws_healthomics_mcp_server.search.file_type_detector import FileTypeDetector
from awslabs.aws_healthomics_mcp_server.search.pattern_matcher import PatternMatcher
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_omics_client
from botocore.exceptions import ClientError
from datetime import datetime
from loguru import logger
from typing import Any, Dict, List, Optional


class HealthOmicsSearchEngine:
    """Search engine for genomics files in HealthOmics sequence and reference stores."""

    def __init__(self, config: SearchConfig):
        """Initialize the HealthOmics search engine.

        Args:
            config: Search configuration containing settings
        """
        self.config = config
        self.omics_client = get_omics_client()
        self.file_type_detector = FileTypeDetector()
        self.pattern_matcher = PatternMatcher()

    async def search_sequence_stores(
        self, file_type: Optional[str], search_terms: List[str]
    ) -> List[GenomicsFile]:
        """Search for genomics files in HealthOmics sequence stores.

        Args:
            file_type: Optional file type filter
            search_terms: List of search terms to match against

        Returns:
            List of GenomicsFile objects matching the search criteria

        Raises:
            ClientError: If HealthOmics API access fails
        """
        try:
            logger.info('Starting search in HealthOmics sequence stores')

            # List all sequence stores
            sequence_stores = await self._list_sequence_stores()
            logger.info(f'Found {len(sequence_stores)} sequence stores')

            all_files = []

            # Create tasks for concurrent store searches
            tasks = []
            for store in sequence_stores:
                store_id = store['id']
                task = self._search_single_sequence_store(store_id, store, file_type, search_terms)
                tasks.append(task)

            # Execute searches concurrently with semaphore to limit concurrent operations
            semaphore = asyncio.Semaphore(self.config.max_concurrent_searches)

            async def bounded_search(task):
                async with semaphore:
                    return await task

            results = await asyncio.gather(
                *[bounded_search(task) for task in tasks], return_exceptions=True
            )

            # Collect results and handle exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    store_id = sequence_stores[i]['id']
                    logger.error(f'Error searching sequence store {store_id}: {result}')
                else:
                    all_files.extend(result)

            logger.info(f'Found {len(all_files)} files in sequence stores')
            return all_files

        except Exception as e:
            logger.error(f'Error searching HealthOmics sequence stores: {e}')
            raise

    async def search_reference_stores(
        self, file_type: Optional[str], search_terms: List[str]
    ) -> List[GenomicsFile]:
        """Search for genomics files in HealthOmics reference stores.

        Args:
            file_type: Optional file type filter
            search_terms: List of search terms to match against

        Returns:
            List of GenomicsFile objects matching the search criteria

        Raises:
            ClientError: If HealthOmics API access fails
        """
        try:
            logger.info('Starting search in HealthOmics reference stores')

            # List all reference stores
            reference_stores = await self._list_reference_stores()
            logger.info(f'Found {len(reference_stores)} reference stores')

            all_files = []

            # Create tasks for concurrent store searches
            tasks = []
            for store in reference_stores:
                store_id = store['id']
                task = self._search_single_reference_store(
                    store_id, store, file_type, search_terms
                )
                tasks.append(task)

            # Execute searches concurrently with semaphore to limit concurrent operations
            semaphore = asyncio.Semaphore(self.config.max_concurrent_searches)

            async def bounded_search(task):
                async with semaphore:
                    return await task

            results = await asyncio.gather(
                *[bounded_search(task) for task in tasks], return_exceptions=True
            )

            # Collect results and handle exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    store_id = reference_stores[i]['id']
                    logger.error(f'Error searching reference store {store_id}: {result}')
                else:
                    all_files.extend(result)

            logger.info(f'Found {len(all_files)} files in reference stores')
            return all_files

        except Exception as e:
            logger.error(f'Error searching HealthOmics reference stores: {e}')
            raise

    async def _list_sequence_stores(self) -> List[Dict[str, Any]]:
        """List all HealthOmics sequence stores.

        Returns:
            List of sequence store dictionaries

        Raises:
            ClientError: If API call fails
        """
        stores = []
        next_token = None

        while True:
            try:
                # Prepare list_sequence_stores parameters
                params = {'maxResults': 100}  # AWS maximum for this API
                if next_token:
                    params['nextToken'] = next_token

                # Execute the list operation asynchronously
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, self.omics_client.list_sequence_stores, params
                )

                # Add stores from this page
                if 'sequenceStores' in response:
                    stores.extend(response['sequenceStores'])

                # Check if there are more pages
                next_token = response.get('nextToken')
                if not next_token:
                    break

            except ClientError as e:
                logger.error(f'Error listing sequence stores: {e}')
                raise

        logger.debug(f'Listed {len(stores)} sequence stores')
        return stores

    async def _list_reference_stores(self) -> List[Dict[str, Any]]:
        """List all HealthOmics reference stores.

        Returns:
            List of reference store dictionaries

        Raises:
            ClientError: If API call fails
        """
        stores = []
        next_token = None

        while True:
            try:
                # Prepare list_reference_stores parameters
                params = {'maxResults': 100}  # AWS maximum for this API
                if next_token:
                    params['nextToken'] = next_token

                # Execute the list operation asynchronously
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, self.omics_client.list_reference_stores, params
                )

                # Add stores from this page
                if 'referenceStores' in response:
                    stores.extend(response['referenceStores'])

                # Check if there are more pages
                next_token = response.get('nextToken')
                if not next_token:
                    break

            except ClientError as e:
                logger.error(f'Error listing reference stores: {e}')
                raise

        logger.debug(f'Listed {len(stores)} reference stores')
        return stores

    async def _search_single_sequence_store(
        self,
        store_id: str,
        store_info: Dict[str, Any],
        file_type_filter: Optional[str],
        search_terms: List[str],
    ) -> List[GenomicsFile]:
        """Search a single HealthOmics sequence store for genomics files.

        Args:
            store_id: ID of the sequence store
            store_info: Store information from list_sequence_stores
            file_type_filter: Optional file type filter
            search_terms: List of search terms to match against

        Returns:
            List of GenomicsFile objects found in this store
        """
        try:
            logger.debug(f'Searching sequence store {store_id}')

            # List read sets in the sequence store
            read_sets = await self._list_read_sets(store_id)
            logger.debug(f'Found {len(read_sets)} read sets in store {store_id}')

            genomics_files = []
            for read_set in read_sets:
                genomics_file = await self._convert_read_set_to_genomics_file(
                    read_set, store_id, store_info, file_type_filter, search_terms
                )
                if genomics_file:
                    genomics_files.append(genomics_file)

            logger.debug(
                f'Found {len(genomics_files)} matching files in sequence store {store_id}'
            )
            return genomics_files

        except Exception as e:
            logger.error(f'Error searching sequence store {store_id}: {e}')
            raise

    async def _search_single_reference_store(
        self,
        store_id: str,
        store_info: Dict[str, Any],
        file_type_filter: Optional[str],
        search_terms: List[str],
    ) -> List[GenomicsFile]:
        """Search a single HealthOmics reference store for genomics files.

        Args:
            store_id: ID of the reference store
            store_info: Store information from list_reference_stores
            file_type_filter: Optional file type filter
            search_terms: List of search terms to match against

        Returns:
            List of GenomicsFile objects found in this store
        """
        try:
            logger.debug(f'Searching reference store {store_id}')

            # List references in the reference store
            references = await self._list_references(store_id)
            logger.debug(f'Found {len(references)} references in store {store_id}')

            genomics_files = []
            for reference in references:
                genomics_file = await self._convert_reference_to_genomics_file(
                    reference, store_id, store_info, file_type_filter, search_terms
                )
                if genomics_file:
                    genomics_files.append(genomics_file)

            logger.debug(
                f'Found {len(genomics_files)} matching files in reference store {store_id}'
            )
            return genomics_files

        except Exception as e:
            logger.error(f'Error searching reference store {store_id}: {e}')
            raise

    async def _list_read_sets(self, sequence_store_id: str) -> List[Dict[str, Any]]:
        """List read sets in a HealthOmics sequence store.

        Args:
            sequence_store_id: ID of the sequence store

        Returns:
            List of read set dictionaries

        Raises:
            ClientError: If API call fails
        """
        read_sets = []
        next_token = None

        while True:
            try:
                # Prepare list_read_sets parameters
                params = {
                    'sequenceStoreId': sequence_store_id,
                    'maxResults': 100,  # AWS maximum for this API
                }
                if next_token:
                    params['nextToken'] = next_token

                # Execute the list operation asynchronously
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, self.omics_client.list_read_sets, params
                )

                # Add read sets from this page
                if 'readSets' in response:
                    read_sets.extend(response['readSets'])

                # Check if there are more pages
                next_token = response.get('nextToken')
                if not next_token:
                    break

            except ClientError as e:
                logger.error(f'Error listing read sets in sequence store {sequence_store_id}: {e}')
                raise

        return read_sets

    async def _list_references(self, reference_store_id: str) -> List[Dict[str, Any]]:
        """List references in a HealthOmics reference store.

        Args:
            reference_store_id: ID of the reference store

        Returns:
            List of reference dictionaries

        Raises:
            ClientError: If API call fails
        """
        references = []
        next_token = None

        while True:
            try:
                # Prepare list_references parameters
                params = {
                    'referenceStoreId': reference_store_id,
                    'maxResults': 100,  # AWS maximum for this API
                }
                if next_token:
                    params['nextToken'] = next_token

                # Execute the list operation asynchronously
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, self.omics_client.list_references, params
                )

                # Add references from this page
                if 'references' in response:
                    references.extend(response['references'])

                # Check if there are more pages
                next_token = response.get('nextToken')
                if not next_token:
                    break

            except ClientError as e:
                logger.error(
                    f'Error listing references in reference store {reference_store_id}: {e}'
                )
                raise

        return references

    async def _convert_read_set_to_genomics_file(
        self,
        read_set: Dict[str, Any],
        store_id: str,
        store_info: Dict[str, Any],
        file_type_filter: Optional[str],
        search_terms: List[str],
    ) -> Optional[GenomicsFile]:
        """Convert a HealthOmics read set to a GenomicsFile if it matches search criteria.

        Args:
            read_set: Read set dictionary from list_read_sets
            store_id: ID of the sequence store
            store_info: Store information
            file_type_filter: Optional file type to filter by
            search_terms: List of search terms to match against

        Returns:
            GenomicsFile object if the read set matches criteria, None otherwise
        """
        try:
            read_set_id = read_set['id']
            read_set_name = read_set.get('name', read_set_id)

            # Determine file type based on read set type or default to FASTQ
            file_format = read_set.get('fileType', 'FASTQ')
            if file_format.upper() == 'FASTQ':
                detected_file_type = GenomicsFileType.FASTQ
            else:
                # Try to detect from name if available
                detected_file_type = self.file_type_detector.detect_file_type(read_set_name)
                if not detected_file_type:
                    detected_file_type = GenomicsFileType.FASTQ  # Default for sequence data

            # Apply file type filter if specified
            if file_type_filter and detected_file_type.value != file_type_filter:
                return None

            # Create metadata for pattern matching
            metadata = {
                'name': read_set_name,
                'description': read_set.get('description', ''),
                'subject_id': read_set.get('subjectId', ''),
                'sample_id': read_set.get('sampleId', ''),
                'reference_arn': read_set.get('referenceArn', ''),
            }

            # Check if read set matches search terms
            if search_terms and not self._matches_search_terms_metadata(
                read_set_name, metadata, search_terms
            ):
                return None

            # Generate S3 access point path for HealthOmics data
            # HealthOmics uses S3 access points with specific format
            access_point_path = f's3://omics-{store_id}.s3-accesspoint.{self._get_region()}.amazonaws.com/{read_set_id}'

            # Create GenomicsFile object
            genomics_file = GenomicsFile(
                path=access_point_path,
                file_type=detected_file_type,
                size_bytes=read_set.get(
                    'totalReadLength', 0
                ),  # Use total read length as size approximation
                storage_class='STANDARD',  # HealthOmics manages storage internally
                last_modified=read_set.get('creationTime', datetime.now()),
                tags={},  # HealthOmics doesn't expose tags through read sets API
                source_system='sequence_store',
                metadata={
                    'store_id': store_id,
                    'store_name': store_info.get('name', ''),
                    'read_set_id': read_set_id,
                    'read_set_name': read_set_name,
                    'subject_id': read_set.get('subjectId', ''),
                    'sample_id': read_set.get('sampleId', ''),
                    'reference_arn': read_set.get('referenceArn', ''),
                    'status': read_set.get('status', ''),
                    'sequence_information': read_set.get('sequenceInformation', {}),
                },
            )

            return genomics_file

        except Exception as e:
            logger.error(
                f'Error converting read set {read_set.get("id", "unknown")} to GenomicsFile: {e}'
            )
            return None

    async def _convert_reference_to_genomics_file(
        self,
        reference: Dict[str, Any],
        store_id: str,
        store_info: Dict[str, Any],
        file_type_filter: Optional[str],
        search_terms: List[str],
    ) -> Optional[GenomicsFile]:
        """Convert a HealthOmics reference to a GenomicsFile if it matches search criteria.

        Args:
            reference: Reference dictionary from list_references
            store_id: ID of the reference store
            store_info: Store information
            file_type_filter: Optional file type to filter by
            search_terms: List of search terms to match against

        Returns:
            GenomicsFile object if the reference matches criteria, None otherwise
        """
        try:
            reference_id = reference['id']
            reference_name = reference.get('name', reference_id)

            # References are typically FASTA files
            detected_file_type = GenomicsFileType.FASTA

            # Apply file type filter if specified
            if file_type_filter and detected_file_type.value != file_type_filter:
                return None

            # Create metadata for pattern matching
            metadata = {
                'name': reference_name,
                'description': reference.get('description', ''),
            }

            # Check if reference matches search terms
            if search_terms and not self._matches_search_terms_metadata(
                reference_name, metadata, search_terms
            ):
                return None

            # Generate S3 access point path for HealthOmics reference data
            access_point_path = f's3://omics-{store_id}.s3-accesspoint.{self._get_region()}.amazonaws.com/{reference_id}'

            # Create GenomicsFile object
            genomics_file = GenomicsFile(
                path=access_point_path,
                file_type=detected_file_type,
                size_bytes=0,  # Size not readily available from references API
                storage_class='STANDARD',  # HealthOmics manages storage internally
                last_modified=reference.get('creationTime', datetime.now()),
                tags={},  # HealthOmics doesn't expose tags through references API
                source_system='reference_store',
                metadata={
                    'store_id': store_id,
                    'store_name': store_info.get('name', ''),
                    'reference_id': reference_id,
                    'reference_name': reference_name,
                    'status': reference.get('status', ''),
                    'md5': reference.get('md5', ''),
                },
            )

            return genomics_file

        except Exception as e:
            logger.error(
                f'Error converting reference {reference.get("id", "unknown")} to GenomicsFile: {e}'
            )
            return None

    def _matches_search_terms_metadata(
        self, name: str, metadata: Dict[str, Any], search_terms: List[str]
    ) -> bool:
        """Check if a HealthOmics resource matches the search terms based on name and metadata.

        Args:
            name: Resource name
            metadata: Resource metadata dictionary
            search_terms: List of search terms to match against

        Returns:
            True if the resource matches the search terms, False otherwise
        """
        if not search_terms:
            return True

        # Check name match
        name_score, _ = self.pattern_matcher.calculate_match_score(name, search_terms)
        if name_score > 0:
            return True

        # Check metadata values
        for key, value in metadata.items():
            if isinstance(value, str) and value:
                value_score, _ = self.pattern_matcher.calculate_match_score(value, search_terms)
                if value_score > 0:
                    return True

        return False

    def _get_region(self) -> str:
        """Get the current AWS region.

        Returns:
            AWS region string
        """
        # Import here to avoid circular imports
        from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_region

        return get_region()
