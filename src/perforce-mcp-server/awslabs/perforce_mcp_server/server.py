# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""awslabs perforce MCP Server implementation."""

import argparse
import json
import os
import re
import subprocess
from loguru import logger
from mcp.server.fastmcp import FastMCP
from typing import Dict, Optional


mcp = FastMCP(
    'awslabs.perforce-mcp-server',
    instructions='Instructions for using this perforce MCP server. This can be used by clients to improve the LLM'
    's understanding of available tools, resources, etc. It can be thought of like a '
    'hint'
    ' to the model. For example, this information MAY be added to the system prompt. Important to be clear, direct, and detailed.',
    dependencies=[
        'pydantic',
        'loguru',
    ],
)


@mcp.tool(name='ListFiles')
async def list_files(path: str, changelist: Optional[str] = None) -> Dict:
    """List files in a Perforce depot path.

    Args:
        path (str): Perforce depot path (e.g., //depot/project/...)
        changelist (str, optional): Specific changelist to list files from

    Returns:
        Dict: Information about files in the specified path
    """
    try:
        cmd = ['p4', 'files', path]
        if changelist:
            cmd.extend(['@' + changelist])

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        files = result.stdout.strip().split('\n')
        return {'files': files, 'count': len(files)}
    except Exception as e:
        return {'error': str(e)}


@mcp.tool(name='GetFile')
async def get_file(file_path: str, revision: Optional[str] = None) -> Dict:
    """Get the content of a file from Perforce.

    Args:
        file_path (str): Path to the file in Perforce depot
        revision (str, optional): Specific revision to retrieve

    Returns:
        Dict: File content
    """
    try:
        cmd = ['p4', 'print', '-q']
        if revision:
            cmd.append(f'{file_path}#{revision}')
        else:
            cmd.append(file_path)

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            return {'content': result.stdout}
        else:
            return {'error': result.stderr}
    except Exception as e:
        return {'error': str(e)}


@mcp.tool(name='CheckOut')
async def check_out(file_path: str, changelist: Optional[str] = None) -> Dict:
    """Check out a file from Perforce for editing.

    Args:
        file_path (str): Path to the file in Perforce depot
        changelist (str, optional): Changelist to add the file to

    Returns:
        Dict: Status of the checkout operation
    """
    try:
        cmd = ['p4', 'edit']
        if changelist:
            cmd.extend(['-c', changelist])
        cmd.append(file_path)

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            return {'message': f'Successfully checked out {file_path}', 'output': result.stdout}
        else:
            return {'error': result.stderr}
    except Exception as e:
        return {'error': str(e)}


@mcp.tool(name='SubmitChanges')
async def submit_changes(changelist: str, description: str) -> Dict:
    """Submit changes to Perforce.

    Args:
        changelist (str): Changelist number to submit
        description (str): Description for the changelist

    Returns:
        Dict: Status of the submit operation
    """
    try:
        # Create a temporary file for the description
        desc_file = f'/tmp/p4_desc_{os.getpid()}.txt'
        with open(desc_file, 'w') as f:
            f.write(description)

        # Submit the changelist
        cmd = ['p4', 'submit', '-c', changelist, '-d', f'@{desc_file}']
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Clean up
        if os.path.exists(desc_file):
            os.remove(desc_file)

        if result.returncode == 0:
            return {
                'message': f'Successfully submitted changelist {changelist}',
                'output': result.stdout,
            }
        else:
            return {'error': result.stderr}
    except Exception as e:
        return {'error': str(e)}


@mcp.tool(name='CreateChangelist')
async def create_changelist(description: str) -> Dict:
    """Create a new Perforce changelist.

    Args:
        description (str): Description for the new changelist

    Returns:
        Dict: Information about the created changelist
    """
    try:
        # Create a temporary file for the description
        desc_file = f'/tmp/p4_change_{os.getpid()}.txt'
        with open(desc_file, 'w') as f:
            f.write(f'Change: new\n\nDescription:\n\t{description}\n\n')

        # Create the changelist
        cmd = ['p4', 'change', '-i', '<', desc_file]
        result = subprocess.run(' '.join(cmd), shell=True, capture_output=True, text=True)

        # Clean up
        if os.path.exists(desc_file):
            os.remove(desc_file)

        if result.returncode == 0:
            # Extract the changelist number from the output
            output = result.stdout
            changelist_num = None
            if 'Change' in output and 'created' in output:
                import re

                match = re.search(r'Change (\d+) created', output)
                if match:
                    changelist_num = match.group(1)

            return {
                'message': 'Changelist created successfully',
                'changelist': changelist_num,
                'output': output,
            }
        else:
            return {'error': result.stderr}
    except Exception as e:
        return {'error': str(e)}


@mcp.tool(name='ListChangelists')
async def list_changelists(
    user: Optional[str] = None, status: Optional[str] = None, max_count: int = 10
) -> Dict:
    """List Perforce changelists.

    Args:
        user (str, optional): Filter by specific user
        status (str, optional): Filter by status (pending, submitted, shelved)
        max_count (int, optional): Maximum number of changelists to return. Defaults to 10.

    Returns:
        Dict: List of changelists
    """
    try:
        cmd = ['p4', 'changes', '-l', '-m', str(max_count)]

        if user:
            cmd.extend(['-u', user])

        if status:
            if status.lower() == 'pending':
                cmd.append('-p')
            elif status.lower() == 'shelved':
                cmd.append('-s')
            # For submitted, no flag is needed as it's the default

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            changelists = result.stdout.strip().split('\n\n')
            parsed_changelists = []

            for cl in changelists:
                if not cl.strip():
                    continue

                cl_info = {}
                lines = cl.strip().split('\n')

                # Parse the first line which contains change number, user, date, etc.
                if lines and lines[0].startswith('Change '):
                    header = lines[0].split()
                    cl_info['number'] = header[1]
                    cl_info['status'] = header[3] if len(header) > 3 else 'unknown'

                    # Extract user from "by username@client"
                    if 'by' in lines[0]:
                        user_part = lines[0].split('by ')[1].split()[0]
                        cl_info['user'] = user_part.split('@')[0]
                        cl_info['client'] = user_part.split('@')[1] if '@' in user_part else ''

                # Extract description
                desc_start = False
                description = []
                for line in lines[1:]:
                    if line.strip().startswith('Description:'):
                        desc_start = True
                        continue
                    if desc_start:
                        description.append(line.strip())

                cl_info['description'] = '\n'.join(description)
                parsed_changelists.append(cl_info)

            return {'changelists': parsed_changelists, 'count': len(parsed_changelists)}
        else:
            return {'error': result.stderr}
    except Exception as e:
        return {'error': str(e)}


@mcp.tool(name='Sync')
async def sync(path: Optional[str] = None, force: bool = False) -> Dict:
    """Sync files from Perforce.

    Args:
        path (str, optional): Path to sync. If not provided, syncs the entire client workspace.
        force (bool, optional): Force sync even if files are up to date. Defaults to False.

    Returns:
        Dict: Status of the sync operation
    """
    try:
        cmd = ['p4', 'sync']

        if force:
            cmd.append('-f')

        if path:
            cmd.append(path)

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            return {'message': 'Sync completed successfully', 'output': result.stdout}
        else:
            return {'error': result.stderr}
    except Exception as e:
        return {'error': str(e)}


@mcp.tool(name='CreateDepot')
async def create_depot(
    depot_name: str, depot_type: str = 'local', description: str = '', stream_depth: int = 1
) -> Dict:
    """Create a new Perforce depot.

    Args:
        depot_name (str): Name for the new depot
        depot_type (str, optional): Type of depot to create (local, stream, remote, etc.). Defaults to "local".
        description (str, optional): Description for the depot. Defaults to empty string.
        stream_depth (int, optional): Depth for stream depots (required when depot_type is "stream"). Value must be between 1-10. Defaults to 1.

    Returns:
        Dict: Status of the depot creation operation
    """
    try:
        # Validate stream_depth is between 1-10 for stream depots
        if depot_type.lower() == 'stream' and not 1 <= stream_depth <= 10:
            return {'error': 'StreamDepth must be between 1 and 10 for stream depots'}

        # Create a temporary file for the depot specification
        spec_file = f'/tmp/p4_depot_{os.getpid()}.txt'

        # Build the depot specification content
        spec_content = [
            f'Depot: {depot_name}',
            f'Type: {depot_type}',
            f'Description: {description}',
            f'Map: {depot_name}/...',
        ]

        # Add StreamDepth for stream depots with proper format
        if depot_type.lower() == 'stream':
            spec_content.append(f'StreamDepth: //{depot_name}/{stream_depth}')

        # Write the specification to the temporary file
        with open(spec_file, 'w') as f:
            f.write('\n'.join(spec_content) + '\n')

        # Create the depot using the specification
        cmd = f'p4 depot -i < {spec_file}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        # Clean up
        if os.path.exists(spec_file):
            os.remove(spec_file)

        if result.returncode == 0:
            return {
                'message': f"Successfully created depot '{depot_name}'",
                'output': result.stdout,
                'depot_name': depot_name,
                'depot_type': depot_type,
                'stream_depth': stream_depth if depot_type.lower() == 'stream' else None,
            }
        else:
            return {'error': result.stderr}
    except Exception as e:
        return {'error': str(e)}


@mcp.tool(name='CreateStream')
async def create_stream(
    stream_name: str,
    parent_stream: Optional[str] = None,
    stream_type: str = 'development',
    description: str = '',
) -> Dict:
    """Create a new Perforce stream.

    Args:
        stream_name (str): Full name of the stream (e.g., //depot/stream)
        parent_stream (str, optional): Parent stream path. If not provided, creates a mainline stream.
        stream_type (str, optional): Type of stream (mainline, development, release, virtual, task). Defaults to "development".
        description (str, optional): Description for the stream. Defaults to empty string.

    Returns:
        Dict: Status of the stream creation operation
    """
    try:
        # Create a temporary file for the stream specification
        spec_file = f'/tmp/p4_stream_{os.getpid()}.txt'

        # Get the depot name from the stream name
        if not stream_name.startswith('//'):
            return {'error': 'Stream name must start with // (e.g., //depot/stream)'}

        parts = stream_name.split('/')
        if len(parts) < 3:
            return {'error': 'Invalid stream name format. Expected format: //depot/stream'}

        # Create the stream specification with ParentView field
        stream_spec = f"""Stream: {stream_name}
Owner: {os.environ.get('USER', 'perforce')}
Name: {stream_name.split('/')[-1]}
Parent: {parent_stream if parent_stream else 'none'}
Type: {stream_type}
Description: {description}
Options: allsubmit unlocked notoparent nofromparent mergedown
ParentView: inherit
Paths:
\tshare ...
"""

        # Write the specification to the temporary file
        with open(spec_file, 'w') as f:
            f.write(stream_spec)

        # Create the stream using the specification
        cmd = ['p4', 'stream', '-i', '<', spec_file]
        result = subprocess.run(' '.join(cmd), shell=True, capture_output=True, text=True)

        # Clean up
        if os.path.exists(spec_file):
            os.remove(spec_file)

        if result.returncode == 0:
            return {
                'message': f"Successfully created stream '{stream_name}'",
                'output': result.stdout,
                'stream_name': stream_name,
                'stream_type': stream_type,
                'parent_stream': parent_stream if parent_stream else 'none',
            }
        else:
            return {'error': result.stderr}
    except Exception as e:
        return {'error': str(e)}


@mcp.tool(name='ListStreams')
async def list_streams(
    depot_name: Optional[str] = None, stream_type: Optional[str] = None, max_count: int = 20
) -> Dict:
    """List Perforce streams.

    Args:
        depot_name (str, optional): Filter streams by depot name
        stream_type (str, optional): Filter by stream type (mainline, development, release, virtual, task)
        max_count (int, optional): Maximum number of streams to return. Defaults to 20.

    Returns:
        Dict: List of streams
    """
    try:
        cmd = ['p4', 'streams', '-m', str(max_count)]

        if depot_name:
            cmd.append(f'//{depot_name}/...')

        if stream_type:
            cmd.extend(['-t', stream_type])

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            streams = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 3:
                        stream_info = {
                            'stream': parts[0],
                            'type': parts[1],
                            'parent': parts[2] if parts[2] != 'none' else None,
                        }
                        streams.append(stream_info)

            return {'streams': streams, 'count': len(streams)}
        else:
            return {'error': result.stderr}
    except Exception as e:
        return {'error': str(e)}


@mcp.tool(name='DeleteDepot')
async def delete_depot(depot_name: str) -> Dict:
    """Delete a Perforce depot.

    Args:
        depot_name (str): Name of the depot to delete

    Returns:
        Dict: Status of the depot deletion operation
    """
    try:
        # Execute the depot deletion command
        cmd = ['p4', 'depot', '-d', depot_name]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            return {
                'message': f"Successfully deleted depot '{depot_name}'",
                'output': result.stdout,
            }
        else:
            return {'error': result.stderr}
    except Exception as e:
        return {'error': str(e)}


@mcp.tool(name='DeleteStream')
async def delete_stream(stream_name: str, force: bool = False, obliterate: bool = False) -> Dict:
    """Delete a Perforce stream.

    Args:
        stream_name (str): Full name of the stream to delete (e.g., //depot/stream)
        force (bool, optional): Force deletion even if the stream has clients. Defaults to False.
        obliterate (bool, optional): Completely remove the stream from metadata. Defaults to False.

    Returns:
        Dict: Status of the stream deletion operation
    """
    try:
        # Always use the --obliterate flag to completely remove the stream
        # This ensures streams are fully removed from the database
        cmd = ['p4', 'stream', '--obliterate', '-y', stream_name]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            return {
                'message': f"Successfully obliterated stream '{stream_name}'",
                'output': result.stdout,
            }
        else:
            # If obliterate fails, try standard deletion as fallback
            cmd = ['p4', 'stream', '-d']

            if force:
                cmd.append('-f')

            cmd.append(stream_name)

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                return {
                    'message': f"Successfully deleted stream '{stream_name}'",
                    'output': result.stdout,
                }
            else:
                # If the stream has clients and force is not enabled
                if 'has active clients' in result.stderr and not force:
                    # Get the list of clients using this stream
                    clients_cmd = ['p4', 'clients', '-S', stream_name]
                    clients_result = subprocess.run(clients_cmd, capture_output=True, text=True)

                    if clients_result.returncode == 0:
                        clients = []
                        for line in clients_result.stdout.strip().split('\n'):
                            if line.strip():
                                client_name = line.split()[1]
                                clients.append(client_name)

                        return {
                            'error': result.stderr,
                            'clients': clients,
                            'message': 'Stream has active clients. Use force=True to delete the stream and its clients.',
                        }

                return {'error': result.stderr}
    except Exception as e:
        return {'error': str(e)}


@mcp.tool(name='ListDepots')
async def list_depots() -> Dict:
    """List all Perforce depots.

    Returns:
        Dict: List of all depots with their types and descriptions
    """
    try:
        # Execute the command to list all depots
        cmd = ['p4', 'depots']
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            depots = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        depot_info = {'name': parts[0], 'type': parts[1]}

                        # Get detailed information for each depot
                        detail_cmd = ['p4', 'depot', '-o', parts[0]]
                        detail_result = subprocess.run(detail_cmd, capture_output=True, text=True)

                        if detail_result.returncode == 0:
                            # Extract description from the detailed output
                            description = ''
                            for detail_line in detail_result.stdout.strip().split('\n'):
                                if detail_line.startswith('Description:'):
                                    description = detail_line.replace('Description:', '').strip()
                                    break

                            depot_info['description'] = description

                        depots.append(depot_info)

            return {'depots': depots, 'count': len(depots)}
        else:
            return {'error': result.stderr}
    except Exception as e:
        return {'error': str(e)}


@mcp.resource('http://perforce/info')
def get_perforce_info() -> Dict:
    """Get information about the Perforce installation and connection.

    Returns:
        Dict: Perforce version and connection information
    """
    try:
        # Get Perforce version
        version_cmd = ['p4', '-V']
        version_result = subprocess.run(version_cmd, capture_output=True, text=True)

        # Get Perforce connection info
        info_cmd = ['p4', 'info']
        info_result = subprocess.run(info_cmd, capture_output=True, text=True)

        return {
            'version': version_result.stdout.strip(),
            'connection_info': info_result.stdout.strip(),
            'status': 'active' if info_result.returncode == 0 else 'error',
        }
    except Exception as e:
        return {'error': str(e)}


@mcp.tool(name='ConnectToServer')
async def connect_to_server(
    config_file: Optional[str] = None,
    server: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
) -> Dict:
    """Connect to a Perforce server using configuration from a file or direct parameters.

    Args:
        config_file (str, optional): Path to a text file containing Perforce server details
        server (str, optional): Perforce server address (e.g., ssl:hostname:1666)
        user (str, optional): Perforce username
        password (str, optional): Perforce password

    Returns:
        Dict: Status of the connection operation
    """
    try:
        # If config file is provided, parse it to extract server details
        if config_file:
            with open(config_file, 'r') as f:
                content = f.read()

                # Extract server address
                server_match = re.search(r'server:\s*(ssl:[^:\s]+:\d+)', content)
                if server_match:
                    server = server_match.group(1)
                else:
                    # Try alternative format with IP directly mentioned
                    ip_match = re.search(r'Public IP\s*-\s*([0-9.]+)', content)
                    if ip_match:
                        ip = ip_match.group(1)
                        server = f'ssl:{ip}:1666'  # Assuming standard SSL port

                # Extract username
                user_match = re.search(r'user:\s*(\w+)', content)
                if user_match:
                    user = user_match.group(1)

                # Extract password
                password_match = re.search(r'(?:password|First-password)\s*-\s*([^\s]+)', content)
                if password_match:
                    password = password_match.group(1)

        # Validate that we have the necessary information
        if not server:
            return {'error': 'Server address not found in config file or provided as parameter'}

        if not user:
            return {'error': 'Username not found in config file or provided as parameter'}

        # Set P4PORT environment variable
        os.environ['P4PORT'] = server

        # Set P4USER environment variable
        os.environ['P4USER'] = user

        # Test the connection
        cmd = ['p4', 'info']
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            # If password is provided, try to log in
            if password:
                # Create a temporary file for the password
                pwd_file = f'/tmp/p4_pwd_{os.getpid()}.txt'
                with open(pwd_file, 'w') as f:
                    f.write(password)

                # Login using the password file
                login_cmd = f'p4 login < {pwd_file}'
                login_result = subprocess.run(
                    login_cmd, shell=True, capture_output=True, text=True
                )

                # Clean up
                if os.path.exists(pwd_file):
                    os.remove(pwd_file)

                if login_result.returncode != 0:
                    return {
                        'status': 'connected_but_login_failed',
                        'server': server,
                        'user': user,
                        'connection_info': result.stdout,
                        'login_error': login_result.stderr,
                    }

            return {
                'status': 'connected',
                'server': server,
                'user': user,
                'connection_info': result.stdout,
            }
        else:
            return {
                'status': 'connection_failed',
                'server': server,
                'user': user,
                'error': result.stderr,
            }
    except Exception as e:
        return {'error': str(e)}


@mcp.tool(name='CreateClientWorkspace')
async def create_client_workspace(
    depot_name: str,
    client_name: Optional[str] = None,
    root_dir: Optional[str] = None,
    stream_path: Optional[str] = None,
    description: str = '',
) -> Dict:
    """Create a client workspace for a specified Perforce depot.

    Args:
        depot_name (str): Name of the depot to create a client workspace for
        client_name (str, optional): Name for the client workspace. If not provided, uses username_depot_name
        root_dir (str, optional): Root directory for the client workspace. If not provided, uses current directory
        stream_path (str, optional): Full path to the stream (e.g., //depot/main). Required for stream workspaces
        description (str, optional): Description for the client workspace

    Returns:
        Dict: Status of the client workspace creation
    """
    try:
        # Get current user
        user_cmd = ['p4', 'user', '-o']
        user_result = subprocess.run(user_cmd, capture_output=True, text=True)

        if user_result.returncode != 0:
            return {'error': f'Failed to get user information: {user_result.stderr}'}

        # Extract username from the output
        username = None
        for line in user_result.stdout.split('\n'):
            if line.startswith('User:'):
                username = line.split()[1].strip()
                break

        if not username:
            return {'error': 'Could not determine Perforce username'}

        # Set default client name if not provided
        if not client_name:
            client_name = f'{username}_{depot_name}_client'

        # Set default root directory if not provided
        if not root_dir:
            root_dir = os.getcwd()

        # Create a temporary file for the client specification
        spec_file = f'/tmp/p4_client_{os.getpid()}.txt'

        # Build the client specification
        client_spec = [
            f'Client: {client_name}',
            f'Owner: {username}',
            f'Description: {description or f"Client workspace for {depot_name} depot"}',
            f'Root: {root_dir}',
            'Options: noallwrite noclobber nocompress unlocked nomodtime normdir noaltsync',
            'SubmitOptions: submitunchanged',
            'LineEnd: local',
        ]

        # Add stream mapping if provided
        if stream_path:
            client_spec.append(f'Stream: {stream_path}')
        else:
            # Add standard view mapping for non-stream clients
            client_spec.append('View:')
            client_spec.append(f'\t//{depot_name}/... //{client_name}/...')

        # Write the specification to the temporary file
        with open(spec_file, 'w') as f:
            f.write('\n'.join(client_spec) + '\n')

        # Create the client using the specification
        cmd = f'p4 client -i < {spec_file}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        # Clean up
        if os.path.exists(spec_file):
            os.remove(spec_file)

        if result.returncode == 0:
            # Set the P4CLIENT environment variable to the new client
            os.environ['P4CLIENT'] = client_name

            return {
                'message': f"Successfully created client workspace '{client_name}'",
                'output': result.stdout,
                'client_name': client_name,
                'root_directory': root_dir,
                'depot': depot_name,
                'stream': stream_path,
            }
        else:
            return {'error': result.stderr}
    except Exception as e:
        return {'error': str(e)}


@mcp.tool(name='AddAllFilesToDepot')
async def add_all_files_to_depot(
    local_folder: str, depot_path: str, description: str = 'Add files to depot'
) -> Dict:
    """Copy all files from a local folder to a Perforce depot.

    Args:
        local_folder (str): Path to the local folder containing files to add
        depot_path (str): Target path in the Perforce depot (e.g., //depot/main)
        description (str, optional): Description for the changelist. Defaults to "Add files to depot".

    Returns:
        Dict: Status of the add operation
    """
    try:
        # Validate inputs
        if not os.path.isdir(local_folder):
            return {'status': 'error', 'error': f'Local folder does not exist: {local_folder}'}

        # Create a changelist for the add operation
        change_file = f'/tmp/p4_change_{os.getpid()}.txt'
        with open(change_file, 'w') as f:
            f.write(f'Change: new\n\nDescription:\n\t{description}\n\n')

        change_cmd = f'p4 change -i < {change_file}'
        change_result = subprocess.run(change_cmd, shell=True, capture_output=True, text=True)

        # Clean up the change file
        if os.path.exists(change_file):
            os.remove(change_file)

        if change_result.returncode != 0:
            return {
                'status': 'error',
                'error': f'Failed to create changelist: {change_result.stderr}',
            }

        # Extract the changelist number
        changelist_num = None
        if 'Change' in change_result.stdout and 'created' in change_result.stdout:
            match = re.search(r'Change (\d+) created', change_result.stdout)
            if match:
                changelist_num = match.group(1)

        if not changelist_num:
            return {'status': 'error', 'error': 'Failed to extract changelist number'}

        # Get the current client workspace
        info_cmd = ['p4', 'info']
        info_result = subprocess.run(info_cmd, capture_output=True, text=True)

        if info_result.returncode != 0:
            return {
                'status': 'error',
                'error': f'Failed to get Perforce info: {info_result.stderr}',
            }

        client_name = None
        for line in info_result.stdout.split('\n'):
            if line.startswith('Client name:'):
                client_name = line.split(':', 1)[1].strip()
                break

        if not client_name:
            return {'status': 'error', 'error': 'Failed to determine client workspace name'}

        # Get client workspace mapping
        client_cmd = ['p4', 'client', '-o', client_name]
        client_result = subprocess.run(client_cmd, capture_output=True, text=True)

        if client_result.returncode != 0:
            return {
                'status': 'error',
                'error': f'Failed to get client workspace info: {client_result.stderr}',
            }

        # Get client root directory
        client_root = None
        for line in client_result.stdout.split('\n'):
            if line.startswith('Root:'):
                client_root = line.split(':', 1)[1].strip()
                break

        if not client_root:
            return {
                'status': 'error',
                'error': 'Failed to determine client workspace root directory',
            }

        # Determine the relative path from client root to local folder
        try:
            # Convert both paths to absolute paths
            abs_local_folder = os.path.abspath(local_folder)
            abs_client_root = os.path.abspath(client_root)

            # Check if local folder is within client root
            if not abs_local_folder.startswith(abs_client_root):
                # If not, we need to copy files to client workspace first
                temp_dir = os.path.join(client_root, 'temp_add_files')
                os.makedirs(temp_dir, exist_ok=True)

                # Copy files to temp directory in client workspace
                copy_cmd = f'cp -r {abs_local_folder}/* {temp_dir}/'
                copy_result = subprocess.run(copy_cmd, shell=True, capture_output=True, text=True)

                if copy_result.returncode != 0:
                    return {
                        'status': 'error',
                        'error': f'Failed to copy files to client workspace: {copy_result.stderr}',
                    }

                # Use the temp directory for adding files
                target_dir = temp_dir
                rel_path = os.path.relpath(temp_dir, abs_client_root)
            else:
                # Use the original directory
                target_dir = abs_local_folder
                rel_path = os.path.relpath(abs_local_folder, abs_client_root)
        except Exception as e:
            return {'status': 'error', 'error': f'Failed to determine relative path: {str(e)}'}

        # Ensure depot path ends with /...
        if not depot_path.endswith('/...'):
            if depot_path.endswith('/'):
                depot_path += '...'
            else:
                depot_path += '/...'

        # Add files to Perforce
        add_cmd = ['p4', 'add', '-c', changelist_num, '-f', os.path.join(target_dir, '...')]
        add_result = subprocess.run(add_cmd, capture_output=True, text=True)

        if add_result.returncode != 0:
            return {
                'status': 'error',
                'error': f'Failed to add files: {add_result.stderr}',
                'changelist': changelist_num,
            }

        # Count added files
        added_files = []
        for line in add_result.stdout.split('\n'):
            if line.strip() and 'opened for add' in line:
                added_files.append(line.strip())

        # Submit the changelist
        submit_cmd = ['p4', 'submit', '-c', changelist_num]
        submit_result = subprocess.run(submit_cmd, capture_output=True, text=True)

        if submit_result.returncode != 0:
            return {
                'status': 'error',
                'error': f'Failed to submit changelist: {submit_result.stderr}',
                'changelist': changelist_num,
                'files_added': len(added_files),
            }

        # Clean up temp directory if created
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            cleanup_cmd = f'rm -rf {temp_dir}'
            subprocess.run(cleanup_cmd, shell=True)

        return {
            'status': 'success',
            'message': f'Successfully added files from {local_folder} to {depot_path}',
            'files_added': len(added_files),
            'changelist': changelist_num,
            'output': submit_result.stdout,
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


@mcp.tool(name='DeleteAllFilesFromStream')
async def delete_all_files_from_stream(
    stream_path: str, description: str = 'Delete all files from stream'
) -> Dict:
    """Delete all files from a specified Perforce stream.

    Args:
        stream_path (str): Full path to the stream (e.g., //depot/main)
        description (str, optional): Description for the changelist. Defaults to "Delete all files from stream".

    Returns:
        Dict: Status of the deletion operation
    """
    try:
        # First, list all files in the stream
        list_cmd = ['p4', 'files', f'{stream_path}/...']
        list_result = subprocess.run(list_cmd, capture_output=True, text=True)

        if list_result.returncode != 0:
            return {'status': 'error', 'error': f'Failed to list files: {list_result.stderr}'}

        files = list_result.stdout.strip().split('\n')
        if not files or (len(files) == 1 and not files[0].strip()):
            return {
                'status': 'success',
                'message': 'No files found in the stream',
                'files_deleted': 0,
            }

        # Create a changelist for the deletion
        change_file = f'/tmp/p4_change_{os.getpid()}.txt'
        with open(change_file, 'w') as f:
            f.write(f'Change: new\n\nDescription:\n\t{description}\n\n')

        change_cmd = f'p4 change -i < {change_file}'
        change_result = subprocess.run(change_cmd, shell=True, capture_output=True, text=True)

        # Clean up the change file
        if os.path.exists(change_file):
            os.remove(change_file)

        if change_result.returncode != 0:
            return {
                'status': 'error',
                'error': f'Failed to create changelist: {change_result.stderr}',
            }

        # Extract the changelist number
        changelist_num = None
        if 'Change' in change_result.stdout and 'created' in change_result.stdout:
            match = re.search(r'Change (\d+) created', change_result.stdout)
            if match:
                changelist_num = match.group(1)

        if not changelist_num:
            return {'status': 'error', 'error': 'Failed to extract changelist number'}

        # Mark all files for deletion
        delete_cmd = ['p4', 'delete', '-c', changelist_num, f'{stream_path}/...']
        delete_result = subprocess.run(delete_cmd, capture_output=True, text=True)

        if delete_result.returncode != 0:
            return {
                'status': 'error',
                'error': f'Failed to mark files for deletion: {delete_result.stderr}',
            }

        # Submit the changelist
        submit_cmd = ['p4', 'submit', '-c', changelist_num]
        submit_result = subprocess.run(submit_cmd, capture_output=True, text=True)

        if submit_result.returncode != 0:
            return {
                'status': 'error',
                'error': f'Failed to submit changelist: {submit_result.stderr}',
                'changelist': changelist_num,
            }

        return {
            'status': 'success',
            'message': f'Successfully deleted all files from {stream_path}',
            'files_deleted': len(files),
            'changelist': changelist_num,
            'output': submit_result.stdout,
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


@mcp.tool(name='AddSingleFile')
async def add_single_file(
    file_path: str, depot_path: str, description: str = 'Add single file to depot'
) -> Dict:
    """Add a single file to Perforce.

    Args:
        file_path (str): Path to the local file to add
        depot_path (str): Target path in the Perforce depot (e.g., //depot/main/file.txt)
        description (str, optional): Description for the changelist. Defaults to "Add single file to depot".

    Returns:
        Dict: Status of the add operation
    """
    try:
        # Validate inputs
        if not os.path.isfile(file_path):
            return {'status': 'error', 'error': f'Local file does not exist: {file_path}'}

        # Create a changelist for the add operation
        change_file = f'/tmp/p4_change_{os.getpid()}.txt'
        with open(change_file, 'w') as f:
            f.write(f'Change: new\n\nDescription:\n\t{description}\n\n')

        change_cmd = f'p4 change -i < {change_file}'
        change_result = subprocess.run(change_cmd, shell=True, capture_output=True, text=True)

        # Clean up the change file
        if os.path.exists(change_file):
            os.remove(change_file)

        if change_result.returncode != 0:
            return {
                'status': 'error',
                'error': f'Failed to create changelist: {change_result.stderr}',
            }

        # Extract the changelist number
        changelist_num = None
        if 'Change' in change_result.stdout and 'created' in change_result.stdout:
            match = re.search(r'Change (\d+) created', change_result.stdout)
            if match:
                changelist_num = match.group(1)

        if not changelist_num:
            return {'status': 'error', 'error': 'Failed to extract changelist number'}

        # Get the current client workspace
        info_cmd = ['p4', 'info']
        info_result = subprocess.run(info_cmd, capture_output=True, text=True)

        if info_result.returncode != 0:
            return {
                'status': 'error',
                'error': f'Failed to get Perforce info: {info_result.stderr}',
            }

        client_name = None
        for line in info_result.stdout.split('\n'):
            if line.startswith('Client name:'):
                client_name = line.split(':', 1)[1].strip()
                break

        if not client_name:
            return {'status': 'error', 'error': 'Failed to determine client workspace name'}

        # Get client workspace mapping
        client_cmd = ['p4', 'client', '-o', client_name]
        client_result = subprocess.run(client_cmd, capture_output=True, text=True)

        if client_result.returncode != 0:
            return {
                'status': 'error',
                'error': f'Failed to get client workspace info: {client_result.stderr}',
            }

        # Get client root directory
        client_root = None
        for line in client_result.stdout.split('\n'):
            if line.startswith('Root:'):
                client_root = line.split(':', 1)[1].strip()
                break

        if not client_root:
            return {
                'status': 'error',
                'error': 'Failed to determine client workspace root directory',
            }

        # Determine if the file is already in the client workspace
        abs_file_path = os.path.abspath(file_path)
        abs_client_root = os.path.abspath(client_root)

        if not abs_file_path.startswith(abs_client_root):
            # File is outside client workspace, need to copy it
            file_name = os.path.basename(file_path)
            target_path = os.path.join(client_root, file_name)

            # Copy the file to client workspace
            copy_cmd = f'cp {abs_file_path} {target_path}'
            copy_result = subprocess.run(copy_cmd, shell=True, capture_output=True, text=True)

            if copy_result.returncode != 0:
                return {
                    'status': 'error',
                    'error': f'Failed to copy file to client workspace: {copy_result.stderr}',
                }

            # Use the copied file for adding
            file_to_add = target_path
        else:
            # File is already in client workspace
            file_to_add = abs_file_path

        # Add the file to Perforce
        add_cmd = ['p4', 'add', '-c', changelist_num, file_to_add]
        add_result = subprocess.run(add_cmd, capture_output=True, text=True)

        if add_result.returncode != 0:
            return {
                'status': 'error',
                'error': f'Failed to add file: {add_result.stderr}',
                'changelist': changelist_num,
            }

        # Submit the changelist
        submit_cmd = ['p4', 'submit', '-c', changelist_num]
        submit_result = subprocess.run(submit_cmd, capture_output=True, text=True)

        if submit_result.returncode != 0:
            return {
                'status': 'error',
                'error': f'Failed to submit changelist: {submit_result.stderr}',
                'changelist': changelist_num,
            }

        # Clean up temporary file if created
        if (
            'target_path' in locals()
            and os.path.exists(target_path)
            and target_path != abs_file_path
        ):
            os.remove(target_path)

        return {
            'status': 'success',
            'message': f'Successfully added file {file_path} to {depot_path}',
            'changelist': changelist_num,
            'output': submit_result.stdout,
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


@mcp.tool(name='ConnectWithSecret')
async def connect_with_secret(
    secret_name: str = 'perforce/credentials', region: str = 'us-east-1'
) -> Dict:
    """Connect to a Perforce server using credentials stored in AWS Secrets Manager.

    Args:
        secret_name (str, optional): Name of the secret in AWS Secrets Manager. Defaults to "perforce/credentials".
        region (str, optional): AWS region where the secret is stored. Defaults to "us-east-1".

    Returns:
        Dict: Status of the connection operation
    """
    try:
        # Get the AWS CLI command to retrieve the secret
        get_secret_cmd = f'aws secretsmanager get-secret-value --secret-id {secret_name} --region {region} --query SecretString --output text'
        secret_result = subprocess.run(get_secret_cmd, shell=True, capture_output=True, text=True)

        if secret_result.returncode != 0:
            return {
                'status': 'error',
                'error': f'Failed to retrieve secret: {secret_result.stderr}',
            }

        # Parse the JSON secret value
        secret_json = json.loads(secret_result.stdout)
        server = secret_json.get('server')
        username = secret_json.get('username')
        password = secret_json.get('password')

        if not all([server, username, password]):
            return {
                'status': 'error',
                'error': 'Secret is missing required fields (server, username, password)',
            }

        # Set P4PORT and P4USER environment variables
        os.environ['P4PORT'] = server
        os.environ['P4USER'] = username

        # Create a temporary file for the password
        pwd_file = f'/tmp/p4_pwd_{os.getpid()}.txt'
        with open(pwd_file, 'w') as f:
            f.write(password)

        # Login using the password file
        login_cmd = f'p4 login < {pwd_file}'
        login_result = subprocess.run(login_cmd, shell=True, capture_output=True, text=True)

        # Clean up
        if os.path.exists(pwd_file):
            os.remove(pwd_file)

        if login_result.returncode != 0:
            return {'status': 'error', 'error': f'Failed to login: {login_result.stderr}'}

        # Test the connection
        info_cmd = ['p4', 'info']
        info_result = subprocess.run(info_cmd, capture_output=True, text=True)

        if info_result.returncode != 0:
            return {'status': 'error', 'error': f'Failed to get server info: {info_result.stderr}'}

        return {
            'status': 'connected',
            'server': server,
            'username': username,
            'connection_info': info_result.stdout,
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for perforce'
    )
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')

    args = parser.parse_args()

    logger.trace('A trace message.')
    logger.debug('A debug message.')
    logger.info('An info message.')
    logger.success('A success message.')
    logger.warning('A warning message.')
    logger.error('An error message.')
    logger.critical('A critical message.')

    # Run server with appropriate transport
    if args.sse:
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        mcp.run()


if __name__ == '__main__':
    main()
