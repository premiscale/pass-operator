"""
End-to-end tests of the operator that validate the lifecycle of a PassSecret and managed secret objects.
"""


from unittest import TestCase
from kubernetes import client, config
from time import sleep
from deepdiff import DeepDiff
from http import HTTPStatus
from humps import decamelize

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


config.load_kube_config(
    context='pass-operator'
)


ATTEMPTS_TO_READ_SECRETS = 10


class PassSecretE2E(TestCase):
    """
    Methods for testing the Kubernetes operator end-to-end.
    """

    maxDiff = None

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
        This is just a helper method for when we're DeepDiff'ing locally-unencrypted (random) PassSecret data with the managed
        secret data that the operator decrypts and creates. This method is similar to what src.operator.secret looked like
        before it was refactored with attrs and cattrs, but it's different in that it ties together the randomly generated
        secret data with the original PassSecret objects, which is only useful for e2e testing.

        This method also ties together the snake_case and camelCase fields of the PassSecret and managed secret objects returned
        by the k8s client.

        Args:
            passsecret (dict): The PassSecret object that's submitted to the cluster to generate a managed secret.
            decrypted_passsecret (dict): The decrypted PassSecret object, so we can tie the managed secret and generated test data together.

        Returns:
            dict: The expected managed secret object from tying together a PassSecret manifest and a decrypted PassSecret
                manifest, which is generated on-the-fly every e2e run.
        """

        converted_managed_secret = {
            # These two fields are automatically provided by the dataclasses, anyway.
            'apiVersion': 'v1',
            'kind': 'Secret',
            'metadata': passsecret['spec']['managedSecret']['metadata'],
            'type': passsecret['spec']['managedSecret']['type'],
            'data': {}
        }

        # Handle optional fields.
        if 'immutable' in passsecret['spec']['managedSecret']:
            converted_managed_secret['immutable'] = passsecret['spec']['managedSecret']['immutable']
        else:
            converted_managed_secret['immutable'] = None

        if 'stringData' in passsecret['spec']['managedSecret']:
            converted_managed_secret['string_data'] = passsecret['spec']['managedSecret']['stringData']
        else:
            converted_managed_secret['string_data'] = None

        decamelized_converted_managed_secret = decamelize(converted_managed_secret)

        # Now populate the data with the proper keys.
        for key in passsecret['spec']['encryptedData']:
            passstore_path = passsecret['spec']['encryptedData'][key]
            decamelized_converted_managed_secret['data'][key] = b64Enc(decrypted_passsecret['spec']['encryptedData'][passstore_path])

        return decamelized_converted_managed_secret

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
            git_url='root@pass-operator-e2e:/root/repo.git',
            git_branch='main'
        )

    def setUp(self) -> None:
        """
        Common steps to run before every test.
        """

        # Wait for all pods in the cluster to be ready before running each test.
        if not check_cluster_pod_status():
            self.fail('Not all pods are determined ready in the cluster.')

    # def tearDown(self) -> None:
    #     return super().tearDown()

    def test_operator_singular_data(self) -> None:
        """
        Test that a PassSecret object with a single encrypted data field is created and managed by the operator correctly.
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

        _managedSecret: client.V1Secret

        # Check that the managed secret exists.
        for _ in range(ATTEMPTS_TO_READ_SECRETS):
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
                self.fail(
                    f'Failed to create managed secret for singular-data PassSecret: {e}'
                )
        else:
            self.fail(
                'Failed to read managed secret within the alotted time period.'
            )

        # Check that the managed secret contains the expected data. This is done by asserting that the difference between the
        # expected managed secret data and the actual managed secret data is an empty dictionary, with the exception of a few
        # fields that are not relevant to the test.
        self.assertDictEqual(
            DeepDiff(
                _managedSecret.to_dict(),
                # Convert the unencrypted PassSecret data to the format that the operator would have created the managed secret in.
                self.convertDecryptedPassSecrets(
                    self.passsecret_data_singular,
                    self.decrypted_passsecret_data_singular
                ),
                include_paths=[
                    "root['metadata']['name']",
                    "root['metadata']['namespace']",
                ],
                exclude_paths=[
                    "root['metadata']"
                ],
                ignore_order=True
            ),
            {}
        )

    def test_operator_zero_data(self) -> None:
        """
        Test that the application of a PassSecret with no data is handled correctly by the operator.
        """
        v1custom = client.CustomObjectsApi()
        v1 = client.CoreV1Api()

        # Create a namespaced PassSecret object, then vet that the managed secret both exists and contains the proper data (i.e., the operator did its job).
        v1custom.create_namespaced_custom_object(
            group='secrets.premiscale.com',
            version='v1alpha1',
            namespace='pass-operator',
            plural='passsecrets',
            body=self.passsecret_data_zero
        )

        _managedSecret: client.V1Secret

        # Check that the managed secret exists.
        for _ in range(ATTEMPTS_TO_READ_SECRETS):
            try:
                _managedSecret = v1.read_namespaced_secret(
                    name='zero-data',
                    namespace='pass-operator'
                )
                break
            except client.rest.ApiException as e:
                if e.status == HTTPStatus.NOT_FOUND:
                    sleep(3)
                    continue
                self.fail(
                    f'Failed to create managed secret for zero-data PassSecret: {e}'
                )
        else:
            self.fail(
                'Failed to read managed secret within the alotted time period.'
            )

        self.assertDictEqual(
            DeepDiff(
                _managedSecret.to_dict(),
                self.convertDecryptedPassSecrets(
                    self.passsecret_data_zero,
                    self.decrypted_passsecret_data_zero
                ),
                include_paths=[
                    "root['metadata']['name']",
                    "root['metadata']['namespace']",
                ],
                exclude_paths=[
                    "root['metadata']"
                ],
                ignore_order=True
            ),
            {}
        )

    def test_operator_multiple_data(self) -> None:
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
            body=self.passsecret_data_multiple
        )

        _managedSecret: client.V1Secret

        # Check that the managed secret exists.
        for _ in range(ATTEMPTS_TO_READ_SECRETS):
            try:
                _managedSecret = v1.read_namespaced_secret(
                    name='multiple-data',
                    namespace='pass-operator'
                )
                break
            except client.rest.ApiException as e:
                if e.status == HTTPStatus.NOT_FOUND:
                    sleep(3)
                    continue
                self.fail(
                    f'Failed to create managed secret for multiple-data PassSecret: {e}'
                )
        else:
            self.fail(
                'Failed to read managed secret within the alotted time period.'
            )

        # Check that the managed secret contains the expected data. This is done by asserting that the difference between the
        # expected managed secret data and the actual managed secret data is an empty dictionary, with the exception of a few
        # fields that are not relevant to the test.
        self.assertDictEqual(
            DeepDiff(
                _managedSecret.to_dict(),
                # Convert the unencrypted PassSecret data to the format that the operator would have created the managed secret in.
                self.convertDecryptedPassSecrets(
                    self.passsecret_data_multiple,
                    self.decrypted_passsecret_data_multiple
                ),
                include_paths=[
                    "root['metadata']['name']",
                    "root['metadata']['namespace']",
                ],
                exclude_paths=[
                    "root['metadata']"
                ],
                ignore_order=True
            ),
            {}
        )

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