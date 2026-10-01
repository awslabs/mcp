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

"""Tests for which resources the end-to-end harness acts on, against stubbed clients.

The harness addresses resources by the names in its config, so a name that belongs to something
else has to be refused rather than acted on. What is pinned here is which calls it makes.
"""

import pytest
from e2e_tests import deploy, run
from helpers import _client_error


_OURS = [{'Key': 'purpose', 'Value': deploy._PURPOSE}]


def _cluster(tags, status='available'):
    """Build a DescribeClusters entry."""
    return {'ClusterIdentifier': 'c', 'ClusterStatus': status, 'Tags': tags}


class TestPausingTouchesOnlyWhatTheHarnessCreated:
    """Teardown pauses the configured cluster only if it carries the purpose tag."""

    @pytest.mark.parametrize('status', ['available', 'paused'])
    def test_a_cluster_it_did_not_create_is_refused(self, mocker, status):
        """Unchecked, a run `up` had refused still paused the colliding cluster at teardown."""
        redshift = mocker.Mock()
        # Described once; a pause would wait on it again, which fails here rather than polling.
        redshift.describe_clusters.side_effect = [
            {'Clusters': [_cluster([], status)]},
            AssertionError('waited on a cluster it did not create'),
        ]

        with pytest.raises(deploy.DeployError, match='did not create it'):
            deploy.pause_cluster(redshift, 'c')

        redshift.pause_cluster.assert_not_called()

    def test_its_own_cluster_is_paused(self, mocker):
        """The check refuses only what is not the harness's."""
        redshift = mocker.Mock()
        redshift.describe_clusters.side_effect = [
            {'Clusters': [_cluster(_OURS)]},
            {'Clusters': [_cluster(_OURS, 'paused')]},
        ]

        assert deploy.pause_cluster(redshift, 'c') is True
        redshift.pause_cluster.assert_called_once_with(ClusterIdentifier='c')


class TestPausingReportsAClusterItCannotPause:
    """Teardown fails on a cluster it cannot pause; only an absent or paused one needs no pause."""

    def test_a_cluster_still_resuming_fails_the_pause(self, mocker):
        """Taken as not running, a cluster `up` left mid-resume billed after a clean teardown."""
        redshift = mocker.Mock()
        # Described once; waiting on it would describe it again, which fails here.
        redshift.describe_clusters.side_effect = [
            {'Clusters': [_cluster(_OURS, 'resuming')]},
            AssertionError('waited on a cluster it did not pause'),
        ]

        with pytest.raises(deploy.DeployError, match='cluster c is resuming'):
            deploy.pause_cluster(redshift, 'c')

        redshift.pause_cluster.assert_not_called()

    @pytest.mark.parametrize(
        'described',
        [
            {'Clusters': [_cluster(_OURS, 'paused')]},
            _client_error('ClusterNotFound', 'not found', operation='DescribeClusters'),
        ],
        ids=['paused', 'absent'],
    )
    def test_a_cluster_that_bills_no_compute_needs_nothing(self, mocker, described):
        """Paused, it bills storage only, which is what a pause is for; absent, it bills nothing."""
        redshift = mocker.Mock()
        redshift.describe_clusters.side_effect = [
            described,
            AssertionError('waited on a cluster that needed no pause'),
        ]

        assert deploy.pause_cluster(redshift, 'c') is False
        redshift.pause_cluster.assert_not_called()


class TestOwnershipIsCheckedBeforeAnythingIsCreated:
    """Every configured name is checked before a run creates anything."""

    def _session(self, mocker, foreign=None):
        """Wire a session where every resource exists and is the harness's, except `foreign`.

        A role is named by its config name, since the config names two.
        """
        iam, redshift, serverless = mocker.Mock(), mocker.Mock(), mocker.Mock()

        def tags(kind):
            return [] if kind == foreign else _OURS

        iam.get_role.side_effect = lambda RoleName: {
            'Role': {'Arn': f'arn:{RoleName}', 'Tags': tags(RoleName)}
        }
        redshift.describe_clusters.return_value = {'Clusters': [_cluster(tags('cluster'))]}
        serverless.get_namespace.return_value = {'namespace': {'namespaceArn': 'arn:namespace'}}
        serverless.get_workgroup.return_value = {'workgroup': {'workgroupArn': 'arn:workgroup'}}
        serverless.list_tags_for_resource.side_effect = lambda resourceArn: {
            'tags': [
                {'key': tag['Key'], 'value': tag['Value']}
                for tag in tags(resourceArn.removeprefix('arn:'))
            ]
        }

        # Every client the session hands out, so a check of what was called misses none of them.
        created = {'iam': iam, 'redshift': redshift, 'redshift-serverless': serverless}
        session = mocker.Mock()
        session.client.side_effect = lambda service: created.setdefault(service, mocker.Mock())
        return session, created

    @pytest.mark.parametrize(
        ('foreign', 'kind'),
        [
            ('s3-read-role', 'role'),
            ('denied-batch-role', 'role'),
            ('cluster', 'cluster'),
            ('namespace', 'namespace'),
            ('workgroup', 'workgroup'),
        ],
    )
    def test_a_name_that_belongs_to_something_else_is_refused(self, mocker, foreign, kind):
        """Each resource the config names is refused alike, and nothing is changed."""
        session, clients = self._session(mocker, foreign)
        config = mocker.Mock(
            s3_read_role_name='s3-read-role', denied_batch_role_name='denied-batch-role'
        )

        with pytest.raises(deploy.DeployError, match=f'{kind} .* did not create it'):
            deploy.check_ownership(session, config)

        for client in clients.values():
            assert all(
                call[0].startswith(('get_', 'describe_', 'list_')) for call in client.method_calls
            ), client.method_calls

    def test_names_the_harness_owns_pass(self, mocker):
        """The check refuses only what is not the harness's."""
        session, _ = self._session(mocker)

        deploy.check_ownership(session, mocker.Mock())

    def test_names_that_do_not_exist_pass(self, mocker):
        """Absent is fine: `up` creates it. A fresh account has none of them."""
        session, clients = self._session(mocker)
        iam, redshift, serverless = (
            clients['iam'],
            clients['redshift'],
            clients['redshift-serverless'],
        )
        iam.get_role.side_effect = _client_error('NoSuchEntity', 'not found', operation='GetRole')
        redshift.describe_clusters.side_effect = _client_error(
            'ClusterNotFound', 'not found', operation='DescribeClusters'
        )
        for method in (serverless.get_namespace, serverless.get_workgroup):
            method.side_effect = _client_error('ResourceNotFoundException', 'not found')

        deploy.check_ownership(session, mocker.Mock())


class TestARefusedRunTearsNothingDown:
    """A run refused before it created anything has nothing of its own to tear down."""

    def test_a_colliding_name_stops_the_run_before_teardown_is_armed(self, mocker):
        """Refused under the `finally`, the run went on to tear down, and paused the collision."""
        mocker.patch('e2e_tests.run._session')
        mocker.patch(
            'e2e_tests.deploy.check_ownership',
            side_effect=deploy.DeployError('cluster c exists but carries no purpose tag'),
        )
        # Raising, so a run that got past the check stops here rather than writing agent files.
        up = mocker.patch(
            'e2e_tests.deploy.up', side_effect=AssertionError('created before the ownership check')
        )
        teardown = mocker.patch('e2e_tests.run._teardown')

        with pytest.raises(deploy.DeployError):
            run.test(mocker.Mock(), [], keep_up=False)

        up.assert_not_called()
        teardown.assert_not_called()

    def test_a_failure_after_the_check_still_tears_down(self, mocker):
        """By then something may be billing, which is what the `finally` is for."""
        mocker.patch('e2e_tests.run._session')
        mocker.patch('e2e_tests.deploy.check_ownership')
        mocker.patch('e2e_tests.deploy.up', side_effect=deploy.DeployError('cluster c timed out'))
        teardown = mocker.patch('e2e_tests.run._teardown', return_value=True)

        with pytest.raises(deploy.DeployError):
            run.test(mocker.Mock(), [], keep_up=False)

        teardown.assert_called_once()
