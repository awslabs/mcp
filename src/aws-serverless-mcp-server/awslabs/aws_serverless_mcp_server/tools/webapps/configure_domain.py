#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

"""Configure domain tool for AWS Serverless MCP Server."""

from awslabs.aws_serverless_mcp_server.models import ConfigureDomainRequest
from awslabs.aws_serverless_mcp_server.utils.aws_client_helper import get_aws_client
from loguru import logger
from typing import Any, Dict, List


async def configure_domain(request: ConfigureDomainRequest) -> Dict[str, Any]:
    """Configure a custom domain for a deployed application.

    Args:
        request: ConfigureDomainRequest object containing domain configuration parameters

    Returns:
        Dict: Domain configuration result
    """
    try:
        project_name = request.project_name
        domain_name = request.domain_name
        create_certificate = getattr(request, 'create_certificate', False)
        should_create_route53_records = getattr(request, 'create_route53_record', False)

        # Log status update
        logger.info(f'Starting domain configuration for {project_name}...')

        # Validate parameters
        if not project_name:
            raise ValueError('project_name is required')

        if not domain_name:
            raise ValueError('domain_name is required')

        # Initialize AWS clients
        acm_client = get_aws_client('acm', request.region)
        cloudfront_client = get_aws_client('cloudfront', region=request.region)
        route53_client = get_aws_client('route53', request.region)

        # Step 1: Create or find ACM certificate
        certificate_arn = None
        if create_certificate:
            logger.info(f'Creating ACM certificate for {domain_name}...')
            certificate_arn = await create_acm_certificate(acm_client, domain_name)

            logger.info('Waiting for certificate validation...')
            await wait_for_certificate_validation(acm_client, certificate_arn)
        else:
            logger.info(f'Finding existing certificate for {domain_name}...')
            certificate_arn = await find_existing_certificate(acm_client, domain_name)

        # Step 2: Update CloudFront distribution with the custom domain
        logger.info(f'Updating CloudFront distribution for {project_name}...')
        distribution_id = await update_cloudfront_distribution(
            cloudfront_client, project_name, domain_name, certificate_arn
        )

        # Step 3: Create Route53 records if requested
        route53_records = None
        if should_create_route53_records:
            logger.info(f'Creating Route 53 records for {domain_name}...')
            route53_records = await create_route53_records(
                route53_client, domain_name, distribution_id
            )

        return {
            'success': True,
            'status': 'configured',
            'project_name': project_name,
            'domain_name': domain_name,
            'certificate': {'arn': certificate_arn, 'status': 'ISSUED'},
            'cloudfront_distribution': {
                'id': distribution_id,
                'domain': f'{distribution_id}.cloudfront.net',
            },
            'route53_records': route53_records,
        }
    except Exception as error:
        logger.error(f'Domain configuration failed: {error}')
        return {'success': False, 'error': str(error)}


async def create_acm_certificate(acm_client, domain_name: str) -> str:
    """Create an ACM certificate for the domain.

    Args:
        acm_client: ACM boto3 client
        domain_name: Domain name for the certificate

    Returns:
        str: Certificate ARN
    """
    try:
        # Request a certificate using the SDK
        logger.info(f'Requesting certificate for {domain_name} using ACM SDK...')

        response = acm_client.request_certificate(DomainName=domain_name, ValidationMethod='DNS')

        certificate_arn = response.get('CertificateArn')

        if not certificate_arn:
            raise Exception('Failed to create ACM certificate: No ARN returned')

        logger.info(f'Certificate requested with ARN: {certificate_arn}')
        return certificate_arn
    except Exception as error:
        raise Exception(f'Failed to create ACM certificate: {str(error)}')


async def wait_for_certificate_validation(acm_client, certificate_arn: str) -> None:
    """Wait for certificate validation.

    Args:
        acm_client: ACM boto3 client
        certificate_arn: Certificate ARN to wait for
    """
    try:
        logger.info('Waiting for certificate validation...')

        # Use boto3 waiter for certificate validation
        waiter = acm_client.get_waiter('certificate_validated')
        waiter.wait(
            CertificateArn=certificate_arn,
            WaiterConfig={
                'Delay': 30,
                'MaxAttempts': 30,  # 15 minutes total
            },
        )

        logger.info('Certificate validated successfully.')
    except Exception as error:
        raise Exception(f'Certificate validation failed: {str(error)}')


async def find_existing_certificate(acm_client, domain_name: str) -> str:
    """Find an existing certificate for the domain.

    Args:
        acm_client: ACM boto3 client
        domain_name: Domain name to find certificate for

    Returns:
        str: Certificate ARN
    """
    try:
        # List certificates using SDK
        logger.info('Listing certificates using ACM SDK...')

        response = acm_client.list_certificates()

        # Find a certificate for the domain
        certificate = None
        for cert in response.get('CertificateSummaryList', []):
            if cert.get('DomainName') == domain_name and cert.get('Status') == 'ISSUED':
                certificate = cert
                break

        if not certificate:
            raise Exception(f'No existing certificate found for {domain_name}')

        certificate_arn = certificate.get('CertificateArn')
        if not certificate_arn:
            raise Exception('Certificate found but ARN is missing')

        logger.info(f'Found existing certificate with ARN: {certificate_arn}')
        return certificate_arn
    except Exception as error:
        raise Exception(f'Failed to find existing certificate: {str(error)}')


async def update_cloudfront_distribution(
    cloudfront_client, project_name: str, domain_name: str, certificate_arn: str
) -> str:
    """Update CloudFront distribution with custom domain.

    Args:
        cloudfront_client: CloudFront boto3 client
        project_name: Project name
        domain_name: Custom domain name
        certificate_arn: ACM certificate ARN

    Returns:
        str: Distribution ID
    """
    try:
        # Step 1: Find the CloudFront distribution for the project using SDK
        logger.info(f'Finding CloudFront distribution for {project_name} using CloudFront SDK...')

        response = cloudfront_client.list_distributions()

        # Find the distribution by looking for origins that match the project name
        distribution = None
        for dist in response.get('DistributionList', {}).get('Items', []):
            origins = dist.get('Origins', {}).get('Items', [])
            for origin in origins:
                if f'{project_name}-bucket' in origin.get('DomainName', ''):
                    distribution = dist
                    break
            if distribution:
                break

        if not distribution:
            raise Exception(f'No CloudFront distribution found for {project_name}')

        distribution_id = distribution['Id']
        logger.info(f'Found CloudFront distribution: {distribution_id}')

        # Step 2: Get the distribution config using SDK
        config_response = cloudfront_client.get_distribution_config(Id=distribution_id)
        etag = config_response['ETag']
        config = config_response['DistributionConfig']

        if not etag or not config:
            raise Exception('Failed to get distribution configuration')

        # Step 3: Update the distribution config
        aliases = config.get('Aliases', {'Quantity': 0, 'Items': []})
        current_items = aliases.get('Items', [])

        # Add the new domain if it's not already there
        if domain_name not in current_items:
            current_items.append(domain_name)

        config['Aliases'] = {'Quantity': len(current_items), 'Items': current_items}

        # Update the SSL certificate
        config['ViewerCertificate'] = {
            'ACMCertificateArn': certificate_arn,
            'SSLSupportMethod': 'sni-only',
            'MinimumProtocolVersion': 'TLSv1.2_2021',
        }

        # Step 4: Update the distribution using SDK
        logger.info('Updating CloudFront distribution with custom domain...')

        cloudfront_client.update_distribution(
            Id=distribution_id, DistributionConfig=config, IfMatch=etag
        )

        logger.info('CloudFront distribution updated successfully.')

        return distribution_id
    except Exception as error:
        raise Exception(f'Failed to update CloudFront distribution: {str(error)}')


async def create_route53_records(
    route53_client, domain_name: str, distribution_id: str
) -> List[Dict[str, Any]]:
    """Create Route53 records for the domain.

    Args:
        route53_client: Route53 boto3 client
        domain_name: Domain name
        distribution_id: CloudFront distribution ID

    Returns:
        List[Dict]: Created Route53 records
    """
    try:
        # Step 1: Find the hosted zone for the domain using SDK
        logger.info(f'Finding Route 53 hosted zone for {domain_name} using Route53 SDK...')

        zones_response = route53_client.list_hosted_zones()

        # Find the hosted zone that matches the domain
        hosted_zone = None
        for zone in zones_response.get('HostedZones', []):
            zone_name = zone.get('Name', '')
            if zone_name.endswith('.'):
                zone_name = zone_name[:-1]
            if zone_name and domain_name.endswith(zone_name):
                hosted_zone = zone
                break

        if not hosted_zone or not hosted_zone.get('Id'):
            raise Exception(f'No Route 53 hosted zone found for {domain_name}')

        hosted_zone_id = hosted_zone['Id'].replace('/hostedzone/', '')
        logger.info(f'Found Route 53 hosted zone: {hosted_zone_id}')

        # Step 2: Create the record set using SDK
        changes = [
            {
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': domain_name,
                    'Type': 'A',
                    'AliasTarget': {
                        'HostedZoneId': 'Z2FDTNDATAQYW2',  # CloudFront's hosted zone ID
                        'DNSName': f'{distribution_id}.cloudfront.net',
                        'EvaluateTargetHealth': False,
                    },
                },
            }
        ]

        logger.info(f'Creating Route 53 record for {domain_name}...')

        route53_client.change_resource_record_sets(
            HostedZoneId=hosted_zone_id, ChangeBatch={'Changes': changes}
        )

        logger.info('Route 53 record created successfully.')

        return [
            {
                'name': domain_name,
                'type': 'A',
                'alias': True,
                'target': f'{distribution_id}.cloudfront.net',
            }
        ]
    except Exception as error:
        raise Exception(f'Failed to create Route 53 records: {str(error)}')
