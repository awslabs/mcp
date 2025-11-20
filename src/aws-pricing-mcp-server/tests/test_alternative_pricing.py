from awslabs.aws_pricing_mcp_server.alternative_pricing import get_pricing_alternatives


class TestGetPricingAlternatives:
    """Test suite for get_pricing_alternatives function."""

    def test_service_with_alternatives(self):
        """Test service with alternatives returns correct structure."""
        result = get_pricing_alternatives('AmazonCloudFront')

        assert result is not None
        assert len(result) > 0

        alternative = result[0]
        assert alternative['service_code'] == 'CloudFrontPlans'
        assert 'service_code' in alternative
        assert 'keywords' in alternative
        assert 'bundled_services' in alternative
        assert 'description' in alternative
        assert 'AmazonCloudFront' in alternative['bundled_services']

    def test_service_without_alternatives(self):
        """Test service without alternatives returns None."""
        result = get_pricing_alternatives('AmazonEC2')

        assert result is None

    def test_invalid_service_code(self):
        """Test invalid service code returns None."""
        result = get_pricing_alternatives('InvalidService')

        assert result is None
