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

"""Tests for the ROSA advisor handler."""

import json
import pytest
from awslabs.rosa_mcp_server.rosa_advisor_handler import (
    INSTANCE_SPECS,
    ROSA_SERVICE_HOURLY_COST,
    RosaAdvisorHandler,
)


class TestRosaRecommendInstanceType:
    """Tests for rosa_recommend_instance_type."""

    @pytest.mark.asyncio
    async def test_given_general_workload_when_recommend_then_returns_general_instances(
        self, mock_mcp, mock_context
    ):
        """Test rosa_recommend_instance_type for general workload."""
        handler = RosaAdvisorHandler(mock_mcp)
        result = await handler.rosa_recommend_instance_type(
            mock_context, workload_type='general', vcpus=4, memory_gb=16
        )

        assert isinstance(result, list)
        data = json.loads(result[0].text)
        assert data['workload_type'] == 'general'
        assert data['requested'] == {'vcpus': 4, 'memory_gb': 16}
        assert len(data['recommendations']) > 0
        # All recommendations should meet min requirements
        for rec in data['recommendations']:
            assert rec['vcpus'] >= 4
            assert rec['memory_gb'] >= 16

    @pytest.mark.asyncio
    async def test_given_memory_workload_when_recommend_then_returns_memory_instances(
        self, mock_mcp, mock_context
    ):
        """Test rosa_recommend_instance_type for memory workload."""
        handler = RosaAdvisorHandler(mock_mcp)
        result = await handler.rosa_recommend_instance_type(
            mock_context, workload_type='memory', vcpus=4, memory_gb=32
        )

        data = json.loads(result[0].text)
        assert data['workload_type'] == 'memory'
        # Memory instances should be r5/r6i family
        for rec in data['recommendations']:
            assert rec['instance_type'].startswith(('r5', 'r6'))

    @pytest.mark.asyncio
    async def test_given_compute_workload_when_recommend_then_returns_compute_instances(
        self, mock_mcp, mock_context
    ):
        """Test rosa_recommend_instance_type for compute workload."""
        handler = RosaAdvisorHandler(mock_mcp)
        result = await handler.rosa_recommend_instance_type(
            mock_context, workload_type='compute', vcpus=4, memory_gb=8
        )

        data = json.loads(result[0].text)
        assert data['workload_type'] == 'compute'
        for rec in data['recommendations']:
            assert rec['instance_type'].startswith(('c5', 'c6'))

    @pytest.mark.asyncio
    async def test_given_gpu_workload_when_recommend_then_returns_gpu_instances(
        self, mock_mcp, mock_context
    ):
        """Test rosa_recommend_instance_type for gpu workload."""
        handler = RosaAdvisorHandler(mock_mcp)
        result = await handler.rosa_recommend_instance_type(
            mock_context, workload_type='gpu', vcpus=4, memory_gb=16
        )

        data = json.loads(result[0].text)
        assert data['workload_type'] == 'gpu'
        for rec in data['recommendations']:
            assert rec['instance_type'].startswith(('p3', 'g4'))

    @pytest.mark.asyncio
    async def test_given_invalid_workload_when_recommend_then_raises_value_error(
        self, mock_mcp, mock_context
    ):
        """Test rosa_recommend_instance_type rejects invalid workload type."""
        handler = RosaAdvisorHandler(mock_mcp)

        with pytest.raises(ValueError, match="Invalid workload_type"):
            await handler.rosa_recommend_instance_type(
                mock_context, workload_type='invalid'
            )

    @pytest.mark.asyncio
    async def test_given_high_requirements_when_recommend_then_falls_back_to_largest(
        self, mock_mcp, mock_context
    ):
        """Test that high requirements fall back to largest in category."""
        handler = RosaAdvisorHandler(mock_mcp)
        result = await handler.rosa_recommend_instance_type(
            mock_context, workload_type='general', vcpus=64, memory_gb=256
        )

        data = json.loads(result[0].text)
        assert len(data['recommendations']) == 1
        assert 'note' in data['recommendations'][0]


class TestRosaValidateClusterConfig:
    """Tests for rosa_validate_cluster_config."""

    @pytest.mark.asyncio
    async def test_given_valid_config_when_validate_then_returns_valid(
        self, mock_mcp, mock_context
    ):
        """Test rosa_validate_cluster_config with valid config."""
        handler = RosaAdvisorHandler(mock_mcp)
        result = await handler.rosa_validate_cluster_config(
            mock_context,
            cluster_name='my-cluster',
            multi_az=True,
            replicas=3,
            machine_type='m5.xlarge',
            version='4.14.5',
        )

        data = json.loads(result[0].text)
        assert data['valid'] is True
        assert len(data['errors']) == 0

    @pytest.mark.asyncio
    async def test_given_name_too_long_when_validate_then_returns_error(
        self, mock_mcp, mock_context
    ):
        """Test rosa_validate_cluster_config catches invalid name (too long)."""
        handler = RosaAdvisorHandler(mock_mcp)
        long_name = 'a' * 55
        result = await handler.rosa_validate_cluster_config(
            mock_context,
            cluster_name=long_name,
            multi_az=False,
            replicas=2,
            machine_type='m5.xlarge',
            version='4.14.5',
        )

        data = json.loads(result[0].text)
        assert data['valid'] is False
        assert any('2-54 characters' in e for e in data['errors'])

    @pytest.mark.asyncio
    async def test_given_name_with_uppercase_when_validate_then_returns_error(
        self, mock_mcp, mock_context
    ):
        """Test rosa_validate_cluster_config catches invalid name (uppercase)."""
        handler = RosaAdvisorHandler(mock_mcp)
        result = await handler.rosa_validate_cluster_config(
            mock_context,
            cluster_name='My-Cluster',
            multi_az=False,
            replicas=2,
            machine_type='m5.xlarge',
            version='4.14.5',
        )

        data = json.loads(result[0].text)
        assert data['valid'] is False
        assert any('lowercase' in e for e in data['errors'])

    @pytest.mark.asyncio
    async def test_given_multi_az_with_non_multiple_of_3_when_validate_then_error(
        self, mock_mcp, mock_context
    ):
        """Test rosa_validate_cluster_config catches multi_az replicas not multiple of 3."""
        handler = RosaAdvisorHandler(mock_mcp)
        result = await handler.rosa_validate_cluster_config(
            mock_context,
            cluster_name='my-cluster',
            multi_az=True,
            replicas=4,
            machine_type='m5.xlarge',
            version='4.14.5',
        )

        data = json.loads(result[0].text)
        assert data['valid'] is False
        assert any('multiple of 3' in e for e in data['errors'])

    @pytest.mark.asyncio
    async def test_given_one_replica_when_validate_then_returns_warning(
        self, mock_mcp, mock_context
    ):
        """Test rosa_validate_cluster_config catches replicas < 2."""
        handler = RosaAdvisorHandler(mock_mcp)
        result = await handler.rosa_validate_cluster_config(
            mock_context,
            cluster_name='my-cluster',
            multi_az=False,
            replicas=1,
            machine_type='m5.xlarge',
            version='4.14.5',
        )

        data = json.loads(result[0].text)
        # This is a warning, not an error
        assert any('below the recommended minimum' in w for w in data['warnings'])

    @pytest.mark.asyncio
    async def test_given_invalid_version_format_when_validate_then_returns_error(
        self, mock_mcp, mock_context
    ):
        """Test rosa_validate_cluster_config catches invalid version format."""
        handler = RosaAdvisorHandler(mock_mcp)
        result = await handler.rosa_validate_cluster_config(
            mock_context,
            cluster_name='my-cluster',
            multi_az=False,
            replicas=2,
            machine_type='m5.xlarge',
            version='4.14',
        )

        data = json.loads(result[0].text)
        assert data['valid'] is False
        assert any('X.Y.Z format' in e for e in data['errors'])

    @pytest.mark.asyncio
    async def test_given_unknown_machine_type_when_validate_then_returns_warning(
        self, mock_mcp, mock_context
    ):
        """Test rosa_validate_cluster_config warns about unknown machine type."""
        handler = RosaAdvisorHandler(mock_mcp)
        result = await handler.rosa_validate_cluster_config(
            mock_context,
            cluster_name='my-cluster',
            multi_az=False,
            replicas=2,
            machine_type='z99.mega',
            version='4.14.5',
        )

        data = json.loads(result[0].text)
        assert data['valid'] is True  # Unknown machine type is a warning, not error
        assert any('not in the known recommendations' in w for w in data['warnings'])


class TestRosaRecommendClusterConfig:
    """Tests for rosa_recommend_cluster_config."""

    @pytest.mark.asyncio
    async def test_given_production_env_when_recommend_then_returns_ha_config(
        self, mock_mcp, mock_context
    ):
        """Test rosa_recommend_cluster_config for production."""
        handler = RosaAdvisorHandler(mock_mcp)
        result = await handler.rosa_recommend_cluster_config(
            mock_context, environment='production'
        )

        data = json.loads(result[0].text)
        assert data['environment'] == 'production'
        config = data['recommended_config']
        assert config['multi_az'] is True
        assert config['replicas'] == 3
        assert config['private'] is True
        assert config['etcd_encryption'] is True
        assert len(data['notes']) > 0

    @pytest.mark.asyncio
    async def test_given_staging_env_when_recommend_then_returns_staging_config(
        self, mock_mcp, mock_context
    ):
        """Test rosa_recommend_cluster_config for staging."""
        handler = RosaAdvisorHandler(mock_mcp)
        result = await handler.rosa_recommend_cluster_config(
            mock_context, environment='staging'
        )

        data = json.loads(result[0].text)
        assert data['environment'] == 'staging'
        config = data['recommended_config']
        assert config['multi_az'] is True
        assert config['replicas'] == 3
        assert config['private'] is False

    @pytest.mark.asyncio
    async def test_given_development_env_when_recommend_then_returns_dev_config(
        self, mock_mcp, mock_context
    ):
        """Test rosa_recommend_cluster_config for development."""
        handler = RosaAdvisorHandler(mock_mcp)
        result = await handler.rosa_recommend_cluster_config(
            mock_context, environment='development'
        )

        data = json.loads(result[0].text)
        assert data['environment'] == 'development'
        config = data['recommended_config']
        assert config['multi_az'] is False
        assert config['replicas'] == 2
        assert config['machine_type'] == 'm5.large'

    @pytest.mark.asyncio
    async def test_given_invalid_environment_when_recommend_then_raises_value_error(
        self, mock_mcp, mock_context
    ):
        """Test rosa_recommend_cluster_config rejects invalid environment."""
        handler = RosaAdvisorHandler(mock_mcp)

        with pytest.raises(ValueError, match="Invalid environment"):
            await handler.rosa_recommend_cluster_config(
                mock_context, environment='invalid'
            )


class TestRosaEstimateClusterCost:
    """Tests for rosa_estimate_cluster_cost."""

    @pytest.mark.asyncio
    async def test_given_valid_params_when_estimate_then_returns_reasonable_cost(
        self, mock_mcp, mock_context
    ):
        """Test rosa_estimate_cluster_cost returns reasonable estimate."""
        handler = RosaAdvisorHandler(mock_mcp)
        result = await handler.rosa_estimate_cluster_cost(
            mock_context,
            machine_type='m5.xlarge',
            replicas=3,
            multi_az=True,
            region='us-east-1',
        )

        data = json.loads(result[0].text)
        assert data['estimate']['machine_type'] == 'm5.xlarge'
        assert data['estimate']['replicas'] == 3
        assert data['estimate']['multi_az'] is True

        costs = data['costs']
        # Verify worker node costs
        assert costs['worker_nodes']['hourly_per_node'] == INSTANCE_SPECS['m5.xlarge']['hourly_cost']
        expected_hourly = INSTANCE_SPECS['m5.xlarge']['hourly_cost'] * 3
        assert costs['worker_nodes']['hourly_total'] == round(expected_hourly, 3)

        # Verify ROSA service fee
        assert costs['rosa_service_fee']['hourly'] == ROSA_SERVICE_HOURLY_COST

        # Verify total is positive and reasonable
        assert costs['estimated_monthly_total'] > 0
        # Should include at least worker + service fee
        assert costs['estimated_monthly_total'] > costs['worker_nodes']['monthly_total']

    @pytest.mark.asyncio
    async def test_given_unknown_machine_type_when_estimate_then_raises_value_error(
        self, mock_mcp, mock_context
    ):
        """Test rosa_estimate_cluster_cost rejects unknown machine type."""
        handler = RosaAdvisorHandler(mock_mcp)

        with pytest.raises(ValueError, match="Unknown machine type"):
            await handler.rosa_estimate_cluster_cost(
                mock_context, machine_type='x99.super', replicas=3
            )

    @pytest.mark.asyncio
    async def test_given_single_node_when_estimate_then_cost_scales_linearly(
        self, mock_mcp, mock_context
    ):
        """Test cost scales linearly with replicas."""
        handler = RosaAdvisorHandler(mock_mcp)

        result_1 = await handler.rosa_estimate_cluster_cost(
            mock_context, machine_type='m5.xlarge', replicas=1
        )
        result_3 = await handler.rosa_estimate_cluster_cost(
            mock_context, machine_type='m5.xlarge', replicas=3
        )

        data_1 = json.loads(result_1[0].text)
        data_3 = json.loads(result_3[0].text)

        worker_1 = data_1['costs']['worker_nodes']['monthly_total']
        worker_3 = data_3['costs']['worker_nodes']['monthly_total']

        # Worker cost should scale exactly 3x
        assert abs(worker_3 - worker_1 * 3) < 0.01
