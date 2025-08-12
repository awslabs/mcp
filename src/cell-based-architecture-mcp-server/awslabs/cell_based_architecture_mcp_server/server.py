# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Cell-Based Architecture MCP Server implementation."""

import json
import os
import sys
from typing import List, Literal, Optional

from loguru import logger
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .knowledge import CellBasedArchitectureKnowledge
from .models import CellArchitectureQuery, ImplementationStage, CellDesignAnalysis

# Set up logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

# Initialize MCP server
mcp = FastMCP(
    'awslabs-cell-based-architecture-mcp-server',
    instructions="""
# Cell-Based Architecture MCP Server

This MCP server provides expert guidance on cell-based architecture patterns based on the AWS Well-Architected whitepaper "Reducing the Scope of Impact with Cell-Based Architecture".

## Available Tools

### query-cell-concepts
Query cell-based architecture concepts with progressive complexity levels (beginner → intermediate → expert).

### get-implementation-guidance  
Get stage-specific implementation guidance following the whitepaper's methodology.

### analyze-cell-design
Analyze cell-based architecture designs and provide recommendations.

### validate-architecture
Validate architecture against cell-based architecture principles.

## Available Resources

### cell-architecture-guide
Complete guide to cell-based architecture principles organized by whitepaper sections.

### implementation-patterns
Common implementation patterns and AWS service integration examples.

### best-practices
Best practices and troubleshooting guidance for cell-based architecture.

## Usage Notes

Content is organized following the whitepaper structure for progressive learning:
- **Beginners**: Start with introduction, shared responsibility model, and basic concepts
- **Intermediate**: Focus on implementation guidance and design patterns  
- **Expert**: Access advanced topics like cell sizing, placement, migration, and observability
""",
    dependencies=['pydantic', 'loguru'],
)


@mcp.tool(name='query-cell-concepts')
async def query_cell_concepts(
    concept: str = Field(
        ..., 
        description='The cell-based architecture concept to query (e.g., "cell isolation", "fault tolerance", "blast radius")'
    ),
    detail_level: Literal['beginner', 'intermediate', 'expert'] = Field(
        default='intermediate',
        description='Experience level: beginner (new to cell-based architecture), intermediate (some experience), expert (advanced implementation)'
    ),
    whitepaper_section: Optional[Literal[
        'introduction', 'shared_responsibility', 'what_is_cell_based', 'why_use_cell_based', 
        'when_to_use', 'control_data_plane', 'cell_design', 'cell_partition', 'cell_routing', 
        'cell_sizing', 'cell_placement', 'cell_migration', 'cell_deployment', 
        'cell_observability', 'best_practices', 'faq'
    ]] = Field(
        default=None,
        description='Specific whitepaper section to focus the response on'
    ),
) -> str:
    """Query cell-based architecture concepts following the whitepaper structure.
    
    This tool provides explanations of cell-based architecture concepts with content
    organized by the AWS Well-Architected whitepaper structure. Responses are tailored
    to the user's experience level for progressive learning.
    """
    try:
        logger.info(f'Querying concept: {concept}, level: {detail_level}, section: {whitepaper_section}')
        
        # Get relevant section content
        if whitepaper_section:
            section = CellBasedArchitectureKnowledge.get_section(whitepaper_section)
            if section:
                response = f"## {section.title}\n\n{section.content}"
                if section.subsections:
                    response += f"\n\n### Key Topics:\n" + "\n".join([f"- {sub}" for sub in section.subsections])
                
                # Add related sections for navigation
                related = CellBasedArchitectureKnowledge.get_related_sections(whitepaper_section)
                if related:
                    response += f"\n\n### Related Sections:\n" + "\n".join([f"- {r.title}" for r in related])
                
                return response
        
        # General concept query with level-appropriate content
        if detail_level == 'beginner':
            sections = CellBasedArchitectureKnowledge.get_sections_by_level('beginner')
            response = f"# Cell-Based Architecture: {concept}\n\n"
            response += "## Introduction for Beginners\n\n"
            response += "Cell-based architecture is a resilience pattern that helps build more reliable distributed systems. "
            response += f"Here's what you need to know about {concept}:\n\n"
            
            for section in sections[:2]:  # Limit to first 2 beginner sections
                response += f"### {section.title}\n{section.content}\n\n"
                
        elif detail_level == 'expert':
            sections = CellBasedArchitectureKnowledge.get_sections_by_level('expert')
            response = f"# Advanced Cell-Based Architecture: {concept}\n\n"
            response += "## Expert-Level Implementation Details\n\n"
            
            for section in sections[:3]:  # Show more expert content
                response += f"### {section.title}\n{section.content}\n\n"
                if section.subsections:
                    response += "**Key Implementation Areas:**\n" + "\n".join([f"- {sub}" for sub in section.subsections]) + "\n\n"
        
        else:  # intermediate
            response = f"# Cell-Based Architecture: {concept}\n\n"
            response += "## Intermediate Overview\n\n"
            response += f"Understanding {concept} in the context of cell-based architecture:\n\n"
            
            # Mix of beginner and intermediate content
            intro_section = CellBasedArchitectureKnowledge.get_section('what_is_cell_based')
            why_section = CellBasedArchitectureKnowledge.get_section('why_use_cell_based')
            
            if intro_section:
                response += f"### {intro_section.title}\n{intro_section.content}\n\n"
            if why_section:
                response += f"### {why_section.title}\n{why_section.content}\n\n"
        
        return response
        
    except Exception as e:
        logger.error(f'Error in query_cell_concepts: {str(e)}')
        return f'Error querying cell-based architecture concepts: {str(e)}'


@mcp.tool(name='get-implementation-guidance')
async def get_implementation_guidance(
    stage: Literal['planning', 'design', 'implementation', 'monitoring'] = Field(
        ...,
        description='Implementation stage: planning (initial planning), design (architecture design), implementation (coding/deployment), monitoring (observability)'
    ),
    aws_services: List[str] = Field(
        default_factory=list,
        description='AWS services to consider for implementation (e.g., ["lambda", "dynamodb", "api-gateway"])'
    ),
    experience_level: Literal['beginner', 'intermediate', 'expert'] = Field(
        default='intermediate',
        description='User experience level for tailored guidance'
    ),
) -> str:
    """Get stage-specific implementation guidance following the whitepaper methodology.
    
    Provides implementation guidance organized by the whitepaper's logical flow,
    with content appropriate for the user's experience level.
    """
    try:
        logger.info(f'Getting guidance for stage: {stage}, level: {experience_level}, services: {aws_services}')
        
        response = f"# Cell-Based Architecture Implementation Guidance\n\n"
        response += f"## {stage.title()} Stage ({experience_level} level)\n\n"
        
        if stage == 'planning':
            response += "### Planning Your Cell-Based Architecture\n\n"
            if experience_level == 'beginner':
                response += "Start with understanding the fundamentals:\n\n"
                intro = CellBasedArchitectureKnowledge.get_section('introduction')
                what_is = CellBasedArchitectureKnowledge.get_section('what_is_cell_based')
                if intro:
                    response += f"**{intro.title}**\n{intro.content}\n\n"
                if what_is:
                    response += f"**{what_is.title}**\n{what_is.content}\n\n"
            else:
                when_to_use = CellBasedArchitectureKnowledge.get_section('when_to_use')
                if when_to_use:
                    response += f"{when_to_use.content}\n\n"
                    
        elif stage == 'design':
            design_section = CellBasedArchitectureKnowledge.get_section('cell_design')
            partition_section = CellBasedArchitectureKnowledge.get_section('cell_partition')
            
            if design_section:
                response += f"### {design_section.title}\n{design_section.content}\n\n"
            if partition_section and experience_level != 'beginner':
                response += f"### {partition_section.title}\n{partition_section.content}\n\n"
                
        elif stage == 'implementation':
            deployment_section = CellBasedArchitectureKnowledge.get_section('cell_deployment')
            routing_section = CellBasedArchitectureKnowledge.get_section('cell_routing')
            
            if deployment_section:
                response += f"### {deployment_section.title}\n{deployment_section.content}\n\n"
            if routing_section and experience_level == 'expert':
                response += f"### {routing_section.title}\n{routing_section.content}\n\n"
                
        elif stage == 'monitoring':
            observability_section = CellBasedArchitectureKnowledge.get_section('cell_observability')
            if observability_section:
                response += f"### {observability_section.title}\n{observability_section.content}\n\n"
        
        # Add AWS services recommendations if provided
        if aws_services:
            response += f"### AWS Services Integration\n\n"
            response += f"For the {stage} stage with services {', '.join(aws_services)}:\n\n"
            for service in aws_services:
                response += f"- **{service.upper()}**: Consider how this service fits into your cell boundaries and isolation strategy\n"
        
        return response
        
    except Exception as e:
        logger.error(f'Error in get_implementation_guidance: {str(e)}')
        return f'Error getting implementation guidance: {str(e)}'


@mcp.resource(uri='resource://cell-architecture-guide', name='CellArchitectureGuide', mime_type='application/json')
async def cell_architecture_guide() -> str:
    """Complete guide to cell-based architecture principles organized by whitepaper sections.
    
    This resource provides the complete cell-based architecture guide organized
    following the AWS Well-Architected whitepaper structure for progressive learning.
    """
    try:
        guide = {
            'title': 'Cell-Based Architecture Complete Guide',
            'description': 'Comprehensive guide organized by AWS Well-Architected whitepaper sections',
            'sections': {}
        }
        
        for section_name, section_data in CellBasedArchitectureKnowledge.WHITEPAPER_SECTIONS.items():
            guide['sections'][section_name] = {
                'title': section_data.title,
                'content': section_data.content,
                'complexity_level': section_data.complexity_level,
                'subsections': section_data.subsections,
                'related_sections': section_data.related_sections
            }
        
        return json.dumps(guide, indent=2)
        
    except Exception as e:
        logger.error(f'Error serving cell architecture guide: {str(e)}')
        return json.dumps({'error': f'Error loading guide: {str(e)}'})


def main():
    """Run the MCP server with CLI argument support and environment configuration.
    
    Environment Variables:
    - AWS_REGION: AWS region for service calls (default: us-east-1)
    - AWS_PROFILE: AWS profile to use for authentication
    - FASTMCP_LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)
    
    FastMCP Server Instructions:
    This server provides cell-based architecture guidance following the AWS Well-Architected
    whitepaper structure. Use the tools for interactive queries and resources for comprehensive
    documentation. Content is organized by experience level for progressive learning.
    """
    try:
        # Configure AWS region if not set
        if not os.getenv('AWS_REGION'):
            os.environ['AWS_REGION'] = 'us-east-1'
            logger.info('AWS_REGION not set, defaulting to us-east-1')
        
        # Log configuration info
        aws_region = os.getenv('AWS_REGION')
        aws_profile = os.getenv('AWS_PROFILE', 'default')
        log_level = os.getenv('FASTMCP_LOG_LEVEL', 'WARNING')
        
        logger.info(f'Starting Cell-Based Architecture MCP Server')
        logger.info(f'AWS Region: {aws_region}')
        logger.info(f'AWS Profile: {aws_profile}')
        logger.info(f'Log Level: {log_level}')
        
        # Run the MCP server with graceful shutdown handling
        mcp.run()
        
    except KeyboardInterrupt:
        logger.info('Received shutdown signal, stopping server gracefully')
        sys.exit(0)
    except Exception as e:
        logger.error(f'Server startup failed: {str(e)}')
        sys.exit(1)


if __name__ == '__main__':
    main()

@mcp.tool(name='analyze-cell-design')
async def analyze_cell_design(
    architecture_description: str = Field(
        ...,
        description='Description of the cell-based architecture design to analyze'
    ),
    focus_areas: List[str] = Field(
        default_factory=list,
        description='Specific areas to focus the analysis on (e.g., ["isolation", "scalability", "fault_tolerance"])'
    ),
) -> str:
    """Analyze cell-based architecture designs and provide recommendations."""
    try:
        logger.info(f'Analyzing cell design, focus areas: {focus_areas}')
        
        response = f"# Cell-Based Architecture Design Analysis\n\n"
        response += f"## Architecture Description\n{architecture_description}\n\n"
        
        strengths = []
        recommendations = []
        
        if 'isolation' in architecture_description.lower():
            strengths.append('Design mentions isolation principles')
        else:
            recommendations.append('Define clear cell isolation boundaries')
        
        if 'fault' in architecture_description.lower():
            strengths.append('Considers fault tolerance')
        else:
            recommendations.append('Consider failure scenarios and fault isolation')
        
        compliance_score = 0.7 if len(strengths) > 0 else 0.5
        
        response += f"## Analysis Results\n\n"
        response += f"**Compliance Score:** {compliance_score:.1f}/1.0\n\n"
        
        if strengths:
            response += f"### Strengths\n"
            for strength in strengths:
                response += f"- {strength}\n"
            response += "\n"
        
        if recommendations:
            response += f"### Recommendations\n"
            for rec in recommendations:
                response += f"- {rec}\n"
        
        return response
        
    except Exception as e:
        logger.error(f'Error in analyze_cell_design: {str(e)}')
        return f'Error analyzing cell design: {str(e)}'


@mcp.tool(name='validate-architecture')
async def validate_architecture(
    design_document: str = Field(
        ...,
        description='Architecture design document or description to validate'
    ),
) -> str:
    """Validate architecture against cell-based architecture principles."""
    try:
        logger.info('Validating architecture')
        
        response = f"# Cell-Based Architecture Validation\n\n"
        
        validation_results = {
            'isolation': 'PASS' if 'isolation' in design_document.lower() else 'FAIL',
            'fault_tolerance': 'PASS' if 'fault' in design_document.lower() else 'FAIL',
        }
        
        passed = sum(1 for result in validation_results.values() if result == 'PASS')
        total = len(validation_results)
        compliance_score = passed / total
        
        response += f"**Compliance Score:** {compliance_score:.1f}/1.0\n\n"
        
        for criteria, result in validation_results.items():
            status_icon = "✅" if result == 'PASS' else "❌"
            response += f"{status_icon} **{criteria.replace('_', ' ').title()}**: {result}\n"
        
        return response
        
    except Exception as e:
        logger.error(f'Error in validate_architecture: {str(e)}')
        return f'Error validating architecture: {str(e)}'

@mcp.resource(uri='resource://implementation-patterns', name='ImplementationPatterns', mime_type='application/json')
async def implementation_patterns() -> str:
    """Common implementation patterns and AWS service integration examples."""
    try:
        patterns = {
            'title': 'Cell-Based Architecture Implementation Patterns',
            'description': 'Common patterns and AWS service integration examples',
            'patterns': {
                'basic_cell_pattern': {
                    'name': 'Basic Cell Pattern',
                    'description': 'Simple cell with isolated compute and data',
                    'aws_services': ['Lambda', 'DynamoDB', 'API Gateway'],
                    'use_case': 'Small to medium applications with clear boundaries'
                },
                'multi_tier_cell': {
                    'name': 'Multi-Tier Cell Pattern',
                    'description': 'Cell with separate presentation, business, and data tiers',
                    'aws_services': ['CloudFront', 'ALB', 'ECS', 'RDS'],
                    'use_case': 'Complex applications requiring tier separation'
                },
                'event_driven_cell': {
                    'name': 'Event-Driven Cell Pattern',
                    'description': 'Cells communicating through events',
                    'aws_services': ['EventBridge', 'SQS', 'SNS', 'Lambda'],
                    'use_case': 'Loosely coupled systems with async communication'
                }
            }
        }
        
        return json.dumps(patterns, indent=2)
        
    except Exception as e:
        logger.error(f'Error serving implementation patterns: {str(e)}')
        return json.dumps({'error': f'Error loading patterns: {str(e)}'})


@mcp.resource(uri='resource://best-practices', name='BestPractices', mime_type='application/json')
async def best_practices() -> str:
    """Best practices and troubleshooting guidance for cell-based architecture."""
    try:
        practices = {
            'title': 'Cell-Based Architecture Best Practices',
            'description': 'Best practices and troubleshooting guidance',
            'categories': {
                'design_principles': {
                    'title': 'Design Principles',
                    'practices': [
                        'Keep cells independent and self-contained',
                        'Design for failure scenarios from the start',
                        'Minimize cross-cell dependencies',
                        'Implement proper cell boundaries'
                    ]
                },
                'operational_guidelines': {
                    'title': 'Operational Guidelines',
                    'practices': [
                        'Monitor cell health independently',
                        'Implement automated failover mechanisms',
                        'Plan for cell migration scenarios',
                        'Test failure scenarios regularly'
                    ]
                },
                'common_pitfalls': {
                    'title': 'Common Pitfalls to Avoid',
                    'practices': [
                        'Avoid shared databases across cells',
                        'Do not create tight coupling between cells',
                        'Avoid single points of failure in routing',
                        'Do not ignore blast radius considerations'
                    ]
                }
            }
        }
        
        return json.dumps(practices, indent=2)
        
    except Exception as e:
        logger.error(f'Error serving best practices: {str(e)}')
        return json.dumps({'error': f'Error loading best practices: {str(e)}'})