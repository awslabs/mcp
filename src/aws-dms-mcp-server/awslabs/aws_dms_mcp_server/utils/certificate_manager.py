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

"""Certificate Manager.

Handles business logic for AWS DMS certificate operations.
"""

from .dms_client import DMSClient
from loguru import logger
from typing import Any, Dict, List, Optional


class CertificateManager:
    """Manager for SSL certificate operations."""

    def __init__(self, client: DMSClient):
        """Initialize certificate manager.

        Args:
            client: DMS client wrapper
        """
        self.client = client
        logger.debug('Initialized CertificateManager')

    def import_certificate(
        self,
        certificate_identifier: str,
        certificate_pem: Optional[str] = None,
        certificate_wallet: Optional[bytes] = None,
        tags: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Import an SSL certificate for DMS endpoints.

        Args:
            certificate_identifier: Unique identifier for certificate
            certificate_pem: PEM-encoded certificate data
            certificate_wallet: Oracle wallet certificate data
            tags: Resource tags

        Returns:
            Imported certificate details
        """
        logger.info('Importing certificate', identifier=certificate_identifier)

        params: Dict[str, Any] = {'CertificateIdentifier': certificate_identifier}

        if certificate_pem:
            params['CertificatePem'] = certificate_pem
        if certificate_wallet:
            params['CertificateWallet'] = certificate_wallet
        if tags:
            params['Tags'] = tags

        response = self.client.call_api('import_certificate', **params)

        certificate = response.get('Certificate', {})

        return {
            'success': True,
            'data': {'certificate': certificate, 'message': 'Certificate imported successfully'},
            'error': None,
        }

    def list_certificates(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List SSL certificates with optional filtering.

        Args:
            filters: Optional filters for certificate selection
            max_results: Maximum results per page
            marker: Pagination token

        Returns:
            List of certificates
        """
        logger.info('Listing certificates', filters=filters)

        params: Dict[str, Any] = {'MaxRecords': max_results}

        if filters:
            params['Filters'] = filters
        if marker:
            params['Marker'] = marker

        response = self.client.call_api('describe_certificates', **params)

        certificates = response.get('Certificates', [])

        result = {
            'success': True,
            'data': {'certificates': certificates, 'count': len(certificates)},
            'error': None,
        }

        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        logger.info(f'Retrieved {len(certificates)} certificates')
        return result

    def delete_certificate(self, certificate_arn: str) -> Dict[str, Any]:
        """Delete an SSL certificate.

        Args:
            certificate_arn: Certificate ARN to delete

        Returns:
            Deleted certificate details
        """
        logger.info('Deleting certificate', certificate_arn=certificate_arn)

        response = self.client.call_api('delete_certificate', CertificateArn=certificate_arn)

        certificate = response.get('Certificate', {})

        return {
            'success': True,
            'data': {'certificate': certificate, 'message': 'Certificate deleted successfully'},
            'error': None,
        }
