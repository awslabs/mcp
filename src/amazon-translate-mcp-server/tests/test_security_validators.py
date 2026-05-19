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

"""Security validation tests for Amazon Translate MCP Server."""

import pytest
from awslabs.amazon_translate_mcp_server.exceptions import SecurityError, ValidationError
from awslabs.amazon_translate_mcp_server.security_validators import (
    MAX_BATCH_SIZE,
    MAX_TEXT_LENGTH,
    validate_aws_region,
    validate_batch_size,
    validate_iam_role_arn,
    validate_job_name,
    validate_language_code,
    validate_s3_uri,
    validate_target_languages,
    validate_terminology_name,
    validate_text_input,
)


class TestRegionValidation:
    """Test AWS region validation."""

    def test_valid_region(self):
        """Test validation of valid AWS regions."""
        valid_regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']
        for region in valid_regions:
            assert validate_aws_region(region) == region

    def test_invalid_region(self):
        """Test rejection of invalid regions."""
        with pytest.raises(SecurityError) as exc_info:
            validate_aws_region('invalid-region-1')
        assert 'Invalid or unsupported AWS region' in str(exc_info.value)

    def test_empty_region(self):
        """Test rejection of empty region."""
        with pytest.raises(ValidationError) as exc_info:
            validate_aws_region('')
        assert 'AWS region is required' in str(exc_info.value)

    def test_none_region(self):
        """Test rejection of None region."""
        with pytest.raises(ValidationError):
            validate_aws_region(None)

    def test_ssrf_attempt_region(self):
        """Test rejection of SSRF attempts via region."""
        malicious_regions = [
            'http://evil.com',
            '127.0.0.1',
            'localhost',
            '../../../etc/passwd',
        ]
        for region in malicious_regions:
            with pytest.raises(SecurityError):
                validate_aws_region(region)


class TestLanguageCodeValidation:
    """Test language code validation."""

    def test_valid_language_codes(self):
        """Test validation of valid language codes."""
        valid_codes = ['en', 'es', 'fr', 'de', 'ja', 'zh', 'pt', 'ar']
        for code in valid_codes:
            assert validate_language_code(code) == code

    def test_case_insensitive_validation(self):
        """Test case-insensitive language code validation."""
        assert validate_language_code('EN') == 'EN'
        assert validate_language_code('Es') == 'Es'

    def test_invalid_language_code(self):
        """Test rejection of invalid language codes."""
        with pytest.raises(ValidationError) as exc_info:
            validate_language_code('invalid')
        assert 'Unsupported language code' in str(exc_info.value)

    def test_empty_language_code(self):
        """Test rejection of empty language code."""
        with pytest.raises(ValidationError):
            validate_language_code('')

    def test_injection_attempt(self):
        """Test rejection of clearly malicious injection attempts."""
        # Focus on truly malicious patterns that should never be valid language codes
        malicious_codes = [
            '../../../etc/passwd',  # Path traversal
            '<script>alert(1)</script>',  # XSS
        ]
        for code in malicious_codes:
            with pytest.raises(ValidationError):
                validate_language_code(code)


class TestTextInputValidation:
    """Test text input validation."""

    def test_valid_text(self):
        """Test validation of valid text input."""
        text = 'Hello, world!'
        assert validate_text_input(text) == text

    def test_empty_text(self):
        """Test rejection of empty text."""
        with pytest.raises(ValidationError) as exc_info:
            validate_text_input('')
        assert 'Text input is required' in str(exc_info.value)

    def test_text_exceeds_max_length(self):
        """Test rejection of text exceeding maximum length."""
        long_text = 'a' * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValidationError) as exc_info:
            validate_text_input(long_text)
        assert 'exceeds maximum length' in str(exc_info.value)

    def test_custom_max_length(self):
        """Test validation with custom maximum length."""
        text = 'a' * 100
        assert validate_text_input(text, max_length=100) == text

        with pytest.raises(ValidationError):
            validate_text_input(text, max_length=50)

    def test_dos_prevention(self):
        """Test DoS prevention via text length limits."""
        # Attempt to send extremely large text
        huge_text = 'a' * 1000000  # 1MB
        with pytest.raises(ValidationError):
            validate_text_input(huge_text)


class TestS3URIValidation:
    """Test S3 URI validation."""

    def test_valid_s3_uri(self):
        """Test validation of valid S3 URIs."""
        valid_uris = [
            's3://my-bucket/path/to/file.txt',
            's3://my-bucket-123/folder/',
            's3://test-bucket/prefix',
        ]
        for uri in valid_uris:
            assert validate_s3_uri(uri) == uri

    def test_invalid_scheme(self):
        """Test rejection of non-S3 schemes."""
        invalid_uris = [
            'http://bucket/file',
            'https://bucket/file',
            'ftp://bucket/file',
            'file:///etc/passwd',
        ]
        for uri in invalid_uris:
            with pytest.raises(SecurityError) as exc_info:
                validate_s3_uri(uri)
            assert 'Invalid S3 URI' in str(exc_info.value)

    def test_ssrf_prevention(self):
        """Test SSRF prevention in S3 URIs."""
        ssrf_attempts = [
            's3://localhost/file',
            's3://127.0.0.1/file',
            's3://169.254.169.254/latest/meta-data/',  # AWS metadata service
            's3://metadata/file',
            's3://0.0.0.0/file',
        ]
        for uri in ssrf_attempts:
            with pytest.raises(SecurityError) as exc_info:
                validate_s3_uri(uri)
            assert 'suspicious pattern' in str(exc_info.value).lower()

    def test_empty_bucket_name(self):
        """Test rejection of empty bucket name."""
        with pytest.raises(SecurityError):
            validate_s3_uri('s3:///file')

    def test_uri_length_limit(self):
        """Test rejection of excessively long URIs."""
        long_uri = 's3://bucket/' + 'a' * 2000
        with pytest.raises(ValidationError):
            validate_s3_uri(long_uri)


class TestIAMRoleARNValidation:
    """Test IAM role ARN validation."""

    def test_valid_role_arn(self):
        """Test validation of valid IAM role ARNs."""
        valid_arns = [
            'arn:aws:iam::123456789012:role/MyRole',
            'arn:aws:iam::123456789012:role/service-role/MyServiceRole',
            'arn:aws:iam::123456789012:role/path/to/MyRole',
        ]
        for arn in valid_arns:
            assert validate_iam_role_arn(arn) == arn

    def test_invalid_arn_format(self):
        """Test rejection of invalid ARN formats."""
        invalid_arns = [
            'not-an-arn',
            'arn:aws:s3:::bucket',  # Wrong service
            'arn:aws:iam::123456789012:user/MyUser',  # User, not role
            'arn:aws:iam::invalid:role/MyRole',  # Invalid account ID
        ]
        for arn in invalid_arns:
            with pytest.raises(ValidationError):
                validate_iam_role_arn(arn)

    def test_empty_arn(self):
        """Test rejection of empty ARN."""
        with pytest.raises(ValidationError):
            validate_iam_role_arn('')


class TestJobNameValidation:
    """Test batch job name validation."""

    def test_valid_job_name(self):
        """Test validation of valid job names."""
        valid_names = [
            'my-job',
            'job_123',
            'TranslationJob-2024',
            'test-job_v1',
        ]
        for name in valid_names:
            assert validate_job_name(name) == name

    def test_invalid_characters(self):
        """Test rejection of invalid characters in job names."""
        invalid_names = [
            'job with spaces',
            'job@special',
            'job#123',
            'job/path',
            'job\\path',
        ]
        for name in invalid_names:
            with pytest.raises(ValidationError):
                validate_job_name(name)

    def test_empty_job_name(self):
        """Test rejection of empty job name."""
        with pytest.raises(ValidationError):
            validate_job_name('')

    def test_job_name_length_limit(self):
        """Test rejection of excessively long job names."""
        long_name = 'a' * 300
        with pytest.raises(ValidationError):
            validate_job_name(long_name)


class TestTerminologyNameValidation:
    """Test terminology name validation."""

    def test_valid_terminology_name(self):
        """Test validation of valid terminology names."""
        valid_names = [
            'my-terminology',
            'term_123',
            'CustomTerms-v1',
        ]
        for name in valid_names:
            assert validate_terminology_name(name) == name

    def test_invalid_characters(self):
        """Test rejection of invalid characters."""
        invalid_names = [
            'term with spaces',
            'term@special',
            'term#123',
        ]
        for name in invalid_names:
            with pytest.raises(ValidationError):
                validate_terminology_name(name)

    def test_empty_name(self):
        """Test rejection of empty name."""
        with pytest.raises(ValidationError):
            validate_terminology_name('')


class TestBatchSizeValidation:
    """Test batch size validation."""

    def test_valid_batch_size(self):
        """Test validation of valid batch sizes."""
        assert validate_batch_size(1) == 1
        assert validate_batch_size(100) == 100
        assert validate_batch_size(MAX_BATCH_SIZE) == MAX_BATCH_SIZE

    def test_zero_batch_size(self):
        """Test rejection of zero batch size."""
        with pytest.raises(ValidationError):
            validate_batch_size(0)

    def test_negative_batch_size(self):
        """Test rejection of negative batch size."""
        with pytest.raises(ValidationError):
            validate_batch_size(-1)

    def test_exceeds_maximum(self):
        """Test rejection of batch size exceeding maximum."""
        with pytest.raises(ValidationError) as exc_info:
            validate_batch_size(MAX_BATCH_SIZE + 1)
        assert 'exceeds maximum' in str(exc_info.value)

    def test_cost_amplification_prevention(self):
        """Test prevention of cost amplification via large batches."""
        # Attempt to send extremely large batch
        with pytest.raises(ValidationError):
            validate_batch_size(1000000)


class TestTargetLanguagesValidation:
    """Test target languages list validation."""

    def test_valid_target_languages(self):
        """Test validation of valid target language lists."""
        languages = ['en', 'es', 'fr']
        result = validate_target_languages(languages)
        assert result == languages

    def test_empty_list(self):
        """Test rejection of empty target languages list."""
        with pytest.raises(ValidationError):
            validate_target_languages([])

    def test_invalid_language_in_list(self):
        """Test rejection of invalid language code in list."""
        with pytest.raises(ValidationError):
            validate_target_languages(['en', 'invalid', 'fr'])

    def test_too_many_languages(self):
        """Test rejection of too many target languages."""
        # More than 10 languages
        many_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ja', 'zh', 'ko', 'ar', 'ru']
        with pytest.raises(ValidationError):
            validate_target_languages(many_languages)


class TestSecurityIntegration:
    """Integration tests for security validators."""

    def test_combined_validation_workflow(self):
        """Test combined validation in a typical workflow."""
        # Validate all inputs for a translation request
        region = validate_aws_region('us-east-1')
        source_lang = validate_language_code('en')
        target_langs = validate_target_languages(['es', 'fr'])
        text = validate_text_input('Hello, world!')

        assert region == 'us-east-1'
        assert source_lang == 'en'
        assert target_langs == ['es', 'fr']
        assert text == 'Hello, world!'

    def test_batch_translation_validation(self):
        """Test validation for batch translation workflow."""
        input_uri = validate_s3_uri('s3://my-bucket/input/')
        output_uri = validate_s3_uri('s3://my-bucket/output/')
        role_arn = validate_iam_role_arn('arn:aws:iam::123456789012:role/TranslateRole')
        job_name = validate_job_name('my-translation-job')

        assert input_uri.startswith('s3://')
        assert output_uri.startswith('s3://')
        assert role_arn.startswith('arn:aws:iam::')
        assert job_name == 'my-translation-job'

    def test_attack_vector_prevention(self):
        """Test prevention of common attack vectors."""
        # Test various attack attempts
        attack_vectors = [
            ('region', 'http://evil.com', validate_aws_region),
            ('language', '../../../etc/passwd', validate_language_code),
            ('s3_uri', 's3://169.254.169.254/metadata', validate_s3_uri),
            ('job_name', 'job; DROP TABLE users;', validate_job_name),
        ]

        for name, malicious_input, validator in attack_vectors:
            with pytest.raises((SecurityError, ValidationError)):
                validator(malicious_input)


class TestAdditionalCoverage:
    """Additional tests for edge cases and full coverage."""

    def test_s3_uri_empty(self):
        """Test rejection of empty S3 URI."""
        with pytest.raises(ValidationError) as exc_info:
            validate_s3_uri('')
        assert 's3_uri' in str(exc_info.value)

    def test_s3_uri_invalid_bucket_format(self):
        """Test rejection of invalid bucket name format."""
        # Bucket name starting with invalid character
        with pytest.raises(SecurityError) as exc_info:
            validate_s3_uri('s3://-invalid-bucket/file')
        assert 'Invalid S3 bucket name format' in str(exc_info.value)

    def test_s3_uri_ipv6_ssrf(self):
        """Test SSRF prevention with IPv6 localhost - caught by bucket validation."""
        with pytest.raises(SecurityError) as exc_info:
            validate_s3_uri('s3://::1/file')
        # IPv6 format fails bucket name validation first
        assert 'Invalid S3 bucket name format' in str(exc_info.value)

    def test_terminology_name_too_long(self):
        """Test rejection of terminology name exceeding max length."""
        long_name = 'a' * 300
        with pytest.raises(ValidationError) as exc_info:
            validate_terminology_name(long_name)
        assert 'exceeds maximum length' in str(exc_info.value)

    def test_s3_uri_with_custom_field_name(self):
        """Test S3 URI validation with custom field name."""
        with pytest.raises(ValidationError) as exc_info:
            validate_s3_uri('', field_name='input_s3_uri')
        assert 'input_s3_uri' in str(exc_info.value)

    def test_language_code_with_custom_field_name(self):
        """Test language code validation with custom field name."""
        with pytest.raises(ValidationError) as exc_info:
            validate_language_code('', field_name='source_language')
        assert 'source_language' in str(exc_info.value)
