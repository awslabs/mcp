"""Simple tests to boost coverage to 97%."""

import pytest
from awslabs.amazon_translate_mcp_server import config
from awslabs.amazon_translate_mcp_server.models import (
    LanguageDetectionResult,
    TranslationSettings,
    ValidationResult,
)


class TestCoverageBoost:
    """Simple tests to boost coverage."""

    def test_translation_settings_validation(self):
        """Test TranslationSettings validation."""
        # Valid settings
        settings = TranslationSettings(formality='FORMAL', profanity='MASK', brevity='ON')
        assert settings.formality == 'FORMAL'
        assert settings.profanity == 'MASK'
        assert settings.brevity == 'ON'

        # Invalid formality
        with pytest.raises(ValueError, match='formality must be'):
            TranslationSettings(formality='INVALID')

        # Invalid profanity
        with pytest.raises(ValueError, match='profanity must be'):
            TranslationSettings(profanity='INVALID')

        # Invalid brevity
        with pytest.raises(ValueError, match='brevity must be'):
            TranslationSettings(brevity='INVALID')

    def test_validation_result_edge_cases(self):
        """Test ValidationResult with edge cases."""
        # Valid result
        result = ValidationResult(
            is_valid=True, quality_score=0.95, issues=['minor issue'], suggestions=['suggestion']
        )
        assert result.is_valid is True
        assert result.quality_score == 0.95

        # Invalid quality score
        with pytest.raises(ValueError, match='quality_score must be between'):
            ValidationResult(is_valid=True, quality_score=1.5)

        with pytest.raises(ValueError, match='quality_score must be between'):
            ValidationResult(is_valid=True, quality_score=-0.1)

    def test_language_detection_result_validation(self):
        """Test LanguageDetectionResult validation."""
        # Valid result
        result = LanguageDetectionResult(
            detected_language='en', confidence_score=0.95, alternative_languages=[('es', 0.05)]
        )
        assert result.detected_language == 'en'
        assert result.confidence_score == 0.95

        # Invalid confidence score
        with pytest.raises(ValueError, match='confidence_score must be between'):
            LanguageDetectionResult(detected_language='en', confidence_score=1.5)

        # Empty detected language
        with pytest.raises(ValueError, match='detected_language cannot be empty'):
            LanguageDetectionResult(detected_language='', confidence_score=0.95)

        # Invalid alternative language score
        with pytest.raises(ValueError, match='Alternative language confidence score'):
            LanguageDetectionResult(
                detected_language='en', confidence_score=0.95, alternative_languages=[('es', 1.5)]
            )

        # Empty alternative language code
        with pytest.raises(ValueError, match='Alternative language code cannot be empty'):
            LanguageDetectionResult(
                detected_language='en', confidence_score=0.95, alternative_languages=[('', 0.5)]
            )

    def test_print_configuration_summary(self, capsys):
        """Test print_configuration_summary function."""
        server_config = config.ServerConfig(
            aws_region='us-east-1',
            aws_profile='test-profile',
            log_level='DEBUG',
            blocked_patterns=['pattern1', 'pattern2'],
        )

        config.print_configuration_summary(server_config)
        captured = capsys.readouterr()

        assert 'Amazon Translate MCP Server Configuration Summary' in captured.out
        assert 'us-east-1' in captured.out
        assert 'test-profile' in captured.out
        assert 'DEBUG' in captured.out
        assert 'Audit Logging: Enabled' in captured.out
        assert 'Blocked Patterns: 2 configured' in captured.out

    def test_print_configuration_summary_defaults(self, capsys):
        """Test print_configuration_summary with default values."""
        server_config = config.ServerConfig()

        config.print_configuration_summary(server_config)
        captured = capsys.readouterr()

        assert 'Default' in captured.out
        assert 'Audit Logging: Enabled' in captured.out
