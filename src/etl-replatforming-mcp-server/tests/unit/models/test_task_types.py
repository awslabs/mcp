import pytest

from awslabs.etl_replatforming_mcp_server.models.task_types import (
    ALL_TASK_TYPES,
    BRANCH_TASK_TYPES,
    LOOP_TASK_TYPES,
    SCRIPT_TASK_TYPES,
    get_all_task_types,
    is_branch_task_type,
    is_loop_task_type,
    is_valid_task_type,
    requires_script_file,
)


class TestTaskTypes:
    """Tests for FLEX task type constants and utilities"""

    def test_get_all_task_types(self):
        """Test get_all_task_types returns sorted list"""
        task_types = get_all_task_types()

        assert isinstance(task_types, list)
        assert len(task_types) > 0
        assert task_types == sorted(task_types)  # Should be sorted

        # Check some expected types are present
        expected_types = ['sql', 'python', 'bash', 'for_each', 'branch', 'email']
        for expected_type in expected_types:
            assert expected_type in task_types

    def test_is_valid_task_type(self):
        """Test task type validation"""
        # Valid types
        assert is_valid_task_type('sql') is True
        assert is_valid_task_type('python') is True
        assert is_valid_task_type('for_each') is True
        assert is_valid_task_type('branch') is True

        # Invalid types
        assert is_valid_task_type('invalid_type') is False
        assert is_valid_task_type('') is False
        # Note: None would cause TypeError, so we test with empty string instead

    def test_is_loop_task_type(self):
        """Test loop task type detection"""
        # Loop types
        assert is_loop_task_type('for_each') is True
        assert is_loop_task_type('while') is True
        assert is_loop_task_type('parallel') is True

        # Non-loop types
        assert is_loop_task_type('sql') is False
        assert is_loop_task_type('python') is False
        assert is_loop_task_type('branch') is False

    def test_is_branch_task_type(self):
        """Test branch task type detection"""
        # Branch types
        assert is_branch_task_type('branch') is True

        # Non-branch types
        assert is_branch_task_type('sql') is False
        assert is_branch_task_type('python') is False
        assert is_branch_task_type('for_each') is False

    def test_requires_script_file(self):
        """Test script file requirement detection"""
        # Script types
        assert requires_script_file('python') is True
        assert requires_script_file('bash') is True
        assert requires_script_file('container') is True

        # Non-script types
        assert requires_script_file('sql') is False
        assert requires_script_file('branch') is False
        assert requires_script_file('for_each') is False

    def test_task_type_sets_are_disjoint(self):
        """Test that task type sets don't overlap inappropriately"""
        # Loop and branch types should be disjoint
        assert LOOP_TASK_TYPES.isdisjoint(BRANCH_TASK_TYPES)

        # All sets should be subsets of ALL_TASK_TYPES
        assert LOOP_TASK_TYPES.issubset(ALL_TASK_TYPES)
        assert BRANCH_TASK_TYPES.issubset(ALL_TASK_TYPES)
        assert SCRIPT_TASK_TYPES.issubset(ALL_TASK_TYPES)

    def test_all_task_types_comprehensive(self):
        """Test that ALL_TASK_TYPES includes all expected categories"""
        from awslabs.etl_replatforming_mcp_server.models.task_types import (
            CONTROL_FLOW_TASK_TYPES,
            CORE_TASK_TYPES,
            DATA_TASK_TYPES,
            INTEGRATION_TASK_TYPES,
            UTILITY_TASK_TYPES,
        )

        expected_all = (
            CORE_TASK_TYPES
            | CONTROL_FLOW_TASK_TYPES
            | DATA_TASK_TYPES
            | INTEGRATION_TASK_TYPES
            | UTILITY_TASK_TYPES
        )

        assert ALL_TASK_TYPES == expected_all

    def test_specific_task_types_present(self):
        """Test that specific important task types are present"""
        # Core types
        assert 'sql' in ALL_TASK_TYPES
        assert 'python' in ALL_TASK_TYPES
        assert 'bash' in ALL_TASK_TYPES

        # Control flow types
        assert 'branch' in ALL_TASK_TYPES
        assert 'for_each' in ALL_TASK_TYPES
        assert 'while' in ALL_TASK_TYPES

        # Data types
        assert 'extract' in ALL_TASK_TYPES
        assert 'transform' in ALL_TASK_TYPES
        assert 'load' in ALL_TASK_TYPES

        # Integration types
        assert 'email' in ALL_TASK_TYPES
        assert 'http' in ALL_TASK_TYPES


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
