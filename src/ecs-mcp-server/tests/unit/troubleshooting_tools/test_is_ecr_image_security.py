"""
Security-focused unit tests for the is_ecr_image function.

These tests ensure the function properly validates ECR image URIs and prevents
URL substring sanitization vulnerabilities.
"""

import pytest

from awslabs.ecs_mcp_server.api.troubleshooting_tools.get_ecs_troubleshooting_guidance import (
    is_ecr_image,
)


class TestIsEcrImageSecurity:
    """Security-focused tests for the is_ecr_image function."""

    def test_valid_ecr_images(self):
        """Test that valid ECR image URLs are correctly identified."""
        valid_ecr_urls = [
            "123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo",
            "123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app:latest",
            "999999999999.dkr.ecr.eu-west-1.amazonaws.com/service:v1.0",
            "123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/repo/sub-repo:tag",
            "https://123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo",
            "http://123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo",
        ]

        for url in valid_ecr_urls:
            assert is_ecr_image(url) is True, f"Expected True for valid ECR URL: {url}"

    def test_malicious_urls_with_embedded_amazonaws_com(self):
        """Test that URLs with embedded 'amazonaws.com' are rejected."""
        malicious_urls = [
            "malicious-site.com/amazonaws.com/ecr",
            "evil.amazonaws.com.fake.com/ecr",
            "hack.com/path/amazonaws.com/ecr",
            "amazonaws.com.evil.com/ecr",
            "sub.amazonaws.com.attacker.com/ecr/repo",
            "fake-amazonaws.com/ecr",
            "amazonhttps://fake.amazonaws.com.evil.com/ecr",
        ]

        for url in malicious_urls:
            assert is_ecr_image(url) is False, f"Expected False for malicious URL: {url}"

    def test_non_ecr_amazonaws_urls(self):
        """Test that amazonaws.com URLs without proper ECR structure are rejected."""
        non_ecr_urls = [
            "s3.amazonaws.com/bucket",
            "ec2.amazonaws.com/instance",
            "lambda.amazonaws.com/function",
            "123456789012.dkr.amazonaws.com/repo",  # Missing .ecr.
            "ecr.amazonaws.com",  # Wrong structure, should be account.dkr.ecr.region.amazonaws.com
            "amazonaws.com/ecr",  # Missing proper subdomain structure
        ]

        for url in non_ecr_urls:
            assert is_ecr_image(url) is False, f"Expected False for non-ECR AWS URL: {url}"

    def test_completely_different_registries(self):
        """Test that other container registries are correctly rejected."""
        other_registries = [
            "docker.io/library/nginx:latest",
            "nginx:latest",
            "gcr.io/project/image",
            "quay.io/organization/repo",
            "mcr.microsoft.com/dotnet/sdk:6.0",
            "registry.hub.docker.com/library/ubuntu",
            "localhost:5000/local-image",
        ]

        for url in other_registries:
            assert is_ecr_image(url) is False, f"Expected False for non-ECR registry: {url}"

    def test_edge_cases_and_malformed_inputs(self):
        """Test edge cases and malformed inputs for robustness."""
        edge_cases = [
            "",  # Empty string
            " ",  # Whitespace
            "amazonaws.com",  # Just the domain
            "ecr",  # Just the service
            ".amazonaws.com",  # Leading dot
            "amazonaws.com.",  # Trailing dot
            "123456789012.dkr.ecr..amazonaws.com/repo",  # Double dots - should be False
            "123456789012.dkr.ecr.amazonaws.com",  # Missing region
            "https://",  # Incomplete URL
            "://amazonaws.com/ecr",  # Malformed scheme
        ]

        for case in edge_cases:
            result = is_ecr_image(case)
            assert result is False, f"Expected False for edge case: {case}"

    def test_case_sensitivity(self):
        """Test that the function handles case variations appropriately."""
        case_variations = [
            "123456789012.dkr.ECR.us-east-1.AMAZONAWS.COM/repo",
            "123456789012.dkr.Ecr.us-east-1.Amazonaws.Com/repo",
            "123456789012.DKR.ECR.US-EAST-1.AMAZONAWS.COM/REPO",
        ]

        # These should still be valid ECR URLs despite case differences
        for url in case_variations:
            assert is_ecr_image(url) is True, f"Expected True for case variation: {url}"

    def test_url_with_paths_and_parameters(self):
        """Test URLs with additional paths and query parameters."""
        urls_with_extras = [
            "123456789012.dkr.ecr.us-east-1.amazonaws.com/repo/path?param=value",
            "123456789012.dkr.ecr.us-east-1.amazonaws.com/repo#fragment",
            "123456789012.dkr.ecr.us-east-1.amazonaws.com/repo:tag?version=latest",
        ]

        for url in urls_with_extras:
            assert is_ecr_image(url) is True, f"Expected True for URL with extras: {url}"

    def test_subdomain_validation(self):
        """Test that subdomains are properly validated."""
        invalid_subdomains = [
            # These should fail because they don't have proper ECR subdomain structure
            "ecr.amazonaws.com/repo",  # Wrong structure
            "123456789012.amazonaws.com/repo",  # Missing dkr.ecr
            "dkr.amazonaws.com/repo",  # Missing account ID and ecr
            "123456789012.ecr.amazonaws.com/repo",  # Missing dkr
            "fake.ecr.amazonaws.com/repo",  # Invalid account ID format
        ]

        for url in invalid_subdomains:
            assert is_ecr_image(url) is False, f"Expected False for invalid subdomain: {url}"

    def test_injection_attempts(self):
        """Test various injection attempts that might bypass validation."""
        injection_attempts = [
            "javascript:alert('xss');//amazonaws.com/ecr",
            "data:text/html,<script>alert('xss')</script>//amazonaws.com/ecr",
            "ftp://amazonaws.com/ecr",
            "file://amazonaws.com/ecr",
            "../../../amazonaws.com/ecr",
            "\\amazonaws.com\\ecr",
            "%61mazonaws.com/ecr",  # URL encoded 'a'
            "amazonaws&#46;com/ecr",  # HTML encoded '.'
            "amazonaws\x2ecom/ecr",  # Hex encoded '.'
        ]

        for attempt in injection_attempts:
            assert is_ecr_image(attempt) is False, (
                f"Expected False for injection attempt: {attempt}"
            )

    def test_performance_with_long_strings(self):
        """Test that the function performs reasonably with very long strings."""
        long_prefix = "a" * 1000
        long_urls = [
            f"{long_prefix}.amazonaws.com/ecr",
            f"amazonaws.com/{long_prefix}/ecr",
            f"evil.com/{long_prefix}/amazonaws.com/ecr",
        ]

        for url in long_urls:
            # Should handle long strings without crashing
            try:
                result = is_ecr_image(url)
                assert result is False, f"Expected False for long string: {url[:50]}..."
            except Exception as e:
                pytest.fail(f"Function should handle long strings gracefully: {e}")

    def test_account_id_validation(self):
        """Test that proper 12-digit account IDs are required."""
        invalid_account_ids = [
            "12345.dkr.ecr.us-east-1.amazonaws.com/repo",  # Too short
            "1234567890123.dkr.ecr.us-east-1.amazonaws.com/repo",  # Too long
            "abcdefghijk.dkr.ecr.us-east-1.amazonaws.com/repo",  # Non-numeric
            "123456789.dkr.ecr.us-east-1.amazonaws.com/repo",  # Too short
        ]

        for url in invalid_account_ids:
            assert is_ecr_image(url) is False, f"Expected False for invalid account ID: {url}"

    def test_region_validation(self):
        """Test that regions follow proper AWS format."""
        valid_regions = [
            "123456789012.dkr.ecr.us-east-1.amazonaws.com/repo",
            "123456789012.dkr.ecr.eu-west-1.amazonaws.com/repo",
            "123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/repo",
            "123456789012.dkr.ecr.ca-central-1.amazonaws.com/repo",
        ]

        for url in valid_regions:
            assert is_ecr_image(url) is True, f"Expected True for valid region: {url}"
