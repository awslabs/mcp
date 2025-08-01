from unittest import TestCase

import pytest

import sys
from pathlib import Path

qs_mcp_directory = Path(__file__).parent.parent
sys.path.append(str(qs_mcp_directory))
print(qs_mcp_directory)

import awslabs.aws_quicksight_dashboards_mcp_server.resources.chart_configuration_helper as chart_config_helper


class TestCreateCategory(TestCase):
    """Test cases for create_category function."""

    def test_create_category_categorical(self):
        """Test create_category with Categorical column type."""
        # Call the function with Categorical type
        result = chart_config_helper.create_category("product", "dataset1", "Categorical")

        # Verify the result structure
        self.assertIn("CategoricalDimensionField", result)
        self.assertEqual(result["CategoricalDimensionField"]["FieldId"], "product")
        self.assertEqual(result["CategoricalDimensionField"]["Column"]["ColumnName"], "product")
        self.assertEqual(
            result["CategoricalDimensionField"]["Column"]["DataSetIdentifier"], "dataset1"
        )

    def test_create_category_numerical(self):
        """Test create_category with Numerical column type."""
        # Call the function with Numerical type
        result = chart_config_helper.create_category("sales", "dataset1", "Numerical")

        # Verify the result structure
        self.assertIn("NumericalDimensionField", result)
        self.assertEqual(result["NumericalDimensionField"]["FieldId"], "sales")
        self.assertEqual(result["NumericalDimensionField"]["Column"]["ColumnName"], "sales")
        self.assertEqual(
            result["NumericalDimensionField"]["Column"]["DataSetIdentifier"], "dataset1"
        )

    def test_create_category_date(self):
        """Test create_category with Date column type."""
        # Call the function with Date type
        result = chart_config_helper.create_category("date", "dataset1", "Date")

        # Verify the result structure
        self.assertIn("DateDimensionField", result)
        self.assertEqual(result["DateDimensionField"]["FieldId"], "date")
        self.assertEqual(result["DateDimensionField"]["Column"]["ColumnName"], "date")
        self.assertEqual(result["DateDimensionField"]["Column"]["DataSetIdentifier"], "dataset1")
        self.assertEqual(result["DateDimensionField"]["HierarchyId"], "date")
        self.assertEqual(
            result["DateDimensionField"]["FormatConfiguration"]["DateTimeFormat"],
            "MM-DD-YYYY h:mm a",
        )
        self.assertEqual(
            result["DateDimensionField"]["FormatConfiguration"]["NullValueFormatConfiguration"][
                "NullString"
            ],
            "null",
        )

    def test_create_category_date_with_granularity(self):
        """Test create_category with Date column type and date granularity."""
        # Call the function with Date type and MONTH granularity
        result = chart_config_helper.create_category("date", "dataset1", "Date", "MONTH")

        # Verify the result structure
        self.assertIn("DateDimensionField", result)
        self.assertEqual(result["DateDimensionField"]["FieldId"], "date")
        self.assertEqual(result["DateDimensionField"]["Column"]["ColumnName"], "date")
        self.assertEqual(result["DateDimensionField"]["Column"]["DataSetIdentifier"], "dataset1")
        self.assertEqual(result["DateDimensionField"]["HierarchyId"], "date")
        self.assertEqual(result["DateDimensionField"]["DateGranularity"], "MONTH")
        self.assertEqual(
            result["DateDimensionField"]["FormatConfiguration"]["DateTimeFormat"],
            "MM-DD-YYYY h:mm a",
        )

    def test_create_category_none_column_name(self):
        """Test create_category with None as column_name (should raise AssertionError)."""
        # Verify that passing None as column_name raises an AssertionError
        with pytest.raises(AssertionError, match="column_name cannot be None"):
            chart_config_helper.create_category(None, "dataset1", "Categorical")

    def test_create_category_none_dataset_id(self):
        """Test create_category with None as dataset_id (should raise AssertionError)."""
        # Verify that passing None as dataset_id raises an AssertionError
        with pytest.raises(AssertionError, match="dataset_id cannot be None"):
            chart_config_helper.create_category("product", None, "Categorical")

    def test_create_category_none_column_type(self):
        """Test create_category with None as column_type (should raise AssertionError)."""
        # Verify that passing None as column_type raises an AssertionError
        with pytest.raises(AssertionError, match="column_type cannot be None"):
            chart_config_helper.create_category("product", "dataset1", None)

    def test_create_category_none_date_granularity(self):
        """Test create_category with None as date_granularity (should raise AssertionError)."""
        # Verify that passing None as date_granularity raises an AssertionError
        with pytest.raises(AssertionError, match="date_granularity cannot be None"):
            chart_config_helper.create_category("date", "dataset1", "Date", None)

    def test_create_category_invalid_date_granularity(self):
        """Test create_category with invalid date_granularity (should raise AssertionError)."""
        # Verify that passing an invalid date_granularity raises an AssertionError
        with pytest.raises(AssertionError):
            chart_config_helper.create_category("date", "dataset1", "Date", "INVALID_GRANULARITY")


class TestCreateColumnHierarchy(TestCase):
    """Test cases for create_column_hierarchy function."""

    def test_create_column_hierarchy_valid_column_name(self):
        """Test create_column_hierarchy with a valid column name."""
        # Call the function with a valid column name
        result = chart_config_helper.create_column_hierarchy("date")

        # Verify the result structure
        self.assertIn("DateTimeHierarchy", result)
        self.assertEqual(result["DateTimeHierarchy"]["HierarchyId"], "date")

    def test_create_column_hierarchy_none_column_name(self):
        """Test create_column_hierarchy with None as column_name (should raise AssertionError)."""
        # Verify that passing None as column_name raises an AssertionError
        with pytest.raises(AssertionError, match="column_name cannot be None"):
            chart_config_helper.create_column_hierarchy(None)


class TestCreateValue(TestCase):
    """Test cases for create_value function."""

    def test_create_value_valid_inputs(self):
        """Test create_value with valid inputs."""
        # Call the function with valid inputs
        result = chart_config_helper.create_value("sales", "dataset1", "SUM")

        # Verify the result structure
        self.assertIn("NumericalMeasureField", result)
        self.assertEqual(result["NumericalMeasureField"]["FieldId"], "sales")
        self.assertEqual(result["NumericalMeasureField"]["Column"]["ColumnName"], "sales")
        self.assertEqual(result["NumericalMeasureField"]["Column"]["DataSetIdentifier"], "dataset1")
        self.assertEqual(
            result["NumericalMeasureField"]["AggregationFunction"]["SimpleNumericalAggregation"],
            "SUM",
        )

    def test_create_value_different_aggregation(self):
        """Test create_value with different aggregation function."""
        # Call the function with AVERAGE aggregation
        result = chart_config_helper.create_value("revenue", "dataset1", "AVERAGE")

        # Verify the result structure
        self.assertIn("NumericalMeasureField", result)
        self.assertEqual(result["NumericalMeasureField"]["FieldId"], "revenue")
        self.assertEqual(
            result["NumericalMeasureField"]["AggregationFunction"]["SimpleNumericalAggregation"],
            "AVERAGE",
        )

    def test_create_value_none_column_name(self):
        """Test create_value with None as column_name (should raise AssertionError)."""
        # Verify that passing None as column_name raises an AssertionError
        with pytest.raises(AssertionError, match="column_name cannot be None"):
            chart_config_helper.create_value(None, "dataset1", "SUM")

    def test_create_value_none_dataset_id(self):
        """Test create_value with None as dataset_id (should raise AssertionError)."""
        # Verify that passing None as dataset_id raises an AssertionError
        with pytest.raises(AssertionError, match="dataset_id cannot be None"):
            chart_config_helper.create_value("sales", None, "SUM")

    def test_create_value_none_numerical_aggregation(self):
        """Test create_value with None as numerical_aggregation (should raise AssertionError)."""
        # Verify that passing None as numerical_aggregation raises an AssertionError
        with pytest.raises(AssertionError, match="numerical_aggregation cannot be None"):
            chart_config_helper.create_value("sales", "dataset1", None)


class TestCreateColor(TestCase):
    """Test cases for create_color function."""

    def test_create_color_valid_inputs(self):
        """Test create_color with valid inputs."""
        # Call the function with valid inputs
        result = chart_config_helper.create_color("region", "dataset1")

        # Verify the result structure
        self.assertIn("CategoricalDimensionField", result)
        self.assertEqual(result["CategoricalDimensionField"]["FieldId"], "region")
        self.assertEqual(result["CategoricalDimensionField"]["Column"]["ColumnName"], "region")
        self.assertEqual(
            result["CategoricalDimensionField"]["Column"]["DataSetIdentifier"], "dataset1"
        )

    def test_create_color_none_column_name(self):
        """Test create_color with None as column_name (should raise AssertionError)."""
        # Verify that passing None as column_name raises an AssertionError
        with pytest.raises(AssertionError, match="column_name cannot be None"):
            chart_config_helper.create_color(None, "dataset1")

    def test_create_color_none_dataset_id(self):
        """Test create_color with None as dataset_id (should raise AssertionError)."""
        # Verify that passing None as dataset_id raises an AssertionError
        with pytest.raises(AssertionError, match="dataset_id cannot be None"):
            chart_config_helper.create_color("region", None)


class TestCreateHighchartDate(TestCase):
    """Test cases for create_highchart_date function."""

    def test_create_highchart_date_valid_inputs(self):
        """Test create_highchart_date with valid inputs."""
        # Call the function with valid inputs
        result = chart_config_helper.create_highchart_date("order_date", "dataset1", "DAY")

        # Verify the result structure
        self.assertIn("DateDimensionField", result)
        self.assertEqual(result["DateDimensionField"]["FieldId"], "order_date")
        self.assertEqual(result["DateDimensionField"]["Column"]["ColumnName"], "order_date")
        self.assertEqual(result["DateDimensionField"]["Column"]["DataSetIdentifier"], "dataset1")
        self.assertEqual(result["DateDimensionField"]["DateGranularity"], "DAY")
        self.assertEqual(
            result["DateDimensionField"]["FormatConfiguration"]["DateTimeFormat"], "MM-DD-YYYY"
        )
        self.assertEqual(
            result["DateDimensionField"]["FormatConfiguration"]["NullValueFormatConfiguration"][
                "NullString"
            ],
            "null",
        )

    def test_create_highchart_date_different_granularity(self):
        """Test create_highchart_date with different date granularity."""
        # Call the function with MONTH granularity
        result = chart_config_helper.create_highchart_date("order_date", "dataset1", "MONTH")

        # Verify the result structure
        self.assertIn("DateDimensionField", result)
        self.assertEqual(result["DateDimensionField"]["DateGranularity"], "MONTH")

    def test_create_highchart_date_none_column_name(self):
        """Test create_highchart_date with None as column_name (should raise AssertionError)."""
        # Verify that passing None as column_name raises an AssertionError
        with pytest.raises(AssertionError, match="column_name cannot be None"):
            chart_config_helper.create_highchart_date(None, "dataset1", "DAY")

    def test_create_highchart_date_none_dataset_id(self):
        """Test create_highchart_date with None as dataset_id (should raise AssertionError)."""
        # Verify that passing None as dataset_id raises an AssertionError
        with pytest.raises(AssertionError, match="dataset_id cannot be None"):
            chart_config_helper.create_highchart_date("order_date", None, "DAY")

    def test_create_highchart_date_invalid_granularity(self):
        """Test create_highchart_date with invalid date granularity (should raise AssertionError)."""
        # Verify that passing an invalid date granularity raises an AssertionError
        with pytest.raises(AssertionError):
            chart_config_helper.create_highchart_date(
                "order_date", "dataset1", "INVALID_GRANULARITY"
            )


class TestCreateCategorySort(TestCase):
    """Test cases for create_category_sort function."""

    def test_create_category_sort_valid_inputs(self):
        """Test create_category_sort with valid inputs."""
        # Call the function with valid inputs
        result = chart_config_helper.create_category_sort("product", "DESC")

        # Verify the result structure
        self.assertIn("FieldSort", result)
        self.assertEqual(result["FieldSort"]["FieldId"], "product")
        self.assertEqual(result["FieldSort"]["Direction"], "DESC")

    def test_create_category_sort_none_field_id(self):
        """Test create_category_sort with None as field_id (should raise AssertionError)."""
        # Verify that passing None as field_id raises an AssertionError
        with pytest.raises(AssertionError, match="field_id cannot be None"):
            chart_config_helper.create_category_sort(None, "DESC")

    def test_create_category_sort_none_sort_direction(self):
        """Test create_category_sort with None as sort_direction (should raise AssertionError)."""
        # Verify that passing None as sort_direction raises an AssertionError
        with pytest.raises(AssertionError, match="sort_direction cannot be None"):
            chart_config_helper.create_category_sort("product", None)


class TestCreateToolTipItem(TestCase):
    """Test cases for create_tool_tip_item function."""

    def test_create_tool_tip_item_valid_inputs(self):
        # Call the function with valid inputs
        result = chart_config_helper.create_tool_tip_item("product1")

        # Verify the result structure
        self.assertIn("FieldTooltipItem", result)
        self.assertEqual(result["FieldTooltipItem"]["FieldId"], "product1")

    def test_create_tool_tip_item_none_field_id(self):
        # Verify that passing None as field_id raises an AssertionError
        with pytest.raises(AssertionError, match="field_id cannot be None"):
            chart_config_helper.create_tool_tip_item(None)


class TestCreateFieldOptions(TestCase):
    """Test cases for create_field_options function."""

    def test_create_field_options_valid_inputs(self):
        """Test create_field_options with valid inputs."""
        # Call the function with valid inputs
        result = chart_config_helper.create_field_options("sales", "VISIBLE")

        # Verify the result structure
        self.assertEqual(result["FieldId"], "sales")
        self.assertEqual(result["Visibility"], "VISIBLE")

    def test_create_field_options_hidden_visibility(self):
        """Test create_field_options with HIDDEN visibility."""
        # Call the function with HIDDEN visibility
        result = chart_config_helper.create_field_options("product", "HIDDEN")

        # Verify the result structure
        self.assertEqual(result["FieldId"], "product")
        self.assertEqual(result["Visibility"], "HIDDEN")

    def test_create_field_options_none_field_id(self):
        """Test create_field_options with None as field_id (should raise AssertionError)."""
        # Verify that passing None as field_id raises an AssertionError
        with pytest.raises(AssertionError, match="field_id cannot be None"):
            chart_config_helper.create_field_options(None, "VISIBLE")

    def test_create_field_options_none_visibility(self):
        """Test create_field_options with None as visibility (should raise AssertionError)."""
        # Verify that passing None as visibility raises an AssertionError
        with pytest.raises(AssertionError, match="visibility cannot be None"):
            chart_config_helper.create_field_options("sales", None)


class TestCreateFieldSortOptions(TestCase):
    """Test cases for create_field_sort_options function."""

    def test_create_field_sort_options_valid_inputs(self):
        """Test create_field_sort_options with valid inputs."""
        # Call the function with valid inputs
        result = chart_config_helper.create_field_sort_options("sales", "DESC")

        # Verify the result structure
        self.assertEqual(result["FieldId"], "sales")
        self.assertEqual(result["SortBy"]["Field"]["FieldId"], "sales")
        self.assertEqual(result["SortBy"]["Field"]["Direction"], "DESC")

    def test_create_field_sort_options_asc_direction(self):
        """Test create_field_sort_options with ASC direction."""
        # Call the function with ASC direction
        result = chart_config_helper.create_field_sort_options("product", "ASC")

        # Verify the result structure
        self.assertEqual(result["FieldId"], "product")
        self.assertEqual(result["SortBy"]["Field"]["FieldId"], "product")
        self.assertEqual(result["SortBy"]["Field"]["Direction"], "ASC")

    def test_create_field_sort_options_none_field_id(self):
        """Test create_field_sort_options with None as field_id (should raise AssertionError)."""
        # Verify that passing None as field_id raises an AssertionError
        with pytest.raises(AssertionError, match="field_id cannot be None"):
            chart_config_helper.create_field_sort_options(None, "DESC")

    def test_create_field_sort_options_none_direction(self):
        """Test create_field_sort_options with None as direction (should raise AssertionError)."""
        # Verify that passing None as direction raises an AssertionError
        with pytest.raises(AssertionError, match="direction cannot be None"):
            chart_config_helper.create_field_sort_options("sales", None)


class TestCreateCalculatedField(TestCase):
    """Test cases for create_calculated_field function."""

    def test_create_calculated_field_running_total(self):
        """Test create_calculated_field with Running_Total calculation type."""
        # Call the function with Running_Total calculation
        result = chart_config_helper.create_calculated_field(
            "sales", "Running_Total", "Sum", "region", ["country", "region", "city"]
        )

        # Verify the result structure
        self.assertIn("CalculatedMeasureField", result)
        self.assertEqual(result["CalculatedMeasureField"]["FieldId"], "sales")
        self.assertTrue("Expression" in result["CalculatedMeasureField"])
        # Check that the expression contains the expected parts
        expression = result["CalculatedMeasureField"]["Expression"]
        self.assertTrue(
            expression.startswith(
                "runningSum(SUM({sales}), [{country} ASC,{region} ASC,{city} ASC],"
            )
        )

    def test_create_calculated_field_difference(self):
        """Test create_calculated_field with Difference calculation type."""
        # Call the function with Difference calculation
        result = chart_config_helper.create_calculated_field(
            "revenue", "Difference", "Avg", "product", ["date", "product"]
        )

        # Verify the result structure
        self.assertIn("CalculatedMeasureField", result)
        self.assertEqual(result["CalculatedMeasureField"]["FieldId"], "revenue")
        # Check that the expression contains the expected parts
        expression = result["CalculatedMeasureField"]["Expression"]
        self.assertTrue(
            expression.startswith("difference(AVG({revenue}), [{date} ASC,{product} ASC], -1,")
        )

    def test_create_calculated_field_percentage_difference(self):
        """Test create_calculated_field with Percentage_Difference calculation type."""
        # Call the function with Percentage_Difference calculation
        result = chart_config_helper.create_calculated_field(
            "profit", "Percentage_Difference", "Sum", "category", ["year", "category"]
        )

        # Verify the result structure
        self.assertIn("CalculatedMeasureField", result)
        self.assertEqual(result["CalculatedMeasureField"]["FieldId"], "profit")
        # Check that the expression contains the expected parts
        expression = result["CalculatedMeasureField"]["Expression"]
        self.assertTrue(
            expression.startswith(
                "percentDifference(SUM({profit}), [{year} ASC,{category} ASC], -1,"
            )
        )

    def test_create_calculated_field_percent_of_total(self):
        """Test create_calculated_field with Percent_of_Total calculation type."""
        # Call the function with Percent_of_Total calculation
        result = chart_config_helper.create_calculated_field(
            "sales", "Percent_of_Total", "Sum", "region", []
        )

        # Verify the result structure
        self.assertIn("CalculatedMeasureField", result)
        self.assertEqual(result["CalculatedMeasureField"]["FieldId"], "sales")
        # Check that the expression contains the expected parts
        expression = result["CalculatedMeasureField"]["Expression"]
        self.assertTrue(expression.startswith("percentOfTotal(SUM({sales}), [{region}])"))

    def test_create_calculated_field_rank(self):
        """Test create_calculated_field with Rank calculation type."""
        # Call the function with Rank calculation
        result = chart_config_helper.create_calculated_field("sales", "Rank", "Sum", "region", [])

        # Verify the result structure
        self.assertIn("CalculatedMeasureField", result)
        self.assertEqual(result["CalculatedMeasureField"]["FieldId"], "sales")
        # Check that the expression contains the expected parts
        expression = result["CalculatedMeasureField"]["Expression"]
        self.assertTrue(expression.startswith("rank([SUM({sales}) DESC], [{region}])"))

    def test_create_calculated_field_percentile(self):
        """Test create_calculated_field with Percentile calculation type."""
        # Call the function with Percentile calculation
        result = chart_config_helper.create_calculated_field(
            "sales", "Percentile", "Sum", "region", []
        )

        # Verify the result structure
        self.assertIn("CalculatedMeasureField", result)
        self.assertEqual(result["CalculatedMeasureField"]["FieldId"], "sales")
        # Check that the expression contains the expected parts
        expression = result["CalculatedMeasureField"]["Expression"]
        self.assertTrue(expression.startswith("percentileRank(SUM({sales}) ASC], [{region}])"))

    def test_create_calculated_field_count_aggregation(self):
        """Test create_calculated_field with Count aggregation type."""
        # Call the function with Count aggregation
        result = chart_config_helper.create_calculated_field(
            "orders", "Running_Total", "Count", "region", ["country", "region"]
        )

        # Verify the result structure
        self.assertIn("CalculatedMeasureField", result)
        self.assertEqual(result["CalculatedMeasureField"]["FieldId"], "orders")
        # Check that the expression contains the expected parts
        expression = result["CalculatedMeasureField"]["Expression"]
        self.assertTrue(
            expression.startswith("runningSum(COUNT({orders}), [{country} ASC,{region} ASC],")
        )

    def test_create_calculated_field_max_aggregation(self):
        """Test create_calculated_field with Max aggregation type."""
        # Call the function with Max aggregation
        result = chart_config_helper.create_calculated_field(
            "price", "Percent_of_Total", "Max", "product", []
        )

        # Verify the result structure
        self.assertIn("CalculatedMeasureField", result)
        self.assertEqual(result["CalculatedMeasureField"]["FieldId"], "price")
        # Check that the expression contains the expected parts
        expression = result["CalculatedMeasureField"]["Expression"]
        self.assertTrue(expression.startswith("percentOfTotal(MAX({price}), [{product}])"))

    def test_create_calculated_field_median_aggregation(self):
        """Test create_calculated_field with Median aggregation type."""
        # Call the function with Median aggregation
        result = chart_config_helper.create_calculated_field(
            "response_time", "Difference", "Median", "service", ["date", "service"]
        )

        # Verify the result structure
        self.assertIn("CalculatedMeasureField", result)
        self.assertEqual(result["CalculatedMeasureField"]["FieldId"], "response_time")
        # Check that the expression contains the expected parts
        expression = result["CalculatedMeasureField"]["Expression"]
        self.assertTrue(
            expression.startswith(
                "difference(MEDIAN({response_time}), [{date} ASC,{service} ASC], -1,"
            )
        )

    def test_create_calculated_field_min_aggregation(self):
        """Test create_calculated_field with Min aggregation type."""
        # Call the function with Min aggregation
        result = chart_config_helper.create_calculated_field(
            "temperature", "Rank", "Min", "location", []
        )

        # Verify the result structure
        self.assertIn("CalculatedMeasureField", result)
        self.assertEqual(result["CalculatedMeasureField"]["FieldId"], "temperature")
        # Check that the expression contains the expected parts
        expression = result["CalculatedMeasureField"]["Expression"]
        self.assertTrue(expression.startswith("rank([MIN({temperature}) DESC], [{location}])"))

    def test_create_calculated_field_none_value_col(self):
        """Test create_calculated_field with None as value_col (should raise AssertionError)."""
        # Verify that passing None as value_col raises an AssertionError
        with pytest.raises(AssertionError, match="value_col cannot be None"):
            chart_config_helper.create_calculated_field(None, "Running_Total", "Sum", "region", [])

    def test_create_calculated_field_invalid_calc_type(self):
        """Test create_calculated_field with invalid calc_type (should raise AssertionError)."""
        # Verify that passing an invalid calc_type raises an AssertionError
        with pytest.raises(AssertionError):
            chart_config_helper.create_calculated_field(
                "sales", "INVALID_TYPE", "Sum", "region", []
            )

    def test_create_calculated_field_invalid_agg_type(self):
        """Test create_calculated_field with invalid agg_type (should raise AssertionError)."""
        # Verify that passing an invalid agg_type raises an AssertionError
        with pytest.raises(AssertionError):
            chart_config_helper.create_calculated_field(
                "sales", "Running_Total", "INVALID_AGG", "region", []
            )

    def test_create_calculated_field_none_group(self):
        """Test create_calculated_field with None as group (should raise AssertionError)."""
        # Verify that passing None as group raises an AssertionError
        with pytest.raises(AssertionError, match="group cannot be None"):
            chart_config_helper.create_calculated_field("sales", "Running_Total", "Sum", None, [])
