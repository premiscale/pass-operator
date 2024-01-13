"""
A kubernetes operator that syncs and decrypts secrets from Linux password store (https://www.passwordstore.org/) git repositories
"""

import logging
import sys
import kopf
import kubernetes
import datetime
import yaml
import os

from typing import Any, Dict
from pathlib import Path
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from importlib import metadata as meta, resources
from functools import cache

from src.passoperator.git import GitRepo
from src.passoperator.utils import LogLevel


__version__ = meta.version('pass-operator')
log = logging.getLogger(__name__)


INTERVAL = int(os.getenv('PASSOPERATOR_INTERVAL') or 60)
pass_git_repo: GitRepo


@cache
def read_manifest(path: str) -> Dict[str, str]:
    """
    Read a secret template from file and cache the contents.

    Args:
        path (str): filename to read from data.

    Returns:
        str: contents of the file.
    """
    with resources.open_text('src.data', path) as obj:
        return yaml.safe_load(obj.read().rstrip())


def get_current_namespace(namespace_path: str ='/var/run/secrets/kubernetes.io/serviceaccount/namespace') -> str:
    """
    Get the current namespace this operator is deployed in. Refactored from the following GitHub issue.

        https://github.com/kubernetes-client/python/issues/363

    Args:
        namespace_path (str): Namespace path in the local filesystem. Defaults to '/var/run/secrets/kubernetes.io/serviceaccount/namespace'.

    Returns:
        str: the namespace this process is running within on K8s.
    """
    if os.path.exists(namespace_path):
        with open(namespace_path) as f:
            return f.read().strip()
    try:
        _, active_context = kubernetes.config.list_kube_config_contexts()
        return active_context['context']['namespace']
    except KeyError:
        return 'default'


@kopf.on.cleanup()
def cleanup(**kwargs) -> None:
    pass


@kopf.on.startup()
def start(param: Any, retry: Any, started: Any, runtime: Any, logger: Any, memo: Any, activity: Any, settings: Any) -> None:
    """
    Reconcile current state of PassSecret objects and remote git repository (desired state);
    bring current state of those objects into alignment.
    """
    log.info(f'Starting operator version {__version__}')
    # print(param, retry, started, runtime, logger, memo, activity, settings)


@kopf.on.update('PassSecret')
def update(**kwargs: Any) -> None:
    """
    An update was received on the PassSecret object, so attempt to update the corresponding Secret.
    """


@kopf.on.create('PassSecret')
def create(**kwargs: Any) -> None:
    """
    Create a new Secret from a PassSecret manifest.

    Args:
        version (str): version of the agent.

    Returns:
        None.
    """


@kopf.on.delete('PassSecret')
def delete(**kwargs: Any) -> None:
    """
    Remove the secret from memory.

    Args:
        spec (str):
    """


@kopf.timer('PassSecret', interval=INTERVAL, initial_delay=1)
def reconciliation() -> None:
    """
    Reconcile secrets across all namespaces and ensure they match the stored desired state.
    """
    pass_git_repo.git_pull()


@kopf.on.probe(id='now')
def get_current_timestamp(**kwargs) -> str:
    return datetime.datetime.utcnow().isoformat()


@kopf.on.probe(id='status')
def get_current_status(**kwargs) -> str:
    return 'ok'


def main() -> None:
    """
    Set up operator.
    """
    parser = ArgumentParser(description=__doc__, formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        '--version', action='store_true', default=False,
        help='Display the operator version.'
    )

    parser.add_argument(
        '--log-stdout', action='store_true', default=False,
        help='Print logs to stdout.'
    )

    parser.add_argument(
        '--log-level', default='info', choices=list(LogLevel), type=LogLevel.from_string,
        help='Set the logging level. Valid choices are info, debug, error, and warn (in any case).'
    )

    parser.add_argument(
        '--log-file', default='/opt/pass-operator/runtime.log', type=str,
        help='Log file location (if log-stdout is not provided).'
    )

    parser.add_argument(
        '--pass-binary', type=str, default='/usr/bin/pass',
        help='Path to an alternate pass binary.'
    )

    parser.add_argument(
        '--priority', type=int, default=100,
        help='Operator priority.'
    )

    parser.add_argument(
        '--pass-dir', type=str, default='/opt/pass-operator/repo',
        help='Pass directory to clone into.'
    )

    parser.add_argument(
        '--gpg-key-id', type=str,
        help='Private GPG key ID to use with pass to decrypt secrets.'
    )

    parser.add_argument(
        '--git-ssh-url', type=str,
        help='Repository\'s git domain to clone.'
    )

    parser.add_argument(
        '--git-branch', type=str, default='main',
        help='Git branch to pull secrets from in repository.'
    )

    args = parser.parse_args()

    if args.version:
        print(f'passoperator v{__version__}')
        sys.exit(0)

    # Configure logger
    if args.log_stdout:
        logging.basicConfig(
            stream=sys.stdout,
            format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            level=args.log_level.value
        )
    else:
        try:
            # Instantiate log path (when logging locally).
            if not Path.exists(Path(args.log_file)):
                Path(args.log_file).parent.mkdir(parents=True, exist_ok=True)

            logging.basicConfig(
                filename=args.log_file,
                format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
                level=args.log_level.value,
                filemode='a'
            )
        except (FileNotFoundError, PermissionError) as msg:
            log.error(f'Failed to configure logging, received: {msg}')
            sys.exit(1)

    global pass_git_repo
    pass_git_repo = GitRepo(
        repo_url=args.git_ssh_url,
        branch=args.git_branch,
        clone_location=args.pass_dir
    )

    kopf.run(
        # https://github.com/nolar/kopf/blob/main/kopf/cli.py#L86
        # paths: List[str],
        # modules: List[str],
        # peering_name: Optional[str]
        priority=args.priority,
        standalone=True,
        namespaces=get_current_namespace(),
        clusterwide=False,
        # liveness_endpoint: Optional[str],
    )