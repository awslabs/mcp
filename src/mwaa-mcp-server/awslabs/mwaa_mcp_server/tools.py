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

"""MWAA MCP Server Tools - Implementation of MWAA operations."""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


class MWAATools:
    """Tools for interacting with Amazon MWAA."""

    def __init__(self) -> None:
        """Initialize MWAA tools with AWS clients."""
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.readonly = os.getenv("MWAA_MCP_READONLY", "true").lower() == "true"

        self.mwaa_client = boto3.client("mwaa", region_name=self.region)

        logger.info("Initialized MWAA tools for region: %s", self.region)
        if self.readonly:
            logger.info("Running in read-only mode")

    def _check_readonly(self, operation: str) -> None:
        """Check if operation is allowed in read-only mode."""
        if self.readonly:
            raise PermissionError(f"Operation '{operation}' not allowed in read-only mode")

    def _invoke_airflow_api(
        self, environment_name: str, method: str, path: str, **kwargs: Any
    ) -> Dict[str, Any]:
        """Invoke Airflow REST API using MWAA client."""
        try:
            params: Dict[str, Any] = {
                "Name": environment_name,
                "Method": method.upper(),
                "Path": path,
            }

            if "params" in kwargs:
                processed_params: Dict[str, Any] = {}
                for k, v in kwargs["params"].items():
                    if v is not None:
                        if isinstance(v, str) and v.isdigit():
                            processed_params[k] = int(v)
                        elif isinstance(v, str) and v.lower() in ["true", "false"]:
                            processed_params[k] = v.lower() == "true"
                        elif isinstance(v, str) and v.startswith("[") and v.endswith("]"):
                            try:
                                processed_params[k] = json.loads(v)
                            except json.JSONDecodeError:
                                processed_params[k] = v
                        else:
                            processed_params[k] = v

                query_string = urlencode(processed_params)
                if query_string:
                    params["Path"] = f"{path}?{query_string}"

            if "json_data" in kwargs:
                params["Body"] = json.dumps(kwargs["json_data"])

            response = self.mwaa_client.invoke_rest_api(**params)
            return response

        except (ClientError, BotoCoreError) as e:
            logger.error("Error invoking Airflow API %s %s: %s", method, path, e)
            return {"error": str(e)}

    # Environment Management Methods
    async def list_environments(self, max_results: Optional[int] = None) -> Dict[str, Any]:
        """List MWAA environments."""
        try:
            kwargs: Dict[str, Any] = {}
            if max_results:
                kwargs["MaxResults"] = min(max_results, 25)

            response = self.mwaa_client.list_environments(**kwargs)

            environments = []
            for env_name in response.get("Environments", []):
                try:
                    env_details = await self.get_environment(env_name)
                    environments.append(
                        {
                            "Name": env_name,
                            "Status": env_details.get("Environment", {}).get("Status"),
                            "Arn": env_details.get("Environment", {}).get("Arn"),
                            "CreatedAt": env_details.get("Environment", {}).get("CreatedAt"),
                        }
                    )
                except Exception as e:
                    logger.error("Error getting details for environment %s: %s", env_name, e)
                    environments.append(
                        {
                            "Name": env_name,
                            "Status": "ERROR",
                            "Error": str(e),
                        }
                    )

            return {
                "Environments": environments,
                "NextToken": response.get("NextToken"),
            }

        except (ClientError, BotoCoreError) as e:
            logger.error("Error listing environments: %s", e)
            return {"error": str(e)}

    async def get_environment(self, name: str) -> Dict[str, Any]:
        """Get environment details."""
        try:
            response = self.mwaa_client.get_environment(Name=name)

            env = response.get("Environment", {})
            if "CreatedAt" in env:
                env["CreatedAt"] = env["CreatedAt"].isoformat()
            if "LastUpdate" in env and "CreatedAt" in env["LastUpdate"]:
                env["LastUpdate"]["CreatedAt"] = env["LastUpdate"]["CreatedAt"].isoformat()

            return {"Environment": env}

        except (ClientError, BotoCoreError) as e:
            logger.error("Error getting environment %s: %s", name, e)
            return {"error": str(e)}

    async def create_environment(self, **kwargs: Any) -> Dict[str, Any]:
        """Create a new MWAA environment."""
        self._check_readonly("create_environment")

        try:
            params = {k: v for k, v in kwargs.items() if v is not None}

            boto_params: Dict[str, Any] = {}
            param_mapping = {
                "name": "Name",
                "dag_s3_path": "DagS3Path",
                "execution_role_arn": "ExecutionRoleArn",
                "network_configuration": "NetworkConfiguration",
                "source_bucket_arn": "SourceBucketArn",
                "airflow_version": "AirflowVersion",
                "environment_class": "EnvironmentClass",
                "max_workers": "MaxWorkers",
                "min_workers": "MinWorkers",
                "schedulers": "Schedulers",
                "webserver_access_mode": "WebserverAccessMode",
                "weekly_maintenance_window_start": "WeeklyMaintenanceWindowStart",
                "tags": "Tags",
                "airflow_configuration_options": "AirflowConfigurationOptions",
                "logging_configuration": "LoggingConfiguration",
                "requirements_s3_path": "RequirementsS3Path",
                "plugins_s3_path": "PluginsS3Path",
                "startup_script_s3_path": "StartupScriptS3Path",
            }

            for snake_key, value in params.items():
                if snake_key in param_mapping:
                    boto_params[param_mapping[snake_key]] = value

            response = self.mwaa_client.create_environment(**boto_params)
            return {"Arn": response["Arn"]}

        except (ClientError, BotoCoreError) as e:
            logger.error("Error creating environment: %s", e)
            return {"error": str(e)}

    async def update_environment(self, **kwargs: Any) -> Dict[str, Any]:
        """Update an existing MWAA environment."""
        self._check_readonly("update_environment")

        try:
            params = {k: v for k, v in kwargs.items() if v is not None}

            boto_params: Dict[str, Any] = {}
            param_mapping = {
                "name": "Name",
                "dag_s3_path": "DagS3Path",
                "execution_role_arn": "ExecutionRoleArn",
                "network_configuration": "NetworkConfiguration",
                "source_bucket_arn": "SourceBucketArn",
                "airflow_version": "AirflowVersion",
                "environment_class": "EnvironmentClass",
                "max_workers": "MaxWorkers",
                "min_workers": "MinWorkers",
                "schedulers": "Schedulers",
                "webserver_access_mode": "WebserverAccessMode",
                "weekly_maintenance_window_start": "WeeklyMaintenanceWindowStart",
                "airflow_configuration_options": "AirflowConfigurationOptions",
                "logging_configuration": "LoggingConfiguration",
                "requirements_s3_path": "RequirementsS3Path",
                "plugins_s3_path": "PluginsS3Path",
                "startup_script_s3_path": "StartupScriptS3Path",
            }

            for snake_key, value in params.items():
                if snake_key in param_mapping:
                    boto_params[param_mapping[snake_key]] = value

            response = self.mwaa_client.update_environment(**boto_params)
            return {"Arn": response["Arn"]}

        except (ClientError, BotoCoreError) as e:
            logger.error("Error updating environment: %s", e)
            return {"error": str(e)}

    async def delete_environment(self, name: str) -> Dict[str, Any]:
        """Delete an existing MWAA environment."""
        self._check_readonly("delete_environment")

        try:
            self.mwaa_client.delete_environment(Name=name)
            return {"message": f"Environment {name} deleted successfully"}

        except (ClientError, BotoCoreError) as e:
            logger.error("Error deleting environment %s: %s", name, e)
            return {"error": str(e)}

    async def create_cli_token(self, name: str) -> Dict[str, Any]:
        """Create a CLI token for the environment."""
        try:
            response = self.mwaa_client.create_cli_token(Name=name)
            return {
                "CliToken": response["CliToken"],
                "WebServerHostname": response["WebServerHostname"],
            }

        except (ClientError, BotoCoreError) as e:
            logger.error("Error creating CLI token for %s: %s", name, e)
            return {"error": str(e)}

    async def create_web_login_token(self, name: str) -> Dict[str, Any]:
        """Create a web login token for the environment."""
        try:
            response = self.mwaa_client.create_web_login_token(Name=name)
            return {
                "WebToken": response["WebToken"],
                "WebServerHostname": response["WebServerHostname"],
                "IamIdentity": response["IamIdentity"],
            }

        except (ClientError, BotoCoreError) as e:
            logger.error("Error creating web login token for %s: %s", name, e)
            return {"error": str(e)}

    # Airflow API Methods
    async def list_dags(
        self,
        environment_name: str,
        limit: Optional[int] = 100,
        offset: Optional[int] = 0,
        tags: Optional[List[str]] = None,
        dag_id_pattern: Optional[str] = None,
        only_active: Optional[bool] = True,
    ) -> Dict[str, Any]:
        """List DAGs via Airflow API."""
        params: Dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            "only_active": only_active,
        }

        if tags:
            params["tags"] = ",".join(tags)
        if dag_id_pattern:
            params["dag_id_pattern"] = dag_id_pattern

        return self._invoke_airflow_api(environment_name, "GET", "/dags", params=params)

    async def get_dag(self, environment_name: str, dag_id: str) -> Dict[str, Any]:
        """Get DAG details via Airflow API."""
        return self._invoke_airflow_api(environment_name, "GET", f"/dags/{dag_id}")

    async def get_dag_source(self, environment_name: str, dag_id: str) -> Dict[str, Any]:
        """Get DAG source code via Airflow API."""
        return self._invoke_airflow_api(
            environment_name, "GET", f"/dags/{dag_id}/dagSource"
        )

    async def trigger_dag_run(
        self,
        environment_name: str,
        dag_id: str,
        dag_run_id: Optional[str] = None,
        conf: Optional[Dict[str, Any]] = None,
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Trigger a DAG run via Airflow API."""
        self._check_readonly("trigger_dag_run")

        data: Dict[str, Any] = {}

        if dag_run_id:
            data["dag_run_id"] = dag_run_id
        else:
            data["dag_run_id"] = f"manual__{datetime.now(timezone.utc).isoformat()}"

        if conf:
            data["conf"] = conf
        if note:
            data["note"] = note

        return self._invoke_airflow_api(
            environment_name, "POST", f"/dags/{dag_id}/dagRuns", json_data=data
        )

    async def get_dag_run(
        self, environment_name: str, dag_id: str, dag_run_id: str
    ) -> Dict[str, Any]:
        """Get DAG run details via Airflow API."""
        return self._invoke_airflow_api(
            environment_name, "GET", f"/dags/{dag_id}/dagRuns/{dag_run_id}"
        )

    async def list_dag_runs(
        self,
        environment_name: str,
        dag_id: str,
        limit: Optional[int] = 100,
        state: Optional[List[str]] = None,
        execution_date_gte: Optional[str] = None,
        execution_date_lte: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List DAG runs via Airflow API."""
        params: Dict[str, Any] = {"limit": limit}

        if state:
            params["state"] = state
        if execution_date_gte:
            params["execution_date_gte"] = execution_date_gte
        if execution_date_lte:
            params["execution_date_lte"] = execution_date_lte

        return self._invoke_airflow_api(
            environment_name, "GET", f"/dags/{dag_id}/dagRuns", params=params
        )

    async def get_task_instance(
        self, environment_name: str, dag_id: str, dag_run_id: str, task_id: str
    ) -> Dict[str, Any]:
        """Get task instance details via Airflow API."""
        return self._invoke_airflow_api(
            environment_name,
            "GET",
            f"/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id}",
        )

    async def get_task_logs(
        self,
        environment_name: str,
        dag_id: str,
        dag_run_id: str,
        task_id: str,
        task_try_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get task logs via Airflow API."""
        if task_try_number is None:
            task_try_number = 1

        endpoint = (
            f"/dags/{dag_id}/dagRuns/{dag_run_id}"
            f"/taskInstances/{task_id}/logs/{task_try_number}"
        )
        return self._invoke_airflow_api(environment_name, "GET", endpoint)

    async def list_connections(
        self,
        environment_name: str,
        limit: Optional[int] = 100,
        offset: Optional[int] = 0,
    ) -> Dict[str, Any]:
        """List connections via Airflow API."""
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        return self._invoke_airflow_api(
            environment_name, "GET", "/connections", params=params
        )

    async def list_variables(
        self,
        environment_name: str,
        limit: Optional[int] = 100,
        offset: Optional[int] = 0,
    ) -> Dict[str, Any]:
        """List variables via Airflow API."""
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        return self._invoke_airflow_api(
            environment_name, "GET", "/variables", params=params
        )

    async def get_import_errors(
        self,
        environment_name: str,
        limit: Optional[int] = 100,
        offset: Optional[int] = 0,
    ) -> Dict[str, Any]:
        """Get import errors via Airflow API."""
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        return self._invoke_airflow_api(
            environment_name, "GET", "/dags/importErrors", params=params
        )
