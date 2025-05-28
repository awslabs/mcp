"""Tests for the workflow_prompts module imports."""

import unittest


class TestWorkflowPromptsImports(unittest.TestCase):
    """Test cases for workflow_prompts imports."""

    def test_imports(self):
        """Test that the workflow_prompts module imports correctly."""
        # Import the module
        from awslabs.openapi_mcp_server.prompts import workflow_prompts

        # Verify that the imported functions are available
        self.assertTrue(hasattr(workflow_prompts, '_generate_list_get_update_workflow'))
        self.assertTrue(hasattr(workflow_prompts, '_generate_search_create_workflow'))
        self.assertTrue(hasattr(workflow_prompts, 'generate_generic_workflow_prompts'))

    def test_imported_functions(self):
        """Test that the imported functions are the same as the original functions."""
        # Import both modules
        from awslabs.openapi_mcp_server.prompts import api_documentation_workflow, workflow_prompts

        # Verify that the imported functions are the same as the original functions
        self.assertIs(
            workflow_prompts._generate_list_get_update_workflow,
            api_documentation_workflow._generate_list_get_update_workflow,
        )
        self.assertIs(
            workflow_prompts._generate_search_create_workflow,
            api_documentation_workflow._generate_search_create_workflow,
        )
        self.assertIs(
            workflow_prompts.generate_generic_workflow_prompts,
            api_documentation_workflow.generate_generic_workflow_prompts,
        )

    def test_all_variable(self):
        """Test that the __all__ variable contains the expected functions."""
        # Import the module
        from awslabs.openapi_mcp_server.prompts import workflow_prompts

        # Verify that the __all__ variable contains the expected functions
        self.assertIn('_generate_list_get_update_workflow', workflow_prompts.__all__)
        self.assertIn('_generate_search_create_workflow', workflow_prompts.__all__)
        self.assertIn('generate_generic_workflow_prompts', workflow_prompts.__all__)
        self.assertEqual(len(workflow_prompts.__all__), 3)


if __name__ == '__main__':
    unittest.main()
