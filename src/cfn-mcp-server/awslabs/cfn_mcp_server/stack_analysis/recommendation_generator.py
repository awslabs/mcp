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

import logging
import time
import uuid
from awslabs.cfn_mcp_server.errors import ClientError, ServerError
from awslabs.cfn_mcp_server.stack_analysis.cloudformation_utils import CloudFormationUtils
from awslabs.cfn_mcp_server.stack_analysis.constants.productTypeMapping import (
    resource_to_category_mapping,
)
from awslabs.cfn_mcp_server.stack_analysis.utils.common_utils import (
    save_template_file,
)
from datetime import datetime
from pydantic import BaseModel
from typing import Any, Dict, List, Literal, Optional, Set, Tuple


logger = logging.getLogger(__name__)


class AugmentRecommendation(BaseModel):
    """Model for stack augmentation recommendations."""

    recommendation_type: Literal['AUGMENT_EXISTING_STACK']
    stack_name: str
    resource_count: int
    generated_template_id: str
    template_body: str


class NewStackProposal(BaseModel):
    """Model for new stack proposals with template generation."""

    proposal_id: str
    product_type: str
    description: str
    resource_count: int
    affected_resources: List[Dict[str, Any]]
    generated_template_id: Optional[str] = None
    template_status: Optional[str] = None
    template_creation_time: Optional[str] = None
    stack_name_suggestion: Optional[str] = None
    template_body: Optional[str] = None


class RecommendationGenerator:
    """Generate recommendation templates for CloudFormation stacks and unmanaged resources."""

    # Constants
    MAX_RESOURCES_PER_STACK = 450
    MAX_TEMPLATE_POLLING_ATTEMPTS = 30
    DEFAULT_CATEGORY = 'Unknown'

    # Delay settings for template polling
    BASE_DELAY = 1  # Start with 1 second
    MAX_DELAY = 30  # Maximum delay in seconds

    # Template statuses
    COMPLETE_STATUS = 'COMPLETE'
    FAILED_STATUS = 'FAILED'
    PENDING_STATUSES = [
        'CREATE_PENDING',
        'UPDATE_PENDING',
        'CREATE_IN_PROGRESS',
        'UPDATE_IN_PROGRESS',
    ]

    def __init__(self, region: str):
        """Initialize the RecommendationGenerator with the specified region."""
        self.region = region
        self.cfn_utils = CloudFormationUtils(region)

    def build_augment_template(
        self, stack_name: str, related_unmanaged_resources: List[Dict]
    ) -> AugmentRecommendation:
        """Create template to import related unmanaged resources into existing stack."""
        self._validate_augment_resources(related_unmanaged_resources)

        try:
            template_name = self._generate_template_name('augment', stack_name)
            template_response = self.cfn_utils.create_generated_template(
                stack_name=stack_name,
                resources=related_unmanaged_resources,
                generated_template_name=template_name,
            )

            generated_template_name = template_response.get('GeneratedTemplateName', template_name)
            template_body = self._wait_for_template_completion(generated_template_name)

            recommendation = AugmentRecommendation(
                recommendation_type='AUGMENT_EXISTING_STACK',
                stack_name=stack_name,
                resource_count=len(related_unmanaged_resources),
                generated_template_id=generated_template_name,
                template_body=template_body,
            )

            # Save the template to working directory
            save_template_file(stack_name, template_body)

            return recommendation
        except Exception as e:
            logger.error(f'Error generating augment template: {str(e)}')
            raise ServerError(f'Failed to generate augment template: {str(e)}')

    def propose_new_stacks_by_product_type(
        self, product_type: Optional[str] = None, create_templates: bool = False
    ) -> Dict[str, Any]:
        """Propose new stacks organized by product type with resource limits.

        If product_type is provided, filter resources by that specific type.
        If product_type is None, return all unmanaged resources separated by product types.
        """
        try:
            self._ensure_resource_scan()
            unmanaged_resources = self._get_unmanaged_resources()

            if not unmanaged_resources:
                raise ClientError('No unmanaged resources found in the resource scan.')

            categorized_resources = self._categorize_resources_by_product_type(unmanaged_resources)

            if product_type is not None:
                if product_type not in categorized_resources:
                    available_types = list(categorized_resources.keys())
                    raise ClientError(
                        f"Product type '{product_type}' not found. "
                        f'Available types: {available_types}'
                    )
                filtered_resources = {product_type: categorized_resources[product_type]}
                logger.info(
                    f'Filtered to {len(filtered_resources[product_type])} resources of type {product_type}'
                )
            else:
                # If no product type specified, use all categorized resources
                filtered_resources = categorized_resources
                logger.info(
                    f'Using all {len(unmanaged_resources)} unmanaged resources across {len(categorized_resources)} product types'
                )

            chunked_resources = self._chunk_resources_by_limit(
                filtered_resources, self.MAX_RESOURCES_PER_STACK
            )

            proposals = self._create_proposals(chunked_resources, create_templates)

            return self._build_response_multi_product(
                product_type, filtered_resources, proposals, chunked_resources, create_templates
            )

        except Exception as e:
            logger.error(f'Error creating stack proposals: {str(e)}')
            raise ServerError(f'Failed to create stack proposals: {str(e)}')

    def _validate_augment_resources(self, resources: List[Dict]) -> None:
        """Validate input resources for augmentation."""
        if not resources:
            raise ClientError('No unmanaged resources found to augment the stack.')

        for resource in resources:
            if (
                not isinstance(resource, dict)
                or 'ResourceType' not in resource
                or 'ResourceIdentifier' not in resource
            ):
                raise ClientError(
                    'Invalid resource format. Each resource must be a dictionary '
                    "with 'ResourceType' and 'ResourceIdentifier' keys."
                )

    def _generate_template_name(self, prefix: str, suffix: Optional[str] = None) -> str:
        """Generate unique template name with prefix and optional suffix."""
        unique_id = str(uuid.uuid4())[:8]
        if suffix:
            return f'{prefix}-{suffix}-{unique_id}'
        return f'{prefix}-{unique_id}'

    def _wait_for_template_completion(
        self, template_name: str, max_attempts: Optional[int] = None
    ) -> str:
        """Poll for template generation completion and return template body."""
        max_attempts = max_attempts or self.MAX_TEMPLATE_POLLING_ATTEMPTS

        for attempt in range(max_attempts):
            try:
                status_response = self.cfn_utils.describe_generated_template(template_name)
                status = status_response.get('Status', 'UNKNOWN')

                if status == self.COMPLETE_STATUS:
                    return self.cfn_utils.get_generated_template(template_name)
                elif status == self.FAILED_STATUS:
                    error_reason = status_response.get('StatusReason', 'Unknown error')
                    raise ServerError(f'Template generation failed: {error_reason}')
                elif status in self.PENDING_STATUSES:
                    # Simple progressive delay that increases with each attempt
                    delay = min(self.BASE_DELAY + attempt, self.MAX_DELAY)
                    time.sleep(delay)
                    continue
                else:
                    raise ServerError(f'Unexpected template status: {status}')

            except Exception as e:
                if attempt == max_attempts - 1:
                    raise ServerError(
                        f'Failed to get template after {max_attempts} attempts: {str(e)}'
                    )
                # Simple progressive delay
                delay = min(self.BASE_DELAY + attempt, self.MAX_DELAY)
                time.sleep(delay)

        raise ServerError(f'Template generation timed out after {max_attempts} attempts')

    def _ensure_resource_scan(self) -> None:
        """Ensure a resource scan ID is available."""
        if self.cfn_utils.resource_scan_id:
            return

        logger.info('No resource scan ID provided, looking for latest scan...')
        try:
            scans = self.cfn_utils.list_resource_scans()
            if scans:
                # Prioritize FULL scans over partial scans
                full_scans = [
                    scan
                    for scan in scans
                    if scan.get('Status') == 'COMPLETE' and scan.get('ScanType') == 'FULL'
                ]
                if full_scans:
                    self.cfn_utils.resource_scan_id = full_scans[0].get('ResourceScanId')
                    logger.info(
                        f'Using latest FULL resource scan with ID: {self.cfn_utils.resource_scan_id}'
                    )
                else:
                    # Fall back to the latest scan if no FULL scan is available
                    self.cfn_utils.resource_scan_id = scans[0].get('ResourceScanId')
                    logger.info(
                        f'No FULL scan found, using latest scan with ID: {self.cfn_utils.resource_scan_id}'
                    )
                logger.info(
                    f'Using latest resource scan with ID: {self.cfn_utils.resource_scan_id}'
                )
            else:
                raise ClientError('No resource scans found. Please run a resource scan first.')
        except Exception as e:
            logger.error(f'Failed to get latest resource scan: {str(e)}')
            raise ClientError('Unable to find or access resource scan data.')

    def _get_unmanaged_resources(self) -> List[Dict[str, Any]]:
        """Get unmanaged resources from resource scan."""
        all_resources = self.cfn_utils.list_resource_scan_resources()
        unmanaged_resources = [r for r in all_resources if not r.get('ManagedByStack')]

        logger.info(f'Found {len(unmanaged_resources)} unmanaged resources from resource scan')
        return unmanaged_resources

    def _categorize_resources_by_product_type(
        self, resources: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize resources by their product type."""
        categorized = {}
        unmapped_resources = []

        for resource in resources:
            resource_type = resource.get('ResourceType', '')
            if not resource_type:
                logger.warning(f'Resource missing ResourceType: {resource}')
                continue

            category = resource_to_category_mapping.get(resource_type, self.DEFAULT_CATEGORY)

            if (
                category == self.DEFAULT_CATEGORY
                and resource_type not in resource_to_category_mapping
            ):
                unmapped_resources.append(resource_type)

            categorized.setdefault(category, []).append(resource)

        if unmapped_resources:
            unique_unmapped = set(unmapped_resources)
            logger.info(f'Resources with unmapped types (defaulted to Unknown): {unique_unmapped}')

        return categorized

    def _chunk_resources_by_limit(
        self, categorized_resources: Dict[str, List[Dict[str, Any]]], max_resources_per_chunk: int
    ) -> List[Dict[str, Any]]:
        """Split each product type category into chunks based on resource limit."""
        chunks = []

        for product_type, resources in categorized_resources.items():
            if not resources:
                continue

            total_chunks = (
                len(resources) + max_resources_per_chunk - 1
            ) // max_resources_per_chunk

            for i in range(0, len(resources), max_resources_per_chunk):
                chunk_resources = resources[i : i + max_resources_per_chunk]
                chunk_number = (i // max_resources_per_chunk) + 1

                chunk_name, description = self._generate_chunk_info(
                    product_type, chunk_number, total_chunks, len(chunk_resources)
                )

                chunks.append(
                    {
                        'product_type': product_type,
                        'chunk_name': chunk_name,
                        'description': description,
                        'resources': chunk_resources,
                        'resource_count': len(chunk_resources),
                    }
                )

        return chunks

    def _generate_chunk_info(
        self, product_type: str, chunk_number: int, total_chunks: int, resource_count: int
    ) -> Tuple[str, str]:
        """Generate chunk name and description."""
        if total_chunks > 1:
            chunk_name = f'{product_type}-Stack-{chunk_number}'
            description = (
                f'{product_type} resources stack {chunk_number} of {total_chunks} '
                f'({resource_count} resources)'
            )
        else:
            chunk_name = f'{product_type}-Stack'
            description = f'{product_type} resources stack ({resource_count} resources)'

        return chunk_name, description

    def _create_proposals(
        self, chunked_resources: List[Dict[str, Any]], create_templates: bool
    ) -> List[NewStackProposal]:
        """Create enhanced stack proposals for each resource chunk."""
        proposals = []

        for chunk_info in chunked_resources:
            try:
                proposal = self._create_enhanced_stack_proposal(chunk_info, create_templates)
                proposals.append(proposal)
            except Exception as e:
                logger.error(
                    f'Failed to create proposal for {chunk_info["product_type"]}: {str(e)}'
                )
                # Continue with other proposals rather than failing completely

        return proposals

    def _create_enhanced_stack_proposal(
        self, chunk_info: Dict[str, Any], create_templates: bool
    ) -> NewStackProposal:
        """Create an enhanced stack proposal with optional template generation."""
        proposal_id = str(uuid.uuid4())

        proposal = NewStackProposal(
            proposal_id=proposal_id,
            product_type=chunk_info['product_type'],
            description=chunk_info['description'],
            resource_count=chunk_info['resource_count'],
            affected_resources=chunk_info['resources'],
            stack_name_suggestion=chunk_info['chunk_name'],
        )

        if create_templates:
            self._generate_template_for_proposal(proposal, chunk_info, proposal_id)

        return proposal

    def _generate_template_for_proposal(
        self, proposal: NewStackProposal, chunk_info: Dict[str, Any], proposal_id: str
    ) -> None:
        """Generate CloudFormation template for a proposal."""
        try:
            template_name = (
                f'proposed-{chunk_info["chunk_name"].lower().replace("_", "-")}-{proposal_id[:8]}'
            )
            logger.info(
                f'Creating template {template_name} with {len(chunk_info["resources"])} resources'
            )

            cleaned_resources = self._clean_resources_for_cfn_api(chunk_info['resources'])

            template_response = self.cfn_utils.create_generated_template(
                stack_name='', resources=cleaned_resources, generated_template_name=template_name
            )

            proposal.generated_template_id = template_response.get(
                'GeneratedTemplateId', template_name
            )
            proposal.template_status = 'CREATE_PENDING'
            proposal.template_creation_time = datetime.now().isoformat()

            try:
                proposal.template_body = self._wait_for_template_completion(
                    template_name, max_attempts=30
                )
                proposal.template_status = self.COMPLETE_STATUS
                logger.info(f'Successfully created template for {chunk_info["chunk_name"]}')

                # Save template to working directory
                if proposal.template_body and proposal.stack_name_suggestion:
                    save_template_file(proposal.stack_name_suggestion, proposal.template_body)
            except Exception as template_error:
                logger.error(
                    f'Template polling failed for {chunk_info["chunk_name"]}: {str(template_error)}'
                )
                proposal.template_status = self.FAILED_STATUS

        except Exception as e:
            logger.error(f'Failed to create template for {chunk_info["chunk_name"]}: {str(e)}')
            proposal.template_status = self.FAILED_STATUS

    def _clean_resources_for_cfn_api(
        self, resources: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Clean and deduplicate resources for the CloudFormation API."""
        cleaned_resources = []
        seen_resources: Set[Tuple[str, tuple]] = set()

        for resource in resources:
            resource_identifier = resource.get('ResourceIdentifier', {})
            resource_type = resource.get('ResourceType')
            if resource_type is None:
                continue

            resource_key = (
                resource_type,
                tuple(sorted(resource_identifier.items())) if resource_identifier else (),
            )

            if resource_key not in seen_resources:
                seen_resources.add(resource_key)
                cleaned_resource = {
                    'ResourceType': resource_type,
                    'ResourceIdentifier': resource_identifier,
                }

                if 'LogicalResourceId' in resource:
                    cleaned_resource['LogicalResourceId'] = resource['LogicalResourceId']

                cleaned_resources.append(cleaned_resource)
            else:
                logger.debug(
                    f'Skipping duplicate resource: {resource.get("ResourceType")} '
                    f'with identifier {resource_identifier}'
                )

        logger.info(
            f'Deduplicated {len(resources)} resources to {len(cleaned_resources)} unique resources'
        )
        return cleaned_resources

    def _build_response(
        self,
        product_type: str,
        filtered_resources: List[Dict[str, Any]],
        proposals: List[NewStackProposal],
        chunked_resources: List[Dict[str, Any]],
        create_templates: bool,
    ) -> Dict[str, Any]:
        """Build the final response based on whether templates were created for a single product type."""
        summary = {
            'product_type': product_type,
            'total_resources': len(filtered_resources),
            'stacks_proposed': len(proposals),
        }

        if create_templates:
            summary['successful_templates'] = sum(
                1 for p in proposals if p.template_status == self.COMPLETE_STATUS
            )
            return {
                'summary': summary,
                'proposals': [
                    {
                        k: v
                        for k, v in proposal.model_dump().items()
                        if k not in ['affected_resources', 'template_body']
                    }
                    for proposal in proposals
                ],
            }
        else:
            return {
                'summary': summary,
                'resource_chunks': [
                    {
                        'chunk_name': chunk_info['chunk_name'],
                        'description': chunk_info['description'],
                        'resource_count': chunk_info['resource_count'],
                        'product_type': chunk_info['product_type'],
                    }
                    for chunk_info in chunked_resources
                ],
            }

    def _build_response_multi_product(
        self,
        product_type: Optional[str],
        filtered_resources: Dict[str, List[Dict[str, Any]]],
        proposals: List[NewStackProposal],
        chunked_resources: List[Dict[str, Any]],
        create_templates: bool,
    ) -> Dict[str, Any]:
        """Build the final response for either single or multiple product types."""
        if product_type is not None:
            # Single product type case, use existing method
            return self._build_response(
                product_type,
                filtered_resources[product_type],
                proposals,
                chunked_resources,
                create_templates,
            )

        # Multiple product types case
        total_resources = sum(len(resources) for resources in filtered_resources.values())

        summary = {
            'product_type': 'All',
            'total_resources': total_resources,
            'stacks_proposed': len(proposals),
            'product_types_count': len(filtered_resources),
            'product_types': list(filtered_resources.keys()),
        }

        if create_templates:
            summary['successful_templates'] = sum(
                1 for p in proposals if p.template_status == self.COMPLETE_STATUS
            )

            # Group proposals by product type
            grouped_proposals = {}
            for proposal in proposals:
                product = proposal.product_type
                if product not in grouped_proposals:
                    grouped_proposals[product] = []
                grouped_proposals[product].append(
                    {
                        k: v
                        for k, v in proposal.model_dump().items()
                        if k not in ['affected_resources', 'template_body']
                    }
                )

            return {
                'Present this to the User and DO NOT USE the toolsummary': summary,
                'grouped_proposals': grouped_proposals,
            }
        else:
            # Group resource chunks by product type
            grouped_chunks = {}
            for chunk_info in chunked_resources:
                product = chunk_info['product_type']
                if product not in grouped_chunks:
                    grouped_chunks[product] = []
                grouped_chunks[product].append(
                    {
                        'chunk_name': chunk_info['chunk_name'],
                        'description': chunk_info['description'],
                        'resource_count': chunk_info['resource_count'],
                        'product_type': chunk_info['product_type'],
                    }
                )

            return {
                'Present this to the User and DO NOT USE the toolsummary': summary,
                'grouped_resource_chunks': grouped_chunks,
            }
