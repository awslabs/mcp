from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import patch

import pytest

import sys
from pathlib import Path

qs_mcp_directory = Path(__file__).parent.parent
sys.path.append(str(qs_mcp_directory))
print(qs_mcp_directory)

import awslabs.aws_quicksight_dashboards_mcp_server.resources.table as table
import awslabs.aws_quicksight_dashboards_mcp_server.quicksight as qs


class TestMyUpdateDashboardAddTable(IsolatedAsyncioTestCase):
    """
    Test cases for my_update_dashboard_add_table function.

    Tests visual creation (getting chart object, update) and parameter validation
    """

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.table.qs.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.table.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.table.qs.update_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.table.create_table_visual")
    async def test_update_dashboard_add_table_success(
        self, mock_create_table_visual, mock_update_visual, mock_get_current_visuals, mock_client
    ):
        """Test my_update_dashboard_add_table with valid parameters."""
        # Setup mock visuals
        mock_visuals = [
            {"LineChartVisual": {"VisualId": "visual1", "Title": {"Visibility": "VISIBLE"}}},
        ]
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock table
        mock_table = {
            "TableVisual": {
                "VisualId": "visual2",
                "Title": {"Visibility": "VISIBLE"},
                "ChartConfiguration": {
                    "FieldWells": {"TableAggregatedFieldWells": {}},
                },
            }
        }
        mock_create_table_visual.return_value = mock_table

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
                                "VisualId": "visual1",
                                "Title": {"Visibility": "VISIBLE"},
                            }
                        },
                        mock_table,
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
        result = await table.my_update_dashboard_add_table(
            dash_id="dashboard1",
            dash_name="Dashboard 1",
            sheet_id="sheet1",
            visual_id="visual2",
            dataset_id="dataset1",
            category_column_names=["product", "region"],
            date_column_names=["Date"],
            value_column_names=["sales", "profit"],
            value_column_aggregation=["SUM", "AVERAGE"],
        )

        # Verify get_current_visuals was called correctly
        mock_get_current_visuals.assert_called_once_with("dashboard1", "sheet1")

        # Verify create_table_visual was called with the correct parameters
        expected_table_params = {
            "visual_id": "visual2",
            "dataset_id": "dataset1",
            "category_column_names": ["product", "region"],
            "date_column_names": ["Date"],
            "date_granularity": "",
            "value_column_names": ["sales", "profit"],
            "value_column_aggregation": ["SUM", "AVERAGE"],
        }
        mock_create_table_visual.assert_called_once_with(expected_table_params)

        # Verify update_visual was called with the updated visuals
        expected_visuals = [
            {"LineChartVisual": {"VisualId": "visual1", "Title": {"Visibility": "VISIBLE"}}},
            mock_table,
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

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.table.qs.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.table.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.table.qs.update_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.table.create_table_visual")
    async def test_update_dashboard_add_table_empty_category_columns(
        self, mock_create_table_visual, mock_update_visual, mock_get_current_visuals, mock_client
    ):
        """Test my_update_dashboard_add_table with empty category_column_names."""
        # Setup mock visuals
        mock_visuals = [
            {"LineChartVisual": {"VisualId": "visual1", "Title": {"Visibility": "VISIBLE"}}},
        ]
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock table
        mock_table = {
            "TableVisual": {
                "VisualId": "visual2",
                "Title": {"Visibility": "VISIBLE"},
                "ChartConfiguration": {
                    "FieldWells": {
                        "TableAggregatedFieldWells": {
                            "GroupBy": [],
                            "Values": [
                                {
                                    "NumericalMeasureField": {
                                        "FieldId": "fieldid1",
                                        "Column": {
                                            "DataSetIdentifier": "SaaS-Sales.csv",
                                            "ColumnName": "sales",
                                        },
                                        "AggregationFunction": {
                                            "SimpleNumericalAggregation": "SUM"
                                        },
                                    }
                                }
                            ],
                        }
                    },
                },
            }
        }
        mock_create_table_visual.return_value = mock_table

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
                                "VisualId": "visual1",
                                "Title": {"Visibility": "VISIBLE"},
                            }
                        },
                        mock_table,
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

        # Call the function with empty category_column_names
        result = await table.my_update_dashboard_add_table(
            dash_id="dashboard1",
            dash_name="Dashboard 1",
            sheet_id="sheet1",
            visual_id="visual2",
            dataset_id="dataset1",
            category_column_names=[],  # Empty category columns
            date_column_names=["Date"],
            value_column_names=["sales"],
            value_column_aggregation=["SUM"],
        )

        # Verify create_table_visual was called with the correct parameters
        expected_table_params = {
            "visual_id": "visual2",
            "dataset_id": "dataset1",
            "category_column_names": [],  # Empty category columns
            "date_column_names": ["Date"],
            "date_granularity": "",
            "value_column_names": ["sales"],
            "value_column_aggregation": ["SUM"],
        }
        mock_create_table_visual.assert_called_once_with(expected_table_params)

        # Verify the result
        self.assertEqual(result, mock_response)

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.table.qs.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.table.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.table.qs.update_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.table.create_table_visual")
    async def test_update_dashboard_add_table_empty_value_columns(
        self, mock_create_table_visual, mock_update_visual, mock_get_current_visuals, mock_client
    ):
        """Test my_update_dashboard_add_table with empty value_column_names."""
        # Setup mock visuals
        mock_visuals = [
            {"LineChartVisual": {"VisualId": "visual1", "Title": {"Visibility": "VISIBLE"}}},
        ]
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock table
        mock_table = {
            "TableVisual": {
                "VisualId": "visual2",
                "Title": {"Visibility": "VISIBLE"},
                "ChartConfiguration": {
                    "FieldWells": {
                        "TableAggregatedFieldWells": {
                            "GroupBy": [
                                {
                                    "CategoricalDimensionField": {
                                        "FieldId": "fieldid1",
                                        "Column": {
                                            "DataSetIdentifier": "SaaS-Sales.csv",
                                            "ColumnName": "product",
                                        },
                                        "AggregationFunction": {
                                            "SimpleNumericalAggregation": "SUM"
                                        },
                                    },
                                    "DateDimensionField": {
                                        "FieldId": "fieldid2",
                                        "Column": {
                                            "DataSetIdentifier": "SaaS-Sales.csv",
                                            "ColumnName": "Date",
                                        },
                                    },
                                }
                            ],
                            "Values": [],
                        }
                    },
                },
            }
        }
        mock_create_table_visual.return_value = mock_table

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
                                "VisualId": "visual1",
                                "Title": {"Visibility": "VISIBLE"},
                            }
                        },
                        mock_table,
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

        # Call the function with empty value_column_names and value_column_aggregation
        result = await table.my_update_dashboard_add_table(
            dash_id="dashboard1",
            dash_name="Dashboard 1",
            sheet_id="sheet1",
            visual_id="visual2",
            dataset_id="dataset1",
            category_column_names=["product"],
            date_column_names=["Date"],
            value_column_names=[],  # Empty value columns
            value_column_aggregation=[],  # Empty value column aggregation
        )

        # Verify create_table_visual was called with the correct parameters
        expected_table_params = {
            "visual_id": "visual2",
            "dataset_id": "dataset1",
            "category_column_names": ["product"],
            "date_column_names": ["Date"],
            "date_granularity": "",
            "value_column_names": [],  # Empty value columns
            "value_column_aggregation": [],  # Empty value column aggregation
        }
        mock_create_table_visual.assert_called_once_with(expected_table_params)

        # Verify the result
        self.assertEqual(result, mock_response)

    async def test_update_dashboard_add_table_length_mismatch(self):
        """Test my_update_dashboard_add_table with length mismatch between value_column_names and value_column_aggregation."""
        # Verify that passing mismatched lengths raises an AssertionError
        with pytest.raises(
            AssertionError, match="Length mismatch. Each value column needs an aggregation function"
        ):
            await table.my_update_dashboard_add_table(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                category_column_names=["product", "region"],
                date_column_names=["Date"],
                value_column_names=["sales", "profit", "quantity"],  # 3 value columns
                value_column_aggregation=["SUM", "AVERAGE"],  # Only 2 aggregation functions
            )

    async def test_update_dashboard_add_table_none_dash_id(self):
        """Test my_update_dashboard_add_table with None as dash_id (should raise AssertionError)."""
        # Verify that passing None as dash_id raises an AssertionError
        with pytest.raises(AssertionError, match="dash_id cannot be None"):
            await table.my_update_dashboard_add_table(
                dash_id=None,
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                category_column_names=["product", "region"],
                date_column_names=["Date"],
                value_column_names=["sales", "profit"],
                value_column_aggregation=["SUM", "AVERAGE"],
            )

    async def test_update_dashboard_add_table_none_dash_name(self):
        """Test my_update_dashboard_add_table with None as dash_name (should raise AssertionError)."""
        # Verify that passing None as dash_name raises an AssertionError
        with pytest.raises(AssertionError, match="dash_name cannot be None"):
            await table.my_update_dashboard_add_table(
                dash_id="dashboard1",
                dash_name=None,
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                category_column_names=["product", "region"],
                date_column_names=["Date"],
                value_column_names=["sales", "profit"],
                value_column_aggregation=["SUM", "AVERAGE"],
            )

    async def test_update_dashboard_add_table_none_sheet_id(self):
        """Test my_update_dashboard_add_table with None as sheet_id (should raise AssertionError)."""
        # Verify that passing None as sheet_id raises an AssertionError
        with pytest.raises(AssertionError, match="sheet_id cannot be None"):
            await table.my_update_dashboard_add_table(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id=None,
                visual_id="visual1",
                dataset_id="dataset1",
                category_column_names=["product", "region"],
                date_column_names=["Date"],
                value_column_names=["sales", "profit"],
                value_column_aggregation=["SUM", "AVERAGE"],
            )

    async def test_update_dashboard_add_table_none_visual_id(self):
        """Test my_update_dashboard_add_table with None as visual_id (should raise AssertionError)."""
        # Verify that passing None as visual_id raises an AssertionError
        with pytest.raises(AssertionError, match="visual_id cannot be None"):
            await table.my_update_dashboard_add_table(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id=None,
                dataset_id="dataset1",
                category_column_names=["product", "region"],
                date_column_names=["Date"],
                value_column_names=["sales", "profit"],
                value_column_aggregation=["SUM", "AVERAGE"],
            )

    async def test_update_dashboard_add_table_none_dataset_id(self):
        """Test my_update_dashboard_add_table with None as dataset_id (should raise AssertionError)."""
        # Verify that passing None as dataset_id raises an AssertionError
        with pytest.raises(AssertionError, match="dataset_id cannot be None"):
            await table.my_update_dashboard_add_table(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id=None,
                category_column_names=["product", "region"],
                date_column_names=["Date"],
                value_column_names=["sales", "profit"],
                value_column_aggregation=["SUM", "AVERAGE"],
            )

    async def test_update_dashboard_add_table_none_category_column_names(self):
        """Test my_update_dashboard_add_table with None as category_column_names (should raise AssertionError)."""
        # Verify that passing None as category_column_names raises an AssertionError
        with pytest.raises(AssertionError, match="category_column_names cannot be None"):
            await table.my_update_dashboard_add_table(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                category_column_names=None,
                date_column_names=["Date"],
                value_column_names=["sales", "profit"],
                value_column_aggregation=["SUM", "AVERAGE"],
            )

    async def test_update_dashboard_add_table_none_date_column_names(self):
        """Test my_update_dashboard_add_table with None as date_column_names (should raise AssertionError)."""
        # Verify that passing None as date_column_names raises an AssertionError
        with pytest.raises(AssertionError, match="date_column_names cannot be None"):
            await table.my_update_dashboard_add_table(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                category_column_names=["product", "region"],
                date_column_names=None,
                value_column_names=["sales", "profit"],
                value_column_aggregation=["SUM", "AVERAGE"],
            )

    async def test_update_dashboard_add_table_none_value_column_names(self):
        """Test my_update_dashboard_add_table with None as value_column_names (should raise AssertionError)."""
        # Verify that passing None as value_column_names raises an AssertionError
        with pytest.raises(AssertionError, match="value_column_names cannot be None"):
            await table.my_update_dashboard_add_table(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                category_column_names=["product", "region"],
                date_column_names=["Date"],
                value_column_names=None,
                value_column_aggregation=["SUM", "AVERAGE"],
            )

    async def test_update_dashboard_add_table_none_value_column_aggregation(self):
        """Test my_update_dashboard_add_table with None as value_column_aggregation (should raise AssertionError)."""
        # Verify that passing None as value_column_aggregation raises an AssertionError
        with pytest.raises(AssertionError, match="value_column_aggregation cannot be None"):
            await table.my_update_dashboard_add_table(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                category_column_names=["product", "region"],
                date_column_names=["Date"],
                value_column_names=["sales", "profit"],
                value_column_aggregation=None,
            )


class TestCreateEmptyTableVisual(TestCase):
    """Test cases for create_empty_table_visual function."""

    @patch("builtins.open")
    @patch("json.load")
    def test_create_empty_table_visual_success(self, mock_json_load, mock_open):
        """Test create_empty_table_visual with a valid visual_id."""
        # Setup mock response for json.load
        mock_table = {
            "TableVisual": {
                "VisualId": "",
                "Title": {"Visibility": "VISIBLE"},
                "ChartConfiguration": {
                    "FieldWells": {"TableAggregatedFieldWells": {}},
                },
            }
        }
        mock_json_load.return_value = mock_table

        # Call the function
        result = table.create_empty_table_visual("visual1")

        # Verify open was called with the correct path
        self.assertEqual(mock_open.call_count, 1)
        call_args = mock_open.call_args[0]
        self.assertEqual(len(call_args), 2)
        self.assertTrue(call_args[0].endswith("json_definitions/table_definition.json"))
        self.assertEqual(call_args[1], "r")

        # Verify json.load was called correctly
        mock_json_load.assert_called_once()

        # Verify the visual_id was set correctly
        self.assertEqual(result["TableVisual"]["VisualId"], "visual1")

    def test_create_empty_table_visual_none_visual_id(self):
        """Test create_empty_table_visual with None as visual_id (should raise AssertionError)."""
        # Verify that passing None as visual_id raises an AssertionError
        with self.assertRaises(AssertionError) as context:
            table.create_empty_table_visual(None)

        # Verify the exception message
        self.assertEqual(str(context.exception), "visual cannot be None")

    @patch("builtins.open")
    def test_create_empty_table_visual_file_error(self, mock_open):
        """Test create_empty_table_visual when there's an error opening the JSON file."""
        # Setup mock to raise an exception
        mock_open.side_effect = FileNotFoundError("File not found")

        # Verify the exception is propagated
        with self.assertRaises(FileNotFoundError) as context:
            table.create_empty_table_visual("visual1")

        # Verify the exception message
        self.assertEqual(str(context.exception), "File not found")


class TestCreateTableVisual(TestCase):
    """
    Test cases for create_table_visual function.

    Tests structure of table object for each parameter
    """

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.table.create_empty_table_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.table.chart_config.create_category")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.table.chart_config.create_value")
    def test_create_table_visual_basic(
        self, mock_create_value, mock_create_category, mock_create_empty_table_visual
    ):
        """Test create_table_visual with basic valid parameters."""
        # Setup mock responses
        mock_empty_table = {
            "TableVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {"TableAggregatedFieldWells": {"GroupBy": [], "Values": []}},
                },
            }
        }
        mock_create_empty_table_visual.return_value = mock_empty_table

        mock_create_category.side_effect = [
            {"CategoricalDimensionField": {"FieldId": "product"}},
            {"CategoricalDimensionField": {"FieldId": "region"}},
            {"DateDimensionField": {"FieldId": "Date"}},
        ]

        mock_create_value.side_effect = [
            {"NumericalMeasureField": {"FieldId": "sales"}},
            {"NumericalMeasureField": {"FieldId": "profit"}},
        ]

        # Call the function with basic parameters
        table_params = {
            "visual_id": "visual1",
            "dataset_id": "dataset1",
            "category_column_names": ["product", "region"],
            "date_column_names": ["Date"],
            "date_granularity": "",
            "value_column_names": ["sales", "profit"],
            "value_column_aggregation": ["SUM", "AVERAGE"],
        }
        result = table.create_table_visual(table_params)

        # Verify create_empty_table_visual was called correctly
        mock_create_empty_table_visual.assert_called_once_with("visual1")

        # Verify create_category was called correctly for each category column
        self.assertEqual(mock_create_category.call_count, 3)
        mock_create_category.assert_any_call(
            column_name="product", dataset_id="dataset1", column_type="Categorical"
        )
        mock_create_category.assert_any_call(
            column_name="region", dataset_id="dataset1", column_type="Categorical"
        )
        mock_create_category.assert_any_call(
            column_name="Date", dataset_id="dataset1", column_type="Date", date_granularity=""
        )

        # Verify create_value was called correctly for each value column
        self.assertEqual(mock_create_value.call_count, 2)
        mock_create_value.assert_any_call(
            column_name="sales", dataset_id="dataset1", numerical_aggregation="SUM"
        )
        mock_create_value.assert_any_call(
            column_name="profit", dataset_id="dataset1", numerical_aggregation="AVERAGE"
        )

        # Verify the result structure
        self.assertEqual(result["TableVisual"]["VisualId"], "visual1")
        self.assertEqual(
            len(
                result["TableVisual"]["ChartConfiguration"]["FieldWells"][
                    "TableAggregatedFieldWells"
                ]["GroupBy"]
            ),
            3,
        )
        self.assertEqual(
            len(
                result["TableVisual"]["ChartConfiguration"]["FieldWells"][
                    "TableAggregatedFieldWells"
                ]["Values"]
            ),
            2,
        )

    def test_create_table_visual_none_parameters(self):
        """Test create_table_visual with None parameters (should raise AssertionError)."""
        # Verify that passing None as table_parameters raises an AssertionError
        with pytest.raises(AssertionError, match="table_parameters cannot be None"):
            table.create_table_visual(None)
