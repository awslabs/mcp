import json
import os

import sys
from pathlib import Path

awslabs_dir = Path(__file__).parent.parent.parent
sys.path.append(str(awslabs_dir))

import aws_quicksight_dashboards_mcp_server.resources.chart_configuration_helper as chart_config
import aws_quicksight_dashboards_mcp_server.quicksight as qs


def create_empty_line_chart_visual(visual_id: str):
    """
    Creates an empty line chart visual with the given visual ID.

    Args:
        visual_id: The ID of the visual to be created with

    Returns:
        Skeleton definition of line chart visual
    """

    assert visual_id is not None, "visual_id cannot be None"

    empty_line_chart_visual = None

    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "json_definitions", "line_chart_definition.json")
    
    with open(json_path, "r") as f:
        empty_line_chart_visual = json.load(f)
        empty_line_chart_visual["LineChartVisual"]["VisualId"] = visual_id

    return empty_line_chart_visual


def create_line_chart(line_chart_parameters):
    """
    Creates a filled out line chart with given parameters

    Args:
        line_chart_parameters (dictionary): Key-value pairs that hosts all parameters required to generate a line chart

    Returns:
        A filled out line chart JSON object
    """

    assert line_chart_parameters is not None, "line_chart_parameters cannot be None"

    # Create skeleton
    chart_object = create_empty_line_chart_visual(line_chart_parameters["visual_id"])

    # Create parameter based JSON objects
    category = chart_config.create_category(
        line_chart_parameters["category_column_name"],
        line_chart_parameters["dataset_id"],
        line_chart_parameters["category_column_type"],
        line_chart_parameters["date_granularity"],
    )

    # For DateTime type, you need a column hierarchy
    column_hierarchy = None
    if line_chart_parameters["category_column_type"] == "Date":
        column_hierarchy = chart_config.create_column_hierarchy(
            line_chart_parameters["category_column_name"]
        )

    values = []
    for value_column in line_chart_parameters["value_column_names"]:
        values.append(
            chart_config.create_value(
                value_column,
                line_chart_parameters["dataset_id"],
                line_chart_parameters["numerical_aggregation"],
            )
        )

    color = (
        chart_config.create_color(
            line_chart_parameters["color_column_name"], line_chart_parameters["dataset_id"]
        )
        if line_chart_parameters["color_column_name"] != ""
        else None
    )

    category_sort = chart_config.create_category_sort(
        line_chart_parameters["sorting_variable"], line_chart_parameters["sort_direction"]
    )

    tool_tip_fields = []
    tool_tip_fields.append(
        chart_config.create_tool_tip_item(line_chart_parameters["category_column_name"])
    )
    for value_column in line_chart_parameters["value_column_names"]:
        tool_tip_fields.append(chart_config.create_tool_tip_item(value_column))
    if color:
        tool_tip_fields.append(
            chart_config.create_tool_tip_item(line_chart_parameters["color_column_name"])
        )

    # Populate Skeleton with parameters
    chart_object["LineChartVisual"]["ChartConfiguration"]["FieldWells"][
        "LineChartAggregatedFieldWells"
    ]["Category"].append(category)

    if column_hierarchy:
        chart_object["LineChartVisual"]["ColumnHierarchies"].append(column_hierarchy)

    chart_object["LineChartVisual"]["ChartConfiguration"]["FieldWells"][
        "LineChartAggregatedFieldWells"
    ]["Values"] = values

    if color:
        chart_object["LineChartVisual"]["ChartConfiguration"]["FieldWells"][
            "LineChartAggregatedFieldWells"
        ]["Colors"].append(color)

    chart_object["LineChartVisual"]["ChartConfiguration"]["SortConfiguration"][
        "CategorySort"
    ].append(category_sort)

    chart_object["LineChartVisual"]["ChartConfiguration"]["Tooltip"]["FieldBasedTooltip"][
        "TooltipFields"
    ] = tool_tip_fields

    return chart_object


async def my_update_dashboard_add_line_chart(
    dash_id: str,
    dash_name: str,
    sheet_id: str,
    visual_id: str,
    dataset_id: str,
    sort_var: str,
    category_column_name: str,
    category_column_type: str,
    value_column_names: list[str],
    color_column_name: str = "",
    sort_direction: str = "DESC",
    numerical_aggregation: str = "SUM",
    date_granularity: str = "",
):
    """
    Updates an existing dashboard to add a line chart visual

    Args:
        dash_id: ID of the dashboard to add the line chart visual
        dash_name: Name of the dashboard to be updated to
        sheet_id: ID of the sheet to add the line chart visual
        visual_id: ID of the new line chart
        dataset_id: ID of the dataset to create line chart from
        sort_var: Value or category column name of the variable you want to sort; Unless told otherwise, it will usually be one of the value column names.
        category_column_name: Name of the row/column of the dataset you want to use as the x-axis in a vertical graph or the y-axis in a horizontal graph. This is usually the category of the data you want to see
        category_column_type: One of Categorical, Numerical, or Date; If the type of the column in the dataset is STRING,use Categorical. If the type of the column in the dataset is INTEGER or DECIMAL use Numerical. If the type of the column in the dataset is DATETIME, use Date.
        value_column_names: A list of names of the row/column of the dataset you want to use as the y-axis in a vertical graph of the x-axis in a horizontal graph. This is usually the measure of the data you want to see
        color_column_name: This is optional. Do not use when not needed. Name of the row/column of the sub-category of the category_column you want to plot
        sort_direction: Either ASC or DESC; determines the sorting order of aggregated values; ASC sorts in ascending order and DESC sorts in descending order
        numerical_aggregation: Function to aggregate the value data. Options: SUM, AVERAGE, MIN, MAX, COUNT, DISTINCT_COUNT, VAR, VARP, STDEV, STDEVP, MEDIAN. Only choose one from the options
        date_granularity: Granularity for the category column. One of YEAR, QUARTER, MONTH, WEEK, DAY, HOUR, MINUTE, SECOND. Only provide this granularity if the category column is of DATETIME type.
    Returns:
        Status of update dashboard
        After calling this function, call update_dashboard_add_visual_layout.
    """

    assert dash_id is not None, "dash_id cannot be None"
    assert dash_name is not None, "dash_name cannot be None"
    assert sheet_id is not None, "sheet_id cannot be None"
    assert visual_id is not None, "visual_id cannot be None"
    assert dataset_id is not None, "dataset_id cannot be None"
    assert sort_var is not None, "sort_var cannot be None"
    assert category_column_name is not None, "category_column_name cannot be None"
    assert category_column_type is not None, "category_column_type cannot be None"
    assert value_column_names is not None, "value_column_names cannot be None"
    assert color_column_name is not None, "color_column_name cannot be None"
    assert sort_direction is not None, "sort_direction cannot be None"
    assert numerical_aggregation is not None, "numerical_aggregation cannot be None"
    assert date_granularity is not None, "date_granularity cannot be None"

    # Get the current dashboard definition[Visual]
    visuals = qs.get_current_visuals(dash_id, sheet_id)

    # Set parameters to create the line chart
    line_chart_parameters = {
        "visual_id": visual_id,
        "dataset_id": dataset_id,
        "numerical_aggregation": numerical_aggregation,
        "sorting_variable": sort_var,
        "sort_direction": sort_direction,
        "category_column_name": category_column_name,
        "category_column_type": category_column_type,
        "value_column_names": value_column_names,
        "color_column_name": color_column_name,
        "date_granularity": date_granularity,
    }

    # Create new line chart object
    new_line_chart = create_line_chart(line_chart_parameters)

    # Append to list of visual objects
    visuals.append(new_line_chart)

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
    mcp_server.tool()(my_update_dashboard_add_line_chart)
