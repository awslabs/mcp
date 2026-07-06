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


"""Knowledge base for RODA metadata."""

from collections import defaultdict
from typing import Any


class DatasetKnowledgeBase:
    """In-memory knowledge base for dataset metadata with indexing and search capabilities."""

    # Fixed set of recognized license categories used by the indexer.
    # This is the authoritative list regardless of which categories have matches.
    SUPPORTED_LICENSE_TYPES = ['creative commons', 'mit', 'apache', 'public domain']

    def __init__(self):
        """Initialize an empty knowledge base with dataset storage and search indexes."""
        self.datasets: list[dict[str, Any]] = []
        self.tag_index: dict[str, list[int]] = defaultdict(list)
        self.managed_by_index: dict[str, list[int]] = defaultdict(list)
        self.license_index: dict[str, list[int]] = defaultdict(list)
        self.resource_type_index: dict[str, list[int]] = defaultdict(list)

    def build_indexes(self, datasets: list[dict[str, Any]]) -> None:
        """Build all indexes from dataset list."""
        self.datasets = datasets
        self.tag_index.clear()
        self.managed_by_index.clear()
        self.license_index.clear()
        self.resource_type_index.clear()

        for idx, dataset in enumerate(datasets):
            # Index tags (guard against null values from upstream JSON)
            for tag in dataset.get('Tags') or []:
                if isinstance(tag, str):
                    self.tag_index[tag.lower()].append(idx)

            # Index managed by
            managed_by = (dataset.get('ManagedBy') or '').lower()
            if managed_by:
                self.managed_by_index[managed_by].append(idx)

            # Index license
            license_text = (dataset.get('License') or '').lower()
            if license_text:
                # Extract common license types
                if 'cc' in license_text or 'creative commons' in license_text:
                    self.license_index['creative commons'].append(idx)
                if 'mit' in license_text:
                    self.license_index['mit'].append(idx)
                if 'apache' in license_text:
                    self.license_index['apache'].append(idx)
                if 'public domain' in license_text:
                    self.license_index['public domain'].append(idx)

            # Index resource types
            for resource in dataset.get('Resources') or []:
                resource_type = (resource.get('Type') or '').lower()
                if resource_type:
                    self.resource_type_index[resource_type].append(idx)

    def search_by_organization(self, org: str) -> list[dict[str, Any]]:
        """Find datasets managed by a specific organization."""
        org_lower = org.lower()
        matching_indices = []

        for managed_by, indices in self.managed_by_index.items():
            if org_lower in managed_by:
                matching_indices.extend(indices)

        return [self.datasets[idx] for idx in set(matching_indices)]

    def search_by_license(self, license_type: str) -> list[dict[str, Any]]:
        """Find datasets with a specific license type."""
        indices = self.license_index.get(license_type.lower(), [])
        return [self.datasets[idx] for idx in indices]

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about the knowledge base."""
        total_datasets = len(self.datasets)

        # Count datasets with resources
        datasets_with_resources = sum(1 for d in self.datasets if d.get('Resources'))

        # Count datasets with documentation
        datasets_with_docs = sum(1 for d in self.datasets if d.get('Documentation'))

        # Get top tags
        tag_counts = {tag: len(indices) for tag, indices in self.tag_index.items()}
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        # Get top organizations
        org_counts = {org: len(indices) for org, indices in self.managed_by_index.items()}
        top_orgs = sorted(org_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            'total_datasets': total_datasets,
            'datasets_with_resources': datasets_with_resources,
            'datasets_with_documentation': datasets_with_docs,
            'total_tags': len(self.tag_index),
            'total_organizations': len(self.managed_by_index),
            'top_tags': top_tags,
            'top_organizations': top_orgs,
            'resource_types': list(self.resource_type_index.keys()),
            'license_types': list(self.license_index.keys()),
        }

    def find_related_datasets(self, slug: str, limit: int = 5) -> list[dict[str, Any]]:
        """Find datasets related to a given dataset based on shared tags."""
        # Find the dataset
        dataset = None
        for d in self.datasets:
            if d.get('Slug') == slug:
                dataset = d
                break

        if not dataset:
            return []

        # Get tags from the dataset
        tags = dataset.get('Tags') or []
        if not tags:
            return []

        # Find datasets with overlapping tags
        related_scores: dict[int, int] = defaultdict(int)

        for tag in tags:
            for idx in self.tag_index.get(tag.lower(), []):
                if self.datasets[idx].get('Slug') != slug:
                    related_scores[idx] += 1

        # Sort by score and return top results
        sorted_results = sorted(related_scores.items(), key=lambda x: x[1], reverse=True)[:limit]

        return [self.datasets[idx] for idx, _ in sorted_results]
