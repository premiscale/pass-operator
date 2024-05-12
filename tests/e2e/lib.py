from tests.common import run
from textwrap import dedent
from gnupg import GPG

import re
import os


def generate_ssh_keypair() -> tuple:
    """
    Generate an RSA SSH keypair.

    Returns:
        tuple: The public and private keys.
    """
    try:
        run('ssh-keygen -t ed25519 -f /tmp/id_rsa -q -N ""')

        return (
            run('cat /tmp/id_rsa.pub').stdout,
            run('cat /tmp/id_rsa').stdout
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


def build_operator_image(tag: str = '0.0.1') -> int:
    """
    Build the local operator image.

    Returns:
        int: The return code of the docker build or push command that failed, or 0 if both succeeded.
    """
    return run(f'docker build -t localhost/pass-operator:{tag} -f ./Dockerfile .').returnCode \
        or run(f'docker push localhost/pass-operator:{tag}').returnCode


def build_e2e_image(
    ssh_public_key: str,
    gpg_key_id: str,
    gpg_key: str,
    tag: str = '0.0.1',
    pass_version: str = '1.7.4-5',
    tini_version: str = 'v0.19.0',
    architecture: str = 'arm64',
    pass_directory: str = 'repo',
    gpg_passphrase: str = '',
    git_branch: str = 'main',
) -> int:
    """
    Build the e2e testing image for a local git server.

    Returns:
        int: The return code of the docker build or push command that failed, or 0 if both succeeded.
    """
    return run(f"""
        docker build .
            --build-arg PASS_VERSION={pass_version}
            --build-arg TINI_VERSION={tini_version}
            --build-arg ARCHITECTURE={architecture}
            --build-arg PASS_DIRECTORY={pass_directory}
            --build-arg PASS_GPG_KEY_ID={gpg_key_id}
            --build-arg PASS_GPG_KEY={gpg_key}
            --build-arg PASS_GPG_PASSPHRASE={gpg_passphrase}
            --build-arg PASS_GIT_BRANCH={git_branch}
            --build-arg SSH_PUBLIC_KEY={ssh_public_key}
            -f ./Dockerfile.e2e
            -t pass-operator-e2e:{tag}
    """)
    # or run(f'docker push localhost/pass-operator-e2e:{tag}').returnCode


def cleanup_operator_image(tag: str = '0.0.1') -> int:
    """
    Remove the operator image.

    Returns:
        int: The return code of the docker rmi command.
    """
    return run(f'docker rmi localhost/pass-operator:{tag}').returnCode


def cleanup_e2e_image(tag: str = '0.0.1') -> int:
    """
    Remove the e2e image.

    Returns:
        int: The return code of the docker rmi command.
    """
    return run(f'docker rmi localhost/pass-operator-e2e:{tag}').returnCode


def install_pass_operator_crds(namespace: str = 'default') -> int:
    """
    Install the operator CRDs in the cluster.

    Returns:
        int: The return code of the helm upgrade command.
    """
    return run(f'helm upgrade install --namespace {namespace} pass-operator-crds ./charts/operator-crds').returnCode


def uninstall_pass_operator_crds(namespace: str = 'default') -> int:
    """
    Uninstall the operator CRDs from the cluster.

    Returns:
        int: The return code of the helm uninstall command.
    """
    return run(f'helm uninstall --namespace {namespace} pass-operator-crds').returnCode


def install_pass_operator(
    ssh_value: str,
    gpg_value: str,
    gpg_key_id: str,
    namespace: str = 'default',
    priority: int = 100,
    ssh_createSecret: bool = True,
    pass_storeSubPath: str = 'repo',
    gpg_createSecret: bool = True,
    gpg_passphrase: str = '',
    git_url: str = '',
    git_branch: str = 'main'
) -> int:
    """
    Install the operator in the cluster.

    Returns:
        int: The return code of the helm upgrade command.
    """
    return run(f"""
        helm upgrade install --namespace {namespace} pass-operator ./charts/operator
            --set global.image.registry="localhost"
            --set operator.interval="3"
            --set operator.initial_delay="1"
            --set operator.priority="{priority}"
            --set operator.ssh.createSecret="{str(ssh_createSecret).lower()}"
            --set operator.pass.storeSubPath="{pass_storeSubPath}"
            --set operator.gpg.createSecret="{str(gpg_createSecret).lower()}"
            --set operator.gpg.value="{gpg_value}"
            --set operator.gpg.key_id="{gpg_key_id}"
            --set operator.gpg.passphrase="{gpg_passphrase}"
            --set operator.git.url="{git_url}"
            --set operator.git.branch="{git_branch}"
            --set operator.ssh.value="{ssh_value}"
    """).returnCode


def uninstall_pass_operator(namespace: str = 'default') -> int:
    """
    Uninstall the operator from the cluster.

    Returns:
        int: The return code of the helm uninstall command.
    """
    return run(f'helm uninstall --namespace {namespace} pass-operator').returnCode


def install_pass_operator_e2e(namespace: str = 'default') -> int:
    """
    Install the e2e testing image in the cluster.

    Returns:
        int: The return code of the helm upgrade command.
    """
    return run(f'helm upgrade install --namespace {namespace} pass-operator-e2e ./charts/operator-e2e').returnCode


def uninstall_pass_operator_e2e(namespace: str = 'default') -> int:
    """
    Uninstall the e2e testing image from the cluster.

    Returns:
        int: The return code of the helm uninstall command.
    """
    return run(f'helm uninstall --namespace {namespace} pass-operator-e2e').returnCode