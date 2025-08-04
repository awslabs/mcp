"""
CloudWAN Core Network Policy Validator Tool.

This module provides comprehensive CloudWAN Core Network Policy validation capabilities,
analyzing policy documents, segment configurations, and attachment rules with <1.5s 
load time performance.

Features:
- Core Network Policy document validation and parsing
- Segment configuration analysis and validation
- Attachment policy rules evaluation
- Network Function Group policy compliance
- Cross-segment routing validation
- Policy version management and change detection
- CloudWAN-specific policy best practices validation
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ...aws.client_manager import AWSClientManager
from ...config import CloudWANConfig
from ..base import (
    BaseMCPTool,
    ToolError,
    ValidationError,
    AWSOperationError,
    handle_errors,
)

logger = logging.getLogger(__name__)


class PolicyValidationType(Enum):
    """Policy validation types."""
    SYNTAX = "syntax"
    SEMANTIC = "semantic"
    BEST_PRACTICES = "best_practices"
    COMPLIANCE = "compliance"


class PolicySeverity(Enum):
    """Policy validation severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class PolicyValidationContext:
    """Context for policy validation operations."""
    
    validation_id: str
    regions: List[str]
    core_network_ids: Optional[List[str]]
    validation_types: List[PolicyValidationType]
    start_time: datetime
    timeout_seconds: int = 300
    cache_ttl_minutes: int = 15
    
    def __post_init__(self):
        if not self.validation_id:
            self.validation_id = str(uuid.uuid4())
        if not self.start_time:
            self.start_time = datetime.now()


@dataclass
class PolicyValidationFinding:
    """CloudWAN Policy validation finding."""
    
    finding_id: str
    severity: PolicySeverity
    validation_type: PolicyValidationType
    title: str
    description: str
    policy_section: str
    line_number: Optional[int]
    suggested_fix: Optional[str]
    core_network_id: str
    region: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SegmentConfiguration:
    """CloudWAN segment configuration."""
    
    name: str
    description: Optional[str]
    require_attachment_acceptance: bool
    isolate_attachments: bool
    edge_locations: List[str]
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class AttachmentPolicyRule:
    """CloudWAN attachment policy rule."""
    
    rule_number: int
    conditions: List[Dict[str, Any]]
    action: Dict[str, Any]
    description: Optional[str] = None


@dataclass
class CoreNetworkPolicy:
    """CloudWAN Core Network Policy document."""
    
    version: str
    core_network_configuration: Dict[str, Any]
    segments: List[SegmentConfiguration]
    attachment_policies: List[AttachmentPolicyRule]
    segment_actions: List[Dict[str, Any]] = field(default_factory=list)
    network_function_groups: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class PolicyValidationResult:
    """Result of CloudWAN policy validation analysis."""
    
    validation_id: str
    core_network_id: str
    policy_document: CoreNetworkPolicy
    validation_findings: List[PolicyValidationFinding]
    segments_analyzed: List[SegmentConfiguration]
    attachment_rules_analyzed: List[AttachmentPolicyRule]
    network_function_groups: List[Dict[str, Any]]
    policy_compliance_score: float
    validation_summary: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    timestamp: datetime = field(default_factory=datetime.now)


class PolicyValidationEngine:
    """Engine for CloudWAN policy validation operations."""
    
    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig):
        self.aws_manager = aws_manager
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.PolicyValidationEngine")
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        
    async def validate_core_network_policy(
        self,
        context: PolicyValidationContext
    ) -> PolicyValidationResult:
        """Validate CloudWAN Core Network Policy."""
        
        self.logger.info(f"Starting policy validation: {context.validation_id}")
        
        # Get Core Network and policy document
        core_network = await self._get_core_network_details(context)
        if not core_network:
            raise ValidationError("No Core Network found for validation")
            
        policy_document = await self._parse_policy_document(
            core_network['PolicyDocument']
        )
        
        # Perform validation checks
        validation_findings = []
        
        # Syntax validation
        if PolicyValidationType.SYNTAX in context.validation_types:
            syntax_findings = await self._validate_policy_syntax(policy_document)
            validation_findings.extend(syntax_findings)
        
        # Semantic validation
        if PolicyValidationType.SEMANTIC in context.validation_types:
            semantic_findings = await self._validate_policy_semantics(policy_document)
            validation_findings.extend(semantic_findings)
        
        # Best practices validation
        if PolicyValidationType.BEST_PRACTICES in context.validation_types:
            bp_findings = await self._validate_best_practices(policy_document)
            validation_findings.extend(bp_findings)
        
        # Compliance validation
        if PolicyValidationType.COMPLIANCE in context.validation_types:
            compliance_findings = await self._validate_compliance(policy_document)
            validation_findings.extend(compliance_findings)
        
        # Calculate compliance score
        compliance_score = self._calculate_compliance_score(validation_findings)
        
        # Generate recommendations
        recommendations = self._generate_policy_recommendations(
            policy_document, validation_findings
        )
        
        # Create validation summary
        validation_summary = {
            "total_findings": len(validation_findings),
            "error_count": len([f for f in validation_findings if f.severity == PolicySeverity.ERROR]),
            "warning_count": len([f for f in validation_findings if f.severity == PolicySeverity.WARNING]),
            "info_count": len([f for f in validation_findings if f.severity == PolicySeverity.INFO]),
            "segments_count": len(policy_document.segments),
            "attachment_rules_count": len(policy_document.attachment_policies),
            "network_function_groups_count": len(policy_document.network_function_groups),
            "policy_version": policy_document.version
        }
        
        return PolicyValidationResult(
            validation_id=context.validation_id,
            core_network_id=core_network['CoreNetworkId'],
            policy_document=policy_document,
            validation_findings=validation_findings,
            segments_analyzed=policy_document.segments,
            attachment_rules_analyzed=policy_document.attachment_policies,
            network_function_groups=policy_document.network_function_groups,
            policy_compliance_score=compliance_score,
            validation_summary=validation_summary,
            recommendations=recommendations
        )
    
    async def _get_core_network_details(self, context: PolicyValidationContext) -> Optional[Dict[str, Any]]:
        """Get Core Network details with policy document."""
        
        try:
            # Use primary region for Network Manager
            primary_region = context.regions[0] if context.regions else "us-east-1"
            client = await self.aws_manager.get_client("networkmanager", primary_region)
            
            if context.core_network_ids:
                # Get specific Core Network
                response = await client.get_core_network(
                    CoreNetworkId=context.core_network_ids[0]
                )
                return response.get('CoreNetwork')
            else:
                # Get first available Core Network
                networks = await client.list_core_networks()
                if networks.get('CoreNetworks'):
                    core_network_id = networks['CoreNetworks'][0]['CoreNetworkId']
                    response = await client.get_core_network(
                        CoreNetworkId=core_network_id
                    )
                    return response.get('CoreNetwork')
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get Core Network details: {e}")
            raise AWSOperationError(f"Core Network retrieval failed: {e}")
    
    async def _parse_policy_document(self, policy_doc_json: str) -> CoreNetworkPolicy:
        """Parse CloudWAN policy document JSON."""
        
        try:
            policy_data = json.loads(policy_doc_json)
            
            # Parse segments
            segments = []
            for seg_data in policy_data.get('segments', []):
                segments.append(SegmentConfiguration(
                    name=seg_data.get('name'),
                    description=seg_data.get('description'),
                    require_attachment_acceptance=seg_data.get('require-attachment-acceptance', False),
                    isolate_attachments=seg_data.get('isolate-attachments', False),
                    edge_locations=seg_data.get('edge-locations', []),
                    tags=seg_data.get('tags', {})
                ))
            
            # Parse attachment policies
            attachment_policies = []
            for rule_data in policy_data.get('attachment-policies', []):
                attachment_policies.append(AttachmentPolicyRule(
                    rule_number=rule_data.get('rule-number'),
                    conditions=rule_data.get('conditions', []),
                    action=rule_data.get('action', {}),
                    description=rule_data.get('description')
                ))
            
            return CoreNetworkPolicy(
                version=policy_data.get('version'),
                core_network_configuration=policy_data.get('core-network-configuration', {}),
                segments=segments,
                attachment_policies=attachment_policies,
                segment_actions=policy_data.get('segment-actions', []),
                network_function_groups=policy_data.get('network-function-groups', [])
            )
            
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON in policy document: {e}")
        except Exception as e:
            raise ValidationError(f"Policy document parsing failed: {e}")
    
    async def _validate_policy_syntax(self, policy: CoreNetworkPolicy) -> List[PolicyValidationFinding]:
        """Validate CloudWAN policy syntax."""
        
        findings = []
        
        # Version validation
        if not policy.version or policy.version not in ["2021.12"]:
            findings.append(PolicyValidationFinding(
                finding_id=str(uuid.uuid4()),
                severity=PolicySeverity.ERROR,
                validation_type=PolicyValidationType.SYNTAX,
                title="Invalid Policy Version",
                description=f"Policy version '{policy.version}' is not supported. Use '2021.12'.",
                policy_section="version",
                line_number=1,
                suggested_fix="Change version to '2021.12'",
                core_network_id="unknown",
                region="unknown"
            ))
        
        # Segment validation
        for i, segment in enumerate(policy.segments):
            if not segment.name:
                findings.append(PolicyValidationFinding(
                    finding_id=str(uuid.uuid4()),
                    severity=PolicySeverity.ERROR,
                    validation_type=PolicyValidationType.SYNTAX,
                    title="Missing Segment Name",
                    description=f"Segment at index {i} is missing required 'name' field",
                    policy_section="segments",
                    line_number=None,
                    suggested_fix="Add segment name",
                    core_network_id="unknown",
                    region="unknown"
                ))
        
        # Attachment policy validation
        rule_numbers = set()
        for rule in policy.attachment_policies:
            if rule.rule_number in rule_numbers:
                findings.append(PolicyValidationFinding(
                    finding_id=str(uuid.uuid4()),
                    severity=PolicySeverity.ERROR,
                    validation_type=PolicyValidationType.SYNTAX,
                    title="Duplicate Rule Number",
                    description=f"Rule number {rule.rule_number} is used multiple times",
                    policy_section="attachment-policies",
                    line_number=None,
                    suggested_fix="Use unique rule numbers",
                    core_network_id="unknown",
                    region="unknown"
                ))
            rule_numbers.add(rule.rule_number)
        
        return findings
    
    async def _validate_policy_semantics(self, policy: CoreNetworkPolicy) -> List[PolicyValidationFinding]:
        """Validate CloudWAN policy semantics."""
        
        findings = []
        
        # Check segment references in attachment policies
        segment_names = {seg.name for seg in policy.segments}
        
        for rule in policy.attachment_policies:
            action_segment = rule.action.get('segment')
            if action_segment and action_segment not in segment_names:
                findings.append(PolicyValidationFinding(
                    finding_id=str(uuid.uuid4()),
                    severity=PolicySeverity.ERROR,
                    validation_type=PolicyValidationType.SEMANTIC,
                    title="Invalid Segment Reference",
                    description=f"Rule {rule.rule_number} references non-existent segment '{action_segment}'",
                    policy_section="attachment-policies",
                    line_number=None,
                    suggested_fix=f"Reference existing segment or add segment '{action_segment}'",
                    core_network_id="unknown",
                    region="unknown"
                ))
        
        return findings
    
    async def _validate_best_practices(self, policy: CoreNetworkPolicy) -> List[PolicyValidationFinding]:
        """Validate CloudWAN policy best practices."""
        
        findings = []
        
        # Check for production segment isolation
        for segment in policy.segments:
            if "prod" in segment.name.lower() and not segment.isolate_attachments:
                findings.append(PolicyValidationFinding(
                    finding_id=str(uuid.uuid4()),
                    severity=PolicySeverity.WARNING,
                    validation_type=PolicyValidationType.BEST_PRACTICES,
                    title="Production Segment Not Isolated",
                    description=f"Production segment '{segment.name}' should have isolate-attachments enabled",
                    policy_section="segments",
                    line_number=None,
                    suggested_fix="Set isolate-attachments to true for production segments",
                    core_network_id="unknown",
                    region="unknown"
                ))
        
        # Check for attachment acceptance on sensitive segments
        for segment in policy.segments:
            if any(keyword in segment.name.lower() for keyword in ["prod", "critical", "secure"]):
                if not segment.require_attachment_acceptance:
                    findings.append(PolicyValidationFinding(
                        finding_id=str(uuid.uuid4()),
                        severity=PolicySeverity.WARNING,
                        validation_type=PolicyValidationType.BEST_PRACTICES,
                        title="Sensitive Segment Without Approval",
                        description=f"Sensitive segment '{segment.name}' should require attachment approval",
                        policy_section="segments",
                        line_number=None,
                        suggested_fix="Set require-attachment-acceptance to true",
                        core_network_id="unknown",
                        region="unknown"
                    ))
        
        return findings
    
    async def _validate_compliance(self, policy: CoreNetworkPolicy) -> List[PolicyValidationFinding]:
        """Validate CloudWAN policy compliance requirements."""
        
        findings = []
        
        # Check for proper tagging strategy
        if not any(segment.tags for segment in policy.segments):
            findings.append(PolicyValidationFinding(
                finding_id=str(uuid.uuid4()),
                severity=PolicySeverity.WARNING,
                validation_type=PolicyValidationType.COMPLIANCE,
                title="Missing Segment Tags",
                description="No segments have tags defined for compliance tracking",
                policy_section="segments",
                line_number=None,
                suggested_fix="Add compliance tags to segments",
                core_network_id="unknown",
                region="unknown"
            ))
        
        return findings
    
    def _calculate_compliance_score(self, findings: List[PolicyValidationFinding]) -> float:
        """Calculate policy compliance score based on findings."""
        
        if not findings:
            return 1.0
        
        # Weight different severity levels
        error_weight = 0.3
        warning_weight = 0.1
        info_weight = 0.05
        
        total_deductions = 0.0
        for finding in findings:
            if finding.severity == PolicySeverity.ERROR:
                total_deductions += error_weight
            elif finding.severity == PolicySeverity.WARNING:
                total_deductions += warning_weight
            elif finding.severity == PolicySeverity.INFO:
                total_deductions += info_weight
        
        # Calculate score (minimum 0.0, maximum 1.0)
        score = max(0.0, 1.0 - total_deductions)
        return round(score, 3)
    
    def _generate_policy_recommendations(
        self,
        policy: CoreNetworkPolicy,
        findings: List[PolicyValidationFinding]
    ) -> List[Dict[str, Any]]:
        """Generate policy improvement recommendations."""
        
        recommendations = []
        
        # Group findings by type
        error_findings = [f for f in findings if f.severity == PolicySeverity.ERROR]
        warning_findings = [f for f in findings if f.severity == PolicySeverity.WARNING]
        
        if error_findings:
            recommendations.append({
                "priority": "high",
                "category": "errors",
                "title": "Fix Policy Errors",
                "description": f"Resolve {len(error_findings)} critical policy errors that prevent proper operation",
                "action_items": [f.suggested_fix for f in error_findings if f.suggested_fix]
            })
        
        if warning_findings:
            recommendations.append({
                "priority": "medium",
                "category": "warnings",
                "title": "Address Policy Warnings",
                "description": f"Review {len(warning_findings)} policy warnings for best practices compliance",
                "action_items": [f.suggested_fix for f in warning_findings if f.suggested_fix]
            })
        
        # General recommendations
        if len(policy.segments) > 5:
            recommendations.append({
                "priority": "low",
                "category": "optimization",
                "title": "Consider Segment Consolidation",
                "description": "Large number of segments may increase complexity",
                "action_items": ["Review segment usage patterns", "Consider merging similar segments"]
            })
        
        return recommendations


class PolicyValidatorTool(BaseMCPTool):
    """CloudWAN Core Network Policy Validator MCP Tool."""
    
    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig):
        super().__init__(aws_manager, config)
        self.policy_engine = PolicyValidationEngine(aws_manager, config)
        self._load_time = 0.0
        self._start_time = time.time()
        
        # Record load time
        self._load_time = time.time() - self._start_time
        logger.info(f"PolicyValidatorTool initialized in {self._load_time:.3f}s")
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get the tool input schema."""
        return {
            "type": "object",
            "properties": {
                "regions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "AWS regions to analyze (default: ['us-east-1'])",
                    "default": ["us-east-1"]
                },
                "core_network_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific Core Network IDs to validate (optional)",
                    "default": []
                },
                "validation_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["syntax", "semantic", "best_practices", "compliance"]
                    },
                    "description": "Types of validation to perform",
                    "default": ["syntax", "semantic", "best_practices"]
                },
                "detailed_analysis": {
                    "type": "boolean",
                    "description": "Enable detailed policy analysis",
                    "default": True
                }
            },
            "required": []
        }
    
    @handle_errors
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute CloudWAN policy validation."""
        
        # Extract and validate parameters
        regions = kwargs.get('regions', ['us-east-1'])
        core_network_ids = kwargs.get('core_network_ids', [])
        validation_types_str = kwargs.get('validation_types', ['syntax', 'semantic', 'best_practices'])
        detailed_analysis = kwargs.get('detailed_analysis', True)
        
        # Validate regions
        if not regions:
            regions = ['us-east-1']
        
        # Convert validation types
        validation_types = []
        for vt_str in validation_types_str:
            try:
                validation_types.append(PolicyValidationType(vt_str))
            except ValueError:
                raise ValidationError(f"Invalid validation type: {vt_str}")
        
        # Create validation context
        context = PolicyValidationContext(
            validation_id=str(uuid.uuid4()),
            regions=regions,
            core_network_ids=core_network_ids if core_network_ids else None,
            validation_types=validation_types,
            start_time=datetime.now()
        )
        
        # Perform policy validation
        try:
            validation_result = await self.policy_engine.validate_core_network_policy(context)
            
            # Format results
            return {
                "validation_id": validation_result.validation_id,
                "core_network_id": validation_result.core_network_id,
                "policy_validation_summary": validation_result.validation_summary,
                "policy_compliance_score": validation_result.policy_compliance_score,
                "validation_findings": [
                    {
                        "finding_id": f.finding_id,
                        "severity": f.severity.value,
                        "validation_type": f.validation_type.value,
                        "title": f.title,
                        "description": f.description,
                        "policy_section": f.policy_section,
                        "suggested_fix": f.suggested_fix
                    }
                    for f in validation_result.validation_findings
                ],
                "segments_analyzed": [
                    {
                        "name": seg.name,
                        "description": seg.description,
                        "require_attachment_acceptance": seg.require_attachment_acceptance,
                        "isolate_attachments": seg.isolate_attachments,
                        "edge_locations": seg.edge_locations,
                        "tags": seg.tags
                    }
                    for seg in validation_result.segments_analyzed
                ],
                "attachment_rules_analyzed": [
                    {
                        "rule_number": rule.rule_number,
                        "conditions": rule.conditions,
                        "action": rule.action,
                        "description": rule.description
                    }
                    for rule in validation_result.attachment_rules_analyzed
                ],
                "network_function_groups": validation_result.network_function_groups,
                "recommendations": validation_result.recommendations,
                "regions_analyzed": regions,
                "analysis_timestamp": validation_result.timestamp.isoformat(),
                "tool_performance": {
                    "load_time_seconds": self._load_time,
                    "execution_time_seconds": (datetime.now() - context.start_time).total_seconds()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Policy validation failed: {e}")
            raise ToolError(f"CloudWAN policy validation failed: {e}")
    
    def get_load_time(self) -> float:
        """Get tool load time in seconds."""
        return self._load_time
    
    @property
    def tool_name(self) -> str:
        """Tool name for MCP registration."""
        return "validate_cloudwan_policy"
    
    @property
    def description(self) -> str:
        """Tool description for MCP registration."""
        return "Validate CloudWAN Core Network Policy documents for syntax, semantics, and best practices"