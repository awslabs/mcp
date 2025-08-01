import json
import os

import sys
from pathlib import Path

awslabs_dir = Path(__file__).parent.parent.parent
sys.path.append(str(awslabs_dir))

import aws_quicksight_dashboards_mcp_server.resources.chart_configuration_helper as chart_config
import aws_quicksight_dashboards_mcp_server.quicksight as qs


def create_empty_highchart_visual(visual_id: str):
    """
    Creates an empty highchart visual with the given visual ID.

    Args:
        visual_id (str): The ID of the visual to be created.

    Returns:
        Skeleton definition of table visual
    """

    assert visual_id is not None, "visual cannot be None"

    empty_highchart_visual = None

    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "json_definitions", "highchart_definition.json")

    with open(json_path, "r") as f:
        empty_highchart_visual = json.load(f)
        empty_highchart_visual["PluginVisual"]["VisualId"] = visual_id

    return empty_highchart_visual


def create_highchart_visual(highchart_parameters):
    """
    Creates a filled out highchart definition with given parameters

    Args:
        highchart_parameters (dictionary): Key-value pairs that hosts all parameters required to generate a highchart

    Returns:
        A filled out higchart JSON object
    """

    assert highchart_parameters is not None, "highchart_parameters cannot be None"

    # Create skeleton
    highchart_object = create_empty_highchart_visual(highchart_parameters["visual_id"])

    # Set in highchart columns (category and value columns)
    highchart_categories = []
    for category_name in highchart_parameters["category_column_names"]:
        highchart_categories.append(
            chart_config.create_category(
                column_name=category_name,
                dataset_id=highchart_parameters["dataset_id"],
                column_type="Categorical",
                date_granularity=highchart_parameters["date_granularity"],
            )
        )

    for date_name in highchart_parameters["date_column_names"]:
        highchart_categories.append(
            chart_config.create_highchart_date(
                column_name=date_name,
                dataset_id=highchart_parameters["dataset_id"],
                date_granularity=highchart_parameters["date_granularity"],
            )
        )

    highchart_values = []
    for i in range(len(highchart_parameters["value_column_names"])):
        highchart_values.append(
            chart_config.create_value(
                column_name=highchart_parameters["value_column_names"][i],
                dataset_id=highchart_parameters["dataset_id"],
                numerical_aggregation=highchart_parameters["value_column_aggregation"][i],
            )
        )

    # Populate skeleton with parameters
    highchart_object["PluginVisual"]["ChartConfiguration"]["FieldWells"][0][
        "Dimensions"
    ] = highchart_categories

    highchart_object["PluginVisual"]["ChartConfiguration"]["FieldWells"][1][
        "Measures"
    ] = highchart_values

    highchart_object["PluginVisual"]["ChartConfiguration"]["VisualOptions"]["VisualProperties"][0][
        "Value"
    ] = json.loads(highchart_parameters["highchart_code"])

    return highchart_object


async def my_update_dashboard_add_highchart(
    dash_id: str,
    dash_name: str,
    sheet_id: str,
    visual_id: str,
    dataset_id: str,
    category_column_names: list[str] = [],
    date_column_names: list[str] = [],
    date_granularity: str = "",
    value_column_names: list[str] = [],
    value_column_aggregation: list[str] = [],
    highchart_code: str = "",
):
    r"""
    Updates an existing dashboard to add a highchart visual

    An example highchart code: "\"{\\\"chart\\\":{\\\"type\\\":\\\"line\\\"},\\\"title\\\":{\\\"text\\\":\\\"Sales by Region\\\"},\\\"xAxis\\\":{\\\"categories\\\":[\\\"getColumnFromGroupBy\\\",0],\\\"title\\\":{\\\"text\\\":\\\"Region\\\"}},\\\"yAxis\\\":{\\\"title\\\":{\\\"text\\\":\\\"Sales ($)\\\"}},\\\"series\\\":[{\\\"name\\\":\\\"Sales\\\",\\\"data\\\":[\\\"getColumnFromValue\\\",0]}]}\""
    When generating code, make sure to use column arithmetics and not point-wise operations
    Add another double quote in the front and the end of the code to make sure it is passed as a string.
    For the category types use getColumnFromGroupBy.
    For the value type use getColumnFromValue.
    COLUMN ARITHMETIC PATTERNS:
        - For basic data access: ["getColumnFromGroupBy", 0] for categories, ["getColumnFromValue", 0] for values
        - For mapping over data: ["map", ["getColumnFromGroupBy", 0], {...}] to iterate through category values
        - For creating data points with names: {"name": ["item"], "value": ["get", ["getColumnFromValue", 0], ["itemIndex"]]}
        - For unique values: ["unique", ["getColumnFromGroupBy", 0]] to get distinct category values
        - Use ["item"] to reference current iteration item, ["itemIndex"] for current index
    PACKED BUBBLE CHART REQUIREMENTS:
        - Chart type: "packedbubble"
        - Data structure must use mapping to associate names with values
        - Correct series format: [{"name": "SeriesName", "data": ["map", ["getColumnFromGroupBy", 0], {"name": ["item"], "value": ["get", ["getColumnFromValue", 0], ["itemIndex"]]}]}]
        - Tooltip format: Use {point.name} for category names and {point.value} for values
        - Data labels format: Use {point.name} to display category names on bubbles
    CHART TYPE EXAMPLES:
        - Line Chart: {"chart": {"type": "line"}, "series": [{"data": ["getColumnFromValue", 0]}]}
        - Bubble Chart: {"chart": {"type": "bubble"}, "series": [{"data": ["map", ["getColumnFromGroupBy", 0], {"name": ["item"], "x": ["itemIndex"], "y": ["get", ["getColumnFromValue", 0], ["itemIndex"]], "z": ["get", ["getColumnFromValue", 0], ["itemIndex"]]}]}]}
        - Packed Bubble: {"chart": {"type": "packedbubble"}, "series": [{"data": ["map", ["getColumnFromGroupBy", 0], {"name": ["item"], "value": ["get", ["getColumnFromValue", 0], ["itemIndex"]]}]}]}
    TOOLTIP AND LABEL CONFIGURATION:
        - Always use {point.name} to display category names from the dataset
        - Use {point.value} for packed bubbles, {point.y} or {point.z} for regular bubbles
        - Format tooltips with HTML for better presentation: "useHTML": true
        - Include proper formatting for numbers: {point.value:,.0f} for currency/large numbers
    COMMON ISSUES AND SOLUTIONS:
        - If bubbles show generic names instead of category names: Ensure proper data mapping with ["map", ["getColumnFromGroupBy", 0], {...}]
        - If chart shows no data: Verify column arithmetic syntax and ensure data structure matches chart type requirements
        - If tooltips don't show category names: Use {point.name} instead of {series.name} in tooltip format
        - For packed bubbles specifically: Use "value" property in data points, not "y" or "z"
    STRING ESCAPING RULES:
        - Wrap entire JSON in double quotes and escape internal quotes with \"
        - For nested quotes in tooltips: Use \\\" for proper escaping
        - Example: "\"tooltip\":{\"pointFormat\":\"<b>{point.name}</b>: ${point.value:,.0f}\"}"

    Args:
        dash_id: ID of the dashboard to add highchart visual
        dash_name: Name of the dashboard to be updated to
        sheet_id: ID of the sheet to add highchart visual
        visual_id: ID of newly created highchart visual
        dataset_id: ID of the dataset to create highchart from
        category_column_names: A list of column names you wish to add to highcharts. Columns listed here should have the type STRING in the dataset. If the type of the column is DATETIME, add to date_column_names. If the type of the column is INTEGER or DECIMAL, add to value_column_names
        date_column_names: A list of column names you wish to add to highcharts. Columns listed here should have the type DATETIME in the dataset. If the type of the column is STRING add to category_column_names. If the type of the column is INTEGER or DECIMAL, add to value_column_names
        value_column_names: A list of column names you wish to add to highcharts. Columns listed here should have the type INTEGER or DECIMAL in the dataset. If the type of the column is STRING add to category_column_names. If the type of the column is DATETIME, add to date_column_names.
        value_column_aggregation: Function to aggregate the value data. Options: SUM, AVERAGE, MIN, MAX, COUNT, DISTINCT_COUNT, VAR, VARP, STDEV, STDEVP, MEDIAN. For each element in value_column_name, there should be a corresponding aggregation function. Use SUM unless otherwise specified.
        highchart_code: Source code that creates the highchart visual in string format
    Returns:
        Status of update dashboard
    """

    assert dash_id is not None, "dash_id cannot be None"
    assert dash_name is not None, "dash_name cannot be None"
    assert sheet_id is not None, "sheet_id cannot be None"
    assert visual_id is not None, "visual_id cannot be None"
    assert dataset_id is not None, "dataset_id cannot be None"
    assert category_column_names is not None, "category_column_names cannot be None"
    assert date_column_names is not None, "date_column_names cannot be None"
    assert date_granularity is not None, "date_granularity cannot be None"
    assert value_column_names is not None, "value_column_names cannot be None"
    assert value_column_aggregation is not None, "value_column_aggregation cannot be None"
    assert len(value_column_names) == len(
        value_column_aggregation
    ), "Length mismatch. Each value column needs an aggregation function"
    assert highchart_code is not None, "highchart_code cannot be None"

    # Get the current dashboard definition[Visual]
    visuals = qs.get_current_visuals(dash_id, sheet_id)

    # Set parameters to create highcharts
    highchart_parameters = {
        "visual_id": visual_id,
        "dataset_id": dataset_id,
        "category_column_names": category_column_names,
        "date_column_names": date_column_names,
        "date_granularity": date_granularity,
        "value_column_names": value_column_names,
        "value_column_aggregation": value_column_aggregation,
        "highchart_code": highchart_code,
    }

    # Create new highchart object
    new_highchart = create_highchart_visual(highchart_parameters)

    # Append to list of visual objects
    visuals.append(new_highchart)

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
    mcp_server.tool()(my_update_dashboard_add_highchart)