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

import argparse
import re
import sys
import time
from ..core.aws.services import driver
from ..core.kb.dense_retriever import (
    DEFAULT_CACHE_DIR,
    DEFAULT_EMBEDDING_MODEL,
    KNOWLEDGE_BASE_SUFFIX,
    DenseRetriever,
)
from ..core.parser.parser import (
    DENIED_CUSTOM_SERVICES,
    is_denied_custom_operation,
)
from awscli.bcdoc.restdoc import ReSTDocument
from awscli.clidriver import ServiceCommand
from awscli.clidriver import __version__ as awscli_version
from awscli.customizations.commands import BasicCommand
from loguru import logger
from pathlib import Path
from typing import Any


IGNORED_ARGUMENTS = frozenset({'cli-input-json', 'generate-cli-skeleton'})


def _clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    return text.strip()


def _clean_description(description: str) -> str:
    """This removes the section title added by the help event handlers."""
    description = re.sub(r'=+\s*Description\s*=+\s', '', description)
    return _clean_text(description)


def _generate_operation_document(
    service_name: str, operation_name: str, operation: Any
) -> dict[str, Any] | None:
    """Generate a document for a single AWS API operation."""
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


def _get_aws_api_documents() -> list[dict[str, Any]]:
    documents = []
    for service_name, command in driver._get_command_table().items():
        if service_name in DENIED_CUSTOM_SERVICES:
            continue
        try:
            if isinstance(command, BasicCommand):
                command_table = command.subcommand_table
            elif isinstance(command, ServiceCommand):
                command_table = command._get_command_table()
            else:
                logger.warning(f'Unknown command type {service_name} {command}')
                continue

            for operation_name, operation in command_table.items():
                if is_denied_custom_operation(service_name, operation_name):
                    # skip so we don't suggest these and later fail to execute
                    continue

                documents.append(
                    _generate_operation_document(service_name, operation_name, operation)
                )
        except Exception:
            logger.warning(f'Failed to generate document for {service_name}.', exc_info=True)
            continue

    return documents


def generate_embeddings(model_name: str, cache_dir: Path, overwrite: bool):
    """Generate embeddings for AWS API commands and save them to a cache file."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f'{KNOWLEDGE_BASE_SUFFIX}-{awscli_version}.npz'

    if cache_file.exists():
        if not overwrite:
            logger.info(
                f'Embeddings are already generated and cached: {cache_file}. Use --overwrite to regenerate.'
            )
            return
        else:
            logger.info(f'Overwriting existing cached embeddings: {cache_file}')

    documents = _get_aws_api_documents()
    logger.info(f'Collected {len(documents)} documents.')

    logger.info(f'Embedding generation started with model: {model_name}')
    start_time = time.time()
    retriever = DenseRetriever(model_name=model_name, cache_dir=cache_dir)
    retriever.generate_index(documents)
    elapsed_time = time.time() - start_time
    logger.info(f'Generated embeddings in {elapsed_time:.2f} seconds.')

    retriever.save_to_cache()
    logger.info(f'Embeddings are saved to: {cache_file}')


def main():
    """Driver for the generate embeddings util."""
    parser = argparse.ArgumentParser(description='Argument parser for model loading')
    parser.add_argument(
        '--model-name',
        type=str,
        default=DEFAULT_EMBEDDING_MODEL,
        help='Name or path of the model to load',
    )
    parser.add_argument(
        '--cache-dir',
        type=str,
        default=DEFAULT_CACHE_DIR,
        help='Directory to use for caching models',
    )
    parser.add_argument(
        '--overwrite', action='store_true', help='Overwrite existing cached files (default: False)'
    )
    args = parser.parse_args()
    generate_embeddings(args.model_name, Path(args.cache_dir), args.overwrite)


if __name__ == '__main__':
    # Configure Loguru logging
    logger.remove()
    logger.add(sys.stderr)

    main()
