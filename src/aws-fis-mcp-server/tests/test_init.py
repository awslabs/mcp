import awslabs.aws_fis_mcp_server


class TestInit:
    """Test cases for package initialization."""

    def test_version(self):
        """Test that the package has a version."""
        assert hasattr(awslabs.aws_fis_mcp_server, '__version__')
        assert isinstance(awslabs.aws_fis_mcp_server.__version__, str)
        assert awslabs.aws_fis_mcp_server.__version__ == '0.1.0'
