from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import patch

import pytest

import sys
from pathlib import Path

qs_mcp_directory = Path(__file__).parent.parent
sys.path.append(str(qs_mcp_directory))
print(qs_mcp_directory)

import awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table as pivot_table
import awslabs.aws_quicksight_dashboards_mcp_server.quicksight as qs


class TestCreateEmptyPivotTableVisual(TestCase):
    """Test cases for create_empty_pivot_table_visual function."""

    @patch("builtins.open")
    @patch("json.load")
    def test_create_empty_pivot_table_visual_success(self, mock_json_load, mock_open):
        """Test create_empty_pivot_table_visual with a valid visual_id."""
        # Setup mock response for json.load
        mock_pivot_table = {
            "PivotTableVisual": {
                "VisualId": "",
                "Title": {"Visibility": "VISIBLE"},
                "ChartConfiguration": {
                    "FieldWells": {"PivotTableAggregatedFieldWells": {}},
                },
            }
        }
        mock_json_load.return_value = mock_pivot_table

        # Call the function
        result = pivot_table.create_empty_pivot_table_visual("visual1")

        # Verify open was called with the correct path
        self.assertEqual(mock_open.call_count, 1)
        call_args = mock_open.call_args[0]
        self.assertEqual(len(call_args), 2)
        self.assertTrue(call_args[0].endswith("json_definitions/pivot_table_definition.json"))
        self.assertEqual(call_args[1], "r")

        # Verify json.load was called correctly
        mock_json_load.assert_called_once()

        # Verify the visual_id was set correctly
        self.assertEqual(result["PivotTableVisual"]["VisualId"], "visual1")

    def test_create_empty_pivot_table_visual_none_visual_id(self):
        """Test create_empty_pivot_table_visual with None as visual_id (should raise AssertionError)."""
        # Verify that passing None as visual_id raises an AssertionError
        with self.assertRaises(AssertionError) as context:
            pivot_table.create_empty_pivot_table_visual(None)

        # Verify the exception message
        self.assertEqual(str(context.exception), "visual cannot be None")

    @patch("builtins.open")
    def test_create_empty_pivot_table_visual_file_error(self, mock_open):
        """Test create_empty_pivot_table_visual when there's an error opening the JSON file."""
        # Setup mock to raise an exception
        mock_open.side_effect = FileNotFoundError("File not found")

        # Verify the exception is propagated
        with self.assertRaises(FileNotFoundError) as context:
            pivot_table.create_empty_pivot_table_visual("visual1")

        # Verify the exception message
        self.assertEqual(str(context.exception), "File not found")


class TestCreatePivotTableVisual(TestCase):
    """Test cases for create_pivot_table_visual function."""

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.create_empty_pivot_table_visual")
    def test_create_pivot_table_visual_basic(self, mock_create_empty_pivot_table_visual):
        """Test create_pivot_table_visual with minimal valid parameters."""
        # Setup mock response for create_empty_pivot_table_visual
        mock_empty_pivot_table = {
            "PivotTableVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {"PivotTableAggregatedFieldWells": {"Rows": [], "Values": []}},
                    "FieldOptions": {"SelectedFieldOptions": []},
                    "SortConfiguration": {"FieldSortOptions": []},
                },
            }
        }
        mock_create_empty_pivot_table_visual.return_value = mock_empty_pivot_table

        # Call the function with minimal parameters
        pivot_table_params = {
            "visual_id": "visual1",
            "dataset_id": "dataset1",
            "category_column_names": [],
            "date_column_names": [],
            "date_granularity": "",
            "value_column_names": [],
            "value_column_aggregation": [],
        }

        result = pivot_table.create_pivot_table_visual(pivot_table_params)

        # Verify create_empty_pivot_table_visual was called correctly
        mock_create_empty_pivot_table_visual.assert_called_once_with("visual1")

        # Verify the result structure
        self.assertEqual(result["PivotTableVisual"]["VisualId"], "visual1")
        self.assertEqual(
            len(
                result["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
                    "PivotTableAggregatedFieldWells"
                ]["Rows"]
            ),
            0,
        )
        self.assertEqual(
            len(
                result["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
                    "PivotTableAggregatedFieldWells"
                ]["Values"]
            ),
            0,
        )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.create_empty_pivot_table_visual")
    def test_create_pivot_table_visual_category_columns(self, mock_create_empty_pivot_table_visual):
        """Test create_pivot_table_visual with multiple category columns."""
        # Setup mock response for create_empty_pivot_table_visual
        mock_empty_pivot_table = {
            "PivotTableVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {"PivotTableAggregatedFieldWells": {"Rows": [], "Values": []}},
                    "FieldOptions": {"SelectedFieldOptions": []},
                    "SortConfiguration": {"FieldSortOptions": []},
                },
            }
        }
        mock_create_empty_pivot_table_visual.return_value = mock_empty_pivot_table

        # Setup mock category objects
        mock_category1 = {"CategoricalDimensionField": {"FieldId": "region"}}
        mock_category2 = {"CategoricalDimensionField": {"FieldId": "product"}}

        # Setup mock field options and sort options
        mock_field_option = {"FieldId": "region", "Visibility": "VISIBLE"}
        mock_sort_option = {"FieldId": "region", "Direction": "ASC"}

        # Call the function with category columns
        pivot_table_params = {
            "visual_id": "visual1",
            "dataset_id": "dataset1",
            "category_column_names": ["region", "product"],
            "date_column_names": [],
            "date_granularity": "",
            "value_column_names": [],
            "value_column_aggregation": [],
        }

        # Mock chart_config functions
        with patch(
            "awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_category"
        ) as mock_create_category, patch(
            "awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_field_options"
        ) as mock_create_field_options, patch(
            "awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_field_sort_options"
        ) as mock_create_field_sort_options:

            # Setup mock return values
            mock_create_category.side_effect = [mock_category1, mock_category2]
            mock_create_field_options.return_value = mock_field_option
            mock_create_field_sort_options.return_value = mock_sort_option

            result = pivot_table.create_pivot_table_visual(pivot_table_params)

            # Verify create_category was called correctly for each category column
            self.assertEqual(mock_create_category.call_count, 2)
            mock_create_category.assert_any_call(
                column_name="region", dataset_id="dataset1", column_type="Categorical"
            )
            mock_create_category.assert_any_call(
                column_name="product", dataset_id="dataset1", column_type="Categorical"
            )

            # Verify create_field_options was called correctly
            self.assertEqual(mock_create_field_options.call_count, 2)

            # Verify create_field_sort_options was called correctly
            self.assertEqual(mock_create_field_sort_options.call_count, 2)

            # Verify the result structure
            self.assertEqual(
                len(
                    result["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
                        "PivotTableAggregatedFieldWells"
                    ]["Rows"]
                ),
                2,
            )
            self.assertEqual(
                result["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
                    "PivotTableAggregatedFieldWells"
                ]["Rows"][0],
                mock_category1,
            )
            self.assertEqual(
                result["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
                    "PivotTableAggregatedFieldWells"
                ]["Rows"][1],
                mock_category2,
            )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.create_empty_pivot_table_visual")
    def test_create_pivot_table_visual_date_columns(self, mock_create_empty_pivot_table_visual):
        """Test create_pivot_table_visual with date columns and granularity."""
        # Setup mock response for create_empty_pivot_table_visual
        mock_empty_pivot_table = {
            "PivotTableVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {"PivotTableAggregatedFieldWells": {"Rows": [], "Values": []}},
                    "FieldOptions": {"SelectedFieldOptions": []},
                    "SortConfiguration": {"FieldSortOptions": []},
                },
            }
        }
        mock_create_empty_pivot_table_visual.return_value = mock_empty_pivot_table

        # Setup mock date category object
        mock_date_category = {"DateDimensionField": {"FieldId": "date"}}

        # Setup mock field options and sort options
        mock_field_option = {"FieldId": "date", "Visibility": "VISIBLE"}
        mock_sort_option = {"FieldId": "date", "Direction": "ASC"}

        # Call the function with date columns and granularity
        pivot_table_params = {
            "visual_id": "visual1",
            "dataset_id": "dataset1",
            "category_column_names": [],
            "date_column_names": ["date"],
            "date_granularity": "MONTH",
            "value_column_names": [],
            "value_column_aggregation": [],
        }

        # Mock chart_config functions
        with patch(
            "awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_category"
        ) as mock_create_category, patch(
            "awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_field_options"
        ) as mock_create_field_options, patch(
            "awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_field_sort_options"
        ) as mock_create_field_sort_options:

            # Setup mock return values
            mock_create_category.return_value = mock_date_category
            mock_create_field_options.return_value = mock_field_option
            mock_create_field_sort_options.return_value = mock_sort_option

            result = pivot_table.create_pivot_table_visual(pivot_table_params)

            # Verify create_category was called correctly with date granularity
            mock_create_category.assert_called_once_with(
                column_name="date",
                dataset_id="dataset1",
                column_type="Date",
                date_granularity="MONTH",
            )

            # Verify the result structure
            self.assertEqual(
                len(
                    result["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
                        "PivotTableAggregatedFieldWells"
                    ]["Rows"]
                ),
                1,
            )
            self.assertEqual(
                result["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
                    "PivotTableAggregatedFieldWells"
                ]["Rows"][0],
                mock_date_category,
            )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.create_empty_pivot_table_visual")
    def test_create_pivot_table_visual_value_columns(self, mock_create_empty_pivot_table_visual):
        """Test create_pivot_table_visual with multiple value columns and aggregation functions."""
        # Setup mock response for create_empty_pivot_table_visual
        mock_empty_pivot_table = {
            "PivotTableVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {"PivotTableAggregatedFieldWells": {"Rows": [], "Values": []}},
                    "FieldOptions": {"SelectedFieldOptions": []},
                    "SortConfiguration": {"FieldSortOptions": []},
                },
            }
        }
        mock_create_empty_pivot_table_visual.return_value = mock_empty_pivot_table

        # Setup mock value objects
        mock_value1 = {"NumericalMeasureField": {"FieldId": "sales"}}
        mock_value2 = {"NumericalMeasureField": {"FieldId": "profit"}}

        # Setup mock field options
        mock_field_option = {"FieldId": "category", "Visibility": "VISIBLE"}

        # Call the function with value columns and different aggregations
        pivot_table_params = {
            "visual_id": "visual1",
            "dataset_id": "dataset1",
            "category_column_names": ["category"],
            "date_column_names": [],
            "date_granularity": "",
            "value_column_names": ["sales", "profit"],
            "value_column_aggregation": ["SUM", "AVERAGE"],
        }

        # Mock chart_config functions
        with patch(
            "awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_category"
        ) as mock_create_category, patch(
            "awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_value"
        ) as mock_create_value, patch(
            "awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_field_options"
        ) as mock_create_field_options, patch(
            "awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_field_sort_options"
        ) as mock_create_field_sort_options:

            # Setup mock return values
            mock_create_category.return_value = {
                "CategoricalDimensionField": {"FieldId": "category"}
            }
            mock_create_value.side_effect = [mock_value1, mock_value2]
            mock_create_field_options.return_value = mock_field_option
            mock_create_field_sort_options.return_value = {
                "FieldSort": {"FieldId": "category", "Direction": "ASC"}
            }

            result = pivot_table.create_pivot_table_visual(pivot_table_params)

            # Verify create_value was called correctly for each value column with correct aggregation
            self.assertEqual(mock_create_value.call_count, 2)
            mock_create_value.assert_any_call(
                column_name="sales", dataset_id="dataset1", numerical_aggregation="SUM"
            )
            mock_create_value.assert_any_call(
                column_name="profit", dataset_id="dataset1", numerical_aggregation="AVERAGE"
            )

            # Verify the result structure
            self.assertEqual(
                len(
                    result["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
                        "PivotTableAggregatedFieldWells"
                    ]["Values"]
                ),
                2,
            )
            self.assertEqual(
                result["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
                    "PivotTableAggregatedFieldWells"
                ]["Values"][0],
                mock_value1,
            )
            self.assertEqual(
                result["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
                    "PivotTableAggregatedFieldWells"
                ]["Values"][1],
                mock_value2,
            )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.create_empty_pivot_table_visual")
    def test_create_pivot_table_visual_mixed_columns(self, mock_create_empty_pivot_table_visual):
        """Test create_pivot_table_visual with a mix of category, date, and value columns."""
        # Setup mock response for create_empty_pivot_table_visual
        mock_empty_pivot_table = {
            "PivotTableVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {"PivotTableAggregatedFieldWells": {"Rows": [], "Values": []}},
                    "FieldOptions": {"SelectedFieldOptions": []},
                    "SortConfiguration": {"FieldSortOptions": []},
                },
            }
        }
        mock_create_empty_pivot_table_visual.return_value = mock_empty_pivot_table

        # Setup mock objects
        mock_category = {"CategoricalDimensionField": {"FieldId": "region"}}
        mock_date = {"DateDimensionField": {"FieldId": "date"}}
        mock_value = {"NumericalMeasureField": {"FieldId": "sales"}}

        # Setup mock field options
        mock_field_option = {"FieldId": "field", "Visibility": "VISIBLE"}
        mock_sort_option = {"FieldId": "field", "Direction": "ASC"}

        # Call the function with mixed column types
        pivot_table_params = {
            "visual_id": "visual1",
            "dataset_id": "dataset1",
            "category_column_names": ["region"],
            "date_column_names": ["date"],
            "date_granularity": "YEAR",
            "value_column_names": ["sales"],
            "value_column_aggregation": ["SUM"],
        }

        # Mock chart_config functions
        with patch(
            "awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_category"
        ) as mock_create_category, patch(
            "awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_value"
        ) as mock_create_value, patch(
            "awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_field_options"
        ) as mock_create_field_options, patch(
            "awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_field_sort_options"
        ) as mock_create_field_sort_options:

            # Setup mock return values
            mock_create_category.side_effect = [mock_category, mock_date]
            mock_create_value.return_value = mock_value
            mock_create_field_options.return_value = mock_field_option
            mock_create_field_sort_options.return_value = mock_sort_option

            result = pivot_table.create_pivot_table_visual(pivot_table_params)

            # Verify create_category was called correctly for both category and date columns
            self.assertEqual(mock_create_category.call_count, 2)
            mock_create_category.assert_any_call(
                column_name="region", dataset_id="dataset1", column_type="Categorical"
            )
            mock_create_category.assert_any_call(
                column_name="date",
                dataset_id="dataset1",
                column_type="Date",
                date_granularity="YEAR",
            )

            # Verify create_value was called correctly
            mock_create_value.assert_called_once_with(
                column_name="sales", dataset_id="dataset1", numerical_aggregation="SUM"
            )

            # Verify the result structure
            self.assertEqual(
                len(
                    result["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
                        "PivotTableAggregatedFieldWells"
                    ]["Rows"]
                ),
                2,
            )
            self.assertEqual(
                len(
                    result["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
                        "PivotTableAggregatedFieldWells"
                    ]["Values"]
                ),
                1,
            )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.create_empty_pivot_table_visual")
    def test_create_pivot_table_visual_empty_category_columns(
        self, mock_create_empty_pivot_table_visual
    ):
        """Test create_pivot_table_visual with empty category_column_names."""
        # Setup mock response for create_empty_pivot_table_visual
        mock_empty_pivot_table = {
            "PivotTableVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {"PivotTableAggregatedFieldWells": {"Rows": [], "Values": []}},
                    "FieldOptions": {"SelectedFieldOptions": []},
                    "SortConfiguration": {"FieldSortOptions": []},
                },
            }
        }
        mock_create_empty_pivot_table_visual.return_value = mock_empty_pivot_table

        # Setup mock value object
        mock_value = {"NumericalMeasureField": {"FieldId": "sales"}}

        # Call the function with empty category_column_names
        pivot_table_params = {
            "visual_id": "visual1",
            "dataset_id": "dataset1",
            "category_column_names": [],  # Empty category columns
            "date_column_names": [],
            "date_granularity": "",
            "value_column_names": ["sales"],
            "value_column_aggregation": ["SUM"],
        }

        # Mock chart_config functions
        with patch(
            "awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_value"
        ) as mock_create_value, patch(
            "awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_field_options"
        ) as mock_create_field_options:

            # Setup mock return values
            mock_create_value.return_value = mock_value
            mock_create_field_options.return_value = {"FieldId": "sales", "Visibility": "VISIBLE"}

            result = pivot_table.create_pivot_table_visual(pivot_table_params)

            # Verify create_value was called correctly
            mock_create_value.assert_called_once_with(
                column_name="sales", dataset_id="dataset1", numerical_aggregation="SUM"
            )

            # Verify the result structure
            self.assertEqual(
                len(
                    result["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
                        "PivotTableAggregatedFieldWells"
                    ]["Rows"]
                ),
                0,
            )
            self.assertEqual(
                len(
                    result["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
                        "PivotTableAggregatedFieldWells"
                    ]["Values"]
                ),
                1,
            )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.create_empty_pivot_table_visual")
    def test_create_pivot_table_visual_empty_value_columns(
        self, mock_create_empty_pivot_table_visual
    ):
        """Test create_pivot_table_visual with empty value_column_names."""
        # Setup mock response for create_empty_pivot_table_visual
        mock_empty_pivot_table = {
            "PivotTableVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {"PivotTableAggregatedFieldWells": {"Rows": [], "Values": []}},
                    "FieldOptions": {"SelectedFieldOptions": []},
                    "SortConfiguration": {"FieldSortOptions": []},
                },
            }
        }
        mock_create_empty_pivot_table_visual.return_value = mock_empty_pivot_table

        # Setup mock category object
        mock_category = {"CategoricalDimensionField": {"FieldId": "region"}}

        # Setup mock field options and sort options
        mock_field_option = {"FieldId": "region", "Visibility": "VISIBLE"}
        mock_sort_option = {"FieldId": "region", "Direction": "ASC"}

        # Call the function with empty value_column_names
        pivot_table_params = {
            "visual_id": "visual1",
            "dataset_id": "dataset1",
            "category_column_names": ["region"],
            "date_column_names": [],
            "date_granularity": "",
            "value_column_names": [],  # Empty value columns
            "value_column_aggregation": [],
        }

        # Mock chart_config functions
        with patch(
            "awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_category"
        ) as mock_create_category, patch(
            "awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_field_options"
        ) as mock_create_field_options, patch(
            "awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_field_sort_options"
        ) as mock_create_field_sort_options:

            # Setup mock return values
            mock_create_category.return_value = mock_category
            mock_create_field_options.return_value = mock_field_option
            mock_create_field_sort_options.return_value = mock_sort_option

            result = pivot_table.create_pivot_table_visual(pivot_table_params)

            # Verify create_category was called correctly
            mock_create_category.assert_called_once_with(
                column_name="region", dataset_id="dataset1", column_type="Categorical"
            )

            # Verify the result structure
            self.assertEqual(
                len(
                    result["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
                        "PivotTableAggregatedFieldWells"
                    ]["Rows"]
                ),
                1,
            )
            self.assertEqual(
                len(
                    result["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
                        "PivotTableAggregatedFieldWells"
                    ]["Values"]
                ),
                0,
            )

    def test_create_pivot_table_visual_none_parameters(self):
        """Test create_pivot_table_visual with None parameters (should raise AssertionError)."""
        # Verify that passing None as pivot_table_parameters raises an AssertionError
        with pytest.raises(AssertionError, match="pivot table parameters cannot be None"):
            pivot_table.create_pivot_table_visual(None)


class TestMyUpdateDashboardAddPivotTable(IsolatedAsyncioTestCase):
    """
    Test cases for my_update_dashboard_add_pivot_table function.

    Tests visual creation (getting chart object, update) and parameter validation
    """

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.update_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.create_pivot_table_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_dash_version")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.my_update_dashboard_publish")
    async def test_update_dashboard_add_pivot_table_success(
        self,
        mock_publish,
        mock_get_dash_version,
        mock_create_pivot_table_visual,
        mock_update_visual,
        mock_get_current_visuals,
        mock_client,
    ):
        """Test my_update_dashboard_add_pivot_table with valid parameters."""
        # Setup mock visuals
        mock_visuals = [
            {"LineChartVisual": {"VisualId": "visual1", "Title": {"Visibility": "VISIBLE"}}},
        ]
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock pivot table
        mock_pivot_table = {
            "PivotTableVisual": {
                "VisualId": "visual2",
                "Title": {"Visibility": "VISIBLE"},
                "ChartConfiguration": {
                    "FieldWells": {"PivotTableAggregatedFieldWells": {}},
                    "FieldOptions": {"SelectedFieldOptions": []},
                    "SortConfiguration": {"FieldSortOptions": []},
                },
            }
        }
        mock_create_pivot_table_visual.return_value = mock_pivot_table

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
                        mock_pivot_table,
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

        # Setup mock version and publish response
        mock_get_dash_version.return_value = 2
        mock_publish.return_value = {"Status": 200}

        # Call the function
        result = await pivot_table.my_update_dashboard_add_pivot_table(
            dash_id="dashboard1",
            dash_name="Dashboard 1",
            sheet_id="sheet1",
            visual_id="visual2",
            dataset_id="dataset1",
            category_column_names=["product", "region"],
            date_column_names=["Date"],
            date_granularity="MONTH",
            value_column_names=["sales", "profit"],
            value_column_aggregation=["SUM", "AVERAGE"],
        )

        # Verify get_current_visuals was called correctly
        mock_get_current_visuals.assert_called_once_with("dashboard1", "sheet1")

        # Verify create_pivot_table_visual was called with the correct parameters
        expected_pivot_table_params = {
            "visual_id": "visual2",
            "dataset_id": "dataset1",
            "category_column_names": ["product", "region"],
            "date_column_names": ["Date"],
            "date_granularity": "MONTH",
            "value_column_names": ["sales", "profit"],
            "value_column_aggregation": ["SUM", "AVERAGE"],
        }
        mock_create_pivot_table_visual.assert_called_once_with(expected_pivot_table_params)

        # Verify update_visual was called with the updated visuals
        expected_visuals = [
            {"LineChartVisual": {"VisualId": "visual1", "Title": {"Visibility": "VISIBLE"}}},
            mock_pivot_table,
        ]
        mock_update_visual.assert_called_once_with("dashboard1", "sheet1", expected_visuals)

        # Verify client.update_dashboard was called correctly
        mock_client.update_dashboard.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID,
            DashboardId="dashboard1",
            Name="Dashboard 1",
            Definition=mock_updated_definition,
        )

        # Verify get_dash_version and publish were called correctly
        mock_get_dash_version.assert_called_once_with(mock_response)
        mock_publish.assert_called_once_with("dashboard1", 2)

        # Verify the result
        self.assertEqual(result, mock_response)

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.update_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.create_pivot_table_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_dash_version")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.my_update_dashboard_publish")
    async def test_update_dashboard_add_pivot_table_empty_category_columns(
        self,
        mock_publish,
        mock_get_dash_version,
        mock_create_pivot_table_visual,
        mock_update_visual,
        mock_get_current_visuals,
        mock_client,
    ):
        """Test my_update_dashboard_add_pivot_table with empty category_column_names."""
        # Setup mock visuals
        mock_visuals = [
            {"LineChartVisual": {"VisualId": "visual1", "Title": {"Visibility": "VISIBLE"}}},
        ]
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock pivot table
        mock_pivot_table = {
            "PivotTableVisual": {
                "VisualId": "visual2",
                "Title": {"Visibility": "VISIBLE"},
                "ChartConfiguration": {
                    "FieldWells": {
                        "PivotTableAggregatedFieldWells": {
                            "Rows": [],
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
                    "FieldOptions": {"SelectedFieldOptions": []},
                    "SortConfiguration": {"FieldSortOptions": []},
                },
            }
        }
        mock_create_pivot_table_visual.return_value = mock_pivot_table

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
                        mock_pivot_table,
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

        # Setup mock version and publish response
        mock_get_dash_version.return_value = 2
        mock_publish.return_value = {"Status": 200}

        # Call the function with empty category_column_names
        result = await pivot_table.my_update_dashboard_add_pivot_table(
            dash_id="dashboard1",
            dash_name="Dashboard 1",
            sheet_id="sheet1",
            visual_id="visual2",
            dataset_id="dataset1",
            category_column_names=[],  # Empty category columns
            date_column_names=["Date"],
            date_granularity="MONTH",
            value_column_names=["sales"],
            value_column_aggregation=["SUM"],
        )

        # Verify create_pivot_table_visual was called with the correct parameters
        expected_pivot_table_params = {
            "visual_id": "visual2",
            "dataset_id": "dataset1",
            "category_column_names": [],  # Empty category columns
            "date_column_names": ["Date"],
            "date_granularity": "MONTH",
            "value_column_names": ["sales"],
            "value_column_aggregation": ["SUM"],
        }
        mock_create_pivot_table_visual.assert_called_once_with(expected_pivot_table_params)

        # Verify the result
        self.assertEqual(result, mock_response)

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.update_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.create_pivot_table_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_dash_version")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.my_update_dashboard_publish")
    async def test_update_dashboard_add_pivot_table_empty_value_columns(
        self,
        mock_publish,
        mock_get_dash_version,
        mock_create_pivot_table_visual,
        mock_update_visual,
        mock_get_current_visuals,
        mock_client,
    ):
        """Test my_update_dashboard_add_pivot_table with empty value_column_names."""
        # Setup mock visuals
        mock_visuals = [
            {"LineChartVisual": {"VisualId": "visual1", "Title": {"Visibility": "VISIBLE"}}},
        ]
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock pivot table
        mock_pivot_table = {
            "PivotTableVisual": {
                "VisualId": "visual2",
                "Title": {"Visibility": "VISIBLE"},
                "ChartConfiguration": {
                    "FieldWells": {
                        "PivotTableAggregatedFieldWells": {
                            "Rows": [
                                {
                                    "CategoricalDimensionField": {
                                        "FieldId": "fieldid1",
                                        "Column": {
                                            "DataSetIdentifier": "SaaS-Sales.csv",
                                            "ColumnName": "product",
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
                    "FieldOptions": {"SelectedFieldOptions": []},
                    "SortConfiguration": {"FieldSortOptions": []},
                },
            }
        }
        mock_create_pivot_table_visual.return_value = mock_pivot_table

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
                        mock_pivot_table,
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

        # Setup mock version and publish response
        mock_get_dash_version.return_value = 2
        mock_publish.return_value = {"Status": 200}

        # Call the function with empty value_column_names and value_column_aggregation
        result = await pivot_table.my_update_dashboard_add_pivot_table(
            dash_id="dashboard1",
            dash_name="Dashboard 1",
            sheet_id="sheet1",
            visual_id="visual2",
            dataset_id="dataset1",
            category_column_names=["product"],
            date_column_names=["Date"],
            date_granularity="MONTH",
            value_column_names=[],  # Empty value columns
            value_column_aggregation=[],  # Empty value column aggregation
        )

        # Verify create_pivot_table_visual was called with the correct parameters
        expected_pivot_table_params = {
            "visual_id": "visual2",
            "dataset_id": "dataset1",
            "category_column_names": ["product"],
            "date_column_names": ["Date"],
            "date_granularity": "MONTH",
            "value_column_names": [],  # Empty value columns
            "value_column_aggregation": [],  # Empty value column aggregation
        }
        mock_create_pivot_table_visual.assert_called_once_with(expected_pivot_table_params)

        # Verify the result
        self.assertEqual(result, mock_response)

    async def test_update_dashboard_add_pivot_table_length_mismatch(self):
        """Test my_update_dashboard_add_pivot_table with length mismatch between value_column_names and value_column_aggregation."""
        # Verify that passing mismatched lengths raises an AssertionError
        with pytest.raises(
            AssertionError, match="Length mismatch. Each value column needs an aggregation function"
        ):
            await pivot_table.my_update_dashboard_add_pivot_table(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                category_column_names=["product", "region"],
                date_column_names=["Date"],
                date_granularity="MONTH",
                value_column_names=["sales", "profit", "quantity"],  # 3 value columns
                value_column_aggregation=["SUM", "AVERAGE"],  # Only 2 aggregation functions
            )

    async def test_update_dashboard_add_pivot_table_none_dash_id(self):
        """Test my_update_dashboard_add_pivot_table with None as dash_id (should raise AssertionError)."""
        # Verify that passing None as dash_id raises an AssertionError
        with pytest.raises(AssertionError, match="dash_id cannot be None"):
            await pivot_table.my_update_dashboard_add_pivot_table(
                dash_id=None,
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                category_column_names=["product", "region"],
                date_column_names=["Date"],
                date_granularity="MONTH",
                value_column_names=["sales", "profit"],
                value_column_aggregation=["SUM", "AVERAGE"],
            )

    async def test_update_dashboard_add_pivot_table_none_dash_name(self):
        """Test my_update_dashboard_add_pivot_table with None as dash_name (should raise AssertionError)."""
        # Verify that passing None as dash_name raises an AssertionError
        with pytest.raises(AssertionError, match="dash_name cannot be None"):
            await pivot_table.my_update_dashboard_add_pivot_table(
                dash_id="dashboard1",
                dash_name=None,
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                category_column_names=["product", "region"],
                date_column_names=["Date"],
                date_granularity="MONTH",
                value_column_names=["sales", "profit"],
                value_column_aggregation=["SUM", "AVERAGE"],
            )

    async def test_update_dashboard_add_pivot_table_none_sheet_id(self):
        """Test my_update_dashboard_add_pivot_table with None as sheet_id (should raise AssertionError)."""
        # Verify that passing None as sheet_id raises an AssertionError
        with pytest.raises(AssertionError, match="sheet_id cannot be None"):
            await pivot_table.my_update_dashboard_add_pivot_table(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id=None,
                visual_id="visual1",
                dataset_id="dataset1",
                category_column_names=["product", "region"],
                date_column_names=["Date"],
                date_granularity="MONTH",
                value_column_names=["sales", "profit"],
                value_column_aggregation=["SUM", "AVERAGE"],
            )

    async def test_update_dashboard_add_pivot_table_none_visual_id(self):
        """Test my_update_dashboard_add_pivot_table with None as visual_id (should raise AssertionError)."""
        # Verify that passing None as visual_id raises an AssertionError
        with pytest.raises(AssertionError, match="visual_id cannot be None"):
            await pivot_table.my_update_dashboard_add_pivot_table(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id=None,
                dataset_id="dataset1",
                category_column_names=["product", "region"],
                date_column_names=["Date"],
                date_granularity="MONTH",
                value_column_names=["sales", "profit"],
                value_column_aggregation=["SUM", "AVERAGE"],
            )

    async def test_update_dashboard_add_pivot_table_none_dataset_id(self):
        """Test my_update_dashboard_add_pivot_table with None as dataset_id (should raise AssertionError)."""
        # Verify that passing None as dataset_id raises an AssertionError
        with pytest.raises(AssertionError, match="dataset_id cannot be None"):
            await pivot_table.my_update_dashboard_add_pivot_table(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id=None,
                category_column_names=["product", "region"],
                date_column_names=["Date"],
                date_granularity="MONTH",
                value_column_names=["sales", "profit"],
                value_column_aggregation=["SUM", "AVERAGE"],
            )

    async def test_update_dashboard_add_pivot_table_none_category_column_names(self):
        """Test my_update_dashboard_add_pivot_table with None as category_column_names (should raise AssertionError)."""
        # Verify that passing None as category_column_names raises an AssertionError
        with pytest.raises(AssertionError, match="category_column_names cannot be None"):
            await pivot_table.my_update_dashboard_add_pivot_table(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                category_column_names=None,
                date_column_names=["Date"],
                date_granularity="MONTH",
                value_column_names=["sales", "profit"],
                value_column_aggregation=["SUM", "AVERAGE"],
            )

    async def test_update_dashboard_add_pivot_table_none_date_column_names(self):
        """Test my_update_dashboard_add_pivot_table with None as date_column_names (should raise AssertionError)."""
        # Verify that passing None as date_column_names raises an AssertionError
        with pytest.raises(AssertionError, match="date_column_names cannot be None"):
            await pivot_table.my_update_dashboard_add_pivot_table(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                category_column_names=["product", "region"],
                date_column_names=None,
                date_granularity="MONTH",
                value_column_names=["sales", "profit"],
                value_column_aggregation=["SUM", "AVERAGE"],
            )

    async def test_update_dashboard_add_pivot_table_none_date_granularity(self):
        """Test my_update_dashboard_add_pivot_table with None as date_granularity (should raise AssertionError)."""
        # Verify that passing None as date_granularity raises an AssertionError
        with pytest.raises(AssertionError, match="date_granularity cannot be None"):
            await pivot_table.my_update_dashboard_add_pivot_table(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                category_column_names=["product", "region"],
                date_column_names=["Date"],
                date_granularity=None,
                value_column_names=["sales", "profit"],
                value_column_aggregation=["SUM", "AVERAGE"],
            )

    async def test_update_dashboard_add_pivot_table_none_value_column_names(self):
        """Test my_update_dashboard_add_pivot_table with None as value_column_names (should raise AssertionError)."""
        # Verify that passing None as value_column_names raises an AssertionError
        with pytest.raises(AssertionError, match="value_column_names cannot be None"):
            await pivot_table.my_update_dashboard_add_pivot_table(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                category_column_names=["product", "region"],
                date_column_names=["Date"],
                date_granularity="MONTH",
                value_column_names=None,
                value_column_aggregation=["SUM", "AVERAGE"],
            )

    async def test_update_dashboard_add_pivot_table_none_value_column_aggregation(self):
        """Test my_update_dashboard_add_pivot_table with None as value_column_aggregation (should raise AssertionError)."""
        # Verify that passing None as value_column_aggregation raises an AssertionError
        with pytest.raises(AssertionError, match="value_column_aggregation cannot be None"):
            await pivot_table.my_update_dashboard_add_pivot_table(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                category_column_names=["product", "region"],
                date_column_names=["Date"],
                date_granularity="MONTH",
                value_column_names=["sales", "profit"],
                value_column_aggregation=None,
            )


class TestUpdatePivotTableEditCalculation(IsolatedAsyncioTestCase):
    """
    Test cases for update_pivot_table_edit_calculation function.

    Tests calculation editing, finding visuals, calculation types, group by options, and visual structure.
    """

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.update_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_calculated_field")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_dash_version")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.my_update_dashboard_publish")
    async def test_update_pivot_table_edit_calculation_success(
        self,
        mock_publish,
        mock_get_dash_version,
        mock_create_calculated_field,
        mock_update_visual,
        mock_get_current_visuals,
        mock_client,
    ):
        """Test update_pivot_table_edit_calculation with valid parameters."""
        # Setup mock visuals with a pivot table
        mock_pivot_table = {
            "PivotTableVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {
                        "PivotTableAggregatedFieldWells": {
                            "Rows": [
                                {
                                    "CategoricalDimensionField": {
                                        "FieldId": "region",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
                                            "ColumnName": "region",
                                        },
                                    }
                                },
                                {
                                    "CategoricalDimensionField": {
                                        "FieldId": "product",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
                                            "ColumnName": "product",
                                        },
                                    }
                                },
                            ],
                            "Values": [
                                {
                                    "NumericalMeasureField": {
                                        "FieldId": "sales",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
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
        mock_visuals = [mock_pivot_table]
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock calculated field
        mock_calculated_field = {
            "CalculatedMeasureField": {
                "FieldId": "sales",
                "Expression": "runningSum({sales})",
            }
        }
        mock_create_calculated_field.return_value = mock_calculated_field

        # Setup mock updated definition
        mock_updated_definition = {
            "DataSetIdentifierDeclarations": [],
            "Sheets": [
                {
                    "SheetId": "sheet1",
                    "Name": "Sheet 1",
                    "Visuals": [mock_pivot_table],
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

        # Setup mock version and publish response
        mock_get_dash_version.return_value = 2
        mock_publish.return_value = {"Status": 200}

        # Call the function
        result = await pivot_table.update_pivot_table_edit_calculation(
            dash_id="dashboard1",
            dash_name="Dashboard 1",
            sheet_id="sheet1",
            visual_id="visual1",
            value_col="sales",
            calc_type="Running_Total",
            agg_type="Sum",
            by_group=True,
        )

        # Verify get_current_visuals was called correctly
        mock_get_current_visuals.assert_called_once_with("dashboard1", "sheet1")

        # Verify create_calculated_field was called with the correct parameters
        # The group should be "region" (second-to-last category)
        mock_create_calculated_field.assert_called_once_with(
            "sales", "Running_Total", "Sum", "region", ["region", "product"]
        )

        # Verify update_visual was called with the updated visuals
        mock_update_visual.assert_called_once_with("dashboard1", "sheet1", mock_visuals)

        # Verify client.update_dashboard was called correctly
        mock_client.update_dashboard.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID,
            DashboardId="dashboard1",
            Name="Dashboard 1",
            Definition=mock_updated_definition,
        )

        # Verify get_dash_version and publish were called correctly
        mock_get_dash_version.assert_called_once_with(mock_response)
        mock_publish.assert_called_once_with("dashboard1", 2)

        # Verify the result
        self.assertEqual(result, mock_response)

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_current_visuals")
    async def test_update_pivot_table_edit_calculation_visual_not_found(
        self, mock_get_current_visuals
    ):
        """Test update_pivot_table_edit_calculation when the visual_id doesn't exist."""
        # Setup mock visuals without the target pivot table
        mock_visuals = [
            {
                "LineChartVisual": {
                    "VisualId": "visual2",
                    "Title": {"Visibility": "VISIBLE"},
                }
            }
        ]
        mock_get_current_visuals.return_value = mock_visuals

        # Verify that the function raises an AssertionError when the visual is not found
        with pytest.raises(
            AssertionError, match="Pivot table does not exist in the dashboard sheet yet"
        ):
            await pivot_table.update_pivot_table_edit_calculation(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",  # This visual_id doesn't exist
                value_col="sales",
                calc_type="Running_Total",
                agg_type="Sum",
                by_group=True,
            )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.update_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_calculated_field")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_dash_version")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.my_update_dashboard_publish")
    async def test_update_pivot_table_edit_calculation_existing_calculation(
        self,
        mock_publish,
        mock_get_dash_version,
        mock_create_calculated_field,
        mock_update_visual,
        mock_get_current_visuals,
        mock_client,
    ):
        """Test update_pivot_table_edit_calculation with an existing calculation."""
        # Setup mock visuals with a pivot table that already has a calculated field
        mock_pivot_table = {
            "PivotTableVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {
                        "PivotTableAggregatedFieldWells": {
                            "Rows": [
                                {
                                    "CategoricalDimensionField": {
                                        "FieldId": "region",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
                                            "ColumnName": "region",
                                        },
                                    }
                                }
                            ],
                            "Values": [
                                {
                                    "CalculatedMeasureField": {
                                        "FieldId": "sales",
                                        "Expression": "runningSum({sales})",
                                    }
                                },
                                {
                                    "NumericalMeasureField": {
                                        "FieldId": "profit",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
                                            "ColumnName": "profit",
                                        },
                                        "AggregationFunction": {
                                            "SimpleNumericalAggregation": "SUM"
                                        },
                                    }
                                },
                            ],
                        }
                    },
                },
            }
        }
        mock_visuals = [mock_pivot_table]
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock calculated field
        mock_calculated_field = {
            "CalculatedMeasureField": {
                "FieldId": "sales",
                "Expression": "percentDifference({sales})",
            }
        }
        mock_create_calculated_field.return_value = mock_calculated_field

        # Setup mock updated definition
        mock_updated_definition = {
            "DataSetIdentifierDeclarations": [],
            "Sheets": [
                {
                    "SheetId": "sheet1",
                    "Name": "Sheet 1",
                    "Visuals": [mock_pivot_table],
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

        # Setup mock version and publish response
        mock_get_dash_version.return_value = 2
        mock_publish.return_value = {"Status": 200}

        # Call the function to replace the existing calculation
        result = await pivot_table.update_pivot_table_edit_calculation(
            dash_id="dashboard1",
            dash_name="Dashboard 1",
            sheet_id="sheet1",
            visual_id="visual1",
            value_col="sales",
            calc_type="Percentage_Difference",
            agg_type="Sum",
            by_group=False,
        )

        # Verify create_calculated_field was called with the correct parameters
        mock_create_calculated_field.assert_called_once_with(
            "sales", "Percentage_Difference", "Sum", "", ["region"]
        )

        # Verify the result
        self.assertEqual(result, mock_response)

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.update_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_calculated_field")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_dash_version")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.my_update_dashboard_publish")
    async def test_update_pivot_table_edit_calculation_by_group_false(
        self,
        mock_publish,
        mock_get_dash_version,
        mock_create_calculated_field,
        mock_update_visual,
        mock_get_current_visuals,
        mock_client,
    ):
        """Test update_pivot_table_edit_calculation with by_group=False."""
        # Setup mock visuals with a pivot table
        mock_pivot_table = {
            "PivotTableVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {
                        "PivotTableAggregatedFieldWells": {
                            "Rows": [
                                {
                                    "CategoricalDimensionField": {
                                        "FieldId": "region",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
                                            "ColumnName": "region",
                                        },
                                    }
                                },
                                {
                                    "CategoricalDimensionField": {
                                        "FieldId": "product",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
                                            "ColumnName": "product",
                                        },
                                    }
                                },
                            ],
                            "Values": [
                                {
                                    "NumericalMeasureField": {
                                        "FieldId": "sales",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
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
        mock_visuals = [mock_pivot_table]
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock calculated field
        mock_calculated_field = {
            "CalculatedMeasureField": {
                "FieldId": "sales",
                "Expression": "percentOfTotal({sales})",
            }
        }
        mock_create_calculated_field.return_value = mock_calculated_field

        # Setup mock updated definition and response
        mock_update_visual.return_value = {
            "Sheets": [{"SheetId": "sheet1", "Visuals": mock_visuals}]
        }
        mock_client.update_dashboard.return_value = {"Status": 200}
        mock_get_dash_version.return_value = 2
        mock_publish.return_value = {"Status": 200}

        # Call the function with by_group=False
        await pivot_table.update_pivot_table_edit_calculation(
            dash_id="dashboard1",
            dash_name="Dashboard 1",
            sheet_id="sheet1",
            visual_id="visual1",
            value_col="sales",
            calc_type="Percent_of_Total",
            agg_type="Sum",
            by_group=False,  # Calculate by the table, not by group
        )

        # Verify create_calculated_field was called with empty group
        mock_create_calculated_field.assert_called_once_with(
            "sales", "Percent_of_Total", "Sum", "", ["region", "product"]
        )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.update_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_calculated_field")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_dash_version")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.my_update_dashboard_publish")
    async def test_update_pivot_table_edit_calculation_single_category(
        self,
        mock_publish,
        mock_get_dash_version,
        mock_create_calculated_field,
        mock_update_visual,
        mock_get_current_visuals,
        mock_client,
    ):
        """Test update_pivot_table_edit_calculation with only one category."""
        # Setup mock visuals with a pivot table that has only one category
        mock_pivot_table = {
            "PivotTableVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {
                        "PivotTableAggregatedFieldWells": {
                            "Rows": [
                                {
                                    "CategoricalDimensionField": {
                                        "FieldId": "region",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
                                            "ColumnName": "region",
                                        },
                                    }
                                }
                            ],
                            "Values": [
                                {
                                    "NumericalMeasureField": {
                                        "FieldId": "sales",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
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
        mock_visuals = [mock_pivot_table]
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock calculated field
        mock_calculated_field = {
            "CalculatedMeasureField": {
                "FieldId": "sales",
                "Expression": "rank({sales})",
            }
        }
        mock_create_calculated_field.return_value = mock_calculated_field

        # Setup mock updated definition and response
        mock_update_visual.return_value = {
            "Sheets": [{"SheetId": "sheet1", "Visuals": mock_visuals}]
        }
        mock_client.update_dashboard.return_value = {"Status": 200}
        mock_get_dash_version.return_value = 2
        mock_publish.return_value = {"Status": 200}

        # Call the function with by_group=True, but there's only one category
        await pivot_table.update_pivot_table_edit_calculation(
            dash_id="dashboard1",
            dash_name="Dashboard 1",
            sheet_id="sheet1",
            visual_id="visual1",
            value_col="sales",
            calc_type="Rank",
            agg_type="Sum",
            by_group=True,  # Even though by_group is True, there's no group to use
        )

        # Verify create_calculated_field was called with empty group
        # since there's only one category, there's no second-to-last category to use as group
        mock_create_calculated_field.assert_called_once_with("sales", "Rank", "Sum", "", ["region"])

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.update_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_calculated_field")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_dash_version")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.my_update_dashboard_publish")
    async def test_update_pivot_table_edit_calculation_column_wise(
        self,
        mock_publish,
        mock_get_dash_version,
        mock_create_calculated_field,
        mock_update_visual,
        mock_get_current_visuals,
        mock_client,
    ):
        """Test update_pivot_table_edit_calculation with column-wise table."""
        # Setup mock visuals with a pivot table that has empty Rows but populated Columns
        mock_pivot_table = {
            "PivotTableVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {
                        "PivotTableAggregatedFieldWells": {
                            "Rows": [],
                            "Columns": [
                                {
                                    "CategoricalDimensionField": {
                                        "FieldId": "region",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
                                            "ColumnName": "region",
                                        },
                                    }
                                },
                                {
                                    "CategoricalDimensionField": {
                                        "FieldId": "product",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
                                            "ColumnName": "product",
                                        },
                                    }
                                },
                            ],
                            "Values": [
                                {
                                    "NumericalMeasureField": {
                                        "FieldId": "sales",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
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
        mock_visuals = [mock_pivot_table]
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock calculated field
        mock_calculated_field = {
            "CalculatedMeasureField": {
                "FieldId": "sales",
                "Expression": "difference({sales})",
            }
        }
        mock_create_calculated_field.return_value = mock_calculated_field

        # Setup mock updated definition and response
        mock_update_visual.return_value = {
            "Sheets": [{"SheetId": "sheet1", "Visuals": mock_visuals}]
        }
        mock_client.update_dashboard.return_value = {"Status": 200}
        mock_get_dash_version.return_value = 2
        mock_publish.return_value = {"Status": 200}

        # Call the function with by_group=True
        await pivot_table.update_pivot_table_edit_calculation(
            dash_id="dashboard1",
            dash_name="Dashboard 1",
            sheet_id="sheet1",
            visual_id="visual1",
            value_col="sales",
            calc_type="Difference",
            agg_type="Sum",
            by_group=True,
        )

        # Verify create_calculated_field was called with "region" as group
        # since it's the second-to-last category in Columns
        mock_create_calculated_field.assert_called_once_with(
            "sales", "Difference", "Sum", "region", ["region", "product"]
        )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.update_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_calculated_field")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_dash_version")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.my_update_dashboard_publish")
    async def test_update_pivot_table_edit_calculation_date_dimension(
        self,
        mock_publish,
        mock_get_dash_version,
        mock_create_calculated_field,
        mock_update_visual,
        mock_get_current_visuals,
        mock_client,
    ):
        """Test update_pivot_table_edit_calculation with DateDimensionField."""
        # Setup mock visuals with a pivot table that has DateDimensionField
        mock_pivot_table = {
            "PivotTableVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {
                        "PivotTableAggregatedFieldWells": {
                            "Rows": [
                                {
                                    "DateDimensionField": {
                                        "FieldId": "date",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
                                            "ColumnName": "date",
                                        },
                                    }
                                },
                                {
                                    "CategoricalDimensionField": {
                                        "FieldId": "product",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
                                            "ColumnName": "product",
                                        },
                                    }
                                },
                            ],
                            "Values": [
                                {
                                    "NumericalMeasureField": {
                                        "FieldId": "sales",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
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
        mock_visuals = [mock_pivot_table]
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock calculated field
        mock_calculated_field = {
            "CalculatedMeasureField": {
                "FieldId": "sales",
                "Expression": "percentile({sales})",
            }
        }
        mock_create_calculated_field.return_value = mock_calculated_field

        # Setup mock updated definition and response
        mock_update_visual.return_value = {
            "Sheets": [{"SheetId": "sheet1", "Visuals": mock_visuals}]
        }
        mock_client.update_dashboard.return_value = {"Status": 200}
        mock_get_dash_version.return_value = 2
        mock_publish.return_value = {"Status": 200}

        # Call the function with by_group=True
        await pivot_table.update_pivot_table_edit_calculation(
            dash_id="dashboard1",
            dash_name="Dashboard 1",
            sheet_id="sheet1",
            visual_id="visual1",
            value_col="sales",
            calc_type="Percentile",
            agg_type="Sum",
            by_group=True,
        )

        # Verify create_calculated_field was called with "date" as group
        # since it's the second-to-last category and it's a DateDimensionField
        mock_create_calculated_field.assert_called_once_with(
            "sales", "Percentile", "Sum", "date", ["date", "product"]
        )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.update_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.chart_config.create_calculated_field")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_dash_version")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.my_update_dashboard_publish")
    async def test_update_pivot_table_edit_calculation_preserve_order(
        self,
        mock_publish,
        mock_get_dash_version,
        mock_create_calculated_field,
        mock_update_visual,
        mock_get_current_visuals,
        mock_client,
    ):
        """Test update_pivot_table_edit_calculation preserves the order of columns."""
        # Setup mock visuals with a pivot table that has multiple value columns
        mock_pivot_table = {
            "PivotTableVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {
                        "PivotTableAggregatedFieldWells": {
                            "Rows": [
                                {
                                    "CategoricalDimensionField": {
                                        "FieldId": "region",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
                                            "ColumnName": "region",
                                        },
                                    }
                                }
                            ],
                            "Values": [
                                {
                                    "NumericalMeasureField": {
                                        "FieldId": "profit",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
                                            "ColumnName": "profit",
                                        },
                                        "AggregationFunction": {
                                            "SimpleNumericalAggregation": "SUM"
                                        },
                                    }
                                },
                                {
                                    "NumericalMeasureField": {
                                        "FieldId": "sales",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
                                            "ColumnName": "sales",
                                        },
                                        "AggregationFunction": {
                                            "SimpleNumericalAggregation": "SUM"
                                        },
                                    }
                                },
                                {
                                    "NumericalMeasureField": {
                                        "FieldId": "quantity",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
                                            "ColumnName": "quantity",
                                        },
                                        "AggregationFunction": {
                                            "SimpleNumericalAggregation": "SUM"
                                        },
                                    }
                                },
                            ],
                        }
                    },
                },
            }
        }
        mock_visuals = [mock_pivot_table]
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock calculated field
        mock_calculated_field = {
            "CalculatedMeasureField": {
                "FieldId": "sales",
                "Expression": "runningSum({sales})",
            }
        }
        mock_create_calculated_field.return_value = mock_calculated_field

        # Setup mock updated definition and response
        mock_update_visual.return_value = {
            "Sheets": [{"SheetId": "sheet1", "Visuals": mock_visuals}]
        }
        mock_client.update_dashboard.return_value = {"Status": 200}
        mock_get_dash_version.return_value = 2
        mock_publish.return_value = {"Status": 200}

        # Store the original values array to check order preservation later
        original_values = mock_pivot_table["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
            "PivotTableAggregatedFieldWells"
        ]["Values"].copy()

        # Find the index of the sales column
        sales_index = -1
        for i, value in enumerate(original_values):
            if (
                "NumericalMeasureField" in value
                and value["NumericalMeasureField"]["FieldId"] == "sales"
            ):
                sales_index = i
                break

        self.assertGreaterEqual(sales_index, 0, "Sales column not found in values")

        # Call the function to replace the sales column with a calculated field
        await pivot_table.update_pivot_table_edit_calculation(
            dash_id="dashboard1",
            dash_name="Dashboard 1",
            sheet_id="sheet1",
            visual_id="visual1",
            value_col="sales",
            calc_type="Running_Total",
            agg_type="Sum",
            by_group=False,
        )

        # Verify create_calculated_field was called with the correct parameters
        mock_create_calculated_field.assert_called_once_with(
            "sales", "Running_Total", "Sum", "", ["region"]
        )

        # Verify the calculated field was inserted at the same index as the original sales column
        values_after = mock_pivot_table["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
            "PivotTableAggregatedFieldWells"
        ]["Values"]
        self.assertEqual(len(original_values), len(values_after), "Number of value columns changed")
        self.assertEqual(
            values_after[sales_index],
            mock_calculated_field,
            "Calculated field not inserted at the correct position",
        )

        # Verify the other columns remain in the same order
        for i in range(len(original_values)):
            if i != sales_index:
                self.assertEqual(
                    original_values[i],
                    values_after[i],
                    f"Column at index {i} was changed unexpectedly",
                )


class TestUpdatePivotTableChangeOrientation(IsolatedAsyncioTestCase):
    """
    Test cases for update_pivot_table_change_orientation function.

    Tests orientation change and finding visuals.
    """

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.update_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_dash_version")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.my_update_dashboard_publish")
    async def test_update_pivot_table_change_orientation_row_to_column(
        self,
        mock_publish,
        mock_get_dash_version,
        mock_update_visual,
        mock_get_current_visuals,
        mock_client,
    ):
        """Test update_pivot_table_change_orientation changing from row-wise to column-wise."""
        # Setup mock visuals with a row-wise pivot table
        mock_pivot_table = {
            "PivotTableVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {
                        "PivotTableAggregatedFieldWells": {
                            "Rows": [
                                {
                                    "CategoricalDimensionField": {
                                        "FieldId": "region",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
                                            "ColumnName": "region",
                                        },
                                    }
                                },
                                {
                                    "CategoricalDimensionField": {
                                        "FieldId": "product",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
                                            "ColumnName": "product",
                                        },
                                    }
                                },
                            ],
                            "Columns": [],
                            "Values": [
                                {
                                    "NumericalMeasureField": {
                                        "FieldId": "sales",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
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
        mock_visuals = [mock_pivot_table]
        mock_get_current_visuals.return_value = mock_visuals

        # Store the original Rows and Columns for later comparison
        original_rows = mock_pivot_table["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
            "PivotTableAggregatedFieldWells"
        ]["Rows"].copy()
        original_columns = mock_pivot_table["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
            "PivotTableAggregatedFieldWells"
        ]["Columns"].copy()

        # Setup mock updated definition
        mock_updated_definition = {
            "DataSetIdentifierDeclarations": [],
            "Sheets": [
                {
                    "SheetId": "sheet1",
                    "Name": "Sheet 1",
                    "Visuals": [mock_pivot_table],
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

        # Setup mock version and publish response
        mock_get_dash_version.return_value = 2
        mock_publish.return_value = {"Status": 200}

        # Call the function
        result = await pivot_table.update_pivot_table_change_orientation(
            dash_id="dashboard1",
            dash_name="Dashboard 1",
            sheet_id="sheet1",
            visual_id="visual1",
        )

        # Verify get_current_visuals was called correctly
        mock_get_current_visuals.assert_called_once_with("dashboard1", "sheet1")

        # Verify the Rows and Columns were swapped
        current_rows = mock_pivot_table["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
            "PivotTableAggregatedFieldWells"
        ]["Rows"]
        current_columns = mock_pivot_table["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
            "PivotTableAggregatedFieldWells"
        ]["Columns"]

        self.assertEqual(current_rows, original_columns, "Rows should be equal to original Columns")
        self.assertEqual(current_columns, original_rows, "Columns should be equal to original Rows")

        # Verify update_visual was called with the updated visuals
        mock_update_visual.assert_called_once_with("dashboard1", "sheet1", mock_visuals)

        # Verify client.update_dashboard was called correctly
        mock_client.update_dashboard.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID,
            DashboardId="dashboard1",
            Name="Dashboard 1",
            Definition=mock_updated_definition,
        )

        # Verify get_dash_version and publish were called correctly
        mock_get_dash_version.assert_called_once_with(mock_response)
        mock_publish.assert_called_once_with("dashboard1", 2)

        # Verify the result
        self.assertEqual(result, mock_response)

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.update_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_dash_version")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.my_update_dashboard_publish")
    async def test_update_pivot_table_change_orientation_column_to_row(
        self,
        mock_publish,
        mock_get_dash_version,
        mock_update_visual,
        mock_get_current_visuals,
        mock_client,
    ):
        """Test update_pivot_table_change_orientation changing from column-wise to row-wise."""
        # Setup mock visuals with a column-wise pivot table
        mock_pivot_table = {
            "PivotTableVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {
                        "PivotTableAggregatedFieldWells": {
                            "Rows": [],
                            "Columns": [
                                {
                                    "CategoricalDimensionField": {
                                        "FieldId": "region",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
                                            "ColumnName": "region",
                                        },
                                    }
                                },
                                {
                                    "CategoricalDimensionField": {
                                        "FieldId": "product",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
                                            "ColumnName": "product",
                                        },
                                    }
                                },
                            ],
                            "Values": [
                                {
                                    "NumericalMeasureField": {
                                        "FieldId": "sales",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
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
        mock_visuals = [mock_pivot_table]
        mock_get_current_visuals.return_value = mock_visuals

        # Store the original Rows and Columns for later comparison
        original_rows = mock_pivot_table["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
            "PivotTableAggregatedFieldWells"
        ]["Rows"].copy()
        original_columns = mock_pivot_table["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
            "PivotTableAggregatedFieldWells"
        ]["Columns"].copy()

        # Setup mock updated definition
        mock_updated_definition = {
            "DataSetIdentifierDeclarations": [],
            "Sheets": [
                {
                    "SheetId": "sheet1",
                    "Name": "Sheet 1",
                    "Visuals": [mock_pivot_table],
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

        # Setup mock version and publish response
        mock_get_dash_version.return_value = 2
        mock_publish.return_value = {"Status": 200}

        # Call the function
        result = await pivot_table.update_pivot_table_change_orientation(
            dash_id="dashboard1",
            dash_name="Dashboard 1",
            sheet_id="sheet1",
            visual_id="visual1",
        )

        # Verify the Rows and Columns were swapped
        current_rows = mock_pivot_table["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
            "PivotTableAggregatedFieldWells"
        ]["Rows"]
        current_columns = mock_pivot_table["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
            "PivotTableAggregatedFieldWells"
        ]["Columns"]

        self.assertEqual(current_rows, original_columns, "Rows should be equal to original Columns")
        self.assertEqual(current_columns, original_rows, "Columns should be equal to original Rows")

        # Verify update_visual was called with the updated visuals
        mock_update_visual.assert_called_once_with("dashboard1", "sheet1", mock_visuals)

        # Verify the result
        self.assertEqual(result, mock_response)

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.update_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_dash_version")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.my_update_dashboard_publish")
    async def test_update_pivot_table_change_orientation_mixed_content(
        self,
        mock_publish,
        mock_get_dash_version,
        mock_update_visual,
        mock_get_current_visuals,
        mock_client,
    ):
        """Test update_pivot_table_change_orientation with mixed content in Rows and Columns."""
        # Setup mock visuals with a pivot table that has both Rows and Columns
        mock_pivot_table = {
            "PivotTableVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {
                        "PivotTableAggregatedFieldWells": {
                            "Rows": [
                                {
                                    "CategoricalDimensionField": {
                                        "FieldId": "region",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
                                            "ColumnName": "region",
                                        },
                                    }
                                }
                            ],
                            "Columns": [
                                {
                                    "DateDimensionField": {
                                        "FieldId": "date",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
                                            "ColumnName": "date",
                                        },
                                    }
                                }
                            ],
                            "Values": [
                                {
                                    "NumericalMeasureField": {
                                        "FieldId": "sales",
                                        "Column": {
                                            "DataSetIdentifier": "dataset1",
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
        mock_visuals = [mock_pivot_table]
        mock_get_current_visuals.return_value = mock_visuals

        # Store the original Rows and Columns for later comparison
        original_rows = mock_pivot_table["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
            "PivotTableAggregatedFieldWells"
        ]["Rows"].copy()
        original_columns = mock_pivot_table["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
            "PivotTableAggregatedFieldWells"
        ]["Columns"].copy()

        # Setup mock updated definition and response
        mock_update_visual.return_value = {
            "Sheets": [{"SheetId": "sheet1", "Visuals": mock_visuals}]
        }
        mock_client.update_dashboard.return_value = {"Status": 200}
        mock_get_dash_version.return_value = 2
        mock_publish.return_value = {"Status": 200}

        # Call the function
        await pivot_table.update_pivot_table_change_orientation(
            dash_id="dashboard1",
            dash_name="Dashboard 1",
            sheet_id="sheet1",
            visual_id="visual1",
        )

        # Verify the Rows and Columns were swapped
        current_rows = mock_pivot_table["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
            "PivotTableAggregatedFieldWells"
        ]["Rows"]
        current_columns = mock_pivot_table["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
            "PivotTableAggregatedFieldWells"
        ]["Columns"]

        self.assertEqual(current_rows, original_columns, "Rows should be equal to original Columns")
        self.assertEqual(current_columns, original_rows, "Columns should be equal to original Rows")

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table.qs.get_current_visuals")
    async def test_update_pivot_table_change_orientation_visual_not_found(
        self, mock_get_current_visuals
    ):
        """Test update_pivot_table_change_orientation when the visual_id doesn't exist."""
        # Setup mock visuals without the target pivot table
        mock_visuals = [
            {
                "LineChartVisual": {
                    "VisualId": "visual2",
                    "Title": {"Visibility": "VISIBLE"},
                }
            }
        ]
        mock_get_current_visuals.return_value = mock_visuals

        # Verify that the function raises an AssertionError when the visual is not found
        with pytest.raises(
            AssertionError, match="Pivot table does not exist in the dashboard sheet yet"
        ):
            await pivot_table.update_pivot_table_change_orientation(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",  # This visual_id doesn't exist
            )
