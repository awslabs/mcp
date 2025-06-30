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

"""Tests for the models module."""

from awslabs.elasticbeanstalk_mcp_server.models import (
    ApplicationDescription,
    ApplicationVersionDescription,
    EnvironmentDescription,
    EnvironmentTier,
    OptionSetting,
    Tag,
)


class TestEnvironmentTier:
    """Test class for the EnvironmentTier model."""

    def test_environment_tier_init(self):
        """Test initialization of EnvironmentTier."""
        # Arrange & Act
        tier = EnvironmentTier(Name='WebServer', Type='Standard', Version='1.0')

        # Assert
        assert tier.Name == 'WebServer'
        assert tier.Type == 'Standard'
        assert tier.Version == '1.0'

    def test_environment_tier_optional_fields(self):
        """Test initialization of EnvironmentTier with optional fields."""
        # Arrange & Act
        tier = EnvironmentTier()

        # Assert
        assert tier.Name is None
        assert tier.Type is None
        assert tier.Version is None


class TestTag:
    """Test class for the Tag model."""

    def test_tag_init(self):
        """Test initialization of Tag."""
        # Arrange & Act
        tag = Tag(Key='Name', Value='TestEnvironment')

        # Assert
        assert tag.Key == 'Name'
        assert tag.Value == 'TestEnvironment'


class TestOptionSetting:
    """Test class for the OptionSetting model."""

    def test_option_setting_init(self):
        """Test initialization of OptionSetting."""
        # Arrange & Act
        option = OptionSetting(
            Namespace='aws:elasticbeanstalk:environment',
            OptionName='EnvironmentType',
            Value='SingleInstance',
        )

        # Assert
        assert option.Namespace == 'aws:elasticbeanstalk:environment'
        assert option.OptionName == 'EnvironmentType'
        assert option.Value == 'SingleInstance'


class TestEnvironmentDescription:
    """Test class for the EnvironmentDescription model."""

    def test_environment_description_init(self):
        """Test initialization of EnvironmentDescription."""
        # Arrange & Act
        env = EnvironmentDescription(
            EnvironmentName='test-env',
            EnvironmentId='e-12345',
            ApplicationName='test-app',
            VersionLabel='v1',
            SolutionStackName='64bit Amazon Linux 2 v5.4.9 running Node.js 14',
            PlatformArn='arn:aws:elasticbeanstalk:us-east-1::platform/Node.js 14 running on 64bit Amazon Linux 2/5.4.9',
            TemplateName='default',
            Description='Test environment',
            EndpointURL='test-env.elasticbeanstalk.com',
            CNAME='test-env.elasticbeanstalk.com',
            DateCreated='2023-01-01T00:00:00Z',
            DateUpdated='2023-01-02T00:00:00Z',
            Status='Ready',
            AbortableOperationInProgress=False,
            Health='Green',
            HealthStatus='Ok',
            Resources={'LoadBalancer': {'Name': 'awseb-e-a-AWSEBLoa-1SAMPLE1'}},
            Tier=EnvironmentTier(Name='WebServer', Type='Standard', Version='1.0'),
            EnvironmentLinks=[{'LinkName': 'test', 'EnvironmentName': 'linked-env'}],
            EnvironmentArn='arn:aws:elasticbeanstalk:us-east-1:123456789012:environment/test-app/test-env',
            OperationsRole='aws-elasticbeanstalk-service-role',
        )

        # Assert
        assert env.EnvironmentName == 'test-env'
        assert env.EnvironmentId == 'e-12345'
        assert env.ApplicationName == 'test-app'
        assert env.VersionLabel == 'v1'
        assert env.SolutionStackName == '64bit Amazon Linux 2 v5.4.9 running Node.js 14'
        assert (
            env.PlatformArn
            == 'arn:aws:elasticbeanstalk:us-east-1::platform/Node.js 14 running on 64bit Amazon Linux 2/5.4.9'
        )
        assert env.TemplateName == 'default'
        assert env.Description == 'Test environment'
        assert env.EndpointURL == 'test-env.elasticbeanstalk.com'
        assert env.CNAME == 'test-env.elasticbeanstalk.com'
        assert env.DateCreated == '2023-01-01T00:00:00Z'
        assert env.DateUpdated == '2023-01-02T00:00:00Z'
        assert env.Status == 'Ready'
        assert env.AbortableOperationInProgress is False
        assert env.Health == 'Green'
        assert env.HealthStatus == 'Ok'
        assert env.Resources == {'LoadBalancer': {'Name': 'awseb-e-a-AWSEBLoa-1SAMPLE1'}}
        assert isinstance(env.Tier, EnvironmentTier)
        assert env.Tier.Name == 'WebServer'
        assert env.EnvironmentLinks == [{'LinkName': 'test', 'EnvironmentName': 'linked-env'}]
        assert (
            env.EnvironmentArn
            == 'arn:aws:elasticbeanstalk:us-east-1:123456789012:environment/test-app/test-env'
        )
        assert env.OperationsRole == 'aws-elasticbeanstalk-service-role'

    def test_environment_description_optional_fields(self):
        """Test initialization of EnvironmentDescription with optional fields."""
        # Arrange & Act
        env = EnvironmentDescription()

        # Assert
        assert env.EnvironmentName is None
        assert env.EnvironmentId is None
        assert env.ApplicationName is None
        assert env.VersionLabel is None
        assert env.SolutionStackName is None
        assert env.PlatformArn is None
        assert env.TemplateName is None
        assert env.Description is None
        assert env.EndpointURL is None
        assert env.CNAME is None
        assert env.DateCreated is None
        assert env.DateUpdated is None
        assert env.Status is None
        assert env.AbortableOperationInProgress is None
        assert env.Health is None
        assert env.HealthStatus is None
        assert env.Resources is None
        assert env.Tier is None
        assert env.EnvironmentLinks is None
        assert env.EnvironmentArn is None
        assert env.OperationsRole is None


class TestApplicationDescription:
    """Test class for the ApplicationDescription model."""

    def test_application_description_init(self):
        """Test initialization of ApplicationDescription."""
        # Arrange & Act
        app = ApplicationDescription(
            ApplicationName='test-app',
            Description='Test application',
            DateCreated='2023-01-01T00:00:00Z',
            DateUpdated='2023-01-02T00:00:00Z',
            Versions=['v1', 'v2'],
            ConfigurationTemplates=['default'],
            ResourceLifecycleConfig={'ServiceRole': 'aws-elasticbeanstalk-service-role'},
            ApplicationArn='arn:aws:elasticbeanstalk:us-east-1:123456789012:application/test-app',
        )

        # Assert
        assert app.ApplicationName == 'test-app'
        assert app.Description == 'Test application'
        assert app.DateCreated == '2023-01-01T00:00:00Z'
        assert app.DateUpdated == '2023-01-02T00:00:00Z'
        assert app.Versions == ['v1', 'v2']
        assert app.ConfigurationTemplates == ['default']
        assert app.ResourceLifecycleConfig == {'ServiceRole': 'aws-elasticbeanstalk-service-role'}
        assert (
            app.ApplicationArn
            == 'arn:aws:elasticbeanstalk:us-east-1:123456789012:application/test-app'
        )

    def test_application_description_optional_fields(self):
        """Test initialization of ApplicationDescription with optional fields."""
        # Arrange & Act
        app = ApplicationDescription()

        # Assert
        assert app.ApplicationName is None
        assert app.Description is None
        assert app.DateCreated is None
        assert app.DateUpdated is None
        assert app.Versions is None
        assert app.ConfigurationTemplates is None
        assert app.ResourceLifecycleConfig is None
        assert app.ApplicationArn is None


class TestApplicationVersionDescription:
    """Test class for the ApplicationVersionDescription model."""

    def test_application_version_description_init(self):
        """Test initialization of ApplicationVersionDescription."""
        # Arrange & Act
        version = ApplicationVersionDescription(
            ApplicationVersionArn='arn:aws:elasticbeanstalk:us-east-1:123456789012:applicationversion/test-app/v1',
            ApplicationName='test-app',
            Description='Test version',
            VersionLabel='v1',
            SourceBuildInformation={'SourceType': 'Git', 'SourceRepository': 'CodeCommit'},
            BuildArn='arn:aws:codebuild:us-east-1:123456789012:build/test-build',
            SourceBundle={
                'S3Bucket': 'elasticbeanstalk-us-east-1-123456789012',
                'S3Key': 'test-app/v1.zip',
            },
            DateCreated='2023-01-01T00:00:00Z',
            DateUpdated='2023-01-02T00:00:00Z',
            Status='PROCESSED',
        )

        # Assert
        assert (
            version.ApplicationVersionArn
            == 'arn:aws:elasticbeanstalk:us-east-1:123456789012:applicationversion/test-app/v1'
        )
        assert version.ApplicationName == 'test-app'
        assert version.Description == 'Test version'
        assert version.VersionLabel == 'v1'
        assert version.SourceBuildInformation == {
            'SourceType': 'Git',
            'SourceRepository': 'CodeCommit',
        }
        assert version.BuildArn == 'arn:aws:codebuild:us-east-1:123456789012:build/test-build'
        assert version.SourceBundle == {
            'S3Bucket': 'elasticbeanstalk-us-east-1-123456789012',
            'S3Key': 'test-app/v1.zip',
        }
        assert version.DateCreated == '2023-01-01T00:00:00Z'
        assert version.DateUpdated == '2023-01-02T00:00:00Z'
        assert version.Status == 'PROCESSED'

    def test_application_version_description_optional_fields(self):
        """Test initialization of ApplicationVersionDescription with optional fields."""
        # Arrange & Act
        version = ApplicationVersionDescription()

        # Assert
        assert version.ApplicationVersionArn is None
        assert version.ApplicationName is None
        assert version.Description is None
        assert version.VersionLabel is None
        assert version.SourceBuildInformation is None
        assert version.BuildArn is None
        assert version.SourceBundle is None
        assert version.DateCreated is None
        assert version.DateUpdated is None
        assert version.Status is None
