"""
Export engine for CloudWAN MCP Server.

This module provides the core export functionality for AWS CloudWAN network data
in various formats, with support for filtering, pagination, and region selection.

The engine handles AWS API pagination properly, ensuring complete data collection
even when the number of resources exceeds the default page size limits set by AWS services.
"""

import os
import json
import time
import logging
import asyncio
from datetime import datetime
from typing import (
    Dict,
    List,
    Any,
    Optional,
    Callable,
    Protocol,
    runtime_checkable,
    TypeVar,
    Type,
    AsyncGenerator,
)
import traceback
import base64

from pydantic import BaseModel
from botocore.exceptions import ClientError

from ...aws.client_manager import AWSClientManager
from ...config import CloudWANConfig
from ...utils.aws_operations import handle_aws_errors
from .security import (
    validate_path,
    encrypt_file,
    compute_file_hash,
    create_integrity_signature,
)
from ...utils.resilience import (
    resilient_aws_call,
    RetryExhaustedError,
)

# Import format exporters
from .format_exporters import (
    FormatExporter,
    JSONExporter,
    CSVExporter,
    YAMLExporter,
    ExcelExporter,
    MarkdownExporter,
    HTMLExporter,
    XMLExporter,
)

# Import streaming exporters for large datasets
from .streaming_exports import (
    StreamingExportManager,
)

# Import discovery and data collection tools
from ..core.discovery import CoreNetworkDiscoveryTool, VPCDiscoveryTool
from ..core.path_tracing import NetworkPathTracingTool
from ..cloudwan.bgp_analyzer import BGPSessionAnalysisTool
from ..visualization.topology_discovery import NetworkTopologyDiscovery


# Define Protocol classes for type-safe dictionary conversion
@runtime_checkable
class DictConvertible(Protocol):
    """Protocol for objects that can be converted to dictionaries using dict() method."""

    def dict(self) -> Dict[str, Any]: ...


@runtime_checkable
class ModelDumpable(Protocol):
    """Protocol for objects with model_dump method (Pydantic v2)."""

    def model_dump(self) -> Dict[str, Any]: ...


# Create a generic type variable for our conversion function
T = TypeVar("T")

# Import models
from .models import (
    NetworkDataExportFormat,
    NetworkDataType,
    ExportRequest,
    NetworkDataExportResponse,
    NetworkDataFilter,
)

logger = logging.getLogger(__name__)


from abc import ABC, abstractmethod


class BaseDataCollector(ABC):
    """Abstract base class for data collectors.

    This class provides common functionality for collecting and processing
    network data. Subclasses must implement the data collection methods
    specific to their data types.
    """

    def __init__(self, aws_manager: AWSClientManager, config: Optional[CloudWANConfig] = None):
        """Initialize the base data collector.

        Args:
            aws_manager: AWS client manager for making AWS API calls
            config: Optional CloudWAN configuration
        """
        self.aws_manager = aws_manager
        self.config = config or CloudWANConfig()
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    async def collect_data(self, request: Any, regions: List[str]) -> Dict[str, Any]:
        """Collect data based on request parameters.

        Args:
            request: The export request containing parameters
            regions: List of AWS regions to collect data from

        Returns:
            Dictionary containing the collected data

        Raises:
            ValueError: If data collection fails
        """
        pass

    def apply_filters(self, data: Dict[str, Any], filters: Any) -> Dict[str, Any]:
        """Apply filters to collected data.

        Args:
            data: The raw collected data
            filters: Filter criteria to apply

        Returns:
            Filtered data dictionary
        """
        if not filters:
            return data

        filtered_data = data.copy()

        # Resource ID filtering
        if hasattr(filters, "resource_ids") and filters.resource_ids:
            if "vpcs" in filtered_data and isinstance(filtered_data["vpcs"], list):
                filtered_data["vpcs"] = [
                    vpc
                    for vpc in filtered_data["vpcs"]
                    if vpc.get("vpc_id") in filters.resource_ids
                ]

            if "core_networks" in filtered_data and isinstance(
                filtered_data["core_networks"], list
            ):
                filtered_data["core_networks"] = [
                    cn
                    for cn in filtered_data["core_networks"]
                    if cn.get("core_network_id") in filters.resource_ids
                ]

        # VPC ID filtering
        if hasattr(filters, "vpc_ids") and filters.vpc_ids:
            if "vpcs" in filtered_data and isinstance(filtered_data["vpcs"], list):
                filtered_data["vpcs"] = [
                    vpc for vpc in filtered_data["vpcs"] if vpc.get("vpc_id") in filters.vpc_ids
                ]

        # Segment name filtering
        if hasattr(filters, "segment_names") and filters.segment_names:
            # Filter attachments by segment if present
            if "cloudwan_attachments" in filtered_data and isinstance(
                filtered_data["cloudwan_attachments"], list
            ):
                filtered_data["cloudwan_attachments"] = [
                    att
                    for att in filtered_data["cloudwan_attachments"]
                    if att.get("segment_name") in filters.segment_names
                ]

        # Include/exclude specific data types
        if not getattr(filters, "include_subnets", True) and "subnets" in filtered_data:
            del filtered_data["subnets"]

        if not getattr(filters, "include_route_tables", True) and "route_tables" in filtered_data:
            del filtered_data["route_tables"]

        if (
            not getattr(filters, "include_security_groups", True)
            and "security_groups" in filtered_data
        ):
            del filtered_data["security_groups"]

        if not getattr(filters, "include_policies", True) and "policy_documents" in filtered_data:
            del filtered_data["policy_documents"]

        return filtered_data

    def get_stats(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get statistics about the exported data.

        Args:
            data: The data to analyze

        Returns:
            Dictionary containing statistics
        """
        stats = {"element_count": 0, "warnings": []}

        # Count elements in various data structures
        for key, value in data.items():
            if key == "metadata":
                continue

            if isinstance(value, list):
                stats["element_count"] += len(value)

            # Add warnings for large datasets
            if isinstance(value, list) and len(value) > 10000:
                stats["warnings"].append(f"Large dataset: {key} contains {len(value)} items")

        return stats

    def generate_metadata(self, request: Any, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate metadata about the export.

        Args:
            request: The export request
            data: The exported data

        Returns:
            Dictionary containing metadata
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "data_type": request.data_type.value,
            "format": request.format.value,
            "regions": request.regions,
            "streaming_mode": getattr(request, "use_streaming", False),
            "filter_options": {
                k: v for k, v in request.filters.__dict__.items() if not k.startswith("_")
            },
        }

    def generate_streaming_metadata(self, request: Any, regions: List[str]) -> Dict[str, Any]:
        """Generate metadata for streaming exports.

        Args:
            request: The export request
            regions: List of regions included in the export

        Returns:
            Dictionary containing metadata
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "data_type": request.data_type.value,
            "format": request.format.value,
            "regions": regions,
            "streaming_mode": True,
            "filter_options": {
                k: v for k, v in request.filters.__dict__.items() if not k.startswith("_")
            },
        }

    async def convert_to_dict(self, obj: Any) -> Dict[str, Any]:
        """Convert object to dictionary using appropriate method based on its type.

        Args:
            obj: Any object to convert to a dictionary

        Returns:
            Dictionary representation of the object

        Raises:
            TypeError: If the object cannot be converted to a dictionary
        """
        if isinstance(obj, dict):
            return obj
        if isinstance(obj, DictConvertible):
            return obj.dict()
        if isinstance(obj, ModelDumpable):
            return obj.model_dump()
        if isinstance(obj, BaseModel):
            # For backward compatibility with code not using the protocols
            if hasattr(obj, "model_dump"):
                return obj.model_dump()
            return obj.dict()

        # If we got here, we couldn't convert the object
        raise TypeError(f"Cannot convert {type(obj).__name__} to dictionary")

    async def collect_data_template(
        self,
        collection_func: Callable,
        regions: List[str],
        filters: Any,
        error_prefix: str = "data",
    ) -> Dict[str, Any]:
        """Template method for data collection with consistent error handling.

        Args:
            collection_func: The specific collection function to call
            regions: List of AWS regions to collect data from
            filters: Data filtering options
            error_prefix: Prefix for error messages, used to identify the data type

        Returns:
            Dictionary containing the collected data

        Raises:
            ValueError: If data collection fails
        """
        try:
            response = await collection_func(regions, filters)

            # If the tool returns a Pydantic model or any type that can be converted to dict
            try:
                return await self.convert_to_dict(response)
            except TypeError:
                pass

            # If it returns a dict
            if isinstance(response, dict):
                if "error" in response:
                    raise ValueError(f"Error collecting {error_prefix} data: {response['error']}")
                return response

            # Handle TextContent list
            if isinstance(response, list) and all(hasattr(item, "type") for item in response):
                # Extract JSON from text content
                content = response[0].text
                return json.loads(content)

            # If it returns None or empty data, return empty dict
            if not response:
                return {}

            raise ValueError(f"Unexpected response type: {type(response).__name__}")
        except Exception as e:
            self.logger.error(f"Error collecting {error_prefix} data: {e}")
            raise ValueError(f"Failed to collect {error_prefix} data: {e}")

    async def paginated_aws_collection(self, client, method_name, **kwargs) -> List[Any]:
        """
        Collect paginated results from AWS API with resilience patterns.

        This method handles pagination for AWS API responses, ensuring all resources
        are collected even when they exceed the default page size limits. It incorporates
        resilience patterns with exponential backoff and proper error handling.

        Args:
            client: AWS Boto3 client
            method_name: API method name to call
            **kwargs: Additional keyword arguments to pass to the paginator

        Returns:
            List of collected results across all pages
        """
        self.logger.debug(f"Starting paginated collection for {method_name}")
        results = []

        try:
            # Create paginator - use resilient_aws_call for the initial operation
            # that creates the paginator to handle any throttling during initialization
            try:
                paginator = client.get_paginator(method_name)
                page_iterator = paginator.paginate(**kwargs)
            except ClientError as e:
                # If throttling occurs during paginator creation, handle it specially
                error_code = e.response.get("Error", {}).get("Code", "")
                if error_code in ("ThrottlingException", "RequestLimitExceeded"):
                    self.logger.warning(
                        f"Throttling during paginator creation for {method_name}. Retrying..."
                    )
                    # Short sleep before retry
                    await asyncio.sleep(1)
                    paginator = client.get_paginator(method_name)
                    page_iterator = paginator.paginate(**kwargs)
                else:
                    raise

            # Process each page with resilience
            page_count = 0
            async for page in page_iterator:
                page_count += 1
                # Handle different API response structures
                if "CoreNetworks" in page:
                    results.extend(page["CoreNetworks"])
                elif "Vpcs" in page:
                    results.extend(page["Vpcs"])
                elif "Attachments" in page:
                    results.extend(page["Attachments"])
                elif "SecurityGroups" in page:
                    results.extend(page["SecurityGroups"])
                elif "RouteTables" in page:
                    results.extend(page["RouteTables"])
                elif "NatGateways" in page:
                    results.extend(page["NatGateways"])
                elif "TransitGateways" in page:
                    results.extend(page["TransitGateways"])
                elif "TransitGatewayAttachments" in page:
                    results.extend(page["TransitGatewayAttachments"])
                elif "TransitGatewayRouteTables" in page:
                    results.extend(page["TransitGatewayRouteTables"])
                elif "GlobalNetworks" in page:
                    results.extend(page["GlobalNetworks"])
                elif "NetworkInterfaces" in page:
                    results.extend(page["NetworkInterfaces"])
                else:
                    # Generic fallback for other response structures
                    for key, value in page.items():
                        if isinstance(value, list):
                            results.extend(value)
                            break

                # Log progress for long-running collections
                if page_count % 5 == 0:
                    self.logger.debug(
                        f"Paginated collection for {method_name}: processed {page_count} pages, {len(results)} items so far"
                    )

            self.logger.debug(
                f"Paginated collection for {method_name} complete. Total items: {len(results)} across {page_count} pages"
            )
            return results

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_message = e.response.get("Error", {}).get("Message", "")
            self.logger.error(
                f"AWS error during paginated collection for {method_name}: {error_code} - {error_message}"
            )
            raise
        except RetryExhaustedError as e:
            self.logger.error(
                f"Retry limit exceeded during paginated collection for {method_name}: {e}"
            )
            raise
        except Exception as e:
            self.logger.error(
                f"Unexpected error during paginated collection for {method_name}: {e}"
            )
            self.logger.debug(traceback.format_exc())
            raise


class NetworkDataExportEngine(BaseDataCollector):
    """Engine for exporting network data in various formats."""

    def __init__(self, aws_manager: AWSClientManager, config: Optional[CloudWANConfig] = None):
        """Initialize the export engine."""
        super().__init__(aws_manager, config)

        # Initialize discovery tools
        self.core_network_discovery = CoreNetworkDiscoveryTool(aws_manager, config)
        self.vpc_discovery = VPCDiscoveryTool(aws_manager, config)
        self.path_tracing = NetworkPathTracingTool(aws_manager, config)
        self.bgp_analyzer = BGPSessionAnalysisTool(aws_manager, config)

        # Initialize topology discovery if available
        try:
            self.topology_discovery = NetworkTopologyDiscovery(aws_manager)
            self.topology_available = True
        except Exception as e:
            self.logger.warning(f"NetworkTopologyDiscovery initialization failed: {e}")
            self.topology_available = False

    async def collect_data(self, request: ExportRequest, regions: List[str]) -> Dict[str, Any]:
        """
        Collect network data based on request type.

        Args:
            request: The export request containing parameters
            regions: List of AWS regions to collect data from

        Returns:
            Dictionary containing the collected data

        Raises:
            ValueError: If data collection fails or the data type is not supported
        """
        # Use the registry pattern for data collectors
        collection_methods = {
            NetworkDataType.TOPOLOGY: self._collect_topology_data,
            NetworkDataType.ROUTES: self._collect_route_data,
            NetworkDataType.SEGMENT_ROUTES: self._collect_segment_route_data,
            NetworkDataType.ATTACHMENTS: self._collect_attachment_data,
            NetworkDataType.PATH_TRACE: self._collect_path_trace_data,
            NetworkDataType.BGP_SESSIONS: self._collect_bgp_data,
            NetworkDataType.TRANSIT_GATEWAY_ROUTES: self._collect_tgw_route_data,
            NetworkDataType.SECURITY_GROUPS: self._collect_security_group_data,
            NetworkDataType.CORE_NETWORKS: self._collect_core_network_data,
            NetworkDataType.VPCS: self._collect_vpc_data,
        }

        collector = collection_methods.get(request.data_type)
        if not collector:
            raise ValueError(f"Unsupported data type: {request.data_type}")

        return await collector(regions, request.filters)

    def _convert_to_dict(self, obj: Any) -> Dict[str, Any]:
        """
        Convert object to dictionary synchronously for backward compatibility.

        Args:
            obj: Any object to convert to a dictionary

        Returns:
            Dictionary representation of the object

        Raises:
            TypeError: If the object cannot be converted to a dictionary
        """
        # This is a synchronous wrapper around the async method from the base class
        # Use asyncio.run to run the async method synchronously
        import asyncio

        try:
            # Create a new event loop if one doesn't exist
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.convert_to_dict(obj))
        except RuntimeError:
            # If there's already an event loop running (e.g., in an async context)
            # we need to create a new event loop for this synchronous call
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(self.convert_to_dict(obj))
            loop.close()
            return result

    @handle_aws_errors
    async def export_data(self, request: ExportRequest) -> NetworkDataExportResponse:
        """
        Export network data according to request specifications.

        Args:
            request: Export request parameters

        Returns:
            NetworkDataExportResponse with export results
        """
        start_time = time.time()
        try:
            # Validate regions
            regions = request.regions or self.config.aws.regions
            self.logger.info(
                f"Exporting {request.data_type.value} data in {request.format.value} format for regions: {regions}"
            )

            # Check if streaming mode is requested or should be auto-enabled
            use_streaming = getattr(request, "use_streaming", False)

            # Auto-enable streaming for certain data types that might be large
            large_data_types = [
                NetworkDataType.TOPOLOGY,
                NetworkDataType.ROUTES,
                NetworkDataType.SECURITY_GROUPS,
                NetworkDataType.VPCS,
            ]

            if not use_streaming and request.data_type in large_data_types:
                # Check if the request has a use_streaming attribute and if regions > 2
                if len(regions) > 2:
                    use_streaming = True
                    self.logger.info(
                        f"Auto-enabling streaming mode for large dataset: {request.data_type.value} across {len(regions)} regions"
                    )

            # Generate output path if not provided
            output_path = request.output_path
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = (
                    f"cloudwan_{request.data_type.value}_export_{timestamp}.{request.format.value}"
                )
                output_path = os.path.join(os.getcwd(), filename)

            # Validate the output path for security
            allowed_dirs = self.config.data.get("allowed_export_directories", [os.getcwd()])
            is_valid, error = validate_path(output_path, allowed_dirs)
            if not is_valid:
                return NetworkDataExportResponse(
                    data_type=request.data_type,
                    export_format=request.format,
                    success=False,
                    error_message=f"Invalid output path: {error}",
                    regions=regions,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

            # Use streaming export if requested and format supports it
            streaming_formats = ["json", "csv"]
            if use_streaming and request.format.value in streaming_formats:
                self.logger.info(
                    f"Using streaming export for {request.data_type.value} data in {request.format.value} format"
                )
                try:
                    # Create streaming generator function
                    async def data_stream_generator():
                        # Process data in chunks to minimize memory usage
                        chunk_size = 100  # Configurable chunk size

                        # Collect and yield data in streaming fashion
                        data_collector = self._get_streaming_collector(
                            request.data_type, regions, request.filters
                        )
                        async for chunk in data_collector:
                            yield chunk

                    # Create streaming export manager
                    streaming_mgr = StreamingExportManager()

                    # Export data in streaming mode
                    result_path = await streaming_mgr.export_stream(
                        data_source=data_stream_generator,
                        format=request.format.value,
                        output_path=output_path,
                    )

                    # Get file stats
                    file_size = (
                        os.path.getsize(result_path) if os.path.exists(result_path) else None
                    )

                    # Since we streamed the data, we don't have an exact element count
                    # We'll estimate based on file size
                    est_element_count = file_size // 500 if file_size else 0  # Rough estimate

                    # Compute file hash for integrity verification
                    file_hash = compute_file_hash(result_path)

                    # Create metadata with integrity information
                    metadata = self.generate_streaming_metadata(request, regions)
                    metadata["file_hash"] = file_hash

                    # Add integrity signature if requested
                    if getattr(request, "add_integrity_signature", False):
                        integrity_data = create_integrity_signature(result_path, metadata)
                        metadata["integrity"] = integrity_data

                    # Encrypt the file if requested
                    encrypted_path = None
                    encryption_key = None
                    if getattr(request, "encrypt_output", False):
                        try:
                            encrypted_path, encryption_key = encrypt_file(result_path)
                            # Store the key as base64 in metadata
                            metadata["encrypted"] = True
                            metadata["encryption_key"] = base64.b64encode(encryption_key).decode(
                                "utf-8"
                            )
                            # Update the path and file size
                            result_path = encrypted_path
                            file_size = (
                                os.path.getsize(encrypted_path)
                                if os.path.exists(encrypted_path)
                                else None
                            )
                        except Exception as e:
                            self.logger.warning(f"Failed to encrypt file: {e}")
                            metadata["encryption_error"] = str(e)

                    return NetworkDataExportResponse(
                        data_type=request.data_type,
                        export_format=request.format,
                        output_path=result_path,
                        file_size_bytes=file_size,
                        element_count=est_element_count,
                        regions=regions,
                        execution_time_ms=int((time.time() - start_time) * 1000),
                        success=True,
                        warnings=["Element count is estimated due to streaming mode"],
                        metadata=metadata,
                    )

                except Exception as e:
                    self.logger.error(f"Streaming export failed: {e}")
                    return NetworkDataExportResponse(
                        data_type=request.data_type,
                        export_format=request.format,
                        success=False,
                        error_message=f"Streaming export failed: {str(e)}",
                        regions=regions,
                        execution_time_ms=int((time.time() - start_time) * 1000),
                    )
            else:
                # Use traditional non-streaming export
                # Collect all data at once
                data = await self.collect_data(request, regions)
                if not data:
                    return NetworkDataExportResponse(
                        data_type=request.data_type,
                        export_format=request.format,
                        success=False,
                        error_message="No data found for export",
                        regions=regions,
                        execution_time_ms=int((time.time() - start_time) * 1000),
                    )

                # Apply filters if specified
                filtered_data = self.apply_filters(data, request.filters)

                # Export in requested format
                try:
                    result_path = await self._export_to_format(
                        filtered_data,
                        request.format,
                        output_path,
                        request.filters.include_metadata,
                    )

                    # Get stats for response
                    stats = self.get_stats(filtered_data)
                    file_size = (
                        os.path.getsize(result_path) if os.path.exists(result_path) else None
                    )

                    # Compute file hash for integrity verification
                    file_hash = compute_file_hash(result_path)

                    # Create metadata with integrity information
                    metadata = self.generate_metadata(request, filtered_data)
                    metadata["file_hash"] = file_hash

                    # Add integrity signature if requested
                    if getattr(request, "add_integrity_signature", False):
                        integrity_data = create_integrity_signature(result_path, metadata)
                        metadata["integrity"] = integrity_data

                    # Encrypt the file if requested
                    encrypted_path = None
                    encryption_key = None
                    if getattr(request, "encrypt_output", False):
                        try:
                            encrypted_path, encryption_key = encrypt_file(result_path)
                            # Store the key as base64 in metadata
                            metadata["encrypted"] = True
                            metadata["encryption_key"] = base64.b64encode(encryption_key).decode(
                                "utf-8"
                            )
                            # Update the path and file size
                            result_path = encrypted_path
                            file_size = (
                                os.path.getsize(encrypted_path)
                                if os.path.exists(encrypted_path)
                                else None
                            )
                        except Exception as e:
                            self.logger.warning(f"Failed to encrypt file: {e}")
                            metadata["encryption_error"] = str(e)

                    return NetworkDataExportResponse(
                        data_type=request.data_type,
                        export_format=request.format,
                        output_path=result_path,
                        file_size_bytes=file_size,
                        element_count=stats.get("element_count", 0),
                        regions=regions,
                        execution_time_ms=int((time.time() - start_time) * 1000),
                        success=True,
                        warnings=stats.get("warnings", []),
                        metadata=metadata,
                    )
                except Exception as e:
                    self.logger.error(f"Export format conversion failed: {e}")
                    return NetworkDataExportResponse(
                        data_type=request.data_type,
                        export_format=request.format,
                        success=False,
                        error_message=f"Export format conversion failed: {str(e)}",
                        regions=regions,
                        execution_time_ms=int((time.time() - start_time) * 1000),
                    )

        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            self.logger.debug(traceback.format_exc())
            return NetworkDataExportResponse(
                data_type=request.data_type,
                export_format=request.format,
                success=False,
                error_message=str(e),
                regions=regions or [],
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    async def _collect_data_template(
        self,
        collection_func: Callable,
        regions: List[str],
        filters: Any,
        error_prefix: str = "data",
    ) -> Dict[str, Any]:
        """Delegate to the base class method for data collection template."""
        return await self.collect_data_template(collection_func, regions, filters, error_prefix)

    async def _collect_data(self, request: ExportRequest, regions: List[str]) -> Dict[str, Any]:
        """Collect network data based on request type."""
        collection_methods = {
            NetworkDataType.TOPOLOGY: self._collect_topology_data,
            NetworkDataType.ROUTES: self._collect_route_data,
            NetworkDataType.SEGMENT_ROUTES: self._collect_segment_route_data,
            NetworkDataType.ATTACHMENTS: self._collect_attachment_data,
            NetworkDataType.PATH_TRACE: self._collect_path_trace_data,
            NetworkDataType.BGP_SESSIONS: self._collect_bgp_data,
            NetworkDataType.TRANSIT_GATEWAY_ROUTES: self._collect_tgw_route_data,
            NetworkDataType.SECURITY_GROUPS: self._collect_security_group_data,
            NetworkDataType.CORE_NETWORKS: self._collect_core_network_data,
            NetworkDataType.VPCS: self._collect_vpc_data,
        }

        collector = collection_methods.get(request.data_type)
        if not collector:
            raise ValueError(f"Unsupported data type: {request.data_type}")

        return await collector(regions, request.filters)

    async def _collect_topology_data(
        self, regions: List[str], filters: NetworkDataFilter
    ) -> Dict[str, Any]:
        """Collect network topology data."""
        if not self.topology_available:
            raise ValueError("Network topology discovery is not available")

        async def fetch_topology_data(regions: List[str], filters: NetworkDataFilter):
            topology = await self.topology_discovery.discover_complete_topology(
                regions=regions,
                include_performance_metrics=filters.include_performance_metrics,
            )
            # Convert to serializable dictionary
            return self._topology_to_dict(topology)

        return await self._collect_data_template(fetch_topology_data, regions, filters, "topology")

    async def _collect_core_network_data(
        self, regions: List[str], filters: NetworkDataFilter
    ) -> Dict[str, Any]:
        """
        Collect Core Network data with pagination support.

        This method uses pagination to ensure all Core Networks are collected,
        even when they exceed AWS API page size limits.
        """

        async def fetch_core_network_data(regions: List[str], filters: NetworkDataFilter):
            # Use the core network discovery tool with pagination support
            result = await self.core_network_discovery.execute(
                regions=regions, include_policy=filters.include_policies
            )

            # If the result includes a success indicator, it's already been handled by the tool
            if isinstance(result, list) and len(result) > 0 and hasattr(result[0], "type"):
                return result

            # For direct API calls with pagination, handle it here
            try:
                # Check for raw API results that might need processing
                if isinstance(result, dict) and "CoreNetworks" in result:
                    self.logger.info("Processing Core Networks from direct API result")
                    return result
            except Exception as e:
                self.logger.debug(f"Error checking core network result structure: {e}")

            # Return the result as-is if no special handling needed
            return result

        return await self._collect_data_template(
            fetch_core_network_data, regions, filters, "core network"
        )

    async def _collect_vpc_data(
        self, regions: List[str], filters: NetworkDataFilter
    ) -> Dict[str, Any]:
        """
        Collect VPC data with pagination support.

        This method uses pagination to ensure all VPCs are collected,
        even when they exceed AWS API page size limits.
        """

        async def fetch_vpc_data(regions: List[str], filters: NetworkDataFilter):
            # Use the VPC discovery tool with pagination
            result = await self.vpc_discovery.execute(
                regions=regions,
                include_subnets=filters.include_subnets,
                include_route_tables=filters.include_route_tables,
            )

            # If the result includes a success indicator, it's already been handled by the tool
            if isinstance(result, list) and len(result) > 0 and hasattr(result[0], "type"):
                return result

            # Return the result as-is if no special handling needed
            return result

        return await self._collect_data_template(fetch_vpc_data, regions, filters, "VPC")

    async def _collect_bgp_data(
        self, regions: List[str], filters: NetworkDataFilter
    ) -> Dict[str, Any]:
        """
        Collect BGP session data with pagination support.

        This method uses pagination to ensure all BGP sessions are collected,
        even when they exceed AWS API page size limits.
        """

        async def fetch_bgp_data(regions: List[str], filters: NetworkDataFilter):
            # Use the BGP analyzer tool with pagination support
            result = await self.bgp_analyzer.execute(
                regions=regions, include_metrics=filters.include_performance_metrics
            )

            # If the result includes a success indicator, it's already been handled by the tool
            if isinstance(result, list) and len(result) > 0 and hasattr(result[0], "type"):
                return result

            # Return the result as-is if no special handling needed
            return result

        return await self._collect_data_template(fetch_bgp_data, regions, filters, "BGP")

    async def _collect_path_trace_data(
        self, regions: List[str], filters: NetworkDataFilter
    ) -> Dict[str, Any]:
        """Collect path trace data."""
        if not hasattr(filters, "source_ip") or not hasattr(filters, "destination_ip"):
            raise ValueError("Both source_ip and destination_ip are required for path trace export")

        async def fetch_path_trace_data(regions: List[str], filters: NetworkDataFilter):
            return await self.path_tracing.execute(
                source_ip=filters.source_ip,
                destination_ip=filters.destination_ip,
                protocol=filters.protocol if hasattr(filters, "protocol") else "tcp",
                port=filters.port if hasattr(filters, "port") else 443,
                regions=regions,
            )

        return await self._collect_data_template(
            fetch_path_trace_data, regions, filters, "path trace"
        )

    async def _collect_route_data(
        self, regions: List[str], filters: NetworkDataFilter
    ) -> Dict[str, Any]:
        """Collect route data from VPC route tables and CloudWAN route tables.

        This method collects route information from VPC route tables and CloudWAN routes
        across all specified regions, with support for pagination and filtering.
        """

        async def fetch_route_data(regions: List[str], filters: NetworkDataFilter):
            routes = {
                "vpc_routes": [],
                "cloudwan_routes": [],
                "direct_connect_routes": [],
                "transit_gateway_routes": [],
            }
            region_results = {}
            region_errors = {}

            for region in regions:
                try:
                    # Get VPC route tables
                    if filters.include_route_tables:
                        async with self.aws_manager.client_context("ec2", region) as ec2:
                            # First get route tables with pagination
                            route_tables = await self._paginated_aws_collection(
                                ec2,
                                "describe_route_tables",
                                **(
                                    {
                                        "Filters": [
                                            {
                                                "Name": "vpc-id",
                                                "Values": filters.vpc_ids,
                                            }
                                        ]
                                    }
                                    if filters.vpc_ids
                                    else {}
                                ),
                            )

                            # Extract and normalize route information
                            for rt in route_tables:
                                rt["Region"] = region
                                for route in rt.get("Routes", []):
                                    route_entry = {
                                        "route_table_id": rt.get("RouteTableId"),
                                        "vpc_id": rt.get("VpcId"),
                                        "region": region,
                                        "destination_cidr": route.get("DestinationCidrBlock"),
                                        "destination_ipv6_cidr": route.get(
                                            "DestinationIpv6CidrBlock"
                                        ),
                                        "destination_prefix_list_id": route.get(
                                            "DestinationPrefixListId"
                                        ),
                                        "gateway_id": route.get("GatewayId"),
                                        "instance_id": route.get("InstanceId"),
                                        "nat_gateway_id": route.get("NatGatewayId"),
                                        "transit_gateway_id": route.get("TransitGatewayId"),
                                        "vpc_peering_connection_id": route.get(
                                            "VpcPeeringConnectionId"
                                        ),
                                        "state": route.get("State"),
                                    }
                                    routes["vpc_routes"].append(route_entry)

                    # Get CloudWAN core network routes if available
                    if hasattr(self, "core_network_discovery"):
                        async with self.aws_manager.client_context(
                            "networkmanager", region
                        ) as nm_client:
                            # Get core network IDs first
                            try:
                                core_networks_response = await resilient_aws_call(
                                    nm_client.list_core_networks,
                                    {},  # No params needed for list operation
                                )

                                # For each core network, get segment and attachment routes
                                core_networks = core_networks_response.get("CoreNetworks", [])
                                for core in core_networks:
                                    core_id = core.get("CoreNetworkId")

                                    # Get core network routes
                                    routes_response = await resilient_aws_call(
                                        nm_client.get_core_network_routes,
                                        {
                                            "CoreNetworkId": core_id,
                                            "DestinationCidrBlock": "0.0.0.0/0",  # Get all routes
                                        },
                                    )

                                    # Extract and normalize CloudWAN routes
                                    for route in routes_response.get("Routes", []):
                                        route_entry = {
                                            "core_network_id": core_id,
                                            "region": region,
                                            "destination_cidr": route.get("DestinationCidrBlock"),
                                            "segment": route.get("SegmentName"),
                                            "attachment_id": route.get("AttachmentId"),
                                            "attachment_type": route.get("AttachmentType"),
                                            "route_type": route.get("RouteType"),
                                            "state": route.get("State"),
                                        }
                                        routes["cloudwan_routes"].append(route_entry)
                            except Exception as e:
                                self.logger.warning(
                                    f"Failed to get core network routes in {region}: {e}"
                                )

                    # Get Transit Gateway routes if needed
                    if filters.include_tgw_attachments:
                        async with self.aws_manager.client_context("ec2", region) as ec2:
                            # Get transit gateways first
                            tgws = await self._paginated_aws_collection(
                                ec2, "describe_transit_gateways"
                            )

                            # For each TGW, get route tables
                            for tgw in tgws:
                                tgw_id = tgw.get("TransitGatewayId")

                                # Get TGW route tables
                                tgw_rts = await self._paginated_aws_collection(
                                    ec2,
                                    "describe_transit_gateway_route_tables",
                                    **{
                                        "Filters": [
                                            {
                                                "Name": "transit-gateway-id",
                                                "Values": [tgw_id],
                                            }
                                        ]
                                    },
                                )

                                # For each route table, get routes
                                for tgw_rt in tgw_rts:
                                    tgw_rt_id = tgw_rt.get("TransitGatewayRouteTableId")

                                    # Get routes with pagination
                                    try:
                                        routes_response = await resilient_aws_call(
                                            ec2.search_transit_gateway_routes,
                                            {
                                                "TransitGatewayRouteTableId": tgw_rt_id,
                                                "Filters": [],
                                            },
                                        )

                                        # Extract and normalize TGW routes
                                        for route in routes_response.get("Routes", []):
                                            route_entry = {
                                                "transit_gateway_id": tgw_id,
                                                "route_table_id": tgw_rt_id,
                                                "region": region,
                                                "destination_cidr": route.get(
                                                    "DestinationCidrBlock"
                                                ),
                                                "transit_gateway_attachment_id": route.get(
                                                    "TransitGatewayAttachmentId"
                                                ),
                                                "resource_id": route.get("ResourceId"),
                                                "resource_type": route.get("ResourceType"),
                                                "state": route.get("State"),
                                                "type": route.get("Type"),
                                            }
                                            routes["transit_gateway_routes"].append(route_entry)
                                    except Exception as e:
                                        self.logger.warning(
                                            f"Failed to get TGW routes for route table {tgw_rt_id}: {e}"
                                        )

                    # Record successful region collection
                    region_results[region] = {
                        "vpc_routes": len(
                            [r for r in routes["vpc_routes"] if r.get("region") == region]
                        ),
                        "cloudwan_routes": len(
                            [r for r in routes["cloudwan_routes"] if r.get("region") == region]
                        ),
                        "transit_gateway_routes": len(
                            [
                                r
                                for r in routes["transit_gateway_routes"]
                                if r.get("region") == region
                            ]
                        ),
                    }

                except Exception as e:
                    self.logger.error(f"Error collecting route data in {region}: {e}")
                    region_errors[region] = str(e)

            # Combine results
            result = {
                "routes": routes,
                "vpc_route_count": len(routes["vpc_routes"]),
                "cloudwan_route_count": len(routes["cloudwan_routes"]),
                "tgw_route_count": len(routes["transit_gateway_routes"]),
                "direct_connect_route_count": len(routes["direct_connect_routes"]),
                "regions": list(region_results.keys()),
                "region_stats": region_results,
            }

            # Add errors if any occurred
            if region_errors:
                result["errors"] = region_errors
                result["partial_data"] = True
                result["success_rate"] = (
                    len(region_results) / (len(region_results) + len(region_errors))
                    if (len(region_results) + len(region_errors)) > 0
                    else 0
                )

            return result

        return await self._collect_data_template(fetch_route_data, regions, filters, "route")

    async def _collect_segment_route_data(
        self, regions: List[str], filters: NetworkDataFilter
    ) -> Dict[str, Any]:
        """Collect segment route data from CloudWAN core networks.

        This method collects segment route information from CloudWAN core networks
        across all specified regions with detailed segment-specific information.
        """

        async def fetch_segment_route_data(regions: List[str], filters: NetworkDataFilter):
            segment_routes = []
            segment_policies = []
            region_results = {}
            region_errors = {}

            for region in regions:
                try:
                    # CloudWAN segment data is primarily in us-west-2
                    if region != "us-west-2":
                        continue

                    async with self.aws_manager.client_context(
                        "networkmanager", region
                    ) as nm_client:
                        # Get core networks first
                        core_networks_response = await resilient_aws_call(
                            nm_client.list_core_networks,
                            {},  # No params needed for list operation
                        )

                        # For each core network, get segment information
                        core_networks = core_networks_response.get("CoreNetworks", [])
                        for core in core_networks:
                            core_id = core.get("CoreNetworkId")

                            # Get core network policy if needed
                            if filters.include_policies:
                                try:
                                    policy_response = await resilient_aws_call(
                                        nm_client.get_core_network_policy,
                                        {"CoreNetworkId": core_id},
                                    )

                                    # Extract segment definitions from policy
                                    policy = policy_response.get("CoreNetworkPolicy", {})
                                    policy_doc = json.loads(policy.get("PolicyDocument", "{}"))

                                    # Add policy to collection
                                    policy_entry = {
                                        "core_network_id": core_id,
                                        "policy_version": policy.get("PolicyVersionId"),
                                        "change_set_state": policy.get("ChangeSetState"),
                                        "segments": policy_doc.get("segments", []),
                                        "region": region,
                                    }
                                    segment_policies.append(policy_entry)
                                except Exception as e:
                                    self.logger.warning(
                                        f"Failed to get core network policy for {core_id}: {e}"
                                    )

                            # Get segment-specific route information by segment name
                            segments_list = []

                            try:
                                # Get core network segments
                                segments_response = await resilient_aws_call(
                                    nm_client.list_core_network_segments,
                                    {"CoreNetworkId": core_id},
                                )

                                segments_list = segments_response.get("CoreNetworkSegments", [])

                                # Filter by segment names if specified
                                if filters.segment_names:
                                    segments_list = [
                                        s
                                        for s in segments_list
                                        if s.get("SegmentName") in filters.segment_names
                                    ]

                            except Exception as e:
                                self.logger.warning(
                                    f"Failed to get core network segments for {core_id}: {e}"
                                )

                            # For each segment, get route information
                            for segment in segments_list:
                                segment_name = segment.get("SegmentName")

                                try:
                                    # Get routes for this segment
                                    routes_response = await resilient_aws_call(
                                        nm_client.get_core_network_routes,
                                        {
                                            "CoreNetworkId": core_id,
                                            "SegmentName": segment_name,
                                        },
                                    )

                                    # Extract and normalize segment routes
                                    for route in routes_response.get("Routes", []):
                                        route_entry = {
                                            "core_network_id": core_id,
                                            "segment_name": segment_name,
                                            "edge_location": segment.get("EdgeLocation"),
                                            "destination_cidr": route.get("DestinationCidrBlock"),
                                            "attachment_id": route.get("AttachmentId"),
                                            "attachment_type": route.get("AttachmentType"),
                                            "route_type": route.get("RouteType"),
                                            "state": route.get("State"),
                                            "region": region,
                                        }
                                        segment_routes.append(route_entry)
                                except Exception as e:
                                    self.logger.warning(
                                        f"Failed to get routes for segment {segment_name}: {e}"
                                    )

                    # Record successful region collection
                    region_results[region] = {
                        "segment_routes": len(
                            [r for r in segment_routes if r.get("region") == region]
                        ),
                        "segment_policies": len(
                            [p for p in segment_policies if p.get("region") == region]
                        ),
                    }

                except Exception as e:
                    self.logger.error(f"Error collecting segment route data in {region}: {e}")
                    region_errors[region] = str(e)

            # Combine results
            result = {
                "segment_routes": segment_routes,
                "segment_policies": (segment_policies if filters.include_policies else []),
                "route_count": len(segment_routes),
                "policy_count": len(segment_policies),
                "regions": list(region_results.keys()),
                "region_stats": region_results,
            }

            # Add errors if any occurred
            if region_errors:
                result["errors"] = region_errors
                result["partial_data"] = True
                result["success_rate"] = (
                    len(region_results) / (len(region_results) + len(region_errors))
                    if (len(region_results) + len(region_errors)) > 0
                    else 0
                )

            return result

        return await self._collect_data_template(
            fetch_segment_route_data, regions, filters, "segment route"
        )

    async def _collect_attachment_data(
        self, regions: List[str], filters: NetworkDataFilter
    ) -> Dict[str, Any]:
        """Collect attachment data from CloudWAN and Transit Gateway.

        This method collects attachment information from CloudWAN core networks
        and Transit Gateways across all specified regions with proper pagination.
        """

        async def fetch_attachment_data(regions: List[str], filters: NetworkDataFilter):
            attachments = {
                "cloudwan_attachments": [],
                "tgw_attachments": [],
                "vpc_attachments": [],
            }
            region_results = {}
            region_errors = {}

            for region in regions:
                try:
                    # Get CloudWAN attachments if needed
                    if filters.include_cloudwan_attachments:
                        async with self.aws_manager.client_context(
                            "networkmanager", region
                        ) as nm_client:
                            # Get global networks first for CloudWAN
                            global_networks_response = await resilient_aws_call(
                                nm_client.describe_global_networks, {}
                            )

                            for gn in global_networks_response.get("GlobalNetworks", []):
                                gn_id = gn.get("GlobalNetworkId")

                                # Get core networks for this global network
                                core_networks_response = await resilient_aws_call(
                                    nm_client.list_core_networks, {}
                                )

                                for core in core_networks_response.get("CoreNetworks", []):
                                    core_id = core.get("CoreNetworkId")

                                    # Get attachments for this core network with pagination support
                                    next_token = None
                                    while True:
                                        kwargs = {"CoreNetworkId": core_id}
                                        if next_token:
                                            kwargs["NextToken"] = next_token

                                        attachments_response = await resilient_aws_call(
                                            nm_client.list_core_network_attachments,
                                            kwargs,
                                        )

                                        # Process and filter attachments
                                        core_attachments = attachments_response.get(
                                            "CoreNetworkAttachments", []
                                        )

                                        # Filter by attachment types if specified
                                        if filters.attachment_types:
                                            core_attachments = [
                                                a
                                                for a in core_attachments
                                                if a.get("AttachmentType")
                                                in filters.attachment_types
                                            ]

                                        # Filter by segment names if specified
                                        if filters.segment_names:
                                            core_attachments = [
                                                a
                                                for a in core_attachments
                                                if a.get("SegmentName") in filters.segment_names
                                            ]

                                        # Normalize and add attachment data
                                        for attachment in core_attachments:
                                            attachment_entry = {
                                                "core_network_id": core_id,
                                                "global_network_id": gn_id,
                                                "attachment_id": attachment.get(
                                                    "Attachment", {}
                                                ).get("AttachmentId"),
                                                "attachment_type": attachment.get("AttachmentType"),
                                                "edge_location": attachment.get("EdgeLocation"),
                                                "resource_arn": attachment.get("ResourceArn"),
                                                "segment_name": attachment.get("SegmentName"),
                                                "state": attachment.get("State"),
                                                "region": attachment.get(
                                                    "AttachmentRegion", region
                                                ),
                                                "owner_account": attachment.get("OwnerAccountId"),
                                            }
                                            attachments["cloudwan_attachments"].append(
                                                attachment_entry
                                            )

                                        # Check for pagination
                                        next_token = attachments_response.get("NextToken")
                                        if not next_token:
                                            break

                    # Get Transit Gateway attachments if needed
                    if filters.include_tgw_attachments:
                        async with self.aws_manager.client_context("ec2", region) as ec2:
                            # Get transit gateways first using pagination
                            tgws = await self._paginated_aws_collection(
                                ec2, "describe_transit_gateways"
                            )

                            # For each TGW, get attachments
                            for tgw in tgws:
                                tgw_id = tgw.get("TransitGatewayId")

                                # Get TGW attachments with pagination
                                tgw_attachments = await self._paginated_aws_collection(
                                    ec2,
                                    "describe_transit_gateway_attachments",
                                    **{
                                        "Filters": [
                                            {
                                                "Name": "transit-gateway-id",
                                                "Values": [tgw_id],
                                            }
                                        ]
                                    },
                                )

                                # Filter by attachment types if specified
                                if filters.attachment_types:
                                    tgw_attachments = [
                                        a
                                        for a in tgw_attachments
                                        if a.get("ResourceType") in filters.attachment_types
                                    ]

                                # Normalize and add attachment data
                                for attachment in tgw_attachments:
                                    attachment_entry = {
                                        "transit_gateway_id": tgw_id,
                                        "transit_gateway_attachment_id": attachment.get(
                                            "TransitGatewayAttachmentId"
                                        ),
                                        "resource_type": attachment.get("ResourceType"),
                                        "resource_id": attachment.get("ResourceId"),
                                        "state": attachment.get("State"),
                                        "association_state": attachment.get("Association", {}).get(
                                            "State"
                                        ),
                                        "region": region,
                                    }
                                    attachments["tgw_attachments"].append(attachment_entry)

                    # Get VPC attachments if needed
                    if filters.include_vpcs:
                        async with self.aws_manager.client_context("ec2", region) as ec2:
                            # Get VPC attachments with pagination
                            vpc_filters = {}
                            if filters.vpc_ids:
                                vpc_filters = {
                                    "Filters": [{"Name": "vpc-id", "Values": filters.vpc_ids}]
                                }

                            # Note: 'describe_vpc_attachments' is replaced with a more accurate API call
                            # since AWS doesn't have a direct 'describe_vpc_attachments' method
                            vpc_network_interfaces = await self._paginated_aws_collection(
                                ec2, "describe_network_interfaces", **vpc_filters
                            )

                            # Find attachments among network interfaces
                            for eni in vpc_network_interfaces:
                                if eni.get("Attachment"):
                                    attachment_entry = {
                                        "vpc_id": eni.get("VpcId"),
                                        "attachment_id": eni.get("Attachment", {}).get(
                                            "AttachmentId"
                                        ),
                                        "attachment_type": "network_interface",
                                        "state": eni.get("Attachment", {}).get("Status"),
                                        "network_interface_id": eni.get("NetworkInterfaceId"),
                                        "region": region,
                                    }
                                    attachments["vpc_attachments"].append(attachment_entry)

                    # Record successful region collection
                    region_results[region] = {
                        "cloudwan_attachments": len(
                            [
                                a
                                for a in attachments["cloudwan_attachments"]
                                if a.get("region") == region
                            ]
                        ),
                        "tgw_attachments": len(
                            [a for a in attachments["tgw_attachments"] if a.get("region") == region]
                        ),
                        "vpc_attachments": len(
                            [a for a in attachments["vpc_attachments"] if a.get("region") == region]
                        ),
                    }

                except Exception as e:
                    self.logger.error(f"Error collecting attachment data in {region}: {e}")
                    region_errors[region] = str(e)

            # Combine results
            result = {
                "attachments": attachments,
                "cloudwan_attachment_count": len(attachments["cloudwan_attachments"]),
                "tgw_attachment_count": len(attachments["tgw_attachments"]),
                "vpc_attachment_count": len(attachments["vpc_attachments"]),
                "regions": list(region_results.keys()),
                "region_stats": region_results,
            }

            # Add errors if any occurred
            if region_errors:
                result["errors"] = region_errors
                result["partial_data"] = True
                result["success_rate"] = (
                    len(region_results) / (len(region_results) + len(region_errors))
                    if (len(region_results) + len(region_errors)) > 0
                    else 0
                )

            return result

        return await self._collect_data_template(
            fetch_attachment_data, regions, filters, "attachment"
        )

        async def fetch_attachment_data(regions: List[str], filters: NetworkDataFilter):
            attachments = {
                "cloudwan_attachments": [],
                "tgw_attachments": [],
                "vpc_attachments": [],
            }
            region_results = {}
            region_errors = {}

            for region in regions:
                try:
                    # Get CloudWAN attachments if needed
                    if filters.include_cloudwan_attachments:
                        async with self.aws_manager.client_context(
                            "networkmanager", region
                        ) as nm_client:
                            # Get global networks first for CloudWAN
                            global_networks = await resilient_aws_call(
                                nm_client.describe_global_networks, {}
                            )

                            for gn in global_networks.get("GlobalNetworks", []):
                                gn_id = gn.get("GlobalNetworkId")

                                # Get core networks for this global network
                                core_networks = await resilient_aws_call(
                                    nm_client.list_core_networks, {}
                                )

                                for core in core_networks.get("CoreNetworks", []):
                                    core_id = core.get("CoreNetworkId")

                                    # Get attachments for this core network
                                    attachments_response = await resilient_aws_call(
                                        nm_client.list_core_network_attachments,
                                        {"CoreNetworkId": core_id},
                                    )

                                    # Process and filter attachments
                                    core_attachments = attachments_response.get(
                                        "CoreNetworkAttachments", []
                                    )

                                    # Filter by attachment types if specified
                                    if filters.attachment_types:
                                        core_attachments = [
                                            a
                                            for a in core_attachments
                                            if a.get("AttachmentType") in filters.attachment_types
                                        ]

                                    # Filter by segment names if specified
                                    if filters.segment_names:
                                        core_attachments = [
                                            a
                                            for a in core_attachments
                                            if a.get("SegmentName") in filters.segment_names
                                        ]

                                    # Normalize and add attachment data
                                    for attachment in core_attachments:
                                        attachment_entry = {
                                            "core_network_id": core_id,
                                            "global_network_id": gn_id,
                                            "attachment_id": attachment.get("Attachment", {}).get(
                                                "AttachmentId"
                                            ),
                                            "attachment_type": attachment.get("AttachmentType"),
                                            "edge_location": attachment.get("EdgeLocation"),
                                            "resource_arn": attachment.get("ResourceArn"),
                                            "segment_name": attachment.get("SegmentName"),
                                            "state": attachment.get("State"),
                                            "region": attachment.get("AttachmentRegion", region),
                                            "owner_account": attachment.get("OwnerAccountId"),
                                        }
                                        attachments["cloudwan_attachments"].append(attachment_entry)

                    # Get Transit Gateway attachments if needed
                    if filters.include_tgw_attachments:
                        async with self.aws_manager.client_context("ec2", region) as ec2:
                            # Get transit gateways first
                            tgws = await self._paginated_aws_collection(
                                ec2, "describe_transit_gateways"
                            )

                            # For each TGW, get attachments
                            for tgw in tgws:
                                tgw_id = tgw.get("TransitGatewayId")

                                # Get TGW attachments with pagination
                                tgw_attachments = await self._paginated_aws_collection(
                                    ec2,
                                    "describe_transit_gateway_attachments",
                                    **{
                                        "Filters": [
                                            {
                                                "Name": "transit-gateway-id",
                                                "Values": [tgw_id],
                                            }
                                        ]
                                    },
                                )

                                # Filter by attachment types if specified
                                if filters.attachment_types:
                                    tgw_attachments = [
                                        a
                                        for a in tgw_attachments
                                        if a.get("ResourceType") in filters.attachment_types
                                    ]

                                # Normalize and add attachment data
                                for attachment in tgw_attachments:
                                    attachment_entry = {
                                        "transit_gateway_id": tgw_id,
                                        "transit_gateway_attachment_id": attachment.get(
                                            "TransitGatewayAttachmentId"
                                        ),
                                        "resource_type": attachment.get("ResourceType"),
                                        "resource_id": attachment.get("ResourceId"),
                                        "state": attachment.get("State"),
                                        "association_state": attachment.get("Association", {}).get(
                                            "State"
                                        ),
                                        "region": region,
                                    }
                                    attachments["tgw_attachments"].append(attachment_entry)

                    # Get VPC attachments if needed
                    if filters.include_vpcs and filters.include_tgw_attachments:
                        async with self.aws_manager.client_context("ec2", region) as ec2:
                            # Get VPC attachments with pagination
                            vpc_filters = {}
                            if filters.vpc_ids:
                                vpc_filters = {
                                    "Filters": [{"Name": "vpc-id", "Values": filters.vpc_ids}]
                                }

                            vpc_attachments = await self._paginated_aws_collection(
                                ec2,
                                "describe_vpc_attachments",  # This might not be the exact API name
                                **vpc_filters,
                            )

                            # Normalize and add attachment data
                            for attachment in vpc_attachments:
                                attachment_entry = {
                                    "vpc_id": attachment.get("VpcId"),
                                    "attachment_id": attachment.get("AttachmentId"),
                                    "attachment_type": attachment.get("AttachmentType"),
                                    "state": attachment.get("State"),
                                    "region": region,
                                }
                                attachments["vpc_attachments"].append(attachment_entry)

                    # Record successful region collection
                    region_results[region] = {
                        "cloudwan_attachments": len(
                            [
                                a
                                for a in attachments["cloudwan_attachments"]
                                if a.get("region") == region
                            ]
                        ),
                        "tgw_attachments": len(
                            [a for a in attachments["tgw_attachments"] if a.get("region") == region]
                        ),
                        "vpc_attachments": len(
                            [a for a in attachments["vpc_attachments"] if a.get("region") == region]
                        ),
                    }

                except Exception as e:
                    self.logger.error(f"Error collecting attachment data in {region}: {e}")
                    region_errors[region] = str(e)

            # Combine results
            result = {
                "attachments": attachments,
                "cloudwan_attachment_count": len(attachments["cloudwan_attachments"]),
                "tgw_attachment_count": len(attachments["tgw_attachments"]),
                "vpc_attachment_count": len(attachments["vpc_attachments"]),
                "regions": list(region_results.keys()),
                "region_stats": region_results,
            }

            # Add errors if any occurred
            if region_errors:
                result["errors"] = region_errors
                result["partial_data"] = True
                result["success_rate"] = (
                    len(region_results) / (len(region_results) + len(region_errors))
                    if (len(region_results) + len(region_errors)) > 0
                    else 0
                )

            return result

        return await self._collect_data_template(
            fetch_attachment_data, regions, filters, "attachment"
        )

    async def _collect_tgw_route_data(
        self, regions: List[str], filters: NetworkDataFilter
    ) -> Dict[str, Any]:
        """Collect Transit Gateway route data with pagination support.

        This method collects Transit Gateway routes across all specified regions,
        including route tables, routes, and propagations.
        """

        async def fetch_tgw_route_data(regions: List[str], filters: NetworkDataFilter):
            tgw_data = {
                "transit_gateways": [],
                "route_tables": [],
                "routes": [],
                "propagations": [],
                "associations": [],
            }
            region_results = {}
            region_errors = {}

            for region in regions:
                try:
                    async with self.aws_manager.client_context("ec2", region) as ec2:
                        # Get transit gateways with pagination
                        tgws = await self._paginated_aws_collection(
                            ec2, "describe_transit_gateways"
                        )

                        # Add region info to each transit gateway
                        for tgw in tgws:
                            tgw["Region"] = region
                            tgw_data["transit_gateways"].append(tgw)

                        # For each TGW, get route tables
                        for tgw in tgws:
                            tgw_id = tgw.get("TransitGatewayId")

                            # Get TGW route tables with pagination
                            tgw_route_tables = await self._paginated_aws_collection(
                                ec2,
                                "describe_transit_gateway_route_tables",
                                **{
                                    "Filters": [
                                        {
                                            "Name": "transit-gateway-id",
                                            "Values": [tgw_id],
                                        }
                                    ]
                                },
                            )

                            # Add route tables to collection
                            for rt in tgw_route_tables:
                                rt["Region"] = region
                                tgw_data["route_tables"].append(rt)

                                rt_id = rt.get("TransitGatewayRouteTableId")

                                # Get routes for this route table
                                try:
                                    # First static routes
                                    routes_response = await resilient_aws_call(
                                        ec2.search_transit_gateway_routes,
                                        {
                                            "TransitGatewayRouteTableId": rt_id,
                                            "Filters": [{"Name": "type", "Values": ["static"]}],
                                        },
                                    )

                                    # Extract and normalize static routes
                                    for route in routes_response.get("Routes", []):
                                        route["Region"] = region
                                        route["RouteTableId"] = rt_id
                                        route["TransitGatewayId"] = tgw_id
                                        route["RouteType"] = "static"
                                        tgw_data["routes"].append(route)

                                    # Then propagated routes
                                    routes_response = await resilient_aws_call(
                                        ec2.search_transit_gateway_routes,
                                        {
                                            "TransitGatewayRouteTableId": rt_id,
                                            "Filters": [
                                                {
                                                    "Name": "type",
                                                    "Values": ["propagated"],
                                                }
                                            ],
                                        },
                                    )

                                    # Extract and normalize propagated routes
                                    for route in routes_response.get("Routes", []):
                                        route["Region"] = region
                                        route["RouteTableId"] = rt_id
                                        route["TransitGatewayId"] = tgw_id
                                        route["RouteType"] = "propagated"
                                        tgw_data["routes"].append(route)
                                except Exception as e:
                                    self.logger.warning(
                                        f"Failed to get routes for TGW route table {rt_id}: {e}"
                                    )

                                # Get route propagations
                                try:
                                    # Use pagination for propagations which could be numerous
                                    propagations = await self._paginated_aws_collection(
                                        ec2,
                                        "get_transit_gateway_route_table_propagations",
                                        **{"TransitGatewayRouteTableId": rt_id},
                                    )

                                    # Add propagations to collection
                                    for prop in propagations:
                                        prop["Region"] = region
                                        prop["TransitGatewayId"] = tgw_id
                                        tgw_data["propagations"].append(prop)
                                except Exception as e:
                                    self.logger.warning(
                                        f"Failed to get propagations for TGW route table {rt_id}: {e}"
                                    )

                                # Get route associations
                                try:
                                    # Use pagination for associations which could be numerous
                                    associations = await self._paginated_aws_collection(
                                        ec2,
                                        "get_transit_gateway_route_table_associations",
                                        **{"TransitGatewayRouteTableId": rt_id},
                                    )

                                    # Add associations to collection
                                    for assoc in associations:
                                        assoc["Region"] = region
                                        assoc["TransitGatewayId"] = tgw_id
                                        tgw_data["associations"].append(assoc)
                                except Exception as e:
                                    self.logger.warning(
                                        f"Failed to get associations for TGW route table {rt_id}: {e}"
                                    )

                    # Record successful region collection
                    region_results[region] = {
                        "transit_gateways": len(
                            [
                                tgw
                                for tgw in tgw_data["transit_gateways"]
                                if tgw.get("Region") == region
                            ]
                        ),
                        "route_tables": len(
                            [rt for rt in tgw_data["route_tables"] if rt.get("Region") == region]
                        ),
                        "routes": len(
                            [route for route in tgw_data["routes"] if route.get("Region") == region]
                        ),
                        "propagations": len(
                            [
                                prop
                                for prop in tgw_data["propagations"]
                                if prop.get("Region") == region
                            ]
                        ),
                        "associations": len(
                            [
                                assoc
                                for assoc in tgw_data["associations"]
                                if assoc.get("Region") == region
                            ]
                        ),
                    }

                except Exception as e:
                    self.logger.error(f"Error collecting TGW route data in {region}: {e}")
                    region_errors[region] = str(e)

            # Combine results
            result = {
                "tgw_data": tgw_data,
                "transit_gateway_count": len(tgw_data["transit_gateways"]),
                "route_table_count": len(tgw_data["route_tables"]),
                "route_count": len(tgw_data["routes"]),
                "propagation_count": len(tgw_data["propagations"]),
                "association_count": len(tgw_data["associations"]),
                "regions": list(region_results.keys()),
                "region_stats": region_results,
            }

            # Add errors if any occurred
            if region_errors:
                result["errors"] = region_errors
                result["partial_data"] = True
                result["success_rate"] = (
                    len(region_results) / (len(region_results) + len(region_errors))
                    if (len(region_results) + len(region_errors)) > 0
                    else 0
                )

            return result

        return await self._collect_data_template(
            fetch_tgw_route_data, regions, filters, "TGW route"
        )

        async def fetch_tgw_route_data(regions: List[str], filters: NetworkDataFilter):
            tgw_data = {
                "transit_gateways": [],
                "route_tables": [],
                "routes": [],
                "propagations": [],
                "associations": [],
            }
            region_results = {}
            region_errors = {}

            for region in regions:
                try:
                    async with self.aws_manager.client_context("ec2", region) as ec2:
                        # Get transit gateways with pagination
                        tgws = await self._paginated_aws_collection(
                            ec2, "describe_transit_gateways"
                        )

                        # Add region info to each transit gateway
                        for tgw in tgws:
                            tgw["Region"] = region
                            tgw_data["transit_gateways"].append(tgw)

                        # For each TGW, get route tables
                        for tgw in tgws:
                            tgw_id = tgw.get("TransitGatewayId")

                            # Get TGW route tables with pagination
                            tgw_route_tables = await self._paginated_aws_collection(
                                ec2,
                                "describe_transit_gateway_route_tables",
                                **{
                                    "Filters": [
                                        {
                                            "Name": "transit-gateway-id",
                                            "Values": [tgw_id],
                                        }
                                    ]
                                },
                            )

                            # Add route tables to collection
                            for rt in tgw_route_tables:
                                rt["Region"] = region
                                tgw_data["route_tables"].append(rt)

                                rt_id = rt.get("TransitGatewayRouteTableId")

                                # Get routes for this route table
                                try:
                                    # First static routes
                                    routes_response = await resilient_aws_call(
                                        ec2.search_transit_gateway_routes,
                                        {
                                            "TransitGatewayRouteTableId": rt_id,
                                            "Filters": [{"Name": "type", "Values": ["static"]}],
                                        },
                                    )

                                    # Extract and normalize static routes
                                    for route in routes_response.get("Routes", []):
                                        route["Region"] = region
                                        route["RouteTableId"] = rt_id
                                        route["TransitGatewayId"] = tgw_id
                                        route["RouteType"] = "static"
                                        tgw_data["routes"].append(route)

                                    # Then propagated routes
                                    routes_response = await resilient_aws_call(
                                        ec2.search_transit_gateway_routes,
                                        {
                                            "TransitGatewayRouteTableId": rt_id,
                                            "Filters": [
                                                {
                                                    "Name": "type",
                                                    "Values": ["propagated"],
                                                }
                                            ],
                                        },
                                    )

                                    # Extract and normalize propagated routes
                                    for route in routes_response.get("Routes", []):
                                        route["Region"] = region
                                        route["RouteTableId"] = rt_id
                                        route["TransitGatewayId"] = tgw_id
                                        route["RouteType"] = "propagated"
                                        tgw_data["routes"].append(route)
                                except Exception as e:
                                    self.logger.warning(
                                        f"Failed to get routes for TGW route table {rt_id}: {e}"
                                    )

                                # Get route propagations
                                try:
                                    propagations = await self._paginated_aws_collection(
                                        ec2,
                                        "get_transit_gateway_route_table_propagations",
                                        **{"TransitGatewayRouteTableId": rt_id},
                                    )

                                    # Add propagations to collection
                                    for prop in propagations:
                                        prop["Region"] = region
                                        prop["TransitGatewayId"] = tgw_id
                                        tgw_data["propagations"].append(prop)
                                except Exception as e:
                                    self.logger.warning(
                                        f"Failed to get propagations for TGW route table {rt_id}: {e}"
                                    )

                                # Get route associations
                                try:
                                    associations = await self._paginated_aws_collection(
                                        ec2,
                                        "get_transit_gateway_route_table_associations",
                                        **{"TransitGatewayRouteTableId": rt_id},
                                    )

                                    # Add associations to collection
                                    for assoc in associations:
                                        assoc["Region"] = region
                                        assoc["TransitGatewayId"] = tgw_id
                                        tgw_data["associations"].append(assoc)
                                except Exception as e:
                                    self.logger.warning(
                                        f"Failed to get associations for TGW route table {rt_id}: {e}"
                                    )

                    # Record successful region collection
                    region_results[region] = {
                        "transit_gateways": len(
                            [
                                tgw
                                for tgw in tgw_data["transit_gateways"]
                                if tgw.get("Region") == region
                            ]
                        ),
                        "route_tables": len(
                            [rt for rt in tgw_data["route_tables"] if rt.get("Region") == region]
                        ),
                        "routes": len(
                            [route for route in tgw_data["routes"] if route.get("Region") == region]
                        ),
                        "propagations": len(
                            [
                                prop
                                for prop in tgw_data["propagations"]
                                if prop.get("Region") == region
                            ]
                        ),
                        "associations": len(
                            [
                                assoc
                                for assoc in tgw_data["associations"]
                                if assoc.get("Region") == region
                            ]
                        ),
                    }

                except Exception as e:
                    self.logger.error(f"Error collecting TGW route data in {region}: {e}")
                    region_errors[region] = str(e)

            # Combine results
            result = {
                "tgw_data": tgw_data,
                "transit_gateway_count": len(tgw_data["transit_gateways"]),
                "route_table_count": len(tgw_data["route_tables"]),
                "route_count": len(tgw_data["routes"]),
                "propagation_count": len(tgw_data["propagations"]),
                "association_count": len(tgw_data["associations"]),
                "regions": list(region_results.keys()),
                "region_stats": region_results,
            }

            # Add errors if any occurred
            if region_errors:
                result["errors"] = region_errors
                result["partial_data"] = True
                result["success_rate"] = (
                    len(region_results) / (len(region_results) + len(region_errors))
                    if (len(region_results) + len(region_errors)) > 0
                    else 0
                )

            return result

        return await self._collect_data_template(
            fetch_tgw_route_data, regions, filters, "TGW route"
        )

    async def _collect_security_group_data(
        self, regions: List[str], filters: NetworkDataFilter
    ) -> Dict[str, Any]:
        """
        Collect security group data with pagination support and resilience.

        This method implements security group data collection with pagination
        and resilience patterns to handle large numbers of security groups across regions,
        with proper retry and exponential backoff for throttling and transient errors.
        """

        async def fetch_security_group_data(regions: List[str], filters: NetworkDataFilter):
            security_groups = []
            region_results = {}
            region_errors = {}

            for region in regions:
                try:
                    # Use direct client access with resilient_aws_call
                    # Build filter parameters
                    kwargs = {}
                    if filters.resource_ids:
                        kwargs["GroupIds"] = filters.resource_ids

                    # Get client and use pagination with resilience
                    async with self.aws_manager.client_context("ec2", region) as ec2:
                        security_groups_data = await self._paginated_aws_collection(
                            ec2, "describe_security_groups", **kwargs
                        )

                        # Add region info to each security group
                        for sg in security_groups_data:
                            sg["Region"] = region
                            security_groups.append(sg)

                        self.logger.info(
                            f"Successfully collected {len(security_groups_data)} security groups from {region}"
                        )
                        region_results[region] = len(security_groups_data)

                except RetryExhaustedError as e:
                    self.logger.error(
                        f"Retry limit exceeded collecting security groups in {region}: {e}"
                    )
                    region_errors[region] = f"Retry limit exceeded: {str(e.original_error)}"

                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "")
                    error_message = e.response.get("Error", {}).get("Message", "")
                    self.logger.error(
                        f"AWS error collecting security groups in {region}: {error_code} - {error_message}"
                    )
                    region_errors[region] = f"AWS error: {error_code} - {error_message}"

                except Exception as e:
                    self.logger.error(
                        f"Unexpected error collecting security groups in {region}: {str(e)}"
                    )
                    region_errors[region] = f"Unexpected error: {str(e)}"

            # If we have at least some successful regions, continue with what we have
            if security_groups:
                result = {
                    "security_groups": security_groups,
                    "count": len(security_groups),
                    "regions": list(region_results.keys()),
                    "region_stats": region_results,
                }
                # Add errors if any occurred
                if region_errors:
                    result["errors"] = region_errors
                    result["partial_data"] = True
                    result["success_rate"] = len(region_results) / (
                        len(region_results) + len(region_errors)
                    )

                return result
            elif region_errors:
                # If all regions failed, raise an exception
                error_summary = ", ".join(
                    [f"{region}: {error}" for region, error in region_errors.items()]
                )
                raise ValueError(
                    f"Failed to collect security groups from any region: {error_summary}"
                )
            else:
                # No security groups found but no errors either
                return {
                    "security_groups": [],
                    "count": 0,
                    "regions": regions,
                    "message": "No security groups found in specified regions",
                }

        return await self._collect_data_template(
            fetch_security_group_data, regions, filters, "security group"
        )

    # Using apply_filters from BaseDataCollector

    async def _paginated_aws_collection(self, client, method_name, **kwargs) -> List[Any]:
        """Delegate to the base class method for paginated AWS collection."""
        return await self.paginated_aws_collection(client, method_name, **kwargs)

    async def _export_to_format(
        self,
        data: Dict[str, Any],
        format: NetworkDataExportFormat,
        output_path: str,
        include_metadata: bool = True,
    ) -> str:
        """Export data to specified format."""
        # Add metadata if requested
        if include_metadata:
            data["metadata"] = {
                "generated_at": datetime.now().isoformat(),
                "generator": "CloudWAN MCP Data Export",
                "version": "1.0.0",
            }

        # Get appropriate exporter class
        exporter_class = self._get_exporter_class(format)

        # Create exporter instance
        exporter = exporter_class(self)

        # Check dependencies
        success, error_message = await exporter.check_dependencies()
        if not success:
            raise ImportError(error_message)

        # Export data
        return await exporter.export(data, output_path)

    def _get_exporter_class(self, format: NetworkDataExportFormat) -> Type[FormatExporter]:
        """Get the appropriate exporter class for the format.

        Args:
            format: The export format

        Returns:
            The FormatExporter subclass for the format

        Raises:
            ValueError: If the format is not supported
        """
        exporter_classes = {
            NetworkDataExportFormat.JSON: JSONExporter,
            NetworkDataExportFormat.CSV: CSVExporter,
            NetworkDataExportFormat.YAML: YAMLExporter,
            NetworkDataExportFormat.EXCEL: ExcelExporter,
            NetworkDataExportFormat.MARKDOWN: MarkdownExporter,
            NetworkDataExportFormat.HTML: HTMLExporter,
            NetworkDataExportFormat.XML: XMLExporter,
        }

        exporter_class = exporter_classes.get(format)
        if not exporter_class:
            raise ValueError(f"Unsupported export format: {format}")

        return exporter_class

    def _topology_to_dict(self, topology: Any) -> Dict[str, Any]:
        """
        Convert NetworkTopology to dictionary using type-safe protocols.

        Args:
            topology: NetworkTopology object to convert

        Returns:
            Dictionary representation of the topology
        """
        # First try to convert the whole topology object at once
        try:
            return self._convert_to_dict(topology)
        except TypeError:
            # If that fails, try to convert individual attributes
            result = {}
            for attr in ["elements", "connections", "regions", "accounts", "metadata"]:
                if hasattr(topology, attr):
                    value = getattr(topology, attr)
                    try:
                        result[attr] = self._convert_to_dict(value)
                    except TypeError:
                        # If attribute can't be converted, use it as is
                        result[attr] = value

            return result

    # Using generate_metadata from BaseDataCollector

    # Using generate_streaming_metadata from BaseDataCollector

    def _get_streaming_collector(
        self, data_type: NetworkDataType, regions: List[str], filters: NetworkDataFilter
    ) -> AsyncGenerator:
        """Get the appropriate streaming data collector for the data type.

        Args:
            data_type: Type of network data to collect
            regions: AWS regions to collect data from
            filters: Data filtering options

        Returns:
            Async generator that yields chunks of data
        """
        collectors = {
            NetworkDataType.TOPOLOGY: self._stream_topology_data,
            NetworkDataType.ROUTES: self._stream_route_data,
            NetworkDataType.SEGMENT_ROUTES: self._stream_segment_route_data,
            NetworkDataType.ATTACHMENTS: self._stream_attachment_data,
            NetworkDataType.PATH_TRACE: self._stream_path_trace_data,
            NetworkDataType.BGP_SESSIONS: self._stream_bgp_data,
            NetworkDataType.TRANSIT_GATEWAY_ROUTES: self._stream_tgw_route_data,
            NetworkDataType.SECURITY_GROUPS: self._stream_security_group_data,
            NetworkDataType.CORE_NETWORKS: self._stream_core_network_data,
            NetworkDataType.VPCS: self._stream_vpc_data,
        }

        collector = collectors.get(data_type)
        if not collector:
            raise ValueError(f"Unsupported data type for streaming: {data_type}")

        return collector(regions, filters)

    async def _stream_vpc_data(
        self, regions: List[str], filters: NetworkDataFilter
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream VPC data in chunks to minimize memory usage."""
        for region in regions:
            try:
                async with self.aws_manager.client_context("ec2", region) as ec2:
                    # Create paginator for VPC API
                    paginator = ec2.get_paginator("describe_vpcs")
                    kwargs = {}
                    if filters.vpc_ids:
                        kwargs["VpcIds"] = filters.vpc_ids

                    # Process each page of results
                    async for page in paginator.paginate(**kwargs):
                        vpcs = page.get("Vpcs", [])

                        # Add region information to each VPC
                        for vpc in vpcs:
                            vpc["Region"] = region

                        # Yield the VPCs from this page
                        if vpcs:
                            yield vpcs

                        # Fetch and yield subnets if requested
                        if filters.include_subnets:
                            for vpc in vpcs:
                                vpc_id = vpc.get("VpcId")
                                subnet_paginator = ec2.get_paginator("describe_subnets")
                                subnet_kwargs = {
                                    "Filters": [{"Name": "vpc-id", "Values": [vpc_id]}]
                                }

                                # Process each page of subnet results
                                async for subnet_page in subnet_paginator.paginate(**subnet_kwargs):
                                    subnets = subnet_page.get("Subnets", [])

                                    # Add region and VPC information to each subnet
                                    for subnet in subnets:
                                        subnet["Region"] = region
                                        subnet["VpcId"] = vpc_id

                                    # Yield the subnets from this page
                                    if subnets:
                                        yield {"vpc_id": vpc_id, "subnets": subnets}

                        # Fetch and yield route tables if requested
                        if filters.include_route_tables:
                            for vpc in vpcs:
                                vpc_id = vpc.get("VpcId")
                                rt_paginator = ec2.get_paginator("describe_route_tables")
                                rt_kwargs = {"Filters": [{"Name": "vpc-id", "Values": [vpc_id]}]}

                                # Process each page of route table results
                                async for rt_page in rt_paginator.paginate(**rt_kwargs):
                                    route_tables = rt_page.get("RouteTables", [])

                                    # Add region and VPC information to each route table
                                    for rt in route_tables:
                                        rt["Region"] = region
                                        rt["VpcId"] = vpc_id

                                    # Yield the route tables from this page
                                    if route_tables:
                                        yield {
                                            "vpc_id": vpc_id,
                                            "route_tables": route_tables,
                                        }

            except Exception as e:
                self.logger.error(f"Error streaming VPC data for region {region}: {e}")
                yield {"error": f"Failed to stream VPC data for region {region}: {str(e)}"}

    async def _stream_security_group_data(
        self, regions: List[str], filters: NetworkDataFilter
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream security group data in chunks to minimize memory usage."""
        for region in regions:
            try:
                async with self.aws_manager.client_context("ec2", region) as ec2:
                    # Build filter parameters
                    kwargs = {}
                    if filters.resource_ids:
                        kwargs["GroupIds"] = filters.resource_ids

                    # Create paginator for security groups API
                    paginator = ec2.get_paginator("describe_security_groups")

                    # Process each page of results
                    async for page in paginator.paginate(**kwargs):
                        security_groups = page.get("SecurityGroups", [])

                        # Add region information to each security group
                        for sg in security_groups:
                            sg["Region"] = region

                        # Yield the security groups from this page
                        if security_groups:
                            yield security_groups
            except Exception as e:
                self.logger.error(f"Error streaming security group data for region {region}: {e}")
                yield {
                    "error": f"Failed to stream security group data for region {region}: {str(e)}"
                }

    async def _stream_core_network_data(
        self, regions: List[str], filters: NetworkDataFilter
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream core network data in chunks to minimize memory usage."""
        # Core networks are primarily in us-west-2
        core_regions = ["us-west-2"] if "us-west-2" in regions else regions[:1]

        for region in core_regions:
            try:
                async with self.aws_manager.client_context("networkmanager", region) as nm_client:
                    # Get core networks
                    core_networks_response = await resilient_aws_call(
                        nm_client.list_core_networks,
                        {},  # No params needed for list operation
                    )

                    core_networks = core_networks_response.get("CoreNetworks", [])

                    # Add region information to each core network
                    for core in core_networks:
                        core["Region"] = region

                    # Yield the core networks
                    if core_networks:
                        yield core_networks

                    # For each core network, get additional information
                    for core in core_networks:
                        core_id = core.get("CoreNetworkId")

                        # Get core network policy if needed
                        if filters.include_policies:
                            try:
                                policy_response = await resilient_aws_call(
                                    nm_client.get_core_network_policy,
                                    {"CoreNetworkId": core_id},
                                )

                                policy = policy_response.get("CoreNetworkPolicy", {})
                                policy["CoreNetworkId"] = core_id
                                policy["Region"] = region

                                # Yield the policy
                                yield {"policy": policy}
                            except Exception as e:
                                self.logger.warning(
                                    f"Failed to get policy for core network {core_id}: {e}"
                                )
            except Exception as e:
                self.logger.error(f"Error streaming core network data for region {region}: {e}")
                yield {"error": f"Failed to stream core network data for region {region}: {str(e)}"}

    # Implement other streaming data methods as needed
    async def _stream_topology_data(
        self, regions: List[str], filters: NetworkDataFilter
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream network topology data in chunks."""
        # This is a stub implementation - would need to be implemented based on your actual data structure
        if not self.topology_available:
            yield {"error": "Network topology discovery is not available"}
            return

        # Instead of collecting all data at once, stream it in chunks
        yield {"message": "Topology streaming not fully implemented"}

    async def _stream_route_data(
        self, regions: List[str], filters: NetworkDataFilter
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream route data in chunks."""
        # This is a stub implementation - would need to be implemented based on your actual data structure
        for region in regions:
            try:
                # Get VPC route tables in streaming fashion
                if filters.include_route_tables:
                    async with self.aws_manager.client_context("ec2", region) as ec2:
                        paginator = ec2.get_paginator("describe_route_tables")
                        kwargs = {}
                        if filters.vpc_ids:
                            kwargs["Filters"] = [{"Name": "vpc-id", "Values": filters.vpc_ids}]

                        # Process each page of results
                        async for page in paginator.paginate(**kwargs):
                            route_tables = page.get("RouteTables", [])

                            # Extract route information
                            routes = []
                            for rt in route_tables:
                                rt_id = rt.get("RouteTableId")
                                vpc_id = rt.get("VpcId")

                                for route in rt.get("Routes", []):
                                    route_entry = {
                                        "route_table_id": rt_id,
                                        "vpc_id": vpc_id,
                                        "region": region,
                                        "destination_cidr": route.get("DestinationCidrBlock"),
                                        "gateway_id": route.get("GatewayId"),
                                        "instance_id": route.get("InstanceId"),
                                        "state": route.get("State"),
                                    }
                                    routes.append(route_entry)

                            # Yield the routes from this page
                            if routes:
                                yield {"vpc_routes": routes}
            except Exception as e:
                self.logger.error(f"Error streaming route data for region {region}: {e}")
                yield {"error": f"Failed to stream route data for region {region}: {str(e)}"}

    async def _stream_segment_route_data(
        self, regions: List[str], filters: NetworkDataFilter
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream segment route data in chunks to minimize memory usage."""
        # Core networks are primarily in us-west-2
        core_regions = ["us-west-2"] if "us-west-2" in regions else regions[:1]

        for region in core_regions:
            try:
                async with self.aws_manager.client_context("networkmanager", region) as nm_client:
                    # Get core networks first
                    core_networks_response = await resilient_aws_call(
                        nm_client.list_core_networks,
                        {},  # No params needed for list operation
                    )

                    # For each core network, get segment information
                    core_networks = core_networks_response.get("CoreNetworks", [])
                    for core in core_networks:
                        core_id = core.get("CoreNetworkId")

                        # Get core network policy if needed
                        if filters.include_policies:
                            try:
                                policy_response = await resilient_aws_call(
                                    nm_client.get_core_network_policy,
                                    {"CoreNetworkId": core_id},
                                )

                                # Extract segment definitions from policy
                                policy = policy_response.get("CoreNetworkPolicy", {})
                                policy_doc = json.loads(policy.get("PolicyDocument", "{}"))

                                # Add policy to collection
                                policy_entry = {
                                    "core_network_id": core_id,
                                    "policy_version": policy.get("PolicyVersionId"),
                                    "change_set_state": policy.get("ChangeSetState"),
                                    "segments": policy_doc.get("segments", []),
                                    "region": region,
                                }

                                # Yield policy data in chunks
                                yield [policy_entry]
                            except Exception as e:
                                self.logger.warning(
                                    f"Failed to get core network policy for {core_id}: {e}"
                                )

                        # Get segment-specific route information by segment name
                        try:
                            # Get core network segments
                            segments_response = await resilient_aws_call(
                                nm_client.list_core_network_segments,
                                {"CoreNetworkId": core_id},
                            )

                            segments_list = segments_response.get("CoreNetworkSegments", [])

                            # Filter by segment names if specified
                            if filters.segment_names:
                                segments_list = [
                                    s
                                    for s in segments_list
                                    if s.get("SegmentName") in filters.segment_names
                                ]

                            # Yield segments data
                            if segments_list:
                                yield [
                                    {
                                        "core_network_id": core_id,
                                        "segments": segments_list,
                                    }
                                ]

                        except Exception as e:
                            self.logger.warning(
                                f"Failed to get core network segments for {core_id}: {e}"
                            )

                        # For each segment, get route information
                        for segment in segments_list:
                            segment_name = segment.get("SegmentName")

                            try:
                                # Get routes for this segment
                                routes_response = await resilient_aws_call(
                                    nm_client.get_core_network_routes,
                                    {
                                        "CoreNetworkId": core_id,
                                        "SegmentName": segment_name,
                                    },
                                )

                                # Extract and normalize segment routes
                                segment_routes = []
                                for route in routes_response.get("Routes", []):
                                    route_entry = {
                                        "core_network_id": core_id,
                                        "segment_name": segment_name,
                                        "edge_location": segment.get("EdgeLocation"),
                                        "destination_cidr": route.get("DestinationCidrBlock"),
                                        "attachment_id": route.get("AttachmentId"),
                                        "attachment_type": route.get("AttachmentType"),
                                        "route_type": route.get("RouteType"),
                                        "state": route.get("State"),
                                        "region": region,
                                    }
                                    segment_routes.append(route_entry)

                                # Yield segment routes in chunks
                                if segment_routes:
                                    yield segment_routes
                            except Exception as e:
                                self.logger.warning(
                                    f"Failed to get routes for segment {segment_name}: {e}"
                                )
            except Exception as e:
                self.logger.error(f"Error streaming segment route data for region {region}: {e}")
                yield [
                    {"error": f"Failed to stream segment route data for region {region}: {str(e)}"}
                ]

    async def _stream_attachment_data(
        self, regions: List[str], filters: NetworkDataFilter
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream attachment data in chunks to minimize memory usage."""
        for region in regions:
            try:
                # Get CloudWAN attachments if needed
                if filters.include_cloudwan_attachments:
                    async with self.aws_manager.client_context(
                        "networkmanager", region
                    ) as nm_client:
                        # Get global networks first for CloudWAN
                        global_networks = await resilient_aws_call(
                            nm_client.describe_global_networks, {}
                        )

                        for gn in global_networks.get("GlobalNetworks", []):
                            gn_id = gn.get("GlobalNetworkId")

                            # Get core networks for this global network
                            core_networks = await resilient_aws_call(
                                nm_client.list_core_networks, {}
                            )

                            for core in core_networks.get("CoreNetworks", []):
                                core_id = core.get("CoreNetworkId")

                                # Get attachments for this core network with pagination support
                                next_token = None
                                while True:
                                    kwargs = {"CoreNetworkId": core_id}
                                    if next_token:
                                        kwargs["NextToken"] = next_token

                                    attachments_response = await resilient_aws_call(
                                        nm_client.list_core_network_attachments, kwargs
                                    )

                                    # Process and filter attachments
                                    core_attachments = attachments_response.get(
                                        "CoreNetworkAttachments", []
                                    )

                                    # Filter by attachment types if specified
                                    if filters.attachment_types:
                                        core_attachments = [
                                            a
                                            for a in core_attachments
                                            if a.get("AttachmentType") in filters.attachment_types
                                        ]

                                    # Filter by segment names if specified
                                    if filters.segment_names:
                                        core_attachments = [
                                            a
                                            for a in core_attachments
                                            if a.get("SegmentName") in filters.segment_names
                                        ]

                                    # Normalize and add attachment data
                                    cloudwan_attachments = []
                                    for attachment in core_attachments:
                                        attachment_entry = {
                                            "core_network_id": core_id,
                                            "global_network_id": gn_id,
                                            "attachment_id": attachment.get("Attachment", {}).get(
                                                "AttachmentId"
                                            ),
                                            "attachment_type": attachment.get("AttachmentType"),
                                            "edge_location": attachment.get("EdgeLocation"),
                                            "resource_arn": attachment.get("ResourceArn"),
                                            "segment_name": attachment.get("SegmentName"),
                                            "state": attachment.get("State"),
                                            "region": attachment.get("AttachmentRegion", region),
                                            "owner_account": attachment.get("OwnerAccountId"),
                                        }
                                        cloudwan_attachments.append(attachment_entry)

                                    # Yield attachments in chunks
                                    if cloudwan_attachments:
                                        yield {"cloudwan_attachments": cloudwan_attachments}

                                    # Check for pagination
                                    next_token = attachments_response.get("NextToken")
                                    if not next_token:
                                        break

                # Get Transit Gateway attachments if needed
                if filters.include_tgw_attachments:
                    async with self.aws_manager.client_context("ec2", region) as ec2:
                        # Get transit gateways first
                        paginator = ec2.get_paginator("describe_transit_gateways")

                        # Process each page of transit gateways
                        async for page in paginator.paginate():
                            tgws = page.get("TransitGateways", [])

                            # For each TGW, get attachments
                            for tgw in tgws:
                                tgw_id = tgw.get("TransitGatewayId")

                                # Get TGW attachments with pagination
                                attachment_paginator = ec2.get_paginator(
                                    "describe_transit_gateway_attachments"
                                )
                                attachment_kwargs = {
                                    "Filters": [
                                        {
                                            "Name": "transit-gateway-id",
                                            "Values": [tgw_id],
                                        }
                                    ]
                                }

                                # Process each page of attachments
                                async for attachment_page in attachment_paginator.paginate(
                                    **attachment_kwargs
                                ):
                                    tgw_attachments = attachment_page.get(
                                        "TransitGatewayAttachments", []
                                    )

                                    # Filter by attachment types if specified
                                    if filters.attachment_types:
                                        tgw_attachments = [
                                            a
                                            for a in tgw_attachments
                                            if a.get("ResourceType") in filters.attachment_types
                                        ]

                                    # Normalize attachment data
                                    formatted_attachments = []
                                    for attachment in tgw_attachments:
                                        attachment_entry = {
                                            "transit_gateway_id": tgw_id,
                                            "transit_gateway_attachment_id": attachment.get(
                                                "TransitGatewayAttachmentId"
                                            ),
                                            "resource_type": attachment.get("ResourceType"),
                                            "resource_id": attachment.get("ResourceId"),
                                            "state": attachment.get("State"),
                                            "association_state": attachment.get(
                                                "Association", {}
                                            ).get("State"),
                                            "region": region,
                                        }
                                        formatted_attachments.append(attachment_entry)

                                    # Yield attachments in chunks
                                    if formatted_attachments:
                                        yield {"tgw_attachments": formatted_attachments}
            except Exception as e:
                self.logger.error(f"Error streaming attachment data for region {region}: {e}")
                yield {"error": f"Failed to stream attachment data for region {region}: {str(e)}"}
        yield {"message": "Attachment streaming not fully implemented"}

    async def _stream_path_trace_data(
        self, regions: List[str], filters: NetworkDataFilter
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream path trace data in chunks."""
        # Path trace data is typically not large enough to need streaming
        if not hasattr(filters, "source_ip") or not hasattr(filters, "destination_ip"):
            yield {"error": "Both source_ip and destination_ip are required for path trace export"}
            return

        try:
            # Get path trace data
            trace_data = await self.path_tracing.execute(
                source_ip=filters.source_ip,
                destination_ip=filters.destination_ip,
                protocol=filters.protocol if hasattr(filters, "protocol") else "tcp",
                port=filters.port if hasattr(filters, "port") else 443,
                regions=regions,
            )

            # Since path trace data is typically not large, we can yield it all at once
            yield trace_data
        except Exception as e:
            self.logger.error(f"Error streaming path trace data: {e}")
            yield {"error": f"Failed to stream path trace data: {str(e)}"}

    async def _stream_bgp_data(
        self, regions: List[str], filters: NetworkDataFilter
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream BGP session data in chunks to minimize memory usage."""
        for region in regions:
            try:
                async with self.aws_manager.client_context("networkmanager", region) as nm_client:
                    # Get global networks first
                    global_networks_response = await resilient_aws_call(
                        nm_client.describe_global_networks,
                        {},  # No params needed for list operation
                    )

                    global_networks = global_networks_response.get("GlobalNetworks", [])

                    # For each global network, get the BGP peers
                    for gn in global_networks:
                        gn_id = gn.get("GlobalNetworkId")

                        # Get core networks for this global network to find BGP peers
                        try:
                            # Get core network connections with pagination support
                            next_token = None
                            while True:
                                kwargs = {"GlobalNetworkId": gn_id}
                                if next_token:
                                    kwargs["NextToken"] = next_token

                                connections_response = await resilient_aws_call(
                                    nm_client.describe_global_networks_peering, kwargs
                                )

                                # Extract peering connections
                                connections = connections_response.get("GlobalNetworkPeerings", [])

                                # Find BGP peerings
                                bgp_connections = []
                                for conn in connections:
                                    if conn.get("PeeringType") == "BGP":
                                        conn["Region"] = region
                                        conn["GlobalNetworkId"] = gn_id
                                        bgp_connections.append(conn)

                                # Yield BGP connections in chunks
                                if bgp_connections:
                                    yield {"bgp_connections": bgp_connections}

                                # Check for pagination
                                next_token = connections_response.get("NextToken")
                                if not next_token:
                                    break

                            # Get BGP sessions if using core network analyzer
                            if hasattr(self, "bgp_analyzer"):
                                # Get BGP sessions with pagination
                                next_token = None
                                while True:
                                    kwargs = {"GlobalNetworkId": gn_id}
                                    if next_token:
                                        kwargs["NextToken"] = next_token

                                    sessions_response = await resilient_aws_call(
                                        nm_client.get_bgp_sessions, kwargs
                                    )

                                    # Extract BGP sessions
                                    sessions = sessions_response.get("BgpSessions", [])

                                    # Process and add region information
                                    for session in sessions:
                                        session["Region"] = region
                                        session["GlobalNetworkId"] = gn_id

                                        # Add performance metrics if requested
                                        if filters.include_performance_metrics:
                                            try:
                                                session_id = session.get("BgpSessionId")
                                                metrics_response = await resilient_aws_call(
                                                    nm_client.get_bgp_session_metrics,
                                                    {
                                                        "GlobalNetworkId": gn_id,
                                                        "BgpSessionId": session_id,
                                                    },
                                                )
                                                session["Metrics"] = metrics_response.get(
                                                    "Metrics", {}
                                                )
                                            except Exception as e:
                                                self.logger.warning(
                                                    f"Failed to get metrics for BGP session {session_id}: {e}"
                                                )

                                    # Yield BGP sessions in chunks
                                    if sessions:
                                        yield {"bgp_sessions": sessions}

                                    # Check for pagination
                                    next_token = sessions_response.get("NextToken")
                                    if not next_token:
                                        break

                        except Exception as e:
                            self.logger.warning(
                                f"Failed to get BGP data for global network {gn_id}: {e}"
                            )

                # Use the BGP analyzer tool if available
                if hasattr(self, "bgp_analyzer"):
                    try:
                        # Get BGP data through the analyzer tool
                        result = await self.bgp_analyzer.analyze_bgp_data(
                            regions=[region],
                            include_metrics=filters.include_performance_metrics,
                        )

                        # Process results in chunks
                        if isinstance(result, list) and result:
                            # Yield in chunks of 20 records
                            chunk_size = 20
                            for i in range(0, len(result), chunk_size):
                                chunk = result[i : i + chunk_size]
                                yield {"bgp_analysis": chunk}
                        elif isinstance(result, dict):
                            # Single result can be yielded directly
                            yield result
                    except Exception as e:
                        self.logger.warning(f"Failed to use BGP analyzer for region {region}: {e}")

            except Exception as e:
                self.logger.error(f"Error streaming BGP data for region {region}: {e}")
                yield {"error": f"Failed to stream BGP data for region {region}: {str(e)}"}

    async def _stream_tgw_route_data(
        self, regions: List[str], filters: NetworkDataFilter
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream Transit Gateway route data in chunks to minimize memory usage."""
        for region in regions:
            try:
                async with self.aws_manager.client_context("ec2", region) as ec2:
                    # Get transit gateways with pagination
                    paginator = ec2.get_paginator("describe_transit_gateways")

                    # Process each page of transit gateways
                    async for page in paginator.paginate():
                        tgws = page.get("TransitGateways", [])

                        # Add region info to each transit gateway
                        for tgw in tgws:
                            tgw["Region"] = region

                        # Yield transit gateways in chunks
                        if tgws:
                            yield {"transit_gateways": tgws}

                        # For each TGW, get route tables and routes
                        for tgw in tgws:
                            tgw_id = tgw.get("TransitGatewayId")

                            # Get TGW route tables with pagination
                            rt_paginator = ec2.get_paginator(
                                "describe_transit_gateway_route_tables"
                            )
                            rt_kwargs = {
                                "Filters": [{"Name": "transit-gateway-id", "Values": [tgw_id]}]
                            }

                            async for rt_page in rt_paginator.paginate(**rt_kwargs):
                                tgw_route_tables = rt_page.get("TransitGatewayRouteTables", [])

                                # Add region info to each route table
                                for rt in tgw_route_tables:
                                    rt["Region"] = region
                                    rt["TransitGatewayId"] = tgw_id

                                # Yield route tables in chunks
                                if tgw_route_tables:
                                    yield {"route_tables": tgw_route_tables}

                                # For each route table, get routes
                                for rt in tgw_route_tables:
                                    rt_id = rt.get("TransitGatewayRouteTableId")

                                    # First get static routes
                                    try:
                                        static_routes_response = await resilient_aws_call(
                                            ec2.search_transit_gateway_routes,
                                            {
                                                "TransitGatewayRouteTableId": rt_id,
                                                "Filters": [
                                                    {
                                                        "Name": "type",
                                                        "Values": ["static"],
                                                    }
                                                ],
                                            },
                                        )

                                        # Extract and normalize static routes
                                        static_routes = []
                                        for route in static_routes_response.get("Routes", []):
                                            route["Region"] = region
                                            route["RouteTableId"] = rt_id
                                            route["TransitGatewayId"] = tgw_id
                                            route["RouteType"] = "static"
                                            static_routes.append(route)

                                        # Yield static routes in chunks
                                        if static_routes:
                                            yield {"static_routes": static_routes}

                                    except Exception as e:
                                        self.logger.warning(
                                            f"Failed to get static routes for TGW route table {rt_id}: {e}"
                                        )

                                    # Then get propagated routes
                                    try:
                                        propagated_routes_response = await resilient_aws_call(
                                            ec2.search_transit_gateway_routes,
                                            {
                                                "TransitGatewayRouteTableId": rt_id,
                                                "Filters": [
                                                    {
                                                        "Name": "type",
                                                        "Values": ["propagated"],
                                                    }
                                                ],
                                            },
                                        )

                                        # Extract and normalize propagated routes
                                        propagated_routes = []
                                        for route in propagated_routes_response.get("Routes", []):
                                            route["Region"] = region
                                            route["RouteTableId"] = rt_id
                                            route["TransitGatewayId"] = tgw_id
                                            route["RouteType"] = "propagated"
                                            propagated_routes.append(route)

                                        # Yield propagated routes in chunks
                                        if propagated_routes:
                                            yield {"propagated_routes": propagated_routes}

                                    except Exception as e:
                                        self.logger.warning(
                                            f"Failed to get propagated routes for TGW route table {rt_id}: {e}"
                                        )

                                    # Get route propagations with pagination
                                    try:
                                        propagation_paginator = ec2.get_paginator(
                                            "get_transit_gateway_route_table_propagations"
                                        )
                                        propagation_kwargs = {"TransitGatewayRouteTableId": rt_id}

                                        async for prop_page in propagation_paginator.paginate(
                                            **propagation_kwargs
                                        ):
                                            propagations = prop_page.get(
                                                "TransitGatewayRouteTablePropagations",
                                                [],
                                            )

                                            # Add region info to each propagation
                                            for prop in propagations:
                                                prop["Region"] = region
                                                prop["TransitGatewayId"] = tgw_id
                                                prop["RouteTableId"] = rt_id

                                            # Yield propagations in chunks
                                            if propagations:
                                                yield {"propagations": propagations}

                                    except Exception as e:
                                        self.logger.warning(
                                            f"Failed to get propagations for TGW route table {rt_id}: {e}"
                                        )

                                    # Get route associations with pagination
                                    try:
                                        association_paginator = ec2.get_paginator(
                                            "get_transit_gateway_route_table_associations"
                                        )
                                        association_kwargs = {"TransitGatewayRouteTableId": rt_id}

                                        async for assoc_page in association_paginator.paginate(
                                            **association_kwargs
                                        ):
                                            associations = assoc_page.get("Associations", [])

                                            # Add region info to each association
                                            for assoc in associations:
                                                assoc["Region"] = region
                                                assoc["TransitGatewayId"] = tgw_id
                                                assoc["RouteTableId"] = rt_id

                                            # Yield associations in chunks
                                            if associations:
                                                yield {"associations": associations}

                                    except Exception as e:
                                        self.logger.warning(
                                            f"Failed to get associations for TGW route table {rt_id}: {e}"
                                        )

                            # Get transit gateway attachments with pagination
                            attachment_paginator = ec2.get_paginator(
                                "describe_transit_gateway_attachments"
                            )
                            attachment_kwargs = {
                                "Filters": [{"Name": "transit-gateway-id", "Values": [tgw_id]}]
                            }

                            async for attachment_page in attachment_paginator.paginate(
                                **attachment_kwargs
                            ):
                                attachments = attachment_page.get("TransitGatewayAttachments", [])

                                # Add region info to each attachment
                                for attachment in attachments:
                                    attachment["Region"] = region
                                    attachment["TransitGatewayId"] = tgw_id

                                # Filter by attachment types if specified
                                if filters.attachment_types:
                                    attachments = [
                                        a
                                        for a in attachments
                                        if a.get("ResourceType") in filters.attachment_types
                                    ]

                                # Yield attachments in chunks
                                if attachments:
                                    yield {"tgw_attachments": attachments}

            except Exception as e:
                self.logger.error(f"Error streaming TGW route data for region {region}: {e}")
                yield {"error": f"Failed to stream TGW route data for region {region}: {str(e)}"}
