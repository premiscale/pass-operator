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
import string
import random


log = logging.getLogger(__name__)
logging.basicConfig(
    stream=sys.stdout,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    level=logging.INFO
)

# # Uninstalling prior Helm chart installations.
# uninstall_pass_operator(namespace='pass-operator')
# uninstall_pass_operator_e2e(namespace='pass-operator')
# uninstall_pass_operator_crds(namespace='pass-operator')

# Generate GPG and SSH keypairs for use in testing.
log.info('Generating GPG and SSH keypairs for testing.')
gpg_passphrase = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
gpg_public_key, gpg_private_key, gpg_fingerprint = generate_gpg_keypair(
    passphrase=gpg_passphrase,
    delete_from_keyring=True
)
ssh_public_key, ssh_private_key = generate_ssh_keypair()

log.info('Building e2e image')
# e2e artifacts that the operator depends on to run.
build_e2e_image()

log.info('Installing pass-operator-e2e')
install_pass_operator_e2e(
    ssh_value=ssh_public_key,
    gpg_value=gpg_public_key,
    gpg_key_id=gpg_fingerprint,
    namespace='pass-operator',
    ssh_createSecret=True,
    pass_storeSubPath='repo',
    gpg_createSecret=True,
    gpg_passphrase=gpg_passphrase,
    git_branch='main'
)

log.info('Installing pass-operator crds')

# Build and install operator artifacts.
install_pass_operator_crds(namespace='pass-operator')

log.info('Building operator image')
build_operator_image()

log.info('Installing pass-operator')
install_pass_operator(
    ssh_value=ssh_private_key,
    gpg_value=gpg_private_key,
    gpg_key_id=gpg_fingerprint,
    namespace='pass-operator',
    ssh_createSecret=True,
    pass_storeSubPath='repo',
    gpg_createSecret=True,
    gpg_passphrase=gpg_passphrase,
    git_url='root@pass-operator-e2e:/opt/operator/repo.git',
    git_branch='main'
)

cleanup_e2e_image()
cleanup_operator_image()

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