"""
End-to-end tests of the operator that validate the lifecycle of a PassSecret and managed secret objects.
"""


from unittest import TestCase
from kubernetes import client, config

from tests.common import (
    load_data,
    # Docker
    build_operator_image,
    cleanup_operator_image,
    build_e2e_image,
    cleanup_e2e_image,
    # Helm
    install_pass_operator_crds,
    install_pass_operator,
    install_pass_operator_e2e
)


config.load_kube_config(
    context='pass-operator'
)


class PassSecretE2E(TestCase):
    """
    Methods for testing the Kubernetes operator end-to-end.
    """

    def setUp(self) -> None:
        """
        Create a PassSecret instance for use in testing.
        """
        self.passsecret_data_singular = load_data('test_singular_data')
        self.passsecret_data_singular_immutable = load_data('test_singular_data_immutable')
        self.passsecret_data_singular_different_managed_secret_name = load_data('test_singular_data_different_managed_secret_name')
        self.passsecret_data_zero = load_data('test_zero_data')
        self.passsecret_data_multiple = load_data('test_multiple_data')
        self.passsecret_singular_collision_1 = load_data('test_singular_data_collision_1')
        self.passsecret_singular_collision_2 = load_data('test_singular_data_collision_2')

        build_operator_image()
        install_pass_operator_crds()
        install_pass_operator(
            ssh_value=,
            gpg_value=,
            gpg_key_id=,
            namespace='pass-operator',
            ssh_createSecret: bool = True,
            pass_storeSubPath: str = 'repo',
            gpg_createSecret: bool = True,
            gpg_passphrase: str = '',
            git_url: str = '',
            git_branch: str = 'main'
        )

        build_e2e_image()
        install_pass_operator_e2e(
            namespace='pass-operator-e2e'
        )

        return super().setUp()

    def test_cluster_state(self) -> None:
        """
        Ensure the cluster's state is correct for e2e tests to proceed.
        """

    def test_operator_initialized(self) -> None:
        """
        Test that the operator is running as intended in the cluster.
        """

    def tearDown(self) -> None:
        cleanup_operator_image()
        cleanup_e2e_image()
        return super().tearDown()