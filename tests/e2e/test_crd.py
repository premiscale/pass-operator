"""
End-to-end tests of the operator that validate the lifecycle of a PassSecret and managed secret objects.
"""


from unittest import TestCase
from kubernetes import client, config

from tests.common import (
    load_data
)

from tests.e2e.lib import (
    # Tools
    check_cluster_pod_status,
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


# Generate GPG and SSH keypairs for use in testing.
gpg_passphrase = '1234'
gpg_public_key, gpg_private_key, gpg_fingerprint = generate_gpg_keypair(
    passphrase=gpg_passphrase,
    delete_from_keyring=True
)
ssh_public_key, ssh_private_key = generate_ssh_keypair()

# e2e artifacts that the operator depends on to run.
build_e2e_image(
    ssh_public_key=ssh_public_key,
    gpg_key_id=gpg_fingerprint,
    gpg_key=gpg_public_key,
    gpg_passphrase=gpg_passphrase,
)
install_pass_operator_e2e(
    namespace='pass-operator-e2e'
)

# Build and install operator artifacts.
install_pass_operator_crds()
build_operator_image()
install_pass_operator(
    ssh_value=ssh_private_key,
    gpg_value=gpg_private_key,
    gpg_key_id=gpg_fingerprint,
    namespace='pass-operator',
    ssh_createSecret=True,
    pass_storeSubPath='repo',
    gpg_createSecret=True,
    gpg_passphrase='',
    git_url='git+ssh://localhost:2222/pass-operator.git',
    git_branch='main'
)

cleanup_operator_image()
cleanup_e2e_image()


class PassSecret(TestCase):
    """
    Methods for testing the Kubernetes operator end-to-end.
    """

    def setUp(self) -> None:
        """
        Create a PassSecret instance for use in testing.
        """

        # Wait for all pods in the cluster to be ready.
        check_cluster_pod_status()

        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()

    def test_operator_singular_data(self) -> None:
        """
        Test that the operator is running as intended in the cluster.
        """
        self.passsecret_data_singular = load_data('test_singular_data')

    def test_operator_zero_data(self) -> None:
        """
        Test that the operator is running as intended in the cluster.
        """
        self.passsecret_data_zero = load_data('test_zero_data')

    def test_operator_multiple_data(self) -> None:
        """
        Test that the operator is running as intended in the cluster.
        """
        self.passsecret_data_multiple = load_data('test_multiple_data')

    def test_operator_singular_data_immutable(self) -> None:
        """
        Test that the operator is running as intended in the cluster.
        """
        self.passsecret_data_singular_immutable = load_data('test_singular_data_immutable')

    def test_operator_singular_data_different_managed_secret_name(self) -> None:
        """
        Test that the operator is running as intended in the cluster.
        """
        self.passsecret_data_singular_different_managed_secret_name = load_data('test_singular_data_different_managed_secret_name')

    def test_operator_singular_collision_1(self) -> None:
        """
        Test that the operator is running as intended in the cluster.
        """
        self.passsecret_singular_collision_1 = load_data('test_singular_data_collision_1')

    def test_operator_singular_collision_2(self) -> None:
        """
        Test that the operator is running as intended in the cluster.
        """
        self.passsecret_singular_collision_2 = load_data('test_singular_data_collision_2')