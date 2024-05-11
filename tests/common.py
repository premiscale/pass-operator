"""
Helper interface with common methods for managing the operator installation and making API calls.
"""


from textwrap import dedent
from importlib import resources
from subprocess import Popen, PIPE
from kubernetes import client, config
from gnupg import GPG
from dataclasses import dataclass

import yaml


@dataclass
class CommandOutput:
    stdout: str
    stderr: str
    returnCode: int


def run(command: str, split: str = ' ', shell=False) -> CommandOutput:
    """
    Run a command and return the output, error, and return code.
    Args:
        command (str): shell command to run as a string.
        split (str, optional): character to split the command by. Defaults to ' '.
        shell (bool, optional): whether to run the command in a shell. Defaults to False.
    Returns:
        CommandOutput: output, error, and return code.
    """
    with Popen(dedent(command).lstrip().rstrip().split(split), stdout=PIPE, stderr=PIPE, text=True, shell=shell, encoding='utf-8') as p:
        stdout, stderr = p.communicate() # blocking
        return CommandOutput(stdout.rstrip(), stderr.rstrip(), p.returncode)


def load_data(file: str, dtype: str = 'crd') -> dict:
    """
    Load a YAML file into a dictionary.

    Args:
        file (str): The path to the YAML file.
        dtype (str): The type of data to load. Defaults to 'crd'.

    Returns:
        dict: The dictionary representation of the YAML file.
    """
    with resources.open_text(f'tests.data.{dtype}', f'{file}.yaml') as f:
        return yaml.load(f, Loader=yaml.Loader)


def generate_ssh_keypair() -> tuple:
    """
    Generate an RSA SSH keypair.

    Returns:
        tuple: The public and private keys.
    """
    return (
        run('ssh-keygen -t rsa -f /tmp/id_rsa -q -N ""').stdout.split('\n')[-2],
        run('cat /tmp/id_rsa.pub').stdout
    )


def generate_gpg_keypair() -> tuple:
    """
    Generate a test GPG keypair.

    Returns:
        tuple: The public and private keys followed by the key ID.
    """
    return (
        run('gpg ').stdout,
        run('gpg ').stdout,
        run('gpg --list-secret-keys --keyid-format LONG').stdout
    )


def build_operator_image(tag: str = '0.0.1') -> int:
    """
    Build the operator image.

    Returns:
        int: The return code of the docker build or push command that failed, or 0 if both succeeded.
    """
    return run(f'docker build -t localhost/pass-operator:{tag} -f ./Dockerfile .').returnCode \
        or run(f'docker push localhost/pass-operator:{tag}').returnCode


def build_e2e_image(tag: str = '0.0.1') -> int:
    """
    Build the e2e testing image for a local git server.

    Returns:
        int: The return code of the docker build or push command that failed, or 0 if both succeeded.
    """
    return run(f'docker build . -f ./Dockerfile.e2e -t pass-operator-e2e:{tag}').returnCode \
        or run(f'docker push localhost/pass-operator-e2e:{tag}').returnCode


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
    return run(f'helm upgrade install --namespace {namespace} pass-operator ./charts/operator-crds').returnCode


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
        """
    ).returnCode


def install_pass_operator_e2e(namespace: str = 'default') -> int:
    """
    Install the e2e testing image in the cluster.

    Returns:
        int: The return code of the helm upgrade command.
    """
    return run(f'helm upgrade install --namespace {namespace} pass-operator-e2e ./charts/operator-e2e').returnCode