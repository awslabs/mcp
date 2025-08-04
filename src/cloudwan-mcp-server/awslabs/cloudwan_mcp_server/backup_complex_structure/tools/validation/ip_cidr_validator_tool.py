"""
Comprehensive IP/CIDR Validation and Networking Utilities Tool for CloudWAN MCP Server.

This module provides comprehensive IPv4 and IPv6 networking utilities including:
- IP address validation and format conversion
- CIDR block validation and calculations  
- Subnet calculations and network range analysis
- Network overlap detection and subnet planning
- Automation-friendly JSON output for integration
"""

import ipaddress
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from ...config import CloudWANConfig
from ..base import BaseMCPTool, ValidationError, handle_errors

logger = logging.getLogger(__name__)


class NetworkCalculator:
    """Core networking calculation engine for IPv4/IPv6 operations."""
    
    @staticmethod
    def validate_ip(ip_str: str) -> Dict[str, Any]:
        """Validate IP address and return detailed information."""
        try:
            ip = ipaddress.ip_address(ip_str)
            return {
                "valid": True,
                "version": ip.version,
                "type": "ipv4" if ip.version == 4 else "ipv6",
                "compressed": str(ip.compressed),
                "exploded": str(ip.exploded),
                "packed": ip.packed.hex(),
                "is_private": ip.is_private,
                "is_global": ip.is_global,
                "is_multicast": ip.is_multicast,
                "is_reserved": ip.is_reserved,
                "is_loopback": ip.is_loopback,
                "is_link_local": ip.is_link_local,
                "max_prefixlen": ip.max_prefixlen
            }
        except ValueError as e:
            return {
                "valid": False,
                "error": str(e),
                "input": ip_str
            }
    
    @staticmethod
    def validate_cidr(cidr_str: str) -> Dict[str, Any]:
        """Validate CIDR block and return network information."""
        try:
            network = ipaddress.ip_network(cidr_str, strict=False)
            return {
                "valid": True,
                "version": network.version,
                "type": "ipv4" if network.version == 4 else "ipv6",
                "network_address": str(network.network_address),
                "broadcast_address": str(network.broadcast_address) if network.version == 4 else None,
                "netmask": str(network.netmask),
                "hostmask": str(network.hostmask),
                "prefix_length": network.prefixlen,
                "num_addresses": network.num_addresses,
                "is_private": network.is_private,
                "is_global": network.is_global,
                "is_multicast": network.is_multicast,
                "is_reserved": network.is_reserved,
                "is_link_local": network.is_link_local,
                "supernet_of": network.supernet().with_prefixlen if network.prefixlen > 0 else None,
                "subnets": {
                    "possible_subnets": network.prefixlen < network.max_prefixlen,
                    "max_prefixlen": network.max_prefixlen,
                    "current_prefixlen": network.prefixlen
                }
            }
        except ValueError as e:
            return {
                "valid": False,
                "error": str(e),
                "input": cidr_str
            }
    
    @staticmethod
    def calculate_subnet_info(cidr_str: str, target_hosts: Optional[int] = None, 
                            target_subnets: Optional[int] = None) -> Dict[str, Any]:
        """Calculate subnet information and planning."""
        try:
            network = ipaddress.ip_network(cidr_str, strict=False)
            result = {
                "original_network": str(network),
                "available_addresses": network.num_addresses,
                "usable_addresses": network.num_addresses - 2 if network.version == 4 and network.prefixlen < 31 else network.num_addresses,
                "subnet_calculations": {}
            }
            
            if target_hosts:
                # Calculate minimum prefix length for target hosts
                if network.version == 4:
                    # IPv4: need +2 for network and broadcast
                    required_addresses = target_hosts + 2
                else:
                    # IPv6: no broadcast address
                    required_addresses = target_hosts
                
                import math
                required_bits = math.ceil(math.log2(required_addresses))
                min_prefix = network.max_prefixlen - required_bits
                
                if min_prefix >= network.prefixlen:
                    result["subnet_calculations"]["target_hosts"] = {
                        "requested_hosts": target_hosts,
                        "required_prefix_length": max(min_prefix, 0),
                        "actual_hosts_per_subnet": 2 ** (network.max_prefixlen - max(min_prefix, 0)) - (2 if network.version == 4 else 0),
                        "possible": min_prefix >= 0
                    }
                else:
                    result["subnet_calculations"]["target_hosts"] = {
                        "requested_hosts": target_hosts,
                        "error": "Requested host count exceeds network capacity",
                        "possible": False
                    }
            
            if target_subnets:
                # Calculate prefix length for target number of subnets
                import math
                required_bits = math.ceil(math.log2(target_subnets))
                new_prefix = network.prefixlen + required_bits
                
                if new_prefix <= network.max_prefixlen:
                    subnet_size = 2 ** (network.max_prefixlen - new_prefix)
                    result["subnet_calculations"]["target_subnets"] = {
                        "requested_subnets": target_subnets,
                        "new_prefix_length": new_prefix,
                        "actual_subnets": 2 ** required_bits,
                        "hosts_per_subnet": subnet_size - (2 if network.version == 4 and new_prefix < 31 else 0),
                        "possible": True
                    }
                else:
                    result["subnet_calculations"]["target_subnets"] = {
                        "requested_subnets": target_subnets,
                        "error": "Requested subnet count exceeds network capacity",
                        "possible": False
                    }
            
            return result
            
        except ValueError as e:
            return {
                "valid": False,
                "error": str(e),
                "input": cidr_str
            }
    
    @staticmethod
    def generate_subnets(cidr_str: str, new_prefix: int, max_subnets: int = 256) -> Dict[str, Any]:
        """Generate subnet list with specified prefix length."""
        try:
            network = ipaddress.ip_network(cidr_str, strict=False)
            
            if new_prefix <= network.prefixlen:
                return {
                    "error": "New prefix length must be greater than current prefix length",
                    "current_prefix": network.prefixlen,
                    "requested_prefix": new_prefix
                }
            
            if new_prefix > network.max_prefixlen:
                return {
                    "error": "New prefix length exceeds maximum for IP version",
                    "max_prefix": network.max_prefixlen,
                    "requested_prefix": new_prefix
                }
            
            subnets = list(network.subnets(new_prefix=new_prefix))
            if len(subnets) > max_subnets:
                subnets = subnets[:max_subnets]
                truncated = True
            else:
                truncated = False
            
            result = {
                "parent_network": str(network),
                "new_prefix_length": new_prefix,
                "total_possible_subnets": 2 ** (new_prefix - network.prefixlen),
                "subnets_returned": len(subnets),
                "truncated": truncated,
                "subnets": []
            }
            
            for subnet in subnets:
                subnet_info = {
                    "network": str(subnet),
                    "network_address": str(subnet.network_address),
                    "broadcast_address": str(subnet.broadcast_address) if subnet.version == 4 else None,
                    "first_host": str(subnet.network_address + 1) if subnet.num_addresses > 2 else str(subnet.network_address),
                    "last_host": str(subnet.broadcast_address - 1) if subnet.version == 4 and subnet.num_addresses > 2 else str(subnet.broadcast_address) if subnet.version == 4 else str(subnet.network_address + subnet.num_addresses - 1),
                    "num_addresses": subnet.num_addresses,
                    "usable_hosts": subnet.num_addresses - 2 if subnet.version == 4 and subnet.prefixlen < 31 else subnet.num_addresses
                }
                result["subnets"].append(subnet_info)
            
            return result
            
        except ValueError as e:
            return {
                "valid": False,
                "error": str(e),
                "input": cidr_str
            }
    
    @staticmethod
    def check_overlap(networks: List[str]) -> Dict[str, Any]:
        """Check for overlapping networks."""
        try:
            network_objects = []
            for net_str in networks:
                try:
                    net = ipaddress.ip_network(net_str, strict=False)
                    network_objects.append((net_str, net))
                except ValueError as e:
                    return {
                        "error": f"Invalid network: {net_str} - {str(e)}",
                        "input_networks": networks
                    }
            
            overlaps = []
            contained = []
            adjacent = []
            
            for i, (str1, net1) in enumerate(network_objects):
                for j, (str2, net2) in enumerate(network_objects[i+1:], i+1):
                    if net1.overlaps(net2):
                        if net1.subnet_of(net2):
                            contained.append({
                                "contained": str1,
                                "container": str2,
                                "relationship": f"{str1} is a subnet of {str2}"
                            })
                        elif net2.subnet_of(net1):
                            contained.append({
                                "contained": str2,
                                "container": str1,
                                "relationship": f"{str2} is a subnet of {str1}"
                            })
                        else:
                            overlaps.append({
                                "network1": str1,
                                "network2": str2,
                                "relationship": "partial overlap"
                            })
                    
                    # Check adjacency
                    try:
                        if net1.supernet() == net2.supernet():
                            # They could be adjacent subnets
                            if (net1.network_address + net1.num_addresses == net2.network_address or
                                net2.network_address + net2.num_addresses == net1.network_address):
                                adjacent.append({
                                    "network1": str1,
                                    "network2": str2,
                                    "relationship": "adjacent subnets"
                                })
                    except:
                        pass
            
            return {
                "total_networks": len(networks),
                "valid_networks": len(network_objects),
                "has_overlaps": len(overlaps) > 0,
                "has_containment": len(contained) > 0,
                "has_adjacent": len(adjacent) > 0,
                "overlapping_pairs": overlaps,
                "containment_relationships": contained,
                "adjacent_pairs": adjacent
            }
            
        except Exception as e:
            return {
                "error": f"Network overlap analysis failed: {str(e)}",
                "input_networks": networks
            }
    
    @staticmethod
    def ip_range_to_cidrs(start_ip: str, end_ip: str) -> Dict[str, Any]:
        """Convert IP range to minimal set of CIDR blocks."""
        try:
            start = ipaddress.ip_address(start_ip)
            end = ipaddress.ip_address(end_ip)
            
            if start.version != end.version:
                return {
                    "error": "Start and end IP must be the same version",
                    "start_ip": start_ip,
                    "end_ip": end_ip
                }
            
            if start > end:
                return {
                    "error": "Start IP must be less than or equal to end IP",
                    "start_ip": start_ip,
                    "end_ip": end_ip
                }
            
            # Use ipaddress library's summarize_address_range
            cidrs = list(ipaddress.summarize_address_range(start, end))
            
            return {
                "start_ip": start_ip,
                "end_ip": end_ip,
                "ip_version": start.version,
                "total_addresses": int(end) - int(start) + 1,
                "cidr_blocks": [str(cidr) for cidr in cidrs],
                "cidr_count": len(cidrs),
                "efficiency": f"{len(cidrs)} CIDR blocks for {int(end) - int(start) + 1} addresses"
            }
            
        except ValueError as e:
            return {
                "error": str(e),
                "start_ip": start_ip,
                "end_ip": end_ip
            }
    
    @staticmethod
    def cidr_to_ip_range(cidr_str: str) -> Dict[str, Any]:
        """Convert CIDR block to IP range."""
        try:
            network = ipaddress.ip_network(cidr_str, strict=False)
            
            return {
                "cidr": str(network),
                "ip_version": network.version,
                "network_address": str(network.network_address),
                "broadcast_address": str(network.broadcast_address) if network.version == 4 else str(network.network_address + network.num_addresses - 1),
                "first_ip": str(network.network_address),
                "last_ip": str(network.broadcast_address) if network.version == 4 else str(network.network_address + network.num_addresses - 1),
                "first_host": str(network.network_address + 1) if network.num_addresses > 2 else str(network.network_address),
                "last_host": str(network.broadcast_address - 1) if network.version == 4 and network.num_addresses > 2 else str(network.broadcast_address) if network.version == 4 else str(network.network_address + network.num_addresses - 1),
                "total_addresses": network.num_addresses,
                "usable_addresses": network.num_addresses - 2 if network.version == 4 and network.prefixlen < 31 else network.num_addresses
            }
            
        except ValueError as e:
            return {
                "error": str(e),
                "input": cidr_str
            }


class IPCIDRValidatorTool(BaseMCPTool):
    """Comprehensive IP/CIDR validation and networking utilities tool."""
    
    def __init__(self, config: CloudWANConfig):
        # This tool doesn't require AWS manager
        super().__init__(None, config)
        self.calculator = NetworkCalculator()
        self._load_time = 0.0
        self._start_time = time.time()
        self._load_time = time.time() - self._start_time
        logger.info(f"IP/CIDR Validator Tool initialized in {self._load_time:.3f}s")
    
    @property
    def tool_name(self) -> str:
        """Tool name for MCP registration."""
        return "validate_ip_cidr"
    
    @property
    def description(self) -> str:
        """Tool description for MCP registration."""
        return ("Comprehensive IP/CIDR validation and networking utilities including "
                "subnet calculation, CIDR conversion, IP range calculation, validation, "
                "and automation-friendly output")
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        """Input schema definition."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [
                        "validate_ip", "validate_cidr", "calculate_subnets", 
                        "generate_subnets", "check_overlap", "ip_range_to_cidrs",
                        "cidr_to_ip_range", "comprehensive_analysis"
                    ],
                    "description": "Type of networking operation to perform"
                },
                "ip": {
                    "type": "string",
                    "description": "IP address for validation (IPv4 or IPv6)"
                },
                "cidr": {
                    "type": "string", 
                    "description": "CIDR block for validation/analysis"
                },
                "networks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of networks for overlap analysis"
                },
                "start_ip": {
                    "type": "string",
                    "description": "Start IP address for range operations"
                },
                "end_ip": {
                    "type": "string", 
                    "description": "End IP address for range operations"
                },
                "target_hosts": {
                    "type": "integer",
                    "description": "Target number of hosts per subnet"
                },
                "target_subnets": {
                    "type": "integer",
                    "description": "Target number of subnets"
                },
                "new_prefix": {
                    "type": "integer",
                    "description": "New prefix length for subnet generation"
                },
                "max_subnets": {
                    "type": "integer",
                    "default": 256,
                    "description": "Maximum number of subnets to return"
                }
            },
            "required": ["operation"],
            "additionalProperties": False
        }
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        """Output schema definition."""
        return {
            "type": "object",
            "properties": {
                "operation": {"type": "string"},
                "timestamp": {"type": "string", "format": "date-time"},
                "success": {"type": "boolean"},
                "result": {"type": "object"},
                "error": {"type": "string"},
                "metadata": {
                    "type": "object",
                    "properties": {
                        "execution_time_ms": {"type": "number"},
                        "tool_version": {"type": "string"}
                    }
                }
            },
            "required": ["operation", "timestamp", "success"]
        }

    @handle_errors
    async def execute(self, arguments: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Execute IP/CIDR validation and networking operations with MCP-compliant signature."""
        # Combine arguments dict with legacy kwargs for compatibility
        if arguments:
            kwargs.update(arguments)
        start_time = time.time()
        operation = kwargs.get("operation")
        
        if not operation:
            raise ValidationError("Operation is required")
        
        try:
            result = None
            
            if operation == "validate_ip":
                ip = kwargs.get("ip")
                if not ip:
                    raise ValidationError("IP address is required for validate_ip operation")
                result = self.calculator.validate_ip(ip)
                
            elif operation == "validate_cidr":
                cidr = kwargs.get("cidr")
                if not cidr:
                    raise ValidationError("CIDR block is required for validate_cidr operation")
                result = self.calculator.validate_cidr(cidr)
                
            elif operation == "calculate_subnets":
                cidr = kwargs.get("cidr")
                if not cidr:
                    raise ValidationError("CIDR block is required for calculate_subnets operation")
                target_hosts = kwargs.get("target_hosts")
                target_subnets = kwargs.get("target_subnets")
                result = self.calculator.calculate_subnet_info(cidr, target_hosts, target_subnets)
                
            elif operation == "generate_subnets":
                cidr = kwargs.get("cidr")
                new_prefix = kwargs.get("new_prefix")
                if not cidr or new_prefix is None:
                    raise ValidationError("CIDR block and new_prefix are required for generate_subnets operation")
                max_subnets = kwargs.get("max_subnets", 256)
                result = self.calculator.generate_subnets(cidr, new_prefix, max_subnets)
                
            elif operation == "check_overlap":
                networks = kwargs.get("networks")
                if not networks or len(networks) < 2:
                    raise ValidationError("At least 2 networks are required for check_overlap operation")
                result = self.calculator.check_overlap(networks)
                
            elif operation == "ip_range_to_cidrs":
                start_ip = kwargs.get("start_ip")
                end_ip = kwargs.get("end_ip")
                if not start_ip or not end_ip:
                    raise ValidationError("start_ip and end_ip are required for ip_range_to_cidrs operation")
                result = self.calculator.ip_range_to_cidrs(start_ip, end_ip)
                
            elif operation == "cidr_to_ip_range":
                cidr = kwargs.get("cidr")
                if not cidr:
                    raise ValidationError("CIDR block is required for cidr_to_ip_range operation")
                result = self.calculator.cidr_to_ip_range(cidr)
                
            elif operation == "comprehensive_analysis":
                # Perform comprehensive analysis on provided IP/CIDR
                ip = kwargs.get("ip")
                cidr = kwargs.get("cidr")
                if not ip and not cidr:
                    raise ValidationError("Either IP address or CIDR block is required for comprehensive analysis")
                
                result = {"analysis_type": "comprehensive"}
                
                if ip:
                    result["ip_analysis"] = self.calculator.validate_ip(ip)
                    
                if cidr:
                    result["cidr_analysis"] = self.calculator.validate_cidr(cidr)
                    result["subnet_info"] = self.calculator.calculate_subnet_info(cidr)
                    result["ip_range"] = self.calculator.cidr_to_ip_range(cidr)
                    
                    # Generate some example subnets if possible
                    try:
                        network = ipaddress.ip_network(cidr, strict=False)
                        if network.prefixlen < network.max_prefixlen - 2:
                            example_prefix = min(network.prefixlen + 4, network.max_prefixlen)
                            result["example_subnets"] = self.calculator.generate_subnets(
                                cidr, example_prefix, 8
                            )
                    except:
                        pass
            
            else:
                raise ValidationError(f"Unknown operation: {operation}")
            
            execution_time = (time.time() - start_time) * 1000
            
            return {
                "operation": operation,
                "timestamp": datetime.now().isoformat(),
                "success": True,
                "result": result,
                "metadata": {
                    "execution_time_ms": round(execution_time, 2),
                    "tool_version": "1.0.0"
                }
            }
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"IP/CIDR validation operation failed: {e}")
            
            return {
                "operation": operation,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e),
                "metadata": {
                    "execution_time_ms": round(execution_time, 2),
                    "tool_version": "1.0.0"
                }
            }