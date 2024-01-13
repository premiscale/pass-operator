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
pass_git_repo: GitRepo


# Environment variables to configure the operator's performance.
OPERATOR_INTERVAL = int(os.getenv('OPERATOR_INTERVAL') or 60)
OPERATOR_INITIAL_DELAY = int(os.getenv('OPERATOR_INITIAL_DELAY') or 3)
OPERATOR_PRIORITY = int(os.getenv('OPERATOR_PRIORITY') or 100)
OPERATOR_NAMESPACE = os.getenv('OPERATOR_NAMESPACE') or 'default'

# Environment variables to configure pass.
PASS_BINARY = os.getenv('PASS_BINARY') or '/usr/bin/pass'
PASS_DIRECTORY = os.getenv('PASS_DIRECTORY') or '/opt/pass-operator/repo'
PASS_GPG_KEY_ID = os.getenv('PASS_GPG_KEY_ID')
PASS_GIT_URL = os.getenv('PASS_GIT_URL')
PASS_GIT_BRANCH = os.getenv('PASS_GIT_BRANCH') or 'main'
PASS_SSH_PRIVATE_KEY = os.getenv('PASS_SSH_PRIVATE_KEY')


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


# @kopf.on.cleanup()
# def cleanup(**kwargs) -> None:
#     pass


@kopf.on.startup()
def start(param: Any, retry: Any, started: Any, runtime: Any, logger: Any, memo: Any, activity: Any, settings: Any) -> None:
    """
    Reconcile current state of PassSecret objects and remote git repository (desired state);
    bring current state of those objects into alignment.
    """
    log.info(f'Starting operator version {__version__}')
    pass_git_repo.git_clone()
    # print(param, retry, started, runtime, logger, memo, activity, settings)


# @kopf.on.update('PassSecret')
# def update(**kwargs: Any) -> None:
#     """
#     An update was received on the PassSecret object, so attempt to update the corresponding Secret.
#     """


# @kopf.on.create('PassSecret')
# def create(**kwargs: Any) -> None:
#     """
#     Create a new Secret from a PassSecret manifest.

#     Args:
#         version (str): version of the agent.

#     Returns:
#         None.
#     """


# @kopf.on.delete('PassSecret')
# def delete(**kwargs: Any) -> None:
#     """
#     Remove the secret from memory.

#     Args:
#         spec (str):
#     """


@kopf.timer('PassSecret', interval=OPERATOR_INTERVAL, initial_delay=OPERATOR_INITIAL_DELAY)
def reconciliation() -> None:
    """
    Reconcile secrets across all namespaces and ensure they match the state of the PassSecrets.
    """
    pass_git_repo.git_pull()


# @kopf.on.probe(id='now')
# def get_current_timestamp(**kwargs) -> str:
#     return datetime.datetime.utcnow().isoformat()


# @kopf.on.probe(id='status')
# def get_current_status(**kwargs) -> str:
#     return 'ok'


def main() -> None:
    """
    Set up this wrapping Python program with logging, etc.
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
        help='Set the logging level. Valid choices are debug, info, warn, and error.'
    )

    parser.add_argument(
        '--log-file', default='/opt/pass-operator/runtime.log', type=str,
        help='Log file location (if log-stdout is not provided).'
    )

    args = parser.parse_args()

    if args.version:
        print(f'passoperator v{__version__}')
        sys.exit(0)

    if not PASS_GPG_KEY_ID:
        log.error(f'Must provide a valid GPG key ID (PASS_GPG_KEY_ID).')
        sys.exit(1)

    if not PASS_GIT_URL:
        log.error(f'Must provide a valid git URL (PASS_GIT_URL).')
        sys.exit(1)

    if not PASS_SSH_PRIVATE_KEY:
        log.error(f'Must provide a valid private SSH key to clone Git repo. (PASS_SSH_PRIVATE_KEY).')
        sys.exit(1)

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
        priority=OPERATOR_PRIORITY,
        standalone=True,
        namespaces=OPERATOR_NAMESPACE,
        clusterwide=False,
        # liveness_endpoint: Optional[str],
    )