"""
A kubernetes operator that syncs and decrypts secrets from Linux password store (https://www.passwordstore.org/) git repositories
"""


from typing import Any
from pathlib import Path
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from importlib import metadata
from ipaddress import IPv4Address
from kubernetes import client, config
from http import HTTPStatus
from src.operator.git import GitRepo
from src.operator.utils import LogLevel
from src.operator.secret import PassSecret

import logging
import sys
import kopf
import os


__version__ = metadata.version('pass-operator')

log = logging.getLogger(__name__)
pass_git_repo: GitRepo

# Environment variables to configure the operator's performance.
OPERATOR_INTERVAL = int(os.getenv('OPERATOR_INTERVAL', '60'))
OPERATOR_INITIAL_DELAY = int(os.getenv('OPERATOR_INITIAL_DELAY', '3'))
OPERATOR_PRIORITY = int(os.getenv('OPERATOR_PRIORITY', '100'))
OPERATOR_NAMESPACE = os.getenv('OPERATOR_NAMESPACE', 'default')
OPERATOR_POD_IP = IPv4Address(os.getenv('OPERATOR_POD_IP', '0.0.0.0'))

# Environment variables to configure pass.
PASS_BINARY = os.getenv('PASS_BINARY', '/usr/bin/pass')
PASS_DIRECTORY = os.getenv('PASS_DIRECTORY', 'repo')
PASS_GPG_PASSPHRASE = os.getenv('PASS_GPG_PASSPHRASE')
PASS_GPG_KEY = os.getenv('PASS_GPG_KEY')
PASS_GPG_KEY_ID = os.getenv('PASS_GPG_KEY_ID')
PASS_GIT_URL = os.getenv('PASS_GIT_URL')
PASS_GIT_BRANCH = os.getenv('PASS_GIT_BRANCH', 'main')


@kopf.on.startup()
def start(**kwargs: Any) -> None:

    """
    Perform initial repo clone and set up operator runtime.
    """
    log.info(f'Starting operator version {__version__}')
    pass_git_repo.clone()


@kopf.timer('secrets.premiscale.com', 'v1alpha1', 'passsecret', interval=OPERATOR_INTERVAL, initial_delay=OPERATOR_INITIAL_DELAY, sharp=True)
def reconciliation(**kwargs) -> None:
    """
    Reconcile state of managed secrets against the pass store. Update secrets' data
    if a mismatch is found.
    """
    log.info('Reconciling cluster state')
    pass_git_repo.pull()
    check_gpg_id()


# @kopf.on.cleanup()
# def cleanup(**kwargs) -> None:
#     pass


@kopf.on.update('secrets.premiscale.com', 'v1alpha1', 'passsecret')
def update(old: kopf.BodyEssence | Any, new: kopf.BodyEssence | Any, meta: kopf.Meta, **_: Any) -> None:
    """
    An update was received on the PassSecret object, so attempt to update the corresponding Secret.

    This method is pretty much identical to 'create'-type events.

    Args:
        body [kopf.Body]:
        old [kopf.BodyEssence]: old body of the PassSecret.
        new [kopf.BodyEssence]: new body of the PassSecret.
    """
    # Parse the old PassSecret manifest.
    try:
        oldPassSecret = PassSecret.from_dict(
            manifest={
                'metadata': {
                    'name': meta['name'],
                    'namespace': meta['namespace']
                },
                **old
            }
        )

        if not oldPassSecret:
            raise kopf.PermanentError()
    except ValueError as e:
        log.error(e)
        raise kopf.PermanentError()

    # Parse the new PassSecret manifest.
    try:
        newPassSecret = PassSecret.from_dict(
            manifest={
                'metadata': {
                    'name': meta['name'],
                    'namespace': meta['namespace']
                },
                **new
            }
        )

        if not newPassSecret:
            raise kopf.PermanentError()
    except ValueError as e:
        log.error(e)
        raise kopf.PermanentError()

    v1 = client.CoreV1Api()

    try:
        if newPassSecret.managedSecret.namespace != oldPassSecret.managedSecret.namespace:
            # Namespace is different. Delete the former secret and create a new one in the new namespace.
            v1.delete_namespaced_secret(
                name=oldPassSecret.managedSecret.name,
                namespace=oldPassSecret.managedSecret.namespace
            )

            v1.create_namespaced_secret(
                namespace=newPassSecret.managedSecret.namespace,
                body=client.V1Secret(
                    **newPassSecret.managedSecret.to_client_dict()
                )
            )
        else:
            # Namespace is the same, secret's being updated in-place.
            v1.patch_namespaced_secret(
                name=oldPassSecret.name,
                namespace=oldPassSecret.namespace,
                body=client.V1Secret(
                    **newPassSecret.managedSecret.to_client_dict()
                )
            )

        log.info(f'Successfully updated PassSecret "{newPassSecret.name}" managed Secret {newPassSecret.managedSecret.name}.')
    except client.ApiException as e:
        log.error(e)


@kopf.on.create('secrets.premiscale.com', 'v1alpha1', 'passsecret')
def create(body: kopf.Body, **_: Any) -> None:
    """
    Create a new Secret with the spec of the newly-created PassSecret.

    Args:
        body [kopf.Body]: body of the create event.
    """
    try:
        secret = PassSecret.from_dict(manifest=dict(body))

        if not secret:
            raise kopf.PermanentError()
    except ValueError as e:
        log.error(e)
        raise kopf.PermanentError()

    log.info(f'PassSecret "{secret.name}" created')

    v1 = client.CoreV1Api()

    try:
        v1.create_namespaced_secret(
            namespace=secret.managedSecret.namespace,
            body=client.V1Secret(
                **secret.managedSecret.to_client_dict()
            )
        )
        log.info(f'Created PassSecret "{secret.name}" managed secret "{secret.managedSecret.name}" in Namespace "{secret.managedSecret.namespace}"')
    except client.ApiException as e:
        if e.status == HTTPStatus.CONFLICT:
            log.error(f'Duplicate PassSecret "{secret.name}" managed Secret "{secret.managedSecret.name}" in Namespace "{secret.managedSecret.namespace}". Skipping.')
            raise kopf.TemporaryError()
        else:
            log.error(e)
            raise kopf.PermanentError()


@kopf.on.delete('secrets.premiscale.com', 'v1alpha1', 'passsecret')
def delete(body: kopf.Body, **_: Any) -> None:
    """
    Remove the secret.
    """
    try:
        secret = PassSecret.from_dict(manifest=dict(body))

        if not secret:
            raise kopf.PermanentError()
    except ValueError as e:
        log.error(e)
        raise kopf.PermanentError()

    log.info(f'PassSecret "{secret.name}" deleted')

    v1 = client.CoreV1Api()

    try:
        v1.delete_namespaced_secret(
            name=secret.managedSecret.name,
            namespace=secret.managedSecret.namespace
        )
        log.info(f'Deleted PassSecret "{secret.name}" managed Secret "{secret.managedSecret.name}" in Namespace "{secret.managedSecret.namespace}"')
    except client.ApiException as e:
        if e.status == HTTPStatus.NOT_FOUND:
            log.warning(f'PassSecret "{secret.name}" managed Secret "{secret.managedSecret.name}" was not found. Skipping.')
        else:
            log.error(e)
            raise kopf.PermanentError()


def check_gpg_id(path: Path = Path(f'~/.password-store/{PASS_DIRECTORY}/.gpg-id').expanduser(), remove: bool =False) -> None:
    """
    Ensure the gpg ID exists (leftover from 'pass init' in the entrypoint, or a git clone) and its contents match PASS_GPG_KEY_ID.

    Args:
        path [Path]: Path-like object to the .gpg-id file.
        remove [bool]: indicate whether or not to remove this file, should it exist.
    """
    if path.exists():
        with open(path, mode='r', encoding='utf-8') as gpg_id_f:
            if gpg_id_f.read().rstrip() != PASS_GPG_KEY_ID:
                log.error(f'PASS_GPG_KEY_ID ({PASS_GPG_KEY_ID}) does not equal .gpg-id contained in {path}')
                sys.exit(1)

        if remove:
            path.unlink(missing_ok=False)
    else:
        log.error(f'.gpg-id at "{path}" does not exist. pass init failure')
        sys.exit(1)


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

    config.load_incluster_config()

    if not PASS_GIT_URL:
        log.error('Must provide a valid git URL (PASS_GIT_URL)')
        sys.exit(1)

    # Set up our global git repository object.
    global pass_git_repo
    pass_git_repo = GitRepo(
        repo_url=PASS_GIT_URL,
        branch=PASS_GIT_BRANCH,
        clone_location=PASS_DIRECTORY
    )

    # Configure logger
    if args.log_stdout:
        logging.basicConfig(
            stream=sys.stdout,
            format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
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
                filemode='w'
            )
        except (FileNotFoundError, PermissionError) as msg:
            log.error(f'Failed to configure logging, received: {msg}')
            sys.exit(1)

    # Reset the directory to be cloned into.
    check_gpg_id(remove=True)

    kopf.run(
        # https://kopf.readthedocs.io/en/stable/packages/kopf/#kopf.run
        priority=OPERATOR_PRIORITY,
        standalone=True,
        namespace=OPERATOR_NAMESPACE,
        clusterwide=False,
        liveness_endpoint=f'http://{OPERATOR_POD_IP}:8080/healthz'
    )