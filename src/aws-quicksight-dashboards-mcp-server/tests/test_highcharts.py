from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import mock_open, patch

import pytest

import sys
from pathlib import Path

qs_mcp_directory = Path(__file__).parent.parent
sys.path.append(str(qs_mcp_directory))
print(qs_mcp_directory)

import awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart as highchart
import awslabs.aws_quicksight_dashboards_mcp_server.quicksight as qs


class TestCreateEmptyHighchartVisual(TestCase):
    """Test cases for create_empty_highchart_visual function."""

    @patch("builtins.open", new_callable=mock_open, read_data='{"PluginVisual": {"VisualId": ""}}')
    @patch("json.load")
    def test_create_empty_highchart_visual_success(self, mock_json_load, mock_file):
        """Test create_empty_highchart_visual with a valid visual_id."""
        # Setup mock response for json.load
        mock_highchart_visual = {"PluginVisual": {"VisualId": ""}}
        mock_json_load.return_value = mock_highchart_visual

        # Call the function
        result = highchart.create_empty_highchart_visual("visual1")

        # Verify open was called with the correct path
        self.assertEqual(mock_file.call_count, 1)
        call_args = mock_file.call_args[0]
        self.assertEqual(len(call_args), 2)
        self.assertTrue(call_args[0].endswith("json_definitions/highchart_definition.json"))
        self.assertEqual(call_args[1], "r")

        # Verify json.load was called correctly
        mock_json_load.assert_called_once()

        # Verify the visual_id was set correctly
        self.assertEqual(result["PluginVisual"]["VisualId"], "visual1")

    def test_create_empty_highchart_visual_none_visual_id(self):
        """Test create_empty_highchart_visual with None as visual_id (should raise AssertionError)."""
        # Verify that passing None as visual_id raises an AssertionError
        with self.assertRaises(AssertionError) as context:
            highchart.create_empty_highchart_visual(None)

        # Verify the exception message
        self.assertEqual(str(context.exception), "visual cannot be None")

    @patch("builtins.open")
    def test_create_empty_highchart_visual_file_error(self, mock_open):
        """Test create_empty_highchart_visual when there's an error opening the JSON file."""
        # Setup mock to raise an exception
        mock_open.side_effect = FileNotFoundError("File not found")

        # Verify the exception is propagated
        with self.assertRaises(FileNotFoundError) as context:
            highchart.create_empty_highchart_visual("visual1")

        # Verify the exception message
        self.assertEqual(str(context.exception), "File not found")


class TestCreateHighchartVisual(TestCase):
    """Test cases for create_highchart_visual function."""

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.create_empty_highchart_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.chart_config.create_category")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.chart_config.create_value")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.chart_config.create_highchart_date")
    def test_create_highchart_visual_basic(
        self,
        mock_create_highchart_date,
        mock_create_value,
        mock_create_category,
        mock_create_empty_highchart_visual,
    ):
        """Test create_highchart_visual with basic parameters."""
        # Setup mock responses
        mock_empty_highchart = {
            "PluginVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": [
                        {"Dimensions": []},
                        {"Measures": []},
                    ],
                    "VisualOptions": {"VisualProperties": [{"Value": {}}]},
                },
            }
        }
        mock_create_empty_highchart_visual.return_value = mock_empty_highchart

        mock_category = {"CategoricalDimensionField": {"FieldId": "product"}}
        mock_create_category.return_value = mock_category

        mock_value = {"NumericalMeasureField": {"FieldId": "sales"}}
        mock_create_value.return_value = mock_value

        # Call the function with basic parameters
        highchart_params = {
            "visual_id": "visual1",
            "dataset_id": "dataset1",
            "category_column_names": ["product"],
            "date_column_names": [],
            "date_granularity": "",
            "value_column_names": ["sales"],
            "value_column_aggregation": ["SUM"],
            "highchart_code": '{"chart":{"type":"line"}}',
        }
        result = highchart.create_highchart_visual(highchart_params)

        # Verify create_empty_highchart_visual was called correctly
        mock_create_empty_highchart_visual.assert_called_once_with("visual1")

        # Verify create_category was called correctly
        mock_create_category.assert_called_once_with(
            column_name="product",
            dataset_id="dataset1",
            column_type="Categorical",
            date_granularity="",
        )

        # Verify create_value was called correctly
        mock_create_value.assert_called_once_with(
            column_name="sales", dataset_id="dataset1", numerical_aggregation="SUM"
        )

        # Verify create_highchart_date was not called
        mock_create_highchart_date.assert_not_called()

        # Verify the result structure
        self.assertEqual(result["PluginVisual"]["VisualId"], "visual1")
        self.assertEqual(
            len(result["PluginVisual"]["ChartConfiguration"]["FieldWells"][0]["Dimensions"]), 1
        )
        self.assertEqual(
            result["PluginVisual"]["ChartConfiguration"]["FieldWells"][0]["Dimensions"][0],
            mock_category,
        )
        self.assertEqual(
            len(result["PluginVisual"]["ChartConfiguration"]["FieldWells"][1]["Measures"]), 1
        )
        self.assertEqual(
            result["PluginVisual"]["ChartConfiguration"]["FieldWells"][1]["Measures"][0], mock_value
        )
        self.assertEqual(
            result["PluginVisual"]["ChartConfiguration"]["VisualOptions"]["VisualProperties"][0][
                "Value"
            ],
            {"chart": {"type": "line"}},
        )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.create_empty_highchart_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.chart_config.create_category")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.chart_config.create_value")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.chart_config.create_highchart_date")
    def test_create_highchart_visual_with_date(
        self,
        mock_create_highchart_date,
        mock_create_value,
        mock_create_category,
        mock_create_empty_highchart_visual,
    ):
        """Test create_highchart_visual with date columns."""
        # Setup mock responses
        mock_empty_highchart = {
            "PluginVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": [
                        {"Dimensions": []},
                        {"Measures": []},
                    ],
                    "VisualOptions": {"VisualProperties": [{"Value": {}}]},
                },
            }
        }
        mock_create_empty_highchart_visual.return_value = mock_empty_highchart

        mock_date = {"DateDimensionField": {"FieldId": "date"}}
        mock_create_highchart_date.return_value = mock_date

        mock_value = {"NumericalMeasureField": {"FieldId": "sales"}}
        mock_create_value.return_value = mock_value

        # Call the function with date columns
        highchart_params = {
            "visual_id": "visual1",
            "dataset_id": "dataset1",
            "category_column_names": [],
            "date_column_names": ["date"],
            "date_granularity": "MONTH",
            "value_column_names": ["sales"],
            "value_column_aggregation": ["SUM"],
            "highchart_code": '{"chart":{"type":"line"}}',
        }
        result = highchart.create_highchart_visual(highchart_params)

        # Verify create_highchart_date was called correctly
        mock_create_highchart_date.assert_called_once_with(
            column_name="date", dataset_id="dataset1", date_granularity="MONTH"
        )

        # Verify create_category was not called
        mock_create_category.assert_not_called()

        # Verify the result structure
        self.assertEqual(
            len(result["PluginVisual"]["ChartConfiguration"]["FieldWells"][0]["Dimensions"]), 1
        )
        self.assertEqual(
            result["PluginVisual"]["ChartConfiguration"]["FieldWells"][0]["Dimensions"][0],
            mock_date,
        )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.create_empty_highchart_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.chart_config.create_category")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.chart_config.create_value")
    def test_create_highchart_visual_multiple_values(
        self, mock_create_value, mock_create_category, mock_create_empty_highchart_visual
    ):
        """Test create_highchart_visual with multiple value columns."""
        # Setup mock responses
        mock_empty_highchart = {
            "PluginVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": [
                        {"Dimensions": []},
                        {"Measures": []},
                    ],
                    "VisualOptions": {"VisualProperties": [{"Value": {}}]},
                },
            }
        }
        mock_create_empty_highchart_visual.return_value = mock_empty_highchart

        mock_category = {"CategoricalDimensionField": {"FieldId": "product"}}
        mock_create_category.return_value = mock_category

        mock_create_value.side_effect = [
            {"NumericalMeasureField": {"FieldId": "sales"}},
            {"NumericalMeasureField": {"FieldId": "profit"}},
        ]

        # Call the function with multiple value columns
        highchart_params = {
            "visual_id": "visual1",
            "dataset_id": "dataset1",
            "category_column_names": ["product"],
            "date_column_names": [],
            "date_granularity": "",
            "value_column_names": ["sales", "profit"],
            "value_column_aggregation": ["SUM", "AVERAGE"],
            "highchart_code": '{"chart":{"type":"line"}}',
        }
        result = highchart.create_highchart_visual(highchart_params)

        # Verify create_value was called for each value column with correct aggregation
        self.assertEqual(mock_create_value.call_count, 2)
        mock_create_value.assert_any_call(
            column_name="sales", dataset_id="dataset1", numerical_aggregation="SUM"
        )
        mock_create_value.assert_any_call(
            column_name="profit", dataset_id="dataset1", numerical_aggregation="AVERAGE"
        )

        # Verify the result structure
        self.assertEqual(
            len(result["PluginVisual"]["ChartConfiguration"]["FieldWells"][1]["Measures"]), 2
        )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.create_empty_highchart_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.chart_config.create_category")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.chart_config.create_value")
    def test_create_highchart_visual_multiple_categories(
        self, mock_create_value, mock_create_category, mock_create_empty_highchart_visual
    ):
        """Test create_highchart_visual with multiple category columns."""
        # Setup mock responses
        mock_empty_highchart = {
            "PluginVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": [
                        {"Dimensions": []},
                        {"Measures": []},
                    ],
                    "VisualOptions": {"VisualProperties": [{"Value": {}}]},
                },
            }
        }
        mock_create_empty_highchart_visual.return_value = mock_empty_highchart

        mock_create_category.side_effect = [
            {"CategoricalDimensionField": {"FieldId": "product"}},
            {"CategoricalDimensionField": {"FieldId": "region"}},
        ]

        mock_value = {"NumericalMeasureField": {"FieldId": "sales"}}
        mock_create_value.return_value = mock_value

        # Call the function with multiple category columns
        highchart_params = {
            "visual_id": "visual1",
            "dataset_id": "dataset1",
            "category_column_names": ["product", "region"],
            "date_column_names": [],
            "date_granularity": "",
            "value_column_names": ["sales"],
            "value_column_aggregation": ["SUM"],
            "highchart_code": '{"chart":{"type":"line"}}',
        }
        result = highchart.create_highchart_visual(highchart_params)

        # Verify create_category was called for each category column
        self.assertEqual(mock_create_category.call_count, 2)
        mock_create_category.assert_any_call(
            column_name="product",
            dataset_id="dataset1",
            column_type="Categorical",
            date_granularity="",
        )
        mock_create_category.assert_any_call(
            column_name="region",
            dataset_id="dataset1",
            column_type="Categorical",
            date_granularity="",
        )

        # Verify the result structure
        self.assertEqual(
            len(result["PluginVisual"]["ChartConfiguration"]["FieldWells"][0]["Dimensions"]), 2
        )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.create_empty_highchart_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.chart_config.create_category")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.chart_config.create_value")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.chart_config.create_highchart_date")
    def test_create_highchart_visual_complex_code(
        self,
        mock_create_highchart_date,
        mock_create_value,
        mock_create_category,
        mock_create_empty_highchart_visual,
    ):
        """Test create_highchart_visual with complex highchart code."""
        # Setup mock responses
        mock_empty_highchart = {
            "PluginVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": [
                        {"Dimensions": []},
                        {"Measures": []},
                    ],
                    "VisualOptions": {"VisualProperties": [{"Value": {}}]},
                },
            }
        }
        mock_create_empty_highchart_visual.return_value = mock_empty_highchart

        mock_category = {"CategoricalDimensionField": {"FieldId": "product"}}
        mock_create_category.return_value = mock_category

        mock_value = {"NumericalMeasureField": {"FieldId": "sales"}}
        mock_create_value.return_value = mock_value

        # Complex highchart code with column arithmetic
        complex_code = '{"chart":{"type":"packedbubble"},"series":[{"name":"Sales","data":["map",["getColumnFromGroupBy",0],{"name":["item"],"value":["get",["getColumnFromValue",0],["itemIndex"]]}]}]}'

        # Call the function with complex highchart code
        highchart_params = {
            "visual_id": "visual1",
            "dataset_id": "dataset1",
            "category_column_names": ["product"],
            "date_column_names": [],
            "date_granularity": "",
            "value_column_names": ["sales"],
            "value_column_aggregation": ["SUM"],
            "highchart_code": complex_code,
        }
        result = highchart.create_highchart_visual(highchart_params)

        # Verify the highchart code was properly parsed and set
        expected_code = {
            "chart": {"type": "packedbubble"},
            "series": [
                {
                    "name": "Sales",
                    "data": [
                        "map",
                        ["getColumnFromGroupBy", 0],
                        {
                            "name": ["item"],
                            "value": ["get", ["getColumnFromValue", 0], ["itemIndex"]],
                        },
                    ],
                }
            ],
        }
        self.assertEqual(
            result["PluginVisual"]["ChartConfiguration"]["VisualOptions"]["VisualProperties"][0][
                "Value"
            ],
            expected_code,
        )

    def test_create_highchart_visual_none_parameters(self):
        """Test create_highchart_visual with None parameters (should raise AssertionError)."""
        # Verify that passing None as highchart_parameters raises an AssertionError
        with pytest.raises(AssertionError, match="highchart_parameters cannot be None"):
            highchart.create_highchart_visual(None)


class TestMyUpdateDashboardAddHighchart(IsolatedAsyncioTestCase):
    """Test cases for my_update_dashboard_add_highchart function."""

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.qs.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.qs.update_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.create_highchart_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.qs.get_dash_version")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.qs.my_update_dashboard_publish")
    async def test_update_dashboard_add_highchart_success(
        self,
        mock_publish,
        mock_get_dash_version,
        mock_create_highchart_visual,
        mock_update_visual,
        mock_get_current_visuals,
        mock_client,
    ):
        """Test my_update_dashboard_add_highchart with valid parameters."""
        # Setup mock visuals
        mock_visuals = [
            {"LineChartVisual": {"VisualId": "visual1", "Title": {"Visibility": "VISIBLE"}}},
        ]
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock highchart visual
        mock_highchart = {
            "PluginVisual": {
                "VisualId": "visual2",
                "ChartConfiguration": {
                    "FieldWells": [
                        {"Dimensions": []},
                        {"Measures": []},
                    ],
                    "VisualOptions": {"VisualProperties": [{"Value": {"chart": {"type": "line"}}}]},
                },
            }
        }
        mock_create_highchart_visual.return_value = mock_highchart

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
                        mock_highchart,
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

        # Setup mock version
        mock_get_dash_version.return_value = 2

        # Setup mock publish response
        mock_publish.return_value = {"Status": 200}

        # Call the function
        result = await highchart.my_update_dashboard_add_highchart(
            dash_id="dashboard1",
            dash_name="Dashboard 1",
            sheet_id="sheet1",
            visual_id="visual2",
            dataset_id="dataset1",
            category_column_names=["product"],
            date_column_names=[],
            date_granularity="",
            value_column_names=["sales"],
            value_column_aggregation=["SUM"],
            highchart_code='{"chart":{"type":"line"}}',
        )

        # Verify get_current_visuals was called correctly
        mock_get_current_visuals.assert_called_once_with("dashboard1", "sheet1")

        # Verify create_highchart_visual was called with the correct parameters
        expected_highchart_params = {
            "visual_id": "visual2",
            "dataset_id": "dataset1",
            "category_column_names": ["product"],
            "date_column_names": [],
            "date_granularity": "",
            "value_column_names": ["sales"],
            "value_column_aggregation": ["SUM"],
            "highchart_code": '{"chart":{"type":"line"}}',
        }
        mock_create_highchart_visual.assert_called_once_with(expected_highchart_params)

        # Verify update_visual was called with the updated visuals
        expected_visuals = [
            {"LineChartVisual": {"VisualId": "visual1", "Title": {"Visibility": "VISIBLE"}}},
            mock_highchart,
        ]
        mock_update_visual.assert_called_once_with("dashboard1", "sheet1", expected_visuals)

        # Verify client.update_dashboard was called correctly
        mock_client.update_dashboard.assert_called_once_with(
            AwsAccountId=qs.ACCOUNT_ID,
            DashboardId="dashboard1",
            Name="Dashboard 1",
            Definition=mock_updated_definition,
        )

        # Verify get_dash_version was called correctly
        mock_get_dash_version.assert_called_once_with(mock_response)

        # Verify my_update_dashboard_publish was called correctly
        mock_publish.assert_called_once_with("dashboard1", 2)

        # Verify the result
        self.assertEqual(result, mock_response)

    async def test_update_dashboard_add_highchart_none_dash_id(self):
        """Test my_update_dashboard_add_highchart with None as dash_id (should raise AssertionError)."""
        # Verify that passing None as dash_id raises an AssertionError
        with pytest.raises(AssertionError, match="dash_id cannot be None"):
            await highchart.my_update_dashboard_add_highchart(
                dash_id=None,
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                category_column_names=["product"],
                date_column_names=[],
                date_granularity="",
                value_column_names=["sales"],
                value_column_aggregation=["SUM"],
                highchart_code='{"chart":{"type":"line"}}',
            )

    async def test_update_dashboard_add_highchart_none_dash_name(self):
        """Test my_update_dashboard_add_highchart with None as dash_name (should raise AssertionError)."""
        # Verify that passing None as dash_name raises an AssertionError
        with pytest.raises(AssertionError, match="dash_name cannot be None"):
            await highchart.my_update_dashboard_add_highchart(
                dash_id="dashboard1",
                dash_name=None,
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                category_column_names=["product"],
                date_column_names=[],
                date_granularity="",
                value_column_names=["sales"],
                value_column_aggregation=["SUM"],
                highchart_code='{"chart":{"type":"line"}}',
            )

    async def test_update_dashboard_add_highchart_none_sheet_id(self):
        """Test my_update_dashboard_add_highchart with None as sheet_id (should raise AssertionError)."""
        # Verify that passing None as sheet_id raises an AssertionError
        with pytest.raises(AssertionError, match="sheet_id cannot be None"):
            await highchart.my_update_dashboard_add_highchart(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id=None,
                visual_id="visual1",
                dataset_id="dataset1",
                category_column_names=["product"],
                date_column_names=[],
                date_granularity="",
                value_column_names=["sales"],
                value_column_aggregation=["SUM"],
                highchart_code='{"chart":{"type":"line"}}',
            )

    async def test_update_dashboard_add_highchart_none_visual_id(self):
        """Test my_update_dashboard_add_highchart with None as visual_id (should raise AssertionError)."""
        # Verify that passing None as visual_id raises an AssertionError
        with pytest.raises(AssertionError, match="visual_id cannot be None"):
            await highchart.my_update_dashboard_add_highchart(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id=None,
                dataset_id="dataset1",
                category_column_names=["product"],
                date_column_names=[],
                date_granularity="",
                value_column_names=["sales"],
                value_column_aggregation=["SUM"],
                highchart_code='{"chart":{"type":"line"}}',
            )

    async def test_update_dashboard_add_highchart_none_dataset_id(self):
        """Test my_update_dashboard_add_highchart with None as dataset_id (should raise AssertionError)."""
        # Verify that passing None as dataset_id raises an AssertionError
        with pytest.raises(AssertionError, match="dataset_id cannot be None"):
            await highchart.my_update_dashboard_add_highchart(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id=None,
                category_column_names=["product"],
                date_column_names=[],
                date_granularity="",
                value_column_names=["sales"],
                value_column_aggregation=["SUM"],
                highchart_code='{"chart":{"type":"line"}}',
            )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.create_highchart_visual")
    async def test_update_dashboard_add_highchart_create_error(
        self, mock_create_highchart_visual, mock_get_current_visuals
    ):
        """Test my_update_dashboard_add_highchart when create_highchart_visual raises an exception."""
        # Setup mock visuals
        mock_visuals = []
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock to raise an exception
        mock_create_highchart_visual.side_effect = Exception("Create Error")

        # Verify the exception is propagated
        with self.assertRaises(Exception) as context:
            await highchart.my_update_dashboard_add_highchart(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                category_column_names=["product"],
                date_column_names=[],
                date_granularity="",
                value_column_names=["sales"],
                value_column_aggregation=["SUM"],
                highchart_code='{"chart":{"type":"line"}}',
            )

        # Verify the exception message
        self.assertEqual(str(context.exception), "Create Error")

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.create_highchart_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.qs.update_visual")
    async def test_update_dashboard_add_highchart_update_error(
        self, mock_update_visual, mock_create_highchart_visual, mock_get_current_visuals
    ):
        """Test my_update_dashboard_add_highchart when update_visual raises an exception."""
        # Setup mock visuals
        mock_visuals = []
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock highchart visual
        mock_highchart = {
            "PluginVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": [
                        {"Dimensions": []},
                        {"Measures": []},
                    ],
                    "VisualOptions": {"VisualProperties": [{"Value": {"chart": {"type": "line"}}}]},
                },
            }
        }
        mock_create_highchart_visual.return_value = mock_highchart

        # Setup mock to raise an exception
        mock_update_visual.side_effect = Exception("Update Error")

        # Verify the exception is propagated
        with self.assertRaises(Exception) as context:
            await highchart.my_update_dashboard_add_highchart(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                category_column_names=["product"],
                date_column_names=[],
                date_granularity="",
                value_column_names=["sales"],
                value_column_aggregation=["SUM"],
                highchart_code='{"chart":{"type":"line"}}',
            )

        # Verify the exception message
        self.assertEqual(str(context.exception), "Update Error")

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart.qs.get_current_visuals")
    async def test_update_dashboard_add_highchart_none_visuals(self, mock_get_current_visuals):
        """Test my_update_dashboard_add_highchart when get_current_visuals returns None."""
        # Setup mock to return None (sheet not found)
        mock_get_current_visuals.return_value = None

        # Verify the function raises an exception when visuals is None
        with self.assertRaises(Exception):
            await highchart.my_update_dashboard_add_highchart(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                category_column_names=["product"],
                date_column_names=[],
                date_granularity="",
                value_column_names=["sales"],
                value_column_aggregation=["SUM"],
                highchart_code='{"chart":{"type":"line"}}',
            )
