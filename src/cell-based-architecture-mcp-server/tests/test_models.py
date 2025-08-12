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
"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from awslabs.cell_based_architecture_mcp_server.models import (
    CellArchitectureQuery,
    ImplementationStage,
    CellDesignAnalysis,
)


class TestCellArchitectureQuery:
    """Test CellArchitectureQuery model."""

    def test_valid_query(self):
        """Test valid query creation."""
        query = CellArchitectureQuery(
            concept="cell isolation",
            detail_level="intermediate",
            whitepaper_section="cell_design"
        )
        assert query.concept == "cell isolation"
        assert query.detail_level == "intermediate"
        assert query.whitepaper_section == "cell_design"

    def test_default_values(self):
        """Test default values."""
        query = CellArchitectureQuery(concept="fault tolerance")
        assert query.detail_level == "intermediate"
        assert query.whitepaper_section is None

    def test_invalid_detail_level(self):
        """Test invalid detail level."""
        with pytest.raises(ValidationError):
            CellArchitectureQuery(
                concept="test",
                detail_level="invalid"
            )

    def test_invalid_whitepaper_section(self):
        """Test invalid whitepaper section."""
        with pytest.raises(ValidationError):
            CellArchitectureQuery(
                concept="test",
                whitepaper_section="invalid_section"
            )


class TestImplementationStage:
    """Test ImplementationStage model."""

    def test_valid_stage(self):
        """Test valid stage creation."""
        stage = ImplementationStage(
            stage="design",
            aws_services=["lambda", "dynamodb"],
            experience_level="expert"
        )
        assert stage.stage == "design"
        assert stage.aws_services == ["lambda", "dynamodb"]
        assert stage.experience_level == "expert"

    def test_default_values(self):
        """Test default values."""
        stage = ImplementationStage(stage="planning")
        assert stage.aws_services == []
        assert stage.experience_level == "intermediate"

    def test_invalid_stage(self):
        """Test invalid stage."""
        with pytest.raises(ValidationError):
            ImplementationStage(stage="invalid")


class TestCellDesignAnalysis:
    """Test CellDesignAnalysis model."""

    def test_valid_analysis(self):
        """Test valid analysis creation."""
        analysis = CellDesignAnalysis(
            strengths=["Good isolation"],
            weaknesses=["Poor monitoring"],
            recommendations=["Add observability"],
            compliance_score=0.8,
            whitepaper_references=["cell_design"]
        )
        assert analysis.strengths == ["Good isolation"]
        assert analysis.compliance_score == 0.8

    def test_compliance_score_validation(self):
        """Test compliance score validation."""
        with pytest.raises(ValidationError):
            CellDesignAnalysis(compliance_score=1.5)
        
        with pytest.raises(ValidationError):
            CellDesignAnalysis(compliance_score=-0.1)

    def test_default_values(self):
        """Test default values."""
        analysis = CellDesignAnalysis(compliance_score=0.7)
        assert analysis.strengths == []
        assert analysis.weaknesses == []
        assert analysis.recommendations == []
        assert analysis.whitepaper_references == []