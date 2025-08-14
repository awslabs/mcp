import json
import os

import sys
from pathlib import Path

awslabs_dir = Path(__file__).parent.parent.parent
sys.path.append(str(awslabs_dir))

import aws_quicksight_dashboards_mcp_server.resources.chart_configuration_helper as chart_config
import aws_quicksight_dashboards_mcp_server.quicksight as qs


def create_empty_table_visual(visual_id: str):
    """
    Creates an empty table visual with the given visual ID.

    Args:
        visual_id (str): The ID of the visual to be created.

    Returns:
        Skeleton definition of table visual
    """

    assert visual_id is not None, "visual cannot be None"

    empty_table_visual = None

    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "json_definitions", "table_definition.json")

    with open(json_path, "r") as f:
        empty_table_visual = json.load(f)
        empty_table_visual["TableVisual"]["VisualId"] = visual_id

    return empty_table_visual


def create_table_visual(table_parameters):
    """
    Creates a filled out table with given parameters

    Args:
        table_parameters (dictionary): Key-value pairs that hosts all parameters required to generate a table

    Returns:
        A filled out table JSON object
    """

    assert table_parameters is not None, "table_parameters cannot be None"

    # Create skeleton
    table_object = create_empty_table_visual(table_parameters["visual_id"])

    # Create parameter based JSON objects
    category_columns = []
    for category_name in table_parameters["category_column_names"]:
        category_columns.append(
            chart_config.create_category(
                column_name=category_name,
                dataset_id=table_parameters["dataset_id"],
                column_type="Categorical",
            )
        )

    for date_name in table_parameters["date_column_names"]:
        category_columns.append(
            chart_config.create_category(
                column_name=date_name,
                dataset_id=table_parameters["dataset_id"],
                column_type="Date",
                date_granularity=table_parameters["date_granularity"],
            )
        )

    value_columns = []
    for i in range(len(table_parameters["value_column_names"])):
        value_columns.append(
            chart_config.create_value(
                column_name=table_parameters["value_column_names"][i],
                dataset_id=table_parameters["dataset_id"],
                numerical_aggregation=table_parameters["value_column_aggregation"][i],
            )
        )

    # Populate Skeleton with parameters
    table_object["TableVisual"]["ChartConfiguration"]["FieldWells"]["TableAggregatedFieldWells"][
        "GroupBy"
    ] = category_columns

    table_object["TableVisual"]["ChartConfiguration"]["FieldWells"]["TableAggregatedFieldWells"][
        "Values"
    ] = value_columns

    return table_object


async def my_update_dashboard_add_table(
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
):
    """
    Updates an existing dashboard to add a table visual

    Args:
        dash_id: ID of the dashboard to add the table visual
        dash_name: Name of the dashboard to be updated to
        sheet_id: ID of the sheet to add the table visual
        visual_id: ID of the new table
        dataset_id: ID of the dataset to create table from
        category_column_names: A list of column names you wish to insert into the table. Columns listed here should have the type STRING in the dataset. If the type of the column is DATETIME, add to date_column_names. If the type of the column is INTEGER or DECIMAL, add to value_column_names
        date_column_names: A list of column names you wish to insert into the table. Columns listed here should have the type DATETIME in the dataset. If the type of the column is STRING add to category_column_names. If the type of the column is INTEGER or DECIMAL, add to value_column_names
        date_granularity: Granularity for the date column. One of YEAR, QUARTER, MONTH, WEEK, DAY, HOUR, MINUTE, SECOND. Only provide this granularity if there is a date_column_names.
        value_column_names: A list of column names you wish to insert into the table. Columns listed here should have the type INTEGER or DECIMAL in the dataset. If the type of the column is STRING add to category_column_names. If the type of the column is DATETIME, add to date_column_names.
        value_column_aggregation: Function to aggregate the value data. Options: SUM, AVERAGE, MIN, MAX, COUNT, DISTINCT_COUNT, VAR, VARP, STDEV, STDEVP, MEDIAN. For each element in value_column_name, there should be a corresponding aggregation function. Use SUM unless otherwise specified.
    Returns:
        Status of update dashboard
        After calling this function, call update_dashboard_add_visual_layout.
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

    # Get the current dashboard definition[Visual]
    visuals = qs.get_current_visuals(dash_id, sheet_id)

    # Set parameters to create the table
    table_parameters = {
        "visual_id": visual_id,
        "dataset_id": dataset_id,
        "category_column_names": category_column_names,
        "date_column_names": date_column_names,
        "date_granularity": date_granularity,
        "value_column_names": value_column_names,
        "value_column_aggregation": value_column_aggregation,
    }

    # Create new table object
    new_table = create_table_visual(table_parameters)

    # Append to list of visual objects
    visuals.append(new_table)

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
    mcp_server.tool()(my_update_dashboard_add_table)
