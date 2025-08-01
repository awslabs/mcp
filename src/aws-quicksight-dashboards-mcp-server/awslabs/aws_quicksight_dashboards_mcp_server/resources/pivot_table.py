import json
import os

import sys
from pathlib import Path

awslabs_dir = Path(__file__).parent.parent.parent
sys.path.append(str(awslabs_dir))

import aws_quicksight_dashboards_mcp_server.resources.chart_configuration_helper as chart_config
import aws_quicksight_dashboards_mcp_server.quicksight as qs


def create_empty_pivot_table_visual(visual_id: str):
    """
    Creates an empty pivot table visual with the given visual ID.

    Args:
        visual_id (str): The ID of the visual to be created.

    Returns:
        Skeleton definition of pivot table visual
    """

    assert visual_id is not None, "visual cannot be None"

    empty_table_visual = None

    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "json_definitions", "pivot_table_definition.json")

    with open(json_path, "r") as f:
        empty_table_visual = json.load(f)
        empty_table_visual["PivotTableVisual"]["VisualId"] = visual_id

    return empty_table_visual


def create_pivot_table_visual(pivot_table_parameters):
    """
    Creates a filled out pivot table with given parameters

    Args:
        pivot_table_parameters (dictionary): Key-value pairs that hosts all parameters required to generate a pivot table

    Returns:
        A filled out pivot table JSON object
    """

    assert pivot_table_parameters is not None, "pivot table parameters cannot be None"

    # Create skeleton
    pivot_table_object = create_empty_pivot_table_visual(pivot_table_parameters["visual_id"])

    # Create parameter based JSON objects
    selected_field_options = []
    field_sort_options = []

    category_columns = []
    for category_name in pivot_table_parameters["category_column_names"]:
        category_columns.append(
            chart_config.create_category(
                column_name=category_name,
                dataset_id=pivot_table_parameters["dataset_id"],
                column_type="Categorical",
            )
        )
        selected_field_options.append(
            chart_config.create_field_options(
                field_id=category_name,
                visibility="VISIBLE",
            )
        )
        field_sort_options.append(
            chart_config.create_field_sort_options(
                field_id=category_name,
                direction="ASC",
            )
        )

    for date_name in pivot_table_parameters["date_column_names"]:
        category_columns.append(
            chart_config.create_category(
                column_name=date_name,
                dataset_id=pivot_table_parameters["dataset_id"],
                column_type="Date",
                date_granularity=pivot_table_parameters["date_granularity"],
            )
        )
        selected_field_options.append(
            chart_config.create_field_options(
                field_id=date_name,
                visibility="VISIBLE",
            )
        )
        field_sort_options.append(
            chart_config.create_field_sort_options(
                field_id=date_name,
                direction="ASC",
            )
        )

    value_columns = []
    for i in range(len(pivot_table_parameters["value_column_names"])):
        value_columns.append(
            chart_config.create_value(
                column_name=pivot_table_parameters["value_column_names"][i],
                dataset_id=pivot_table_parameters["dataset_id"],
                numerical_aggregation=pivot_table_parameters["value_column_aggregation"][i],
            )
        )
        selected_field_options.append(
            chart_config.create_field_options(
                field_id=pivot_table_parameters["value_column_names"][i],
                visibility="VISIBLE",
            )
        )

    # Populate Skeleton with parameters
    pivot_table_object["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
        "PivotTableAggregatedFieldWells"
    ]["Rows"] = category_columns

    pivot_table_object["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
        "PivotTableAggregatedFieldWells"
    ]["Values"] = value_columns

    pivot_table_object["PivotTableVisual"]["ChartConfiguration"]["FieldOptions"][
        "SelectedFieldOptions"
    ] = selected_field_options

    pivot_table_object["PivotTableVisual"]["ChartConfiguration"]["SortConfiguration"][
        "FieldSortOptions"
    ] = field_sort_options

    return pivot_table_object


async def my_update_dashboard_add_pivot_table(
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
    Updates an existing dashboard to add a pivot table visual

    The order of the column names are crucial espcially for the category_column_names. The order determines the nesting order of the columns.
    For example, if the list is populated as ["Country", "City"], the outermost layer will be the list of countries and the cities will be placed within each coutnry.
    However, if the list is populated as ["City", "Country"], the outermost layer will be the list of cities and it's country will be placed within each city.
    You should try to get these order from the user prompt. If there is any unclarity such as when the user does not provide the hierarchy of the columns, prompt the user to provide the hierarchy.

    Args:
        dash_id: ID of the dashboard to add the pivot table visual
        dash_name: Name of the dashboard to be updated to
        sheet_id: ID of the sheet to add the pivot table visual
        visual_id: ID of the new pivot table
        dataset_id: ID of the dataset to create pivot table from
        category_column_names: A list of column names you wish to insert into the pivot table. Columns listed here should have the type STRING in the dataset. If the type of the column is DATETIME, add to date_column_names. If the type of the column is INTEGER or DECIMAL, add to value_column_names
        date_column_names: A list of column names you wish to insert into the pivot table. Columns listed here should have the type DATETIME in the dataset. If the type of the column is STRING add to category_column_names. If the type of the column is INTEGER or DECIMAL, add to value_column_names
        date_granularity: Granularity for the date column. One of YEAR, QUARTER, MONTH, WEEK, DAY, HOUR, MINUTE, SECOND. Only provide this granularity if there is a date_column_names.
        value_column_names: A list of column names you wish to insert into the pivot table. Columns listed here should have the type INTEGER or DECIMAL in the dataset. If the type of the column is STRING add to category_column_names. If the type of the column is DATETIME, add to date_column_names.
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

    # Set parameters to create the pivot table
    pivot_table_parameters = {
        "visual_id": visual_id,
        "dataset_id": dataset_id,
        "category_column_names": category_column_names,
        "date_column_names": date_column_names,
        "date_granularity": date_granularity,
        "value_column_names": value_column_names,
        "value_column_aggregation": value_column_aggregation,
    }

    # Create new table object
    new_pivot_table = create_pivot_table_visual(pivot_table_parameters)

    # Append to list of visual objects
    visuals.append(new_pivot_table)

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


async def update_pivot_table_edit_calculation(
    dash_id: str,
    dash_name: str,
    sheet_id: str,
    visual_id: str,
    value_col: str,
    calc_type: str,
    agg_type: str,
    by_group: bool,
):
    """
    Updates an existing dashboard to edit a pivot table visual by adding or editing a calculated column.
    Use this function if you want to add or change a calculation of a value column

    Args:
        dash_id: ID of the dashboard to edit the pivot table visual
        dash_name: Name of the dashboard to be updated to
        sheet_id: ID of the sheet where the pivot table is located
        visual_id: ID of the pivot table
        value_col: ID of the column to calculate
        calc_type: Type of calculation to perform: One of Running_Total, Difference, Percentage_Difference, Percent_of_Total, Rank, Percentile
        agg_type: Aggregation type to apply to the value column: One of Sum, Avg, Count, Max, Median, Min
        by_group: True if you want to calculate by the group. False if you want to calculate by the table
    Returns:
        Status of update dashboard
    """
    visuals = qs.get_current_visuals(dash_id, sheet_id)

    # Find the pivot table visual
    pivot_table = None
    for visual in visuals:
        if "PivotTableVisual" in visual:
            if visual["PivotTableVisual"]["VisualId"] == visual_id:
                pivot_table = visual
                break

    assert pivot_table is not None, "Pivot table does not exist in the dashboard sheet yet"

    # If the value column already exists, remove the column
    visual_values = pivot_table["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
        "PivotTableAggregatedFieldWells"
    ]["Values"]
    # Use index to preserve order of table columns
    original_index = -1
    for i in range(len(visual_values)):
        if "CalculatedMeasureField" in visual_values[i]:
            if visual_values[i]["CalculatedMeasureField"]["FieldId"] == value_col:
                visual_values.remove(visual_values[i])
                original_index = i
                break
        else:
            if visual_values[i]["NumericalMeasureField"]["FieldId"] == value_col:
                visual_values.remove(visual_values[i])
                original_index = i
                break

    # Automatically find group
    group = ""
    visual_categories = pivot_table["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
        "PivotTableAggregatedFieldWells"
    ]["Rows"]
    if visual_categories == []:  # The data is stored in column-wise table
        visual_categories = pivot_table["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
            "PivotTableAggregatedFieldWells"
        ]["Columns"]

    if by_group:
        # Group is always the 2nd to last of the categories. If there is only 1 category, there is no group to apply
        if len(visual_categories) >= 2:
            if "CategoricalDimensionField" in visual_categories[-2]:
                group = visual_categories[-2]["CategoricalDimensionField"]["FieldId"]
            elif "DateDimensionField" in visual_categories[-2]:
                group = visual_categories[-2]["DateDimensionField"]["FieldId"]

    # Find column names of all the categories
    visual_category_names = []
    for column in visual_categories:
        if "CategoricalDimensionField" in column:
            visual_category_names.append(
                column["CategoricalDimensionField"]["Column"]["ColumnName"]
            )
        elif "DateDimensionField" in column:
            visual_category_names.append(column["DateDimensionField"]["Column"]["ColumnName"])

    calc_field = chart_config.create_calculated_field(
        value_col, calc_type, agg_type, group, visual_category_names
    )
    visual_values.insert(original_index, calc_field)

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
    # return {"update_result": dash_update_res, "publish_result": publish_res}


async def update_pivot_table_change_orientation(
    dash_id: str,
    dash_name: str,
    sheet_id: str,
    visual_id: str,
):
    """
    Updates an existing pivot table by changing the orientation.
    Row-wise table becomes column-wise table and column-wise table becomes row-wise table

    Args:
        dash_id: ID of the dashboard to update the pivot table
        dash_name: Name of the dashboard to update the pivot table. Use this parameter to change the name of the dashboard
        sheet_id: ID of the sheet where the pivot table is located
        visual_id: ID of the pivot table to rotate
    Returns:
        Status of update dashboard
    """
    visuals = qs.get_current_visuals(dash_id, sheet_id)

    # Find the pivot table visual
    pivot_table = None
    for visual in visuals:
        if "PivotTableVisual" in visual:
            if visual["PivotTableVisual"]["VisualId"] == visual_id:
                pivot_table = visual
                break

    assert pivot_table is not None, "Pivot table does not exist in the dashboard sheet yet"

    # Change the orientation
    (
        pivot_table["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
            "PivotTableAggregatedFieldWells"
        ]["Rows"],
        pivot_table["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
            "PivotTableAggregatedFieldWells"
        ]["Columns"],
    ) = (
        pivot_table["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
            "PivotTableAggregatedFieldWells"
        ]["Columns"],
        pivot_table["PivotTableVisual"]["ChartConfiguration"]["FieldWells"][
            "PivotTableAggregatedFieldWells"
        ]["Rows"],
    )

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
    mcp_server.tool()(my_update_dashboard_add_pivot_table)
    mcp_server.tool()(update_pivot_table_edit_calculation)
    mcp_server.tool()(update_pivot_table_change_orientation)
