"""
End-to-end tests of the operator that validate the lifecycle of a PassSecret and managed secret objects.
"""


from importlib import resources
from unittest import TestCase
from kubernetes import client, config

import subprocess
import yaml


class PassSecretParseInverse(TestCase):
    """
    Test that from_dict and to_dict are inverse methods.
    """

    def setUp(self) -> None:
        """
        Create a PassSecret instance for use in testing.
        """
        with resources.open_text('tests.data.crd', 'test_singular_data.yaml') as f:
            self.passsecret_data = yaml.load(f, Loader=yaml.Loader)

        return super().setUp()

    def test_cluster_state(self) -> None:
        """
        Ensure the cluster's state is correct for e2e tests to proceed.
        """

    def test_operator_initialized(self) -> None:
        """
        Test that the operator is running as intended in the cluster.
        """