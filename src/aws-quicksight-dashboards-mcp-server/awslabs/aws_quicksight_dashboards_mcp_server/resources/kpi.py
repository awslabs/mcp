import json
import os

import sys
from pathlib import Path

awslabs_dir = Path(__file__).parent.parent.parent
sys.path.append(str(awslabs_dir))

import aws_quicksight_dashboards_mcp_server.resources.chart_configuration_helper as chart_config
import aws_quicksight_dashboards_mcp_server.quicksight as qs


def create_empty_kpi_visual(visual_id: str):
    """
    Creates an empty kpi visual with the given visual ID.

    Args:
        visual_id (str): The ID of the visual to be created.

    Returns:
        Skeleton definition of kpi visual
    """

    assert visual_id is not None, "visual cannot be None"

    empty_kpi_visual = None

    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "json_definitions", "kpi_definition.json")

    with open(json_path, "r") as f:
        empty_kpi_visual = json.load(f)
        empty_kpi_visual["KPIVisual"]["VisualId"] = visual_id

    return empty_kpi_visual


def create_kpi_visual(kpi_parameters):
    """
    Creates a filled out kpi definition with given parameters

    Args:
        kpi_parameters (dictionary): Key-value pairs that hosts all parameters required to generate a kpi

    Returns:
        A filled out kpi JSON object
    """

    assert kpi_parameters is not None, "kpi_parameters cannot be None"

    # Create skeleton
    kpi_object = create_empty_kpi_visual(kpi_parameters["visual_id"])

    # Create parameter based JSON objects
    value = chart_config.create_value(
        column_name=kpi_parameters["value_column_name"],
        dataset_id=kpi_parameters["dataset_id"],
        numerical_aggregation=kpi_parameters["agg_function"],
    )

    target_value = None
    trend_group = None
    date_column_hierarchy = None
    if kpi_parameters["target_column_name"] != "":
        target_value = chart_config.create_value(
            column_name=kpi_parameters["target_column_name"],
            dataset_id=kpi_parameters["dataset_id"],
            numerical_aggregation=kpi_parameters["agg_function"],
        )
    elif kpi_parameters["trend_column_name"] != "":
        if kpi_parameters["trend_is_date"]:
            trend_group = chart_config.create_category(
                column_name=kpi_parameters["trend_column_name"],
                dataset_id=kpi_parameters["dataset_id"],
                column_type="Date",
                date_granularity=kpi_parameters["date_granularity"],
            )
            del trend_group["DateDimensionField"]["FormatConfiguration"]
            date_column_hierarchy = chart_config.create_column_hierarchy(
                column_name=kpi_parameters["trend_column_name"]
            )
        else:
            trend_group = chart_config.create_category(
                column_name=kpi_parameters["trend_column_name"],
                dataset_id=kpi_parameters["dataset_id"],
                column_type="Categorical",
            )

    field_sort = None
    if kpi_parameters["trend_column_name"] != "":
        field_sort = chart_config.create_category_sort(
            field_id=kpi_parameters["trend_column_name"],
            sort_direction="DESC",
        )

    visual_type = None

    # If you are comparing value by target value, you can only have a progress bar visual type (or no visuals)
    if kpi_parameters["target_column_name"] != "" and kpi_parameters["visual_type"] != "":
        kpi_parameters["visual_type"] = "progress_bar"

    if kpi_parameters["visual_type"] == "progress_bar":
        visual_type = {
            "Visibility": "VISIBLE",
        }
    elif kpi_parameters["visual_type"] == "sparkline":
        visual_type = {
            "Visibility": "VISIBLE",
            "Type": "LINE",
            "TooltipVisibility": "VISIBLE",
        }
    elif kpi_parameters["visual_type"] == "sparkline_area":
        visual_type = {
            "Visibility": "VISIBLE",
            "Type": "AREA",
            "TooltipVisibility": "VISIBLE",
        }

    # Set conditional expression for KPI font color and up/down icon
    conditional_expression = ""
    conditional_expression_positive = ""
    conditional_expression_negative = ""

    if kpi_parameters["target_column_name"] != "":
        conditional_expression = "("
        conditional_expression += kpi_parameters["agg_function"]
        conditional_expression += "({"
        conditional_expression += kpi_parameters["value_column_name"]
        conditional_expression += "})/nullIf("
        conditional_expression += kpi_parameters["agg_function"]
        conditional_expression += "({"
        conditional_expression += kpi_parameters["target_column_name"]
        conditional_expression += "}),0))-1"
    elif kpi_parameters["trend_column_name"] != "":
        conditional_expression = "percentDifference("
        conditional_expression += kpi_parameters["agg_function"]
        conditional_expression += "({"
        conditional_expression += kpi_parameters["value_column_name"]
        conditional_expression += "}),["
        conditional_expression += kpi_parameters["agg_function"]
        conditional_expression += "({"
        conditional_expression += kpi_parameters["value_column_name"]
        conditional_expression += "}) DESC],1,[])"

    if kpi_parameters["target_column_name"] != "" or kpi_parameters["trend_column_name"] != "":
        conditional_expression_positive = conditional_expression + " > 0.0"
        conditional_expression_negative = conditional_expression + " < 0.0"

    # Populate skeleton with parameters
    kpi_object["KPIVisual"]["ChartConfiguration"]["FieldWells"]["Values"] = [value]

    if target_value:
        kpi_object["KPIVisual"]["ChartConfiguration"]["FieldWells"]["TargetValues"] = [target_value]
    elif trend_group:
        kpi_object["KPIVisual"]["ChartConfiguration"]["FieldWells"]["TrendGroups"] = [trend_group]

    if field_sort:
        kpi_object["KPIVisual"]["ChartConfiguration"]["SortConfiguration"]["TrendGroupSort"] = [
            field_sort
        ]

    if kpi_parameters["visual_type"] == "progress_bar":
        kpi_object["KPIVisual"]["ChartConfiguration"]["KPIOptions"]["ProgressBar"] = visual_type
    elif (
        kpi_parameters["visual_type"] == "sparkline"
        or kpi_parameters["visual_type"] == "sparkline_area"
    ):
        kpi_object["KPIVisual"]["ChartConfiguration"]["KPIOptions"]["Sparkline"] = visual_type

    if kpi_parameters["target_column_name"] != "" or kpi_parameters["trend_column_name"] != "":
        kpi_object["KPIVisual"]["ConditionalFormatting"]["ConditionalFormattingOptions"][0][
            "ComparisonValue"
        ]["TextColor"]["Solid"]["Expression"] = conditional_expression_positive
        kpi_object["KPIVisual"]["ConditionalFormatting"]["ConditionalFormattingOptions"][1][
            "ComparisonValue"
        ]["TextColor"]["Solid"]["Expression"] = conditional_expression_negative
        kpi_object["KPIVisual"]["ConditionalFormatting"]["ConditionalFormattingOptions"][2][
            "ComparisonValue"
        ]["Icon"]["CustomCondition"]["Expression"] = conditional_expression_positive
        kpi_object["KPIVisual"]["ConditionalFormatting"]["ConditionalFormattingOptions"][3][
            "ComparisonValue"
        ]["Icon"]["CustomCondition"]["Expression"] = conditional_expression_negative
    else:
        del kpi_object["KPIVisual"]["ConditionalFormatting"]

    kpi_object["KPIVisual"]["ColumnHierarchies"] = (
        [date_column_hierarchy] if date_column_hierarchy else []
    )

    return kpi_object


async def my_update_dashboard_add_kpi(
    dash_id: str,
    dash_name: str,
    sheet_id: str,
    visual_id: str,
    dataset_id: str,
    value_column_name: str,
    target_column_name: str = "",
    trend_column_name: str = "",
    trend_is_date: bool = False,
    date_granularity: str = "",
    agg_function: str = "SUM",
    visual_type: str = "sparkline_area",
):
    """
    Updates an existing dashboard to add a KPI visual

    There are 3 types of KPI charts:
    1. Single Value:
        Use this type if you only want to show a single value.
        For example, use this type if you want to show the total sales. Or if you want to find the average profit.
        In this case, only use the value_column_name parameter. Do not use the target_column_name and trend_column_name parameters.
    2. Target Comparison:
        Use this type if you want to compare two metric columns.
        For example, use this type if you want to compare the sales to proft. Or if you want to compare profit to discount.
        In this case, only use the value_column_name and target_column_name parameters. Do not use the trend_column_name parameter.
    3. Trend Comparison:
        Use this type if you want to compare a single metric over time.
        For example, use this type if you want to compare the year over year sales. Or if you want to compare this month's profit to last month's profit.
        In this case, only use the value_column_name and trend_column_name parameters. Do not use the target_column_name parameter.
        The trend_column_name parameter should be a column of type DATETIME in the dataset. The column name should be identical to a column name in the dataset

    Args:
        dash_id: ID of the dashboard to add KPI visual
        dash_name: Name of the dashboard to be updated to
        sheet_id: ID of the sheet to add KPI visual
        visual_id: ID of newly created KPI visual
        dataset_id: ID of the dataset to create KPI from
        value_column_name: Column name of the value variable. This is the main variable of interest to make comparison. The type of this column should be of type INTEGER or DECIMAL in the dataset. The column name should be identical to a column name in the dataset
        target_column_name: Column name of the target variable. This is the variable you want to compare the value to. The type of this column should be of type INTEGER or DECIMAL in the dataset. The column name should be identical to a column name in the dataset
        trend_column_name: Column name of the trend variable. This is the variable you want to compare the value to. The type of this column should of type STRING or DATETIME in the dataset. The column name should be identical to a column name in the dataset
        trend_is_date: Set to true if and only if when you are using the trend_column_name, and the type of the trend_column_name is DATETIME.
        date_granularity: Granularity for the trend column. One of YEAR, QUARTER, MONTH, WEEK, DAY, HOUR, MINUTE, SECOND. Only provide this granularity if there is a trend_column.
        agg_function: Aggregation function to apply to the value column. One of SUM, AVG, COUNT, MAX, MIN, MEDIAN
        visual_type: Type of visual representation to show on KPI. Options: progress_bar, sparkline, or sparkline_area. If the user does not want any visuals or did not specify, use an empty string
    Returns:
        Status of update dashboard
    """

    assert dash_id is not None, "dash_id cannot be None"
    assert dash_name is not None, "dash_name cannot be None"
    assert sheet_id is not None, "sheet_id cannot be None"
    assert visual_id is not None, "visual_id cannot be None"
    assert dataset_id is not None, "dataset_id cannot be None"
    assert value_column_name is not None, "value_column_name cannot be None"
    assert target_column_name is not None, "target_column_name cannot be None"
    assert trend_column_name is not None, "trend_column_name cannot be None"
    assert trend_is_date is not None, "trend_is_date cannot be None"
    assert date_granularity is not None, "date_granularity cannot be None"
    assert agg_function is not None, "agg_function cannot be None"
    assert visual_type is not None, "visual_type cannot be None"

    # Get the current dashboard definition[Visual]
    visuals = qs.get_current_visuals(dash_id, sheet_id)

    # Set parameters to create KPI
    kpi_parameters = {
        "visual_id": visual_id,
        "dataset_id": dataset_id,
        "value_column_name": value_column_name,
        "target_column_name": target_column_name,
        "trend_column_name": trend_column_name,
        "trend_is_date": trend_is_date,
        "date_granularity": date_granularity,
        "agg_function": agg_function,
        "visual_type": visual_type,
    }

    # Create new KPI object
    new_kpi = create_kpi_visual(kpi_parameters)

    # Append to list of visual objects
    visuals.append(new_kpi)

    # Overwrite existing visual
    new_definition = qs.update_visual(dash_id, sheet_id, visuals)

    dash_update_res = qs.client.update_dashboard(
        AwsAccountId=qs.ACCOUNT_ID,
        DashboardId=dash_id,
        Name=dash_name,
        Definition=new_definition,
    )

    new_dashboard_version = qs.get_dash_version(dash_update_res)
    publish_res = await qs.my_update_dashboard_publish(dash_id, new_dashboard_version)
    print(publish_res)

    return dash_update_res

def register_tool(mcp_server):
    mcp_server.tool()(my_update_dashboard_add_kpi)
