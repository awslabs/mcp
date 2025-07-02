# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for workflow-related tools."""

import base64
import io
import pytest
import zipfile
from awslabs.aws_healthomics_mcp_server.tools.helper_tools import package_workflow
from unittest.mock import AsyncMock, patch


# Test data for workflow packaging
SAMPLE_WDL_WORKFLOW = """version 1.0

workflow HelloWorld {
    call hello_world
}

task hello_world {
    command {
        echo "Hello World!"
    }
    output {
        String message = stdout()
    }
}
"""

ADDITIONAL_TASK_FILE = """task additional_task {
    command {
        echo "Additional task"
    }
    output {
        String result = stdout()
    }
}
"""

SAMPLE_CWL_WORKFLOW = """cwlVersion: v1.0
class: Workflow
inputs:
  message: string
outputs:
  output:
    type: string
    outputSource: hello/output
steps:
  hello:
    run: hello.cwl
    in:
      message: message
    out: [output]
"""


@pytest.mark.asyncio
async def test_package_workflow_basic():
    """Test basic workflow packaging with just main file."""
    mock_ctx = AsyncMock()

    # Call the function directly with values, not Field objects
    result = await package_workflow(
        ctx=mock_ctx,
        main_file_content=SAMPLE_WDL_WORKFLOW,
        main_file_name='main.wdl',
        additional_files=None,  # Explicitly pass None for optional parameter
    )

    # Verify result is a base64 string
    assert isinstance(result, str)

    # Decode base64 string
    zip_data = base64.b64decode(result)

    # Read ZIP contents
    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        # Check file list
        assert len(zf.namelist()) == 1
        assert 'main.wdl' in zf.namelist()

        # Check file content
        with zf.open('main.wdl') as f:
            content = f.read().decode('utf-8')
            assert content == SAMPLE_WDL_WORKFLOW


@pytest.mark.asyncio
async def test_package_workflow_with_additional_files():
    """Test workflow packaging with additional files."""
    mock_ctx = AsyncMock()

    additional_files = {
        'tasks/additional.wdl': ADDITIONAL_TASK_FILE,
        'config/params.json': '{"param1": "value1"}',
    }

    result = await package_workflow(
        ctx=mock_ctx,
        main_file_content=SAMPLE_WDL_WORKFLOW,
        main_file_name='main.wdl',
        additional_files=additional_files,
    )

    # Decode base64 string
    zip_data = base64.b64decode(result)

    # Read ZIP contents
    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        # Check file list
        assert len(zf.namelist()) == 3
        assert 'main.wdl' in zf.namelist()
        assert 'tasks/additional.wdl' in zf.namelist()
        assert 'config/params.json' in zf.namelist()

        # Check main file content
        with zf.open('main.wdl') as f:
            content = f.read().decode('utf-8')
            assert content == SAMPLE_WDL_WORKFLOW

        # Check additional file content
        with zf.open('tasks/additional.wdl') as f:
            content = f.read().decode('utf-8')
            assert content == ADDITIONAL_TASK_FILE

        # Check config file content
        with zf.open('config/params.json') as f:
            content = f.read().decode('utf-8')
            assert content == '{"param1": "value1"}'


@pytest.mark.asyncio
async def test_package_workflow_default_filename():
    """Test workflow packaging with default filename."""
    mock_ctx = AsyncMock()

    result = await package_workflow(
        ctx=mock_ctx,
        main_file_content=SAMPLE_WDL_WORKFLOW,
        main_file_name='main.wdl',  # Explicitly provide default value
        additional_files=None,
    )

    # Decode base64 string
    zip_data = base64.b64decode(result)

    # Read ZIP contents
    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        # Check default filename is used
        assert 'main.wdl' in zf.namelist()


@pytest.mark.asyncio
async def test_package_workflow_cwl_file():
    """Test workflow packaging with CWL file."""
    mock_ctx = AsyncMock()

    result = await package_workflow(
        ctx=mock_ctx,
        main_file_content=SAMPLE_CWL_WORKFLOW,
        main_file_name='workflow.cwl',
        additional_files=None,
    )

    # Decode base64 string
    zip_data = base64.b64decode(result)

    # Read ZIP contents
    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        # Check file list
        assert len(zf.namelist()) == 1
        assert 'workflow.cwl' in zf.namelist()

        # Check file content
        with zf.open('workflow.cwl') as f:
            content = f.read().decode('utf-8')
            assert content == SAMPLE_CWL_WORKFLOW


@pytest.mark.asyncio
async def test_package_workflow_with_subdirectories():
    """Test workflow packaging with nested directory structure."""
    mock_ctx = AsyncMock()

    additional_files = {
        'tasks/subtasks/helper.wdl': "task helper { command { echo 'helper' }}",
        'tasks/main_task.wdl': "task main { command { echo 'main' }}",
        'configs/dev/params.json': '{"env": "dev"}',
        'configs/prod/params.json': '{"env": "prod"}',
    }

    result = await package_workflow(
        ctx=mock_ctx,
        main_file_content=SAMPLE_WDL_WORKFLOW,
        main_file_name='main.wdl',
        additional_files=additional_files,
    )

    # Decode base64 string
    zip_data = base64.b64decode(result)

    # Read ZIP contents
    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        # Check file list
        assert len(zf.namelist()) == 5
        assert 'main.wdl' in zf.namelist()
        assert 'tasks/subtasks/helper.wdl' in zf.namelist()
        assert 'tasks/main_task.wdl' in zf.namelist()
        assert 'configs/dev/params.json' in zf.namelist()
        assert 'configs/prod/params.json' in zf.namelist()

        # Verify directory structure is preserved
        assert any(name.startswith('tasks/subtasks/') for name in zf.namelist())
        assert any(name.startswith('configs/dev/') for name in zf.namelist())
        assert any(name.startswith('configs/prod/') for name in zf.namelist())


@pytest.mark.asyncio
async def test_package_workflow_empty_additional_files():
    """Test workflow packaging with empty additional files dict."""
    mock_ctx = AsyncMock()

    result = await package_workflow(
        ctx=mock_ctx,
        main_file_content=SAMPLE_WDL_WORKFLOW,
        main_file_name='main.wdl',
        additional_files={},  # Empty dict instead of None
    )

    # Decode base64 string
    zip_data = base64.b64decode(result)

    # Read ZIP contents
    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        # Should only contain main file
        assert len(zf.namelist()) == 1
        assert 'main.wdl' in zf.namelist()


@pytest.mark.asyncio
async def test_package_workflow_error_handling():
    """Test error handling in package_workflow."""
    mock_ctx = AsyncMock()

    # Mock create_zip_file to raise an exception - patch it in the helper_tools module
    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.helper_tools.create_zip_file'
    ) as mock_create_zip:
        mock_create_zip.side_effect = Exception('ZIP creation failed')

        with pytest.raises(Exception, match='ZIP creation failed'):
            await package_workflow(
                ctx=mock_ctx,
                main_file_content=SAMPLE_WDL_WORKFLOW,
                main_file_name='main.wdl',
                additional_files=None,
            )

        # Verify error was reported to context
        mock_ctx.error.assert_called_once()
        assert 'Error packaging workflow' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_package_workflow_large_files():
    """Test workflow packaging with large file content."""
    mock_ctx = AsyncMock()

    # Create a large workflow content
    large_content = SAMPLE_WDL_WORKFLOW + '\n# ' + 'x' * 10000

    result = await package_workflow(
        ctx=mock_ctx,
        main_file_content=large_content,
        main_file_name='large.wdl',
        additional_files=None,
    )

    # Decode base64 string
    zip_data = base64.b64decode(result)

    # Read ZIP contents
    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        # Check file content
        with zf.open('large.wdl') as f:
            content = f.read().decode('utf-8')
            assert content == large_content
            assert len(content) > 10000


@pytest.mark.asyncio
async def test_package_workflow_special_characters():
    """Test workflow packaging with special characters in content."""
    mock_ctx = AsyncMock()

    special_content = """version 1.0
workflow SpecialChars {
    String unicode_test = "Hello 世界! 🌍"
    String symbols = "Special chars: @#$%^&*()[]{}|\\:;\"'<>,.?/~`"
}
"""

    result = await package_workflow(
        ctx=mock_ctx,
        main_file_content=special_content,
        main_file_name='special.wdl',
        additional_files=None,
    )

    # Decode base64 string
    zip_data = base64.b64decode(result)

    # Read ZIP contents
    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        # Check file content with special characters
        with zf.open('special.wdl') as f:
            content = f.read().decode('utf-8')
            assert content == special_content
            assert '世界' in content
            assert '🌍' in content
