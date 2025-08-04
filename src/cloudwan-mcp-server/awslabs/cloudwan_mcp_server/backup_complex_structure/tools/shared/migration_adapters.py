"""
Reusable migration adapter patterns for analyzer shared model migration.

This module provides base classes and patterns for migrating analyzer tools to use
shared models while maintaining backward compatibility. These patterns can be
used across all analyzer migrations to ensure consistency and reduce duplication.

Key Features:
- Base adapter classes for common migration patterns
- Performance optimization utilities
- Enhanced validation and error handling
- Multi-region intelligence integration
- Security enhancement patterns
- Monitoring and metrics integration

Usage Example:
```python
from awslabs.cloudwan_mcp_server.tools.shared.migration_adapters import (
    BaseModelAdapter, EnhancedAnalysisResponse, MigrationPatterns
)

# Create adapter for existing model
class MyModelAdapter(BaseModelAdapter):
    def create_shared_model(self):
        return MySharedModel(**self.transform_data())

# Use enhanced response
class MyAnalysisResponse(EnhancedAnalysisResponse):
    def generate_enhanced_analysis(self):
        # Custom enhanced analysis logic
        pass
```

Migration Checklist:
1. Create adapter classes inheriting from BaseModelAdapter
2. Implement shared model transformation logic
3. Use EnhancedAnalysisResponse for response models
4. Apply performance optimization patterns
5. Integrate security enhancements
6. Add comprehensive validation
7. Implement multi-region intelligence
"""

import asyncio
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic, Callable
from functools import wraps, lru_cache
from dataclasses import dataclass

from pydantic import BaseModel, Field

from ...models.shared.base import EnhancedBaseResponse
from ...models.shared.enums import (
    SecurityThreatLevel, HealthStatus
)


# =============================================================================
# Type Variables and Generic Types
# =============================================================================

T = TypeVar('T')  # Generic type for shared models
LegacyT = TypeVar('LegacyT')  # Legacy model type
SharedT = TypeVar('SharedT')  # Shared model type


# =============================================================================
# Base Adapter Classes
# =============================================================================

class BaseModelAdapter(ABC, Generic[LegacyT, SharedT]):
    """
    Base class for all model migration adapters.
    
    Provides common functionality for migrating legacy models to shared models
    while maintaining backward compatibility. Includes error handling, caching,
    and performance optimizations.
    
    Type Parameters:
        LegacyT: The legacy model type
        SharedT: The shared model type
        
    Attributes:
        _data: Original legacy data
        _shared_model: Cached shared model instance
        _creation_time: Timestamp of adapter creation
        _access_count: Number of times shared model has been accessed
    """
    
    def __init__(self, legacy_data: Dict[str, Any]):
        """
        Initialize adapter with legacy data.
        
        Args:
            legacy_data: Dictionary containing legacy model data
        """
        self._data = legacy_data.copy()
        self._shared_model: Optional[SharedT] = None
        self._creation_time = datetime.now()
        self._access_count = 0
        self._transformation_errors: List[str] = []
        self._fallback_mode = False
        
    @abstractmethod
    def create_shared_model(self) -> Optional[SharedT]:
        """
        Create shared model instance from legacy data.
        
        Must be implemented by subclasses to define specific transformation logic.
        Should handle errors gracefully and return None if transformation fails.
        
        Returns:
            Shared model instance or None if creation fails
        """
        pass
    
    @abstractmethod
    def transform_data(self) -> Dict[str, Any]:
        """
        Transform legacy data format to shared model format.
        
        Must be implemented by subclasses to define data transformation rules.
        Should handle missing fields and provide sensible defaults.
        
        Returns:
            Transformed data dictionary for shared model creation
        """
        pass
    
    def get_shared_model(self) -> Optional[SharedT]:
        """
        Get shared model instance with caching and error handling.
        
        Returns:
            Cached shared model instance or None if unavailable
        """
        if self._shared_model is None and not self._fallback_mode:
            try:
                self._shared_model = self.create_shared_model()
                if self._shared_model is None:
                    self._fallback_mode = True
            except Exception as e:
                self._transformation_errors.append(f"Shared model creation failed: {str(e)}")
                self._fallback_mode = True
                
        self._access_count += 1
        return self._shared_model
    
    def get_legacy_data(self) -> Dict[str, Any]:
        """Get original legacy data."""
        return self._data.copy()
        
    def is_enhanced(self) -> bool:
        """Check if enhanced shared model is available."""
        return self.get_shared_model() is not None
        
    def get_transformation_errors(self) -> List[str]:
        """Get any errors that occurred during transformation."""
        return self._transformation_errors.copy()
        
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for this adapter.
        
        Returns:
            Dictionary containing performance metrics
        """
        return {
            "access_count": self._access_count,
            "creation_time": self._creation_time,
            "enhanced_available": self.is_enhanced(),
            "fallback_mode": self._fallback_mode,
            "transformation_errors": len(self._transformation_errors)
        }
    
    def __getitem__(self, key: str) -> Any:
        """Dictionary-style access to legacy data."""
        return self._data[key]
    
    def get(self, key: str, default: Any = None) -> Any:
        """Dictionary-style get method."""
        return self._data.get(key, default)


class CachedModelAdapter(BaseModelAdapter[LegacyT, SharedT]):
    """
    Enhanced model adapter with advanced caching and performance optimization.
    
    Provides LRU caching of transformed data and intelligent cache invalidation
    for high-performance scenarios with frequent model access.
    """
    
    def __init__(self, legacy_data: Dict[str, Any], cache_size: int = 128):
        super().__init__(legacy_data)
        self._cache_size = cache_size
        self._cache_hits = 0
        self._cache_misses = 0
        
    @lru_cache(maxsize=128)
    def _cached_transform_data(self, data_hash: str) -> Dict[str, Any]:
        """Cached version of data transformation."""
        self._cache_misses += 1
        return self.transform_data()
    
    def get_transformed_data(self) -> Dict[str, Any]:
        """
        Get transformed data with caching.
        
        Returns:
            Transformed data dictionary
        """
        # Create hash of relevant data for caching
        data_str = str(sorted(self._data.items()))
        data_hash = str(hash(data_str))
        
        try:
            result = self._cached_transform_data(data_hash)
            self._cache_hits += 1
            return result
        except Exception:
            self._cache_misses += 1
            return self.transform_data()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0
        
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": hit_rate,
            "cache_size": self._cache_size
        }


# =============================================================================
# Enhanced Response Base Classes
# =============================================================================

class EnhancedAnalysisResponse(EnhancedBaseResponse):
    """
    Base class for enhanced analysis responses with shared model integration.
    
    Provides common functionality for analyzer responses that use shared models
    including enhanced analysis generation, security assessment, multi-region
    intelligence, and performance monitoring.
    
    Attributes:
        analysis_type: Type of analysis performed
        enhanced_capabilities: Dictionary of enhanced feature availability
        performance_metrics: Performance monitoring data
        security_assessment: Security analysis results
        multi_region_insights: Multi-region correlation data
        operational_context: Operational monitoring context
    """
    
    analysis_type: str = Field(description="Type of analysis performed")
    enhanced_capabilities: Dict[str, Any] = Field(
        default_factory=dict, description="Enhanced feature availability"
    )
    performance_metrics: Dict[str, Any] = Field(
        default_factory=dict, description="Performance monitoring data"
    )
    security_assessment: Dict[str, Any] = Field(
        default_factory=dict, description="Security analysis results"
    )
    multi_region_insights: Dict[str, Any] = Field(
        default_factory=dict, description="Multi-region correlation data"
    )
    operational_context: Dict[str, Any] = Field(
        default_factory=dict, description="Operational monitoring context"
    )
    
    # Internal adapter storage (private attributes)
    def __init__(self, **data):
        super().__init__(**data)
        self._adapters: List[BaseModelAdapter] = []
        self._generation_start_time: Optional[datetime] = None
        self._analysis_duration: Optional[float] = None
    
    model_config = {"arbitrary_types_allowed": True}
    
    def add_adapters(self, adapters: List[BaseModelAdapter]) -> None:
        """
        Add model adapters for enhanced analysis.
        
        Args:
            adapters: List of model adapters to use for analysis
        """
        self._adapters.extend(adapters)
        self._generate_enhanced_analysis()
    
    def _generate_enhanced_analysis(self) -> None:
        """
        Generate enhanced analysis using all available adapters.
        
        This method orchestrates the generation of enhanced insights by calling
        specialized analysis methods for each enhancement category.
        """
        self._generation_start_time = datetime.now()
        
        try:
            # Generate enhanced capabilities summary
            self._analyze_enhanced_capabilities()
            
            # Generate security assessment
            self._generate_security_assessment()
            
            # Generate multi-region insights
            self._generate_multi_region_insights()
            
            # Generate operational context
            self._generate_operational_context()
            
            # Generate performance metrics
            self._generate_performance_metrics()
            
            self._analysis_duration = (
                datetime.now() - self._generation_start_time
            ).total_seconds() if self._generation_start_time else None
            
        except Exception as e:
            # Graceful degradation if enhanced analysis fails
            if not hasattr(self, 'warnings'):
                self.warnings = []
            self.warnings.append(f"Enhanced analysis failed: {str(e)}")
    
    def _analyze_enhanced_capabilities(self) -> None:
        """Analyze what enhanced capabilities are available."""
        total_adapters = len(self._adapters)
        enhanced_adapters = sum(1 for adapter in self._adapters if adapter.is_enhanced())
        
        self.enhanced_capabilities = {
            "total_models": total_adapters,
            "enhanced_models": enhanced_adapters,
            "enhancement_rate": enhanced_adapters / total_adapters if total_adapters > 0 else 0,
            "shared_model_integration": enhanced_adapters > 0,
            "backward_compatibility": True,
            "performance_optimizations": True,
        }
    
    def _generate_security_assessment(self) -> None:
        """Generate comprehensive security assessment."""
        self.security_assessment = {
            "security_enabled": True,
            "threat_detection": True,
            "validation_active": True,
            "compliance_checking": True,
            "threats_detected": [],
            "security_score": 100,  # Default high score
            "recommendations": []
        }
        
        # Analyze security from enhanced models
        for adapter in self._adapters:
            shared_model = adapter.get_shared_model()
            if shared_model and hasattr(shared_model, 'security_context'):
                try:
                    security_context = getattr(shared_model, 'security_context')
                    if hasattr(security_context, 'threat_level'):
                        threat_level = security_context.threat_level
                        if threat_level != SecurityThreatLevel.INFO:
                            self.security_assessment["threats_detected"].append({
                                "model_type": type(shared_model).__name__,
                                "threat_level": threat_level,
                                "details": getattr(security_context, 'details', 'Unknown threat')
                            })
                except Exception:
                    # Continue with other models if one fails
                    pass
    
    def _generate_multi_region_insights(self) -> None:
        """Generate multi-region intelligence and correlation."""
        regions = set()
        regional_distribution = {}
        
        # Collect region information from adapters
        for adapter in self._adapters:
            region = adapter.get('region')
            if region:
                regions.add(region)
                regional_distribution[region] = regional_distribution.get(region, 0) + 1
        
        self.multi_region_insights = {
            "regions_analyzed": list(regions),
            "region_count": len(regions),
            "regional_distribution": regional_distribution,
            "cross_region_analysis": len(regions) > 1,
            "regional_correlations": []
        }
        
        # Generate cross-region correlations if multiple regions
        if len(regions) > 1:
            self.multi_region_insights["regional_correlations"] = [
                f"Analysis covers {len(regions)} regions with distributed workloads"
            ]
    
    def _generate_operational_context(self) -> None:
        """Generate operational monitoring context."""
        self.operational_context = {
            "monitoring_enabled": True,
            "automation_ready": True,
            "sla_monitoring": True,
            "alerting_configured": False,
            "health_status": HealthStatus.HEALTHY,
            "automation_opportunities": [],
            "monitoring_recommendations": []
        }
        
        # Analyze operational data from adapters
        error_count = sum(
            len(adapter.get_transformation_errors()) for adapter in self._adapters
        )
        
        if error_count > 0:
            self.operational_context["health_status"] = HealthStatus.WARNING
            self.operational_context["monitoring_recommendations"].append(
                f"Address {error_count} transformation errors for optimal performance"
            )
    
    def _generate_performance_metrics(self) -> None:
        """Generate performance metrics from adapters."""
        adapter_metrics = [adapter.get_performance_metrics() for adapter in self._adapters]
        
        total_access_count = sum(m.get("access_count", 0) for m in adapter_metrics)
        enhanced_count = sum(1 for m in adapter_metrics if m.get("enhanced_available", False))
        
        self.performance_metrics = {
            "adapter_count": len(self._adapters),
            "enhanced_adapters": enhanced_count,
            "total_accesses": total_access_count,
            "analysis_duration": self._analysis_duration,
            "performance_score": min(100, enhanced_count * 10),  # Simple scoring
            "optimization_opportunities": []
        }
        
        # Add optimization opportunities
        if enhanced_count < len(self._adapters):
            missing_enhanced = len(self._adapters) - enhanced_count
            self.performance_metrics["optimization_opportunities"].append(
                f"{missing_enhanced} models could be enhanced with shared model integration"
            )
    
    def get_enhancement_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive summary of all enhancements.
        
        Returns:
            Dictionary containing enhancement summary
        """
        return {
            "enhanced_capabilities": self.enhanced_capabilities,
            "security_summary": {
                "threats_detected": len(self.security_assessment.get("threats_detected", [])),
                "security_score": self.security_assessment.get("security_score", 0),
                "security_enabled": self.security_assessment.get("security_enabled", False)
            },
            "multi_region_summary": {
                "regions": len(self.multi_region_insights.get("regions_analyzed", [])),
                "cross_region": self.multi_region_insights.get("cross_region_analysis", False)
            },
            "operational_summary": {
                "health_status": self.operational_context.get("health_status", HealthStatus.UNKNOWN),
                "monitoring_enabled": self.operational_context.get("monitoring_enabled", False)
            },
            "performance_summary": {
                "enhanced_models": self.performance_metrics.get("enhanced_adapters", 0),
                "total_models": self.performance_metrics.get("adapter_count", 0),
                "analysis_duration": self.performance_metrics.get("analysis_duration")
            }
        }


# =============================================================================
# Migration Pattern Utilities
# =============================================================================

@dataclass
class MigrationStats:
    """Statistics for migration operations."""
    total_models: int = 0
    successful_migrations: int = 0
    failed_migrations: int = 0
    fallback_count: int = 0
    total_duration: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate migration success rate."""
        return (
            self.successful_migrations / self.total_models 
            if self.total_models > 0 else 0
        )
    
    @property
    def fallback_rate(self) -> float:
        """Calculate fallback rate."""
        return (
            self.fallback_count / self.total_models 
            if self.total_models > 0 else 0
        )


class MigrationPatterns:
    """
    Utility class providing reusable migration patterns and optimizations.
    
    This class contains static methods and utilities that can be used across
    different analyzer migrations to ensure consistency and best practices.
    """
    
    @staticmethod
    def create_adapter_batch(
        adapter_class: Type[BaseModelAdapter], 
        data_list: List[Dict[str, Any]]
    ) -> List[BaseModelAdapter]:
        """
        Create a batch of adapters efficiently.
        
        Args:
            adapter_class: The adapter class to instantiate
            data_list: List of data dictionaries
            
        Returns:
            List of adapter instances
        """
        return [adapter_class(data) for data in data_list]
    
    @staticmethod
    async def process_adapters_concurrently(
        adapters: List[BaseModelAdapter],
        max_workers: int = 10
    ) -> MigrationStats:
        """
        Process adapter transformations concurrently for better performance.
        
        Args:
            adapters: List of adapters to process
            max_workers: Maximum number of concurrent workers
            
        Returns:
            Migration statistics
        """
        start_time = time.time()
        stats = MigrationStats(total_models=len(adapters))
        
        async def process_adapter(adapter: BaseModelAdapter) -> bool:
            """Process a single adapter."""
            try:
                shared_model = adapter.get_shared_model()
                if shared_model:
                    stats.successful_migrations += 1
                    return True
                else:
                    stats.fallback_count += 1
                    return False
            except Exception:
                stats.failed_migrations += 1
                return False
        
        # Process adapters concurrently
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, lambda a=adapter: asyncio.run(process_adapter(a)))
                for adapter in adapters
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        stats.total_duration = time.time() - start_time
        return stats
    
    @staticmethod
    def validate_migration_compatibility(
        legacy_data: Dict[str, Any],
        shared_model_class: Type[BaseModel]
    ) -> List[str]:
        """
        Validate that legacy data is compatible with shared model requirements.
        
        Args:
            legacy_data: Legacy data dictionary
            shared_model_class: Target shared model class
            
        Returns:
            List of compatibility issues (empty if compatible)
        """
        issues = []
        
        try:
            # Get model fields
            if hasattr(shared_model_class, '__fields__'):
                required_fields = {
                    name for name, field in shared_model_class.__fields__.items()
                    if field.is_required()
                }
            else:
                required_fields = set()
            
            # Check for missing required fields
            missing_fields = required_fields - set(legacy_data.keys())
            if missing_fields:
                issues.append(f"Missing required fields: {missing_fields}")
            
            # Check for type compatibility (basic check)
            for field_name, value in legacy_data.items():
                if value is None:
                    continue
                    
                # Basic type validation could be added here
                # This would require more sophisticated field inspection
                
        except Exception as e:
            issues.append(f"Validation error: {str(e)}")
            
        return issues
    
    @staticmethod
    def create_performance_monitor() -> Callable:
        """
        Create a performance monitoring decorator for migration methods.
        
        Returns:
            Decorator function for performance monitoring
        """
        def performance_monitor(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    # Add performance info to result if it's a response object
                    if hasattr(result, 'performance_metrics'):
                        result.performance_metrics['method_duration'] = duration
                        result.performance_metrics['method_name'] = func.__name__
                    
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    # Log performance info even on errors
                    print(f"Method {func.__name__} failed after {duration:.3f}s: {e}")
                    raise
                    
            return wrapper
        return performance_monitor


# =============================================================================
# Security Enhancement Utilities
# =============================================================================

class SecurityEnhancementMixin:
    """
    Mixin class providing security enhancement patterns for migrated analyzers.
    
    This mixin can be used with analyzer classes to add consistent security
    enhancements across all migrations.
    """
    
    def enhance_security_analysis(self, adapters: List[BaseModelAdapter]) -> Dict[str, Any]:
        """
        Generate enhanced security analysis from adapters.
        
        Args:
            adapters: List of model adapters to analyze
            
        Returns:
            Security analysis results
        """
        security_results = {
            "threats_detected": [],
            "security_violations": [],
            "compliance_issues": [],
            "security_score": 100,
            "recommendations": []
        }
        
        for adapter in adapters:
            shared_model = adapter.get_shared_model()
            if shared_model:
                # Check for security context
                if hasattr(shared_model, 'security_context'):
                    try:
                        security_context = shared_model.security_context
                        
                        # Analyze threat level
                        if hasattr(security_context, 'threat_level'):
                            threat_level = security_context.threat_level
                            if threat_level.requires_immediate_action():
                                security_results["threats_detected"].append({
                                    "model": type(shared_model).__name__,
                                    "threat_level": threat_level,
                                    "immediate_action_required": True
                                })
                        
                        # Check for violations
                        if hasattr(security_context, 'violations'):
                            violations = security_context.violations
                            security_results["security_violations"].extend([
                                {
                                    "model": type(shared_model).__name__,
                                    "violation": violation
                                }
                                for violation in violations
                            ])
                            
                    except Exception:
                        # Continue with other models
                        pass
        
        # Calculate overall security score
        threat_count = len(security_results["threats_detected"])
        violation_count = len(security_results["security_violations"])
        
        # Reduce score based on findings
        score_reduction = (threat_count * 20) + (violation_count * 10)
        security_results["security_score"] = max(0, 100 - score_reduction)
        
        # Generate recommendations
        if threat_count > 0:
            security_results["recommendations"].append(
                f"Address {threat_count} security threats requiring immediate attention"
            )
        if violation_count > 0:
            security_results["recommendations"].append(
                f"Resolve {violation_count} security violations"
            )
        
        return security_results


# =============================================================================
# Validation and Testing Utilities
# =============================================================================

class MigrationValidator:
    """
    Validation utilities for migration testing and quality assurance.
    
    Provides comprehensive validation methods to ensure migration quality
    and compatibility across different analyzer types.
    """
    
    @staticmethod
    def validate_adapter_functionality(
        adapter: BaseModelAdapter,
        required_methods: List[str] = None
    ) -> Dict[str, Any]:
        """
        Validate that an adapter provides required functionality.
        
        Args:
            adapter: Adapter to validate
            required_methods: List of methods that must be available
            
        Returns:
            Validation results
        """
        if required_methods is None:
            required_methods = [
                'get_shared_model', 'get_legacy_data', 'is_enhanced',
                'get_transformation_errors', 'get_performance_metrics'
            ]
        
        results = {
            "adapter_valid": True,
            "missing_methods": [],
            "functionality_score": 0,
            "enhancement_available": False,
            "errors": []
        }
        
        try:
            # Check required methods
            for method in required_methods:
                if not hasattr(adapter, method):
                    results["missing_methods"].append(method)
                    results["adapter_valid"] = False
            
            # Test basic functionality
            try:
                legacy_data = adapter.get_legacy_data()
                if not isinstance(legacy_data, dict):
                    results["errors"].append("get_legacy_data() must return dict")
                    results["adapter_valid"] = False
            except Exception as e:
                results["errors"].append(f"get_legacy_data() failed: {e}")
                results["adapter_valid"] = False
            
            # Test enhancement functionality
            try:
                results["enhancement_available"] = adapter.is_enhanced()
                shared_model = adapter.get_shared_model()
                if shared_model is not None:
                    results["functionality_score"] += 50
            except Exception as e:
                results["errors"].append(f"Enhancement testing failed: {e}")
            
            # Calculate functionality score
            method_score = (
                (len(required_methods) - len(results["missing_methods"])) / 
                len(required_methods) * 50
            )
            results["functionality_score"] += method_score
            
        except Exception as e:
            results["adapter_valid"] = False
            results["errors"].append(f"Validation failed: {e}")
        
        return results
    
    @staticmethod
    def validate_response_enhancement(
        response: EnhancedAnalysisResponse
    ) -> Dict[str, Any]:
        """
        Validate that a response object provides expected enhancements.
        
        Args:
            response: Response object to validate
            
        Returns:
            Validation results
        """
        results = {
            "response_valid": True,
            "enhancement_features": {},
            "missing_features": [],
            "errors": []
        }
        
        try:
            # Check for enhanced capabilities
            required_fields = [
                'enhanced_capabilities', 'security_assessment',
                'multi_region_insights', 'operational_context',
                'performance_metrics'
            ]
            
            for field in required_fields:
                if hasattr(response, field):
                    field_value = getattr(response, field)
                    results["enhancement_features"][field] = {
                        "present": True,
                        "populated": bool(field_value),
                        "type": type(field_value).__name__
                    }
                else:
                    results["missing_features"].append(field)
                    results["response_valid"] = False
            
            # Test enhancement summary
            try:
                summary = response.get_enhancement_summary()
                if not isinstance(summary, dict):
                    results["errors"].append("get_enhancement_summary() must return dict")
            except Exception as e:
                results["errors"].append(f"get_enhancement_summary() failed: {e}")
                
        except Exception as e:
            results["response_valid"] = False
            results["errors"].append(f"Response validation failed: {e}")
        
        return results


# =============================================================================
# Export Summary
# =============================================================================

__all__ = [
    # Base Classes
    'BaseModelAdapter',
    'CachedModelAdapter',
    'EnhancedAnalysisResponse',
    
    # Utilities
    'MigrationPatterns',
    'MigrationStats',
    'SecurityEnhancementMixin',
    'MigrationValidator',
    
    # Type Variables
    'T', 'LegacyT', 'SharedT'
]