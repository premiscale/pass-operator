from tests.common import run
from gnupg import GPG
from kubernetes import client
from time import sleep as syncsleep
from passoperator.utils import b64Enc

import re
import os
import logging


log = logging.getLogger(__name__)


def check_cluster_pod_status(namespace: str | None = None) -> bool:
    """
    Ensure all pods are running or completed or completely ready on a cluster.

    Args:
        namespace (str, optional): The namespace to check for running or completed pods. If None, checks all namespaces. Defaults to None.

    Returns:
        bool: True if all pods are running or completed or completely ready, False otherwise.
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
            syncsleep(3)

    log.info('All pods in the cluster are running or completed or completely ready.')


def generate_ssh_keypair() -> tuple:
    """
    Generate an RSA SSH keypair.

    Returns:
        tuple: The public and private keys.
    """
    try:
        run(['ssh-keygen', '-t', 'ed25519', '-f', '/tmp/id_rsa', '-q', '-N', ''])

        return (
            run(['cat', '/tmp/id_rsa.pub']).stdout,
            run(['cat', '/tmp/id_rsa']).stdout
        )
    finally:
        if os.path.exists('/tmp/id_rsa'):
            os.remove('/tmp/id_rsa')
        if os.path.exists('/tmp/id_rsa.pub'):
            os.remove('/tmp/id_rsa.pub')


def generate_gpg_keypair(passphrase: str, delete_from_keyring: bool = False) -> tuple:
    """
    Generate a test GPG keypair.

    Args:
        passphrase (str): The passphrase for the keypair.

    Returns:
        tuple: The public and private keys followed by the key ID.

    Raises:
        ValueError: If the passphrase is empty.
    """
    if len(passphrase) == 0:
        raise ValueError('Passphrase must not be empty.')

    try:
        gpg = GPG(gnupghome=os.path.expandvars('$HOME/.gnupg'))
        key = gpg.gen_key(
            gpg.gen_key_input(
                key_type='RSA',
                key_length=4096,
                name_real='Emma Test',
                name_email='emmatest@premiscale.com',
                passphrase=passphrase
            )
        )

        return (
            gpg.export_keys(key.fingerprint, passphrase=passphrase),
            gpg.export_keys(key.fingerprint, passphrase=passphrase, secret=True),
            key.fingerprint
        )
    finally:
        if delete_from_keyring:
            delete_gpg_keypair(key.fingerprint, passphrase)


def delete_gpg_keypair(key_id: str, passphrase: str) -> None:
    """
    Delete a GPG keypair.

    Args:
        key_id (str): The key ID to delete.
        passphrase (str): The passphrase for the key.
    """
    if len(passphrase) == 0:
        raise ValueError('Passphrase must not be empty.')

    gpg = GPG(gnupghome=os.path.expandvars('$HOME/.gnupg'))
    gpg.delete_keys(key_id, secret=True, passphrase=passphrase)
    gpg.delete_keys(key_id)


def build_e2e_image(
    tag: str = '0.0.1',
    pass_version: str = '1.7.4-5',
    tini_version: str = 'v0.19.0',
    architecture: str = 'arm64'
) -> int:
    """
    Build the e2e testing image for a local git server.

    Returns:
        int: The return code of the docker build or push command that failed, or 0 if both succeeded.
    """

    return run([
        'docker', 'build', '-t', f'localhost:5000/pass-operator-e2e:{tag}', '-f', './Dockerfile.e2e', '.',
        '--build-arg', f'PASS_VERSION={pass_version}',
        '--build-arg', f'TINI_VERSION={tini_version}',
        '--build-arg', f'ARCHITECTURE={architecture}',
    ]).returnCode or run(['docker', 'push', f'localhost:5000/pass-operator-e2e:{tag}']).returnCode


def install_pass_operator_e2e(
        ssh_value: str,
        gpg_value: str,
        gpg_key_id: str,
        namespace: str = 'default',
        ssh_createSecret: bool = True,
        pass_storeSubPath: str = 'repo',
        gpg_createSecret: bool = True,
        gpg_passphrase: str = '',
        git_branch: str = 'main',
        image_tag: str = '0.0.1'
    ) -> int:
    """
    Install the e2e testing image in the cluster.

    Returns:
        int: The return code of the helm upgrade command.
    """
    return run([
        'helm', 'upgrade', '--install', '--namespace', namespace, '--create-namespace', 'pass-operator-e2e', './helm/operator-e2e',
            '--set', 'global.image.registry=localhost:5000',
            '--set', f'deployment.image.tag={image_tag}',
            '--set', f'operator.ssh.createSecret={str(ssh_createSecret).lower()}',
            '--set', f'operator.pass.storeSubPath={pass_storeSubPath}',
            '--set', f'operator.gpg.createSecret={str(gpg_createSecret).lower()}',
            '--set', f'operator.gpg.value={b64Enc(gpg_value)}',
            '--set', f'operator.gpg.key_id={gpg_key_id}',
            '--set', f'operator.gpg.passphrase={gpg_passphrase}',
            '--set', f'operator.git.branch={git_branch}',
            '--set', f'operator.ssh.value={b64Enc(ssh_value)}'
    ]).returnCode


def uninstall_pass_operator_e2e(namespace: str = 'default') -> int:
    """
    Uninstall the e2e testing image from the cluster.

    Returns:
        int: The return code of the helm uninstall command.
    """
    return run(['helm', 'uninstall', '--namespace', namespace, 'pass-operator-e2e']).returnCode


def cleanup_e2e_image(tag: str = '0.0.1') -> int:
    """
    Remove the e2e image.

    Returns:
        int: The return code of the docker rmi command.
    """
    return run(['docker', 'rmi', f'localhost:5000/pass-operator-e2e:{tag}']).returnCode


def install_pass_operator_crds(namespace: str = 'default') -> int:
    """
    Install the operator CRDs in the cluster.

    Returns:
        int: The return code of the helm upgrade command.
    """
    return run(['helm', 'upgrade', '--install', 'pass-operator-crds', './helm/operator-crds', '--namespace', namespace, '--create-namespace']).returnCode


def uninstall_pass_operator_crds(namespace: str = 'default') -> int:
    """
    Uninstall the operator CRDs from the cluster.

    Returns:
        int: The return code of the helm uninstall command.
    """
    return run(['helm', 'uninstall', '--namespace', namespace, 'pass-operator-crds']).returnCode


def cleanup_operator_image(tag: str = '0.0.1') -> int:
    """
    Remove the operator image.

    Returns:
        int: The return code of the docker rmi command.
    """
    return run(['docker', 'rmi', f'localhost:5000/pass-operator:{tag}']).returnCode


def build_operator_image(tag: str = '0.0.1') -> int:
    """
    Build the local operator image.

    Returns:
        int: The return code of the docker build or push command that failed, or 0 if both succeeded.
    """
    return run(['docker', 'build', '-t', f'localhost:5000/pass-operator:{tag}', '-f', './Dockerfile.develop', '.']).returnCode \
        or run(['docker', 'push', f'localhost:5000/pass-operator:{tag}'])


def install_pass_operator(
    ssh_value: str,
    gpg_value: str,
    gpg_key_id: str,
    git_url: str,
    namespace: str = 'default',
    priority: int = 100,
    ssh_createSecret: bool = True,
    pass_storeSubPath: str = 'repo',
    gpg_createSecret: bool = True,
    gpg_passphrase: str = '',
    git_branch: str = 'main',
    image_tag: str = '0.0.1'
) -> int:
    """
    Install the operator in the cluster.

    Returns:
        int: The return code of the helm upgrade command.
    """
    return run([
        'helm', 'upgrade', '--install', 'pass-operator', './helm/operator', '--namespace', namespace, '--create-namespace',
            '--set', 'global.image.registry=localhost:5000',
            '--set', f'deployment.image.tag={image_tag}',
            '--set', 'operator.interval=60',
            '--set', 'operator.initial_delay=1',
            '--set', f'operator.priority={priority}',
            '--set', f'operator.ssh.createSecret={str(ssh_createSecret).lower()}',
            '--set', f'operator.pass.storeSubPath={pass_storeSubPath}',
            '--set', f'operator.gpg.createSecret={str(gpg_createSecret).lower()}',
            '--set', f'operator.gpg.value={b64Enc(gpg_value)}',
            '--set', f'operator.gpg.key_id={gpg_key_id}',
            '--set', f'operator.gpg.passphrase={gpg_passphrase}',
            '--set', f'operator.git.url={git_url}',
            '--set', f'operator.git.branch={git_branch}',
            '--set', f'operator.ssh.value={b64Enc(ssh_value)}'
    ]).returnCode


def uninstall_pass_operator(namespace: str = 'default') -> int:
    """
    Uninstall the operator from the cluster.

    Returns:
        int: The return code of the helm uninstall command.
    """
    return run(['helm', 'uninstall', '--namespace', namespace, 'pass-operator']).returnCode