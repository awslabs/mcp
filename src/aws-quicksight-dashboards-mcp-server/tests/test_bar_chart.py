from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import patch

import pytest

import sys
from pathlib import Path

qs_mcp_directory = Path(__file__).parent.parent
sys.path.append(str(qs_mcp_directory))
print(qs_mcp_directory)

import awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart as bar_chart
import awslabs.aws_quicksight_dashboards_mcp_server.quicksight as qs


class TestMyUpdateDashboardAddBarChart(IsolatedAsyncioTestCase):
    """
    Test cases for my_update_dashboard_add_bar_chart function.

    Tests visual creation (getting chart object, update) and parameter validation
    """

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.qs.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.qs.update_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.create_bar_chart")
    async def test_update_dashboard_add_bar_chart_success(
        self, mock_create_bar_chart, mock_update_visual, mock_get_current_visuals, mock_client
    ):
        """Test my_update_dashboard_add_bar_chart with valid parameters."""
        # Setup mock response for describe_dashboard_definition
        mock_dashboard_definition = {
            "Definition": {
                "Sheets": [
                    {"SheetId": "sheet1", "Name": "Sheet 1", "Visuals": []}
                ]
            }
        }
        mock_client.describe_dashboard_definition.return_value = mock_dashboard_definition
        
        # Setup mock visuals
        mock_visuals = [
            {"LineChartVisual": {"VisualId": "visual1", "Title": {"Visibility": "VISIBLE"}}},
        ]
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock bar chart
        mock_bar_chart = {
            "BarChartVisual": {
                "VisualId": "visual2",
                "Title": {"Visibility": "VISIBLE"},
                "ChartConfiguration": {
                    "FieldWells": {"BarChartAggregatedFieldWells": {}},
                    "SortConfiguration": {},
                },
            }
        }
        mock_create_bar_chart.return_value = mock_bar_chart

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
                        mock_bar_chart,
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
        result = await bar_chart.my_update_dashboard_add_bar_chart(
            dash_id="dashboard1",
            dash_name="Dashboard 1",
            sheet_id="sheet1",
            visual_id="visual2",
            dataset_id="dataset1",
            sort_var="sales",
            category_column_name="product",
            category_column_type="Categorical",
            value_column_names=["sales", "profit"],
            color_column_name="region",
            sort_direction="DESC",
            numerical_aggregation="SUM",
            orientation="VERTICAL",
            bars_arrangement="CLUSTERED",
        )

        # Verify get_current_visuals was called correctly
        mock_get_current_visuals.assert_called_once_with("dashboard1", "sheet1")

        # Verify create_bar_chart was called with the correct parameters
        expected_bar_chart_params = {
            "visual_id": "visual2",
            "dataset_id": "dataset1",
            "numerical_aggregation": "SUM",
            "orientation": "VERTICAL",
            "sorting_variable": "sales",
            "sort_direction": "DESC",
            "category_column_name": "product",
            "category_column_type": "Categorical",
            "value_column_names": ["sales", "profit"],
            "color_column_name": "region",
            "bars_arrangement": "CLUSTERED",
            "date_granularity": "",
        }
        mock_create_bar_chart.assert_called_once_with(expected_bar_chart_params)

        # Verify update_visual was called with the updated visuals
        expected_visuals = [
            {"LineChartVisual": {"VisualId": "visual1", "Title": {"Visibility": "VISIBLE"}}},
            mock_bar_chart,
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

    async def test_update_dashboard_add_bar_chart_none_dash_id(self):
        """Test my_update_dashboard_add_bar_chart with None as dash_id (should raise AssertionError)."""
        # Verify that passing None as dash_id raises an AssertionError
        with pytest.raises(AssertionError, match="dash_id cannot be None"):
            await bar_chart.my_update_dashboard_add_bar_chart(
                dash_id=None,
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                sort_var="sales",
                category_column_name="product",
                category_column_type="Categorical",
                value_column_names=["sales"],
                color_column_name="",
                sort_direction="DESC",
                numerical_aggregation="SUM",
                orientation="VERTICAL",
                bars_arrangement="CLUSTERED",
            )

    async def test_update_dashboard_add_bar_chart_none_dash_name(self):
        """Test my_update_dashboard_add_bar_chart with None as dash_name (should raise AssertionError)."""
        # Verify that passing None as dash_name raises an AssertionError
        with pytest.raises(AssertionError, match="dash_name cannot be None"):
            await bar_chart.my_update_dashboard_add_bar_chart(
                dash_id="dashboard1",
                dash_name=None,
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                sort_var="sales",
                category_column_name="product",
                category_column_type="Categorical",
                value_column_names=["sales"],
                color_column_name="",
                sort_direction="DESC",
                numerical_aggregation="SUM",
                orientation="VERTICAL",
                bars_arrangement="CLUSTERED",
            )

    async def test_update_dashboard_add_bar_chart_none_sheet_id(self):
        """Test my_update_dashboard_add_bar_chart with None as sheet_id (should raise AssertionError)."""
        # Verify that passing None as sheet_id raises an AssertionError
        with pytest.raises(AssertionError, match="sheet_id cannot be None"):
            await bar_chart.my_update_dashboard_add_bar_chart(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id=None,
                visual_id="visual1",
                dataset_id="dataset1",
                sort_var="sales",
                category_column_name="product",
                category_column_type="Categorical",
                value_column_names=["sales"],
                color_column_name="",
                sort_direction="DESC",
                numerical_aggregation="SUM",
                orientation="VERTICAL",
                bars_arrangement="CLUSTERED",
            )

    async def test_update_dashboard_add_bar_chart_none_visual_id(self):
        """Test my_update_dashboard_add_bar_chart with None as visual_id (should raise AssertionError)."""
        # Verify that passing None as visual_id raises an AssertionError
        with pytest.raises(AssertionError, match="visual_id cannot be None"):
            await bar_chart.my_update_dashboard_add_bar_chart(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id=None,
                dataset_id="dataset1",
                sort_var="sales",
                category_column_name="product",
                category_column_type="Categorical",
                value_column_names=["sales"],
                color_column_name="",
                sort_direction="DESC",
                numerical_aggregation="SUM",
                orientation="VERTICAL",
                bars_arrangement="CLUSTERED",
            )

    async def test_update_dashboard_add_bar_chart_none_dataset_id(self):
        """Test my_update_dashboard_add_bar_chart with None as dataset_id (should raise AssertionError)."""
        # Verify that passing None as dataset_id raises an AssertionError
        with pytest.raises(AssertionError, match="dataset_id cannot be None"):
            await bar_chart.my_update_dashboard_add_bar_chart(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id=None,
                sort_var="sales",
                category_column_name="product",
                category_column_type="Categorical",
                value_column_names=["sales"],
                color_column_name="",
                sort_direction="DESC",
                numerical_aggregation="SUM",
                orientation="VERTICAL",
                bars_arrangement="CLUSTERED",
            )

    async def test_update_dashboard_add_bar_chart_none_sort_var(self):
        """Test my_update_dashboard_add_bar_chart with None as sort_var (should raise AssertionError)."""
        # Verify that passing None as sort_var raises an AssertionError
        with pytest.raises(AssertionError, match="sort_var cannot be None"):
            await bar_chart.my_update_dashboard_add_bar_chart(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                sort_var=None,
                category_column_name="product",
                category_column_type="Categorical",
                value_column_names=["sales"],
                color_column_name="",
                sort_direction="DESC",
                numerical_aggregation="SUM",
                orientation="VERTICAL",
                bars_arrangement="CLUSTERED",
            )

    async def test_update_dashboard_add_bar_chart_none_category_column_name(self):
        """Test my_update_dashboard_add_bar_chart with None as category_column_name (should raise AssertionError)."""
        # Verify that passing None as category_column_name raises an AssertionError
        with pytest.raises(AssertionError, match="category_column_name cannot be None"):
            await bar_chart.my_update_dashboard_add_bar_chart(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                sort_var="sales",
                category_column_name=None,
                category_column_type="Categorical",
                value_column_names=["sales"],
                color_column_name="",
                sort_direction="DESC",
                numerical_aggregation="SUM",
                orientation="VERTICAL",
                bars_arrangement="CLUSTERED",
            )

    async def test_update_dashboard_add_bar_chart_none_category_column_type(self):
        """Test my_update_dashboard_add_bar_chart with None as category_column_type (should raise AssertionError)."""
        # Verify that passing None as category_column_type raises an AssertionError
        with pytest.raises(AssertionError, match="category_column_type cannot be None"):
            await bar_chart.my_update_dashboard_add_bar_chart(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                sort_var="sales",
                category_column_name="product",
                category_column_type=None,
                value_column_names=["sales"],
                color_column_name="",
                sort_direction="DESC",
                numerical_aggregation="SUM",
                orientation="VERTICAL",
                bars_arrangement="CLUSTERED",
            )

    async def test_update_dashboard_add_bar_chart_none_value_column_names(self):
        """Test my_update_dashboard_add_bar_chart with None as value_column_names (should raise AssertionError)."""
        # Verify that passing None as value_column_names raises an AssertionError
        with pytest.raises(AssertionError, match="value_column_names cannot be None"):
            await bar_chart.my_update_dashboard_add_bar_chart(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                sort_var="sales",
                category_column_name="product",
                category_column_type="Categorical",
                value_column_names=None,
                color_column_name="",
                sort_direction="DESC",
                numerical_aggregation="SUM",
                orientation="VERTICAL",
                bars_arrangement="CLUSTERED",
            )

    async def test_update_dashboard_add_bar_chart_none_color_column_name(self):
        """Test my_update_dashboard_add_bar_chart with None as color_column_name (should raise AssertionError)."""
        # Verify that passing None as color_column_name raises an AssertionError
        with pytest.raises(AssertionError, match="color_column_name cannot be None"):
            await bar_chart.my_update_dashboard_add_bar_chart(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                sort_var="sales",
                category_column_name="product",
                category_column_type="Categorical",
                value_column_names=["sales"],
                color_column_name=None,
                sort_direction="DESC",
                numerical_aggregation="SUM",
                orientation="VERTICAL",
                bars_arrangement="CLUSTERED",
            )

    async def test_update_dashboard_add_bar_chart_none_sort_direction(self):
        """Test my_update_dashboard_add_bar_chart with None as sort_direction (should raise AssertionError)."""
        # Verify that passing None as sort_direction raises an AssertionError
        with pytest.raises(AssertionError, match="sort_direction cannot be None"):
            await bar_chart.my_update_dashboard_add_bar_chart(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                sort_var="sales",
                category_column_name="product",
                category_column_type="Categorical",
                value_column_names=["sales"],
                color_column_name="",
                sort_direction=None,
                numerical_aggregation="SUM",
                orientation="VERTICAL",
                bars_arrangement="CLUSTERED",
            )

    async def test_update_dashboard_add_bar_chart_none_numerical_aggregation(self):
        """Test my_update_dashboard_add_bar_chart with None as numerical_aggregation (should raise AssertionError)."""
        # Verify that passing None as numerical_aggregation raises an AssertionError
        with pytest.raises(AssertionError, match="numerical_aggregation cannot be None"):
            await bar_chart.my_update_dashboard_add_bar_chart(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                sort_var="sales",
                category_column_name="product",
                category_column_type="Categorical",
                value_column_names=["sales"],
                color_column_name="",
                sort_direction="DESC",
                numerical_aggregation=None,
                orientation="VERTICAL",
                bars_arrangement="CLUSTERED",
            )

    async def test_update_dashboard_add_bar_chart_none_orientation(self):
        """Test my_update_dashboard_add_bar_chart with None as orientation (should raise AssertionError)."""
        # Verify that passing None as orientation raises an AssertionError
        with pytest.raises(AssertionError, match="orientation cannot be None"):
            await bar_chart.my_update_dashboard_add_bar_chart(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                sort_var="sales",
                category_column_name="product",
                category_column_type="Categorical",
                value_column_names=["sales"],
                color_column_name="",
                sort_direction="DESC",
                numerical_aggregation="SUM",
                orientation=None,
                bars_arrangement="CLUSTERED",
            )

    async def test_update_dashboard_add_bar_chart_none_bars_arrangment(self):
        """Test my_update_dashboard_add_bar_chart with None as bars_arrangment (should raise AssertionError)."""
        # Verify that passing None as bars_arrangment raises an AssertionError
        with pytest.raises(AssertionError, match="bars_arrangement cannot be None"):
            await bar_chart.my_update_dashboard_add_bar_chart(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                sort_var="sales",
                category_column_name="product",
                category_column_type="Categorical",
                value_column_names=["sales"],
                color_column_name="",
                sort_direction="DESC",
                numerical_aggregation="SUM",
                orientation="VERTICAL",
                bars_arrangement=None,
            )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.qs.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.create_bar_chart")
    async def test_update_dashboard_add_bar_chart_create_error(
        self, mock_create_bar_chart, mock_get_current_visuals, mock_client
    ):
        """Test my_update_dashboard_add_bar_chart when create_bar_chart raises an exception."""
        # Setup mock response for describe_dashboard_definition
        mock_dashboard_definition = {
            "Definition": {
                "Sheets": [
                    {"SheetId": "sheet1", "Name": "Sheet 1", "Visuals": []}
                ]
            }
        }
        mock_client.describe_dashboard_definition.return_value = mock_dashboard_definition
        
        # Setup mock visuals
        mock_visuals = []
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock to raise an exception
        mock_create_bar_chart.side_effect = Exception("Create Error")

        # Verify the exception is propagated
        with self.assertRaises(Exception) as context:
            await bar_chart.my_update_dashboard_add_bar_chart(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                sort_var="sales",
                category_column_name="product",
                category_column_type="Categorical",
                value_column_names=["sales"],
                color_column_name="",
                sort_direction="DESC",
                numerical_aggregation="SUM",
                orientation="VERTICAL",
                bars_arrangement="CLUSTERED",
            )

        # Verify the exception message
        self.assertEqual(str(context.exception), "Create Error")

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.qs.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.create_bar_chart")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.qs.update_visual")
    async def test_update_dashboard_add_bar_chart_update_error(
        self, mock_update_visual, mock_create_bar_chart, mock_get_current_visuals, mock_client
    ):
        """Test my_update_dashboard_add_bar_chart when update_visual raises an exception."""
        # Setup mock response for describe_dashboard_definition
        mock_dashboard_definition = {
            "Definition": {
                "Sheets": [
                    {"SheetId": "sheet1", "Name": "Sheet 1", "Visuals": []}
                ]
            }
        }
        mock_client.describe_dashboard_definition.return_value = mock_dashboard_definition
        
        # Setup mock visuals
        mock_visuals = []
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock bar chart
        mock_bar_chart = {
            "BarChartVisual": {
                "VisualId": "visual1",
                "Title": {"Visibility": "VISIBLE"},
                "ChartConfiguration": {
                    "FieldWells": {"BarChartAggregatedFieldWells": {}},
                    "SortConfiguration": {},
                },
            }
        }
        mock_create_bar_chart.return_value = mock_bar_chart

        # Setup mock to raise an exception
        mock_update_visual.side_effect = Exception("Update Error")

        # Verify the exception is propagated
        with self.assertRaises(Exception) as context:
            await bar_chart.my_update_dashboard_add_bar_chart(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                sort_var="sales",
                category_column_name="product",
                category_column_type="Categorical",
                value_column_names=["sales"],
                color_column_name="",
                sort_direction="DESC",
                numerical_aggregation="SUM",
                orientation="VERTICAL",
                bars_arrangement="CLUSTERED",
            )

        # Verify the exception message
        self.assertEqual(str(context.exception), "Update Error")

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.qs.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.qs.get_current_visuals")
    async def test_update_dashboard_add_bar_chart_none_visuals(self, mock_get_current_visuals, mock_client):
        """Test my_update_dashboard_add_bar_chart when get_current_visuals returns None."""
        # Setup mock response for describe_dashboard_definition
        mock_dashboard_definition = {
            "Definition": {
                "Sheets": [
                    {"SheetId": "sheet1", "Name": "Sheet 1", "Visuals": []}
                ]
            }
        }
        mock_client.describe_dashboard_definition.return_value = mock_dashboard_definition
        
        # Setup mock to return None (sheet not found)
        mock_get_current_visuals.return_value = None

        # Verify the function raises an exception when visuals is None
        with self.assertRaises(Exception):
            await bar_chart.my_update_dashboard_add_bar_chart(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                sort_var="sales",
                category_column_name="product",
                category_column_type="Categorical",
                value_column_names=["sales"],
                color_column_name="",
                sort_direction="DESC",
                numerical_aggregation="SUM",
                orientation="VERTICAL",
                bars_arrangement="CLUSTERED",
            )


class TestCreateEmptyBarChartVisual(TestCase):
    """Test cases for create_empty_bar_chart_visual function."""

    @patch("builtins.open")
    @patch("json.load")
    def test_create_empty_bar_chart_visual_success(self, mock_json_load, mock_open):
        """Test create_empty_bar_chart_visual with a valid visual_id."""
        # Setup mock response for json.load
        mock_bar_chart = {
            "BarChartVisual": {
                "VisualId": "",
                "Title": {"Visibility": "VISIBLE"},
                "ChartConfiguration": {
                    "FieldWells": {"BarChartAggregatedFieldWells": {}},
                    "SortConfiguration": {},
                },
            }
        }
        mock_json_load.return_value = mock_bar_chart

        # Call the function
        result = bar_chart.create_empty_bar_chart_visual("visual1")

        # Verify open was called with the correct path
        self.assertEqual(mock_open.call_count, 1)
        call_args = mock_open.call_args[0]
        self.assertEqual(len(call_args), 2)
        self.assertTrue(call_args[0].endswith("json_definitions/bar_chart_definition.json"))
        self.assertEqual(call_args[1], "r")

        # Verify json.load was called correctly
        mock_json_load.assert_called_once()

        # Verify the visual_id was set correctly
        self.assertEqual(result["BarChartVisual"]["VisualId"], "visual1")

    def test_create_empty_bar_chart_visual_none_visual_id(self):
        """Test create_empty_bar_chart_visual with None as visual_id (should raise AssertionError)."""
        # Verify that passing None as visual_id raises an AssertionError
        with self.assertRaises(AssertionError) as context:
            bar_chart.create_empty_bar_chart_visual(None)

        # Verify the exception message
        self.assertEqual(str(context.exception), "visual cannot be None")

    @patch("builtins.open")
    def test_create_empty_bar_chart_visual_file_error(self, mock_open):
        """Test create_empty_bar_chart_visual when there's an error opening the JSON file."""
        # Setup mock to raise an exception
        mock_open.side_effect = FileNotFoundError("File not found")

        # Verify the exception is propagated
        with self.assertRaises(FileNotFoundError) as context:
            bar_chart.create_empty_bar_chart_visual("visual1")

        # Verify the exception message
        self.assertEqual(str(context.exception), "File not found")


class TestCreateBarChart(TestCase):
    """
    Test cases for create_bar_chart function.

    Tests structure of bar chart object for each parameter
    """

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.create_empty_bar_chart_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_category")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_value")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_category_sort")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_tool_tip_item")
    def test_create_bar_chart_basic(
        self,
        mock_create_tool_tip_item,
        mock_create_category_sort,
        mock_create_value,
        mock_create_category,
        mock_create_empty_bar_chart_visual,
    ):
        """Test create_bar_chart with basic valid parameters."""
        # Setup mock responses
        mock_empty_chart = {
            "BarChartVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {
                        "BarChartAggregatedFieldWells": {"Category": [], "Values": [], "Colors": []}
                    },
                    "SortConfiguration": {"CategorySort": []},
                    "Tooltip": {"FieldBasedTooltip": {"TooltipFields": []}},
                    "Orientation": "VERTICAL",
                },
                "ColumnHierarchies": [],
            }
        }
        mock_create_empty_bar_chart_visual.return_value = mock_empty_chart

        mock_category = {"CategoricalDimensionField": {"FieldId": "product"}}
        mock_create_category.return_value = mock_category

        mock_value = {"NumericalMeasureField": {"FieldId": "sales"}}
        mock_create_value.return_value = mock_value

        mock_category_sort = {"FieldSort": {"FieldId": "sales", "Direction": "DESC"}}
        mock_create_category_sort.return_value = mock_category_sort

        mock_create_tool_tip_item.side_effect = [
            {"FieldTooltipItem": {"FieldId": "product"}},
            {"FieldTooltipItem": {"FieldId": "sales"}},
        ]

        # Call the function with basic parameters
        bar_chart_params = {
            "visual_id": "visual1",
            "dataset_id": "dataset1",
            "category_column_name": "product",
            "category_column_type": "Categorical",
            "value_column_names": ["sales"],
            "color_column_name": "",
            "sorting_variable": "sales",
            "sort_direction": "DESC",
            "numerical_aggregation": "SUM",
            "orientation": "VERTICAL",
            "bars_arrangement": "CLUSTERED",
            "date_granularity": "",
        }
        result = bar_chart.create_bar_chart(bar_chart_params)

        # Verify create_empty_bar_chart_visual was called correctly
        mock_create_empty_bar_chart_visual.assert_called_once_with("visual1")

        # Verify create_category was called correctly
        mock_create_category.assert_called_once_with("product", "dataset1", "Categorical", "")

        # Verify create_value was called correctly
        mock_create_value.assert_called_once_with("sales", "dataset1", "SUM")

        # Verify create_category_sort was called correctly
        mock_create_category_sort.assert_called_once_with("sales", "DESC")

        # Verify create_tool_tip_item was called correctly
        self.assertEqual(mock_create_tool_tip_item.call_count, 2)
        mock_create_tool_tip_item.assert_any_call("product")
        mock_create_tool_tip_item.assert_any_call("sales")

        # Verify the result structure
        self.assertEqual(result["BarChartVisual"]["VisualId"], "visual1")
        self.assertEqual(
            result["BarChartVisual"]["ChartConfiguration"]["FieldWells"][
                "BarChartAggregatedFieldWells"
            ]["Category"][0],
            mock_category,
        )
        self.assertEqual(
            result["BarChartVisual"]["ChartConfiguration"]["FieldWells"][
                "BarChartAggregatedFieldWells"
            ]["Values"][0],
            mock_value,
        )
        self.assertEqual(
            result["BarChartVisual"]["ChartConfiguration"]["SortConfiguration"]["CategorySort"][0],
            mock_category_sort,
        )
        self.assertEqual(
            result["BarChartVisual"]["ChartConfiguration"]["BarsArrangement"],
            "CLUSTERED",
        )
        self.assertEqual(
            len(
                result["BarChartVisual"]["ChartConfiguration"]["Tooltip"]["FieldBasedTooltip"][
                    "TooltipFields"
                ]
            ),
            2,
        )
        self.assertEqual(result["BarChartVisual"]["ChartConfiguration"]["Orientation"], "VERTICAL")

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.create_empty_bar_chart_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_category")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_column_hierarchy")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_value")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_category_sort")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_tool_tip_item")
    def test_create_bar_chart_date_category(
        self,
        mock_create_tool_tip_item,
        mock_create_category_sort,
        mock_create_value,
        mock_create_column_hierarchy,
        mock_create_category,
        mock_create_empty_bar_chart_visual,
    ):
        """Test create_bar_chart with Date category type."""
        # Setup mock responses
        mock_empty_chart = {
            "BarChartVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {
                        "BarChartAggregatedFieldWells": {"Category": [], "Values": [], "Colors": []}
                    },
                    "SortConfiguration": {"CategorySort": []},
                    "Tooltip": {"FieldBasedTooltip": {"TooltipFields": []}},
                    "Orientation": "VERTICAL",
                },
                "ColumnHierarchies": [],
            }
        }
        mock_create_empty_bar_chart_visual.return_value = mock_empty_chart

        mock_category = {"DateDimensionField": {"FieldId": "date"}}
        mock_create_category.return_value = mock_category

        mock_column_hierarchy = {"DateTimeHierarchy": {"HierarchyId": "date"}}
        mock_create_column_hierarchy.return_value = mock_column_hierarchy

        mock_value = {"NumericalMeasureField": {"FieldId": "sales"}}
        mock_create_value.return_value = mock_value

        mock_category_sort = {"FieldSort": {"FieldId": "date", "Direction": "ASC"}}
        mock_create_category_sort.return_value = mock_category_sort

        mock_create_tool_tip_item.side_effect = [
            {"FieldTooltipItem": {"FieldId": "date"}},
            {"FieldTooltipItem": {"FieldId": "sales"}},
        ]

        # Call the function with Date category type
        bar_chart_params = {
            "visual_id": "visual1",
            "dataset_id": "dataset1",
            "category_column_name": "date",
            "category_column_type": "Date",
            "value_column_names": ["sales"],
            "color_column_name": "",
            "sorting_variable": "date",
            "sort_direction": "ASC",
            "numerical_aggregation": "SUM",
            "orientation": "VERTICAL",
            "bars_arrangement": "CLUSTERED",
            "date_granularity": "",
        }
        result = bar_chart.create_bar_chart(bar_chart_params)

        # Verify create_category was called correctly
        mock_create_category.assert_called_once_with("date", "dataset1", "Date", "")

        # Verify create_column_hierarchy was called correctly
        mock_create_column_hierarchy.assert_called_once_with("date")

        # Verify the column hierarchy was added to the result
        self.assertEqual(result["BarChartVisual"]["ColumnHierarchies"][0], mock_column_hierarchy)

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.create_empty_bar_chart_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_category")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_value")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_color")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_category_sort")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_tool_tip_item")
    def test_create_bar_chart_with_color(
        self,
        mock_create_tool_tip_item,
        mock_create_category_sort,
        mock_create_color,
        mock_create_value,
        mock_create_category,
        mock_create_empty_bar_chart_visual,
    ):
        """Test create_bar_chart with color column."""
        # Setup mock responses
        mock_empty_chart = {
            "BarChartVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {
                        "BarChartAggregatedFieldWells": {"Category": [], "Values": [], "Colors": []}
                    },
                    "SortConfiguration": {"CategorySort": []},
                    "Tooltip": {"FieldBasedTooltip": {"TooltipFields": []}},
                    "Orientation": "VERTICAL",
                },
                "ColumnHierarchies": [],
            }
        }
        mock_create_empty_bar_chart_visual.return_value = mock_empty_chart

        mock_category = {"CategoricalDimensionField": {"FieldId": "product"}}
        mock_create_category.return_value = mock_category

        mock_value = {"NumericalMeasureField": {"FieldId": "sales"}}
        mock_create_value.return_value = mock_value

        mock_color = {"CategoricalDimensionField": {"FieldId": "region"}}
        mock_create_color.return_value = mock_color

        mock_category_sort = {"FieldSort": {"FieldId": "sales", "Direction": "DESC"}}
        mock_create_category_sort.return_value = mock_category_sort

        mock_create_tool_tip_item.side_effect = [
            {"FieldTooltipItem": {"FieldId": "product"}},
            {"FieldTooltipItem": {"FieldId": "sales"}},
            {"FieldTooltipItem": {"FieldId": "region"}},
        ]

        # Call the function with color column
        bar_chart_params = {
            "visual_id": "visual1",
            "dataset_id": "dataset1",
            "category_column_name": "product",
            "category_column_type": "Categorical",
            "value_column_names": ["sales"],
            "color_column_name": "region",
            "sorting_variable": "sales",
            "sort_direction": "DESC",
            "numerical_aggregation": "SUM",
            "orientation": "VERTICAL",
            "bars_arrangement": "CLUSTERED",
            "date_granularity": "",
        }
        result = bar_chart.create_bar_chart(bar_chart_params)

        # Verify create_color was called correctly
        mock_create_color.assert_called_once_with("region", "dataset1")

        # Verify the color was added to the result
        self.assertEqual(
            result["BarChartVisual"]["ChartConfiguration"]["FieldWells"][
                "BarChartAggregatedFieldWells"
            ]["Colors"][0],
            mock_color,
        )

        # Verify create_tool_tip_item was called for color
        mock_create_tool_tip_item.assert_any_call("region")

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.create_empty_bar_chart_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_category")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_value")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_category_sort")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_tool_tip_item")
    def test_create_bar_chart_multiple_values(
        self,
        mock_create_tool_tip_item,
        mock_create_category_sort,
        mock_create_value,
        mock_create_category,
        mock_create_empty_bar_chart_visual,
    ):
        """Test create_bar_chart with multiple value columns."""
        # Setup mock responses
        mock_empty_chart = {
            "BarChartVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {
                        "BarChartAggregatedFieldWells": {"Category": [], "Values": [], "Colors": []}
                    },
                    "SortConfiguration": {"CategorySort": []},
                    "Tooltip": {"FieldBasedTooltip": {"TooltipFields": []}},
                    "Orientation": "VERTICAL",
                },
                "ColumnHierarchies": [],
            }
        }
        mock_create_empty_bar_chart_visual.return_value = mock_empty_chart

        mock_category = {"CategoricalDimensionField": {"FieldId": "product"}}
        mock_create_category.return_value = mock_category

        mock_create_value.side_effect = [
            {"NumericalMeasureField": {"FieldId": "sales"}},
            {"NumericalMeasureField": {"FieldId": "profit"}},
            {"NumericalMeasureField": {"FieldId": "quantity"}},
        ]

        mock_category_sort = {"FieldSort": {"FieldId": "sales", "Direction": "DESC"}}
        mock_create_category_sort.return_value = mock_category_sort

        mock_create_tool_tip_item.side_effect = [
            {"FieldTooltipItem": {"FieldId": "product"}},
            {"FieldTooltipItem": {"FieldId": "sales"}},
            {"FieldTooltipItem": {"FieldId": "profit"}},
            {"FieldTooltipItem": {"FieldId": "quantity"}},
        ]

        # Call the function with multiple value columns
        bar_chart_params = {
            "visual_id": "visual1",
            "dataset_id": "dataset1",
            "category_column_name": "product",
            "category_column_type": "Categorical",
            "value_column_names": ["sales", "profit", "quantity"],
            "color_column_name": "",
            "sorting_variable": "sales",
            "sort_direction": "DESC",
            "numerical_aggregation": "SUM",
            "orientation": "VERTICAL",
            "bars_arrangement": "CLUSTERED",
            "date_granularity": "",
        }
        result = bar_chart.create_bar_chart(bar_chart_params)

        # Verify create_value was called for each value column
        self.assertEqual(mock_create_value.call_count, 3)
        mock_create_value.assert_any_call("sales", "dataset1", "SUM")
        mock_create_value.assert_any_call("profit", "dataset1", "SUM")
        mock_create_value.assert_any_call("quantity", "dataset1", "SUM")

        # Verify create_tool_tip_item was called for each value column
        self.assertEqual(mock_create_tool_tip_item.call_count, 4)
        mock_create_tool_tip_item.assert_any_call("product")
        mock_create_tool_tip_item.assert_any_call("sales")
        mock_create_tool_tip_item.assert_any_call("profit")
        mock_create_tool_tip_item.assert_any_call("quantity")

        # Verify the values were added to the result
        self.assertEqual(
            len(
                result["BarChartVisual"]["ChartConfiguration"]["FieldWells"][
                    "BarChartAggregatedFieldWells"
                ]["Values"]
            ),
            3,
        )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.create_empty_bar_chart_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_category")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_value")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_category_sort")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_tool_tip_item")
    def test_create_bar_chart_horizontal_orientation(
        self,
        mock_create_tool_tip_item,
        mock_create_category_sort,
        mock_create_value,
        mock_create_category,
        mock_create_empty_bar_chart_visual,
    ):
        """Test create_bar_chart with horizontal orientation."""
        # Setup mock responses
        mock_empty_chart = {
            "BarChartVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {
                        "BarChartAggregatedFieldWells": {"Category": [], "Values": [], "Colors": []}
                    },
                    "SortConfiguration": {"CategorySort": []},
                    "Tooltip": {"FieldBasedTooltip": {"TooltipFields": []}},
                    "Orientation": "VERTICAL",  # Default orientation in the empty chart
                },
                "ColumnHierarchies": [],
            }
        }
        mock_create_empty_bar_chart_visual.return_value = mock_empty_chart

        mock_category = {"CategoricalDimensionField": {"FieldId": "product"}}
        mock_create_category.return_value = mock_category

        mock_value = {"NumericalMeasureField": {"FieldId": "sales"}}
        mock_create_value.return_value = mock_value

        mock_category_sort = {"FieldSort": {"FieldId": "sales", "Direction": "DESC"}}
        mock_create_category_sort.return_value = mock_category_sort

        mock_create_tool_tip_item.side_effect = [
            {"FieldTooltipItem": {"FieldId": "product"}},
            {"FieldTooltipItem": {"FieldId": "sales"}},
        ]

        # Call the function with horizontal orientation
        bar_chart_params = {
            "visual_id": "visual1",
            "dataset_id": "dataset1",
            "category_column_name": "product",
            "category_column_type": "Categorical",
            "value_column_names": ["sales"],
            "color_column_name": "",
            "sorting_variable": "sales",
            "sort_direction": "DESC",
            "numerical_aggregation": "SUM",
            "orientation": "HORIZONTAL",
            "bars_arrangement": "CLUSTERED",
            "date_granularity": "",
        }
        result = bar_chart.create_bar_chart(bar_chart_params)

        # Verify the orientation was set correctly
        self.assertEqual(
            result["BarChartVisual"]["ChartConfiguration"]["Orientation"], "HORIZONTAL"
        )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.create_empty_bar_chart_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_category")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_value")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_category_sort")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart.chart_config.create_tool_tip_item")
    def test_create_bar_chart_different_aggregation(
        self,
        mock_create_tool_tip_item,
        mock_create_category_sort,
        mock_create_value,
        mock_create_category,
        mock_create_empty_bar_chart_visual,
    ):
        """Test create_bar_chart with different numerical aggregation."""
        # Setup mock responses
        mock_empty_chart = {
            "BarChartVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {
                        "BarChartAggregatedFieldWells": {"Category": [], "Values": [], "Colors": []}
                    },
                    "SortConfiguration": {"CategorySort": []},
                    "Tooltip": {"FieldBasedTooltip": {"TooltipFields": []}},
                    "Orientation": "VERTICAL",
                },
                "ColumnHierarchies": [],
            }
        }
        mock_create_empty_bar_chart_visual.return_value = mock_empty_chart

        mock_category = {"CategoricalDimensionField": {"FieldId": "product"}}
        mock_create_category.return_value = mock_category

        mock_value = {
            "NumericalMeasureField": {
                "FieldId": "sales",
                "AggregationFunction": {"SimpleNumericalAggregation": "AVERAGE"},
            }
        }
        mock_create_value.return_value = mock_value

        mock_category_sort = {"FieldSort": {"FieldId": "sales", "Direction": "DESC"}}
        mock_create_category_sort.return_value = mock_category_sort

        mock_create_tool_tip_item.side_effect = [
            {"FieldTooltipItem": {"FieldId": "product"}},
            {"FieldTooltipItem": {"FieldId": "sales"}},
        ]

        # Call the function with AVERAGE aggregation
        bar_chart_params = {
            "visual_id": "visual1",
            "dataset_id": "dataset1",
            "category_column_name": "product",
            "category_column_type": "Categorical",
            "value_column_names": ["sales"],
            "color_column_name": "",
            "sorting_variable": "sales",
            "sort_direction": "DESC",
            "numerical_aggregation": "AVERAGE",
            "orientation": "VERTICAL",
            "bars_arrangement": "CLUSTERED",
            "date_granularity": "",
        }
        bar_chart.create_bar_chart(bar_chart_params)

        # Verify create_value was called with the correct aggregation
        mock_create_value.assert_called_once_with("sales", "dataset1", "AVERAGE")

    def test_create_bar_chart_none_parameters(self):
        """Test create_bar_chart with None parameters (should raise AssertionError)."""
        # Verify that passing None as bar_chart_parameters raises an AssertionError
        with pytest.raises(AssertionError, match="bar_chart_parameters cannot be None"):
            bar_chart.create_bar_chart(None)
