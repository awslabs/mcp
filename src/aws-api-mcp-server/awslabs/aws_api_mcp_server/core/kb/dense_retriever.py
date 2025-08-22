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

import json
import numpy as np
import os
from ...core.common.config import EMBEDDING_MODEL_DIR
from ...core.common.helpers import download_embedding_model
from awscli.clidriver import __version__ as awscli_version
from copy import deepcopy
from loguru import logger
from pathlib import Path
from sentence_transformers import SentenceTransformer


DEFAULT_TOP_K = 5
DEFAULT_EMBEDDING_MODEL = 'BAAI/bge-base-en-v1.5'
DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent / 'data' / 'embeddings'
KNOWLEDGE_BASE_SUFFIX = 'knowledge-base-awscli'


class DenseRetriever:
    """Retrieves documents from a dense index, built by an embedding model.

    The class can receive documents, generate embeddings and cache them to future use.
    """

    def __init__(
        self,
        top_k: int = DEFAULT_TOP_K,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        cache_dir: Path = DEFAULT_CACHE_DIR,
    ):
        """Initializes the retriever.

        If cache_dir is given, the documents and embeddings are loaded fro mthe cache on demand. Otherwise the embeddings are generated on the fly given the documents.
        """
        self.top_k = top_k
        self.cache_dir = cache_dir
        self.model_name = model_name
        self._model = None
        self._index = None
        self._documents = None
        self._embeddings = None
        self._model_ready = False

    @property
    def model(self):
        """Return the sentence transformer model."""
        if self._model is None:
            logger.info('Loading embedding model {} ...', self.model_name)
            model_dir = Path(os.path.join(EMBEDDING_MODEL_DIR, self.model_name))
            if not model_dir.exists():
                download_embedding_model(self.model_name)
            logger.debug('Embedding model is cached at {}', model_dir)
            self._model = SentenceTransformer(
                model_name_or_path=str(model_dir), local_files_only=True, device='cpu'
            )
            self._model_ready = True
            logger.info('Embedding model loaded!')
        return self._model

    @property
    def is_model_ready(self):
        """Return if the model is ready to be used or not."""
        return self._model_ready

    @model.setter
    def model(self, value):
        """Set the model."""
        self._model = value

    @property
    def index(self):
        """Return the FAISS index."""
        if self._index is None:
            import faiss

            if self.embeddings is None:
                raise ValueError('Embeddings are not loaded.')
            self._index = faiss.IndexFlatIP(self.embeddings.shape[1])
            self._index.add(self.embeddings)  # type: ignore
        return self._index

    @index.setter
    def index(self, value):
        """Set the index."""
        self._index = value

    @property
    def documents(self):
        """Return the loaded documents."""
        if self._documents is None:
            try:
                self.load_from_cache_with_version()
            except FileNotFoundError:
                raise FileNotFoundError('No embeddings found for current awscli version')
        return self._documents

    @documents.setter
    def documents(self, value):
        """Set the documents."""
        self._documents = value

    @property
    def embeddings(self):
        """Return the loaded embeddings."""
        if self._embeddings is None:
            try:
                self.load_from_cache_with_version()
            except FileNotFoundError:
                raise FileNotFoundError('No embeddings found for current awscli version')
        return self._embeddings

    @embeddings.setter
    def embeddings(self, value):
        """Set the embeddings."""
        self._embeddings = value

    def get_cache_file_with_version(self):
        """Return cache file name with current awscli version."""
        if self.cache_dir:
            return Path(self.cache_dir) / f'{KNOWLEDGE_BASE_SUFFIX}-{awscli_version}.npz'
        return None

    def load_from_cache_with_version(self):
        """Load documents and embeddings from versioned cache file."""
        cache_file = self.get_cache_file_with_version()
        if not cache_file or not Path(cache_file).exists():
            raise FileNotFoundError(f'Versioned cache file not found: {cache_file}')
        logger.info(f'Loading data from versioned cache: {cache_file}')
        data = np.load(cache_file, allow_pickle=False)
        self._documents = json.loads(str(data['documents']))
        self._embeddings = data['embeddings']

    def save_to_cache(self):
        """Save documents and embeddings to cache file."""
        if not self.cache_dir:
            raise ValueError('Cache directory is not set')
        if self.embeddings is None:
            raise ValueError('Embeddings are not set')

        cache_file = self.get_cache_file_with_version()
        if cache_file is None:
            raise ValueError('Cache file is not set')
        logger.info(f'Saving data to cache: {cache_file}')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            cache_file,
            embeddings=self.embeddings,
            documents=np.array(json.dumps(self.documents)),
        )

    def generate_index(self, documents: list[dict]):
        """Calculate indexes for the given documents."""
        self._documents = deepcopy(documents)
        self._embeddings = self.model.encode(
            [json.dumps(doc) for doc in self._documents],
            normalize_embeddings=True,
            batch_size=64,
            show_progress_bar=True,
        ).astype('float32')

    def get_suggestions(self, query: str, **kwargs) -> dict[str, list[dict]]:
        """Search for similar documents using the query."""
        # Generate embedding for the query
        query_embedding = self.model.encode([query], normalize_embeddings=True).astype('float32')

        # Perform the search
        distances, indices = self.index.search(query_embedding, self.top_k)  # type: ignore

        # Format results
        documents = []
        if self.documents is None:
            raise ValueError('Documents are not loaded.')
        for distance, idx in zip(distances[0], indices[0], strict=False):
            document = deepcopy(self.documents[idx])
            document['similarity'] = round(float(distance), 3)
            documents.append(document)

        return {'suggestions': documents}
