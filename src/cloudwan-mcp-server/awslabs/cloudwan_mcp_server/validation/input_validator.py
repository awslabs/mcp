"""
Production-grade input validation with performance optimization
"""

import re
import ipaddress
from typing import Any, Dict, List, Optional, Union, Callable
from functools import lru_cache
from pydantic import BaseModel, Field, validator
from enum import Enum
import json


class ValidationSeverity(Enum):
    """Validation severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationResult(BaseModel):
    """Validation result with performance metrics"""

    is_valid: bool = True
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validation_time_ms: float = 0.0
    field_results: Dict[str, bool] = Field(default_factory=dict)


class OptimizedInputValidator:
    """High-performance input validator with caching and batch processing"""

    def __init__(self):
        self._compiled_patterns = self._precompile_patterns()
        self._validation_cache = {}

    @lru_cache(maxsize=1000)
    def _precompile_patterns(self) -> Dict[str, re.Pattern]:
        """Pre-compile regex patterns for performance"""
        return {
            "aws_region": re.compile(r"^[a-z0-9\-]{2,20}$"),
            "aws_account": re.compile(r"^\d{12}$"),
            "resource_id": re.compile(r"^[a-zA-Z0-9\-_]{1,64}$"),
            "core_network_id": re.compile(r"^core-network-[a-f0-9]{17}$"),
            "transit_gateway_id": re.compile(r"^tgw-[a-f0-9]{17}$"),
            "attachment_id": re.compile(r"^tgw-attach-[a-f0-9]{17}$"),
            "route_table_id": re.compile(r"^tgw-rtb-[a-f0-9]{17}$"),
            "policy_version_id": re.compile(r"^\d+$"),
            "cidr_block": re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2}$"),
        }

    @lru_cache(maxsize=500)
    def validate_ip_address(self, ip: str) -> ValidationResult:
        """Cached IP address validation with detailed analysis"""
        import time

        start_time = time.perf_counter()

        result = ValidationResult()

        try:
            ip_obj = ipaddress.ip_address(ip)
            result.field_results["ip_format"] = True
            result.field_results["ip_version"] = True

            # Performance optimized checks
            if ip_obj.is_private:
                result.warnings.append(f"IP {ip} is in private address space")
            if ip_obj.is_loopback:
                result.warnings.append(f"IP {ip} is loopback address")
            if ip_obj.is_multicast:
                result.warnings.append(f"IP {ip} is multicast address")

        except ValueError as e:
            result.is_valid = False
            result.errors.append(f"Invalid IP address format: {ip}")
            result.field_results["ip_format"] = False

        result.validation_time_ms = (time.perf_counter() - start_time) * 1000
        return result

    @lru_cache(maxsize=300)
    def validate_cidr_block(self, cidr: str) -> ValidationResult:
        """Optimized CIDR validation with network analysis"""
        import time

        start_time = time.perf_counter()

        result = ValidationResult()

        try:
            network = ipaddress.ip_network(cidr, strict=False)
            result.field_results["cidr_format"] = True

            # Performance checks
            if network.num_addresses > 16777216:  # /8 or larger
                result.warnings.append(f"Very large network block: {cidr}")
            if network.prefixlen < 8:
                result.warnings.append(f"Unusually large prefix length: /{network.prefixlen}")
            if network.is_private:
                result.field_results["is_private"] = True
            if network.overlaps(ipaddress.ip_network("0.0.0.0/0")):
                result.field_results["is_global"] = True

        except ValueError:
            result.is_valid = False
            result.errors.append(f"Invalid CIDR format: {cidr}")
            result.field_results["cidr_format"] = False

        result.validation_time_ms = (time.perf_counter() - start_time) * 1000
        return result

    def validate_aws_resource_id(self, resource_id: str, resource_type: str) -> ValidationResult:
        """Fast AWS resource ID validation using pre-compiled patterns"""
        import time

        start_time = time.perf_counter()

        result = ValidationResult()

        pattern = self._compiled_patterns.get(resource_type)
        if not pattern:
            result.warnings.append(f"Unknown resource type: {resource_type}")
            result.field_results["pattern_available"] = False
            return result

        if pattern.match(resource_id):
            result.field_results["format_valid"] = True
        else:
            result.is_valid = False
            result.errors.append(f"Invalid {resource_type} format: {resource_id}")
            result.field_results["format_valid"] = False

        result.validation_time_ms = (time.perf_counter() - start_time) * 1000
        return result

    def batch_validate(self, validation_tasks: List[Dict[str, Any]]) -> Dict[str, ValidationResult]:
        """Batch validation for improved performance"""
        import time

        start_time = time.perf_counter()

        results = {}

        # Group by validation type for optimized processing
        ip_tasks = []
        cidr_tasks = []
        resource_tasks = []

        for task in validation_tasks:
            task_type = task.get("type")
            if task_type == "ip":
                ip_tasks.append(task)
            elif task_type == "cidr":
                cidr_tasks.append(task)
            elif task_type == "resource":
                resource_tasks.append(task)

        # Process in batches
        for task in ip_tasks:
            results[task["key"]] = self.validate_ip_address(task["value"])

        for task in cidr_tasks:
            results[task["key"]] = self.validate_cidr_block(task["value"])

        for task in resource_tasks:
            results[task["key"]] = self.validate_aws_resource_id(
                task["value"], task.get("resource_type", "resource_id")
            )

        total_time = (time.perf_counter() - start_time) * 1000

        # Add batch performance summary
        batch_summary = ValidationResult()
        batch_summary.validation_time_ms = total_time
        batch_summary.field_results["batch_size"] = len(validation_tasks)
        batch_summary.field_results["avg_time_per_validation"] = (
            total_time / len(validation_tasks) if validation_tasks else 0
        )
        results["_batch_summary"] = batch_summary

        return results

    def validate_json_policy(self, policy_data: Union[str, Dict]) -> ValidationResult:
        """High-performance policy document validation"""
        import time

        start_time = time.perf_counter()

        result = ValidationResult()

        try:
            if isinstance(policy_data, str):
                policy_dict = json.loads(policy_data)
            else:
                policy_dict = policy_data

            result.field_results["json_valid"] = True

            # Required fields validation
            required_fields = ["version", "core-network-configuration"]
            for field in required_fields:
                if field in policy_dict:
                    result.field_results[f"has_{field}"] = True
                else:
                    result.is_valid = False
                    result.errors.append(f"Missing required field: {field}")
                    result.field_results[f"has_{field}"] = False

            # Version validation
            version = policy_dict.get("version")
            if version and version not in ["2021.12", "2022.02"]:
                result.warnings.append(f"Potentially unsupported policy version: {version}")

        except json.JSONDecodeError as e:
            result.is_valid = False
            result.errors.append(f"Invalid JSON format: {str(e)}")
            result.field_results["json_valid"] = False

        result.validation_time_ms = (time.perf_counter() - start_time) * 1000
        return result

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get validation cache performance statistics"""
        ip_cache_info = self.validate_ip_address.cache_info()
        cidr_cache_info = self.validate_cidr_block.cache_info()

        return {
            "ip_validation_cache": {
                "hits": ip_cache_info.hits,
                "misses": ip_cache_info.misses,
                "hit_rate": ip_cache_info.hits / (ip_cache_info.hits + ip_cache_info.misses)
                if ip_cache_info.hits + ip_cache_info.misses > 0
                else 0,
            },
            "cidr_validation_cache": {
                "hits": cidr_cache_info.hits,
                "misses": cidr_cache_info.misses,
                "hit_rate": cidr_cache_info.hits / (cidr_cache_info.hits + cidr_cache_info.misses)
                if cidr_cache_info.hits + cidr_cache_info.misses > 0
                else 0,
            },
            "total_cache_size": ip_cache_info.currsize + cidr_cache_info.currsize,
        }


# Global validator instance for optimal performance
validator_instance = OptimizedInputValidator()
