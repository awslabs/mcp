from awslabs.etl_replatforming_mcp_server.models.llm_config import (
    LLMConfig,
    LLMProvider,
)


class TestLLMConfig:
    """Test cases for LLMConfig model"""

    def test_default_config(self):
        """Test default configuration values"""
        config = LLMConfig()

        assert config.model_id == LLMProvider.ANTHROPIC_CLAUDE_SONNET_4.value
        assert config.max_tokens == 50000
        assert config.temperature == 0.1
        assert config.top_p == 0.9
        assert config.region == 'us-east-1'
        assert config.extra_params == {}

    def test_custom_config(self):
        """Test custom configuration values"""
        config = LLMConfig(
            model_id=LLMProvider.ANTHROPIC_CLAUDE_3_5_SONNET.value,
            max_tokens=6000,
            temperature=0.2,
            top_p=0.8,
            region='us-west-2',
            extra_params={'custom': 'value'},
        )

        assert config.model_id == LLMProvider.ANTHROPIC_CLAUDE_3_5_SONNET.value
        assert config.max_tokens == 6000
        assert config.temperature == 0.2
        assert config.top_p == 0.8
        assert config.region == 'us-west-2'
        assert config.extra_params == {'custom': 'value'}

    def test_get_default_config(self):
        """Test get_default_config class method"""
        config = LLMConfig.get_default_config()

        assert isinstance(config, LLMConfig)
        assert config.model_id == LLMProvider.ANTHROPIC_CLAUDE_SONNET_4.value
        assert config.max_tokens == 50000
        assert config.temperature == 0.1
        assert config.top_p == 0.9
        assert config.region == 'us-east-1'
        assert config.extra_params == {}

    def test_from_dict_empty(self):
        """Test from_dict with empty dictionary"""
        config = LLMConfig.from_dict({})

        assert config.model_id == LLMProvider.ANTHROPIC_CLAUDE_SONNET_4.value
        assert config.max_tokens == 50000
        assert config.temperature == 0.1
        assert config.top_p == 0.9
        assert config.region == 'us-east-1'
        assert config.extra_params == {}

    def test_from_dict_partial(self):
        """Test from_dict with partial configuration"""
        config_dict = {
            'model_id': LLMProvider.ANTHROPIC_CLAUDE_3_HAIKU.value,
            'temperature': 0.3,
        }
        config = LLMConfig.from_dict(config_dict)

        assert config.model_id == LLMProvider.ANTHROPIC_CLAUDE_3_HAIKU.value
        assert config.max_tokens == 50000  # default
        assert config.temperature == 0.3
        assert config.top_p == 0.9  # default
        assert config.region == 'us-east-1'  # default
        assert config.extra_params == {}

    def test_from_dict_full(self):
        """Test from_dict with full configuration"""
        config_dict = {
            'model_id': LLMProvider.ANTHROPIC_CLAUDE_3_OPUS.value,
            'max_tokens': 8000,
            'temperature': 0.5,
            'top_p': 0.7,
            'region': 'eu-west-1',
            'extra_params': {'stop_sequences': ['Human:', 'Assistant:']},
        }
        config = LLMConfig.from_dict(config_dict)

        assert config.model_id == LLMProvider.ANTHROPIC_CLAUDE_3_OPUS.value
        assert config.max_tokens == 8000
        assert config.temperature == 0.5
        assert config.top_p == 0.7
        assert config.region == 'eu-west-1'
        assert config.extra_params == {'stop_sequences': ['Human:', 'Assistant:']}

    def test_extra_params_initialization(self):
        """Test extra_params is properly initialized when None"""
        config = LLMConfig(extra_params={})
        assert config.extra_params == {}

        config = LLMConfig()
        assert config.extra_params == {}


class TestLLMProvider:
    """Test cases for LLMProvider enum"""

    def test_enum_values(self):
        """Test all enum values are correct"""
        assert (
            LLMProvider.ANTHROPIC_CLAUDE_SONNET_4.value
            == 'anthropic.claude-sonnet-4-20250514-v1:0'
        )
        assert (
            LLMProvider.ANTHROPIC_CLAUDE_3_5_SONNET.value
            == 'anthropic.claude-3-5-sonnet-20240620-v1:0'
        )
        assert (
            LLMProvider.ANTHROPIC_CLAUDE_3_SONNET.value
            == 'anthropic.claude-3-sonnet-20240229-v1:0'
        )
        assert (
            LLMProvider.ANTHROPIC_CLAUDE_3_HAIKU.value == 'anthropic.claude-3-haiku-20240307-v1:0'
        )
        assert LLMProvider.ANTHROPIC_CLAUDE_3_OPUS.value == 'anthropic.claude-3-opus-20240229-v1:0'

    def test_enum_count(self):
        """Test correct number of enum values"""
        assert len(LLMProvider) == 5
