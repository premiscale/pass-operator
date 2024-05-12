"""
End-to-end tests of the operator that validate the lifecycle of a PassSecret and managed secret objects.
"""


from unittest import TestCase
from kubernetes import client, config
from time import sleep

from tests.common import (
    load_data
)

from tests.e2e.lib import (
    # Tools
    generate_gpg_keypair,
    generate_ssh_keypair,
    # Docker
    build_operator_image,
    cleanup_operator_image,
    build_e2e_image,
    cleanup_e2e_image,
    # Helm
    install_pass_operator_crds,
    uninstall_pass_operator_crds,
    install_pass_operator,
    uninstall_pass_operator,
    install_pass_operator_e2e,
    uninstall_pass_operator_e2e
)

import logging
import sys


config.load_kube_config(
    context='pass-operator'
)

log = logging.getLogger(__name__)
logging.basicConfig(
    stream=sys.stdout,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    level=logging.INFO
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

        # Generate GPG and SSH keypairs for use in testing.
        self.gpg_passphrase = '1234'
        self.gpg_public, self.gpg_private, self.gpg_fingerprint = generate_gpg_keypair(
            passphrase=self.gpg_passphrase,
            delete_from_keyring=True
        )
        self.ssh_public, self.ssh_private = generate_ssh_keypair()

        # Operator artifacts.
        build_operator_image()
        install_pass_operator(
            ssh_value=self.ssh_private,
            gpg_value=self.gpg_private,
            gpg_key_id=self.gpg_fingerprint,
            namespace='pass-operator',
            ssh_createSecret=True,
            pass_storeSubPath='repo',
            gpg_createSecret=True,
            gpg_passphrase='',
            git_url='',
            git_branch='main'
        )
        install_pass_operator_crds()

        # e2e artifacts.
        build_e2e_image(
            ssh_public_key=self.ssh_public,
            gpg_key_id=self.gpg_fingerprint,
            gpg_key=self.gpg_public,
            gpg_passphrase=self.gpg_passphrase,
        )
        install_pass_operator_e2e(
            namespace='pass-operator-e2e'
        )

        return super().setUp()

    def test_initial_cluster_state(self) -> None:
        """
        Ensure the cluster's state is correct for e2e tests to proceed.
        """
        v1 = client.CoreV1Api()
        namespaces = v1.list_namespace().items

        def _check_namespaced_pods(namespace: client.V1Namespace) -> bool:
            """
            If any pods in the given namespace are not running or completed, return False.

            Args:
                namespace (client.V1Namespace): The namespace to check for running or completed pods.

            Returns:
                bool: True if all pods are running or completed, False otherwise.
            """
            for pod in v1.list_namespaced_pod(namespace.metadata.name).items:
                if pod.status.phase not in ('Running', 'Completed', 'Succeeded') or (pod.status.phase == 'Running' and any((not c.ready) for c in pod.status.container_statuses)):
                    log.warning(f'Pod {pod.metadata.name} in namespace {namespace.metadata.name} is not running or completed or completely ready.')
                    return False
            else:
                return True

        # Ensure that all pods on the cluster are in a ready state.
        for namespace in namespaces:
            while True:
                if _check_namespaced_pods(namespace):
                    break
                log.warning(f'Namespace {namespace.metadata.name} has pods that are not running or completed or completely ready.')
                sleep(3)

        log.info('All pods in the cluster are running or completed or completely ready.')

    def test_operator_initialized(self) -> None:
        """
        Test that the operator is running as intended in the cluster.
        """

    def tearDown(self) -> None:
        cleanup_operator_image()
        cleanup_e2e_image()
        uninstall_pass_operator()
        uninstall_pass_operator_crds()
        uninstall_pass_operator_e2e()
        return super().tearDown()