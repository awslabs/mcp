"""Unit tests for the tool_names module."""

from awslabs.aws_finops_mcp_server.consts import METHOD_ABBR, SERVICE_ABBR
from awslabs.aws_finops_mcp_server.tool_names import get_short_tool_name


def test_service_abbreviations():
    """Test that service abbreviations are correctly defined."""
    # Check that key service abbreviations exist
    assert 'cost_optimization_hub' in SERVICE_ABBR
    assert 'compute_optimizer' in SERVICE_ABBR
    assert 'cost_explorer' in SERVICE_ABBR

    # Check the abbreviation values
    assert SERVICE_ABBR['cost_optimization_hub'] == 'coh'
    assert SERVICE_ABBR['compute_optimizer'] == 'co'
    assert SERVICE_ABBR['cost_explorer'] == 'ce'


def test_method_abbreviations():
    """Test that method abbreviations are correctly defined."""
    # Check that key method abbreviations exist
    assert 'list_recommendations' in METHOD_ABBR
    assert 'get_auto_scaling_group_recommendations' in METHOD_ABBR
    assert 'get_cost_and_usage' in METHOD_ABBR

    # Check some abbreviation values
    assert METHOD_ABBR['list_recommendations'] == 'list_recs'
    assert METHOD_ABBR['get_auto_scaling_group_recommendations'] == 'get_asg_recs'
    assert METHOD_ABBR['get_lambda_function_recommendations'] == 'get_lambda_recs'
    assert METHOD_ABBR['get_cost_and_usage'] == 'get_cost_usage'


def test_get_short_tool_name():
    """Test the get_short_tool_name function."""
    # Test with known service and method
    assert get_short_tool_name('cost_optimization_hub', 'list_recommendations') == 'coh_list_recs'
    assert (
        get_short_tool_name('compute_optimizer', 'get_ec2_instance_recommendations')
        == 'co_get_ec2_recs'
    )
    assert get_short_tool_name('cost_explorer', 'get_cost_and_usage') == 'ce_get_cost_usage'

    # Test with unknown service (should use original)
    assert (
        get_short_tool_name('unknown_service', 'list_recommendations')
        == 'unknown_service_list_recs'
    )

    # Test with unknown method (should use original)
    assert get_short_tool_name('cost_explorer', 'unknown_method') == 'ce_unknown_method'

    # Test with both unknown
    assert (
        get_short_tool_name('unknown_service', 'unknown_method')
        == 'unknown_service_unknown_method'
    )


def test_tool_name_length_compliance():
    """Test that all shortened tool names comply with MCP specifications."""
    # MCP requires tool names to be max 64 chars when combined with server name
    server_name = 'aws_finops'  # From consts.py

    # Test all combinations of services and methods
    for service, service_abbr in SERVICE_ABBR.items():
        for method, method_abbr in METHOD_ABBR.items():
            short_name = get_short_tool_name(service, method)

            # Check that the tool name follows the regex pattern ^[a-zA-Z][a-zA-Z0-9_]*$
            assert short_name[0].isalpha(), f'Tool name {short_name} must start with a letter'
            assert all(c.isalnum() or c == '_' for c in short_name), (
                f'Tool name {short_name} contains invalid characters'
            )

            # Check length when combined with server name
            full_name = f'{server_name}_{short_name}'
            assert len(full_name) <= 64, f'Tool name {full_name} exceeds 64 characters'
