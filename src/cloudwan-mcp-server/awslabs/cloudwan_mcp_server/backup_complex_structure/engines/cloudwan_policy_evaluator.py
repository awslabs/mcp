"""
CloudWAN Policy Evaluator Engine.

This engine provides comprehensive CloudWAN policy evaluation and analysis capabilities,
including policy document parsing, segment isolation rule evaluation, Network Function
Group analysis, and routing policy validation.

Features:
- CloudWAN policy document parsing and validation
- Segment isolation and routing rule evaluation
- Network Function Group send-to/send-via analysis
- Policy routing edge discovery for path tracing
- Policy conflict detection and resolution recommendations
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from botocore.exceptions import ClientError

from ..aws.client_manager import AWSClientManager
from ..config import CloudWANConfig
from .async_executor_bridge import AsyncExecutorBridge


class PolicyAction(str, Enum):
    """CloudWAN policy actions."""

    ALLOW = "allow"
    DENY = "deny"
    INSPECT = "inspect"
    REDIRECT = "redirect"


class AttachmentType(str, Enum):
    """CloudWAN attachment types for policy evaluation."""

    VPC = "vpc"
    VPN = "vpn"
    CONNECT = "connect"
    DIRECT_CONNECT_GATEWAY = "direct-connect-gateway"


@dataclass
class PolicySegment:
    """CloudWAN policy segment definition."""

    name: str
    description: Optional[str] = None
    edge_locations: List[str] = field(default_factory=list)
    require_attachment_acceptance: bool = False
    isolate_attachments: bool = False
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class PolicyRule:
    """CloudWAN policy rule definition."""

    rule_number: int
    description: Optional[str] = None
    source: Optional[str] = None
    destination: Optional[str] = None
    action: PolicyAction = PolicyAction.ALLOW
    protocol: Optional[str] = None
    destination_port: Optional[str] = None


@dataclass
class NetworkFunctionGroup:
    """Network Function Group definition."""

    name: str
    description: Optional[str] = None
    require_attachment_acceptance: bool = False
    edge_locations: List[str] = field(default_factory=list)
    send_to: List[str] = field(default_factory=list)
    send_via: List[str] = field(default_factory=list)


@dataclass
class PolicyEvaluationResult:
    """Result of policy evaluation."""

    policy_document_id: str
    core_network_id: str
    segments: List[PolicySegment] = field(default_factory=list)
    network_function_groups: List[NetworkFunctionGroup] = field(default_factory=list)
    routing_rules: List[PolicyRule] = field(default_factory=list)
    segment_actions: Dict[str, List[PolicyRule]] = field(default_factory=dict)
    policy_conflicts: List[str] = field(default_factory=list)
    evaluation_warnings: List[str] = field(default_factory=list)


class CloudWANPolicyEvaluator:
    """
    CloudWAN policy evaluator engine.

    Provides comprehensive policy document analysis, segment isolation evaluation,
    Network Function Group processing, and routing policy validation for CloudWAN networks.
    """

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig):
        """
        Initialize the CloudWAN policy evaluator.

        Args:
            aws_manager: AWS client manager instance
            config: CloudWAN configuration
        """
        self.aws_manager = aws_manager
        self.config = config
        self.legacy_adapter = AsyncExecutorBridge(aws_manager, config)

        # Caching for performance
        self._policy_cache: Dict[str, Tuple[Dict[str, Any], datetime]] = {}
        self._evaluation_cache: Dict[str, Tuple[PolicyEvaluationResult, datetime]] = {}
        self._cache_ttl = timedelta(minutes=15)

    async def get_core_network_policy(self, core_network_id: str) -> Dict[str, Any]:
        """
        Get the policy document for a Core Network.

        Args:
            core_network_id: Core Network ID

        Returns:
            Policy document as dictionary
        """
        cache_key = f"policy:{core_network_id}"

        # Check cache first
        if cache_key in self._policy_cache:
            cached_policy, cached_time = self._policy_cache[cache_key]
            if datetime.now() - cached_time < self._cache_ttl:
                return cached_policy

        try:
            networkmanager_client = await self.aws_manager.get_client("networkmanager", "us-west-2")

            # Get Core Network policy
            response = await networkmanager_client.get_core_network_policy(
                CoreNetworkId=core_network_id
            )

            policy_doc = response.get("CoreNetworkPolicy", {}).get("PolicyDocument")
            if policy_doc:
                # Parse JSON policy document
                parsed_policy = json.loads(policy_doc)

                # Cache the result
                self._policy_cache[cache_key] = (parsed_policy, datetime.now())

                return parsed_policy

            return {}

        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in [
                "ResourceNotFoundException",
                "AccessDenied",
            ]:
                return {}
            raise

    async def evaluate_policy(self, core_network_id: str) -> PolicyEvaluationResult:
        """
        Evaluate CloudWAN policy for comprehensive analysis.

        Args:
            core_network_id: Core Network ID

        Returns:
            Policy evaluation result
        """
        cache_key = f"evaluation:{core_network_id}"

        # Check cache first
        if cache_key in self._evaluation_cache:
            cached_result, cached_time = self._evaluation_cache[cache_key]
            if datetime.now() - cached_time < self._cache_ttl:
                return cached_result

        try:
            # Get policy document
            policy_doc = await self.get_core_network_policy(core_network_id)

            if not policy_doc:
                return PolicyEvaluationResult(
                    policy_document_id="none",
                    core_network_id=core_network_id,
                    evaluation_warnings=["No policy document found"],
                )

            # Parse policy components
            result = PolicyEvaluationResult(
                policy_document_id=policy_doc.get("version", "unknown"),
                core_network_id=core_network_id,
            )

            # Parse segments
            segments = policy_doc.get("segments", [])
            for segment_def in segments:
                segment = PolicySegment(
                    name=segment_def.get("name", ""),
                    description=segment_def.get("description"),
                    edge_locations=segment_def.get("edge-locations", []),
                    require_attachment_acceptance=segment_def.get(
                        "require-attachment-acceptance", False
                    ),
                    isolate_attachments=segment_def.get("isolate-attachments", False),
                )
                result.segments.append(segment)

            # Parse Network Function Groups
            nfgs = policy_doc.get("network-function-groups", [])
            for nfg_def in nfgs:
                nfg = NetworkFunctionGroup(
                    name=nfg_def.get("name", ""),
                    description=nfg_def.get("description"),
                    require_attachment_acceptance=nfg_def.get(
                        "require-attachment-acceptance", False
                    ),
                    edge_locations=nfg_def.get("edge-locations", []),
                    send_to=nfg_def.get("send-to", []),
                    send_via=nfg_def.get("send-via", []),
                )
                result.network_function_groups.append(nfg)

            # Parse segment actions (routing rules)
            segment_actions = policy_doc.get("segment-actions", [])
            for action_def in segment_actions:
                segment = action_def.get("segment", "")
                action_rules = action_def.get("action", {})

                rules = []
                if "send-to" in action_rules:
                    for i, send_to in enumerate(action_rules["send-to"]):
                        rule = PolicyRule(
                            rule_number=i + 1,
                            description=f"Send to {send_to}",
                            destination=send_to,
                            action=PolicyAction.ALLOW,
                        )
                        rules.append(rule)

                if "send-via" in action_rules:
                    for i, send_via in enumerate(action_rules["send-via"]):
                        rule = PolicyRule(
                            rule_number=len(rules) + i + 1,
                            description=f"Send via {send_via}",
                            destination=send_via,
                            action=PolicyAction.INSPECT,
                        )
                        rules.append(rule)

                result.segment_actions[segment] = rules
                result.routing_rules.extend(rules)

            # Detect policy conflicts
            result.policy_conflicts = await self._detect_policy_conflicts(result)

            # Cache the result
            self._evaluation_cache[cache_key] = (result, datetime.now())

            return result

        except Exception as e:
            return PolicyEvaluationResult(
                policy_document_id="error",
                core_network_id=core_network_id,
                evaluation_warnings=[f"Policy evaluation failed: {str(e)}"],
            )

    async def get_policy_routing_edges(self) -> List[Dict[str, Any]]:
        """
        Get routing edges from CloudWAN policies for path tracing.

        Returns:
            List of routing edges with source, destination, and policy info
        """
        routing_edges = []

        try:
            # Get all Core Networks
            networkmanager_client = await self.aws_manager.get_client("networkmanager", "us-west-2")

            # List Global Networks first
            gn_response = await networkmanager_client.list_global_networks()
            global_networks = gn_response.get("GlobalNetworks", [])

            for gn in global_networks:
                gn_id = gn["GlobalNetworkId"]

                # Get Core Networks for this Global Network
                cn_response = await networkmanager_client.list_core_networks(GlobalNetworkId=gn_id)

                for cn in cn_response.get("CoreNetworks", []):
                    cn_id = cn["CoreNetworkId"]

                    # Evaluate policy for this Core Network
                    policy_eval = await self.evaluate_policy(cn_id)

                    # Create routing edges from segment actions
                    for segment, rules in policy_eval.segment_actions.items():
                        source_node_id = f"{cn_id}-{segment}"

                        for rule in rules:
                            if rule.destination:
                                dest_node_id = f"{cn_id}-{rule.destination}"

                                edge = {
                                    "source": source_node_id,
                                    "destination": dest_node_id,
                                    "policy_id": f"{cn_id}-policy-{rule.rule_number}",
                                    "core_network_id": cn_id,
                                    "rule_type": rule.action.value,
                                    "description": rule.description,
                                }
                                routing_edges.append(edge)

            return routing_edges

        except Exception:
            return []  # Return empty list on error

    async def analyze_path_policies(
        self, path_nodes: List[Any], path_edges: List[Any]
    ) -> Dict[str, Any]:
        """
        Analyze CloudWAN policies affecting a specific path.

        Args:
            path_nodes: List of path nodes
            path_edges: List of path edges

        Returns:
            Policy analysis results
        """
        analysis = {
            "isolation_rules": [],
            "nfg_rules": [],
            "policy_violations": [],
            "path_allowed": True,
        }

        try:
            # Find CloudWAN nodes in the path
            cloudwan_nodes = [
                node
                for node in path_nodes
                if hasattr(node, "node_type")
                and node.node_type in ["cloudwan_core", "cloudwan_segment"]
            ]

            if not cloudwan_nodes:
                return analysis

            # Group nodes by Core Network
            core_networks = {}
            for node in cloudwan_nodes:
                if hasattr(node, "metadata") and "core_network_id" in node.metadata:
                    cn_id = node.metadata["core_network_id"]
                    if cn_id not in core_networks:
                        core_networks[cn_id] = []
                    core_networks[cn_id].append(node)

            # Analyze policies for each Core Network
            for cn_id, nodes in core_networks.items():
                policy_eval = await self.evaluate_policy(cn_id)

                # Check segment isolation rules
                for segment in policy_eval.segments:
                    if segment.isolate_attachments:
                        analysis["isolation_rules"].append(
                            f"Segment {segment.name} has attachment isolation enabled"
                        )

                # Check Network Function Group rules
                for nfg in policy_eval.network_function_groups:
                    if nfg.send_to or nfg.send_via:
                        analysis["nfg_rules"].append(f"NFG {nfg.name} has routing overrides")

            return analysis

        except Exception as e:
            analysis["policy_violations"].append(f"Policy analysis failed: {str(e)}")
            return analysis

    async def _detect_policy_conflicts(self, policy_result: PolicyEvaluationResult) -> List[str]:
        """
        Detect conflicts in CloudWAN policy configuration.

        Args:
            policy_result: Policy evaluation result

        Returns:
            List of detected conflicts
        """
        conflicts = []

        # Check for segment name conflicts
        segment_names = [seg.name for seg in policy_result.segments]
        if len(segment_names) != len(set(segment_names)):
            conflicts.append("Duplicate segment names detected")

        # Check for Network Function Group conflicts
        nfg_names = [nfg.name for nfg in policy_result.network_function_groups]
        if len(nfg_names) != len(set(nfg_names)):
            conflicts.append("Duplicate Network Function Group names detected")

        # Check for conflicting routing rules
        for segment, rules in policy_result.segment_actions.items():
            destinations = [rule.destination for rule in rules if rule.destination]
            if len(destinations) != len(set(destinations)):
                conflicts.append(f"Conflicting routing rules in segment {segment}")

        # Check for isolated segments with routing rules
        for segment in policy_result.segments:
            if segment.isolate_attachments and segment.name in policy_result.segment_actions:
                conflicts.append(f"Isolated segment {segment.name} has routing rules")

        return conflicts

    async def validate_policy_syntax(self, policy_document: Dict[str, Any]) -> List[str]:
        """
        Validate CloudWAN policy document syntax.

        Args:
            policy_document: Policy document to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Check required fields
        if "version" not in policy_document:
            errors.append("Missing required field: version")

        if "core-network-configuration" not in policy_document:
            errors.append("Missing required field: core-network-configuration")

        # Validate segments
        segments = policy_document.get("segments", [])
        for i, segment in enumerate(segments):
            if "name" not in segment:
                errors.append(f"Segment {i}: Missing required field: name")

            if "edge-locations" not in segment:
                errors.append(f"Segment {i}: Missing required field: edge-locations")

        # Validate Network Function Groups
        nfgs = policy_document.get("network-function-groups", [])
        for i, nfg in enumerate(nfgs):
            if "name" not in nfg:
                errors.append(f"Network Function Group {i}: Missing required field: name")

        # Validate segment actions
        segment_actions = policy_document.get("segment-actions", [])
        segment_names = {seg.get("name") for seg in segments}

        for i, action in enumerate(segment_actions):
            if "segment" not in action:
                errors.append(f"Segment action {i}: Missing required field: segment")
            elif action["segment"] not in segment_names:
                errors.append(
                    f"Segment action {i}: References unknown segment: {action['segment']}"
                )

        return errors

    async def cleanup(self):
        """Cleanup resources."""
        self._policy_cache.clear()
        self._evaluation_cache.clear()
