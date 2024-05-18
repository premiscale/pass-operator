"""
A kubernetes operator that syncs and decrypts secrets from Linux password store (https://www.passwordstore.org/) git repositories.
"""


from typing import Any, List
from pathlib import Path
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from importlib import metadata
from kubernetes import client, config
from http import HTTPStatus
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from time import sleep

from passoperator.git import pull, clone
from passoperator.utils import LogLevel
from passoperator.secret import PassSecret, ManagedSecret
from passoperator import env

import asyncio
import logging
import sys
import kopf


__version__ = metadata.version('pass-operator')

log = logging.getLogger(__name__)


@kopf.on.startup()
def start(settings: kopf.OperatorSettings, **_: Any) -> None:
    """
    Set up operator runtime.
    """
    log.info(f'Starting operator version {__version__}')
    settings.persistence.finalizer = 'secrets.premiscale.com/finalizer'
    settings.persistence.progress_storage = kopf.AnnotationsProgressStorage(prefix='secrets.premiscale.com')


@kopf.timer(
    # Target PassSecret.secrets.premiscale.com/v1alpha1
    'secrets.premiscale.com', 'v1alpha1', 'passsecret',
    # Interval to check every instance of a PassSecret.
    interval=float(env['OPERATOR_INTERVAL']),
    # Initial delay in seconds before reviewing all managed PassSecrets.
    initial_delay=float(env['OPERATOR_INITIAL_DELAY']),
    # Don't delay if the prior reconciliation hasn't completed.
    sharp=True)
def reconciliation(body: kopf.Body, **_: Any) -> None:
    """
    Reconcile state of a managed secret against the pass store. Update secrets' data if a mismatch
    is found. Kopf timers are triggered on an object-by-object basis, so this method will
    automatically revisit every PassSecret, iff it resides in the same namespace as the operator.

    Args:
        body [kopf.Body]: raw body of the PassSecret.
    """

    # Ensure the GPG key ID in ~/.password-store/${PASS_DIRECTORY}/.gpg-id did not change with the git update.
    check_gpg_id(
        path=f'{env["PASS_DIRECTORY"]}/.gpg-id'
    )

    # Create a new PassSecret object with an up-to-date managedSecret decrypted value from the pass store.
    passSecretObj = PassSecret.from_kopf(body)

    log.info(
        f'Reconciling PassSecret "{passSecretObj.metadata.name}" managed Secret "{passSecretObj.spec.managedSecret.metadata.name}" in Namespace "{passSecretObj.spec.managedSecret.metadata.namespace}" against password store.'
    )

    v1 = client.CoreV1Api()

    try:
        secret = v1.read_namespaced_secret(
            name=passSecretObj.spec.managedSecret.metadata.name,
            namespace=passSecretObj.spec.managedSecret.metadata.namespace
        )

        log.debug(secret)
        _managedSecret = ManagedSecret.from_kopf(secret.to_dict())

        # If the managed secret data does not match what's in the newly-generated ManagedSecret object,
        # submit a patch request to update it.
        if not _managedSecret.data_equals(passSecretObj.spec.managedSecret):
            if _managedSecret.immutable:
                raise kopf.TemporaryError(
                    f'PassSecret "{passSecretObj.metadata.name}" managed secret "{passSecretObj.spec.managedSecret.metadata.name}" is immutable. Ignoring data patch.'
                )

            v1.patch_namespaced_secret(
                name=passSecretObj.spec.managedSecret.metadata.name,
                namespace=passSecretObj.spec.managedSecret.metadata.namespace,
                body=client.V1Secret(
                    **passSecretObj.spec.managedSecret.to_client_dict(finalizers=False)
                )
            )

            log.info(f'Reconciliation successfully updated Secret "{_managedSecret.metadata.name}".')
    except client.ApiException as e:
        raise kopf.PermanentError(e)


# @kopf.on.cleanup()
# def cleanup(**kwargs) -> None:
#     pass

# @kopf.on.resume()
# def resume(**kwargs) -> None:
#     pass


def lookup_managing_passsecret(managedSecretName: str) -> PassSecret | None:
    """
    Look up a PassSecret object by name and namespace.

    Args:
        managedSecretName [str]: name of the managed Secret to look up a PassSecret by, if it exists.

    Returns:
        PassSecret | None: the PassSecret object if found, else None.
    """
    v1 = client.CustomObjectsApi()

    try:
        passSecrets = v1.list_namespaced_custom_object(
            group='secrets.premiscale.com',
            version='v1alpha1',
            namespace=env['OPERATOR_NAMESPACE'],
            plural='passsecrets'
        )

        for passSecret in passSecrets['items']:
            if passSecret['spec']['managedSecret']['metadata']['name'] == managedSecretName:
                return PassSecret.from_kopf(passSecret)
        else:
            return None
    except client.ApiException as e:
        raise kopf.PermanentError(e)


@kopf.on.update('secrets.premiscale.com', 'v1alpha1', 'passsecret')
def update(old: kopf.BodyEssence | Any, new: kopf.BodyEssence | Any, meta: kopf.Meta, **_: Any) -> None:
    """
    An update was received on the PassSecret object, so attempt to update the corresponding Secret.

    This method is pretty much identical to 'create'-type events.

    Args:
        body [kopf.Body]: raw body of the PassSecret.
        old [kopf.BodyEssence]: old body of the PassSecret.
        new [kopf.BodyEssence]: new body of the PassSecret.
    """
    metadata = {
        'metadata': {
            'name': meta['name'],
            'namespace': meta['namespace']
        }
    }

    # Parse the old PassSecret manifest.
    try:
        oldPassSecret = PassSecret.from_kopf(
            {
                **metadata,
                **old
            }
        )
    except (ValueError, KeyError) as e:
        raise kopf.PermanentError(e)

    # Parse the new PassSecret manifest.
    try:
        newPassSecret = PassSecret.from_kopf(
            {
                **metadata,
                **new
            }
        )
    except (ValueError, KeyError) as e:
        raise kopf.PermanentError(e)

    v1 = client.CoreV1Api()

    # Handle typically immutable field changes separately from the rest of the manifest on Secrets.
    try:
        if newPassSecret.spec.managedSecret.metadata.namespace != oldPassSecret.spec.managedSecret.metadata.namespace or newPassSecret.spec.managedSecret.metadata.name != oldPassSecret.spec.managedSecret.metadata.name:
            # Name or namespace is different. Delete the former secret and create a new one in the new namespace.
            v1.delete_namespaced_secret(
                name=oldPassSecret.spec.managedSecret.metadata.name,
                namespace=oldPassSecret.spec.managedSecret.metadata.namespace
            )

            v1.create_namespaced_secret(
                namespace=newPassSecret.spec.managedSecret.metadata.namespace,
                body=client.V1Secret(
                    **newPassSecret.spec.managedSecret.to_client_dict(finalizers=False)
                )
            )
        else:
            # Name and namespace are the same, but the secret's being updated in-place.
            v1.patch_namespaced_secret(
                name=newPassSecret.metadata.name,
                namespace=oldPassSecret.metadata.namespace,
                body=client.V1Secret(
                    **newPassSecret.spec.managedSecret.to_client_dict(finalizers=False)
                )
            )

        log.info(
            f'Successfully updated PassSecret "{newPassSecret.metadata.name}" managed Secret "{newPassSecret.spec.managedSecret.metadata.name}".'
        )
    except client.ApiException as e:
        raise kopf.PermanentError(e)


@kopf.on.create('secrets.premiscale.com', 'v1alpha1', 'passsecret')
def create(body: kopf.Body, **_: Any) -> None:
    """
    Create a new Secret with the spec of the newly-created PassSecret.

    Args:
        body [kopf.Body]: raw body of the created PassSecret.
    """
    try:
        passSecretObj = PassSecret.from_kopf(body)
    except (ValueError, KeyError) as e:
        raise kopf.PermanentError(e)

    log.info(f'PassSecret "{passSecretObj.metadata.name}" created')

    v1 = client.CoreV1Api()

    try:
        v1.create_namespaced_secret(
            namespace=passSecretObj.spec.managedSecret.metadata.namespace,
            body=client.V1Secret(
                **passSecretObj.spec.managedSecret.to_client_dict(finalizers=False)
            )
        )
        log.info(
            f'Created PassSecret "{passSecretObj.metadata.name}" managed Secret "{passSecretObj.spec.managedSecret.metadata.name}" in Namespace "{passSecretObj.spec.managedSecret.metadata.namespace}"'
        )
    except client.ApiException as e:
        if e.status == HTTPStatus.CONFLICT:
            raise kopf.TemporaryError(f'Duplicate PassSecret "{passSecretObj.metadata.name}" managed Secret "{passSecretObj.spec.managedSecret.metadata.name}" in Namespace "{passSecretObj.spec.managedSecret.metadata.namespace}". Skipping.')
        raise kopf.PermanentError(e)


@kopf.on.delete('secrets.premiscale.com', 'v1alpha1', 'passsecret')
def delete(body: kopf.Body, **_: Any) -> None:
    """
    Remove a managed secret, as the managing PassSecret has been deleted.

    Args:
        body [kopf.Body]: raw body of the deleted PassSecret.
    """
    try:
        passSecretObj = PassSecret.from_kopf(body)
    except (ValueError, KeyError) as e:
        raise kopf.PermanentError(e)

    log.info(f'PassSecret "{passSecretObj.metadata.name}" deleted')

    v1 = client.CoreV1Api()

    try:
        v1.delete_namespaced_secret(
            name=passSecretObj.spec.managedSecret.metadata.name,
            namespace=passSecretObj.spec.managedSecret.metadata.namespace
        )
        log.info(f'Deleted PassSecret "{passSecretObj.metadata.name}" managed Secret "{passSecretObj.spec.managedSecret.metadata.name}" in Namespace "{passSecretObj.spec.managedSecret.metadata.namespace}"')
    except client.ApiException as e:
        if e.status == HTTPStatus.NOT_FOUND:
            log.warning(f'PassSecret "{passSecretObj.metadata.name}" managed Secret "{passSecretObj.spec.managedSecret.metadata.name}" was not found. Skipping.')
        raise kopf.PermanentError(e)


def check_gpg_id(path: Path | str, remove: bool =False) -> None:
    """
    Ensure the gpg ID exists (leftover from 'pass init' in the entrypoint, or a git clone) and its contents match PASS_GPG_KEY_ID.

    Args:
        path [Path]: Path-like object to the .gpg-id file.
        remove [bool]: indicate whether or not to remove this file, should it exist.
    """
    if Path(path).exists():
        with open(path, mode='r', encoding='utf-8') as gpg_id_f:
            _gpg_id = gpg_id_f.read().rstrip()
            if _gpg_id != env['PASS_GPG_KEY_ID']:
                log.error(f'PASS_GPG_KEY_ID ({env["PASS_GPG_KEY_ID"]}) does not equal .gpg-id contained in {path}: {_gpg_id}')
                sys.exit(1)

        if remove:
            Path(path).unlink(missing_ok=False)
    else:
        log.error(f'.gpg-id at "{path}" does not exist. pass init failure')
        sys.exit(1)


def main() -> int:
    """
    Set up this wrapping Python program with logging, etc.

    Returns:
        int: exit code.
    """
    parser = ArgumentParser(
        description=__doc__,
        formatter_class=ArgumentDefaultsHelpFormatter
    )

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
        print(f'passoperator v{__version__}', file=sys.stdout)
        sys.exit(0)

    config.load_incluster_config()

    if not env['PASS_GIT_URL']:
        log.error('Must provide a valid git URL (PASS_GIT_URL)')
        sys.exit(1)

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
            if not Path(args.log_file).exists():
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

    # Reset the directory to be cloned into following the 'pass init' of the entrypoint.
    check_gpg_id(
        path=f'{env["PASS_DIRECTORY"]}/.gpg-id',
        remove=True
    )

    clone()

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix='operator') as executor:
        threads = [
            executor.submit(
                # Start kopf in its event loop in another thread on this process.
                # https://kopf.readthedocs.io/en/stable/embedding/
                lambda: asyncio.run(
                    kopf.operator(
                        # https://kopf.readthedocs.io/en/stable/packages/kopf/#kopf.run
                        priority=int(env['OPERATOR_PRIORITY']),
                        standalone=True,
                        namespace=env['OPERATOR_NAMESPACE'],
                        clusterwide=False,
                        liveness_endpoint=f'http://{env["OPERATOR_POD_IP"]}:8080/healthz'
                    )
                )
            ),
            executor.submit(
                partial(
                    pull,
                    daemon=True
                )
            )
        ]

        for thread in threads:
            thread.result()

    return 0