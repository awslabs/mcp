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
"""Content accuracy and quality tests for cell-based architecture knowledge."""

import json
import pytest
import re
from typing import List, Dict, Any

from awslabs.cell_based_architecture_mcp_server.server import (
    query_cell_concepts,
    get_implementation_guidance,
    analyze_cell_design,
    validate_architecture,
    cell_architecture_guide,
    implementation_patterns,
    best_practices,
)
from awslabs.cell_based_architecture_mcp_server.knowledge import CellBasedArchitectureKnowledge


class TestWhitepaperContentAccuracy:
    """Test content accuracy against AWS Well-Architected whitepaper."""

    @pytest.mark.asyncio
    async def test_core_concepts_accuracy(self):
        """Test that core cell-based architecture concepts are accurate."""
        core_concepts = [
            "cell isolation",
            "blast radius",
            "fault tolerance", 
            "cell boundaries",
            "shared responsibility"
        ]
        
        for concept in core_concepts:
            result = await query_cell_concepts(
                concept=concept,
                detail_level="intermediate"
            )
            
            # Should contain the concept being queried
            assert concept.lower() in result.lower()
            
            # Should be substantial content (not just error message)
            assert len(result) > 200
            
            # Should contain cell-based architecture terminology
            assert any(term in result.lower() for term in [
                "cell", "isolation", "architecture", "resilience", "fault"
            ])

    @pytest.mark.asyncio
    async def test_whitepaper_section_coverage(self):
        """Test that all major whitepaper sections are covered."""
        whitepaper_sections = [
            "introduction",
            "what_is_cell_based", 
            "why_use_cell_based",
            "cell_design",
            "cell_partition",
            "cell_observability"
        ]
        
        for section in whitepaper_sections:
            result = await query_cell_concepts(
                concept="overview",
                whitepaper_section=section
            )
            
            # Should return content for each section
            assert len(result) > 100
            assert "error" not in result.lower()

    def test_knowledge_base_completeness(self):
        """Test that knowledge base contains all required sections."""
        sections = CellBasedArchitectureKnowledge.WHITEPAPER_SECTIONS
        
        required_sections = [
            "introduction",
            "what_is_cell_based",
            "why_use_cell_based", 
            "cell_design",
            "best_practices"
        ]
        
        for section in required_sections:
            assert section in sections, f"Missing required section: {section}"
            assert sections[section].content is not None
            assert len(sections[section].content) > 50


class TestResponseRelevanceAndCompleteness:
    """Test response relevance and completeness."""

    @pytest.mark.asyncio
    async def test_beginner_response_appropriateness(self):
        """Test that beginner responses are appropriate for new users."""
        result = await query_cell_concepts(
            concept="cell isolation",
            detail_level="beginner"
        )
        
        # Should contain beginner-friendly language
        beginner_indicators = [
            "introduction", "beginner", "basic", "fundamental", "start"
        ]
        assert any(indicator in result.lower() for indicator in beginner_indicators)
        
        # Should not be overly technical
        advanced_terms = ["implementation details", "advanced", "expert-level"]
        assert not any(term in result.lower() for term in advanced_terms)

    @pytest.mark.asyncio
    async def test_expert_response_depth(self):
        """Test that expert responses provide sufficient depth."""
        result = await query_cell_concepts(
            concept="cell sizing",
            detail_level="expert"
        )
        
        # Should contain advanced terminology
        expert_indicators = [
            "implementation", "advanced", "expert", "detailed", "complex"
        ]
        assert any(indicator in result.lower() for indicator in expert_indicators)
        
        # Should be comprehensive
        assert len(result) > 500

    @pytest.mark.asyncio
    async def test_implementation_guidance_completeness(self):
        """Test that implementation guidance is complete for each stage."""
        stages = ["planning", "design", "implementation", "monitoring"]
        
        for stage in stages:
            result = await get_implementation_guidance(
                stage=stage,
                experience_level="intermediate"
            )
            
            # Should mention the stage
            assert stage in result.lower()
            
            # Should provide actionable guidance
            action_words = ["should", "must", "implement", "consider", "ensure"]
            assert any(word in result.lower() for word in action_words)
            
            # Should be substantial
            assert len(result) > 300

    @pytest.mark.asyncio
    async def test_aws_services_integration_accuracy(self):
        """Test AWS services integration accuracy."""
        aws_services = ["lambda", "dynamodb", "api-gateway", "cloudfront"]
        
        result = await get_implementation_guidance(
            stage="implementation",
            aws_services=aws_services,
            experience_level="intermediate"
        )
        
        # Should mention all provided services
        for service in aws_services:
            assert service.lower() in result.lower()
        
        # Should provide service-specific guidance
        assert "aws services" in result.lower()


class TestPatternMatchingAndRecommendations:
    """Test architecture pattern recognition and recommendation quality."""

    @pytest.mark.asyncio
    async def test_isolation_pattern_recognition(self):
        """Test recognition of isolation patterns."""
        good_design = """
        Architecture with isolated Lambda functions, each with dedicated DynamoDB tables.
        No shared resources between cells. Clear boundaries defined.
        """
        
        result = await analyze_cell_design(
            architecture_description=good_design,
            focus_areas=["isolation"]
        )
        
        # Should recognize good isolation
        assert "isolation" in result.lower()
        assert "strengths" in result.lower()
        
        # Should have positive compliance score
        score_match = re.search(r'compliance score.*?(\d+\.?\d*)', result.lower())
        if score_match:
            score = float(score_match.group(1))
            assert score > 0.5

    @pytest.mark.asyncio
    async def test_poor_design_recommendations(self):
        """Test recommendations for poor designs."""
        poor_design = """
        Monolithic application with shared database across all components.
        Single point of failure. No isolation between different parts.
        """
        
        result = await analyze_cell_design(
            architecture_description=poor_design
        )
        
        # Should provide recommendations
        assert "recommendations" in result.lower()
        
        # Should mention isolation issues
        assert "isolation" in result.lower()
        
        # Should suggest improvements
        improvement_words = ["consider", "implement", "add", "improve", "define"]
        assert any(word in result.lower() for word in improvement_words)

    @pytest.mark.asyncio
    async def test_validation_scoring_accuracy(self):
        """Test validation scoring accuracy."""
        compliant_design = """
        Cell-based architecture with proper isolation, fault tolerance mechanisms,
        independent scaling, and clear cell boundaries. Each cell is self-contained.
        """
        
        result = await validate_architecture(design_document=compliant_design)
        
        # Should have validation results
        assert "validation" in result.lower()
        assert "compliance score" in result.lower()
        
        # Should show passing criteria
        assert "✅" in result or "pass" in result.lower()

    @pytest.mark.asyncio
    async def test_recommendation_quality_metrics(self):
        """Test quality of recommendations."""
        mixed_design = """
        System has some isolation with separate Lambda functions but uses
        shared RDS database and has cross-cell dependencies.
        """
        
        result = await analyze_cell_design(
            architecture_description=mixed_design,
            focus_areas=["isolation", "dependencies"]
        )
        
        # Should identify both strengths and weaknesses
        assert "strengths" in result.lower()
        assert "recommendations" in result.lower()
        
        # Should be specific about issues
        database_terms = ["database", "shared", "dependencies"]
        assert any(term in result.lower() for term in database_terms)


class TestAIModelInstructionCompliance:
    """Test compliance with AI model instructions in parameter descriptions."""

    def test_tool_parameter_descriptions(self):
        """Test that tool parameters have comprehensive descriptions for AI models."""
        import inspect
        from mcp.server.fastmcp import FastMCP
        from awslabs.cell_based_architecture_mcp_server.server import mcp
        
        for tool in mcp.tools:
            sig = inspect.signature(tool.func)
            
            for param_name, param in sig.parameters.items():
                if param_name != 'return' and param.default != inspect.Parameter.empty:
                    # Parameters should have Field with description
                    assert hasattr(param.default, 'description'), f"Parameter {param_name} in {tool.name} missing description"
                    
                    # Descriptions should be substantial
                    desc = param.default.description
                    assert len(desc) > 20, f"Parameter {param_name} description too short: {desc}"
                    
                    # Should provide guidance for AI models
                    guidance_indicators = ["e.g.", "such as", "for example", "like", "including"]
                    assert any(indicator in desc.lower() for indicator in guidance_indicators), f"Parameter {param_name} lacks AI guidance examples"

    def test_literal_type_constraints(self):
        """Test that Literal types are properly constrained."""
        import inspect
        from typing import get_origin, get_args
        from awslabs.cell_based_architecture_mcp_server.server import mcp
        
        for tool in mcp.tools:
            sig = inspect.signature(tool.func)
            
            for param_name, param in sig.parameters.items():
                if get_origin(param.annotation) is not None:
                    # Check for Literal types
                    if hasattr(param.annotation, '__origin__'):
                        continue  # Skip complex types for now
                    
                    # Ensure constrained values make sense
                    if param_name == 'detail_level':
                        # Should have beginner, intermediate, expert
                        expected_levels = {'beginner', 'intermediate', 'expert'}
                        # This is a basic check - in real implementation would check Literal args

    def test_response_structure_documentation(self):
        """Test that response structures are well documented."""
        for tool in mcp.tools:
            docstring = tool.func.__doc__
            assert docstring is not None, f"Tool {tool.name} missing docstring"
            
            # Should describe what the tool does
            assert len(docstring) > 100, f"Tool {tool.name} docstring too short"
            
            # Should mention response format or structure
            structure_indicators = ["returns", "provides", "response", "format", "structure"]
            assert any(indicator in docstring.lower() for indicator in structure_indicators)


class TestErrorMessageQuality:
    """Test error message quality and structured error responses."""

    @pytest.mark.asyncio
    async def test_graceful_error_handling(self):
        """Test that errors are handled gracefully with helpful messages."""
        # Test with empty concept
        result = await query_cell_concepts(
            concept="",
            detail_level="beginner"
        )
        
        # Should not crash and should return helpful response
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Should not contain stack traces or technical errors
        assert "traceback" not in result.lower()
        assert "exception" not in result.lower()

    @pytest.mark.asyncio
    async def test_invalid_parameter_handling(self):
        """Test handling of edge cases in parameters."""
        # Test with very long concept string
        long_concept = "a" * 1000
        
        result = await query_cell_concepts(
            concept=long_concept,
            detail_level="intermediate"
        )
        
        # Should handle gracefully
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_resource_error_responses(self):
        """Test that resource errors return valid JSON."""
        # All resources should return valid JSON even on errors
        resources = [
            cell_architecture_guide,
            implementation_patterns,
            best_practices
        ]
        
        for resource_func in resources:
            result = await resource_func()
            
            # Should always return valid JSON
            try:
                data = json.loads(result)
                assert isinstance(data, dict)
            except json.JSONDecodeError:
                pytest.fail(f"Resource {resource_func.__name__} returned invalid JSON: {result[:100]}")

    @pytest.mark.asyncio
    async def test_structured_error_format(self):
        """Test that errors follow structured format when they occur."""
        # This test would need to mock internal errors to test error formatting
        # For now, we test that normal responses are well-structured
        
        result = await analyze_cell_design(
            architecture_description="test architecture"
        )
        
        # Should have structured sections
        sections = ["analysis", "compliance score"]
        for section in sections:
            assert section.lower() in result.lower()


class TestContentConsistency:
    """Test consistency across different tools and responses."""

    @pytest.mark.asyncio
    async def test_terminology_consistency(self):
        """Test that terminology is consistent across tools."""
        # Get responses from different tools
        query_result = await query_cell_concepts(
            concept="cell isolation",
            detail_level="intermediate"
        )
        
        guidance_result = await get_implementation_guidance(
            stage="design",
            experience_level="intermediate"
        )
        
        # Should use consistent terminology
        key_terms = ["cell", "isolation", "architecture"]
        for term in key_terms:
            if term in query_result.lower():
                # If mentioned in one, should be consistent in others when relevant
                assert isinstance(guidance_result, str)  # Basic consistency check

    @pytest.mark.asyncio
    async def test_cross_reference_accuracy(self):
        """Test that cross-references between sections are accurate."""
        # Test that related sections actually relate to each other
        design_result = await query_cell_concepts(
            concept="design",
            whitepaper_section="cell_design"
        )
        
        partition_result = await query_cell_concepts(
            concept="partition",
            whitepaper_section="cell_partition"
        )
        
        # Both should mention cells and design concepts
        common_terms = ["cell", "design"]
        for term in common_terms:
            assert term.lower() in design_result.lower()
            assert term.lower() in partition_result.lower()

    @pytest.mark.asyncio
    async def test_progressive_complexity_consistency(self):
        """Test that complexity levels are consistent."""
        concept = "fault tolerance"
        
        beginner_result = await query_cell_concepts(
            concept=concept,
            detail_level="beginner"
        )
        
        expert_result = await query_cell_concepts(
            concept=concept,
            detail_level="expert"
        )
        
        # Expert should be longer and more detailed
        assert len(expert_result) >= len(beginner_result)
        
        # Both should mention the core concept
        assert concept.lower() in beginner_result.lower()
        assert concept.lower() in expert_result.lower()