"""
IP Resolution Context Discovery Engine.

This engine provides comprehensive IP-to-resource mapping with CloudWAN attachment
context resolution. Ported from find_resource_by_ip.py legacy patterns with enhanced
async/await capabilities and CloudWAN awareness.
"""

import asyncio
import ipaddress
import logging
import socket
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import anyio
from botocore.exceptions import ClientError

from ..aws.client_manager import AWSClientManager
from ..models.network import (
    AttachmentState,
    AttachmentType,
    IPContext,
    RouteInfo,
    RouteTableInfo,
    SecurityGroupInfo,
    SecurityGroupRule,
)
from .multi_region_engine import MultiRegionProcessingEngine

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """AWS resource types that can have IP addresses."""

    EC2_INSTANCE = "ec2:instance"
    NETWORK_INTERFACE = "ec2:network-interface"
    LOAD_BALANCER_V2 = "elbv2:load-balancer"
    RDS_INSTANCE = "rds:instance"
    ECS_SERVICE = "ecs:service"
    NAT_GATEWAY = "ec2:nat-gateway"
    VPC_ENDPOINT = "ec2:vpc-endpoint"
    LAMBDA_FUNCTION = "lambda:function"


@dataclass
class IPResourceMatch:
    """Represents a resource that matches an IP address."""

    service: str
    resource_type: str
    resource_id: str
    resource_name: str
    ip_address: str
    region: str
    vpc_id: str | None = None
    subnet_id: str | None = None
    availability_zone: str | None = None
    state: str | None = None
    all_ips: list[str] = field(default_factory=list)
    security_groups: list[str] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)
    additional_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CloudWANContext:
    """CloudWAN context for an IP address."""

    segment_name: str | None = None
    core_network_id: str | None = None
    core_network_arn: str | None = None
    global_network_id: str | None = None
    attachment_id: str | None = None
    attachment_type: AttachmentType | None = None
    attachment_state: AttachmentState | None = None
    edge_location: str | None = None
    policy_segments: list[str] = field(default_factory=list)
    route_preferences: dict[str, Any] = field(default_factory=dict)


@dataclass
class IPResolutionResult:
    """Complete IP resolution result with all context."""

    ip_address: str
    is_valid_ip: bool
    is_public_ip: bool
    dns_resolution: str | None = None
    primary_match: IPResourceMatch | None = None
    all_matches: list[IPResourceMatch] = field(default_factory=list)
    ip_context: IPContext | None = None
    security_groups: list[SecurityGroupInfo] = field(default_factory=list)
    route_tables: list[RouteTableInfo] = field(default_factory=list)
    cloudwan_context: CloudWANContext | None = None
    network_insights: dict[str, Any] = field(default_factory=dict)
    resolution_time_ms: float = 0.0
    regions_searched: list[str] = field(default_factory=list)
    success: bool = False
    errors: list[str] = field(default_factory=list)


class IPResolutionEngine:
    """
    CloudWAN-aware IP resolution engine.

    Features:
    - Comprehensive multi-service IP discovery across EC2, ELB, RDS, ECS
    - CloudWAN attachment context resolution
    - Security group and route table analysis
    - DNS resolution and validation
    - Performance optimization with concurrent execution
    - Result caching with configurable TTL
    - Network insights and topology analysis
    """

    def __init__(
        self,
        aws_manager: AWSClientManager,
        multi_region_engine: MultiRegionProcessingEngine | None = None,
        max_concurrent_services: int = 8,
        dns_resolution_timeout: float = 2.0,
        enable_network_insights: bool = True,
        cache_ttl_seconds: float = 300.0,
        performance_target_ms: float = 2000.0,
    ):
        """
        Initialize IP Resolution Engine.

        Args:
            aws_manager: AWS client manager instance
            multi_region_engine: Multi-region processing engine (creates if None)
            max_concurrent_services: Maximum concurrent service searches
            dns_resolution_timeout: DNS resolution timeout in seconds
            enable_network_insights: Enable network topology insights
            cache_ttl_seconds: Cache TTL in seconds
            performance_target_ms: Target resolution time in milliseconds
        """
        self.aws_manager = aws_manager
        self.multi_region_engine = multi_region_engine or MultiRegionProcessingEngine(
            aws_manager=aws_manager, performance_target_ms=performance_target_ms
        )
        self.max_concurrent_services = max_concurrent_services
        self.dns_resolution_timeout = dns_resolution_timeout
        self.enable_network_insights = enable_network_insights
        self.cache_ttl_seconds = cache_ttl_seconds
        self.performance_target_ms = performance_target_ms

        # Initialize caches
        self._ip_resolution_cache: dict[str, tuple[IPResolutionResult, float]] = {}
        self._cloudwan_cache: dict[str, tuple[CloudWANContext, float]] = {}

        # Service search functions mapping
        self._service_searchers = {
            "ec2_instances": self._search_ec2_instances,
            "network_interfaces": self._search_network_interfaces,
            "load_balancers": self._search_load_balancers,
            "rds_instances": self._search_rds_instances,
            "ecs_services": self._search_ecs_services,
            "nat_gateways": self._search_nat_gateways,
            "vpc_endpoints": self._search_vpc_endpoints,
        }

        logger.info(
            f"IPResolutionEngine initialized - "
            f"max_concurrent_services: {max_concurrent_services}, "
            f"performance_target: {performance_target_ms}ms"
        )

    async def resolve_ip_address(
        self,
        ip_address: str,
        regions: list[str] | None = None,
        include_security_analysis: bool = True,
        include_cloudwan_context: bool = True,
        resolve_dns: bool = True,
        enable_caching: bool = True,
        priority_services: list[str] | None = None,
    ) -> IPResolutionResult:
        """
        Comprehensive IP address resolution with CloudWAN context.

        Args:
            ip_address: IP address to resolve (IPv4 or IPv6)
            regions: AWS regions to search (defaults to all configured)
            include_security_analysis: Include security group and route analysis
            include_cloudwan_context: Include CloudWAN attachment information
            resolve_dns: Attempt DNS resolution
            enable_caching: Enable result caching
            priority_services: Service types to search first

        Returns:
            Complete IP resolution result with all available context
        """
        start_time = time.time()

        # Check cache first
        if enable_caching:
            cache_key = self._generate_ip_cache_key(ip_address, regions or [])
            cached_result = self._get_cached_ip_result(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for IP resolution: {ip_address}")
                return cached_result

        logger.info(f"Starting IP resolution for: {ip_address}")

        # Validate and normalize IP address
        normalized_ip, is_valid, is_public = self._validate_and_normalize_ip(ip_address)
        if not is_valid:
            # Try DNS resolution if IP validation failed
            if resolve_dns:
                resolved_ip = await self._resolve_hostname_async(ip_address)
                if resolved_ip:
                    normalized_ip, is_valid, is_public = self._validate_and_normalize_ip(
                        resolved_ip
                    )

        result = IPResolutionResult(
            ip_address=normalized_ip,
            is_valid_ip=is_valid,
            is_public_ip=is_public,
            resolution_time_ms=0.0,
            success=False,
        )

        if not is_valid:
            result.errors.append(
                f"'{ip_address}' is not a valid IP address and could not be resolved"
            )
            result.resolution_time_ms = (time.time() - start_time) * 1000
            return result

        # DNS resolution for valid IPs
        if resolve_dns:
            result.dns_resolution = await self._resolve_ip_to_hostname_async(normalized_ip)

        # Multi-region resource search
        regions = regions or self.aws_manager.get_supported_regions()
        result.regions_searched = regions

        try:
            # Execute multi-region search
            search_result = await self.multi_region_engine.execute_multi_region_operation(
                operation_name="ip_resource_search",
                regions=regions,
                operation_func=self._search_region_for_ip,
                operation_args={
                    "target_ip": normalized_ip,
                    "priority_services": priority_services,
                },
                timeout_seconds=30,
                enable_caching=enable_caching,
                cache_ttl=self.cache_ttl_seconds,
            )

            # Aggregate all matches from all regions
            all_matches = []
            for region_data in search_result.results.values():
                if isinstance(region_data, dict):
                    for service_matches in region_data.values():
                        if isinstance(service_matches, list):
                            all_matches.extend(service_matches)

            result.all_matches = all_matches
            result.success = len(all_matches) > 0

            if all_matches:
                # Set primary match (first one found)
                result.primary_match = all_matches[0]

                # Build IP context from primary match
                result.ip_context = self._build_ip_context(
                    result.primary_match, normalized_ip, is_public
                )

                # Get security analysis if requested
                if include_security_analysis and result.primary_match.vpc_id:
                    try:
                        result.security_groups = await self._get_security_groups_async(
                            result.primary_match.region,
                            result.primary_match.security_groups,
                        )

                        result.route_tables = await self._get_route_tables_async(
                            result.primary_match.region,
                            result.primary_match.vpc_id,
                            result.primary_match.subnet_id,
                        )
                    except Exception as e:
                        logger.warning(f"Security analysis failed: {e}")
                        result.errors.append(f"Security analysis failed: {str(e)}")

                # Get CloudWAN context if requested
                if include_cloudwan_context and result.primary_match.vpc_id:
                    try:
                        result.cloudwan_context = await self._get_cloudwan_context_async(
                            result.primary_match.region, result.primary_match.vpc_id
                        )
                    except Exception as e:
                        logger.warning(f"CloudWAN context resolution failed: {e}")
                        result.errors.append(f"CloudWAN context failed: {str(e)}")

                # Generate network insights
                if self.enable_network_insights:
                    result.network_insights = await self._generate_network_insights(result)

            else:
                result.errors.append(f"IP address {normalized_ip} not found in any AWS resources")

        except Exception as e:
            logger.error(f"IP resolution failed for {normalized_ip}: {e}")
            result.errors.append(f"Resolution failed: {str(e)}")
            result.success = False

        result.resolution_time_ms = (time.time() - start_time) * 1000

        # Cache successful results
        if enable_caching and result.success:
            cache_key = self._generate_ip_cache_key(ip_address, regions)
            self._cache_ip_result(cache_key, result)

        logger.info(
            f"IP resolution completed for {normalized_ip} - "
            f"success: {result.success}, matches: {len(result.all_matches)}, "
            f"time: {result.resolution_time_ms:.0f}ms"
        )

        return result

    async def _search_region_for_ip(
        self,
        aws_manager: AWSClientManager,
        region: str,
        target_ip: str,
        priority_services: list[str] | None = None,
    ) -> dict[str, list[IPResourceMatch]]:
        """Search all services in a region for the target IP."""
        region_matches = {}

        # Determine search order
        services_to_search = list(self._service_searchers.keys())
        if priority_services:
            # Reorder to prioritize specified services
            priority_set = set(priority_services)
            ordered_services = []
            # Add priority services first
            for service in services_to_search:
                if service in priority_set:
                    ordered_services.append(service)
            # Add remaining services
            for service in services_to_search:
                if service not in priority_set:
                    ordered_services.append(service)
            services_to_search = ordered_services

        # Execute service searches concurrently
        semaphore = anyio.Semaphore(self.max_concurrent_services)

        async def search_service_with_semaphore(
            service_name: str,
        ) -> tuple[str, list[IPResourceMatch]]:
            async with semaphore:
                try:
                    search_func = self._service_searchers[service_name]
                    matches = await search_func(region, target_ip)
                    return service_name, matches
                except Exception as e:
                    logger.warning(f"Error searching {service_name} in {region}: {e}")
                    return service_name, []

        # Launch all service searches
        search_tasks = [
            search_service_with_semaphore(service_name) for service_name in services_to_search
        ]

        # Collect results
        service_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        for result in service_results:
            if isinstance(result, Exception):
                logger.error(f"Service search task failed: {result}")
                continue

            service_name, matches = result
            region_matches[service_name] = matches

        return region_matches

    async def _search_ec2_instances(self, region: str, target_ip: str) -> list[IPResourceMatch]:
        """Search EC2 instances for the target IP."""
        matches = []
        try:
            ec2 = self.aws_manager.get_sync_client("ec2", region)
            response = ec2.describe_instances()

            for reservation in response.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    instance_ips = self._extract_instance_ips(instance)

                    if target_ip in instance_ips:
                        match = IPResourceMatch(
                            service="EC2",
                            resource_type="Instance",
                            resource_id=instance["InstanceId"],
                            resource_name=self._extract_name_tag(instance.get("Tags", [])),
                            ip_address=target_ip,
                            region=region,
                            vpc_id=instance.get("VpcId"),
                            subnet_id=instance.get("SubnetId"),
                            availability_zone=instance.get("Placement", {}).get("AvailabilityZone"),
                            state=instance.get("State", {}).get("Name"),
                            all_ips=list(set(instance_ips)),
                            security_groups=[
                                sg.get("GroupId") for sg in instance.get("SecurityGroups", [])
                            ],
                            tags=self._format_tags(instance.get("Tags", [])),
                            additional_metadata={
                                "instance_type": instance.get("InstanceType"),
                                "launch_time": str(instance.get("LaunchTime", "")),
                                "platform": instance.get("Platform"),
                                "architecture": instance.get("Architecture"),
                            },
                        )
                        matches.append(match)
        except ClientError as e:
            logger.warning(f"Could not search EC2 instances in {region}: {e}")

        return matches

    async def _search_network_interfaces(
        self, region: str, target_ip: str
    ) -> list[IPResourceMatch]:
        """Search ENIs for the target IP."""
        matches = []
        try:
            ec2 = self.aws_manager.get_sync_client("ec2", region)
            response = ec2.describe_network_interfaces()

            for eni in response.get("NetworkInterfaces", []):
                eni_ips = self._extract_eni_ips(eni)

                if target_ip in eni_ips:
                    match = IPResourceMatch(
                        service="EC2",
                        resource_type="NetworkInterface",
                        resource_id=eni["NetworkInterfaceId"],
                        resource_name=self._extract_name_tag(eni.get("TagSet", []))
                        or eni.get("Description", "N/A"),
                        ip_address=target_ip,
                        region=region,
                        vpc_id=eni.get("VpcId"),
                        subnet_id=eni.get("SubnetId"),
                        availability_zone=eni.get("AvailabilityZone"),
                        state=eni.get("Status"),
                        all_ips=list(set(eni_ips)),
                        security_groups=[sg.get("GroupId") for sg in eni.get("Groups", [])],
                        tags=self._format_tags(eni.get("TagSet", [])),
                        additional_metadata={
                            "interface_type": eni.get("InterfaceType"),
                            "mac_address": eni.get("MacAddress"),
                            "owner_id": eni.get("OwnerId"),
                            "attachment": eni.get("Attachment", {}),
                        },
                    )
                    matches.append(match)
        except ClientError as e:
            logger.warning(f"Could not search network interfaces in {region}: {e}")

        return matches

    async def _search_load_balancers(self, region: str, target_ip: str) -> list[IPResourceMatch]:
        """Search load balancers for the target IP."""
        matches = []

        try:
            elbv2 = self.aws_manager.get_sync_client("elbv2", region)
            response = elbv2.describe_load_balancers()

            for lb in response.get("LoadBalancers", []):
                try:
                    # Resolve load balancer DNS to IPs
                    lb_ips = await self._resolve_hostname_to_ips_async(lb["DNSName"])
                    if target_ip in lb_ips:
                        match = IPResourceMatch(
                            service="ELBv2",
                            resource_type=lb["Type"].upper(),
                            resource_id=lb["LoadBalancerArn"].split("/")[-1],
                            resource_name=lb["LoadBalancerName"],
                            ip_address=target_ip,
                            region=region,
                            vpc_id=lb.get("VpcId"),
                            state=lb.get("State", {}).get("Code"),
                            all_ips=lb_ips,
                            tags=self._format_tags(lb.get("Tags", [])),
                            additional_metadata={
                                "dns_name": lb["DNSName"],
                                "scheme": lb.get("Scheme"),
                                "type": lb.get("Type"),
                                "ip_address_type": lb.get("IpAddressType"),
                                "canonical_hosted_zone_id": lb.get("CanonicalHostedZoneId"),
                            },
                        )
                        matches.append(match)
                except Exception as dns_error:
                    logger.debug(
                        f"DNS resolution failed for LB {lb.get('LoadBalancerName', 'unknown')}: {dns_error}"
                    )
                    continue
        except ClientError as e:
            logger.warning(f"Could not search ELBv2 load balancers in {region}: {e}")

        return matches

    async def _search_rds_instances(self, region: str, target_ip: str) -> list[IPResourceMatch]:
        """Search RDS instances for the target IP."""
        matches = []
        try:
            rds = self.aws_manager.get_sync_client("rds", region)
            response = rds.describe_db_instances()

            for db in response.get("DBInstances", []):
                endpoint_address = db.get("Endpoint", {}).get("Address")
                if endpoint_address:
                    try:
                        db_ips = await self._resolve_hostname_to_ips_async(endpoint_address)
                        if target_ip in db_ips:
                            match = IPResourceMatch(
                                service="RDS",
                                resource_type="DBInstance",
                                resource_id=db["DBInstanceIdentifier"],
                                resource_name=db["DBInstanceIdentifier"],
                                ip_address=target_ip,
                                region=region,
                                vpc_id=db.get("DBSubnetGroup", {}).get("VpcId"),
                                state=db.get("DBInstanceStatus"),
                                all_ips=db_ips,
                                tags=self._format_tags(db.get("TagList", [])),
                                additional_metadata={
                                    "engine": db.get("Engine"),
                                    "engine_version": db.get("EngineVersion"),
                                    "endpoint": endpoint_address,
                                    "port": db.get("Endpoint", {}).get("Port"),
                                    "allocated_storage": db.get("AllocatedStorage"),
                                    "db_instance_class": db.get("DBInstanceClass"),
                                    "multi_az": db.get("MultiAZ"),
                                },
                            )
                            matches.append(match)
                    except Exception as dns_error:
                        logger.debug(
                            f"DNS resolution failed for RDS {db.get('DBInstanceIdentifier', 'unknown')}: {dns_error}"
                        )
                        continue
        except ClientError as e:
            logger.warning(f"Could not search RDS instances in {region}: {e}")

        return matches

    async def _search_ecs_services(self, region: str, target_ip: str) -> list[IPResourceMatch]:
        """Search ECS services for the target IP."""
        matches = []
        try:
            ecs = self.aws_manager.get_sync_client("ecs", region)
            ec2 = self.aws_manager.get_sync_client("ec2", region)

            # List clusters
            clusters_response = ecs.list_clusters()

            for cluster_arn in clusters_response.get("clusterArns", []):
                # List services in cluster
                services_response = ecs.list_services(cluster=cluster_arn)

                if services_response.get("serviceArns"):
                    # Describe services
                    services_detail = ecs.describe_services(
                        cluster=cluster_arn, services=services_response["serviceArns"]
                    )

                    for service in services_detail.get("services", []):
                        # List tasks
                        tasks_response = ecs.list_tasks(
                            cluster=cluster_arn, serviceName=service["serviceName"]
                        )

                        if tasks_response.get("taskArns"):
                            # Describe tasks to get ENI information
                            tasks_detail = ecs.describe_tasks(
                                cluster=cluster_arn, tasks=tasks_response["taskArns"]
                            )

                            for task in tasks_detail.get("tasks", []):
                                # Check task attachments for ENIs
                                for attachment in task.get("attachments", []):
                                    if attachment.get("type") == "ElasticNetworkInterface":
                                        for detail in attachment.get("details", []):
                                            if detail.get("name") == "networkInterfaceId":
                                                eni_id = detail["value"]

                                                # Check if this ENI has our target IP
                                                try:
                                                    eni_response = ec2.describe_network_interfaces(
                                                        NetworkInterfaceIds=[eni_id]
                                                    )

                                                    for eni in eni_response.get(
                                                        "NetworkInterfaces", []
                                                    ):
                                                        eni_ips = self._extract_eni_ips(eni)
                                                        if target_ip in eni_ips:
                                                            match = IPResourceMatch(
                                                                service="ECS",
                                                                resource_type="Service",
                                                                resource_id=service["serviceName"],
                                                                resource_name=service[
                                                                    "serviceName"
                                                                ],
                                                                ip_address=target_ip,
                                                                region=region,
                                                                vpc_id=eni.get("VpcId"),
                                                                subnet_id=eni.get("SubnetId"),
                                                                state=service.get("status"),
                                                                all_ips=eni_ips,
                                                                security_groups=[
                                                                    sg.get("GroupId")
                                                                    for sg in eni.get("Groups", [])
                                                                ],
                                                                tags=self._format_tags(
                                                                    service.get("tags", [])
                                                                ),
                                                                additional_metadata={
                                                                    "cluster": cluster_arn.split(
                                                                        "/"
                                                                    )[-1],
                                                                    "task_definition": service.get(
                                                                        "taskDefinition"
                                                                    ),
                                                                    "eni_id": eni_id,
                                                                    "desired_count": service.get(
                                                                        "desiredCount"
                                                                    ),
                                                                    "running_count": service.get(
                                                                        "runningCount"
                                                                    ),
                                                                    "launch_type": service.get(
                                                                        "launchType"
                                                                    ),
                                                                },
                                                            )
                                                            matches.append(match)
                                                except ClientError:
                                                    continue
        except ClientError as e:
            logger.warning(f"Could not search ECS services in {region}: {e}")

        return matches

    async def _search_nat_gateways(self, region: str, target_ip: str) -> list[IPResourceMatch]:
        """Search NAT gateways for the target IP."""
        matches = []
        try:
            ec2 = self.aws_manager.get_sync_client("ec2", region)
            response = ec2.describe_nat_gateways()

            for nat_gw in response.get("NatGateways", []):
                nat_ips = []
                for address in nat_gw.get("NatGatewayAddresses", []):
                    if address.get("PublicIp"):
                        nat_ips.append(address["PublicIp"])
                    if address.get("PrivateIp"):
                        nat_ips.append(address["PrivateIp"])

                if target_ip in nat_ips:
                    match = IPResourceMatch(
                        service="EC2",
                        resource_type="NatGateway",
                        resource_id=nat_gw["NatGatewayId"],
                        resource_name=self._extract_name_tag(nat_gw.get("Tags", [])),
                        ip_address=target_ip,
                        region=region,
                        vpc_id=nat_gw.get("VpcId"),
                        subnet_id=nat_gw.get("SubnetId"),
                        state=nat_gw.get("State"),
                        all_ips=nat_ips,
                        tags=self._format_tags(nat_gw.get("Tags", [])),
                        additional_metadata={
                            "nat_gateway_type": nat_gw.get("Type"),
                            "connectivity_type": nat_gw.get("ConnectivityType"),
                            "create_time": str(nat_gw.get("CreateTime", "")),
                        },
                    )
                    matches.append(match)
        except ClientError as e:
            logger.warning(f"Could not search NAT gateways in {region}: {e}")

        return matches

    async def _search_vpc_endpoints(self, region: str, target_ip: str) -> list[IPResourceMatch]:
        """Search VPC endpoints for the target IP."""
        matches = []
        try:
            ec2 = self.aws_manager.get_sync_client("ec2", region)
            response = ec2.describe_vpc_endpoints()

            for vpc_endpoint in response.get("VpcEndpoints", []):
                # VPC endpoints can have ENIs
                for eni_id in vpc_endpoint.get("NetworkInterfaceIds", []):
                    try:
                        eni_response = ec2.describe_network_interfaces(NetworkInterfaceIds=[eni_id])

                        for eni in eni_response.get("NetworkInterfaces", []):
                            eni_ips = self._extract_eni_ips(eni)
                            if target_ip in eni_ips:
                                match = IPResourceMatch(
                                    service="EC2",
                                    resource_type="VpcEndpoint",
                                    resource_id=vpc_endpoint["VpcEndpointId"],
                                    resource_name=self._extract_name_tag(
                                        vpc_endpoint.get("Tags", [])
                                    ),
                                    ip_address=target_ip,
                                    region=region,
                                    vpc_id=vpc_endpoint.get("VpcId"),
                                    subnet_id=eni.get("SubnetId"),
                                    state=vpc_endpoint.get("State"),
                                    all_ips=eni_ips,
                                    security_groups=[
                                        sg.get("GroupId") for sg in eni.get("Groups", [])
                                    ],
                                    tags=self._format_tags(vpc_endpoint.get("Tags", [])),
                                    additional_metadata={
                                        "vpc_endpoint_type": vpc_endpoint.get("VpcEndpointType"),
                                        "service_name": vpc_endpoint.get("ServiceName"),
                                        "eni_id": eni_id,
                                        "policy_document": vpc_endpoint.get("PolicyDocument"),
                                    },
                                )
                                matches.append(match)
                    except ClientError:
                        continue
        except ClientError as e:
            logger.warning(f"Could not search VPC endpoints in {region}: {e}")

        return matches

    def _validate_and_normalize_ip(self, ip_str: str) -> tuple[str, bool, bool]:
        """Validate and normalize IP address."""
        try:
            ip = ipaddress.ip_address(ip_str.strip())
            return str(ip), True, ip.is_global
        except ValueError:
            return ip_str, False, False

    async def _resolve_hostname_async(self, hostname: str) -> str | None:
        """Resolve hostname to IP address asynchronously."""
        try:
            # Use asyncio's getaddrinfo for async DNS resolution
            result = await asyncio.wait_for(
                asyncio.get_event_loop().getaddrinfo(hostname, None, family=socket.AF_INET),
                timeout=self.dns_resolution_timeout,
            )
            if result:
                return result[0][4][0]  # First IPv4 address
        except (TimeoutError, socket.gaierror, Exception):
            pass
        return None

    async def _resolve_ip_to_hostname_async(self, ip_address: str) -> str | None:
        """Resolve IP address to hostname asynchronously."""
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().getnameinfo((ip_address, 0), 0),
                timeout=self.dns_resolution_timeout,
            )
            return result[0]  # hostname
        except (TimeoutError, socket.herror, socket.gaierror, Exception):
            pass
        return None

    async def _resolve_hostname_to_ips_async(self, hostname: str) -> list[str]:
        """Resolve hostname to list of IP addresses asynchronously."""
        ips = []
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().getaddrinfo(hostname, None, family=socket.AF_UNSPEC),
                timeout=self.dns_resolution_timeout,
            )
            for addr_info in result:
                ip = addr_info[4][0]
                if ip not in ips:
                    ips.append(ip)
        except (TimeoutError, socket.gaierror, Exception):
            pass
        return ips

    def _extract_instance_ips(self, instance: dict[str, Any]) -> list[str]:
        """Extract all IP addresses from an EC2 instance."""
        ips = []

        if instance.get("PrivateIpAddress"):
            ips.append(instance["PrivateIpAddress"])
        if instance.get("PublicIpAddress"):
            ips.append(instance["PublicIpAddress"])

        for eni in instance.get("NetworkInterfaces", []):
            ips.extend(self._extract_eni_ips(eni))

        return ips

    def _extract_eni_ips(self, eni: dict[str, Any]) -> list[str]:
        """Extract all IP addresses from an ENI."""
        ips = []

        if eni.get("PrivateIpAddress"):
            ips.append(eni["PrivateIpAddress"])

        for private_ip in eni.get("PrivateIpAddresses", []):
            if private_ip.get("PrivateIpAddress"):
                ips.append(private_ip["PrivateIpAddress"])
            if private_ip.get("Association", {}).get("PublicIp"):
                ips.append(private_ip["Association"]["PublicIp"])

        return ips

    def _extract_name_tag(self, tags: list[dict[str, str]]) -> str:
        """Extract Name tag from resource tags."""
        for tag in tags:
            if tag.get("Key") == "Name":
                return tag.get("Value", "N/A")
        return "N/A"

    def _format_tags(self, tags: list[dict[str, str]]) -> dict[str, str]:
        """Convert AWS tag format to dictionary."""
        if not tags:
            return {}

        result = {}
        for tag in tags:
            if isinstance(tag, dict) and "Key" in tag:
                result[tag["Key"]] = tag.get("Value", "")
        return result

    def _build_ip_context(
        self, primary_match: IPResourceMatch, ip_address: str, is_public: bool
    ) -> IPContext:
        """Build IP context from primary resource match."""
        return IPContext(
            ip_address=ip_address,
            region=primary_match.region,
            availability_zone=primary_match.availability_zone,
            vpc_id=primary_match.vpc_id,
            subnet_id=primary_match.subnet_id,
            eni_id=(
                primary_match.resource_id
                if primary_match.resource_type == "NetworkInterface"
                else None
            ),
            resource_type=primary_match.service,
            resource_id=primary_match.resource_id,
            is_public=is_public,
        )

    async def _get_security_groups_async(
        self, region: str, sg_ids: list[str]
    ) -> list[SecurityGroupInfo]:
        """Get security group details asynchronously."""
        if not sg_ids:
            return []

        security_groups = []
        try:
            async with self.aws_manager.client_context("ec2", region) as ec2:
                response = await ec2.describe_security_groups(GroupIds=sg_ids)

                for sg in response.get("SecurityGroups", []):
                    # Convert rules
                    ingress_rules = [
                        self._convert_sg_rule(rule, False) for rule in sg.get("IpPermissions", [])
                    ]
                    egress_rules = [
                        self._convert_sg_rule(rule, True)
                        for rule in sg.get("IpPermissionsEgress", [])
                    ]

                    security_groups.append(
                        SecurityGroupInfo(
                            group_id=sg["GroupId"],
                            group_name=sg["GroupName"],
                            description=sg["Description"],
                            vpc_id=sg["VpcId"],
                            ingress_rules=ingress_rules,
                            egress_rules=egress_rules,
                            owner_id=sg["OwnerId"],
                        )
                    )
        except ClientError as e:
            logger.warning(f"Could not get security group details in {region}: {e}")

        return security_groups

    def _convert_sg_rule(self, rule: dict[str, Any], is_egress: bool) -> SecurityGroupRule:
        """Convert AWS security group rule to our model."""
        return SecurityGroupRule(
            ip_protocol=rule.get("IpProtocol", ""),
            from_port=rule.get("FromPort"),
            to_port=rule.get("ToPort"),
            cidr_blocks=[cidr["CidrIp"] for cidr in rule.get("IpRanges", [])],
            security_group_ids=[sg["GroupId"] for sg in rule.get("UserIdGroupPairs", [])],
            description=rule.get("Description", ""),
            is_egress=is_egress,
        )

    async def _get_route_tables_async(
        self, region: str, vpc_id: str, subnet_id: str | None
    ) -> list[RouteTableInfo]:
        """Get route table details asynchronously."""
        route_tables = []
        try:
            async with self.aws_manager.client_context("ec2", region) as ec2:
                filters = [{"Name": "vpc-id", "Values": [vpc_id]}]
                if subnet_id:
                    filters.append({"Name": "association.subnet-id", "Values": [subnet_id]})

                response = await ec2.describe_route_tables(Filters=filters)

                for rt in response.get("RouteTables", []):
                    routes = [self._convert_route(route) for route in rt.get("Routes", [])]

                    # Get associated subnets
                    associated_subnets = []
                    for assoc in rt.get("Associations", []):
                        if assoc.get("SubnetId"):
                            associated_subnets.append(assoc["SubnetId"])

                    route_tables.append(
                        RouteTableInfo(
                            route_table_id=rt["RouteTableId"],
                            vpc_id=rt["VpcId"],
                            is_main=any(
                                assoc.get("Main", False) for assoc in rt.get("Associations", [])
                            ),
                            routes=routes,
                            associated_subnets=associated_subnets,
                            tags=self._format_tags(rt.get("Tags", [])),
                        )
                    )
        except ClientError as e:
            logger.warning(f"Could not get route tables in {region}: {e}")

        return route_tables

    def _convert_route(self, route: dict[str, Any]) -> RouteInfo:
        """Convert AWS route to our model."""
        target_type = "unknown"
        target_id = None

        if route.get("GatewayId"):
            target_type = "gateway"
            target_id = route["GatewayId"]
        elif route.get("NatGatewayId"):
            target_type = "nat-gateway"
            target_id = route["NatGatewayId"]
        elif route.get("NetworkInterfaceId"):
            target_type = "network-interface"
            target_id = route["NetworkInterfaceId"]
        elif route.get("VpcPeeringConnectionId"):
            target_type = "vpc-peering"
            target_id = route["VpcPeeringConnectionId"]
        elif route.get("TransitGatewayId"):
            target_type = "transit-gateway"
            target_id = route["TransitGatewayId"]
        elif route.get("CoreNetworkArn"):
            target_type = "core-network"
            target_id = route["CoreNetworkArn"]

        return RouteInfo(
            destination_cidr=route.get(
                "DestinationCidrBlock", route.get("DestinationIpv6CidrBlock", "")
            ),
            target_type=target_type,
            target_id=target_id,
            state=route.get("State", "unknown"),
            origin=route.get("Origin", "unknown"),
            is_propagated=route.get("Origin") == "CreateRoute",
        )

    async def _get_cloudwan_context_async(self, region: str, vpc_id: str) -> CloudWANContext | None:
        """Get CloudWAN context for a VPC asynchronously."""
        cache_key = f"cloudwan:{region}:{vpc_id}"

        # Check cache first
        cached_context = self._get_cached_cloudwan_context(cache_key)
        if cached_context:
            return cached_context

        try:
            async with self.aws_manager.client_context("networkmanager", "us-west-2") as nm:
                # List global networks
                global_networks = await nm.describe_global_networks()

                for gn in global_networks.get("GlobalNetworks", []):
                    # Get core networks for this global network
                    core_networks = await nm.list_core_networks(
                        GlobalNetworkId=gn["GlobalNetworkId"]
                    )

                    for cn in core_networks.get("CoreNetworks", []):
                        # Get attachments for this core network
                        attachments = await nm.list_attachments(CoreNetworkId=cn["CoreNetworkId"])

                        for attachment in attachments.get("Attachments", []):
                            if attachment.get("AttachmentType") == "VPC" and attachment.get(
                                "ResourceArn", ""
                            ).endswith(f"vpc/{vpc_id}"):
                                # Found a matching VPC attachment
                                context = CloudWANContext(
                                    segment_name=attachment.get("SegmentName"),
                                    core_network_id=cn["CoreNetworkId"],
                                    core_network_arn=cn["CoreNetworkArn"],
                                    global_network_id=gn["GlobalNetworkId"],
                                    attachment_id=attachment["AttachmentId"],
                                    attachment_type=AttachmentType.VPC,
                                    attachment_state=AttachmentState(attachment["State"]),
                                    edge_location=attachment["EdgeLocation"],
                                )

                                # Cache the result
                                self._cache_cloudwan_context(cache_key, context)
                                return context

        except ClientError as e:
            logger.warning(f"Could not get CloudWAN context: {e}")

        return None

    async def _generate_network_insights(self, result: IPResolutionResult) -> dict[str, Any]:
        """Generate network topology insights."""
        insights = {
            "resource_connectivity": {},
            "security_posture": {},
            "routing_analysis": {},
            "cloudwan_integration": {},
        }

        if not result.primary_match:
            return insights

        # Resource connectivity analysis
        insights["resource_connectivity"] = {
            "resource_type": result.primary_match.resource_type,
            "is_public_facing": result.is_public_ip,
            "vpc_isolation": result.primary_match.vpc_id is not None,
            "multi_az_deployment": len(
                set(
                    match.availability_zone
                    for match in result.all_matches
                    if match.availability_zone
                )
            )
            > 1,
            "cross_region_presence": len(set(match.region for match in result.all_matches)) > 1,
        }

        # Security posture analysis
        if result.security_groups:
            open_ports = []
            for sg in result.security_groups:
                for rule in sg.ingress_rules:
                    if "0.0.0.0/0" in rule.cidr_blocks:
                        open_ports.append(
                            {
                                "protocol": rule.ip_protocol,
                                "from_port": rule.from_port,
                                "to_port": rule.to_port,
                            }
                        )

            insights["security_posture"] = {
                "security_groups_count": len(result.security_groups),
                "publicly_accessible_ports": open_ports,
                "security_risk_score": len(open_ports) * 10,  # Simple scoring
            }

        # Routing analysis
        if result.route_tables:
            internet_routes = []
            private_routes = []
            for rt in result.route_tables:
                for route in rt.routes:
                    if route.destination_cidr == "0.0.0.0/0":
                        internet_routes.append(route.target_type)
                    else:
                        private_routes.append(route.target_type)

            insights["routing_analysis"] = {
                "has_internet_gateway": "gateway" in internet_routes,
                "has_nat_gateway": "nat-gateway" in internet_routes,
                "private_routing_types": list(set(private_routes)),
                "route_tables_count": len(result.route_tables),
            }

        # CloudWAN integration analysis
        if result.cloudwan_context:
            insights["cloudwan_integration"] = {
                "is_cloudwan_attached": True,
                "segment_name": result.cloudwan_context.segment_name,
                "attachment_state": (
                    result.cloudwan_context.attachment_state.value
                    if result.cloudwan_context.attachment_state
                    else None
                ),
                "edge_location": result.cloudwan_context.edge_location,
                "global_network_connectivity": True,
            }
        else:
            insights["cloudwan_integration"] = {
                "is_cloudwan_attached": False,
                "traditional_networking": True,
            }

        return insights

    def _generate_ip_cache_key(self, ip_address: str, regions: list[str]) -> str:
        """Generate cache key for IP resolution."""
        import hashlib

        key_data = f"{ip_address}:{':'.join(sorted(regions))}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def _get_cached_ip_result(self, cache_key: str) -> IPResolutionResult | None:
        """Get cached IP resolution result."""
        if cache_key in self._ip_resolution_cache:
            result, cached_time = self._ip_resolution_cache[cache_key]
            if time.time() - cached_time < self.cache_ttl_seconds:
                return result
            else:
                del self._ip_resolution_cache[cache_key]
        return None

    def _cache_ip_result(self, cache_key: str, result: IPResolutionResult):
        """Cache IP resolution result."""
        self._ip_resolution_cache[cache_key] = (result, time.time())

        # Simple cleanup
        current_time = time.time()
        expired_keys = [
            key
            for key, (_, cached_time) in self._ip_resolution_cache.items()
            if current_time - cached_time > self.cache_ttl_seconds
        ]
        for key in expired_keys:
            del self._ip_resolution_cache[key]

    def _get_cached_cloudwan_context(self, cache_key: str) -> CloudWANContext | None:
        """Get cached CloudWAN context."""
        if cache_key in self._cloudwan_cache:
            context, cached_time = self._cloudwan_cache[cache_key]
            if time.time() - cached_time < self.cache_ttl_seconds:
                return context
            else:
                del self._cloudwan_cache[cache_key]
        return None

    def _cache_cloudwan_context(self, cache_key: str, context: CloudWANContext):
        """Cache CloudWAN context."""
        self._cloudwan_cache[cache_key] = (context, time.time())

    def clear_caches(self):
        """Clear all caches."""
        self._ip_resolution_cache.clear()
        self._cloudwan_cache.clear()
        if hasattr(self.multi_region_engine, "clear_cache"):
            self.multi_region_engine.clear_cache()
        logger.info("IP resolution engine caches cleared")

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get performance metrics for the IP resolution engine."""
        return {
            "cache_stats": {
                "ip_resolution_cache_size": len(self._ip_resolution_cache),
                "cloudwan_cache_size": len(self._cloudwan_cache),
                "cache_hit_rate": 0.0,  # TODO: Implement hit rate tracking
            },
            "multi_region_engine_metrics": self.multi_region_engine.get_region_health_status(),
            "performance_target_ms": self.performance_target_ms,
            "max_concurrent_services": self.max_concurrent_services,
        }
