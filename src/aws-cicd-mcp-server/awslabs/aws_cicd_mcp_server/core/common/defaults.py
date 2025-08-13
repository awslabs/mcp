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

"""AWS authorized defaults for CI/CD services."""

from typing import Dict, Any

# CodeBuild Defaults - Updated to latest AWS documentation
CODEBUILD_DEFAULTS = {
    "environment": {
        "type": "LINUX_CONTAINER",
        "image": "aws/codebuild/amazonlinux2-x86_64-standard:5.0",  # Latest as of 2024
        "computeType": "BUILD_GENERAL1_SMALL",
        "privilegedMode": False,
        "imagePullCredentialsType": "CODEBUILD"  # Latest default
    },
    "artifacts": {
        "type": "NO_ARTIFACTS"
    },
    "source": {
        "type": "CODECOMMIT",
        "buildspec": "version: 0.2\nphases:\n  build:\n    commands:\n      - echo Build started on `date`\n      - echo Build completed on `date`",
        "gitCloneDepth": 1,  # Latest optimization
        "reportBuildStatus": False
    },
    "timeoutInMinutes": 60,
    "queuedTimeoutInMinutes": 480,
    "badgeEnabled": False,
    "logsConfig": {
        "cloudWatchLogs": {
            "status": "ENABLED",
            "groupName": "",  # Auto-generated
            "streamName": ""  # Auto-generated
        },
        "s3Logs": {
            "status": "DISABLED"
        }
    },
    "buildBatchConfig": {
        "serviceRole": "",  # Required for batch builds
        "combineArtifacts": False,
        "restrictions": {
            "maximumBuildsAllowed": 100,
            "computeTypesAllowed": ["BUILD_GENERAL1_SMALL", "BUILD_GENERAL1_MEDIUM"]
        }
    },
    "concurrentBuildLimit": 1,
    "visibility": "PRIVATE"  # Latest security default
}

# CodePipeline Defaults - Updated to latest AWS documentation
CODEPIPELINE_DEFAULTS = {
    "pipelineType": "V2",  # Latest version
    "executionMode": "QUEUED",
    "variables": [],  # V2 feature
    "triggers": [],   # V2 feature
    "source": {
        "provider": "CodeCommit",
        "version": "1",
        "branch": "main",
        "outputFormat": "CODE_ZIP",
        "pollForSourceChanges": False  # Use CloudWatch Events instead
    },
    "build": {
        "provider": "CodeBuild",
        "version": "1"
    },
    "deploy": {
        "provider": "CodeDeploy",
        "version": "1"
    }
}

# CodeDeploy Defaults - Updated to latest AWS documentation
CODEDEPLOY_DEFAULTS = {
    "computePlatform": "Server",
    "deploymentConfig": {
        "Server": "CodeDeployDefault.AllAtOneCodeDeploy",
        "Lambda": "CodeDeployDefault.LambdaCanary10Percent5Minutes", 
        "ECS": "CodeDeployDefault.ECSAllAtOnceBlueGreen",
        "ECSBlueGreen": "CodeDeployDefault.ECSAllAtOnceBlueGreen",  # Latest ECS option
        "LambdaBlueGreen": "CodeDeployDefault.LambdaAllAtOnce"      # Latest Lambda option
    },
    "autoRollbackConfiguration": {
        "enabled": True,
        "events": ["DEPLOYMENT_FAILURE", "DEPLOYMENT_STOP_ON_ALARM", "DEPLOYMENT_STOP_ON_INSTANCE_FAILURE"]  # Latest events
    },
    "deploymentStyle": {
        "deploymentType": "IN_PLACE",
        "deploymentOption": "WITHOUT_TRAFFIC_CONTROL"
    },
    "blueGreenDeploymentConfiguration": {  # Latest feature
        "terminateBlueInstancesOnDeploymentSuccess": {
            "action": "TERMINATE",
            "terminationWaitTimeInMinutes": 5
        },
        "deploymentReadyOption": {
            "actionOnTimeout": "CONTINUE_DEPLOYMENT"
        },
        "greenFleetProvisioningOption": {
            "action": "COPY_AUTO_SCALING_GROUP"
        }
    },
    "ec2TagFilters": {
        "type": "KEY_AND_VALUE"
    },
    "onPremisesInstanceTagFilters": {  # Latest on-premises support
        "type": "KEY_AND_VALUE"
    },
    "revision": {
        "revisionType": "S3"
    },
    "alarmConfiguration": {  # Latest monitoring feature
        "enabled": False,
        "ignorePollAlarmFailure": False,
        "alarms": []
    },
    "outdatedInstancesStrategy": "UPDATE",  # Latest strategy
    "tags": []  # Latest tagging support
}

def get_codebuild_defaults(project_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Get CodeBuild defaults with optional overrides."""
    defaults = CODEBUILD_DEFAULTS.copy()
    if project_config:
        # Merge user config with defaults
        for key, value in project_config.items():
            if isinstance(value, dict) and key in defaults:
                defaults[key].update(value)
            else:
                defaults[key] = value
    return defaults

def get_codepipeline_defaults(pipeline_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Get CodePipeline defaults with optional overrides."""
    defaults = CODEPIPELINE_DEFAULTS.copy()
    if pipeline_config:
        for key, value in pipeline_config.items():
            if isinstance(value, dict) and key in defaults:
                defaults[key].update(value)
            else:
                defaults[key] = value
    return defaults

def get_codedeploy_defaults(deploy_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Get CodeDeploy defaults with optional overrides."""
    defaults = CODEDEPLOY_DEFAULTS.copy()
    if deploy_config:
        for key, value in deploy_config.items():
            if isinstance(value, dict) and key in defaults:
                defaults[key].update(value)
            else:
                defaults[key] = value
    return defaults

def get_deployment_config_name(compute_platform: str) -> str:
    """Get default deployment configuration name for compute platform."""
    return CODEDEPLOY_DEFAULTS["deploymentConfig"].get(compute_platform, 
                                                      CODEDEPLOY_DEFAULTS["deploymentConfig"]["Server"])

def get_latest_codebuild_images() -> Dict[str, str]:
    """Get latest CodeBuild standard images by platform."""
    return {
        "amazonlinux2-x86_64": "aws/codebuild/amazonlinux2-x86_64-standard:5.0",
        "amazonlinux2-aarch64": "aws/codebuild/amazonlinux2-aarch64-standard:3.0", 
        "ubuntu-20.04": "aws/codebuild/standard:5.0",
        "ubuntu-22.04": "aws/codebuild/standard:6.0",
        "ubuntu-24.04": "aws/codebuild/standard:7.0",  # Latest Ubuntu
        "windows-2019": "aws/codebuild/windows-base:2019-2.0",
        "windows-2022": "aws/codebuild/windows-base:2022-1.0"  # Latest Windows
    }

def get_latest_compute_types() -> list:
    """Get latest available compute types."""
    return [
        "BUILD_GENERAL1_SMALL",
        "BUILD_GENERAL1_MEDIUM", 
        "BUILD_GENERAL1_LARGE",
        "BUILD_GENERAL1_XLARGE",   # Latest addition
        "BUILD_GENERAL1_2XLARGE",  # Latest addition
        "BUILD_LAMBDA_1GB",        # Latest serverless option
        "BUILD_LAMBDA_2GB",        # Latest serverless option
        "BUILD_LAMBDA_4GB",        # Latest serverless option
        "BUILD_LAMBDA_8GB",        # Latest serverless option
        "BUILD_LAMBDA_10GB"        # Latest serverless option
    ]
