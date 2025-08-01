import os
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import patch

import pytest

import sys
from pathlib import Path

qs_mcp_directory = Path(__file__).parent.parent
sys.path.append(str(qs_mcp_directory))
print(qs_mcp_directory)

import awslabs.aws_quicksight_dashboards_mcp_server.quicksight as qs

class TestGetCurrentVisuals(TestCase):
    """Test cases for get_current_visuals function."""

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    def test_get_current_visuals_success(self, mock_client):
        """Test get_current_visuals with valid parameters."""
        # Setup mock response
        mock_visuals = [
            {"BarChartVisual": {"VisualId": "visual1", "Title": {"Visibility": "VISIBLE"}}},
            {"LineChartVisual": {"VisualId": "visual2", "Title": {"Visibility": "VISIBLE"}}},
        ]

        mock_response = {
            "Definition": {
                "Sheets": [
                    {"SheetId": "sheet1", "Name": "Sheet 1", "Visuals": mock_visuals},
                    {"SheetId": "sheet2", "Name": "Sheet 2", "Visuals": []},
                ]
            }
        }
        mock_client.describe_dashboard_definition.return_value = mock_response

        # Call the function
        result = qs.get_current_visuals("dashboard1", "sheet1")

        # Verify the client was called correctly
        mock_client.describe_dashboard_definition.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID, DashboardId="dashboard1"
        )

        # Verify the result
        self.assertEqual(result, mock_visuals)

    def test_get_current_visuals_none_dash_id(self):
        """Test get_current_visuals with None as dash_id (should raise AssertionError)."""
        # Verify that passing None as dash_id raises an AssertionError
        with self.assertRaises(AssertionError) as context:
            qs.get_current_visuals(None, "sheet1")

        self.assertEqual(str(context.exception), "dash_id (dashboard ID) cannot be None")

    def test_get_current_visuals_none_sheet_id(self):
        """Test get_current_visuals with None as sheet_id (should raise AssertionError)."""
        # Verify that passing None as sheet_id raises an AssertionError
        with self.assertRaises(AssertionError) as context:
            qs.get_current_visuals("dashboard1", None)

        self.assertEqual(str(context.exception), "sheet_id (sheet ID) cannot be None")

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    def test_get_current_visuals_sheet_not_found(self, mock_client):
        """Test get_current_visuals with a non-existent sheet_id."""
        # Setup mock response
        mock_response = {
            "Definition": {"Sheets": [{"SheetId": "sheet1", "Name": "Sheet 1", "Visuals": []}]}
        }
        mock_client.describe_dashboard_definition.return_value = mock_response

        # Call the function with a non-existent sheet_id
        result = qs.get_current_visuals("dashboard1", "non_existent_sheet")

        # Verify the client was called correctly
        mock_client.describe_dashboard_definition.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID, DashboardId="dashboard1"
        )

        # Verify the result is None (sheet not found)
        self.assertIsNone(result)


class TestGetCurrentLayouts(TestCase):
    """Test cases for get_current_layouts function."""

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    def test_get_current_layouts_success(self, mock_client):
        """Test get_current_layouts with valid parameters."""
        # Setup mock response
        mock_layouts = [
            {
                "ElementId": "visual1",
                "ElementType": "VISUAL",
                "ColumnSpan": 18,
                "RowSpan": 12,
                "ColumnIndex": 0,
                "RowIndex": 0,
            },
            {
                "ElementId": "visual2",
                "ElementType": "VISUAL",
                "ColumnSpan": 18,
                "RowSpan": 12,
                "ColumnIndex": 18,
                "RowIndex": 12,
            },
        ]

        mock_response = {
            "Definition": {
                "Sheets": [
                    {
                        "SheetId": "sheet1",
                        "Name": "Sheet 1",
                        "Layouts": [{"Configuration": {"GridLayout": {"Elements": mock_layouts}}}],
                    },
                    {
                        "SheetId": "sheet2",
                        "Name": "Sheet 2",
                        "Layouts": [{"Configuration": {"GridLayout": {"Elements": []}}}],
                    },
                ]
            }
        }
        mock_client.describe_dashboard_definition.return_value = mock_response

        # Call the function
        result = qs.get_current_layouts("dashboard1", "sheet1")

        # Verify the client was called correctly
        mock_client.describe_dashboard_definition.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID, DashboardId="dashboard1"
        )

        # Verify the result
        self.assertEqual(result, mock_layouts)

    def test_get_current_layouts_none_dash_id(self):
        """Test get_current_layouts with None as dash_id (should raise AssertionError)."""
        # Verify that passing None as dash_id raises an AssertionError
        with self.assertRaises(AssertionError) as context:
            qs.get_current_layouts(None, "sheet1")

        self.assertEqual(str(context.exception), "dash_id (dashboard ID) cannot be None")

    def test_get_current_layouts_none_sheet_id(self):
        """Test get_current_layouts with None as sheet_id (should raise AssertionError)."""
        # Verify that passing None as sheet_id raises an AssertionError
        with self.assertRaises(AssertionError) as context:
            qs.get_current_layouts("dashboard1", None)

        self.assertEqual(str(context.exception), "sheet_id (sheet ID) cannot be None")

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    def test_get_current_layouts_sheet_not_found(self, mock_client):
        """Test get_current_layouts with a non-existent sheet_id."""
        # Setup mock response
        mock_response = {
            "Definition": {
                "Sheets": [
                    {
                        "SheetId": "sheet1",
                        "Name": "Sheet 1",
                        "Layouts": [{"Configuration": {"GridLayout": {"Elements": []}}}],
                    }
                ]
            }
        }
        mock_client.describe_dashboard_definition.return_value = mock_response

        # Call the function with a non-existent sheet_id
        result = qs.get_current_layouts("dashboard1", "non_existent_sheet")

        # Verify the client was called correctly
        mock_client.describe_dashboard_definition.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID, DashboardId="dashboard1"
        )

        # Verify the result is None (sheet not found)
        self.assertIsNone(result)

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    def test_get_current_layouts_no_layouts(self, mock_client):
        """Test get_current_layouts when the sheet has no layouts."""
        # Setup mock response with a sheet that has no Layouts key
        mock_response = {
            "Definition": {
                "Sheets": [
                    {
                        "SheetId": "sheet1",
                        "Name": "Sheet 1",
                        # No Layouts key
                    }
                ]
            }
        }
        mock_client.describe_dashboard_definition.return_value = mock_response

        # Verify the exception is raised when trying to access non-existent key
        with self.assertRaises(KeyError):
            qs.get_current_layouts("dashboard1", "sheet1")


class TestGetCurrentDashboardDefinition(TestCase):
    """Test cases for get_current_dashboard_definition function."""

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    def test_get_current_dashboard_definition_success(self, mock_client):
        """Test get_current_dashboard_definition with valid parameters."""
        # Setup mock response
        mock_definition = {
            "DataSetIdentifierDeclarations": [],
            "Sheets": [{"SheetId": "sheet1", "Name": "Sheet 1", "Visuals": []}],
        }

        mock_response = {"Definition": mock_definition}
        mock_client.describe_dashboard_definition.return_value = mock_response

        # Call the function
        result = qs.get_current_dashboard_definition("dashboard1")

        # Verify the client was called correctly
        mock_client.describe_dashboard_definition.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID, DashboardId="dashboard1"
        )

        # Verify the result
        self.assertEqual(result, mock_definition)

    def test_get_current_dashboard_definition_none_dash_id(self):
        """Test get_current_dashboard_definition with None as dash_id (should raise AssertionError)."""
        # Verify that passing None as dash_id raises an AssertionError
        with self.assertRaises(AssertionError) as context:
            qs.get_current_dashboard_definition(None)

        self.assertEqual(str(context.exception), "dash_id (dashboard ID) cannot be None")

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    def test_get_current_dashboard_definition_missing_definition(self, mock_client):
        """Test get_current_dashboard_definition when the response doesn't contain a Definition key."""
        # Setup mock response without Definition key
        mock_response = {}
        mock_client.describe_dashboard_definition.return_value = mock_response

        # Verify the KeyError is raised
        with self.assertRaises(KeyError) as context:
            qs.get_current_dashboard_definition("dashboard1")

        # Verify the exception key
        self.assertEqual(str(context.exception), "'Definition'")


class TestUpdateVisual(TestCase):
    """Test cases for update_visual function."""

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.get_current_dashboard_definition")
    def test_update_visual_success(self, mock_get_definition):
        """Test update_visual with valid parameters."""
        # Setup mock response for get_current_dashboard_definition
        mock_visuals = [
            {"BarChartVisual": {"VisualId": "visual1", "Title": {"Visibility": "VISIBLE"}}},
            {"LineChartVisual": {"VisualId": "visual2", "Title": {"Visibility": "VISIBLE"}}},
        ]

        mock_definition = {
            "DataSetIdentifierDeclarations": [],
            "Sheets": [
                {"SheetId": "sheet1", "Name": "Sheet 1", "Visuals": []},
                {"SheetId": "sheet2", "Name": "Sheet 2", "Visuals": []},
            ],
        }
        mock_get_definition.return_value = mock_definition

        # Call the function
        result = qs.update_visual("dashboard1", "sheet1", mock_visuals)

        # Verify get_current_dashboard_definition was called correctly
        mock_get_definition.assert_called_once_with("dashboard1")

        # Verify the visuals were updated for the correct sheet
        self.assertEqual(result["Sheets"][0]["Visuals"], mock_visuals)
        self.assertEqual(result["Sheets"][1]["Visuals"], [])  # Other sheet should be unchanged

    def test_update_visual_none_dash_id(self):
        """Test update_visual with None as dash_id (should raise AssertionError)."""
        # Verify that passing None as dash_id raises an AssertionError
        with self.assertRaises(AssertionError) as context:
            qs.update_visual(None, "sheet1", [])

        self.assertEqual(str(context.exception), "dash_id (dashboard ID) cannot be None")

    def test_update_visual_none_sheet_id(self):
        """Test update_visual with None as sheet_id (should raise AssertionError)."""
        # Verify that passing None as sheet_id raises an AssertionError
        with self.assertRaises(AssertionError) as context:
            qs.update_visual("dashboard1", None, [])

        self.assertEqual(str(context.exception), "sheet_id (sheet ID) cannot be None")

    def test_update_visual_none_new_visuals(self):
        """Test update_visual with None as new_visuals (should raise AssertionError)."""
        # Verify that passing None as new_visuals raises an AssertionError
        with self.assertRaises(AssertionError) as context:
            qs.update_visual("dashboard1", "sheet1", None)

        self.assertEqual(
            str(context.exception), "new_visuals (a list of visuals to be applied) cannot be None"
        )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.get_current_dashboard_definition")
    def test_update_visual_sheet_not_found(self, mock_get_definition):
        """Test update_visual with a non-existent sheet_id."""
        # Setup mock response for get_current_dashboard_definition
        mock_definition = {
            "DataSetIdentifierDeclarations": [],
            "Sheets": [{"SheetId": "sheet1", "Name": "Sheet 1", "Visuals": []}],
        }
        mock_get_definition.return_value = mock_definition

        # Create a copy of the definition to compare later
        original_definition = mock_definition.copy()

        # Call the function with a non-existent sheet_id
        result = qs.update_visual("dashboard1", "non_existent_sheet", [{"VisualId": "visual1"}])

        # Verify get_current_dashboard_definition was called correctly
        mock_get_definition.assert_called_once_with("dashboard1")

        # Verify no changes were made to the definition (sheet not found)
        self.assertEqual(result, original_definition)


class TestUpdateLayout(TestCase):
    """Test cases for update_layout function."""

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.get_current_dashboard_definition")
    def test_update_layout_success(self, mock_get_definition):
        """Test update_layout with valid parameters."""
        # Setup mock response for get_current_dashboard_definition
        mock_layouts = [
            {"ElementId": "visual1", "ElementType": "VISUAL", "ColumnSpan": 18, "RowSpan": 12},
            {"ElementId": "visual2", "ElementType": "VISUAL", "ColumnSpan": 18, "RowSpan": 12},
        ]

        mock_definition = {
            "DataSetIdentifierDeclarations": [],
            "Sheets": [
                {
                    "SheetId": "sheet1",
                    "Name": "Sheet 1",
                    "Layouts": [{"Configuration": {"GridLayout": {"Elements": []}}}],
                },
                {
                    "SheetId": "sheet2",
                    "Name": "Sheet 2",
                    "Layouts": [{"Configuration": {"GridLayout": {"Elements": []}}}],
                },
            ],
        }
        mock_get_definition.return_value = mock_definition

        # Call the function
        result = qs.update_layout("dashboard1", "sheet1", mock_layouts)

        # Verify get_current_dashboard_definition was called correctly
        mock_get_definition.assert_called_once_with("dashboard1")

        # Verify the layouts were updated for the correct sheet
        self.assertEqual(
            result["Sheets"][0]["Layouts"][0]["Configuration"]["GridLayout"]["Elements"],
            mock_layouts,
        )
        self.assertEqual(
            result["Sheets"][1]["Layouts"][0]["Configuration"]["GridLayout"]["Elements"], []
        )  # Other sheet should be unchanged

    def test_update_layout_none_dash_id(self):
        """Test update_layout with None as dash_id (should raise AssertionError)."""
        # Verify that passing None as dash_id raises an AssertionError
        with self.assertRaises(AssertionError) as context:
            qs.update_layout(None, "sheet1", [])

        self.assertEqual(str(context.exception), "dash_id (dashboard ID) cannot be None")

    def test_update_layout_none_sheet_id(self):
        """Test update_layout with None as sheet_id (should raise AssertionError)."""
        # Verify that passing None as sheet_id raises an AssertionError
        with self.assertRaises(AssertionError) as context:
            qs.update_layout("dashboard1", None, [])

        self.assertEqual(str(context.exception), "sheet_id (sheet ID) cannot be None")

    def test_update_layout_none_new_layout(self):
        """Test update_layout with None as new_bar_chart_layout (should raise AssertionError)."""
        # Verify that passing None as new_bar_chart_layout raises an AssertionError
        with self.assertRaises(AssertionError) as context:
            qs.update_layout("dashboard1", "sheet1", None)

        self.assertEqual(
            str(context.exception),
            "new_bar_chart_layout (a list of layouts to be applied) cannot be None",
        )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.get_current_dashboard_definition")
    def test_update_layout_sheet_not_found(self, mock_get_definition):
        """Test update_layout with a non-existent sheet_id."""
        # Setup mock response for get_current_dashboard_definition
        mock_definition = {
            "DataSetIdentifierDeclarations": [],
            "Sheets": [
                {
                    "SheetId": "sheet1",
                    "Name": "Sheet 1",
                    "Layouts": [{"Configuration": {"GridLayout": {"Elements": []}}}],
                }
            ],
        }
        mock_get_definition.return_value = mock_definition

        # Create a copy of the definition to compare later
        import copy

        original_definition = copy.deepcopy(mock_definition)

        # Call the function with a non-existent sheet_id
        result = qs.update_layout("dashboard1", "non_existent_sheet", [{"ElementId": "visual1"}])

        # Verify get_current_dashboard_definition was called correctly
        mock_get_definition.assert_called_once_with("dashboard1")

        # Verify no changes were made to the definition (sheet not found)
        self.assertEqual(result, original_definition)

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.get_current_dashboard_definition")
    def test_update_layout_no_layouts(self, mock_get_definition):
        """Test update_layout when the sheet has no layouts."""
        # Setup mock response for get_current_dashboard_definition with a sheet that has no Layouts key
        mock_definition = {
            "DataSetIdentifierDeclarations": [],
            "Sheets": [
                {
                    "SheetId": "sheet1",
                    "Name": "Sheet 1",
                    # No Layouts key
                }
            ],
        }
        mock_get_definition.return_value = mock_definition

        # Verify the KeyError is raised when trying to access non-existent key
        with self.assertRaises(KeyError):
            qs.update_layout("dashboard1", "sheet1", [{"ElementId": "visual1"}])


class TestMyListDashboards(IsolatedAsyncioTestCase):
    """Test cases for my_list_dashboards function."""

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    async def test_list_dashboards_no_token(self, mock_client):
        """Test my_list_dashboards with no token (default empty string)."""
        # Setup mock response
        mock_response = {
            "DashboardSummaryList": [
                {"DashboardId": "dashboard1", "Name": "Dashboard 1"},
                {"DashboardId": "dashboard2", "Name": "Dashboard 2"},
            ]
        }
        mock_client.list_dashboards.return_value = mock_response

        # Call the function
        result = await qs.my_list_dashboards()

        # Verify the client was called correctly
        mock_client.list_dashboards.assert_called_once_with(AwsAccountId=qs.ACCOUNT_ID)

        # Verify the result
        self.assertEqual(result, mock_response)

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    async def test_list_dashboards_with_token(self, mock_client):
        """Test my_list_dashboards with a next token."""
        # Setup mock response
        mock_response = {
            "DashboardSummaryList": [
                {"DashboardId": "dashboard3", "Name": "Dashboard 3"},
                {"DashboardId": "dashboard4", "Name": "Dashboard 4"},
            ],
            "NextToken": "next-page-token",
        }
        mock_client.list_dashboards.return_value = mock_response

        # Call the function with a token
        token = "some-token"
        result = await qs.my_list_dashboards(token)

        # Verify the client was called correctly with the token
        mock_client.list_dashboards.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID, NextToken=token
        )

        # Verify the result
        self.assertEqual(result, mock_response)

    async def test_list_dashboards_none_token(self):
        """Test my_list_dashboards with None as token (should raise AssertionError)."""
        # Verify that passing None as token raises an AssertionError
        with pytest.raises(AssertionError, match="next_token cannot be None"):
            await qs.my_list_dashboards(None)

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    async def test_list_dashboards_with_pagination(self, mock_client):
        """Test my_list_dashboards with pagination (multiple pages of results)."""
        # Setup first page response
        first_page_response = {
            "DashboardSummaryList": [
                {"DashboardId": "dashboard1", "Name": "Dashboard 1"},
                {"DashboardId": "dashboard2", "Name": "Dashboard 2"},
            ],
            "NextToken": "page2-token",
        }

        # Setup second page response
        second_page_response = {
            "DashboardSummaryList": [
                {"DashboardId": "dashboard3", "Name": "Dashboard 3"},
                {"DashboardId": "dashboard4", "Name": "Dashboard 4"},
            ]
        }

        # Configure mock to return different responses
        mock_client.list_dashboards.side_effect = [first_page_response, second_page_response]

        # Call the function for first page
        first_result = await qs.my_list_dashboards()

        # Verify first page call
        mock_client.list_dashboards.assert_called_with(AwsAccountId=qs.ACCOUNT_ID)

        # Verify first page result
        self.assertEqual(first_result, first_page_response)
        self.assertIn("NextToken", first_result)

        # Call the function for second page using the token from first page
        second_result = await qs.my_list_dashboards(first_result["NextToken"])

        # Verify second page call
        mock_client.list_dashboards.assert_called_with(
            AwsAccountId=qs.ACCOUNT_ID, NextToken="page2-token"
        )

        # Verify second page result
        self.assertEqual(second_result, second_page_response)
        self.assertNotIn("NextToken", second_result)


class TestMyListDatasets(IsolatedAsyncioTestCase):
    """Test cases for my_list_datasets function."""

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    async def test_list_datasets_no_token(self, mock_client):
        """Test my_list_datasets with no token (default empty string)."""
        # Setup mock response
        mock_response = {
            "DataSetSummaries": [
                {"DataSetId": "dataset1", "Name": "Dataset 1"},
                {"DataSetId": "dataset2", "Name": "Dataset 2"},
            ]
        }
        mock_client.list_data_sets.return_value = mock_response

        # Call the function
        result = await qs.my_list_datasets()

        # Verify the client was called correctly
        mock_client.list_data_sets.assert_called_once_with(AwsAccountId=qs.ACCOUNT_ID)

        # Verify the result
        self.assertEqual(result, mock_response)

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    async def test_list_datasets_with_token(self, mock_client):
        """Test my_list_datasets with a next token."""
        # Setup mock response
        mock_response = {
            "DataSetSummaries": [
                {"DataSetId": "dataset3", "Name": "Dataset 3"},
                {"DataSetId": "dataset4", "Name": "Dataset 4"},
            ],
            "NextToken": "next-page-token",
        }
        mock_client.list_data_sets.return_value = mock_response

        # Call the function with a token
        token = "some-token"
        result = await qs.my_list_datasets(token)

        # Verify the client was called correctly with the token
        mock_client.list_data_sets.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID, NextToken=token
        )

        # Verify the result
        self.assertEqual(result, mock_response)

    async def test_list_datasets_none_token(self):
        """Test my_list_datasets with None as token (should raise AssertionError)."""
        # Verify that passing None as token raises an AssertionError
        with pytest.raises(AssertionError, match="next_token cannot be None"):
            await qs.my_list_datasets(None)

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    async def test_list_datasets_with_pagination(self, mock_client):
        """Test my_list_datasets with pagination (multiple pages of results)."""
        # Setup first page response
        first_page_response = {
            "DataSetSummaries": [
                {"DataSetId": "dataset1", "Name": "Dataset 1"},
                {"DataSetId": "dataset2", "Name": "Dataset 2"},
            ],
            "NextToken": "page2-token",
        }

        # Setup second page response
        second_page_response = {
            "DataSetSummaries": [
                {"DataSetId": "dataset3", "Name": "Dataset 3"},
                {"DataSetId": "dataset4", "Name": "Dataset 4"},
            ]
        }

        # Configure mock to return different responses
        mock_client.list_data_sets.side_effect = [first_page_response, second_page_response]

        # Call the function for first page
        first_result = await qs.my_list_datasets()

        # Verify first page call
        mock_client.list_data_sets.assert_called_with(AwsAccountId=qs.ACCOUNT_ID)

        # Verify first page result
        self.assertEqual(first_result, first_page_response)
        self.assertIn("NextToken", first_result)

        # Call the function for second page using the token from first page
        second_result = await qs.my_list_datasets(first_result["NextToken"])

        # Verify second page call
        mock_client.list_data_sets.assert_called_with(
            AwsAccountId=qs.ACCOUNT_ID, NextToken="page2-token"
        )

        # Verify second page result
        self.assertEqual(second_result, second_page_response)
        self.assertNotIn("NextToken", second_result)


class TestMyGetDataset(IsolatedAsyncioTestCase):
    """Test cases for my_get_dataset function."""

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    async def test_get_dataset_with_id(self, mock_client):
        """Test my_get_dataset with a valid dataset_id."""
        # Setup mock response
        mock_dataset = {
            "DataSetId": "dataset1",
            "Name": "Dataset 1",
            "CreatedTime": "2023-01-01T00:00:00Z",
            "LastUpdatedTime": "2023-01-02T00:00:00Z",
            "PhysicalTableMap": {},
            "LogicalTableMap": {},
        }
        mock_response = {"DataSet": mock_dataset}
        mock_client.describe_data_set.return_value = mock_response

        # Call the function
        result = await qs.my_get_dataset("dataset1")

        # Verify the client was called correctly
        mock_client.describe_data_set.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID, DataSetId="dataset1"
        )

        # Verify the result
        self.assertEqual(result, mock_dataset)

    async def test_get_dataset_none_id(self):
        """Test my_get_dataset with None as dataset_id (should raise AssertionError)."""
        # Verify that passing None as dataset_id raises an AssertionError
        with pytest.raises(AssertionError, match="dataset_id cannot be None"):
            await qs.my_get_dataset(None)


class TestMyGetDashboard(IsolatedAsyncioTestCase):
    """Test cases for my_get_dashboard function."""

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    async def test_get_dashboard_with_id(self, mock_client):
        """Test my_get_dashboard with a valid dashboard_id."""
        # Setup mock response
        mock_dashboard = {
            "DashboardId": "dashboard1",
            "Name": "Dashboard 1",
            "CreatedTime": "2023-01-01T00:00:00Z",
            "LastUpdatedTime": "2023-01-02T00:00:00Z",
            "Version": {
                "VersionNumber": 1,
                "Status": "PUBLISHED",
                "Arn": "arn:aws:quicksight:us-west-2:123456789012:dashboard/dashboard1",
            },
        }
        mock_response = {"Dashboard": mock_dashboard}
        mock_client.describe_dashboard.return_value = mock_response

        # Call the function
        result = await qs.my_get_dashboard("dashboard1")

        # Verify the client was called correctly
        mock_client.describe_dashboard.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID, DashboardId="dashboard1"
        )

        # Verify the result
        self.assertEqual(result, mock_dashboard)

    async def test_get_dashboard_none_id(self):
        """Test my_get_dashboard with None as dashboard_id (should raise AssertionError)."""
        # Verify that passing None as dashboard_id raises an AssertionError
        with pytest.raises(AssertionError, match="dashboard_id cannot be None"):
            await qs.my_get_dashboard(None)


class TestMyGetDashboardDefinition(IsolatedAsyncioTestCase):
    """Test cases for my_get_dashboard_definition function."""

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    async def test_get_dashboard_definition_with_id(self, mock_client):
        """Test my_get_dashboard_definition with a valid dash_id."""
        # Setup mock response
        mock_definition = {
            "DataSetIdentifierDeclarations": [],
            "Sheets": [
                {
                    "SheetId": "sheet1",
                    "Name": "Sheet 1",
                    "Visuals": [],
                    "Layouts": [{"Configuration": {"GridLayout": {"Elements": []}}}],
                }
            ],
        }
        mock_response = {"Definition": mock_definition}
        mock_client.describe_dashboard_definition.return_value = mock_response

        # Call the function
        result = await qs.my_get_dashboard_definition("dashboard1")

        # Verify the client was called correctly
        mock_client.describe_dashboard_definition.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID, DashboardId="dashboard1"
        )

        # Verify the result
        self.assertEqual(result, mock_definition)

    async def test_get_dashboard_definition_none_id(self):
        """Test my_get_dashboard_definition with None as dash_id (should raise AssertionError)."""
        # Verify that passing None as dash_id raises an AssertionError
        with pytest.raises(AssertionError, match="dash_id cannot be None"):
            await qs.my_get_dashboard_definition(None)


class TestMyCreateDashboardDefinition(IsolatedAsyncioTestCase):
    """Test cases for my_create_dashboard_definition function."""

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.json.load")
    @patch("builtins.open")
    async def test_create_dashboard_definition_success(
        self, mock_open, mock_json_load, mock_client
    ):
        """Test my_create_dashboard_definition with valid parameters."""
        # Setup mock response for json.load
        mock_definition = {
            "DataSetIdentifierDeclarations": [
                {"Identifier": "placeholder", "DataSetArn": "placeholder"}
            ],
            "Sheets": [{"SheetId": "sheet1", "Name": "Sheet 1", "Visuals": []}],
        }
        mock_json_load.return_value = mock_definition

        # Setup mock response for client.create_dashboard
        mock_response = {
            "Status": 200,
            "DashboardId": "dashboard1",
            "Arn": "arn:aws:quicksight:us-west-2:123456789012:dashboard/dashboard1",
            "VersionArn": "arn:aws:quicksight:us-west-2:123456789012:dashboard/dashboard1/version/1",
            "RequestId": "request-123",
        }
        mock_client.create_dashboard.return_value = mock_response

        # Call the function
        result = await qs.my_create_dashboard_definition(
            "dashboard1",
            "Dashboard 1",
            "dataset1",
            "arn:aws:quicksight:us-west-2:123456789012:dataset/dataset1",
        )

        # Verify open was called correctly
        mock_open.assert_called_once_with(
            "./resources/json_definitions/empty_dashboard_definition.json",
            "r",
        )

        # Verify json.load was called correctly
        mock_json_load.assert_called_once()

        # Verify the definition was updated correctly
        self.assertEqual(
            mock_definition["DataSetIdentifierDeclarations"][0]["Identifier"], "dataset1"
        )
        self.assertEqual(
            mock_definition["DataSetIdentifierDeclarations"][0]["DataSetArn"],
            "arn:aws:quicksight:us-west-2:123456789012:dataset/dataset1",
        )

        # change account ID to pull from os.env.get something?
        account_id = os.environ.get("AWS_ACCOUNT_ID", "123456789012")
        username = os.environ.get("AWS_USERNAME", "test_username")

        principal_arn = "arn:aws:quicksight:us-east-1:" + account_id + ":user/default/" + username

        # Verify client.create_dashboard was called correctly
        mock_client.create_dashboard.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID,
            DashboardId="dashboard1",
            Name="Dashboard 1",
            Definition=mock_definition,
            Permissions=[
                {
                    "Principal": principal_arn,
                    "Actions": [
                        "quicksight:DescribeDashboard",
                        "quicksight:ListDashboardVersions",
                        "quicksight:UpdateDashboardPermissions",
                        "quicksight:QueryDashboard",
                        "quicksight:UpdateDashboard",
                        "quicksight:DeleteDashboard",
                        "quicksight:DescribeDashboardPermissions",
                        "quicksight:UpdateDashboardPublishedVersion",
                    ],
                },
            ],
        )

        # Verify the result
        self.assertEqual(result, mock_response)

    async def test_create_dashboard_definition_none_dash_id(self):
        """Test my_create_dashboard_definition with None as dash_id (should raise AssertionError)."""
        # Verify that passing None as dash_id raises an AssertionError
        with pytest.raises(AssertionError, match="dash_id cannot be None"):
            await qs.my_create_dashboard_definition(
                None,
                "Dashboard 1",
                "dataset1",
                "arn:aws:quicksight:us-west-2:123456789012:dataset/dataset1",
            )

    async def test_create_dashboard_definition_none_dash_name(self):
        """Test my_create_dashboard_definition with None as dash_name (should raise AssertionError)."""
        # Verify that passing None as dash_name raises an AssertionError
        with pytest.raises(AssertionError, match="dash_name cannot be None"):
            await qs.my_create_dashboard_definition(
                "dashboard1",
                None,
                "dataset1",
                "arn:aws:quicksight:us-west-2:123456789012:dataset/dataset1",
            )

    async def test_create_dashboard_definition_none_dataset_id(self):
        """Test my_create_dashboard_definition with None as dataset_id (should raise AssertionError)."""
        # Verify that passing None as dataset_id raises an AssertionError
        with pytest.raises(AssertionError, match="dataset_id cannot be None"):
            await qs.my_create_dashboard_definition(
                "dashboard1",
                "Dashboard 1",
                None,
                "arn:aws:quicksight:us-west-2:123456789012:dataset/dataset1",
            )

    async def test_create_dashboard_definition_none_dataset_arn(self):
        """Test my_create_dashboard_definition with None as dataset_arn (should raise AssertionError)."""
        # Verify that passing None as dataset_arn raises an AssertionError
        with pytest.raises(AssertionError, match="dataset_arn cannot be None"):
            await qs.my_create_dashboard_definition("dashboard1", "Dashboard 1", "dataset1", None)

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.json.load")
    @patch("builtins.open")
    async def test_create_dashboard_definition_file_error(self, mock_open, mock_json_load):
        """Test my_create_dashboard_definition when there's an error opening the JSON file."""
        # Setup mock to raise an exception
        mock_open.side_effect = FileNotFoundError("File not found")

        # Verify the exception is propagated
        with self.assertRaises(FileNotFoundError) as context:
            await qs.my_create_dashboard_definition(
                "dashboard1",
                "Dashboard 1",
                "dataset1",
                "arn:aws:quicksight:us-west-2:123456789012:dataset/dataset1",
            )

        # Verify the exception message
        self.assertEqual(str(context.exception), "File not found")


class TestMyUpdateDashboardAddSheet(IsolatedAsyncioTestCase):
    """Test cases for my_update_dashboard_add_sheet function."""

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.get_current_dashboard_definition")
    async def test_update_dashboard_add_sheet_success(self, mock_get_definition, mock_client):
        """Test my_update_dashboard_add_sheet with valid parameters."""
        # Setup mock response for get_current_dashboard_definition
        mock_definition = {
            "DataSetIdentifierDeclarations": [],
            "Sheets": [{"SheetId": "sheet1", "Name": "Sheet 1", "Visuals": []}],
        }
        mock_get_definition.return_value = mock_definition

        # Setup mock response for client.update_dashboard
        mock_response = {
            "Status": 200,
            "DashboardId": "dashboard1",
            "VersionArn": "arn:aws:quicksight:us-west-2:123456789012:dashboard/dashboard1/version/2",
            "RequestId": "request-123",
        }
        mock_client.update_dashboard.return_value = mock_response

        # Call the function
        result = await qs.my_update_dashboard_add_sheet(
            "dashboard1", "Dashboard 1", "sheet2", "Sheet 2"
        )

        # Verify get_current_dashboard_definition was called correctly
        mock_get_definition.assert_called_once_with("dashboard1")

        # Verify the sheet was added to the definition
        self.assertEqual(len(mock_definition["Sheets"]), 2)
        self.assertEqual(mock_definition["Sheets"][1]["SheetId"], "sheet2")
        self.assertEqual(mock_definition["Sheets"][1]["Name"], "Sheet 2")
        self.assertEqual(mock_definition["Sheets"][1]["ContentType"], "INTERACTIVE")
        self.assertEqual(mock_definition["Sheets"][1]["Visuals"], [])
        self.assertEqual(len(mock_definition["Sheets"][1]["Layouts"]), 1)

        # Verify client.update_dashboard was called correctly
        mock_client.update_dashboard.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID,
            DashboardId="dashboard1",
            Name="Dashboard 1",
            Definition=mock_definition,
        )

        # Verify the result
        self.assertEqual(result, mock_response)

    async def test_update_dashboard_add_sheet_none_dash_id(self):
        """Test my_update_dashboard_add_sheet with None as dash_id (should raise AssertionError)."""
        # Verify that passing None as dash_id raises an AssertionError
        with pytest.raises(AssertionError, match="dash_id cannot be None"):
            await qs.my_update_dashboard_add_sheet(None, "Dashboard 1", "sheet2", "Sheet 2")

    async def test_update_dashboard_add_sheet_none_dash_name(self):
        """Test my_update_dashboard_add_sheet with None as dash_name (should raise AssertionError)."""
        # Verify that passing None as dash_name raises an AssertionError
        with pytest.raises(AssertionError, match="dash_name cannot be None"):
            await qs.my_update_dashboard_add_sheet("dashboard1", None, "sheet2", "Sheet 2")

    async def test_update_dashboard_add_sheet_none_sheet_id(self):
        """Test my_update_dashboard_add_sheet with None as sheet_id (should raise AssertionError)."""
        # Verify that passing None as sheet_id raises an AssertionError
        with pytest.raises(AssertionError, match="sheet_id cannot be None"):
            await qs.my_update_dashboard_add_sheet("dashboard1", "Dashboard 1", None, "Sheet 2")

    async def test_update_dashboard_add_sheet_none_sheet_name(self):
        """Test my_update_dashboard_add_sheet with None as sheet_name (should raise AssertionError)."""
        # Verify that passing None as sheet_name raises an AssertionError
        with pytest.raises(AssertionError, match="sheet_name cannot be None"):
            await qs.my_update_dashboard_add_sheet("dashboard1", "Dashboard 1", "sheet2", None)


class TestMyUpdateDashboardRemoveSheet(IsolatedAsyncioTestCase):
    """Test cases for my_update_dashboard_remove_sheet function."""

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.get_current_dashboard_definition")
    async def test_update_dashboard_remove_sheet_success(self, mock_get_definition, mock_client):
        """Test my_update_dashboard_remove_sheet with valid parameters."""
        # Setup mock response for get_current_dashboard_definition
        mock_definition = {
            "DataSetIdentifierDeclarations": [],
            "Sheets": [
                {"SheetId": "sheet1", "Name": "Sheet 1", "Visuals": []},
                {"SheetId": "sheet2", "Name": "Sheet 2", "Visuals": []},
            ],
        }
        mock_get_definition.return_value = mock_definition

        # Setup mock response for client.update_dashboard
        mock_response = {
            "Status": 200,
            "DashboardId": "dashboard1",
            "VersionArn": "arn:aws:quicksight:us-west-2:123456789012:dashboard/dashboard1/version/2",
            "RequestId": "request-123",
        }
        mock_client.update_dashboard.return_value = mock_response

        # Call the function
        result = await qs.my_update_dashboard_remove_sheet("dashboard1", "Dashboard 1", "sheet2")

        # Verify get_current_dashboard_definition was called correctly
        mock_get_definition.assert_called_once_with("dashboard1")

        # Verify the sheet was removed from the definition
        self.assertEqual(len(mock_definition["Sheets"]), 1)
        self.assertEqual(mock_definition["Sheets"][0]["SheetId"], "sheet1")

        # Verify client.update_dashboard was called correctly
        mock_client.update_dashboard.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID,
            DashboardId="dashboard1",
            Name="Dashboard 1",
            Definition=mock_definition,
        )

        # Verify the result
        self.assertEqual(result, mock_response)

    async def test_update_dashboard_remove_sheet_none_dash_id(self):
        """Test my_update_dashboard_remove_sheet with None as dash_id (should raise AssertionError)."""
        # Verify that passing None as dash_id raises an AssertionError
        with pytest.raises(AssertionError, match="dash_id cannot be None"):
            await qs.my_update_dashboard_remove_sheet(None, "Dashboard 1", "sheet2")

    async def test_update_dashboard_remove_sheet_none_dash_name(self):
        """Test my_update_dashboard_remove_sheet with None as dash_name (should raise AssertionError)."""
        # Verify that passing None as dash_name raises an AssertionError
        with pytest.raises(AssertionError, match="dash_name cannot be None"):
            await qs.my_update_dashboard_remove_sheet("dashboard1", None, "sheet2")

    async def test_update_dashboard_remove_sheet_none_sheet_id(self):
        """Test my_update_dashboard_remove_sheet with None as sheet_id (should raise AssertionError)."""
        # Verify that passing None as sheet_id raises an AssertionError
        with pytest.raises(AssertionError, match="sheet_id cannot be None"):
            await qs.my_update_dashboard_remove_sheet("dashboard1", "Dashboard 1", None)

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.get_current_dashboard_definition")
    async def test_update_dashboard_remove_sheet_nonexistent_sheet(
        self, mock_get_definition, mock_client
    ):
        """Test my_update_dashboard_remove_sheet with a non-existent sheet_id."""
        # Setup mock response for get_current_dashboard_definition
        mock_definition = {
            "DataSetIdentifierDeclarations": [],
            "Sheets": [{"SheetId": "sheet1", "Name": "Sheet 1", "Visuals": []}],
        }
        mock_get_definition.return_value = mock_definition

        # Create a copy of the definition to compare later
        import copy

        original_definition = copy.deepcopy(mock_definition)

        # Setup mock response for client.update_dashboard
        mock_response = {
            "Status": 200,
            "DashboardId": "dashboard1",
            "VersionArn": "arn:aws:quicksight:us-west-2:123456789012:dashboard/dashboard1/version/2",
            "RequestId": "request-123",
        }
        mock_client.update_dashboard.return_value = mock_response

        # Call the function with a non-existent sheet_id
        result = await qs.my_update_dashboard_remove_sheet(
            "dashboard1", "Dashboard 1", "non_existent_sheet"
        )

        # Verify get_current_dashboard_definition was called correctly
        mock_get_definition.assert_called_once_with("dashboard1")

        # Verify no sheets were removed from the definition
        self.assertEqual(len(mock_definition["Sheets"]), 1)
        self.assertEqual(mock_definition["Sheets"][0]["SheetId"], "sheet1")
        self.assertEqual(mock_definition, original_definition)

        # Verify client.update_dashboard was still called
        mock_client.update_dashboard.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID,
            DashboardId="dashboard1",
            Name="Dashboard 1",
            Definition=mock_definition,
        )

        # Verify the result
        self.assertEqual(result, mock_response)


class TestMyUpdateDashboardPublish(IsolatedAsyncioTestCase):
    """Test cases for my_update_dashboard_publish function."""

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    async def test_update_dashboard_publish_success(self, mock_client):
        """Test my_update_dashboard_publish with valid parameters."""
        # Setup mock response for client.update_dashboard_published_version
        mock_response = {
            "Status": 200,
            "DashboardId": "dashboard1",
            "DashboardArn": "arn:aws:quicksight:us-west-2:123456789012:dashboard/dashboard1",
            "RequestId": "request-123",
        }
        mock_client.update_dashboard_published_version.return_value = mock_response

        # Call the function
        result = await qs.my_update_dashboard_publish("dashboard1", 2)

        # Verify client.update_dashboard_published_version was called correctly
        mock_client.update_dashboard_published_version.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID, DashboardId="dashboard1", VersionNumber=2
        )

        # Verify the result
        self.assertEqual(result, mock_response)

    async def test_update_dashboard_publish_none_dash_id(self):
        """Test my_update_dashboard_publish with None as dash_id (should raise AssertionError)."""
        # Verify that passing None as dash_id raises an AssertionError
        with pytest.raises(AssertionError, match="dash_id cannot be None"):
            await qs.my_update_dashboard_publish(None, 2)

    async def test_update_dashboard_publish_none_version_num(self):
        """Test my_update_dashboard_publish with None as version_num (should raise AssertionError)."""
        # Verify that passing None as version_num raises an AssertionError
        with pytest.raises(AssertionError, match="version_num cannot be None"):
            await qs.my_update_dashboard_publish("dashboard1", None)

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    async def test_update_dashboard_publish_invalid_version(self, mock_client):
        """Test my_update_dashboard_publish with an invalid version number."""
        # Setup mock to raise an exception for invalid version
        mock_client.update_dashboard_published_version.side_effect = Exception(
            "Version number 999 not found"
        )

        # Verify the exception is propagated
        with self.assertRaises(Exception) as context:
            await qs.my_update_dashboard_publish("dashboard1", 999)

        # Verify the exception message
        self.assertEqual(str(context.exception), "Version number 999 not found")

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    async def test_update_dashboard_publish_zero_version(self, mock_client):
        """Test my_update_dashboard_publish with version number 0."""
        # Call the function with version 0
        await qs.my_update_dashboard_publish("dashboard1", 0)

        # Verify client.update_dashboard_published_version was called with version 0
        mock_client.update_dashboard_published_version.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID, DashboardId="dashboard1", VersionNumber=0
        )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    async def test_update_dashboard_publish_negative_version(self, mock_client):
        """Test my_update_dashboard_publish with a negative version number."""
        # Call the function with a negative version
        await qs.my_update_dashboard_publish("dashboard1", -1)

        # Verify client.update_dashboard_published_version was called with the negative version
        mock_client.update_dashboard_published_version.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID, DashboardId="dashboard1", VersionNumber=-1
        )


class TestMyUpdateDashboardRemoveVisual(IsolatedAsyncioTestCase):
    """Test cases for my_update_dashboard_remove_visual function."""

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.update_visual")
    async def test_update_dashboard_remove_visual_success(
        self, mock_update_visual, mock_get_current_visuals, mock_client
    ):
        """Test my_update_dashboard_remove_visual with valid parameters."""
        # Setup mock visuals
        mock_visuals = [
            {"BarChartVisual": {"VisualId": "visual1", "Title": {"Visibility": "VISIBLE"}}},
            {"LineChartVisual": {"VisualId": "visual2", "Title": {"Visibility": "VISIBLE"}}},
        ]
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock updated definition
        mock_updated_definition = {
            "DataSetIdentifierDeclarations": [],
            "Sheets": [
                {
                    "SheetId": "sheet1",
                    "Name": "Sheet 1",
                    "Visuals": [
                        {
                            "LineChartVisual": {
                                "VisualId": "visual2",
                                "Title": {"Visibility": "VISIBLE"},
                            }
                        }
                    ],
                }
            ],
        }
        mock_update_visual.return_value = mock_updated_definition

        # Setup mock response for client.update_dashboard
        mock_response = {
            "Status": 200,
            "DashboardId": "dashboard1",
            "VersionArn": "arn:aws:quicksight:us-west-2:123456789012:dashboard/dashboard1/version/2",
            "RequestId": "request-123",
        }
        mock_client.update_dashboard.return_value = mock_response

        # Call the function
        result = await qs.my_update_dashboard_remove_visual(
            "dashboard1", "Dashboard 1", "sheet1", "BarChartVisual", "visual1"
        )

        # Verify get_current_visuals was called correctly
        mock_get_current_visuals.assert_called_once_with("dashboard1", "sheet1")

        # Verify update_visual was called with the filtered visuals (without the removed visual)
        expected_visuals = [
            {"LineChartVisual": {"VisualId": "visual2", "Title": {"Visibility": "VISIBLE"}}}
        ]
        mock_update_visual.assert_called_once_with("dashboard1", "sheet1", expected_visuals)

        # Verify client.update_dashboard was called correctly
        mock_client.update_dashboard.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID,
            DashboardId="dashboard1",
            Name="Dashboard 1",
            Definition=mock_updated_definition,
        )

        # Verify the result
        self.assertEqual(result, mock_response)

    async def test_update_dashboard_remove_visual_none_dash_id(self):
        """Test my_update_dashboard_remove_visual with None as dash_id (should raise AssertionError)."""
        # Verify that passing None as dash_id raises an AssertionError
        with pytest.raises(AssertionError, match="dash_id cannot be None"):
            await qs.my_update_dashboard_remove_visual(
                None, "Dashboard 1", "sheet1", "BarChartVisual", "visual1"
            )

    async def test_update_dashboard_remove_visual_none_dash_name(self):
        """Test my_update_dashboard_remove_visual with None as dash_name (should raise AssertionError)."""
        # Verify that passing None as dash_name raises an AssertionError
        with pytest.raises(AssertionError, match="dash_name cannot be None"):
            await qs.my_update_dashboard_remove_visual(
                "dashboard1", None, "sheet1", "BarChartVisual", "visual1"
            )

    async def test_update_dashboard_remove_visual_none_sheet_id(self):
        """Test my_update_dashboard_remove_visual with None as sheet_id (should raise AssertionError)."""
        # Verify that passing None as sheet_id raises an AssertionError
        with pytest.raises(AssertionError, match="sheet_id cannot be None"):
            await qs.my_update_dashboard_remove_visual(
                "dashboard1", "Dashboard 1", None, "BarChartVisual", "visual1"
            )

    async def test_update_dashboard_remove_visual_none_visual_type(self):
        """Test my_update_dashboard_remove_visual with None as visual_type (should raise AssertionError)."""
        # Verify that passing None as visual_type raises an AssertionError
        with pytest.raises(AssertionError, match="visual_type cannot be None"):
            await qs.my_update_dashboard_remove_visual(
                "dashboard1", "Dashboard 1", "sheet1", None, "visual1"
            )

    async def test_update_dashboard_remove_visual_none_visual_id(self):
        """Test my_update_dashboard_remove_visual with None as visual_id (should raise AssertionError)."""
        # Verify that passing None as visual_id raises an AssertionError
        with pytest.raises(AssertionError, match="visual_id cannot be None"):
            await qs.my_update_dashboard_remove_visual(
                "dashboard1", "Dashboard 1", "sheet1", "BarChartVisual", None
            )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.update_visual")
    async def test_update_dashboard_remove_visual_not_found(
        self, mock_update_visual, mock_get_current_visuals, mock_client
    ):
        """Test my_update_dashboard_remove_visual when the visual is not found."""
        # Setup mock visuals (without the visual we're trying to remove)
        mock_visuals = [
            {"LineChartVisual": {"VisualId": "visual2", "Title": {"Visibility": "VISIBLE"}}}
        ]
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock updated definition (unchanged since visual not found)
        mock_updated_definition = {
            "DataSetIdentifierDeclarations": [],
            "Sheets": [
                {
                    "SheetId": "sheet1",
                    "Name": "Sheet 1",
                    "Visuals": mock_visuals,
                }
            ],
        }
        mock_update_visual.return_value = mock_updated_definition

        # Setup mock response for client.update_dashboard
        mock_response = {
            "Status": 200,
            "DashboardId": "dashboard1",
            "VersionArn": "arn:aws:quicksight:us-west-2:123456789012:dashboard/dashboard1/version/2",
            "RequestId": "request-123",
        }
        mock_client.update_dashboard.return_value = mock_response

        # Call the function with a visual that doesn't exist
        result = await qs.my_update_dashboard_remove_visual(
            "dashboard1", "Dashboard 1", "sheet1", "BarChartVisual", "nonexistent_visual"
        )

        # Verify get_current_visuals was called correctly
        mock_get_current_visuals.assert_called_once_with("dashboard1", "sheet1")

        # Verify update_visual was called with the unchanged visuals
        mock_update_visual.assert_called_once_with("dashboard1", "sheet1", mock_visuals)

        # Verify client.update_dashboard was called correctly
        mock_client.update_dashboard.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID,
            DashboardId="dashboard1",
            Name="Dashboard 1",
            Definition=mock_updated_definition,
        )

        # Verify the result
        self.assertEqual(result, mock_response)

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.update_visual")
    async def test_update_dashboard_remove_visual_update_error(
        self, mock_update_visual, mock_get_current_visuals
    ):
        """Test my_update_dashboard_remove_visual when update_visual raises an exception."""
        # Setup mock visuals
        mock_visuals = [
            {"BarChartVisual": {"VisualId": "visual1", "Title": {"Visibility": "VISIBLE"}}},
            {"LineChartVisual": {"VisualId": "visual2", "Title": {"Visibility": "VISIBLE"}}},
        ]
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock to raise an exception
        mock_update_visual.side_effect = Exception("Update Error")

        # Verify the exception is propagated
        with self.assertRaises(Exception) as context:
            await qs.my_update_dashboard_remove_visual(
                "dashboard1", "Dashboard 1", "sheet1", "BarChartVisual", "visual1"
            )

        # Verify the exception message
        self.assertEqual(str(context.exception), "Update Error")

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.update_visual")
    async def test_update_dashboard_remove_visual_no_visuals(
        self, mock_update_visual, mock_get_current_visuals, mock_client
    ):
        """Test my_update_dashboard_remove_visual when there are no visuals."""
        # Setup mock with no visuals
        mock_get_current_visuals.return_value = []

        # Setup mock updated definition
        mock_updated_definition = {
            "DataSetIdentifierDeclarations": [],
            "Sheets": [
                {
                    "SheetId": "sheet1",
                    "Name": "Sheet 1",
                    "Visuals": [],
                }
            ],
        }
        mock_update_visual.return_value = mock_updated_definition

        # Setup mock response for client.update_dashboard
        mock_response = {
            "Status": 200,
            "DashboardId": "dashboard1",
            "VersionArn": "arn:aws:quicksight:us-west-2:123456789012:dashboard/dashboard1/version/2",
            "RequestId": "request-123",
        }
        mock_client.update_dashboard.return_value = mock_response

        # Call the function
        result = await qs.my_update_dashboard_remove_visual(
            "dashboard1", "Dashboard 1", "sheet1", "BarChartVisual", "visual1"
        )

        # Verify get_current_visuals was called correctly
        mock_get_current_visuals.assert_called_once_with("dashboard1", "sheet1")

        # Verify update_visual was called with empty visuals
        mock_update_visual.assert_called_once_with("dashboard1", "sheet1", [])

        # Verify client.update_dashboard was called correctly
        mock_client.update_dashboard.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID,
            DashboardId="dashboard1",
            Name="Dashboard 1",
            Definition=mock_updated_definition,
        )

        # Verify the result
        self.assertEqual(result, mock_response)

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.get_current_visuals")
    async def test_update_dashboard_remove_visual_none_visuals(self, mock_get_current_visuals):
        """Test my_update_dashboard_remove_visual when get_current_visuals returns None."""
        # Setup mock to return None (sheet not found)
        mock_get_current_visuals.return_value = None

        # Verify the function raises an exception when visuals is None
        with self.assertRaises(Exception):
            await qs.my_update_dashboard_remove_visual(
                "dashboard1", "Dashboard 1", "sheet1", "BarChartVisual", "visual1"
            )


class TestMyUpdateDashboardAddVisualLayout(IsolatedAsyncioTestCase):
    """Test cases for my_update_dashboard_add_visual_layout function."""

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.get_current_layouts")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.update_layout")
    async def test_update_dashboard_add_visual_layout_success(
        self, mock_update_layout, mock_get_current_layouts, mock_client
    ):
        """Test my_update_dashboard_add_visual_layout with valid parameters."""
        # Setup mock layouts
        mock_layouts = [
            {
                "ElementId": "visual1",
                "ElementType": "VISUAL",
                "ColumnIndex": 0,
                "RowIndex": 0,
                "ColumnSpan": 18,
                "RowSpan": 12,
            },
        ]
        mock_get_current_layouts.return_value = mock_layouts

        # Setup mock updated definition
        mock_updated_definition = {
            "DataSetIdentifierDeclarations": [],
            "Sheets": [
                {
                    "SheetId": "sheet1",
                    "Name": "Sheet 1",
                    "Layouts": [
                        {
                            "Configuration": {
                                "GridLayout": {
                                    "Elements": [
                                        {
                                            "ElementId": "visual1",
                                            "ElementType": "VISUAL",
                                            "ColumnIndex": 0,
                                            "RowIndex": 0,
                                            "ColumnSpan": 18,
                                            "RowSpan": 12,
                                        },
                                        {
                                            "ElementId": "visual2",
                                            "ElementType": "VISUAL",
                                            "ColumnIndex": 18,
                                            "RowIndex": 12,
                                            "ColumnSpan": 18,
                                            "RowSpan": 12,
                                        },
                                    ]
                                }
                            }
                        }
                    ],
                }
            ],
        }
        mock_update_layout.return_value = mock_updated_definition

        # Setup mock response for client.update_dashboard
        mock_response = {
            "Status": 200,
            "DashboardId": "dashboard1",
            "VersionArn": "arn:aws:quicksight:us-west-2:123456789012:dashboard/dashboard1/version/2",
            "RequestId": "request-123",
        }
        mock_client.update_dashboard.return_value = mock_response

        # Call the function
        result = await qs.my_update_dashboard_add_visual_layout(
            "dashboard1", "Dashboard 1", "sheet1", "visual2", 18, 12
        )

        # Verify get_current_layouts was called correctly
        mock_get_current_layouts.assert_called_once_with("dashboard1", "sheet1")

        # Verify update_layout was called with the updated layouts
        expected_layouts = [
            {
                "ElementId": "visual1",
                "ElementType": "VISUAL",
                "ColumnIndex": 0,
                "RowIndex": 0,
                "ColumnSpan": 18,
                "RowSpan": 12,
            },
            {
                "ElementId": "visual2",
                "ElementType": "VISUAL",
                "ColumnIndex": 18,
                "RowIndex": 12,
                "ColumnSpan": 18,
                "RowSpan": 12,
            },
        ]
        mock_update_layout.assert_called_once_with("dashboard1", "sheet1", expected_layouts)

        # Verify client.update_dashboard was called correctly
        mock_client.update_dashboard.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID,
            DashboardId="dashboard1",
            Name="Dashboard 1",
            Definition=mock_updated_definition,
        )

        # Verify the result
        self.assertEqual(result, mock_response)

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.get_current_layouts")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.update_layout")
    async def test_update_dashboard_add_visual_layout_custom_spans(
        self, mock_update_layout, mock_get_current_layouts, mock_client
    ):
        """Test my_update_dashboard_add_visual_layout with custom column_span and row_span."""
        # Setup mock layouts
        mock_layouts = [
            {
                "ElementId": "visual1",
                "ElementType": "VISUAL",
                "ColumnIndex": 0,
                "RowIndex": 0,
                "ColumnSpan": 18,
                "RowSpan": 12,
            },
        ]
        mock_get_current_layouts.return_value = mock_layouts

        # Setup mock updated definition
        mock_updated_definition = {
            "DataSetIdentifierDeclarations": [],
            "Sheets": [
                {
                    "SheetId": "sheet1",
                    "Name": "Sheet 1",
                    "Layouts": [
                        {
                            "Configuration": {
                                "GridLayout": {
                                    "Elements": [
                                        {
                                            "ElementId": "visual1",
                                            "ElementType": "VISUAL",
                                            "ColumnIndex": 0,
                                            "RowIndex": 0,
                                            "ColumnSpan": 18,
                                            "RowSpan": 12,
                                        },
                                        {
                                            "ElementId": "visual2",
                                            "ElementType": "VISUAL",
                                            "ColumnIndex": 18,
                                            "RowIndex": 12,
                                            "ColumnSpan": 24,
                                            "RowSpan": 16,
                                        },
                                    ]
                                }
                            }
                        }
                    ],
                }
            ],
        }
        mock_update_layout.return_value = mock_updated_definition

        # Setup mock response for client.update_dashboard
        mock_response = {
            "Status": 200,
            "DashboardId": "dashboard1",
            "VersionArn": "arn:aws:quicksight:us-west-2:123456789012:dashboard/dashboard1/version/2",
            "RequestId": "request-123",
        }
        mock_client.update_dashboard.return_value = mock_response

        # Call the function with custom spans
        result = await qs.my_update_dashboard_add_visual_layout(
            "dashboard1", "Dashboard 1", "sheet1", "visual2", 18, 12, 24, 16
        )

        # Verify get_current_layouts was called correctly
        mock_get_current_layouts.assert_called_once_with("dashboard1", "sheet1")

        # Verify update_layout was called with the updated layouts including custom spans
        expected_layouts = [
            {
                "ElementId": "visual1",
                "ElementType": "VISUAL",
                "ColumnIndex": 0,
                "RowIndex": 0,
                "ColumnSpan": 18,
                "RowSpan": 12,
            },
            {
                "ElementId": "visual2",
                "ElementType": "VISUAL",
                "ColumnIndex": 18,
                "RowIndex": 12,
                "ColumnSpan": 24,
                "RowSpan": 16,
            },
        ]
        mock_update_layout.assert_called_once_with("dashboard1", "sheet1", expected_layouts)

        # Verify client.update_dashboard was called correctly
        mock_client.update_dashboard.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID,
            DashboardId="dashboard1",
            Name="Dashboard 1",
            Definition=mock_updated_definition,
        )

        # Verify the result
        self.assertEqual(result, mock_response)

    async def test_update_dashboard_add_visual_layout_none_dash_id(self):
        """Test my_update_dashboard_add_visual_layout with None as dash_id (should raise AssertionError)."""
        # Verify that passing None as dash_id raises an AssertionError
        with pytest.raises(AssertionError, match="dash_id cannot be None"):
            await qs.my_update_dashboard_add_visual_layout(
                None, "Dashboard 1", "sheet1", "visual1", 0, 0, 18, 12
            )

    async def test_update_dashboard_add_visual_layout_none_dash_name(self):
        """Test my_update_dashboard_add_visual_layout with None as dash_name (should raise AssertionError)."""
        # Verify that passing None as dash_name raises an AssertionError
        with pytest.raises(AssertionError, match="dash_name cannot be None"):
            await qs.my_update_dashboard_add_visual_layout(
                "dashboard1", None, "sheet1", "visual1", 0, 0, 18, 12
            )

    async def test_update_dashboard_add_visual_layout_none_sheet_id(self):
        """Test my_update_dashboard_add_visual_layout with None as sheet_id (should raise AssertionError)."""
        # Verify that passing None as sheet_id raises an AssertionError
        with pytest.raises(AssertionError, match="sheet_id cannot be None"):
            await qs.my_update_dashboard_add_visual_layout(
                "dashboard1", "Dashboard 1", None, "visual1", 0, 0, 18, 12
            )

    async def test_update_dashboard_add_visual_layout_none_visual_id(self):
        """Test my_update_dashboard_add_visual_layout with None as visual_id (should raise AssertionError)."""
        # Verify that passing None as visual_id raises an AssertionError
        with pytest.raises(AssertionError, match="visual_id cannot be None"):
            await qs.my_update_dashboard_add_visual_layout(
                "dashboard1", "Dashboard 1", "sheet1", None, 0, 0, 18, 12
            )

    async def test_update_dashboard_add_visual_layout_none_column_index(self):
        """Test my_update_dashboard_add_visual_layout with None as column_index (should raise AssertionError)."""
        # Verify that passing None as column_index raises an AssertionError
        with pytest.raises(AssertionError, match="column_index cannot be None"):
            await qs.my_update_dashboard_add_visual_layout(
                "dashboard1", "Dashboard 1", "sheet1", "visual1", None, 0, 18, 12
            )

    async def test_update_dashboard_add_visual_layout_none_row_index(self):
        """Test my_update_dashboard_add_visual_layout with None as row_index (should raise AssertionError)."""
        # Verify that passing None as row_index raises an AssertionError
        with pytest.raises(AssertionError, match="row_index cannot be None"):
            await qs.my_update_dashboard_add_visual_layout(
                "dashboard1", "Dashboard 1", "sheet1", "visual1", 0, None, 18, 12
            )

    async def test_update_dashboard_add_visual_layout_none_column_span(self):
        """Test my_update_dashboard_add_visual_layout with None as column_span (should raise AssertionError)."""
        # Verify that passing None as column_span raises an AssertionError
        with pytest.raises(AssertionError, match="column_span cannot be None"):
            await qs.my_update_dashboard_add_visual_layout(
                "dashboard1", "Dashboard 1", "sheet1", "visual1", 0, 0, None, 12
            )

    async def test_update_dashboard_add_visual_layout_none_row_span(self):
        """Test my_update_dashboard_add_visual_layout with None as row_span (should raise AssertionError)."""
        # Verify that passing None as row_span raises an AssertionError
        with pytest.raises(AssertionError, match="row_span cannot be None"):
            await qs.my_update_dashboard_add_visual_layout(
                "dashboard1", "Dashboard 1", "sheet1", "visual1", 0, 0, 18, None
            )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.get_current_layouts")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.update_layout")
    async def test_update_dashboard_add_visual_layout_update_error(
        self, mock_update_layout, mock_get_current_layouts
    ):
        """Test my_update_dashboard_add_visual_layout when update_layout raises an exception."""
        # Setup mock layouts
        mock_layouts = [
            {
                "ElementId": "visual1",
                "ElementType": "VISUAL",
                "ColumnIndex": 0,
                "RowIndex": 0,
                "ColumnSpan": 18,
                "RowSpan": 12,
            },
        ]
        mock_get_current_layouts.return_value = mock_layouts

        # Setup mock to raise an exception
        mock_update_layout.side_effect = Exception("Update Error")

        # Verify the exception is propagated
        with self.assertRaises(Exception) as context:
            await qs.my_update_dashboard_add_visual_layout(
                "dashboard1", "Dashboard 1", "sheet1", "visual2", 0, 0
            )

        # Verify the exception message
        self.assertEqual(str(context.exception), "Update Error")

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.get_current_layouts")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.update_layout")
    async def test_update_dashboard_add_visual_layout_empty_layouts(
        self, mock_update_layout, mock_get_current_layouts, mock_client
    ):
        """Test my_update_dashboard_add_visual_layout when there are no existing layouts."""
        # Setup mock with empty layouts
        mock_get_current_layouts.return_value = []

        # Setup mock updated definition
        mock_updated_definition = {
            "DataSetIdentifierDeclarations": [],
            "Sheets": [
                {
                    "SheetId": "sheet1",
                    "Name": "Sheet 1",
                    "Layouts": [
                        {
                            "Configuration": {
                                "GridLayout": {
                                    "Elements": [
                                        {
                                            "ElementId": "visual1",
                                            "ElementType": "VISUAL",
                                            "ColumnIndex": 0,
                                            "RowIndex": 0,
                                            "ColumnSpan": 18,
                                            "RowSpan": 12,
                                        },
                                    ]
                                }
                            }
                        }
                    ],
                }
            ],
        }
        mock_update_layout.return_value = mock_updated_definition

        # Setup mock response for client.update_dashboard
        mock_response = {
            "Status": 200,
            "DashboardId": "dashboard1",
            "VersionArn": "arn:aws:quicksight:us-west-2:123456789012:dashboard/dashboard1/version/2",
            "RequestId": "request-123",
        }
        mock_client.update_dashboard.return_value = mock_response

        # Call the function
        result = await qs.my_update_dashboard_add_visual_layout(
            "dashboard1", "Dashboard 1", "sheet1", "visual1", 0, 0
        )

        # Verify get_current_layouts was called correctly
        mock_get_current_layouts.assert_called_once_with("dashboard1", "sheet1")

        # Verify update_layout was called with just the new layout
        expected_layouts = [
            {
                "ElementId": "visual1",
                "ElementType": "VISUAL",
                "ColumnIndex": 0,
                "RowIndex": 0,
                "ColumnSpan": 18,
                "RowSpan": 12,
            },
        ]
        mock_update_layout.assert_called_once_with("dashboard1", "sheet1", expected_layouts)

        # Verify client.update_dashboard was called correctly
        mock_client.update_dashboard.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID,
            DashboardId="dashboard1",
            Name="Dashboard 1",
            Definition=mock_updated_definition,
        )

        # Verify the result
        self.assertEqual(result, mock_response)

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.get_current_layouts")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.update_layout")
    async def test_update_dashboard_add_visual_layout_none_layouts(
        self, mock_update_layout, mock_get_current_layouts, mock_client
    ):
        """Test my_update_dashboard_add_visual_layout when get_current_layouts returns None."""
        # Setup mock to return None (sheet not found)
        mock_get_current_layouts.return_value = None

        # Verify the function raises an exception when layouts is None
        with self.assertRaises(Exception):
            await qs.my_update_dashboard_add_visual_layout(
                "dashboard1", "Dashboard 1", "sheet1", "visual1"
            )


class TestMyUpdateDashboardDeleteVisualLayout(IsolatedAsyncioTestCase):
    """Test cases for my_update_dashboard_delete_visual_layout function."""

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.get_current_layouts")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.update_layout")
    async def test_update_dashboard_delete_visual_layout_success(
        self, mock_update_layout, mock_get_current_layouts, mock_client
    ):
        """Test my_update_dashboard_delete_visual_layout with valid parameters."""
        # Setup mock layouts with two elements
        mock_layouts = [
            {"ElementId": "visual1", "ElementType": "VISUAL", "ColumnSpan": 18, "RowSpan": 12},
            {"ElementId": "visual2", "ElementType": "VISUAL", "ColumnSpan": 18, "RowSpan": 12},
        ]
        mock_get_current_layouts.return_value = mock_layouts

        # Setup mock updated definition with one element (after deletion)
        mock_updated_definition = {
            "DataSetIdentifierDeclarations": [],
            "Sheets": [
                {
                    "SheetId": "sheet1",
                    "Name": "Sheet 1",
                    "Layouts": [
                        {
                            "Configuration": {
                                "GridLayout": {
                                    "Elements": [
                                        {
                                            "ElementId": "visual2",
                                            "ElementType": "VISUAL",
                                            "ColumnSpan": 18,
                                            "RowSpan": 12,
                                        }
                                    ]
                                }
                            }
                        }
                    ],
                }
            ],
        }
        mock_update_layout.return_value = mock_updated_definition

        # Setup mock response for client.update_dashboard
        mock_response = {
            "Status": 200,
            "DashboardId": "dashboard1",
            "VersionArn": "arn:aws:quicksight:us-west-2:123456789012:dashboard/dashboard1/version/2",
            "RequestId": "request-123",
        }
        mock_client.update_dashboard.return_value = mock_response

        # Call the function to delete visual1's layout
        result = await qs.my_update_dashboard_delete_visual_layout(
            "dashboard1", "Dashboard 1", "sheet1", "visual1"
        )

        # Verify get_current_layouts was called correctly
        mock_get_current_layouts.assert_called_once_with("dashboard1", "sheet1")

        # Verify update_layout was called with the filtered layouts (without visual1)
        expected_layouts = [
            {"ElementId": "visual2", "ElementType": "VISUAL", "ColumnSpan": 18, "RowSpan": 12}
        ]
        mock_update_layout.assert_called_once_with("dashboard1", "sheet1", expected_layouts)

        # Verify client.update_dashboard was called correctly
        mock_client.update_dashboard.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID,
            DashboardId="dashboard1",
            Name="Dashboard 1",
            Definition=mock_updated_definition,
        )

        # Verify the result
        self.assertEqual(result, mock_response)

    async def test_update_dashboard_delete_visual_layout_none_dash_id(self):
        """Test my_update_dashboard_delete_visual_layout with None as dash_id (should raise AssertionError)."""
        # Verify that passing None as dash_id raises an AssertionError
        with pytest.raises(AssertionError, match="dash_id cannot be None"):
            await qs.my_update_dashboard_delete_visual_layout(
                None, "Dashboard 1", "sheet1", "visual1"
            )

    async def test_update_dashboard_delete_visual_layout_none_dash_name(self):
        """Test my_update_dashboard_delete_visual_layout with None as dash_name (should raise AssertionError)."""
        # Verify that passing None as dash_name raises an AssertionError
        with pytest.raises(AssertionError, match="dash_name cannot be None"):
            await qs.my_update_dashboard_delete_visual_layout(
                "dashboard1", None, "sheet1", "visual1"
            )

    async def test_update_dashboard_delete_visual_layout_none_sheet_id(self):
        """Test my_update_dashboard_delete_visual_layout with None as sheet_id (should raise AssertionError)."""
        # Verify that passing None as sheet_id raises an AssertionError
        with pytest.raises(AssertionError, match="sheet_id cannot be None"):
            await qs.my_update_dashboard_delete_visual_layout(
                "dashboard1", "Dashboard 1", None, "visual1"
            )

    async def test_update_dashboard_delete_visual_layout_none_visual_id(self):
        """Test my_update_dashboard_delete_visual_layout with None as visual_id (should raise AssertionError)."""
        # Verify that passing None as visual_id raises an AssertionError
        with pytest.raises(AssertionError, match="visual_id cannot be None"):
            await qs.my_update_dashboard_delete_visual_layout(
                "dashboard1", "Dashboard 1", "sheet1", None
            )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.get_current_layouts")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.update_layout")
    async def test_update_dashboard_delete_visual_layout_not_found(
        self, mock_update_layout, mock_get_current_layouts, mock_client
    ):
        """Test my_update_dashboard_delete_visual_layout when the visual layout is not found."""
        # Setup mock layouts without the visual we're trying to delete
        mock_layouts = [
            {"ElementId": "visual2", "ElementType": "VISUAL", "ColumnSpan": 18, "RowSpan": 12}
        ]
        mock_get_current_layouts.return_value = mock_layouts

        # Setup mock updated definition (unchanged since visual not found)
        mock_updated_definition = {
            "DataSetIdentifierDeclarations": [],
            "Sheets": [
                {
                    "SheetId": "sheet1",
                    "Name": "Sheet 1",
                    "Layouts": [{"Configuration": {"GridLayout": {"Elements": mock_layouts}}}],
                }
            ],
        }
        mock_update_layout.return_value = mock_updated_definition

        # Setup mock response for client.update_dashboard
        mock_response = {
            "Status": 200,
            "DashboardId": "dashboard1",
            "VersionArn": "arn:aws:quicksight:us-west-2:123456789012:dashboard/dashboard1/version/2",
            "RequestId": "request-123",
        }
        mock_client.update_dashboard.return_value = mock_response

        # Call the function with a visual that doesn't exist
        result = await qs.my_update_dashboard_delete_visual_layout(
            "dashboard1", "Dashboard 1", "sheet1", "nonexistent_visual"
        )

        # Verify get_current_layouts was called correctly
        mock_get_current_layouts.assert_called_once_with("dashboard1", "sheet1")

        # Verify update_layout was called with the unchanged layouts
        mock_update_layout.assert_called_once_with("dashboard1", "sheet1", mock_layouts)

        # Verify client.update_dashboard was called correctly
        mock_client.update_dashboard.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID,
            DashboardId="dashboard1",
            Name="Dashboard 1",
            Definition=mock_updated_definition,
        )

        # Verify the result
        self.assertEqual(result, mock_response)

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.get_current_layouts")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.update_layout")
    async def test_update_dashboard_delete_visual_layout_update_error(
        self, mock_update_layout, mock_get_current_layouts
    ):
        """Test my_update_dashboard_delete_visual_layout when update_layout raises an exception."""
        # Setup mock layouts
        mock_layouts = [
            {"ElementId": "visual1", "ElementType": "VISUAL", "ColumnSpan": 18, "RowSpan": 12},
            {"ElementId": "visual2", "ElementType": "VISUAL", "ColumnSpan": 18, "RowSpan": 12},
        ]
        mock_get_current_layouts.return_value = mock_layouts

        # Setup mock to raise an exception
        mock_update_layout.side_effect = Exception("Update Error")

        # Verify the exception is propagated
        with self.assertRaises(Exception) as context:
            await qs.my_update_dashboard_delete_visual_layout(
                "dashboard1", "Dashboard 1", "sheet1", "visual1"
            )

        # Verify the exception message
        self.assertEqual(str(context.exception), "Update Error")

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.get_current_layouts")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.update_layout")
    async def test_update_dashboard_delete_visual_layout_empty_layouts(
        self, mock_update_layout, mock_get_current_layouts, mock_client
    ):
        """Test my_update_dashboard_delete_visual_layout when there are no layouts."""
        # Setup mock with empty layouts
        mock_get_current_layouts.return_value = []

        # Setup mock updated definition with empty layouts
        mock_updated_definition = {
            "DataSetIdentifierDeclarations": [],
            "Sheets": [
                {
                    "SheetId": "sheet1",
                    "Name": "Sheet 1",
                    "Layouts": [{"Configuration": {"GridLayout": {"Elements": []}}}],
                }
            ],
        }
        mock_update_layout.return_value = mock_updated_definition

        # Setup mock response for client.update_dashboard
        mock_response = {
            "Status": 200,
            "DashboardId": "dashboard1",
            "VersionArn": "arn:aws:quicksight:us-west-2:123456789012:dashboard/dashboard1/version/2",
            "RequestId": "request-123",
        }
        mock_client.update_dashboard.return_value = mock_response

        # Call the function
        result = await qs.my_update_dashboard_delete_visual_layout(
            "dashboard1", "Dashboard 1", "sheet1", "visual1"
        )

        # Verify get_current_layouts was called correctly
        mock_get_current_layouts.assert_called_once_with("dashboard1", "sheet1")

        # Verify update_layout was called with empty layouts
        mock_update_layout.assert_called_once_with("dashboard1", "sheet1", [])

        # Verify client.update_dashboard was called correctly
        mock_client.update_dashboard.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID,
            DashboardId="dashboard1",
            Name="Dashboard 1",
            Definition=mock_updated_definition,
        )

        # Verify the result
        self.assertEqual(result, mock_response)

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.quicksight.get_current_layouts")
    async def test_update_dashboard_delete_visual_layout_none_layouts(
        self, mock_get_current_layouts
    ):
        """Test my_update_dashboard_delete_visual_layout when get_current_layouts returns None."""
        # Setup mock to return None (sheet not found)
        mock_get_current_layouts.return_value = None

        # Verify the function raises an exception when layouts is None
        with self.assertRaises(Exception):
            await qs.my_update_dashboard_delete_visual_layout(
                "dashboard1", "Dashboard 1", "sheet1", "visual1"
            )
