from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import mock_open, patch

import pytest

import sys
from pathlib import Path

qs_mcp_directory = Path(__file__).parent.parent
sys.path.append(str(qs_mcp_directory))
print(qs_mcp_directory)

import awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi as kpi
import awslabs.aws_quicksight_dashboards_mcp_server.quicksight as qs


class TestCreateEmptyKpiVisual(TestCase):
    """Test cases for create_empty_kpi_visual function."""

    @patch("builtins.open", new_callable=mock_open, read_data='{"KPIVisual": {"VisualId": ""}}')
    @patch("json.load")
    def test_create_empty_kpi_visual_success(self, mock_json_load, mock_file):
        """Test create_empty_kpi_visual with a valid visual_id."""
        # Setup mock response for json.load
        mock_kpi_visual = {"KPIVisual": {"VisualId": ""}}
        mock_json_load.return_value = mock_kpi_visual

        # Call the function
        result = kpi.create_empty_kpi_visual("visual1")

        # Verify open was called with the correct path
        self.assertEqual(mock_file.call_count, 1)
        call_args = mock_file.call_args[0]
        self.assertEqual(len(call_args), 2)
        self.assertTrue(call_args[0].endswith("json_definitions/kpi_definition.json"))
        self.assertEqual(call_args[1], "r")

        # Verify json.load was called correctly
        mock_json_load.assert_called_once()

        # Verify the visual_id was set correctly
        self.assertEqual(result["KPIVisual"]["VisualId"], "visual1")

    def test_create_empty_kpi_visual_none_visual_id(self):
        """Test create_empty_kpi_visual with None as visual_id (should raise AssertionError)."""
        # Verify that passing None as visual_id raises an AssertionError
        with self.assertRaises(AssertionError) as context:
            kpi.create_empty_kpi_visual(None)

        # Verify the exception message
        self.assertEqual(str(context.exception), "visual cannot be None")

    @patch("builtins.open")
    def test_create_empty_kpi_visual_file_error(self, mock_open):
        """Test create_empty_kpi_visual when there's an error opening the JSON file."""
        # Setup mock to raise an exception
        mock_open.side_effect = FileNotFoundError("File not found")

        # Verify the exception is propagated
        with self.assertRaises(FileNotFoundError) as context:
            kpi.create_empty_kpi_visual("visual1")

        # Verify the exception message
        self.assertEqual(str(context.exception), "File not found")


class TestCreateKpiVisual(TestCase):
    """Test cases for create_kpi_visual function."""

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.create_empty_kpi_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.chart_config.create_value")
    def test_create_kpi_visual_basic(self, mock_create_value, mock_create_empty_kpi_visual):
        """Test create_kpi_visual with basic parameters (single value KPI)."""
        # Setup mock responses
        mock_empty_kpi = {
            "KPIVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {"Values": [], "TargetValues": [], "TrendGroups": []},
                    "SortConfiguration": {},
                    "KPIOptions": {},
                },
                "ConditionalFormatting": {
                    "ConditionalFormattingOptions": [
                        {"ComparisonValue": {"TextColor": {"Solid": {"Expression": ""}}}},
                        {"ComparisonValue": {"TextColor": {"Solid": {"Expression": ""}}}},
                        {"ComparisonValue": {"Icon": {"CustomCondition": {"Expression": ""}}}},
                        {"ComparisonValue": {"Icon": {"CustomCondition": {"Expression": ""}}}},
                    ]
                },
                "ColumnHierarchies": [],
            }
        }
        mock_create_empty_kpi_visual.return_value = mock_empty_kpi

        mock_value = {"NumericalMeasureField": {"FieldId": "sales"}}
        mock_create_value.return_value = mock_value

        # Call the function with basic parameters (single value KPI)
        kpi_parameters = {
            "visual_id": "visual1",
            "dataset_id": "dataset1",
            "value_column_name": "sales",
            "target_column_name": "",
            "trend_column_name": "",
            "trend_is_date": False,
            "date_granularity": "",
            "agg_function": "SUM",
            "visual_type": "",
        }
        result = kpi.create_kpi_visual(kpi_parameters)

        # Verify create_empty_kpi_visual was called correctly
        mock_create_empty_kpi_visual.assert_called_once_with("visual1")

        # Verify create_value was called correctly
        mock_create_value.assert_called_once_with(
            column_name="sales", dataset_id="dataset1", numerical_aggregation="SUM"
        )

        # Verify the result structure
        self.assertEqual(result["KPIVisual"]["VisualId"], "visual1")
        self.assertEqual(
            result["KPIVisual"]["ChartConfiguration"]["FieldWells"]["Values"][0], mock_value
        )
        self.assertEqual(
            len(result["KPIVisual"]["ChartConfiguration"]["FieldWells"]["TargetValues"]), 0
        )
        self.assertEqual(
            len(result["KPIVisual"]["ChartConfiguration"]["FieldWells"]["TrendGroups"]), 0
        )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.create_empty_kpi_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.chart_config.create_value")
    def test_create_kpi_visual_with_target(self, mock_create_value, mock_create_empty_kpi_visual):
        """Test create_kpi_visual with target value (target comparison KPI)."""
        # Setup mock responses
        mock_empty_kpi = {
            "KPIVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {"Values": [], "TargetValues": [], "TrendGroups": []},
                    "SortConfiguration": {},
                    "KPIOptions": {},
                },
                "ConditionalFormatting": {
                    "ConditionalFormattingOptions": [
                        {"ComparisonValue": {"TextColor": {"Solid": {"Expression": ""}}}},
                        {"ComparisonValue": {"TextColor": {"Solid": {"Expression": ""}}}},
                        {"ComparisonValue": {"Icon": {"CustomCondition": {"Expression": ""}}}},
                        {"ComparisonValue": {"Icon": {"CustomCondition": {"Expression": ""}}}},
                    ]
                },
                "ColumnHierarchies": [],
            }
        }
        mock_create_empty_kpi_visual.return_value = mock_empty_kpi

        mock_create_value.side_effect = [
            {"NumericalMeasureField": {"FieldId": "sales"}},
            {"NumericalMeasureField": {"FieldId": "target"}},
        ]

        # Call the function with target value parameters
        kpi_parameters = {
            "visual_id": "visual1",
            "dataset_id": "dataset1",
            "value_column_name": "sales",
            "target_column_name": "target",
            "trend_column_name": "",
            "trend_is_date": False,
            "date_granularity": "",
            "agg_function": "SUM",
            "visual_type": "progress_bar",
        }
        result = kpi.create_kpi_visual(kpi_parameters)

        # Verify create_value was called correctly for both value and target
        self.assertEqual(mock_create_value.call_count, 2)
        mock_create_value.assert_any_call(
            column_name="sales", dataset_id="dataset1", numerical_aggregation="SUM"
        )
        mock_create_value.assert_any_call(
            column_name="target", dataset_id="dataset1", numerical_aggregation="SUM"
        )

        # Verify the result structure
        self.assertEqual(
            len(result["KPIVisual"]["ChartConfiguration"]["FieldWells"]["TargetValues"]), 1
        )
        self.assertEqual(
            "ProgressBar" in result["KPIVisual"]["ChartConfiguration"]["KPIOptions"], True
        )
        self.assertEqual(
            result["KPIVisual"]["ChartConfiguration"]["KPIOptions"]["ProgressBar"]["Visibility"],
            "VISIBLE",
        )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.create_empty_kpi_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.chart_config.create_value")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.chart_config.create_category")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.chart_config.create_category_sort")
    def test_create_kpi_visual_with_trend_categorical(
        self,
        mock_create_category_sort,
        mock_create_category,
        mock_create_value,
        mock_create_empty_kpi_visual,
    ):
        """Test create_kpi_visual with trend group (categorical trend comparison KPI)."""
        # Setup mock responses
        mock_empty_kpi = {
            "KPIVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {"Values": [], "TargetValues": [], "TrendGroups": []},
                    "SortConfiguration": {},
                    "KPIOptions": {},
                },
                "ConditionalFormatting": {
                    "ConditionalFormattingOptions": [
                        {"ComparisonValue": {"TextColor": {"Solid": {"Expression": ""}}}},
                        {"ComparisonValue": {"TextColor": {"Solid": {"Expression": ""}}}},
                        {"ComparisonValue": {"Icon": {"CustomCondition": {"Expression": ""}}}},
                        {"ComparisonValue": {"Icon": {"CustomCondition": {"Expression": ""}}}},
                    ]
                },
                "ColumnHierarchies": [],
            }
        }
        mock_create_empty_kpi_visual.return_value = mock_empty_kpi

        mock_value = {"NumericalMeasureField": {"FieldId": "sales"}}
        mock_create_value.return_value = mock_value

        mock_category = {"CategoricalDimensionField": {"FieldId": "region"}}
        mock_create_category.return_value = mock_category

        mock_sort = {"FieldSort": {"FieldId": "region", "Direction": "DESC"}}
        mock_create_category_sort.return_value = mock_sort

        # Call the function with trend group parameters (categorical)
        kpi_parameters = {
            "visual_id": "visual1",
            "dataset_id": "dataset1",
            "value_column_name": "sales",
            "target_column_name": "",
            "trend_column_name": "region",
            "trend_is_date": False,
            "date_granularity": "",
            "agg_function": "SUM",
            "visual_type": "sparkline",
        }
        result = kpi.create_kpi_visual(kpi_parameters)

        # Verify create_category was called correctly
        mock_create_category.assert_called_once_with(
            column_name="region", dataset_id="dataset1", column_type="Categorical"
        )

        # Verify create_category_sort was called correctly
        mock_create_category_sort.assert_called_once_with(field_id="region", sort_direction="DESC")

        # Verify the result structure
        self.assertEqual(
            len(result["KPIVisual"]["ChartConfiguration"]["FieldWells"]["TrendGroups"]), 1
        )
        self.assertEqual(
            result["KPIVisual"]["ChartConfiguration"]["FieldWells"]["TrendGroups"][0], mock_category
        )
        self.assertEqual(
            "Sparkline" in result["KPIVisual"]["ChartConfiguration"]["KPIOptions"], True
        )
        self.assertEqual(
            result["KPIVisual"]["ChartConfiguration"]["KPIOptions"]["Sparkline"]["Visibility"],
            "VISIBLE",
        )
        self.assertEqual(
            result["KPIVisual"]["ChartConfiguration"]["KPIOptions"]["Sparkline"]["Type"], "LINE"
        )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.create_empty_kpi_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.chart_config.create_value")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.chart_config.create_category")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.chart_config.create_category_sort")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.chart_config.create_column_hierarchy")
    def test_create_kpi_visual_with_trend_date(
        self,
        mock_create_column_hierarchy,
        mock_create_category_sort,
        mock_create_category,
        mock_create_value,
        mock_create_empty_kpi_visual,
    ):
        """Test create_kpi_visual with date trend group (date trend comparison KPI)."""
        # Setup mock responses
        mock_empty_kpi = {
            "KPIVisual": {
                "VisualId": "visual1",
                "ChartConfiguration": {
                    "FieldWells": {"Values": [], "TargetValues": [], "TrendGroups": []},
                    "SortConfiguration": {},
                    "KPIOptions": {},
                },
                "ConditionalFormatting": {
                    "ConditionalFormattingOptions": [
                        {"ComparisonValue": {"TextColor": {"Solid": {"Expression": ""}}}},
                        {"ComparisonValue": {"TextColor": {"Solid": {"Expression": ""}}}},
                        {"ComparisonValue": {"Icon": {"CustomCondition": {"Expression": ""}}}},
                        {"ComparisonValue": {"Icon": {"CustomCondition": {"Expression": ""}}}},
                    ]
                },
                "ColumnHierarchies": [],
            }
        }
        mock_create_empty_kpi_visual.return_value = mock_empty_kpi

        mock_value = {"NumericalMeasureField": {"FieldId": "sales"}}
        mock_create_value.return_value = mock_value

        mock_category = {"DateDimensionField": {"FieldId": "date", "FormatConfiguration": {}}}
        mock_create_category.return_value = mock_category

        mock_sort = {"FieldSort": {"FieldId": "date", "Direction": "DESC"}}
        mock_create_category_sort.return_value = mock_sort

        mock_hierarchy = {"DateTimeHierarchy": {"HierarchyId": "date"}}
        mock_create_column_hierarchy.return_value = mock_hierarchy

        # Call the function with trend group parameters (date)
        kpi_parameters = {
            "visual_id": "visual1",
            "dataset_id": "dataset1",
            "value_column_name": "sales",
            "target_column_name": "",
            "trend_column_name": "date",
            "trend_is_date": True,
            "date_granularity": "MONTH",
            "agg_function": "SUM",
            "visual_type": "sparkline_area",
        }
        result = kpi.create_kpi_visual(kpi_parameters)

        # Verify create_category was called correctly
        mock_create_category.assert_called_once_with(
            column_name="date", dataset_id="dataset1", column_type="Date", date_granularity="MONTH"
        )

        # Verify create_column_hierarchy was called correctly
        mock_create_column_hierarchy.assert_called_once_with(column_name="date")

        # Verify the result structure
        self.assertEqual(
            len(result["KPIVisual"]["ChartConfiguration"]["FieldWells"]["TrendGroups"]), 1
        )
        self.assertEqual(
            "FormatConfiguration"
            not in result["KPIVisual"]["ChartConfiguration"]["FieldWells"]["TrendGroups"][0][
                "DateDimensionField"
            ],
            True,
        )
        self.assertEqual(len(result["KPIVisual"]["ColumnHierarchies"]), 1)
        self.assertEqual(result["KPIVisual"]["ColumnHierarchies"][0], mock_hierarchy)
        self.assertEqual(
            "sparkline_area" in result["KPIVisual"]["ChartConfiguration"]["KPIOptions"], False
        )
        self.assertEqual(
            "Sparkline" in result["KPIVisual"]["ChartConfiguration"]["KPIOptions"], True
        )
        self.assertEqual(
            result["KPIVisual"]["ChartConfiguration"]["KPIOptions"]["Sparkline"]["Type"], "AREA"
        )

    def test_create_kpi_visual_none_parameters(self):
        """Test create_kpi_visual with None parameters (should raise AssertionError)."""
        # Verify that passing None as kpi_parameters raises an AssertionError
        with self.assertRaises(AssertionError) as context:
            kpi.create_kpi_visual(None)

        # Verify the exception message
        self.assertEqual(str(context.exception), "kpi_parameters cannot be None")


class TestMyUpdateDashboardAddKpi(IsolatedAsyncioTestCase):
    """Test cases for my_update_dashboard_add_kpi function."""

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.qs.client")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.qs.update_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.create_kpi_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.qs.get_dash_version")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.qs.my_update_dashboard_publish")
    async def test_update_dashboard_add_kpi_success(
        self,
        mock_publish,
        mock_get_dash_version,
        mock_create_kpi_visual,
        mock_update_visual,
        mock_get_current_visuals,
        mock_client,
    ):
        """Test my_update_dashboard_add_kpi with valid parameters."""
        # Setup mock visuals
        mock_visuals = [
            {"LineChartVisual": {"VisualId": "visual1", "Title": {"Visibility": "VISIBLE"}}},
        ]
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock KPI visual
        mock_kpi = {
            "KPIVisual": {
                "VisualId": "visual2",
                "Title": {"Visibility": "VISIBLE"},
                "ChartConfiguration": {
                    "FieldWells": {"Values": []},
                    "KPIOptions": {},
                },
            }
        }
        mock_create_kpi_visual.return_value = mock_kpi

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
                        mock_kpi,
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
        result = await kpi.my_update_dashboard_add_kpi(
            dash_id="dashboard1",
            dash_name="Dashboard 1",
            sheet_id="sheet1",
            visual_id="visual2",
            dataset_id="dataset1",
            value_column_name="sales",
            target_column_name="",
            trend_column_name="",
            trend_is_date=False,
            date_granularity="",
            agg_function="SUM",
            visual_type="",
        )

        # Verify get_current_visuals was called correctly
        mock_get_current_visuals.assert_called_once_with("dashboard1", "sheet1")

        # Verify create_kpi_visual was called with the correct parameters
        expected_kpi_params = {
            "visual_id": "visual2",
            "dataset_id": "dataset1",
            "value_column_name": "sales",
            "target_column_name": "",
            "trend_column_name": "",
            "trend_is_date": False,
            "date_granularity": "",
            "agg_function": "SUM",
            "visual_type": "",
        }
        mock_create_kpi_visual.assert_called_once_with(expected_kpi_params)

        # Verify update_visual was called with the updated visuals
        expected_visuals = [
            {"LineChartVisual": {"VisualId": "visual1", "Title": {"Visibility": "VISIBLE"}}},
            mock_kpi,
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

    async def test_update_dashboard_add_kpi_none_dash_id(self):
        """Test my_update_dashboard_add_kpi with None as dash_id (should raise AssertionError)."""
        # Verify that passing None as dash_id raises an AssertionError
        with pytest.raises(AssertionError, match="dash_id cannot be None"):
            await kpi.my_update_dashboard_add_kpi(
                dash_id=None,
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                value_column_name="sales",
                target_column_name="",
                trend_column_name="",
                trend_is_date=False,
                date_granularity="",
                agg_function="SUM",
                visual_type="",
            )

    async def test_update_dashboard_add_kpi_none_dash_name(self):
        """Test my_update_dashboard_add_kpi with None as dash_name (should raise AssertionError)."""
        # Verify that passing None as dash_name raises an AssertionError
        with pytest.raises(AssertionError, match="dash_name cannot be None"):
            await kpi.my_update_dashboard_add_kpi(
                dash_id="dashboard1",
                dash_name=None,
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                value_column_name="sales",
                target_column_name="",
                trend_column_name="",
                trend_is_date=False,
                date_granularity="",
                agg_function="SUM",
                visual_type="",
            )

    async def test_update_dashboard_add_kpi_none_sheet_id(self):
        """Test my_update_dashboard_add_kpi with None as sheet_id (should raise AssertionError)."""
        # Verify that passing None as sheet_id raises an AssertionError
        with pytest.raises(AssertionError, match="sheet_id cannot be None"):
            await kpi.my_update_dashboard_add_kpi(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id=None,
                visual_id="visual1",
                dataset_id="dataset1",
                value_column_name="sales",
                target_column_name="",
                trend_column_name="",
                trend_is_date=False,
                date_granularity="",
                agg_function="SUM",
                visual_type="",
            )

    async def test_update_dashboard_add_kpi_none_visual_id(self):
        """Test my_update_dashboard_add_kpi with None as visual_id (should raise AssertionError)."""
        # Verify that passing None as visual_id raises an AssertionError
        with pytest.raises(AssertionError, match="visual_id cannot be None"):
            await kpi.my_update_dashboard_add_kpi(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id=None,
                dataset_id="dataset1",
                value_column_name="sales",
                target_column_name="",
                trend_column_name="",
                trend_is_date=False,
                date_granularity="",
                agg_function="SUM",
                visual_type="",
            )

    async def test_update_dashboard_add_kpi_none_dataset_id(self):
        """Test my_update_dashboard_add_kpi with None as dataset_id (should raise AssertionError)."""
        # Verify that passing None as dataset_id raises an AssertionError
        with pytest.raises(AssertionError, match="dataset_id cannot be None"):
            await kpi.my_update_dashboard_add_kpi(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id=None,
                value_column_name="sales",
                target_column_name="",
                trend_column_name="",
                trend_is_date=False,
                date_granularity="",
                agg_function="SUM",
                visual_type="",
            )

    async def test_update_dashboard_add_kpi_none_value_column_name(self):
        """Test my_update_dashboard_add_kpi with None as value_column_name (should raise AssertionError)."""
        # Verify that passing None as value_column_name raises an AssertionError
        with pytest.raises(AssertionError, match="value_column_name cannot be None"):
            await kpi.my_update_dashboard_add_kpi(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                value_column_name=None,
                target_column_name="",
                trend_column_name="",
                trend_is_date=False,
                date_granularity="",
                agg_function="SUM",
                visual_type="",
            )

    async def test_update_dashboard_add_kpi_none_target_column_name(self):
        """Test my_update_dashboard_add_kpi with None as target_column_name (should raise AssertionError)."""
        # Verify that passing None as target_column_name raises an AssertionError
        with pytest.raises(AssertionError, match="target_column_name cannot be None"):
            await kpi.my_update_dashboard_add_kpi(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                value_column_name="sales",
                target_column_name=None,
                trend_column_name="",
                trend_is_date=False,
                date_granularity="",
                agg_function="SUM",
                visual_type="",
            )

    async def test_update_dashboard_add_kpi_none_trend_column_name(self):
        """Test my_update_dashboard_add_kpi with None as trend_column_name (should raise AssertionError)."""
        # Verify that passing None as trend_column_name raises an AssertionError
        with pytest.raises(AssertionError, match="trend_column_name cannot be None"):
            await kpi.my_update_dashboard_add_kpi(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                value_column_name="sales",
                target_column_name="",
                trend_column_name=None,
                trend_is_date=False,
                date_granularity="",
                agg_function="SUM",
                visual_type="",
            )

    async def test_update_dashboard_add_kpi_none_agg_function(self):
        """Test my_update_dashboard_add_kpi with None as agg_function (should raise AssertionError)."""
        # Verify that passing None as agg_function raises an AssertionError
        with pytest.raises(AssertionError, match="agg_function cannot be None"):
            await kpi.my_update_dashboard_add_kpi(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                value_column_name="sales",
                target_column_name="",
                trend_column_name="",
                trend_is_date=False,
                date_granularity="",
                agg_function=None,
                visual_type="",
            )

    async def test_update_dashboard_add_kpi_none_visual_type(self):
        """Test my_update_dashboard_add_kpi with None as visual_type (should raise AssertionError)."""
        # Verify that passing None as visual_type raises an AssertionError
        with pytest.raises(AssertionError, match="visual_type cannot be None"):
            await kpi.my_update_dashboard_add_kpi(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                value_column_name="sales",
                target_column_name="",
                trend_column_name="",
                trend_is_date=False,
                date_granularity="",
                agg_function="SUM",
                visual_type=None,
            )

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.create_kpi_visual")
    async def test_update_dashboard_add_kpi_create_error(
        self, mock_create_kpi_visual, mock_get_current_visuals
    ):
        """Test my_update_dashboard_add_kpi when create_kpi_visual raises an exception."""
        # Setup mock visuals
        mock_visuals = []
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock to raise an exception
        mock_create_kpi_visual.side_effect = Exception("Create Error")

        # Verify the exception is propagated
        with self.assertRaises(Exception) as context:
            await kpi.my_update_dashboard_add_kpi(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                value_column_name="sales",
                target_column_name="",
                trend_column_name="",
                trend_is_date=False,
                date_granularity="",
                agg_function="SUM",
                visual_type="",
            )

        # Verify the exception message
        self.assertEqual(str(context.exception), "Create Error")

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.qs.get_current_visuals")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.create_kpi_visual")
    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.qs.update_visual")
    async def test_update_dashboard_add_kpi_update_error(
        self, mock_update_visual, mock_create_kpi_visual, mock_get_current_visuals
    ):
        """Test my_update_dashboard_add_kpi when update_visual raises an exception."""
        # Setup mock visuals
        mock_visuals = []
        mock_get_current_visuals.return_value = mock_visuals

        # Setup mock KPI visual
        mock_kpi = {
            "KPIVisual": {
                "VisualId": "visual1",
                "Title": {"Visibility": "VISIBLE"},
                "ChartConfiguration": {
                    "FieldWells": {"Values": []},
                    "KPIOptions": {},
                },
            }
        }
        mock_create_kpi_visual.return_value = mock_kpi

        # Setup mock to raise an exception
        mock_update_visual.side_effect = Exception("Update Error")

        # Verify the exception is propagated
        with self.assertRaises(Exception) as context:
            await kpi.my_update_dashboard_add_kpi(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                value_column_name="sales",
                target_column_name="",
                trend_column_name="",
                trend_is_date=False,
                date_granularity="",
                agg_function="SUM",
                visual_type="",
            )

        # Verify the exception message
        self.assertEqual(str(context.exception), "Update Error")

    @patch("awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi.qs.get_current_visuals")
    async def test_update_dashboard_add_kpi_none_visuals(self, mock_get_current_visuals):
        """Test my_update_dashboard_add_kpi when get_current_visuals returns None."""
        # Setup mock to return None (sheet not found)
        mock_get_current_visuals.return_value = None

        # Verify the function raises an exception when visuals is None
        with self.assertRaises(Exception):
            await kpi.my_update_dashboard_add_kpi(
                dash_id="dashboard1",
                dash_name="Dashboard 1",
                sheet_id="sheet1",
                visual_id="visual1",
                dataset_id="dataset1",
                value_column_name="sales",
                target_column_name="",
                trend_column_name="",
                trend_is_date=False,
                date_granularity="",
                agg_function="SUM",
                visual_type="",
            )
