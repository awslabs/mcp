"""Configure domain tool for AWS Lambda MCP Server."""

import os
import boto3
from typing import Dict, Any
from awslabs.aws_lambda_mcp_server.models import ConfigureDomainRequest
from awslabs.aws_lambda_mcp_server.utils.logger import logger

async def configure_domain(request: ConfigureDomainRequest) -> Dict[str, Any]:
    """
    Configure a custom domain for a deployed web application.
    
    Args:
        request: ConfigureDomainRequest object containing domain configuration parameters
    
    Returns:
        Dict: Domain configuration result
    """
    try:
        project_name = request.project_name
        domain_name = request.domain_name
        certificate_arn = request.certificate_arn
        hosted_zone_id = request.hosted_zone_id
        create_route53_record = request.create_route53_record
        
        logger.info(f"Configuring custom domain {domain_name} for project {project_name}")
        
        # Initialize AWS clients
        session = boto3.Session(
            region_name=request.region or os.environ.get('AWS_REGION', 'us-east-1'),
            profile_name=os.environ.get('AWS_PROFILE', 'default')
        )
        cloudfront_client = session.client('cloudfront')
        route53_client = session.client('route53')
        
        # Get the CloudFront distribution for the project
        # This is a simplified implementation - in a real scenario, we would need to
        # query CloudFormation or some other storage to get the distribution ID
        distribution_id = f"{project_name}-distribution"
        
        try:
            # Get the distribution config
            response = cloudfront_client.get_distribution_config(Id=distribution_id)
            etag = response['ETag']
            config = response['DistributionConfig']
            
            # Update the distribution config with the custom domain
            config['Aliases'] = {
                'Quantity': 1,
                'Items': [domain_name]
            }
            
            # Update the SSL certificate
            config['ViewerCertificate'] = {
                'ACMCertificateArn': certificate_arn,
                'SSLSupportMethod': 'sni-only',
                'MinimumProtocolVersion': 'TLSv1.2_2021'
            }
            
            # Update the distribution
            update_response = cloudfront_client.update_distribution(
                Id=distribution_id,
                IfMatch=etag,
                DistributionConfig=config
            )
            
            logger.info(f"Updated CloudFront distribution {distribution_id} with custom domain {domain_name}")
            
            # Create Route53 record if requested
            if create_route53_record and hosted_zone_id:
                # Get the CloudFront domain name
                cf_domain_name = update_response['Distribution']['DomainName']
                
                # Create the Route53 record
                route53_response = route53_client.change_resource_record_sets(
                    HostedZoneId=hosted_zone_id,
                    ChangeBatch={
                        'Changes': [
                            {
                                'Action': 'UPSERT',
                                'ResourceRecordSet': {
                                    'Name': domain_name,
                                    'Type': 'A',
                                    'AliasTarget': {
                                        'HostedZoneId': 'Z2FDTNDATAQYW2',  # CloudFront hosted zone ID
                                        'DNSName': cf_domain_name,
                                        'EvaluateTargetHealth': False
                                    }
                                }
                            }
                        ]
                    }
                )
                
                logger.info(f"Created Route53 record for {domain_name} pointing to {cf_domain_name}")
                
                return {
                    'success': True,
                    'message': f"Custom domain {domain_name} configured successfully for project {project_name}",
                    'cloudfront_domain': cf_domain_name,
                    'route53_record_created': True,
                    'route53_change_id': route53_response['ChangeInfo']['Id']
                }
            else:
                return {
                    'success': True,
                    'message': f"Custom domain {domain_name} configured successfully for project {project_name}",
                    'cloudfront_domain': update_response['Distribution']['DomainName'],
                    'route53_record_created': False,
                    'note': "No Route53 record was created. You will need to create a DNS record manually."
                }
        except Exception as e:
            logger.error(f"Error configuring custom domain: {str(e)}")
            return {
                'success': False,
                'message': f"Failed to configure custom domain {domain_name} for project {project_name}",
                'error': str(e)
            }
    except Exception as e:
        logger.error(f"Error in configure_domain: {str(e)}")
        return {
            'success': False,
            'message': f"Failed to configure custom domain for project {project_name}",
            'error': str(e)
        }
