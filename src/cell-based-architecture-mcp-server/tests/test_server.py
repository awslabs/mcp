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
"""Tests for MCP server functionality."""

import json
import pytest

from awslabs.cell_based_architecture_mcp_server.server import (
    query_cell_concepts,
    get_implementation_guidance,
    analyze_cell_design,
    validate_architecture,
    cell_architecture_guide,
    implementation_patterns,
    best_practices,
)


class TestQueryCellConcepts:
    """Test query_cell_concepts tool."""

    @pytest.mark.asyncio
    async def test_basic_query(self):
        """Test basic concept query."""
        result = await query_cell_concepts(
            concept="cell isolation",
            detail_level="intermediate"
        )
        assert "cell-based architecture" in result.lower()
        assert "isolation" in result.lower()

    @pytest.mark.asyncio
    async def test_beginner_level(self):
        """Test beginner level query."""
        result = await query_cell_concepts(
            concept="fault tolerance",
            detail_level="beginner"
        )
        assert "beginner" in result.lower()
        assert len(result) > 100  # Ensure substantial response

    @pytest.mark.asyncio
    async def test_expert_level(self):
        """Test expert level query."""
        result = await query_cell_concepts(
            concept="cell design",
            detail_level="expert"
        )
        assert "expert" in result.lower()
        assert "implementation" in result.lower()

    @pytest.mark.asyncio
    async def test_specific_section(self):
        """Test query with specific whitepaper section."""
        result = await query_cell_concepts(
            concept="design patterns",
            whitepaper_section="cell_design"
        )
        assert "cell design" in result.lower()


class TestGetImplementationGuidance:
    """Test get_implementation_guidance tool."""

    @pytest.mark.asyncio
    async def test_planning_stage(self):
        """Test planning stage guidance."""
        result = await get_implementation_guidance(
            stage="planning",
            experience_level="beginner"
        )
        assert "planning" in result.lower()
        assert "stage" in result.lower()

    @pytest.mark.asyncio
    async def test_with_aws_services(self):
        """Test guidance with AWS services."""
        result = await get_implementation_guidance(
            stage="implementation",
            aws_services=["lambda", "dynamodb"],
            experience_level="intermediate"
        )
        assert "lambda" in result.lower()
        assert "dynamodb" in result.lower()
        assert "aws services" in result.lower()

    @pytest.mark.asyncio
    async def test_monitoring_stage(self):
        """Test monitoring stage guidance."""
        result = await get_implementation_guidance(
            stage="monitoring",
            experience_level="expert"
        )
        assert "monitoring" in result.lower() or "observability" in result.lower()


class TestAnalyzeCellDesign:
    """Test analyze_cell_design tool."""

    @pytest.mark.asyncio
    async def test_design_with_isolation(self):
        """Test design analysis with isolation mentioned."""
        result = await analyze_cell_design(
            architecture_description="My system uses isolated Lambda functions with separate databases",
            focus_areas=["isolation"]
        )
        assert "analysis" in result.lower()
        assert "compliance score" in result.lower()
        assert "isolation" in result.lower()

    @pytest.mark.asyncio
    async def test_design_without_isolation(self):
        """Test design analysis without isolation."""
        result = await analyze_cell_design(
            architecture_description="My system uses shared resources across all components"
        )
        assert "recommendations" in result.lower()
        assert "isolation" in result.lower()

    @pytest.mark.asyncio
    async def test_design_with_fault_tolerance(self):
        """Test design analysis with fault tolerance."""
        result = await analyze_cell_design(
            architecture_description="System designed for fault tolerance and failure scenarios"
        )
        assert "fault" in result.lower()
        assert "strengths" in result.lower()


class TestValidateArchitecture:
    """Test validate_architecture tool."""

    @pytest.mark.asyncio
    async def test_compliant_architecture(self):
        """Test validation of compliant architecture."""
        result = await validate_architecture(
            design_document="Architecture with proper isolation and fault tolerance mechanisms"
        )
        assert "validation" in result.lower()
        assert "compliance score" in result.lower()
        assert "✅" in result or "pass" in result.lower()

    @pytest.mark.asyncio
    async def test_non_compliant_architecture(self):
        """Test validation of non-compliant architecture."""
        result = await validate_architecture(
            design_document="Simple monolithic architecture with shared database"
        )
        assert "validation" in result.lower()
        assert "❌" in result or "fail" in result.lower()


class TestResources:
    """Test MCP resources."""

    @pytest.mark.asyncio
    async def test_cell_architecture_guide(self):
        """Test cell architecture guide resource."""
        result = await cell_architecture_guide()
        data = json.loads(result)
        
        assert "title" in data
        assert "sections" in data
        assert len(data["sections"]) > 0
        
        # Check that key sections exist
        assert "introduction" in data["sections"]
        assert "cell_design" in data["sections"]
        assert "best_practices" in data["sections"]

    @pytest.mark.asyncio
    async def test_implementation_patterns(self):
        """Test implementation patterns resource."""
        result = await implementation_patterns()
        data = json.loads(result)
        
        assert "title" in data
        assert "patterns" in data
        assert len(data["patterns"]) > 0
        
        # Check for expected patterns
        patterns = data["patterns"]
        assert "basic_cell_pattern" in patterns
        assert "aws_services" in patterns["basic_cell_pattern"]

    @pytest.mark.asyncio
    async def test_best_practices(self):
        """Test best practices resource."""
        result = await best_practices()
        data = json.loads(result)
        
        assert "title" in data
        assert "categories" in data
        assert len(data["categories"]) > 0
        
        # Check for expected categories
        categories = data["categories"]
        assert "design_principles" in categories
        assert "operational_guidelines" in categories
        assert "common_pitfalls" in categories


class TestErrorHandling:
    """Test error handling in tools."""

    @pytest.mark.asyncio
    async def test_query_concepts_error_handling(self):
        """Test error handling in query_cell_concepts."""
        # This should not raise an exception even with unusual input
        result = await query_cell_concepts(
            concept="",
            detail_level="beginner"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_analyze_design_error_handling(self):
        """Test error handling in analyze_cell_design."""
        # This should not raise an exception even with empty input
        result = await analyze_cell_design(
            architecture_description=""
        )
        assert isinstance(result, str)
        assert len(result) > 0