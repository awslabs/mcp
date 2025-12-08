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

import re
from ..parser.parser import driver
from awscli.bcdoc.restdoc import ReSTDocument
from awscli.clidriver import ServiceCommand
from awscli.customizations.commands import BasicCommand
from loguru import logger
from typing import Any


IGNORED_ARGUMENTS = frozenset({'cli-input-json', 'generate-cli-skeleton'})


def _clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    return text.strip()


def _clean_description(description: str) -> str:
    """This removes the section title added by the help event handlers."""
    description = re.sub(r'=+\s*Description\s*=+\s', '', description)
    return _clean_text(description)


def generate_help_document(service_name: str, operation_name: str) -> dict[str, Any] | None:
    """Generate a document for a single AWS API operation."""
    command = driver._get_command_table()[service_name]
    if isinstance(command, BasicCommand):
        command_table = command.subcommand_table
    elif isinstance(command, ServiceCommand):
        command_table = command._get_command_table()
    else:
        logger.warning(f'Unknown command type {service_name} {command}')
        return None

    operation = command_table[operation_name]

    help_command = operation.create_help_command()
    event_handler = help_command.EventHandlerClass(help_command)

    # Get description
    event_handler.doc_description(help_command)
    description = _clean_description(help_command.doc.getvalue().decode('utf-8')).strip()

    # Get parameters
    params = {}
    seen_arg_groups = set()
    for arg_name, arg in help_command.arg_table.items():
        if getattr(arg, '_UNDOCUMENTED', False) or arg_name in IGNORED_ARGUMENTS:
            continue
        if arg.group_name in seen_arg_groups:
            continue
        help_command.doc = ReSTDocument()
        if hasattr(event_handler, 'doc'):
            event_handler.doc = help_command.doc
        event_handler.doc_option(help_command=help_command, arg_name=arg_name)
        key = arg.group_name if arg.group_name else arg_name
        params[key] = _clean_text(help_command.doc.getvalue().decode('utf-8').strip())
        params[key] = params[key][:500] if len(params[key]) > 500 else params[key]
        if arg.group_name:
            # To avoid adding arguments like --disable-rollback and --no-disable-rollback separately
            # we need to make sure a group name is only processed once
            # event_handler.doc_option takes care of mentioning all arguments in a group
            # so we can safely skip the remaining arguments in the group
            seen_arg_groups.add(arg.group_name)

    return {
        'command': f'aws {service_name} {operation_name}',
        'description': description,
        'parameters': params,
    }
