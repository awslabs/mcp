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

"""Tests for AWS authorized defaults."""

import pytest
from awslabs.aws_cicd_mcp_server.core.common.defaults import (
    get_codebuild_defaults,
    get_codepipeline_defaults,
    get_codedeploy_defaults,
    get_deployment_config_name,
    get_latest_codebuild_images,
    get_latest_compute_types
)


def test_codebuild_defaults():
    """Test CodeBuild defaults are properly configured."""
    defaults = get_codebuild_defaults()
    
    assert defaults["environment"]["type"] == "LINUX_CONTAINER"
    assert defaults["environment"]["image"] == "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    assert defaults["environment"]["computeType"] == "BUILD_GENERAL1_SMALL"
    assert defaults["environment"]["privilegedMode"] is False
    assert defaults["environment"]["imagePullCredentialsType"] == "CODEBUILD"
    assert defaults["artifacts"]["type"] == "NO_ARTIFACTS"
    assert defaults["timeoutInMinutes"] == 60
    assert defaults["badgeEnabled"] is False
    assert defaults["source"]["gitCloneDepth"] == 1
    assert defaults["visibility"] == "PRIVATE"


def test_codepipeline_defaults():
    """Test CodePipeline defaults are properly configured."""
    defaults = get_codepipeline_defaults()
    
    assert defaults["pipelineType"] == "V2"
    assert defaults["executionMode"] == "QUEUED"
    assert defaults["source"]["provider"] == "CodeCommit"
    assert defaults["source"]["branch"] == "main"
    assert defaults["source"]["outputFormat"] == "CODE_ZIP"
    assert defaults["source"]["pollForSourceChanges"] is False
    assert "variables" in defaults
    assert "triggers" in defaults


def test_codedeploy_defaults():
    """Test CodeDeploy defaults are properly configured."""
    defaults = get_codedeploy_defaults()
    
    assert defaults["computePlatform"] == "Server"
    assert defaults["autoRollbackConfiguration"]["enabled"] is True
    assert "DEPLOYMENT_FAILURE" in defaults["autoRollbackConfiguration"]["events"]
    assert "DEPLOYMENT_STOP_ON_INSTANCE_FAILURE" in defaults["autoRollbackConfiguration"]["events"]
    assert defaults["deploymentStyle"]["deploymentType"] == "IN_PLACE"
    assert defaults["ec2TagFilters"]["type"] == "KEY_AND_VALUE"
    assert defaults["outdatedInstancesStrategy"] == "UPDATE"
    assert "alarmConfiguration" in defaults


def test_deployment_config_names():
    """Test deployment configuration name selection."""
    assert get_deployment_config_name("Server") == "CodeDeployDefault.AllAtOneCodeDeploy"
    assert get_deployment_config_name("Lambda") == "CodeDeployDefault.LambdaCanary10Percent5Minutes"
    assert get_deployment_config_name("ECS") == "CodeDeployDefault.ECSAllAtOnceBlueGreen"
    assert get_deployment_config_name("Unknown") == "CodeDeployDefault.AllAtOneCodeDeploy"


def test_codebuild_defaults_with_overrides():
    """Test CodeBuild defaults with user overrides."""
    overrides = {
        "environment": {
            "computeType": "BUILD_GENERAL1_MEDIUM"
        },
        "timeoutInMinutes": 120
    }
    
    defaults = get_codebuild_defaults(overrides)
    
    # Override should be applied
    assert defaults["environment"]["computeType"] == "BUILD_GENERAL1_MEDIUM"
    assert defaults["timeoutInMinutes"] == 120
    
    # Other defaults should remain
    assert defaults["environment"]["image"] == "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    assert defaults["badgeEnabled"] is False


def test_codepipeline_defaults_with_overrides():
    """Test CodePipeline defaults with user overrides."""
    overrides = {
        "pipelineType": "V1",
        "source": {
            "branch": "develop"
        }
    }
    
    defaults = get_codepipeline_defaults(overrides)
    
    # Override should be applied
    assert defaults["pipelineType"] == "V1"
    assert defaults["source"]["branch"] == "develop"
    
    # Other defaults should remain
    assert defaults["executionMode"] == "QUEUED"
    assert defaults["source"]["provider"] == "CodeCommit"


def test_codedeploy_defaults_with_overrides():
    """Test CodeDeploy defaults with user overrides."""
    overrides = {
        "computePlatform": "Lambda",
        "autoRollbackConfiguration": {
            "enabled": False
        }
    }
    
    defaults = get_codedeploy_defaults(overrides)
    
    # Override should be applied
    assert defaults["computePlatform"] == "Lambda"
    assert defaults["autoRollbackConfiguration"]["enabled"] is False
    
    # Other defaults should remain
    assert defaults["deploymentStyle"]["deploymentType"] == "IN_PLACE"


def test_latest_codebuild_images():
    """Test latest CodeBuild images are available."""
    images = get_latest_codebuild_images()
    
    assert "amazonlinux2-x86_64" in images
    assert "ubuntu-24.04" in images
    assert "windows-2022" in images
    assert images["amazonlinux2-x86_64"] == "aws/codebuild/amazonlinux2-x86_64-standard:5.0"


def test_latest_compute_types():
    """Test latest compute types are available."""
    compute_types = get_latest_compute_types()
    
    assert "BUILD_GENERAL1_SMALL" in compute_types
    assert "BUILD_GENERAL1_2XLARGE" in compute_types
    assert "BUILD_LAMBDA_10GB" in compute_types
    assert len(compute_types) >= 10
