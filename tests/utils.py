"""
Helper methods for managing the operator installation and making API calls.
"""


from textwrap import dedent
from subprocess import prun, PIPE, DEVNULL
from kubernetes import client, config
from functools import partial


config.load_kube_config(
    context='pass-operator'
)


run = partial(
    prun,
    shell=True,
    stdout=PIPE,
    stderr=DEVNULL
)


def build_operator_image(tag: str = '0.0.1') -> int:
    """
    Build the operator image.

    Returns:
        int: The return code of the docker build or push command that failed.
    """
    if (_code_1 := run(f'docker build -t localhost/pass-operator:{tag} .'.split(' ')).status_code) != 0 or (_code_2 := run(f'docker push localhost/pass-operator:{tag}'.split(' ')).status_code) != 0:
        return _code_1 or _code_2
    return 0


def cleanup_operator_image(tag: str = '0.0.1') -> int:
    """
    Remove the operator image.

    Returns:
        int: The return code of the docker rmi command.
    """
    return run(f'docker rmi localhost/pass-operator:{tag}'.split(' ')).status_code


def install_operator_crds(namespace: str = 'default') -> int:
    """
    Install the operator CRDs in the cluster.

    Returns:
        int: The return code of the helm upgrade command.
    """
    return run(
        dedent(
            f'helm upgrade install --namespace {namespace} pass-operator ./charts/operator-crds'
        ).split()
    ).status_code


def install_operator(
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
    return run(
        dedent(f"""
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
        ).split()
    ).status_code