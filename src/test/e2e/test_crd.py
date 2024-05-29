"""
End-to-end tests of the operator that validate the lifecycle of a PassSecret and managed secret objects.
"""


from unittest import TestCase
from kubernetes import client, config
from time import sleep
from deepdiff import DeepDiff
from http import HTTPStatus

from passoperator.utils import b64Enc

from test.common import (
    load_data,
    random_secret
)

from test.e2e.lib import (
    # Tools
    check_cluster_pod_status,
    generate_gpg_keypair,
    generate_ssh_keypair,
    generate_unencrypted_crds,
    cleanup_unencrypted_crds,
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


log = logging.getLogger(__name__)
logging.basicConfig(
    stream=sys.stdout,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    level=logging.INFO
)

# Generate GPG and SSH keypairs for use in testing.

config.load_kube_config(
    context='pass-operator'
)


class PassSecretE2E(TestCase):
    """
    Methods for testing the Kubernetes operator end-to-end.
    """

    ## Test data attributes.

    passsecret_data_singular: dict
    decrypted_passsecret_data_singular: dict

    passsecret_data_zero: dict
    decrypted_passsecret_data_zero: dict

    passsecret_data_multiple: dict
    decrypted_passsecret_data_multiple: dict

    passsecret_data_singular_immutable: dict
    decrypted_passsecret_data_singular_immutable: dict

    passsecret_data_singular_different_managed_secret_name: dict
    decrypted_passsecret_data_singular_different_managed_secret_name: dict

    passsecret_singular_collision_1: dict
    decrypted_passsecret_singular_collision_1: dict

    passsecret_singular_collision_2: dict
    decrypted_passsecret_singular_collision_2: dict

    ##

    @staticmethod
    def convertDecryptedPassSecrets(passsecret: dict, decrypted_passsecret: dict) -> dict:
        """
        This is just a helper method for DeepDiff'ing locally-unencrypted (random) PassSecret data with the managed
        secret data that the operator decrypts and creates. This method is similar to what src.operator.secret looked like
        before it was refactored with attrs and cattrs.

        Args:
            passsecret (dict): The PassSecret object.
            decrypted_passsecret (dict): The decrypted PassSecret object.
        """

        converted_managed_secret = {
            # These two fields are automatically provided by the dataclasses, anyway.
            'apiVersion': 'v1',
            'kind': 'Secret',
            'metadata': passsecret['spec']['managedSecret']['metadata'],
            'type': passsecret['spec']['managedSecret']['type'],
            'data': {}
        }

        # Now populate the data with the proper keys.
        for key in passsecret['spec']['managedSecret']['data']:
            passstore_path = passsecret['spec']['managedSecret']['data'][key]

            converted_managed_secret['data'][key] = b64Enc(
                decrypted_passsecret['spec']['managedSecret']['data'][passstore_path]
            )

        return converted_managed_secret

    @classmethod
    def setUpClass(cls) -> None:
        """
        Common steps to run before all tests.
        """
        cleanup_unencrypted_crds()

        gpg_passphrase = random_secret()

        ## Generate GPG and SSH keypairs for use in testing.
        gpg_public_key, gpg_private_key, gpg_fingerprint = generate_gpg_keypair(
            passphrase=gpg_passphrase,
            delete_from_keyring=True
        )
        ssh_public_key, ssh_private_key = generate_ssh_keypair()

        ## Generate unencrypted CRDs; these need to both be local for unit tests to reference and in the e2e image for the operator to reference.
        generate_unencrypted_crds()

        cls.passsecret_data_singular = load_data('test_singular_data')
        cls.decrypted_passsecret_data_singular = load_data('test_singular_data.unencrypted')

        cls.passsecret_data_zero = load_data('test_zero_data')
        cls.decrypted_passsecret_data_zero = load_data('test_zero_data.unencrypted')

        cls.passsecret_data_multiple = load_data('test_multiple_data')
        cls.decrypted_passsecret_data_multiple = load_data('test_multiple_data.unencrypted')

        cls.passsecret_data_singular_immutable = load_data('test_singular_data_immutable')
        cls.decrypted_passsecret_data_singular_immutable = load_data('test_singular_data_immutable.unencrypted')

        cls.passsecret_data_singular_different_managed_secret_name = load_data('test_singular_data_different_managed_secret_name')
        cls.decrypted_passsecret_data_singular_different_managed_secret_name = load_data('test_singular_data_different_managed_secret_name.unencrypted')

        cls.passsecret_singular_collision_1 = load_data('test_singular_data_collision_1')
        cls.decrypted_passsecret_singular_collision_1 = load_data('test_singular_data_collision_1.unencrypted')

        cls.passsecret_singular_collision_2 = load_data('test_singular_data_collision_2')
        cls.decrypted_passsecret_singular_collision_2 = load_data('test_singular_data_collision_2.unencrypted')

        ## Build the e2e image and install the pass-operator-e2e Helm chart.
        build_e2e_image()
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

        ## Install the pass-operator Helm chart and CRDs.
        install_pass_operator_crds(namespace='pass-operator')
        build_operator_image()
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

    def setUp(self) -> None:
        """
        Common steps to run before every test.
        """

        # Wait for all pods in the cluster to be ready before running each test.
        check_cluster_pod_status()

    # def tearDown(self) -> None:
    #     return super().tearDown()

    def test_operator_singular_data(self) -> None:
        """
        Test that the operator is running as intended in the cluster.
        """
        v1custom = client.CustomObjectsApi()
        v1 = client.CoreV1Api()

        # Create a namespaced PassSecret object, then vet that the managed secret both exists and contains the proper data (i.e., the operator did its job).
        v1custom.create_namespaced_custom_object(
            group='secrets.premiscale.com',
            version='v1alpha1',
            namespace='pass-operator',
            plural='passsecrets',
            body=self.passsecret_data_singular
        )

        # Check that the managed secret exists.
        while True:
            try:
                _managedSecret = v1.read_namespaced_secret(
                    name='singular-data',
                    namespace='pass-operator'
                )
                break
            except client.rest.ApiException as e:
                if e.status == HTTPStatus.NOT_FOUND:
                    sleep(3)
                    continue
                log.error(e)

        # Check that the managed secret contains the proper data.
        self.assertDictEqual(
            DeepDiff(
                dict(_managedSecret.data),
                # Convert the unencrypted PassSecret data to the format that the operator would have created the managed secret in.
                self.convertDecryptedPassSecrets(
                    self.passsecret_data_singular,
                    self.decrypted_passsecret_data_singular
                ),
                exclude_paths=[
                    "root['metadata']['labels']",
                    "root['metadata']['annotations']",
                    "root['spec']['managedSecret']['apiVersion']",
                    "root['spec']['managedSecret']['finalizers']"
                ]
            ),
            {}
        )

    def test_operator_zero_data(self) -> None:
        """
        Test that the operator is running as intended in the cluster.
        """

    def test_operator_multiple_data(self) -> None:
        """
        Test that the operator is running as intended in the cluster.
        """

    def test_operator_singular_data_immutable(self) -> None:
        """
        Test that the operator is running as intended in the cluster.
        """

    def test_operator_singular_data_different_managed_secret_name(self) -> None:
        """
        Test that the operator is running as intended in the cluster.
        """

    def test_operator_singular_collision_1(self) -> None:
        """
        Test that the operator is running as intended in the cluster.
        """

    def test_operator_singular_collision_2(self) -> None:
        """
        Test that the operator is running as intended in the cluster.
        """

    @classmethod
    def tearDownClass(cls) -> None:
        """
        Common steps to run after all tests.
        """

        ## Reset the cluster and clean up resources.
        cleanup_e2e_image()
        cleanup_operator_image()
        cleanup_unencrypted_crds()

        uninstall_pass_operator(namespace='pass-operator')
        uninstall_pass_operator_e2e(namespace='pass-operator')
        uninstall_pass_operator_crds(namespace='pass-operator')