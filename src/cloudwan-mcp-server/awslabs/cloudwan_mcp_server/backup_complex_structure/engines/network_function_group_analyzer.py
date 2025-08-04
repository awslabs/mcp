"""
Network Function Group Analyzer Engine for CloudWAN MCP Server.

This engine provides comprehensive Network Function Group routing logic analysis,
send-to/send-via policy evaluation, and multi-hop routing path validation.

Features:
- Network Function Group routing logic analysis
- Send-to/send-via policy evaluation and validation
- Multi-hop routing path calculation and optimization
- Network function override analysis and conflict detection
- Service insertion point identification and validation
- Real-time NFG performance monitoring and alerting
"""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from botocore.exceptions import ClientError

from ..aws.client_manager import AWSClientManager
from ..config import CloudWANConfig
from ..utils.aws_operations import AWSOperationError


class NetworkFunctionType(str, Enum):
    """Types of network functions."""

    INSPECTION = "inspection"
    FIREWALL = "firewall"
    IDS_IPS = "ids-ips"
    DLP = "dlp"
    PROXY = "proxy"
    NAT = "nat"
    LOAD_BALANCER = "load-balancer"
    SERVICE_MESH = "service-mesh"
    CUSTOM = "custom"


class RoutingBehavior(str, Enum):
    """Routing behavior for Network Function Groups."""

    SEND_VIA = "send-via"  # Traffic must go through NFG
    SEND_TO = "send-to"  # Traffic can be sent to NFG
    BYPASS = "bypass"  # Traffic can bypass NFG
    DENY = "deny"  # Traffic is denied


class PolicyAction(str, Enum):
    """Policy actions for Network Function Groups."""

    INSPECT = "inspect"
    ALLOW = "allow"
    DROP = "drop"
    REDIRECT = "redirect"
    MODIFY = "modify"
    LOG = "log"


@dataclass
class RoutingRule:
    """Individual routing rule within a Network Function Group."""

    rule_id: str
    priority: int
    source_criteria: Dict[str, Any]
    destination_criteria: Dict[str, Any]
    action: PolicyAction
    parameters: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    last_matched: Optional[datetime] = None
    match_count: int = 0


@dataclass
class ServiceInsertionPoint:
    """Service insertion point for network function deployment."""

    insertion_id: str
    location: str
    segment_name: str
    attachment_id: str
    function_type: NetworkFunctionType
    insertion_mode: str  # "inline", "tap", "redirect"
    capacity_info: Dict[str, Any] = field(default_factory=dict)
    health_status: str = "unknown"
    performance_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingPath:
    """Multi-hop routing path through Network Function Groups."""

    path_id: str
    source_segment: str
    destination_segment: str
    hops: List[str] = field(default_factory=list)
    network_functions: List[str] = field(default_factory=list)
    total_latency_ms: Optional[int] = None
    path_cost: float = 1.0
    is_optimal: bool = False
    alternate_paths: List[str] = field(default_factory=list)
    policy_constraints: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class NetworkFunctionGroup:
    """Complete Network Function Group configuration and analysis."""

    name: str
    core_network_id: str
    function_type: NetworkFunctionType
    description: Optional[str] = None

    # Configuration
    require_attachment_acceptance: bool = False
    send_via_mode: Optional[str] = None
    send_to_segments: List[str] = field(default_factory=list)
    bypass_allowed: bool = False

    # Routing Analysis
    routing_rules: List[RoutingRule] = field(default_factory=list)
    routing_behavior: RoutingBehavior = RoutingBehavior.SEND_TO
    policy_overrides: List[Dict[str, Any]] = field(default_factory=list)

    # Service Insertion
    insertion_points: List[ServiceInsertionPoint] = field(default_factory=list)
    supported_protocols: List[str] = field(default_factory=list)
    processing_capacity: Dict[str, Any] = field(default_factory=dict)

    # Analytics and Performance
    traffic_volume: Dict[str, int] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    error_rates: Dict[str, float] = field(default_factory=dict)

    # State Tracking
    is_active: bool = True
    last_updated: Optional[datetime] = None
    policy_version: Optional[int] = None
    configuration_errors: List[str] = field(default_factory=list)


class NetworkFunctionGroupAnalyzer:
    """
    Network Function Group Analyzer Engine.

    Provides comprehensive analysis of Network Function Groups including
    routing logic, policy evaluation, and multi-hop path calculation.
    """

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig):
        """Initialize the Network Function Group Analyzer."""
        self.aws_manager = aws_manager
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.executor = ThreadPoolExecutor(max_workers=6)

        # NFG analysis cache
        self._nfg_cache: Dict[str, NetworkFunctionGroup] = {}
        self._cache_ttl = timedelta(minutes=10)

        # Custom NetworkManager endpoint support
        self.custom_nm_endpoint = self.config.aws.custom_endpoints.get("networkmanager")

    async def discover_all_network_function_groups(
        self,
        core_network_id: str,
        include_routing_analysis: bool = True,
        include_performance_metrics: bool = True,
        force_refresh: bool = False,
    ) -> List[NetworkFunctionGroup]:
        """
        Discover and analyze all Network Function Groups in a Core Network.

        Args:
            core_network_id: Core Network ID to analyze
            include_routing_analysis: Include detailed routing analysis
            include_performance_metrics: Include performance metrics
            force_refresh: Force cache refresh

        Returns:
            List of analyzed Network Function Groups
        """
        self.logger.info(f"Discovering Network Function Groups for Core Network: {core_network_id}")

        try:
            # Get Core Network policy document
            policy_doc = await self._get_core_network_policy(core_network_id)
            if not policy_doc:
                self.logger.warning("No policy document found - no NFGs to analyze")
                return []

            # Extract Network Function Groups from policy
            nfg_definitions = policy_doc.get("network-function-groups", [])
            if not nfg_definitions:
                self.logger.info("No Network Function Groups defined in policy")
                return []

            # Analyze each NFG concurrently
            analysis_tasks = []
            for nfg_def in nfg_definitions:
                nfg_name = nfg_def.get("name", "")
                if nfg_name:
                    task = self.analyze_network_function_group(
                        core_network_id=core_network_id,
                        nfg_name=nfg_name,
                        nfg_definition=nfg_def,
                        policy_doc=policy_doc,
                        include_routing_analysis=include_routing_analysis,
                        include_performance_metrics=include_performance_metrics,
                        force_refresh=force_refresh,
                    )
                    analysis_tasks.append(task)

            # Execute analysis tasks
            nfg_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)

            # Consolidate results
            network_function_groups = []
            for result in nfg_results:
                if isinstance(result, Exception):
                    self.logger.error(f"NFG analysis failed: {result}")
                    continue
                network_function_groups.append(result)

            self.logger.info(f"Analyzed {len(network_function_groups)} Network Function Groups")
            return network_function_groups

        except Exception as e:
            raise AWSOperationError(f"Network Function Group discovery failed: {str(e)}")

    async def analyze_network_function_group(
        self,
        core_network_id: str,
        nfg_name: str,
        nfg_definition: Optional[Dict[str, Any]] = None,
        policy_doc: Optional[Dict[str, Any]] = None,
        include_routing_analysis: bool = True,
        include_performance_metrics: bool = True,
        force_refresh: bool = False,
    ) -> NetworkFunctionGroup:
        """
        Analyze a specific Network Function Group in detail.

        Args:
            core_network_id: Core Network ID
            nfg_name: Network Function Group name
            nfg_definition: Optional NFG definition from policy
            policy_doc: Optional policy document
            include_routing_analysis: Include routing logic analysis
            include_performance_metrics: Include performance analysis
            force_refresh: Force cache refresh

        Returns:
            Analyzed Network Function Group
        """
        cache_key = f"{core_network_id}:{nfg_name}"

        # Check cache first (unless force refresh)
        if not force_refresh and cache_key in self._nfg_cache:
            cached_nfg = self._nfg_cache[cache_key]
            if (datetime.now() - (cached_nfg.last_updated or datetime.min)) < self._cache_ttl:
                self.logger.debug(f"Using cached analysis for NFG {nfg_name}")
                return cached_nfg

        self.logger.info(f"Analyzing Network Function Group: {nfg_name}")

        try:
            # Get policy document if not provided
            if not policy_doc:
                policy_doc = await self._get_core_network_policy(core_network_id)

            # Get NFG definition if not provided
            if not nfg_definition and policy_doc:
                nfg_definition = self._find_nfg_in_policy(nfg_name, policy_doc)

            if not nfg_definition:
                raise AWSOperationError(f"Network Function Group {nfg_name} not found in policy")

            # Create base NFG object
            nfg = NetworkFunctionGroup(
                name=nfg_name,
                core_network_id=core_network_id,
                function_type=self._determine_function_type(nfg_definition),
                description=nfg_definition.get("description"),
                require_attachment_acceptance=nfg_definition.get(
                    "require-attachment-acceptance", False
                ),
                send_via_mode=nfg_definition.get("send-via"),
                send_to_segments=nfg_definition.get("send-to", []),
                last_updated=datetime.now(),
            )

            # Extract policy version
            if policy_doc:
                nfg.policy_version = policy_doc.get("version")

            # Parallel analysis tasks
            analysis_tasks = []

            # Routing behavior analysis
            analysis_tasks.append(self._analyze_routing_behavior(nfg_definition, policy_doc))

            # Service insertion analysis
            analysis_tasks.append(
                self._analyze_service_insertion_points(core_network_id, nfg_name, nfg_definition)
            )

            # Policy override analysis
            analysis_tasks.append(self._analyze_policy_overrides(nfg_name, policy_doc))

            # Performance metrics (if requested)
            if include_performance_metrics:
                analysis_tasks.append(self._collect_performance_metrics(core_network_id, nfg_name))
            else:
                analysis_tasks.append(asyncio.create_task(asyncio.sleep(0, result={})))

            # Execute analysis tasks
            routing_data, insertion_data, override_data, metrics_data = await asyncio.gather(
                *analysis_tasks, return_exceptions=True
            )

            # Process routing behavior data
            if not isinstance(routing_data, Exception):
                nfg.routing_behavior = routing_data.get("behavior", RoutingBehavior.SEND_TO)
                nfg.routing_rules = routing_data.get("rules", [])
                nfg.bypass_allowed = routing_data.get("bypass_allowed", False)

            # Process service insertion data
            if not isinstance(insertion_data, Exception):
                nfg.insertion_points = insertion_data.get("insertion_points", [])
                nfg.supported_protocols = insertion_data.get("supported_protocols", [])
                nfg.processing_capacity = insertion_data.get("processing_capacity", {})

            # Process policy override data
            if not isinstance(override_data, Exception):
                nfg.policy_overrides = override_data.get("overrides", [])

            # Process performance metrics data
            if not isinstance(metrics_data, Exception):
                nfg.traffic_volume = metrics_data.get("traffic_volume", {})
                nfg.performance_metrics = metrics_data.get("performance_metrics", {})
                nfg.error_rates = metrics_data.get("error_rates", {})

            # Perform detailed routing analysis if requested
            if include_routing_analysis:
                nfg.routing_rules = await self._analyze_detailed_routing_rules(
                    nfg_definition, policy_doc
                )

            # Validate configuration
            nfg.configuration_errors = await self._validate_nfg_configuration(nfg, policy_doc)
            nfg.is_active = len(nfg.configuration_errors) == 0

            # Cache the result
            self._nfg_cache[cache_key] = nfg

            return nfg

        except Exception as e:
            raise AWSOperationError(f"Network Function Group analysis failed: {str(e)}")

    async def calculate_multi_hop_routing_paths(
        self,
        core_network_id: str,
        source_segment: str,
        destination_segment: str,
        include_nfg_constraints: bool = True,
        max_hops: int = 5,
    ) -> List[RoutingPath]:
        """
        Calculate multi-hop routing paths through Network Function Groups.

        Args:
            core_network_id: Core Network ID
            source_segment: Source segment name
            destination_segment: Destination segment name
            include_nfg_constraints: Include NFG routing constraints
            max_hops: Maximum number of hops to consider

        Returns:
            List of possible routing paths
        """
        self.logger.info(
            f"Calculating routing paths from {source_segment} to {destination_segment}"
        )

        try:
            # Get all NFGs for constraint analysis
            nfgs = await self.discover_all_network_function_groups(
                core_network_id, include_routing_analysis=True
            )

            # Get policy document for routing rules
            policy_doc = await self._get_core_network_policy(core_network_id)

            # Initialize path finding
            routing_paths = []
            explored_paths = set()

            # Use graph-based path finding
            paths = await self._find_all_paths(
                source_segment,
                destination_segment,
                nfgs,
                policy_doc,
                max_hops,
                explored_paths,
            )

            # Analyze and optimize each path
            for path_data in paths:
                routing_path = RoutingPath(
                    path_id=f"{source_segment}-{destination_segment}-{len(routing_paths)}",
                    source_segment=source_segment,
                    destination_segment=destination_segment,
                    hops=path_data["hops"],
                    network_functions=path_data["network_functions"],
                )

                # Calculate path metrics
                routing_path.total_latency_ms = await self._calculate_path_latency(routing_path)
                routing_path.path_cost = self._calculate_path_cost(routing_path, nfgs)
                routing_path.policy_constraints = await self._extract_path_constraints(
                    routing_path, nfgs, policy_doc
                )

                routing_paths.append(routing_path)

            # Identify optimal paths
            if routing_paths:
                optimal_path = min(routing_paths, key=lambda p: p.path_cost)
                optimal_path.is_optimal = True

                # Set alternate paths for others
                for path in routing_paths:
                    if path != optimal_path:
                        path.alternate_paths = [optimal_path.path_id]

            self.logger.info(f"Found {len(routing_paths)} routing paths")
            return routing_paths

        except Exception as e:
            raise AWSOperationError(f"Multi-hop routing path calculation failed: {str(e)}")

    async def evaluate_send_to_send_via_policies(
        self, core_network_id: str, nfg_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate send-to and send-via policy configurations.

        Args:
            core_network_id: Core Network ID
            nfg_name: Optional specific NFG name to evaluate

        Returns:
            List of policy evaluation results
        """
        self.logger.info(f"Evaluating send-to/send-via policies for {nfg_name or 'all NFGs'}")

        try:
            # Get all NFGs or specific NFG
            if nfg_name:
                nfg = await self.analyze_network_function_group(core_network_id, nfg_name)
                nfgs = [nfg]
            else:
                nfgs = await self.discover_all_network_function_groups(core_network_id)

            # Evaluate policies for each NFG
            evaluation_results = []

            for nfg in nfgs:
                evaluation = {
                    "nfg_name": nfg.name,
                    "send_to_evaluation": await self._evaluate_send_to_policy(nfg),
                    "send_via_evaluation": await self._evaluate_send_via_policy(nfg),
                    "policy_conflicts": await self._detect_policy_conflicts(nfg, nfgs),
                    "recommendations": await self._generate_policy_recommendations(nfg),
                }
                evaluation_results.append(evaluation)

            return evaluation_results

        except Exception as e:
            raise AWSOperationError(f"Policy evaluation failed: {str(e)}")

    async def _get_core_network_policy(self, core_network_id: str) -> Optional[Dict[str, Any]]:
        """Get Core Network policy document."""
        try:
            nm_client = await self._get_networkmanager_client()
            response = await nm_client.get_core_network_policy(CoreNetworkId=core_network_id)

            policy_doc = response.get("CoreNetworkPolicy", {}).get("PolicyDocument")
            if policy_doc:
                return json.loads(policy_doc)
            return None

        except ClientError as e:
            self.logger.warning(f"Failed to get Core Network policy: {e}")
            return None

    def _find_nfg_in_policy(
        self, nfg_name: str, policy_doc: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Find Network Function Group definition in policy document."""
        for nfg in policy_doc.get("network-function-groups", []):
            if nfg.get("name") == nfg_name:
                return nfg
        return None

    def _determine_function_type(self, nfg_definition: Dict[str, Any]) -> NetworkFunctionType:
        """Determine the function type from NFG definition."""
        # This would analyze the NFG configuration to determine its type
        # For now, return a default based on naming conventions
        name = nfg_definition.get("name", "").lower()

        if "firewall" in name or "fw" in name:
            return NetworkFunctionType.FIREWALL
        elif "inspection" in name or "inspect" in name:
            return NetworkFunctionType.INSPECTION
        elif "ids" in name or "ips" in name:
            return NetworkFunctionType.IDS_IPS
        elif "proxy" in name:
            return NetworkFunctionType.PROXY
        elif "nat" in name:
            return NetworkFunctionType.NAT
        elif "lb" in name or "load" in name:
            return NetworkFunctionType.LOAD_BALANCER
        else:
            return NetworkFunctionType.CUSTOM

    def _determine_function_type_from_attachment(
        self, attachment: Dict[str, Any], nfg_definition: Dict[str, Any]
    ) -> NetworkFunctionType:
        """Determine function type from attachment tags or properties."""
        # Check tags first
        attachment_tags = {t.get("Key"): t.get("Value") for t in attachment.get("Tags", [])}

        if "FunctionType" in attachment_tags:
            function_type = attachment_tags["FunctionType"].lower()

            if function_type == "firewall":
                return NetworkFunctionType.FIREWALL
            elif function_type == "inspection":
                return NetworkFunctionType.INSPECTION
            elif function_type in ["ids", "ips", "idps"]:
                return NetworkFunctionType.IDS_IPS
            elif function_type == "dlp":
                return NetworkFunctionType.DLP
            elif function_type == "proxy":
                return NetworkFunctionType.PROXY
            elif function_type == "nat":
                return NetworkFunctionType.NAT
            elif function_type in ["lb", "loadbalancer", "load-balancer"]:
                return NetworkFunctionType.LOAD_BALANCER
            elif function_type == "service-mesh":
                return NetworkFunctionType.SERVICE_MESH

        # Fall back to NFG name
        nfg_name = nfg_definition.get("name", "").lower()

        if "firewall" in nfg_name or "fw" in nfg_name:
            return NetworkFunctionType.FIREWALL
        elif "inspection" in nfg_name or "inspect" in nfg_name:
            return NetworkFunctionType.INSPECTION
        elif "ids" in nfg_name or "ips" in nfg_name:
            return NetworkFunctionType.IDS_IPS
        elif "dlp" in nfg_name:
            return NetworkFunctionType.DLP
        elif "proxy" in nfg_name:
            return NetworkFunctionType.PROXY
        elif "nat" in nfg_name:
            return NetworkFunctionType.NAT
        elif "lb" in nfg_name or "load" in nfg_name:
            return NetworkFunctionType.LOAD_BALANCER

        # Default
        return NetworkFunctionType.CUSTOM

    async def _analyze_routing_behavior(
        self, nfg_definition: Dict[str, Any], policy_doc: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze routing behavior for NFG."""
        behavior = RoutingBehavior.SEND_TO  # Default

        # Check for send-via configuration
        if nfg_definition.get("send-via"):
            behavior = RoutingBehavior.SEND_VIA
        elif nfg_definition.get("send-to"):
            behavior = RoutingBehavior.SEND_TO

        # Check if bypass is allowed
        bypass_allowed = not nfg_definition.get("require-attachment-acceptance", False)

        return {
            "behavior": behavior,
            "rules": [],  # Would be populated with detailed rules
            "bypass_allowed": bypass_allowed,
        }

    async def _analyze_service_insertion_points(
        self, core_network_id: str, nfg_name: str, nfg_definition: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze service insertion points for NFG."""
        self.logger.info(f"Analyzing service insertion points for {nfg_name}")
        insertion_points = []
        supported_protocols = ["tcp", "udp", "icmp"]
        processing_capacity = {}

        try:
            # Get NetworkManager client
            nm_client = await self._get_networkmanager_client()

            # Get attachments that might be insertion points
            attachments_response = await nm_client.list_attachments(
                CoreNetworkId=core_network_id,
            )

            attachments = attachments_response.get("Attachments", [])

            # Filter attachments that belong to this NFG
            for attachment in attachments:
                # Check if this attachment is used by the NFG
                attachment_tags = {t.get("Key"): t.get("Value") for t in attachment.get("Tags", [])}
                if attachment_tags.get("NetworkFunctionGroup") == nfg_name:
                    # This attachment is part of the NFG
                    insertion_id = attachment.get("AttachmentId", "")
                    segment_name = attachment.get("SegmentName", "")
                    location = attachment.get("EdgeLocation", "")

                    # Determine function type from tags or naming convention
                    function_type = self._determine_function_type_from_attachment(
                        attachment, nfg_definition
                    )

                    # Determine insertion mode
                    insertion_mode = attachment_tags.get("InsertionMode", "inline")

                    # Determine health status from attachment state
                    health_status = (
                        "healthy" if attachment.get("State", "") == "AVAILABLE" else "unhealthy"
                    )

                    # Get capacity info if available
                    capacity_info = {}
                    resource_arn = attachment.get("ResourceArn")
                    if resource_arn:
                        capacity_info = await self._get_resource_capacity_info(resource_arn)

                    insertion_point = ServiceInsertionPoint(
                        insertion_id=insertion_id,
                        location=location,
                        segment_name=segment_name,
                        attachment_id=insertion_id,
                        function_type=function_type,
                        insertion_mode=insertion_mode,
                        capacity_info=capacity_info,
                        health_status=health_status,
                    )

                    insertion_points.append(insertion_point)

            # If there are insertion points, try to determine supported protocols
            if insertion_points:
                supported_protocols = await self._determine_supported_protocols(
                    core_network_id, nfg_name, insertion_points
                )

                # Calculate aggregate processing capacity
                processing_capacity = self._calculate_aggregate_capacity(insertion_points)

        except Exception as e:
            self.logger.error(f"Failed to analyze service insertion points: {e}")

        return {
            "insertion_points": insertion_points,
            "supported_protocols": supported_protocols,
            "processing_capacity": processing_capacity,
        }

    async def _analyze_policy_overrides(
        self, nfg_name: str, policy_doc: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze policy override rules for NFG."""
        overrides = []

        # Look for segment actions that reference this NFG
        for segment in policy_doc.get("segments", []):
            for action in segment.get("segment-actions", []):
                if action.get("network-function-group") == nfg_name:
                    overrides.append(
                        {
                            "segment": segment.get("name"),
                            "action": action.get("action"),
                            "conditions": action.get("conditions", {}),
                            "parameters": action.get("parameters", {}),
                        }
                    )

        return {"overrides": overrides}

    async def _collect_performance_metrics(
        self, core_network_id: str, nfg_name: str
    ) -> Dict[str, Any]:
        """Collect performance metrics for NFG."""
        # This would integrate with CloudWatch or other monitoring systems
        # For now, return placeholder metrics
        return {
            "traffic_volume": {
                "total_bytes": 0,
                "total_packets": 0,
                "average_throughput_mbps": 0,
            },
            "performance_metrics": {
                "average_latency_ms": 0,
                "packet_loss_rate": 0.0,
                "processing_time_ms": 0,
            },
            "error_rates": {
                "connection_errors": 0.0,
                "processing_errors": 0.0,
                "timeout_errors": 0.0,
            },
        }

    async def _analyze_detailed_routing_rules(
        self, nfg_definition: Dict[str, Any], policy_doc: Dict[str, Any]
    ) -> List[RoutingRule]:
        """Analyze detailed routing rules for NFG."""
        routing_rules = []

        # Get NFG name
        nfg_name = nfg_definition.get("name")
        if not nfg_name:
            return routing_rules

        # Extract routing rules from NFG definition
        rule_configs = nfg_definition.get("routing-rules", [])

        # Process each rule in the NFG definition
        for i, rule_config in enumerate(rule_configs):
            rule_id = rule_config.get("rule-id", f"rule-{i+1}")
            priority = rule_config.get("priority", 100 + i * 10)  # Default priority

            source_criteria = rule_config.get("source", {})
            destination_criteria = rule_config.get("destination", {})

            # Map rule action
            action_str = rule_config.get("action", "inspect").lower()
            if action_str == "inspect":
                action = PolicyAction.INSPECT
            elif action_str == "allow":
                action = PolicyAction.ALLOW
            elif action_str == "drop":
                action = PolicyAction.DROP
            elif action_str == "redirect":
                action = PolicyAction.REDIRECT
            elif action_str == "modify":
                action = PolicyAction.MODIFY
            elif action_str == "log":
                action = PolicyAction.LOG
            else:
                action = PolicyAction.INSPECT

            parameters = rule_config.get("parameters", {})
            is_active = rule_config.get("is_active", True)

            rule = RoutingRule(
                rule_id=rule_id,
                priority=priority,
                source_criteria=source_criteria,
                destination_criteria=destination_criteria,
                action=action,
                parameters=parameters,
                is_active=is_active,
            )

            routing_rules.append(rule)

        # Look for segment actions in policy that reference this NFG
        for segment in policy_doc.get("segments", []):
            segment_name = segment.get("name")
            segment_actions = segment.get("segment-actions", [])

            for action in segment_actions:
                if action.get("network-function-group") == nfg_name:
                    # This action references our NFG - create an implied rule
                    rule_id = f"implied-{segment_name}-{len(routing_rules)}"

                    # Extract CIDR blocks or other matching criteria
                    source_criteria = {}
                    destination_criteria = {}

                    if "source-cidr-blocks" in action:
                        source_criteria["cidr-blocks"] = action.get("source-cidr-blocks")

                    if "destination-cidr-blocks" in action:
                        destination_criteria["cidr-blocks"] = action.get("destination-cidr-blocks")

                    # Map action type
                    action_type = action.get("action", "inspect").lower()
                    if action_type == "create-route":
                        policy_action = PolicyAction.REDIRECT
                    elif action_type == "share":
                        policy_action = PolicyAction.ALLOW
                    else:
                        policy_action = PolicyAction.INSPECT

                    rule = RoutingRule(
                        rule_id=rule_id,
                        priority=1000 + len(routing_rules),  # Low priority for implied rules
                        source_criteria=source_criteria,
                        destination_criteria=destination_criteria,
                        action=policy_action,
                        parameters=action,
                        is_active=True,
                    )

                    routing_rules.append(rule)

        # Sort by priority
        routing_rules.sort(key=lambda x: x.priority)

        return routing_rules

    async def _validate_nfg_configuration(
        self, nfg: NetworkFunctionGroup, policy_doc: Dict[str, Any]
    ) -> List[str]:
        """Validate NFG configuration and return errors."""
        errors = []

        # Check for required fields
        if not nfg.send_to_segments and not nfg.send_via_mode:
            errors.append("Neither send-to segments nor send-via mode configured")

        # Check for conflicting configurations
        if nfg.send_to_segments and nfg.send_via_mode:
            errors.append("Both send-to and send-via configured - may cause conflicts")

        # Validate segment references
        all_segments = [s.get("name") for s in policy_doc.get("segments", [])]
        for segment in nfg.send_to_segments:
            if segment not in all_segments:
                errors.append(f"Referenced segment '{segment}' does not exist")

        return errors

    async def _find_all_paths(
        self,
        source: str,
        destination: str,
        nfgs: List[NetworkFunctionGroup],
        policy_doc: Dict[str, Any],
        max_hops: int,
        explored: Set[str],
    ) -> List[Dict[str, Any]]:
        """Find all possible routing paths using graph traversal."""
        self.logger.info(f"Finding paths from {source} to {destination} with max_hops={max_hops}")
        paths = []

        # Build a graph representation of the network
        graph = await self._build_segment_graph(policy_doc, nfgs)

        # Direct path
        if source != destination and destination in graph.get(source, []):
            paths.append({"hops": [source, destination], "network_functions": []})

        # Find paths through NFGs
        nfg_paths = await self._find_paths_through_nfgs(source, destination, nfgs, graph, max_hops)
        paths.extend(nfg_paths)

        return paths

    async def _build_segment_graph(
        self, policy_doc: Dict[str, Any], nfgs: List[NetworkFunctionGroup]
    ) -> Dict[str, List[str]]:
        """Build a graph representation of segments and their connections."""
        graph = {}

        # Get segments from policy document
        segments = policy_doc.get("segments", [])
        for segment in segments:
            segment_name = segment.get("name")
            if not segment_name:
                continue

            # Initialize adjacency list
            graph[segment_name] = []

            # Check if segment is isolated
            if segment.get("isolate-attachments", False):
                # Isolated segments don't connect to other segments directly
                continue

            # Process segment actions
            for action in segment.get("segment-actions", []):
                action_type = action.get("action", "")
                target_segment = action.get("segment")

                # If action is to share with another segment, add edge
                if action_type == "share" and target_segment:
                    graph[segment_name].append(target_segment)

        # Add NFG-based connectivity
        for nfg in nfgs:
            if nfg.routing_behavior == RoutingBehavior.SEND_VIA:
                # NFG with send-via creates connectivity between send-to segments
                for segment1 in nfg.send_to_segments:
                    for segment2 in nfg.send_to_segments:
                        if segment1 != segment2:
                            # Add bidirectional connection
                            if segment1 in graph:
                                if segment2 not in graph[segment1]:
                                    graph[segment1].append(segment2)

                            if segment2 in graph:
                                if segment1 not in graph[segment2]:
                                    graph[segment2].append(segment1)

        return graph

    async def _find_paths_through_nfgs(
        self,
        source: str,
        destination: str,
        nfgs: List[NetworkFunctionGroup],
        graph: Dict[str, List[str]],
        max_hops: int,
    ) -> List[Dict[str, Any]]:
        """Find all paths through Network Function Groups."""
        paths = []

        # For each NFG, check if it can be used as a hop
        for nfg in nfgs:
            nfg_name = nfg.name
            send_to_segments = nfg.send_to_segments

            # Check if NFG connects source and destination
            if source in send_to_segments and destination in send_to_segments:
                paths.append({"hops": [source, destination], "network_functions": [nfg_name]})

            # Check for multi-hop paths through NFGs (if max_hops allows)
            if max_hops > 2:
                # Find intermediate hops
                for intermediate in graph.get(source, []):
                    if intermediate != destination and intermediate in send_to_segments:
                        # Check if destination can be reached from intermediate
                        if destination in graph.get(intermediate, []):
                            paths.append(
                                {
                                    "hops": [source, intermediate, destination],
                                    "network_functions": [nfg_name],
                                }
                            )

                # Look for longer paths with multiple NFGs (if max_hops allows)
                if max_hops > 3:
                    # Create additional paths with multiple NFGs
                    new_paths = await self._find_multi_nfg_paths(
                        source, destination, nfgs, graph, max_hops - 1
                    )
                    paths.extend(new_paths)

        return paths

    async def _find_multi_nfg_paths(
        self,
        source: str,
        destination: str,
        nfgs: List[NetworkFunctionGroup],
        graph: Dict[str, List[str]],
        max_remaining_hops: int,
    ) -> List[Dict[str, Any]]:
        """Find paths that use multiple Network Function Groups."""
        # This is a simplified implementation that considers paths through at most 2 NFGs
        # A full implementation would use graph traversal algorithms like BFS or DFS
        paths = []

        # Skip if max hops is too low
        if max_remaining_hops < 2:
            return paths

        # For each pair of NFGs
        for i, nfg1 in enumerate(nfgs):
            nfg1_name = nfg1.name
            nfg1_segments = nfg1.send_to_segments

            # Skip if source isn't in segments
            if source not in nfg1_segments:
                continue

            for nfg2 in nfgs[i + 1 :]:
                nfg2_name = nfg2.name
                nfg2_segments = nfg2.send_to_segments

                # Skip if destination isn't in segments
                if destination not in nfg2_segments:
                    continue

                # Find common segments between NFGs
                common_segments = set(nfg1_segments) & set(nfg2_segments)

                for middle in common_segments:
                    if middle != source and middle != destination:
                        # We have a path: source -> middle -> destination
                        # through NFG1 and NFG2
                        paths.append(
                            {
                                "hops": [source, middle, destination],
                                "network_functions": [nfg1_name, nfg2_name],
                            }
                        )

        return paths

    async def _calculate_path_latency(self, path: RoutingPath) -> int:
        """Calculate estimated latency for a routing path."""
        # Base latency between segments
        base_latency = len(path.hops) * 5  # 5ms per hop

        # Add NFG processing latency
        nfg_latency = len(path.network_functions) * 10  # 10ms per NFG

        return base_latency + nfg_latency

    async def _get_resource_capacity_info(self, resource_arn: str) -> Dict[str, Any]:
        """Get capacity information for a resource."""
        capacity_info = {}

        try:
            # Extract service and region from ARN
            arn_parts = resource_arn.split(":")
            if len(arn_parts) >= 6:
                service = arn_parts[2]
                region = arn_parts[3]
                resource_type = arn_parts[5].split("/")[0] if "/" in arn_parts[5] else ""

                # For EC2 instance resources
                if service == "ec2" and resource_type == "instance":
                    instance_id = arn_parts[5].split("/")[1] if "/" in arn_parts[5] else ""
                    if instance_id:
                        ec2_client = await self.aws_manager.get_client_async("ec2", region)
                        response = await ec2_client.describe_instances(InstanceIds=[instance_id])

                        if response.get("Reservations") and response["Reservations"][0].get(
                            "Instances"
                        ):
                            instance = response["Reservations"][0]["Instances"][0]
                            instance_type = instance.get("InstanceType", "")

                            # Estimate capacity based on instance type
                            if instance_type.startswith("t3."):
                                capacity_info = {
                                    "max_throughput_gbps": 5,
                                    "max_connections": 100000,
                                    "max_new_connections_per_second": 10000,
                                }
                            elif instance_type.startswith("m5."):
                                capacity_info = {
                                    "max_throughput_gbps": 10,
                                    "max_connections": 200000,
                                    "max_new_connections_per_second": 20000,
                                }
                            elif instance_type.startswith("c5."):
                                capacity_info = {
                                    "max_throughput_gbps": 15,
                                    "max_connections": 300000,
                                    "max_new_connections_per_second": 30000,
                                }
                            else:
                                capacity_info = {
                                    "max_throughput_gbps": 10,
                                    "max_connections": 100000,
                                    "max_new_connections_per_second": 10000,
                                }
        except Exception as e:
            self.logger.warning(f"Failed to get resource capacity info: {e}")
            # Default values if we can't determine capacity
            capacity_info = {
                "max_throughput_gbps": 10,
                "max_connections": 100000,
                "max_new_connections_per_second": 10000,
            }

        return capacity_info

    async def _determine_supported_protocols(
        self,
        core_network_id: str,
        nfg_name: str,
        insertion_points: List[ServiceInsertionPoint],
    ) -> List[str]:
        """Determine supported protocols based on insertion points."""
        # Default supported protocols
        protocols = ["tcp", "udp", "icmp"]

        # Analyze insertion point types to determine supported protocols
        function_types = set(point.function_type for point in insertion_points)

        # Add protocol support based on function types
        for function_type in function_types:
            if function_type == NetworkFunctionType.DLP:
                if "http" not in protocols:
                    protocols.append("http")
                if "https" not in protocols:
                    protocols.append("https")
            elif function_type == NetworkFunctionType.PROXY:
                if "http" not in protocols:
                    protocols.append("http")
                if "https" not in protocols:
                    protocols.append("https")
            elif function_type == NetworkFunctionType.LOAD_BALANCER:
                if "http" not in protocols:
                    protocols.append("http")
                if "https" not in protocols:
                    protocols.append("https")

        return protocols

    def _calculate_aggregate_capacity(
        self, insertion_points: List[ServiceInsertionPoint]
    ) -> Dict[str, Any]:
        """Calculate aggregate processing capacity across insertion points."""
        # Default capacities
        total_throughput = 0
        total_connections = 0
        total_new_connections = 0

        for point in insertion_points:
            # Sum up capacities
            capacity = point.capacity_info
            total_throughput += capacity.get("max_throughput_gbps", 0)
            total_connections += capacity.get("max_connections", 0)
            total_new_connections += capacity.get("max_new_connections_per_second", 0)

        return {
            "max_throughput_gbps": total_throughput,
            "max_connections": total_connections,
            "max_new_connections_per_second": total_new_connections,
        }

    def _calculate_path_cost(self, path: RoutingPath, nfgs: List[NetworkFunctionGroup]) -> float:
        """Calculate cost metric for a routing path."""
        # Base cost by number of hops
        hop_cost = len(path.hops) * 1.0

        # Add NFG processing cost
        nfg_cost = len(path.network_functions) * 2.0

        return hop_cost + nfg_cost

    async def _extract_path_constraints(
        self,
        path: RoutingPath,
        nfgs: List[NetworkFunctionGroup],
        policy_doc: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Extract policy constraints affecting the routing path."""
        constraints = []

        # This would analyze the policy document for constraints
        # that affect this specific path

        return constraints

    async def _evaluate_send_to_policy(self, nfg: NetworkFunctionGroup) -> Dict[str, Any]:
        """Evaluate send-to policy configuration."""
        recommendations = []
        is_valid = len(nfg.send_to_segments) > 0
        segment_types = set()
        segment_locations = set()

        # Check if segments are configured
        if not is_valid:
            recommendations.append(
                "Configure send-to segments to enable traffic routing through the NFG"
            )

        # Analyze segment diversity
        for segment in nfg.send_to_segments:
            # In a real implementation, we'd analyze segment properties
            # For now, we'll just use the segment name as a proxy
            if "shared" in segment.lower():
                segment_types.add("shared")
            elif "prod" in segment.lower() or "production" in segment.lower():
                segment_types.add("production")
            elif "dev" in segment.lower() or "development" in segment.lower():
                segment_types.add("development")
            elif "test" in segment.lower() or "qa" in segment.lower():
                segment_types.add("test")

            # Location analysis would be based on actual segment data
            # For this implementation, we're using placeholder logic
            if "east" in segment.lower():
                segment_locations.add("east")
            elif "west" in segment.lower():
                segment_locations.add("west")
            elif "eu" in segment.lower() or "europe" in segment.lower():
                segment_locations.add("europe")

        # Generate recommendations based on analysis
        if len(segment_types) < 2 and len(nfg.send_to_segments) > 1:
            recommendations.append(
                "Consider adding segments of different types (production, shared, development) for better traffic isolation"
            )

        if len(segment_locations) < 2 and len(nfg.send_to_segments) > 1:
            recommendations.append(
                "Consider adding segments in different regions for geographical redundancy"
            )

        if len(nfg.insertion_points) < len(nfg.send_to_segments):
            recommendations.append(
                "Add more insertion points to handle traffic from all send-to segments"
            )

        return {
            "configured_segments": nfg.send_to_segments,
            "is_valid": is_valid,
            "segment_diversity": {
                "types": list(segment_types),
                "locations": list(segment_locations),
            },
            "recommendations": recommendations,
        }

    async def _evaluate_send_via_policy(self, nfg: NetworkFunctionGroup) -> Dict[str, Any]:
        """Evaluate send-via policy configuration."""
        recommendations = []
        is_configured = nfg.send_via_mode is not None
        is_valid = True
        issues = []

        if not is_configured:
            return {
                "send_via_mode": None,
                "is_configured": False,
                "is_valid": True,  # Not configured is still valid
                "issues": [],
                "recommendations": [
                    "Consider configuring send-via mode for mandatory traffic routing"
                ],
            }

        # Check for valid mode
        valid_modes = ["drop-and-forward", "drop-only"]
        if nfg.send_via_mode not in valid_modes:
            is_valid = False
            issues.append(
                f"Invalid send-via mode: {nfg.send_via_mode}. Valid modes are {', '.join(valid_modes)}"
            )

        # Check for configuration conflicts
        if nfg.send_via_mode and not nfg.send_to_segments:
            is_valid = False
            issues.append("Send-via mode configured but no send-to segments specified")
            recommendations.append("Configure send-to segments to enable traffic routing")

        # Check for insertion points
        if is_configured and not nfg.insertion_points:
            issues.append("No insertion points available for send-via routing")
            recommendations.append(
                "Deploy service insertion points for the NFG to function properly"
            )

        # Generate recommendations
        if nfg.send_via_mode == "drop-and-forward":
            # Check if NFG has sufficient insertion points
            if len(nfg.insertion_points) < 2:
                recommendations.append(
                    "Add multiple insertion points for better redundancy with drop-and-forward mode"
                )

        return {
            "send_via_mode": nfg.send_via_mode,
            "is_configured": is_configured,
            "is_valid": is_valid,
            "issues": issues,
            "recommendations": recommendations,
        }

    async def _detect_policy_conflicts(
        self, nfg: NetworkFunctionGroup, all_nfgs: List[NetworkFunctionGroup]
    ) -> List[Dict[str, Any]]:
        """Detect policy conflicts between NFGs."""
        conflicts = []

        # Check for overlapping send-to segments
        for other_nfg in all_nfgs:
            if other_nfg.name == nfg.name:
                continue

            overlapping_segments = set(nfg.send_to_segments) & set(other_nfg.send_to_segments)
            if overlapping_segments:
                # Only consider it a conflict if both NFGs have send-via
                # or if both have the same function type
                if (
                    nfg.routing_behavior == RoutingBehavior.SEND_VIA
                    and other_nfg.routing_behavior == RoutingBehavior.SEND_VIA
                ):
                    conflicts.append(
                        {
                            "type": "overlapping_send_via_segments",
                            "severity": "high",
                            "conflicting_nfg": other_nfg.name,
                            "overlapping_segments": list(overlapping_segments),
                            "description": "Multiple NFGs with send-via behavior targeting the same segments",
                        }
                    )
                elif nfg.function_type == other_nfg.function_type:
                    conflicts.append(
                        {
                            "type": "duplicate_function_type",
                            "severity": "medium",
                            "conflicting_nfg": other_nfg.name,
                            "overlapping_segments": list(overlapping_segments),
                            "description": f"Multiple NFGs of type {nfg.function_type} targeting the same segments",
                        }
                    )
                else:
                    # Potential conflict but lower severity
                    conflicts.append(
                        {
                            "type": "overlapping_send_to_segments",
                            "severity": "low",
                            "conflicting_nfg": other_nfg.name,
                            "overlapping_segments": list(overlapping_segments),
                            "description": "Multiple NFGs targeting the same segments",
                        }
                    )

        # Check for send-via chains (one NFG sending to another's segments)
        if nfg.routing_behavior == RoutingBehavior.SEND_VIA:
            for other_nfg in all_nfgs:
                if other_nfg.name == nfg.name:
                    continue

                # Check if this NFG's send-to segments include another NFG's send-to segments
                # but not all of them (partial overlap) - could create routing loops
                other_segments = set(other_nfg.send_to_segments)
                this_segments = set(nfg.send_to_segments)

                if (
                    other_segments
                    and this_segments
                    and other_segments < this_segments
                    and other_nfg.routing_behavior == RoutingBehavior.SEND_VIA
                ):
                    conflicts.append(
                        {
                            "type": "potential_routing_loop",
                            "severity": "high",
                            "conflicting_nfg": other_nfg.name,
                            "description": "Potential routing loop through multiple NFGs with send-via behavior",
                        }
                    )

        return conflicts

    async def _generate_policy_recommendations(self, nfg: NetworkFunctionGroup) -> List[str]:
        """Generate policy optimization recommendations."""
        recommendations = []

        # Basic configuration recommendations
        if not nfg.send_to_segments and not nfg.send_via_mode:
            recommendations.append(
                "Configure either send-to segments or send-via mode for proper traffic routing"
            )

        if nfg.configuration_errors:
            recommendations.append("Resolve configuration errors to ensure proper NFG operation")

        if not nfg.insertion_points:
            recommendations.append(
                "Deploy service insertion points to enable network function processing"
            )

        # Function-specific recommendations
        if nfg.function_type == NetworkFunctionType.FIREWALL:
            recommendations.append(
                "Ensure firewall rules are properly configured in your NFG routing rules"
            )

            # Check if NFG has any routing rules
            if len(nfg.routing_rules) < 1:
                recommendations.append(
                    "Add specific routing rules to control traffic through your firewall NFG"
                )

        elif nfg.function_type == NetworkFunctionType.INSPECTION:
            if nfg.routing_behavior != RoutingBehavior.SEND_VIA:
                recommendations.append(
                    "Consider using send-via mode for mandatory traffic inspection"
                )

        elif nfg.function_type == NetworkFunctionType.IDS_IPS:
            # Check insertion points for IDS/IPS
            if nfg.insertion_points:
                inline_points = [p for p in nfg.insertion_points if p.insertion_mode == "inline"]
                tap_points = [p for p in nfg.insertion_points if p.insertion_mode == "tap"]

                if not inline_points and not tap_points:
                    recommendations.append(
                        "Configure insertion points with proper mode (inline or tap) for IDS/IPS"
                    )

        # Performance recommendations
        if nfg.insertion_points and len(nfg.insertion_points) < 2:
            recommendations.append(
                "Add multiple insertion points for better redundancy and performance"
            )

        # Segment recommendations
        if len(nfg.send_to_segments) > 3 and nfg.routing_behavior == RoutingBehavior.SEND_VIA:
            recommendations.append(
                "Consider separating NFG policies for better organization and reduced complexity"
            )

        return recommendations

    async def _get_networkmanager_client(self):
        """Get NetworkManager client with custom endpoint support."""
        region = "us-west-2"  # NetworkManager is a global service
        client = await self.aws_manager.get_client_async("networkmanager", region)

        if self.custom_nm_endpoint:
            # For async wrapped clients, modify the underlying client's endpoint
            if hasattr(client, '_client'):
                client._client._endpoint.host = self.custom_nm_endpoint.replace("https://", "").replace(
                    "http://", ""
                )
            else:
                client._endpoint.host = self.custom_nm_endpoint.replace("https://", "").replace(
                    "http://", ""
                )

        return client
