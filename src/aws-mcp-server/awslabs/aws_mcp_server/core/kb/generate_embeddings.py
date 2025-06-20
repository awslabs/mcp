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
import time
from ..aws.services import driver
from .dense_retriever import DEFAULT_CACHE_DIR, DEFAULT_EMBEDDINGS_MODEL, DenseRetriever
from awscli.clidriver import ServiceCommand
from botocore import xform_name
from loguru import logger
from pathlib import Path
from typing import Any


def _to_cli_style(name: str) -> str:
    return xform_name(name).replace('_', '-')


def _clean_text(text: str) -> str:
    text = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    return text.strip()


def _get_aws_api_documents() -> list[dict[str, Any]]:
    documents = []
    for service_name, command in driver._get_command_table().items():
        if not isinstance(command, ServiceCommand):
            continue

        try:
            service_command_table = command._get_command_table()
            for operation_name, operation in service_command_table.items():
                if hasattr(operation, '_operation_model'):
                    model = operation._operation_model
                    description = _clean_text(model.documentation)

                    params = {}
                    if input_shape := model.input_shape:
                        for param_name, member in input_shape.members.items():
                            key = f'{_to_cli_style(param_name)} ({member.type_name})'
                            params[key] = (
                                _clean_text(member.documentation)
                                if hasattr(member, 'documentation')
                                else 'No description'
                            )

                    documents.append(
                        {
                            'command': f'aws {service_name} {operation_name}',
                            'description': description,
                            'parameters': params,
                        }
                    )
        except Exception:
            continue

    return documents


def generate_embeddings(model_name: str, cache_dir: Path, overwrite: bool):
    """Generate embeddings for AWS API commands and save them to a cache file."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f'{model_name.replace("/", "-")}.npz'
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

    # Save to cache
    retriever.save_to_cache()
    logger.info(f'Embeddings are saved to: {cache_file}')


def main():
    """Driver for the generate embeddings util."""
    parser = argparse.ArgumentParser(description='Argument parser for model loading')
    parser.add_argument(
        '--model-name',
        type=str,
        default=DEFAULT_EMBEDDINGS_MODEL,
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
    main()
