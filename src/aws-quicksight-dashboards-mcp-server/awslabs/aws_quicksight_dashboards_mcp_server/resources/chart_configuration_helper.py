def create_category(
    column_name: str, dataset_id: str, column_type: str, date_granularity: str = ""
):
    """
    Creates a category JSON object for charts

    Args:
        column_name (string): Name of the column to be used as the category
        dataset_id (string): ID of the dataset to be used as the category
        column_type (string): Determines the type of the column

    Returns:
        A category JSON object
    """

    assert column_name is not None, "column_name cannot be None"
    assert dataset_id is not None, "dataset_id cannot be None"
    assert column_type is not None, "column_type cannot be None"
    assert date_granularity is not None, "date_granularity cannot be None"
    if date_granularity != "":
        assert date_granularity in [
            "YEAR",
            "QUARTER",
            "MONTH",
            "WEEK",
            "DAY",
            "HOUR",
            "MINUTE",
            "SECOND",
        ], "Unsupport date granularity type. Make sure it is one of: YEAR, QUARTER, MONTH, WEEK, DAY, HOUR, MINUTE, SECOND"

    category = {}
    if column_type == "Categorical":
        category = {
            "CategoricalDimensionField": {
                "FieldId": column_name,
                "Column": {"ColumnName": column_name, "DataSetIdentifier": dataset_id},
            }
        }
    elif column_type == "Numerical":
        category = {
            "NumericalDimensionField": {
                "FieldId": column_name,
                "Column": {"ColumnName": column_name, "DataSetIdentifier": dataset_id},
            }
        }
    else:
        category = {
            "DateDimensionField": {
                "FieldId": column_name,
                "Column": {"ColumnName": column_name, "DataSetIdentifier": dataset_id},
                "HierarchyId": column_name,
                "DateGranularity": date_granularity,
                "FormatConfiguration": {
                    "DateTimeFormat": "MM-DD-YYYY h:mm a",
                    "NullValueFormatConfiguration": {"NullString": "null"},
                },
            }
        }

    return category


def create_column_hierarchy(column_name: str):
    """
    Creates a column hierarchy JSON object for charts
    This is typically only used for DateTime tpye

    Args:
        column_name (string): Name of the column to be used as the category

    Returns:
        A column hierarchy JSON object
    """

    assert column_name is not None, "column_name cannot be None"

    column_hierarchy = {
        "DateTimeHierarchy": {
            "HierarchyId": column_name,
        }
    }
    return column_hierarchy


def create_value(column_name: str, dataset_id: str, numerical_aggregation: str):
    """
    Creates a value JSON object for charts

    Args:
        column_name (string): Name of the column to be used as the value
        dataset_id (string): ID of the dataset to be used as the value
        numerical_aggregation (string): Function to aggregate values

    Returns:
        A value JSON object
    """

    assert column_name is not None, "column_name cannot be None"
    assert dataset_id is not None, "dataset_id cannot be None"
    assert numerical_aggregation is not None, "numerical_aggregation cannot be None"

    value = {
        "NumericalMeasureField": {
            "FieldId": column_name,
            "Column": {"ColumnName": column_name, "DataSetIdentifier": dataset_id},
            "AggregationFunction": {"SimpleNumericalAggregation": numerical_aggregation},
        }
    }
    return value


def create_color(column_name: str, dataset_id: str):
    """
    Creates a color (sub-category) JSON object for charts

    Args:
        column_name (string): Name of the column to be used as the sub-category
        dataset_id (string): ID of the dataset used

    Returns:
        A JSON color object
    """

    assert column_name is not None, "column_name cannot be None"
    assert dataset_id is not None, "dataset_id cannot be None"

    color = {
        "CategoricalDimensionField": {
            "FieldId": column_name,
            "Column": {"DataSetIdentifier": dataset_id, "ColumnName": column_name},
        }
    }

    return color


def create_highchart_date(column_name: str, dataset_id: str, date_granularity: str = ""):
    """
    Creates a date JSON object for highcharts

    Args:
        column_name (string): Name of the column to be used as the date
        dataset_id (string): ID of the dataset to be used as the date
        date_granularity (string): Granularity of the date

    Returns:
        A JSON date object
    """

    assert column_name is not None, "column_name cannot be None"
    assert dataset_id is not None, "dataset_id cannot be None"
    assert date_granularity in [
        "YEAR",
        "QUARTER",
        "MONTH",
        "WEEK",
        "DAY",
        "HOUR",
        "MINUTE",
        "SECOND",
    ], "Unsupport date granularity type. Make sure it is one of: YEAR, QUARTER, MONTH, WEEK, DAY, HOUR, MINUTE, SECOND"

    date = {
        "DateDimensionField": {
            "FieldId": column_name,
            "Column": {"ColumnName": column_name, "DataSetIdentifier": dataset_id},
            "DateGranularity": date_granularity,
            "FormatConfiguration": {
                "DateTimeFormat": "MM-DD-YYYY",
                "NullValueFormatConfiguration": {"NullString": "null"},
            },
        }
    }

    return date


def create_category_sort(field_id: str, sort_direction: str):
    """
    Creates a category sort JSON object for charts

    Args:
        field_id (string): Name of the column to be sorted
        sort_direction (string): DESC or ASC; chooses the direction of the sort

    Returns:
        A JSON category sort object
    """

    assert field_id is not None, "field_id cannot be None"
    assert sort_direction is not None, "sort_direction cannot be None"

    category_sort = {"FieldSort": {"FieldId": field_id, "Direction": sort_direction}}
    return category_sort


def create_tool_tip_item(field_id: str):
    """
    Creates a tool tip item JSON object

    Args:
        field_id (string): ID of the columns (This should be the IDs of all category, values, and colors)

    Returns:
        A JSON tool tip object
    """

    assert field_id is not None, "field_id cannot be None"

    tool_tip_item = {"FieldTooltipItem": {"FieldId": field_id, "Visibility": "VISIBLE"}}
    return tool_tip_item


def create_field_options(field_id: str, visibility: str):
    """
    Creates a field options JSON object

    Args:
        field_id (string): ID of the columns (This should be the IDs of all category, values, and colors)
        visibility (string): Determines the visibility of the field

    Returns:
        A JSON field options object
    """

    assert field_id is not None, "field_id cannot be None"
    assert visibility is not None, "visibility cannot be None"

    field_options = {"FieldId": field_id, "Visibility": visibility}
    return field_options


def create_field_sort_options(field_id: str, direction: str):
    """
    Creates a field sort options JSON object

    Args:
        field_id (string): ID of the columns (This should be the IDs of all category, values, and colors)
        direction (string): Sorting direction

    Returns:
        A JSON field sorting options object
    """

    assert field_id is not None, "field_id cannot be None"
    assert direction is not None, "direction cannot be None"

    field_sort_options = {
        "FieldId": field_id,
        "SortBy": {"Field": {"FieldId": field_id, "Direction": direction}},
    }

    return field_sort_options


def create_calculated_field(
    value_col: str, calc_type: str, agg_type: str, group: str, category_names: list[str]
):
    """
    Creates a calculated measure field JSON object

    Args:
        value_col (string): ID of the column to calculate
        calc_type (string): Type of calculation to perform: Running_Total, Difference, Percentage_Difference, Percent_of_Total, Rank, Percentile
        agg_type (string): Aggregation type to apply to the value column: Sum, Avg, Count, Max, Median, Min
        group (string): Category column to group calculations by. This is usually the second to last column in the categorical dimensional field
        category_names (list[str]): Column names of all the categories in the pivot table. Used for Running_Total, Difference,
    Returns:
        A calculated measure field JSON object
    """

    assert value_col is not None, "value_col cannot be None"
    assert calc_type in [
        "Running_Total",
        "Difference",
        "Percentage_Difference",
        "Percent_of_Total",
        "Rank",
        "Percentile",
    ], "calc_type must be one of Running_Total, Difference, Percentage_Difference, Percent_of_Total, Rank, or Precentile."
    assert agg_type in [
        "Sum",
        "Avg",
        "Count",
        "Max",
        "Median",
        "Min",
    ], "agg_type must be one of Sum, Avg, Count, Max, Median, or Min."
    assert group is not None, "group cannot be None"

    expression = ""

    # Handle calculation type
    if calc_type == "Running_Total":
        expression += "runningSum("
    elif calc_type == "Difference":
        expression += "difference("
    elif calc_type == "Percentage_Difference":
        expression += "percentDifference("
    elif calc_type == "Percent_of_Total":
        expression += "percentOfTotal("
    elif calc_type == "Rank":
        expression += "rank(["
    elif calc_type == "Percentile":
        expression += "percentileRank("

    # Handle aggregation type
    if agg_type == "Sum":
        expression += "SUM("
    elif agg_type == "Avg":
        expression += "AVG("
    elif agg_type == "Count":
        expression += "COUNT("
    elif agg_type == "Max":
        expression += "MAX("
    elif agg_type == "Median":
        expression += "MEDIAN("
    elif agg_type == "Min":
        expression += "MIN("

    # Add value column
    # Special case for rank and percentile
    if calc_type == "Rank":
        expression += "{" + value_col + "}) DESC], "
    elif calc_type == "Percentile":
        expression += "{" + value_col + "}) ASC], "
    else:
        expression += "{" + value_col + "}), "

    # Special cases for other calc type
    if calc_type == "Running_Total":
        expression += "["
        for category in category_names:
            expression += "{" + category + "} ASC,"
        # Get rid of the last comma at the end
        expression = expression[:-1]
        expression += "],"
    elif calc_type == "Difference" or calc_type == "Percentage_Difference":
        expression += "["
        for category in category_names:
            expression += "{" + category + "} ASC,"
        # Get rid of the last comma at the end
        expression = expression[:-1]
        expression += "], -1,"

    # Handle group
    if group != "":
        expression += "[{" + group + "}])"
    else:
        expression += "[])"

    calc_measure_field = {
        "CalculatedMeasureField": {"FieldId": value_col, "Expression": expression}
    }

    return calc_measure_field
