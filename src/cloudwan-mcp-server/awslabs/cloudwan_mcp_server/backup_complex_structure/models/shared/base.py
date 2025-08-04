"""
Enhanced base data models for CloudWAN MCP Server with multi-region support.

This module extends the existing base models with enhanced multi-region capabilities,
improved error handling, comprehensive validation, and standardized response patterns.

Key Features:
- Enhanced multi-region operation support
- Comprehensive error context and recovery information
- Standardized pagination and filtering
- Advanced validation with custom validators
- Performance metrics and timing information
- Cache integration and invalidation support
- Detailed audit trails and operation tracking
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypeVar, Generic, Tuple
from pydantic import BaseModel, Field, field_validator, model_validator
import uuid

from .enums import HealthStatus

T = TypeVar('T')


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields with timezone support."""
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the record was created"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the record was last updated"
    )

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current UTC time."""
        self.updated_at = datetime.now(timezone.utc)

    def get_age_seconds(self) -> float:
        """Get age of record in seconds."""
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()

    def is_stale(self, max_age_seconds: int = 3600) -> bool:
        """Check if record is stale based on max age."""
        return self.get_age_seconds() > max_age_seconds


class RegionInfo(BaseModel):
    """Information about AWS region operations."""
    
    region: str = Field(description="AWS region identifier")
    status: str = Field(default="pending", description="Operation status in this region")
    success: bool = Field(default=False, description="Whether operation succeeded in this region")
    error_message: Optional[str] = Field(default=None, description="Error message if operation failed")
    operation_time_ms: Optional[float] = Field(default=None, description="Operation duration in milliseconds")
    resources_found: int = Field(default=0, description="Number of resources found in this region")
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this region info was last updated"
    )

    def mark_success(self, resources_count: int = 0, duration_ms: Optional[float] = None) -> None:
        """Mark region operation as successful."""
        self.status = "success"
        self.success = True
        self.resources_found = resources_count
        if duration_ms is not None:
            self.operation_time_ms = duration_ms
        self.last_updated = datetime.now(timezone.utc)

    def mark_failure(self, error: str, duration_ms: Optional[float] = None) -> None:
        """Mark region operation as failed."""
        self.status = "failed"
        self.success = False
        self.error_message = error
        if duration_ms is not None:
            self.operation_time_ms = duration_ms
        self.last_updated = datetime.now(timezone.utc)


class PaginationInfo(BaseModel):
    """Standardized pagination information."""
    
    page: int = Field(ge=1, default=1, description="Current page number (1-based)")
    per_page: int = Field(ge=1, le=1000, default=100, description="Items per page")
    total_items: Optional[int] = Field(default=None, description="Total number of items")
    total_pages: Optional[int] = Field(default=None, description="Total number of pages")
    has_next: bool = Field(default=False, description="Whether there are more pages")
    has_previous: bool = Field(default=False, description="Whether there are previous pages")
    next_token: Optional[str] = Field(default=None, description="Token for next page")
    previous_token: Optional[str] = Field(default=None, description="Token for previous page")

    @model_validator(mode='before')
    def calculate_pagination_info(cls, values):
        """Calculate pagination info when total_items is known."""
        if isinstance(values, dict):
            total_items = values.get('total_items')
            per_page = values.get('per_page', 100)
            page = values.get('page', 1)
            
            if total_items is not None:
                total_pages = (total_items + per_page - 1) // per_page
                values['total_pages'] = total_pages
                values['has_next'] = page < total_pages
                values['has_previous'] = page > 1
                
        return values

    def get_offset(self) -> int:
        """Get offset for database queries."""
        return (self.page - 1) * self.per_page

    def get_slice_indices(self) -> Tuple[int, int]:
        """Get slice indices for list slicing."""
        start = self.get_offset()
        end = start + self.per_page
        return start, end


class PerformanceMetrics(BaseModel):
    """Performance metrics for operations."""
    
    duration_ms: float = Field(description="Total operation duration in milliseconds")
    api_calls: int = Field(default=0, description="Number of API calls made")
    cache_hits: int = Field(default=0, description="Number of cache hits")
    cache_misses: int = Field(default=0, description="Number of cache misses")
    data_size_bytes: Optional[int] = Field(default=None, description="Size of data processed")
    memory_peak_mb: Optional[float] = Field(default=None, description="Peak memory usage in MB")
    cpu_time_ms: Optional[float] = Field(default=None, description="CPU time used in milliseconds")
    
    # Region-specific metrics
    region_metrics: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Per-region performance metrics"
    )

    def add_region_metric(self, region: str, metric: str, value: float) -> None:
        """Add a metric for a specific region."""
        if region not in self.region_metrics:
            self.region_metrics[region] = {}
        self.region_metrics[region][metric] = value

    def get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total

    def get_average_region_duration(self) -> Optional[float]:
        """Get average duration across regions."""
        durations = []
        for metrics in self.region_metrics.values():
            if 'duration_ms' in metrics:
                durations.append(metrics['duration_ms'])
        
        if not durations:
            return None
        return sum(durations) / len(durations)


class CacheInfo(BaseModel):
    """Cache information for responses."""
    
    used: bool = Field(default=False, description="Whether response was served from cache")
    ttl_seconds: Optional[int] = Field(default=None, description="Cache TTL in seconds")
    cache_key: Optional[str] = Field(default=None, description="Cache key used")
    invalidated_at: Optional[datetime] = Field(default=None, description="When cache was invalidated")
    hit_count: int = Field(default=0, description="Number of cache hits for this key")
    
    def is_expired(self) -> bool:
        """Check if cache entry would be expired now."""
        if not self.used or self.ttl_seconds is None:
            return True
        return self.get_age_seconds() > self.ttl_seconds

    def get_age_seconds(self) -> float:
        """Get age of cache entry in seconds."""
        if self.invalidated_at:
            return (datetime.now(timezone.utc) - self.invalidated_at).total_seconds()
        return 0.0


class EnhancedBaseResponse(TimestampMixin):
    """
    Enhanced base response model with comprehensive multi-region support.
    
    Extends the original BaseResponse with additional fields for better
    operational visibility, performance tracking, and error handling.
    """
    
    # Core response information
    operation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique operation identifier for tracing"
    )
    status: str = Field(
        default="success",
        pattern="^(success|partial|error|timeout|cancelled)$",
        description="Overall operation status"
    )
    
    # Multi-region information
    regions_requested: List[str] = Field(
        default_factory=list,
        description="Regions that were requested for this operation"
    )
    regions_analyzed: List[str] = Field(
        default_factory=list,
        description="Regions that were successfully analyzed"
    )
    region_details: Dict[str, RegionInfo] = Field(
        default_factory=dict,
        description="Detailed per-region operation information"
    )
    
    # Operation metrics
    success_count: int = Field(default=0, description="Number of successful operations")
    failure_count: int = Field(default=0, description="Number of failed operations")
    partial_count: int = Field(default=0, description="Number of partially successful operations")
    
    # Error handling
    error_message: Optional[str] = Field(default=None, description="Primary error message")
    error_details: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Detailed error information"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Warning messages that don't fail the operation"
    )
    
    # Performance and caching
    performance_metrics: Optional[PerformanceMetrics] = Field(
        default=None,
        description="Performance metrics for this operation"
    )
    cache_info: CacheInfo = Field(
        default_factory=CacheInfo,
        description="Cache information"
    )
    
    # Pagination support
    pagination: Optional[PaginationInfo] = Field(
        default=None,
        description="Pagination information for paginated responses"
    )
    
    # Additional metadata
    component: Optional[str] = Field(default=None, description="Component that generated this response")
    trace_id: Optional[str] = Field(default=None, description="Distributed tracing ID")
    user_agent: Optional[str] = Field(default=None, description="Client user agent")
    api_version: str = Field(default="1.0", description="API version used")

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate status field values."""
        valid_statuses = {'success', 'partial', 'error', 'timeout', 'cancelled'}
        if v not in valid_statuses:
            raise ValueError(f"Invalid status: {v}. Must be one of: {valid_statuses}")
        return v

    def add_region_info(self, region: str, success: bool = True, 
                       resources_count: int = 0, error: Optional[str] = None,
                       duration_ms: Optional[float] = None) -> None:
        """Add information about region operation."""
        region_info = RegionInfo(region=region)
        
        if success:
            region_info.mark_success(resources_count, duration_ms)
            if region not in self.regions_analyzed:
                self.regions_analyzed.append(region)
            self.success_count += 1
        else:
            region_info.mark_failure(error or "Unknown error", duration_ms)
            self.failure_count += 1
            
        self.region_details[region] = region_info
        
        if region not in self.regions_requested:
            self.regions_requested.append(region)

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        if warning not in self.warnings:
            self.warnings.append(warning)

    def set_error(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Set error information."""
        self.status = "error"
        self.error_message = message
        if details:
            self.error_details.update(details)

    def set_partial_success(self) -> None:
        """Mark response as partially successful."""
        if self.success_count > 0 and self.failure_count > 0:
            self.status = "partial"

    def get_success_rate(self) -> float:
        """Calculate success rate across all operations."""
        total = self.success_count + self.failure_count + self.partial_count
        if total == 0:
            return 1.0
        return self.success_count / total

    def has_errors(self) -> bool:
        """Check if response has any errors."""
        return self.status in ("error", "partial") or bool(self.error_message)

    def has_warnings(self) -> bool:
        """Check if response has warnings."""
        return len(self.warnings) > 0

    def is_complete_success(self) -> bool:
        """Check if operation was completely successful."""
        return self.status == "success" and self.failure_count == 0

    def get_region_summary(self) -> Dict[str, int]:
        """Get summary of region operation results."""
        summary = {"successful": 0, "failed": 0, "total": 0}
        
        for region_info in self.region_details.values():
            summary["total"] += 1
            if region_info.success:
                summary["successful"] += 1
            else:
                summary["failed"] += 1
                
        return summary

    def merge_response(self, other: "EnhancedBaseResponse") -> None:
        """Merge another response into this one."""
        # Merge regions
        self.regions_requested.extend(
            r for r in other.regions_requested if r not in self.regions_requested
        )
        self.regions_analyzed.extend(
            r for r in other.regions_analyzed if r not in self.regions_analyzed
        )
        
        # Merge region details
        self.region_details.update(other.region_details)
        
        # Merge counts
        self.success_count += other.success_count
        self.failure_count += other.failure_count
        self.partial_count += other.partial_count
        
        # Merge warnings
        self.warnings.extend(w for w in other.warnings if w not in self.warnings)
        
        # Update status based on combined results
        if self.failure_count > 0 and self.success_count > 0:
            self.status = "partial"
        elif self.failure_count > 0:
            self.status = "error"
        else:
            self.status = "success"
        
        # Merge error details
        if other.error_message and not self.error_message:
            self.error_message = other.error_message
        elif other.error_message and self.error_message:
            self.error_message = f"{self.error_message}; {other.error_message}"
        
        self.error_details.update(other.error_details)

    def to_summary(self) -> Dict[str, Any]:
        """Create a summary view of the response."""
        return {
            "operation_id": self.operation_id,
            "status": self.status,
            "regions": len(self.regions_analyzed),
            "success_rate": self.get_success_rate(),
            "duration_ms": self.performance_metrics.duration_ms if self.performance_metrics else None,
            "cache_used": self.cache_info.used,
            "has_errors": self.has_errors(),
            "has_warnings": self.has_warnings(),
            "timestamp": self.created_at.isoformat(),
        }


class FilterCriteria(BaseModel):
    """Standardized filtering criteria for queries."""
    
    # Text filters
    name_contains: Optional[str] = Field(default=None, description="Filter by name containing text")
    name_exact: Optional[str] = Field(default=None, description="Filter by exact name match")
    tag_filters: Dict[str, str] = Field(default_factory=dict, description="Key-value tag filters")
    
    # Status filters
    status_filter: Optional[List[str]] = Field(default=None, description="Filter by status values")
    health_filter: Optional[List[HealthStatus]] = Field(default=None, description="Filter by health status")
    
    # Region filters
    regions: Optional[List[str]] = Field(default=None, description="Filter by AWS regions")
    exclude_regions: Optional[List[str]] = Field(default=None, description="Exclude specific regions")
    
    # Time filters
    created_after: Optional[datetime] = Field(default=None, description="Filter by creation time")
    created_before: Optional[datetime] = Field(default=None, description="Filter by creation time")
    updated_after: Optional[datetime] = Field(default=None, description="Filter by update time")
    updated_before: Optional[datetime] = Field(default=None, description="Filter by update time")
    
    # Resource type filters
    resource_types: Optional[List[str]] = Field(default=None, description="Filter by resource types")
    
    def has_filters(self) -> bool:
        """Check if any filters are applied."""
        return any([
            self.name_contains,
            self.name_exact,
            self.tag_filters,
            self.status_filter,
            self.health_filter,
            self.regions,
            self.exclude_regions,
            self.created_after,
            self.created_before,
            self.updated_after,
            self.updated_before,
            self.resource_types,
        ])

    def matches_tags(self, tags: Dict[str, str]) -> bool:
        """Check if resource tags match filter criteria."""
        for key, value in self.tag_filters.items():
            if key not in tags or tags[key] != value:
                return False
        return True

    def matches_region(self, region: str) -> bool:
        """Check if region matches filter criteria."""
        if self.regions and region not in self.regions:
            return False
        if self.exclude_regions and region in self.exclude_regions:
            return False
        return True


class EnhancedAWSResource(TimestampMixin):
    """Enhanced AWS resource model with comprehensive metadata."""
    
    # Core identification
    resource_id: str = Field(description="AWS resource identifier")
    resource_type: str = Field(description="Type of AWS resource")
    arn: Optional[str] = Field(default=None, description="AWS Resource Name")
    
    # Location information
    region: str = Field(description="AWS region")
    availability_zone: Optional[str] = Field(default=None, description="Availability zone")
    
    # Resource metadata
    name: Optional[str] = Field(default=None, description="Resource name or identifier")
    description: Optional[str] = Field(default=None, description="Resource description")
    tags: Dict[str, str] = Field(default_factory=dict, description="Resource tags")
    
    # State and health
    state: str = Field(default="unknown", description="Current resource state")
    health_status: HealthStatus = Field(default=HealthStatus.UNKNOWN, description="Health status")
    
    # Relationships
    parent_resource_id: Optional[str] = Field(default=None, description="Parent resource ID")
    child_resource_ids: List[str] = Field(default_factory=list, description="Child resource IDs")
    
    # CloudWAN specific
    core_network_id: Optional[str] = Field(default=None, description="Associated core network")
    segment_name: Optional[str] = Field(default=None, description="CloudWAN segment")
    attachment_id: Optional[str] = Field(default=None, description="Attachment ID")
    
    # Operational information
    owner_account_id: Optional[str] = Field(default=None, description="AWS account ID")
    cross_account: bool = Field(default=False, description="Whether resource is cross-account")
    
    # Additional context
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Raw AWS API data")
    custom_attributes: Dict[str, Any] = Field(default_factory=dict, description="Custom attributes")

    def get_identifier(self) -> str:
        """Get the best available identifier for this resource."""
        return self.name or self.resource_id

    def has_tag(self, key: str, value: Optional[str] = None) -> bool:
        """Check if resource has a specific tag."""
        if key not in self.tags:
            return False
        if value is not None:
            return self.tags[key] == value
        return True

    def is_healthy(self) -> bool:
        """Check if resource is in healthy state."""
        return self.health_status in (HealthStatus.HEALTHY, HealthStatus.WARNING)

    def is_cloudwan_resource(self) -> bool:
        """Check if resource is CloudWAN related."""
        return any([
            self.core_network_id,
            self.segment_name,
            self.attachment_id,
            'cloudwan' in self.resource_type.lower(),
            'core-network' in self.resource_type.lower(),
        ])

    def add_child_resource(self, child_id: str) -> None:
        """Add a child resource ID."""
        if child_id not in self.child_resource_ids:
            self.child_resource_ids.append(child_id)

    def remove_child_resource(self, child_id: str) -> None:
        """Remove a child resource ID."""
        if child_id in self.child_resource_ids:
            self.child_resource_ids.remove(child_id)

    def update_health_status(self, new_status: HealthStatus, reason: Optional[str] = None) -> None:
        """Update health status with optional reason."""
        self.health_status = new_status
        self.update_timestamp()
        
        if reason:
            self.custom_attributes["health_update_reason"] = reason
            self.custom_attributes["health_update_time"] = datetime.now(timezone.utc).isoformat()


# Generic paginated response wrapper
class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    
    items: List[T] = Field(description="List of items in current page")
    pagination: PaginationInfo = Field(description="Pagination information")
    total_count: Optional[int] = Field(default=None, description="Total number of items available")
    
    @classmethod
    def create(
        cls,
        items: List[T],
        page: int = 1,
        per_page: int = 100,
        total_count: Optional[int] = None
    ) -> "PaginatedResponse[T]":
        """Create paginated response from items."""
        pagination = PaginationInfo(
            page=page,
            per_page=per_page,
            total_items=total_count or len(items)
        )
        
        # Apply pagination to items
        start, end = pagination.get_slice_indices()
        paginated_items = items[start:end]
        
        return cls(
            items=paginated_items,
            pagination=pagination,
            total_count=total_count
        )


# Export key classes for easy importing
__all__ = [
    'TimestampMixin',
    'RegionInfo', 
    'PaginationInfo',
    'PerformanceMetrics',
    'CacheInfo',
    'EnhancedBaseResponse',
    'FilterCriteria',
    'EnhancedAWSResource',
    'PaginatedResponse',
]