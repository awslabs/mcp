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
"""Tests for the configure_domain module."""

import pytest
from awslabs.aws_serverless_mcp_server.tools.webapps.configure_domain import ConfigureDomainTool
from unittest.mock import AsyncMock, MagicMock, patch


class TestConfigureDomain:
    """Tests for the configure_domain function."""

    @pytest.mark.asyncio
    async def test_configure_domain_with_existing_certificate_and_route53(self):
        """Test configuring a domain with existing certificate and Route53 record creation."""
        # Mock boto3 session and clients
        mock_session = MagicMock()
        mock_acm_client = MagicMock()
        mock_cloudfront_client = MagicMock()
        mock_route53_client = MagicMock()

        mock_session.client.side_effect = lambda service, *args, **kwargs: {
            'acm': mock_acm_client,
            'cloudfront': mock_cloudfront_client,
            'route53': mock_route53_client,
        }[service]

        # Mock ACM list_certificates response
        mock_acm_client.list_certificates.return_value = {
            'CertificateSummaryList': [
                {
                    'CertificateArn': 'arn:aws:acm:us-east-1:123456789012:certificate/abcdef12-3456-7890-abcd-ef1234567890',
                    'DomainName': 'test.example.com',
                    'Status': 'ISSUED',
                }
            ]
        }

        # Mock CloudFront list_distributions response
        mock_cloudfront_client.list_distributions.return_value = {
            'DistributionList': {
                'Items': [
                    {
                        'Id': 'ABCDEF12345',  # pragma: allowlist secret
                        'ARN': 'arn:aws:cloudfront::123456789012:distribution/ABCDEF12345',
                        'Status': 'Deployed',
                        'DomainName': 'd1234abcdef.cloudfront.net',
                        'Origins': {
                            'Quantity': 1,
                            'Items': [
                                {
                                    'Id': 'S3Origin',
                                    'DomainName': 'test-project-bucket.s3.amazonaws.com',
                                    'S3OriginConfig': {'OriginAccessIdentity': ''},
                                }
                            ],
                        },
                    }
                ],
                'Quantity': 1,
            }
        }

        # Mock CloudFront get_distribution_config response
        mock_cloudfront_client.get_distribution_config.return_value = {
            'ETag': 'ETAGVALUE',
            'DistributionConfig': {
                'CallerReference': 'test-reference',
                'Origins': {
                    'Quantity': 1,
                    'Items': [
                        {
                            'Id': 'S3Origin',
                            'DomainName': 'test-project-bucket.s3.amazonaws.com',
                            'S3OriginConfig': {'OriginAccessIdentity': ''},
                        }
                    ],
                },
                'DefaultCacheBehavior': {
                    'TargetOriginId': 'S3Origin',
                    'ViewerProtocolPolicy': 'redirect-to-https',
                    'AllowedMethods': {'Quantity': 2, 'Items': ['GET', 'HEAD']},
                },
                'Comment': 'Test distribution',
                'Enabled': True,
            },
        }

        # Mock CloudFront update_distribution response
        mock_cloudfront_client.update_distribution.return_value = {
            'Distribution': {
                'Id': 'ABCDEF12345',  # pragma: allowlist secret
                'ARN': 'arn:aws:cloudfront::123456789012:distribution/ABCDEF12345',
                'Status': 'InProgress',
                'LastModifiedTime': '2023-05-21T12:00:00Z',
                'DomainName': 'd1234abcdef.cloudfront.net',
                'DistributionConfig': {
                    'CallerReference': 'test-reference',
                    'Aliases': {'Quantity': 1, 'Items': ['test.example.com']},
                    'ViewerCertificate': {
                        'ACMCertificateArn': 'arn:aws:acm:us-east-1:123456789012:certificate/abcdef12-3456-7890-abcd-ef1234567890',
                        'SSLSupportMethod': 'sni-only',
                        'MinimumProtocolVersion': 'TLSv1.2_2021',
                    },
                },
            }
        }

        # Mock Route53 list_hosted_zones response
        mock_route53_client.list_hosted_zones.return_value = {
            'HostedZones': [
                {
                    'Id': '/hostedzone/Z1234567890ABCDEFGHIJ',  # pragma: allowlist secret
                    'Name': 'example.com.',
                    'CallerReference': '1234567890',
                    'Config': {'PrivateZone': False},
                    'ResourceRecordSetCount': 10,
                }
            ]
        }

        # Mock Route53 change_resource_record_sets response
        mock_route53_client.change_resource_record_sets.return_value = {
            'ChangeInfo': {
                'Id': '/change/C1234567890ABCDEFGHIJ',  # pragma: allowlist secret
                'Status': 'PENDING',
                'SubmittedAt': '2023-05-21T12:00:00Z',
            }
        }

        with patch('boto3.Session', return_value=mock_session):
            # Call the function
            result = await ConfigureDomainTool(MagicMock(), True).configure_domain(
                AsyncMock(),
                project_name='test-project',
                domain_name='test.example.com',
                create_certificate=False,
                create_route53_record=True,
                region='us-east-1',
            )

            # Verify the result
            assert result['success'] is True
            assert result['status'] == 'configured'
            assert result['project_name'] == 'test-project'
            assert result['domain_name'] == 'test.example.com'
            assert (
                result['certificate']['arn']
                == 'arn:aws:acm:us-east-1:123456789012:certificate/abcdef12-3456-7890-abcd-ef1234567890'
            )
            assert result['certificate']['status'] == 'ISSUED'
            assert (
                result['cloudfront_distribution']['id']
                == 'ABCDEF12345'  # pragma: allowlist secret
            )
            assert result['cloudfront_distribution']['domain'] == 'ABCDEF12345.cloudfront.net'
            assert result['route53_records'] is not None
            assert len(result['route53_records']) == 1
            assert result['route53_records'][0]['name'] == 'test.example.com'
            assert result['route53_records'][0]['type'] == 'A'
            assert result['route53_records'][0]['alias'] is True
            assert result['route53_records'][0]['target'] == 'ABCDEF12345.cloudfront.net'

            # Verify ACM client was called with the correct parameters
            mock_acm_client.list_certificates.assert_called_once()

            # Verify CloudFront client was called with the correct parameters
            mock_cloudfront_client.list_distributions.assert_called_once()
            mock_cloudfront_client.get_distribution_config.assert_called_once_with(
                Id='ABCDEF12345'  # pragma: allowlist secret
            )

            mock_cloudfront_client.update_distribution.assert_called_once()
            args, kwargs = mock_cloudfront_client.update_distribution.call_args
            assert kwargs['Id'] == 'ABCDEF12345'  # pragma: allowlist secret
            assert kwargs['IfMatch'] == 'ETAGVALUE'
            assert kwargs['DistributionConfig']['Aliases']['Quantity'] == 1
            assert kwargs['DistributionConfig']['Aliases']['Items'] == ['test.example.com']
            assert (
                kwargs['DistributionConfig']['ViewerCertificate']['ACMCertificateArn']
                == 'arn:aws:acm:us-east-1:123456789012:certificate/abcdef12-3456-7890-abcd-ef1234567890'
            )

            # Verify Route53 client was called with the correct parameters
            mock_route53_client.list_hosted_zones.assert_called_once()
            mock_route53_client.change_resource_record_sets.assert_called_once()
            args, kwargs = mock_route53_client.change_resource_record_sets.call_args
            assert kwargs['HostedZoneId'] == 'Z1234567890ABCDEFGHIJ'
            assert kwargs['ChangeBatch']['Changes'][0]['Action'] == 'UPSERT'
            assert (
                kwargs['ChangeBatch']['Changes'][0]['ResourceRecordSet']['Name']
                == 'test.example.com'
            )
            assert kwargs['ChangeBatch']['Changes'][0]['ResourceRecordSet']['Type'] == 'A'
            assert (
                kwargs['ChangeBatch']['Changes'][0]['ResourceRecordSet']['AliasTarget']['DNSName']
                == 'ABCDEF12345.cloudfront.net'  # pragma: allowlist secret
            )

    @pytest.mark.asyncio
    async def test_configure_domain_with_new_certificate(self):
        """Test configuring a domain with new certificate creation."""
        # Mock boto3 session and clients
        mock_session = MagicMock()
        mock_acm_client = MagicMock()
        mock_cloudfront_client = MagicMock()
        mock_route53_client = MagicMock()

        mock_session.client.side_effect = lambda service, *args, **kwargs: {
            'acm': mock_acm_client,
            'cloudfront': mock_cloudfront_client,
            'route53': mock_route53_client,
        }[service]

        # Mock ACM request_certificate response
        mock_acm_client.request_certificate.return_value = {
            'CertificateArn': 'arn:aws:acm:us-east-1:123456789012:certificate/abcdef12-3456-7890-abcd-ef1234567890'
        }

        # Mock ACM waiter
        mock_waiter = MagicMock()
        mock_acm_client.get_waiter.return_value = mock_waiter

        # Mock CloudFront list_distributions response
        mock_cloudfront_client.list_distributions.return_value = {
            'DistributionList': {
                'Items': [
                    {
                        'Id': 'ABCDEF12345',  # pragma: allowlist secret
                        'ARN': 'arn:aws:cloudfront::123456789012:distribution/ABCDEF12345',
                        'Status': 'Deployed',
                        'DomainName': 'd1234abcdef.cloudfront.net',
                        'Origins': {
                            'Quantity': 1,
                            'Items': [
                                {
                                    'Id': 'S3Origin',
                                    'DomainName': 'test-project-bucket.s3.amazonaws.com',
                                    'S3OriginConfig': {'OriginAccessIdentity': ''},
                                }
                            ],
                        },
                    }
                ],
                'Quantity': 1,
            }
        }

        # Mock CloudFront get_distribution_config response
        mock_cloudfront_client.get_distribution_config.return_value = {
            'ETag': 'ETAGVALUE',
            'DistributionConfig': {
                'CallerReference': 'test-reference',
                'Origins': {
                    'Quantity': 1,
                    'Items': [
                        {
                            'Id': 'S3Origin',
                            'DomainName': 'test-project-bucket.s3.amazonaws.com',
                            'S3OriginConfig': {'OriginAccessIdentity': ''},
                        }
                    ],
                },
                'DefaultCacheBehavior': {
                    'TargetOriginId': 'S3Origin',
                    'ViewerProtocolPolicy': 'redirect-to-https',
                    'AllowedMethods': {'Quantity': 2, 'Items': ['GET', 'HEAD']},
                },
                'Comment': 'Test distribution',
                'Enabled': True,
            },
        }

        # Mock CloudFront update_distribution response
        mock_cloudfront_client.update_distribution.return_value = {
            'Distribution': {
                'Id': 'ABCDEF12345',  # pragma: allowlist secret
                'ARN': 'arn:aws:cloudfront::123456789012:distribution/ABCDEF12345',
                'Status': 'InProgress',
                'LastModifiedTime': '2023-05-21T12:00:00Z',
                'DomainName': 'd1234abcdef.cloudfront.net',
                'DistributionConfig': {
                    'CallerReference': 'test-reference',
                    'Aliases': {'Quantity': 1, 'Items': ['test.example.com']},
                    'ViewerCertificate': {
                        'ACMCertificateArn': 'arn:aws:acm:us-east-1:123456789012:certificate/abcdef12-3456-7890-abcd-ef1234567890',
                        'SSLSupportMethod': 'sni-only',
                        'MinimumProtocolVersion': 'TLSv1.2_2021',
                    },
                },
            }
        }

        with patch('boto3.Session', return_value=mock_session):
            # Call the function
            result = await ConfigureDomainTool(MagicMock(), True).configure_domain(
                AsyncMock(),
                project_name='test-project',
                domain_name='test.example.com',
                create_certificate=True,
                create_route53_record=False,
                region='us-east-1',
            )

            # Verify the result
            assert result['success'] is True
            assert result['status'] == 'configured'
            assert result['project_name'] == 'test-project'
            assert result['domain_name'] == 'test.example.com'
            assert (
                result['certificate']['arn']
                == 'arn:aws:acm:us-east-1:123456789012:certificate/abcdef12-3456-7890-abcd-ef1234567890'
            )
            assert result['certificate']['status'] == 'ISSUED'
            assert (
                result['cloudfront_distribution']['id']
                == 'ABCDEF12345'  # pragma: allowlist secret
            )  # pragma: allowlist secret
            assert result['cloudfront_distribution']['domain'] == 'ABCDEF12345.cloudfront.net'
            assert result['route53_records'] is None

            # Verify ACM client was called with the correct parameters
            mock_acm_client.request_certificate.assert_called_once_with(
                DomainName='test.example.com', ValidationMethod='DNS'
            )
            mock_acm_client.get_waiter.assert_called_once_with('certificate_validated')
            mock_waiter.wait.assert_called_once()

            # Verify CloudFront client was called with the correct parameters
            mock_cloudfront_client.list_distributions.assert_called_once()
            mock_cloudfront_client.get_distribution_config.assert_called_once_with(
                Id='ABCDEF12345'  # pragma: allowlist secret
            )

            mock_cloudfront_client.update_distribution.assert_called_once()
            args, kwargs = mock_cloudfront_client.update_distribution.call_args
            assert kwargs['Id'] == 'ABCDEF12345'  # pragma: allowlist secret
            assert kwargs['IfMatch'] == 'ETAGVALUE'
            assert kwargs['DistributionConfig']['Aliases']['Quantity'] == 1
            assert kwargs['DistributionConfig']['Aliases']['Items'] == ['test.example.com']
            assert (
                kwargs['DistributionConfig']['ViewerCertificate']['ACMCertificateArn']
                == 'arn:aws:acm:us-east-1:123456789012:certificate/abcdef12-3456-7890-abcd-ef1234567890'
            )

            # Verify Route53 client was not called
            mock_route53_client.change_resource_record_sets.assert_not_called()

    @pytest.mark.asyncio
    async def test_configure_domain_cloudfront_error(self):
        """Test configuring a domain with CloudFront error."""
        # Mock boto3 session and clients
        mock_session = MagicMock()
        mock_acm_client = MagicMock()
        mock_cloudfront_client = MagicMock()

        mock_session.client.side_effect = lambda service, *args, **kwargs: {
            'acm': mock_acm_client,
            'cloudfront': mock_cloudfront_client,
            'route53': MagicMock(),
        }[service]

        # Mock ACM list_certificates response
        mock_acm_client.list_certificates.return_value = {
            'CertificateSummaryList': [
                {
                    'CertificateArn': 'arn:aws:acm:us-east-1:123456789012:certificate/abcdef12-3456-7890-abcd-ef1234567890',
                    'DomainName': 'test.example.com',
                    'Status': 'ISSUED',
                }
            ]
        }

        # Mock CloudFront list_distributions to raise an exception
        error_message = 'The specified distribution does not exist'
        mock_cloudfront_client.list_distributions.side_effect = Exception(error_message)

        with patch('boto3.Session', return_value=mock_session):
            # Call the func
            # tion
            result = await ConfigureDomainTool(MagicMock(), True).configure_domain(
                AsyncMock(),
                project_name='test-project',
                domain_name='test.example.com',
                create_certificate=False,
                create_route53_record=False,
                region='us-east-1',
            )

            # Verify the result
            assert result['success'] is False
            assert error_message in result['error']

    @pytest.mark.asyncio
    async def test_configure_domain_allow_write_false(self):
        """Test configure_domain with allow_write=False."""
        # Initialize the tool with allow_write=False
        tool = ConfigureDomainTool(MagicMock(), allow_write=False)

        # Call the method and expect an exception
        with pytest.raises(Exception) as excinfo:
            await tool.configure_domain(
                AsyncMock(),
                project_name='test-project',
                domain_name='test.example.com',
                create_certificate=True,
                create_route53_record=True,
                region='us-east-1',
            )

        # Verify the exception message
        assert 'Write operations are not allowed' in str(excinfo.value)
        assert 'Set --allow-write flag to true to enable write operations' in str(excinfo.value)
