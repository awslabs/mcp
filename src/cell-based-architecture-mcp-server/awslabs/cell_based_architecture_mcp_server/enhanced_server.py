# Enhanced server with CICD and observability content
import json
from typing import List, Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import Field

# Enhanced MCP server with CICD pipeline content
enhanced_mcp = FastMCP(
    'awslabs-cell-based-architecture-mcp-server-enhanced',
    instructions="""
# Enhanced Cell-Based Architecture MCP Server

Provides expert guidance on cell-based architecture with enhanced CICD pipeline and observability content.

## New Features
- CICD pipeline guidance for cell-based deployments
- Enhanced observability with cell-aware instrumentation
- Deployment checklist and best practices
- Fault isolation boundary alignment
""")

@enhanced_mcp.tool(name='get-cicd-guidance')
async def get_cicd_guidance(
    deployment_type: Literal['single-az', 'multi-az', 'serverless', 'kubernetes'] = Field(
        ...,
        description='Type of deployment architecture (single-az, multi-az, serverless, kubernetes)'
    ),
    stage: Literal['planning', 'implementation', 'monitoring'] = Field(
        default='implementation',
        description='CICD pipeline stage to focus on'
    )
) -> str:
    """Get CICD pipeline guidance for cell-based architecture deployments."""
    
    response = f"# CICD Pipeline Guidance for {deployment_type.title()} Architecture\n\n"
    
    if deployment_type == 'single-az':
        response += """## Single-AZ Deployment Strategy
- Deploy cell by cell within the AZ
- Monitor cell health between deployments
- Automatic rollback on failure detection
- Fault isolation boundary: Individual cell

### Wave-Based Deployment
```
Wave 1: 1 cell (canary) → Bake time → Monitor
Wave 2: 10% of cells → Bake time → Monitor
Wave 3: 50% of cells → Bake time → Monitor
Wave 4: Remaining cells → Final validation
```
"""
    
    elif deployment_type == 'multi-az':
        response += """## Multi-AZ Deployment Strategy
- Coordinate deployment across AZs
- Maintain AZ independence during deployment
- Cross-AZ health validation
- Fault isolation boundary: Cell + AZ

### AZ-Aware Deployment
- Deploy to one AZ first, validate
- Gradual rollout to additional AZs
- Monitor cross-AZ latency during deployment
- Ensure AZ independence is maintained
"""
    
    elif deployment_type == 'serverless':
        response += """## Serverless Deployment Strategy
- Lambda function versioning per cell
- API Gateway stage management per cell
- DynamoDB zero-downtime updates
- Event-driven deployment triggers

### Serverless-Specific Considerations
- Use Lambda aliases for traffic shifting
- Implement gradual rollout with weighted routing
- Monitor cold start impacts during deployment
- Coordinate function and API Gateway deployments
"""
    
    elif deployment_type == 'kubernetes':
        response += """## Kubernetes (EKS) Deployment Strategy
- Namespace-based cell isolation
- Rolling updates with pod disruption budgets
- Service mesh traffic management
- Helm chart per cell deployment

### K8s-Specific Pipeline
- Use separate namespaces per cell
- Implement canary deployments with Flagger/Argo
- Monitor pod health and resource usage
- Coordinate service mesh configuration updates
"""
    
    if stage == 'monitoring':
        response += """
## Observability During Deployment

### Cell-Aware Monitoring
- Include cell_id in all deployment logs
- Monitor per-cell error rates and latency
- Set up deployment-specific alarms
- Track deployment progress across cells

### Key Metrics to Monitor
- Deployment success rate per cell
- Error rate changes during deployment
- Latency impact during rollout
- Resource utilization changes
"""
    
    return response

@enhanced_mcp.tool(name='validate-observability-setup')
async def validate_observability_setup(
    current_setup: str = Field(
        ...,
        description='Description of current observability setup to validate'
    ),
    focus_areas: List[str] = Field(
        default_factory=list,
        description='Specific areas to focus validation on (e.g., ["logging", "metrics", "alerting"])'
    )
) -> str:
    """Validate observability setup against cell-based architecture requirements."""
    
    response = "# Observability Setup Validation\n\n"
    
    validation_results = []
    
    # Check for cell-aware instrumentation
    if 'cell_id' in current_setup.lower():
        validation_results.append("✅ Cell ID instrumentation detected")
    else:
        validation_results.append("❌ Missing cell_id in observability events")
    
    # Check for hierarchical alerting
    if 'hierarchical' in current_setup.lower() or 'cell-level' in current_setup.lower():
        validation_results.append("✅ Hierarchical alerting mentioned")
    else:
        validation_results.append("❌ No hierarchical alerting strategy detected")
    
    # Check for distributed tracing
    if any(term in current_setup.lower() for term in ['tracing', 'x-ray', 'jaeger']):
        validation_results.append("✅ Distributed tracing implementation found")
    else:
        validation_results.append("❌ Distributed tracing not clearly implemented")
    
    # Check for CloudWatch EMF
    if 'emf' in current_setup.lower() or 'embedded metric' in current_setup.lower():
        validation_results.append("✅ CloudWatch EMF format detected")
    else:
        validation_results.append("❌ Consider using CloudWatch EMF for structured metrics")
    
    response += "## Validation Results\n\n"
    for result in validation_results:
        response += f"{result}\n"
    
    response += "\n## Recommendations\n\n"
    
    if focus_areas:
        for area in focus_areas:
            if area.lower() == 'logging':
                response += """### Logging Recommendations
- Implement structured logging with cell_id
- Use consistent log format across all services
- Include availability_zone and region in logs
- Set up centralized log aggregation with cell filtering
"""
            elif area.lower() == 'metrics':
                response += """### Metrics Recommendations  
- Use CloudWatch EMF format with cell dimensions
- Implement per-cell and per-customer metrics
- Set up cross-AZ latency monitoring
- Create cell capacity and health metrics
"""
            elif area.lower() == 'alerting':
                response += """### Alerting Recommendations
- Implement cell-level alarms (error rate, latency)
- Set up zone-level aggregated alarms
- Create customer-specific alerting
- Establish deployment pipeline alarms
"""
    
    return response

@enhanced_mcp.resource(uri='resource://deployment-checklist', name='DeploymentChecklist', mime_type='application/json')
async def deployment_checklist() -> str:
    """Comprehensive deployment and observability checklist for cell-based architecture."""
    
    checklist = {
        "title": "Cell-Based Architecture Deployment Checklist",
        "deployment_questions": {
            "fault_isolation_alignment": {
                "question": "Is your deployment model aligned with your fault isolation boundaries?",
                "best_practice": "Deploy to cells as independent units without affecting other cells",
                "validation": "Can deploy to US-East cell without impacting US-West cells"
            },
            "gradual_deployment": {
                "question": "Can you deploy changes gradually cell by cell?",
                "best_practice": "Implement wave-based deployment: 1 cell → 10% → 50% → remaining",
                "validation": "Monitor 24-48 hours between waves"
            },
            "automatic_rollback": {
                "question": "Can you automatically rollback changes that cause failures?",
                "best_practice": "Rollback when error rates > 1% or latency increases > 20%",
                "validation": "Automated rollback triggers are configured and tested"
            }
        },
        "observability_questions": {
            "boundary_alignment": {
                "question": "Is observability aligned with fault isolation boundaries?",
                "best_practice": "Include cell_id, availability_zone, region in all events",
                "validation": "All logs, metrics, traces contain cell context"
            },
            "cell_health_monitoring": {
                "question": "Can you monitor operational health of a single cell?",
                "best_practice": "Real-time cell health indicators and drill-down capabilities",
                "validation": "Cell-specific dashboards and alerting exist"
            },
            "hierarchical_alerting": {
                "question": "Do you have cell-level and zone-level alarms?",
                "best_practice": "Cell alarms for individual issues, zone alarms for systemic problems",
                "validation": "Both cell and zone level alerting configured"
            }
        },
        "implementation_priorities": [
            "Phase 1: Cell-aware logging and basic monitoring",
            "Phase 2: Hierarchical alerting and distributed tracing", 
            "Phase 3: Automated rollback and cell balancing",
            "Phase 4: Advanced analytics and optimization"
        ]
    }
    
    return json.dumps(checklist, indent=2)

# Export the enhanced server
def get_enhanced_server():
    return enhanced_mcp