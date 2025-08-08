import json
import os
import time

import boto3

session = boto3.Session() #Add profile name here 

# Get correct client endpoint
client = session.client(
    "quicksight",
    region_name="us-east-1",
)


# Get account ID; this is set in cline_mcp_settings.json
def get_account_id():
    """Get AWS account ID from environment or default for testing"""
    return os.environ.get("AWS_ACCOUNT_ID", "123456789012")  # Default for tests


def get_user_name():
    """Get AWS user name from environment or default for testing"""
    return os.environ.get("AWS_USERNAME", "test_username")


# Use this function instead of direct access
ACCOUNT_ID = get_account_id()
USERNAME = get_user_name()


def get_current_visuals(dash_id: str, sheet_id: str):
    """
    Returns the current visual elements of the dashboard

    Args:
        dash_id = ID of the dashboard you want to extract current visuals from
        sheet_id = ID of the sheet you want to extract current visuals from
    """

    assert dash_id is not None, "dash_id (dashboard ID) cannot be None"
    assert sheet_id is not None, "sheet_id (sheet ID) cannot be None"

    dashboard_definition_response = client.describe_dashboard_definition(
        AwsAccountId=ACCOUNT_ID, DashboardId=dash_id
    )

    sheets = dashboard_definition_response["Definition"]["Sheets"]
    for sheet in sheets:
        if sheet["SheetId"] == sheet_id:
            return sheet["Visuals"]


def get_current_layouts(dash_id: str, sheet_id: str):
    """
    Returns the current layout elements of the dashboard

    Args:
        dash_id = ID of the dashboard you want to extract current layouts from
        sheet_id = ID of the sheet you want to extract current layouts from
    """

    assert dash_id is not None, "dash_id (dashboard ID) cannot be None"
    assert sheet_id is not None, "sheet_id (sheet ID) cannot be None"

    dashboard_definition_response = client.describe_dashboard_definition(
        AwsAccountId=ACCOUNT_ID, DashboardId=dash_id
    )

    sheets = dashboard_definition_response["Definition"]["Sheets"]
    for sheet in sheets:
        if sheet["SheetId"] == sheet_id:
            return sheet["Layouts"][0]["Configuration"]["GridLayout"]["Elements"]


def get_current_dashboard_definition(dash_id: str):
    """
    Returns definition JSON object (like dictionary) of the dashboard

    Args:
        dash_id = ID of the dashboard you want to extract current visuals from
    """

    assert dash_id is not None, "dash_id (dashboard ID) cannot be None"

    dashboard_definition_response = client.describe_dashboard_definition(
        AwsAccountId=ACCOUNT_ID, DashboardId=dash_id
    )

    return dashboard_definition_response["Definition"]


def update_visual(dash_id: str, sheet_id: str, new_visuals: list):
    """
    Overwrites the visual components with new visual list

    Returns:
        Updated definition
    """

    assert dash_id is not None, "dash_id (dashboard ID) cannot be None"
    assert sheet_id is not None, "sheet_id (sheet ID) cannot be None"
    assert new_visuals is not None, "new_visuals (a list of visuals to be applied) cannot be None"

    definition = get_current_dashboard_definition(dash_id)
    sheets = definition["Sheets"]
    for sheet in sheets:
        if sheet["SheetId"] == sheet_id:
            sheet["Visuals"] = new_visuals

    return definition


def update_layout(dash_id: str, sheet_id: str, new_bar_chart_layout: list):
    """
    Overwrites the layout components with new layout list

    Returns:
        Updated definition
    """

    assert dash_id is not None, "dash_id (dashboard ID) cannot be None"
    assert sheet_id is not None, "sheet_id (sheet ID) cannot be None"
    assert (
        new_bar_chart_layout is not None
    ), "new_bar_chart_layout (a list of layouts to be applied) cannot be None"

    definition = get_current_dashboard_definition(dash_id)
    sheets = definition["Sheets"]
    for sheet in sheets:
        if sheet["SheetId"] == sheet_id:
            sheet["Layouts"][0]["Configuration"]["GridLayout"]["Elements"] = new_bar_chart_layout

    return definition


def get_dash_version(dash_update_res):
    """
    Returns the version of the dashboard

    Args:
        dash_update_res = Response of the dashboard update
    """

    assert (
        dash_update_res is not None
    ), "dash_update_res (response of dashboard update) cannot be None"

    dashboard_version_arn = dash_update_res["VersionArn"]
    new_dashboard_version = int(dashboard_version_arn.split("/version/")[1])
    return new_dashboard_version


# MCP Tools
async def my_list_dashboards(next_token: str = ""):
    """List all dashboards in the account

    Args:
        next_token: Used to view next set of dashboards
    Returns:
        A list of dashboards
        Run this command again if NextToken is given.
        NextToken will be given if there are more than 100 results and cannot present them in one list.
    """

    assert next_token is not None, "next_token cannot be None"

    dashboard_list = None
    if next_token == "":
        dashboard_list = client.list_dashboards(AwsAccountId=ACCOUNT_ID)
    else:
        dashboard_list = client.list_dashboards(AwsAccountId=ACCOUNT_ID, NextToken=next_token)

    return dashboard_list


async def my_list_datasets(next_token: str = ""):
    """List all datasets in the account

    Args:
        next_token: Used to view next set of datasets
    Returns:
        A list of datasets
        Run this command again if NextToken is given.
        NextToken will be given if there are more than 100 results and cannot present them in one list.
    """

    assert next_token is not None, "next_token cannot be None"

    dataset_list = None
    if next_token == "":
        dataset_list = client.list_data_sets(AwsAccountId=ACCOUNT_ID)
    else:
        dataset_list = client.list_data_sets(AwsAccountId=ACCOUNT_ID, NextToken=next_token)

    return dataset_list


async def my_get_dataset(dataset_id: str):
    """Get a dataset by ID

    Args:
        dataset_id: The ID of the dataset to retrieve.
    """

    assert dataset_id is not None, "dataset_id cannot be None"

    dataset_response = client.describe_data_set(AwsAccountId=ACCOUNT_ID, DataSetId=dataset_id)

    return dataset_response["DataSet"]


async def my_get_dashboard(dashboard_id: str):
    """Get a dashboard by ID

    Args:
        dashboard_id: The ID of the dashboard to retrieve.
    """

    assert dashboard_id is not None, "dashboard_id cannot be None"

    dashboard_response = client.describe_dashboard(
        AwsAccountId=ACCOUNT_ID, DashboardId=dashboard_id
    )

    return dashboard_response["Dashboard"]


async def my_get_dashboard_definition(dash_id: str):
    """
    Returns definition JSON object (like dictionary) of the dashboard

    Args:
        dash_id = ID of the dashboard you want to extract current visuals from
    """

    assert dash_id is not None, "dash_id cannot be None"

    dashboard_definition_response = client.describe_dashboard_definition(
        AwsAccountId=ACCOUNT_ID, DashboardId=dash_id
    )

    return dashboard_definition_response["Definition"]


async def my_create_dashboard_definition(
    dash_id: str, dash_name: str, dataset_id: str, dataset_arn: str
):  # FIXME Current hard codes user arn for permissions
    """Create an empty dashboard with one sheet.

    Args:
        dash_id: ID of the newly created dashboard
        dash_name: The name of the newly created dashboard
        dataset_id: ID of the dataset to create a new dashboard with
        dataset_arn: ARN of the dataset to create a new dashboard with
    """

    assert dash_id is not None, "dash_id cannot be None"
    assert dash_name is not None, "dash_name cannot be None"
    assert dataset_id is not None, "dataset_id cannot be None"
    assert dataset_arn is not None, "dataset_arn cannot be None"

    definition = None
    with open(
        "./resources/json_definitions/empty_dashboard_definition.json",
        "r",
    ) as f:
        definition = json.load(f)

    definition["DataSetIdentifierDeclarations"][0]["Identifier"] = dataset_id
    definition["DataSetIdentifierDeclarations"][0]["DataSetArn"] = dataset_arn

    principal_arn = "arn:aws:quicksight:us-east-1:" + ACCOUNT_ID + ":user/default/" + USERNAME

    dashboard_create_response = client.create_dashboard(
        AwsAccountId=ACCOUNT_ID,
        DashboardId=dash_id,
        Name=dash_name,
        Definition=definition,
        Permissions=[
            {
                "Principal": principal_arn,
                "Actions": [
                    "quicksight:DescribeDashboard",
                    "quicksight:ListDashboardVersions",
                    "quicksight:UpdateDashboardPermissions",
                    "quicksight:QueryDashboard",
                    "quicksight:UpdateDashboard",
                    "quicksight:DeleteDashboard",
                    "quicksight:DescribeDashboardPermissions",
                    "quicksight:UpdateDashboardPublishedVersion",
                ],
            },
        ],
    )

    return dashboard_create_response


async def my_update_dashboard_add_sheet(
    dash_id: str, dash_name: str, sheet_id: str, sheet_name: str
):
    """
    Create a new empty sheet and append the new sheet to a dashboard

    Args:
        dash_id: ID of the dashboard you want to append sheet to
        dash_name: Name of the dashboard you want to append sheet to
        sheet_id: Unique ID of the sheet
        sheet_name: Name of the sheet

    Returns:
        Status of the add sheet operation
    """

    assert dash_id is not None, "dash_id cannot be None"
    assert dash_name is not None, "dash_name cannot be None"
    assert sheet_id is not None, "sheet_id cannot be None"
    assert sheet_name is not None, "sheet_name cannot be None"

    sheet_object = {
        "SheetId": sheet_id,
        "Name": sheet_name,
        "Visuals": [],
        "Layouts": [
            {
                "Configuration": {
                    "GridLayout": {
                        "Elements": [],
                        "CanvasSizeOptions": {
                            "ScreenCanvasSizeOptions": {
                                "ResizeOption": "FIXED",
                                "OptimizedViewPortWidth": "1600px",
                            }
                        },
                    }
                }
            }
        ],
        "ContentType": "INTERACTIVE",
    }

    dashboard_definition = get_current_dashboard_definition(dash_id)
    dashboard_definition["Sheets"].append(sheet_object)

    dash_update_res = client.update_dashboard(
        AwsAccountId=ACCOUNT_ID,
        DashboardId=dash_id,
        Name=dash_name,
        Definition=dashboard_definition,
    )

    new_dashboard_version = get_dash_version(dash_update_res)
    publish_res = await my_update_dashboard_publish(dash_id, new_dashboard_version)
    print(publish_res)

    return dash_update_res


async def my_update_dashboard_remove_sheet(dash_id: str, dash_name: str, sheet_id: str):
    """
    Removes a sheet from a dashboard

    Args:
        dash_id: ID of the dashboard you want to remove sheet from
        dash_name: Name of the dashboard you want to remove sheet from
        sheet_id: ID of the sheet you want to remove

    Returns:
        Status of the remove sheet operation
    """

    assert dash_id is not None, "dash_id cannot be None"
    assert dash_name is not None, "dash_name cannot be None"
    assert sheet_id is not None, "sheet_id cannot be None"

    dashboard_definition = get_current_dashboard_definition(dash_id)
    sheets = dashboard_definition["Sheets"]
    for sheet in sheets:
        if sheet["SheetId"] == sheet_id:
            sheets.remove(sheet)
            break

    dash_update_res = client.update_dashboard(
        AwsAccountId=ACCOUNT_ID,
        DashboardId=dash_id,
        Name=dash_name,
        Definition=dashboard_definition,
    )

    new_dashboard_version = get_dash_version(dash_update_res)
    publish_res = await my_update_dashboard_publish(dash_id, new_dashboard_version)
    print(publish_res)

    return dash_update_res


async def my_update_dashboard_publish(dash_id: str, version_num: int):
    """
    Publishes the updated dashboard

    Args:
        dash_id: ID of the dashboard to publish
        version_num: Version of the dashboard to publish
    """

    assert dash_id is not None, "dash_id cannot be None"
    assert version_num is not None, "version_num cannot be None"

    dash_response = await my_get_dashboard(dash_id)
    creation_status = dash_response["Version"]["Status"]
    max_attempt = 3
    attempt = 0

    while creation_status == "CREATION_IN_PROGRESS" and attempt < max_attempt:
        time.sleep(2**attempt)
        dash_response = await my_get_dashboard(dash_id)
        creation_status = dash_response["Version"]["Status"]
        attempt += 1

    dashboard_publish_response = client.update_dashboard_published_version(
        AwsAccountId=ACCOUNT_ID, DashboardId=dash_id, VersionNumber=version_num
    )

    return dashboard_publish_response


async def my_update_dashboard_remove_visual(
    dash_id: str, dash_name: str, sheet_id: str, visual_type: str, visual_id: str
):
    """
    Updates an existing dashboard to remove a visual
    First call update_dashboard_delete_visual_layout to remove the layout element before removing the visual.
    Once the update_dashboard_delete_visual_layout is complete, call this function.

    Possible Values for visual_type:
                1. BarChartVisual
                2. LineChartVisual
                3. TableVisual
                4. PivotTableVisual
                5. KPIVisual
                6. PluginVisual

    Args:
        dash_id: ID of the dashboard for update
        dash_name: Name of the dashboard
        sheet_id: ID of the sheet to remove the bar chart visual from
        visual_type: Type of the visual you want to remove.
        visual_id: ID of the bar chart to remove

    Returns:
        Status of update dashboard
    """

    assert dash_id is not None, "dash_id cannot be None"
    assert dash_name is not None, "dash_name cannot be None"
    assert sheet_id is not None, "sheet_id cannot be None"
    assert visual_type is not None, "visual_type cannot be None"
    assert visual_id is not None, "visual_id cannot be None"

    # Get the current dashboard definition[Visual]
    visuals = get_current_visuals(dash_id, sheet_id)

    for visual in visuals:
        if visual_type in visual and visual[visual_type]["VisualId"] == visual_id:
            visuals.remove(visual)
            break

    # Overwrite existing visuals with the filtered list
    new_definition = update_visual(dash_id, sheet_id, visuals)
    dash_update_res = client.update_dashboard(
        AwsAccountId=ACCOUNT_ID,
        DashboardId=dash_id,
        Name=dash_name,
        Definition=new_definition,
    )

    new_dashboard_version = get_dash_version(dash_update_res)
    publish_res = await my_update_dashboard_publish(dash_id, new_dashboard_version)
    print(publish_res)

    return dash_update_res


async def my_update_dashboard_add_visual_layout(
    dash_id: str,
    dash_name: str,
    sheet_id: str,
    visual_id: str,
    column_index: int,
    row_index: int,
    column_span: int = 18,
    row_span: int = 12,
):
    """
    Adds a layout element for a visual.
    Adding a layout element will set the visual's position and size.

    Args:
        dash_id: ID of the dashboard to change layout
        dash_name: Name of the dashboard to be updated to
        sheet_id: ID of the sheet to change layout
        visual_id: ID of the visual to change layout
        column_index: The column index for the upper left corner of an element; Min value of 0, Max value of 35
        row_index: The row index for the upper left corner of an element; Min value of 0, Max value of 9009
        column_span: Width of a grid element expressed as a number of grid columns; Min value of 1, Max value of 36; column_span of 18 typically takes about 1/4 of the sheet
        row_span: Height of grid element expressed as a number of grid rows; Min value of 1, Max value of 21. row_span of 12 typically takes about 1/4 of the sheet

    Returns:
        Status of layout update in dashboard
    """

    assert dash_id is not None, "dash_id cannot be None"
    assert dash_name is not None, "dash_name cannot be None"
    assert sheet_id is not None, "sheet_id cannot be None"
    assert visual_id is not None, "visual_id cannot be None"
    assert column_index is not None, "column_index cannot be None"
    assert row_index is not None, "row_index cannot be None"
    assert column_span is not None, "column_span cannot be None"
    assert row_span is not None, "row_span cannot be None"

    layouts = get_current_layouts(dash_id, sheet_id)

    # Create new layout element for bar chart object
    new_layout_element = {
        "ElementId": visual_id,
        "ElementType": "VISUAL",
        "ColumnSpan": column_span,
        "RowSpan": row_span,
        "ColumnIndex": column_index,
        "RowIndex": row_index,
    }

    layouts.append(new_layout_element)

    # Overwrite existing layout
    new_definition = update_layout(dash_id, sheet_id, layouts)

    dash_update_res = client.update_dashboard(
        AwsAccountId=ACCOUNT_ID,
        DashboardId=dash_id,
        Name=dash_name,
        Definition=new_definition,
    )

    new_dashboard_version = get_dash_version(dash_update_res)
    publish_res = await my_update_dashboard_publish(dash_id, new_dashboard_version)
    print(publish_res)

    return dash_update_res


async def my_update_dashboard_delete_visual_layout(
    dash_id: str,
    dash_name: str,
    sheet_id: str,
    visual_id: str,
):
    """
    Removes a layout element for a visual.

    Args:
        dash_id: ID of the dashboard to delete layout element
        dash_name: Name of the dashboard to be updated to
        sheet_id: ID of the sheet to delete layout element
        visual_id: ID of the visual layout element to delete

    Returns:
        Status of layout update in dashboard
    """

    assert dash_id is not None, "dash_id cannot be None"
    assert dash_name is not None, "dash_name cannot be None"
    assert sheet_id is not None, "sheet_id cannot be None"
    assert visual_id is not None, "visual_id cannot be None"

    layouts = get_current_layouts(dash_id, sheet_id)

    for layout in layouts:
        if layout["ElementId"] == visual_id:
            layouts.remove(layout)
            break

    # Overwrite existing layout
    new_definition = update_layout(dash_id, sheet_id, layouts)

    dash_update_res = client.update_dashboard(
        AwsAccountId=ACCOUNT_ID,
        DashboardId=dash_id,
        Name=dash_name,
        Definition=new_definition,
    )

    new_dashboard_version = get_dash_version(dash_update_res)
    publish_res = await my_update_dashboard_publish(dash_id, new_dashboard_version)
    print(publish_res)

    return dash_update_res


def register_tool(mcp_server):
    mcp_server.tool()(my_list_dashboards)
    mcp_server.tool()(my_list_datasets)
    mcp_server.tool()(my_get_dataset)
    mcp_server.tool()(my_get_dashboard)
    mcp_server.tool()(my_get_dashboard_definition)
    mcp_server.tool()(my_create_dashboard_definition)
    mcp_server.tool()(my_update_dashboard_add_sheet)
    mcp_server.tool()(my_update_dashboard_remove_sheet)
    mcp_server.tool()(my_update_dashboard_publish)
    mcp_server.tool()(my_update_dashboard_remove_visual)
    mcp_server.tool()(my_update_dashboard_add_visual_layout)
    mcp_server.tool()(my_update_dashboard_delete_visual_layout)
