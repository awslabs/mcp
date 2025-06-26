"""
Unit tests for ModelDataService.
"""

import pytest

from awslabs.bedrock_advisor_mcp_server.services.model_data import ModelDataService
from awslabs.bedrock_advisor_mcp_server.utils.errors import ModelNotFoundError


class TestModelDataService:
    """Test cases for ModelDataService."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.service = ModelDataService()
    
    def test_singleton_pattern(self):
        """Test that ModelDataService follows singleton pattern."""
        service1 = ModelDataService()
        service2 = ModelDataService()
        assert service1 is service2
    
    def test_get_all_models(self):
        """Test getting all models."""
        models = self.service.get_all_models()
        assert len(models) > 0
        assert all(hasattr(model, 'model_id') for model in models)
        assert all(hasattr(model, 'model_name') for model in models)
    
    def test_get_model_by_id(self):
        """Test getting a specific model by ID."""
        models = self.service.get_all_models()
        first_model = models[0]
        
        retrieved_model = self.service.get_model(first_model.model_id)
        assert retrieved_model.model_id == first_model.model_id
        assert retrieved_model.model_name == first_model.model_name
    
    def test_get_nonexistent_model(self):
        """Test getting a model that doesn't exist."""
        with pytest.raises(ModelNotFoundError) as exc_info:
            self.service.get_model("nonexistent-model")
        
        assert "nonexistent-model" in str(exc_info.value)
        assert exc_info.value.error_code == "MODEL_NOT_FOUND"
    
    def test_get_models_by_provider(self):
        """Test filtering models by provider."""
        anthropic_models = self.service.get_models_by_provider("Anthropic")
        assert len(anthropic_models) > 0
        assert all(model.provider_name == "Anthropic" for model in anthropic_models)
    
    def test_get_models_by_region(self):
        """Test filtering models by region."""
        us_east_models = self.service.get_models_by_region("us-east-1")
        assert len(us_east_models) > 0
        assert all("us-east-1" in model.availability.regions for model in us_east_models)
    
    def test_get_models_by_capabilities(self):
        """Test filtering models by capabilities."""
        text_gen_models = self.service.get_models_by_capabilities(text_generation=True)
        assert len(text_gen_models) > 0
        assert all(model.capabilities.text_generation for model in text_gen_models)
        
        multimodal_models = self.service.get_models_by_capabilities(multimodal=True)
        assert all(model.capabilities.multimodal for model in multimodal_models)
    
    def test_get_supported_regions(self):
        """Test getting all supported regions."""
        regions = self.service.get_supported_regions()
        assert len(regions) > 0
        assert "us-east-1" in regions
        assert "us-west-2" in regions
        assert regions == sorted(regions)  # Should be sorted
    
    def test_search_models(self):
        """Test searching models by query."""
        claude_models = self.service.search_models("claude")
        assert len(claude_models) > 0
        assert all("claude" in model.model_name.lower() for model in claude_models)
        
        anthropic_models = self.service.search_models("anthropic")
        assert len(anthropic_models) > 0
        assert all("anthropic" in model.provider_name.lower() for model in anthropic_models)
