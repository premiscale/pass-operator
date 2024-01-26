"""
A kubernetes operator that syncs and decrypts secrets from Linux password store (https://www.passwordstore.org/) git repositories
"""


from __future__ import annotations

import logging
import sys
import kopf
import os
import base64

from typing import Any, Dict
from kubernetes import client, config
from pathlib import Path
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from importlib import metadata as meta
from ipaddress import IPv4Address
from dataclasses import dataclass, field

from src.passoperator.git import GitRepo
from src.passoperator.utils import LogLevel
from src.passoperator.gpg import decrypt


__version__ = meta.version('pass-operator')

log = logging.getLogger(__name__)
pass_git_repo: GitRepo
config.load_incluster_config()


# Environment variables to configure the operator's performance.
OPERATOR_INTERVAL = int(os.getenv('OPERATOR_INTERVAL', 60))
OPERATOR_INITIAL_DELAY = int(os.getenv('OPERATOR_INITIAL_DELAY', 3))
OPERATOR_PRIORITY = int(os.getenv('OPERATOR_PRIORITY', 100))
OPERATOR_NAMESPACE = os.getenv('OPERATOR_NAMESPACE', 'default')
OPERATOR_POD_IP = IPv4Address(os.getenv('OPERATOR_POD_IP', '0.0.0.0'))

# Environment variables to configure pass.
PASS_BINARY = os.getenv('PASS_BINARY', '/usr/bin/pass')
PASS_DIRECTORY = os.getenv('PASS_DIRECTORY', 'repo')
PASS_GPG_KEY = os.getenv('PASS_GPG_KEY')
PASS_GPG_KEY_ID = os.getenv('PASS_GPG_KEY_ID')
PASS_GPG_PASSPHRASE = os.getenv('PASS_GPG_PASSPHRASE')
PASS_GIT_URL = os.getenv('PASS_GIT_URL')
PASS_GIT_BRANCH = os.getenv('PASS_GIT_BRANCH', 'main')


@dataclass
class ManagedSecret:
    name: str
    namespace: str ='default'
    data: Dict[str, str] =dict()
    stringData: Dict[str, str] =dict()
    immutable: bool =False
    secretType: str ='Opaque'
    kind: str ='Secret'
    apiGroup: str =''
    apiVersion: str ='v1'

    def __post_init__(self) -> None:
        if not self.data and not self.stringData:
            raise RuntimeError('ManagedSecret type expects at least one of \'data\', \'stringData\', to be set.')

        # Propagate one field to the other, if only one or the other is set.
        if self.data and not self.stringData:
            self.stringData = {
                key: base64.b64decode(value).rstrip().decode() for key, value in self.data.items()
            }

        if self.stringData and not self.data:
            self.data = {
                key: base64.b64encode(bytes(value.rstrip().encode('utf-8'))).decode() for key, value in self.stringData.items()
            }

    def to_client_dict(self) -> Dict:
        """
        Output this secret to a dictionary with keys that match the arguments of kubernetes.client.V1Secret, for convenience.
        """
        return {
            'api_version': f'{self.apiGroup}/{self.apiVersion}' if self.apiGroup else self.apiVersion,
            'kind': self.kind,
            'metadata': {
                'name': self.name,
                'namespace': self.namespace,
            },
            'string_data': self.stringData,
            'type': self.secretType,
            'immutable': self.immutable
        }


@dataclass
class PassSecret:
    name: str
    managedSecretName: str
    encryptedData: Dict[str, str]
    namespace: str ='default'
    kind: str ='PassSecret'
    apiGroup: str ='secrets.premiscale.com'
    apiVersion: str ='v1alpha1'
    annotations: Dict[str, str] =dict()
    labels: Dict[str, str] =dict()

    managedSecret: ManagedSecret = field(init=False)
    managedSecretNamespace: str ='default'
    managedSecretType: str ='Opaque'
    managedSecretImmutable: bool =False

    def __post_init__(self) -> None:
        if (decryptedData := self.decrypt()) is None:
            raise ValueError(f'Could not decrypt data on PassSecret {self.name}')

        self.managedSecret = ManagedSecret(
            name=self.managedSecretName,
            namespace=self.managedSecretNamespace,
            stringData=decryptedData,
            immutable=self.managedSecretImmutable,
            secretType=self.managedSecretType
        )

    def to_dict(self) -> Dict:
        """
        Output this object as a K8s manifest as JSON.
        """
        return {
            'apiVersion': f'{self.apiGroup}/{self.apiVersion}',
            'kind': self.kind,
            'metadata': {
                'name': self.name,
                'namespace': self.namespace,
                'annotations': self.annotations,
                'labels': self.labels
            },
            'spec': {
                'encryptedData': self.encryptedData,
                'managedSecret': {
                    'name': self.managedSecret.name,
                    'namespace': self.managedSecret.namespace,
                    'type': self.managedSecret.secretType,
                    'immutable': self.managedSecret.immutable
                }
            }
        }

    @classmethod
    def from_dict(cls, manifest: Dict) -> PassSecret | None:
        """
        Parse a k8s manifest into a PassSecret dataclass.
        """
        try:
            if 'annotations' in manifest and len(manifest['annotations']):
                annotations = manifest['annotations']
            else:
                annotations = dict()

            if 'labels' in manifest and len(manifest['labels']):
                labels = manifest['labels']
            else:
                labels = dict()

            return cls(
                name=manifest['metadata']['name'],
                namespace=manifest['metadata']['namespace'],
                encryptedData=manifest['spec']['encryptedData'],
                labels=labels,
                annotations=annotations,
                # Parse out managed secret fields into arguments.
                managedSecretName=manifest['spec']['managedSecret']['name'],
                managedSecretNamespace=manifest['spec']['managedSecret']['namespace'],
                managedSecretType=manifest['spec']['managedSecret']['type'],
                managedSecretImmutable=manifest['spec']['managedSecret']['immutable']
            )
        except (KeyError, ValueError) as e:
            log.error(f'Could not parse PassSecret into dataclass: {e}')
            return None

    def decrypt(self) -> Dict[str, str] | None:
        """
        Decrypt the contents of this PassSecret's paths and store them on an attribute

        Returns:
            Optional[Dict[str, str]]: a dictionary of data keys and decrypted paths' values. If decryption was not possible, None.
        """
        stringData = dict()

        for secretKey in self.encryptedData:
            secretPath = self.encryptedData[secretKey]

            decryptedSecret = decrypt(
                Path(f'~/.password-store/{PASS_DIRECTORY}/{secretPath}').expanduser(),
                passphrase=PASS_GPG_PASSPHRASE
            )

            if decryptedSecret:
                stringData[secretKey] = decryptedSecret
            else:
                return None

        return stringData


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
    Reconcile user-defined PassSecrets with the state of the cluster.
    """
    log.info(f'Reconciling cluster state')
    pass_git_repo.pull()
    check_gpg_id()


# @kopf.on.cleanup()
# def cleanup(**kwargs) -> None:
#     pass


@kopf.on.update('secrets.premiscale.com', 'v1alpha1', 'passsecret')
def update(old: kopf.BodyEssence, new: kopf.BodyEssence, meta: kopf.Meta, **_: Any) -> None:
    """
    An update was received on the PassSecret object, so attempt to update the corresponding Secret.

    This method is pretty much identical to 'create'-type events.

    Args:
        body [kopf.Body]:
        old [dict]: old body of the PassSecret.
        new [dict]: new body of the PassSecret.
    """
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
        v1.patch_namespaced_secret(
            name=oldPassSecret.name,
            namespace=oldPassSecret.namespace,
            body=client.V1Secret(
                **newPassSecret.managedSecret.to_client_dict()
            )
        )
        log.info(f'PassSecret "{oldPassSecret.name}" updated')
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
        secret = PassSecret.from_dict(
            manifest={
                **body.spec
            }
        )

        if not secret:
            raise kopf.PermanentError()
    except ValueError as e:
        log.error(e)
        raise kopf.PermanentError()

    log.info(f'PassSecret "{secret.name}" created')

    v1 = client.CoreV1Api()

    try:
        v1.create_namespaced_secret(
            name=secret.managedSecret.name,
            namespace=secret.managedSecret.namespace,
            body=client.V1Secret(
                **secret.managedSecret.to_client_dict()
            )
        )
        log.info(f'PassSecret {secret.name} managed secret {secret.managedSecret.name} created in namespace {secret.managedSecret.namespace}')
    except client.ApiException as e:
        log.error(e)


@kopf.on.delete('secrets.premiscale.com', 'v1alpha1', 'passsecret')
def delete(body: kopf.Body, **_: Any) -> None:
    """
    Remove the secret.
    """
    try:
        secret = PassSecret.from_dict(
            manifest={
                **body.spec
            }
        )

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
        log.info(f'PassSecret {secret.name} managed secret "{secret.managedSecret.name}" deleted in namespace {secret.managedSecret}')
    except client.ApiException as e:
        log.error(e)


def check_gpg_id(path: Path = Path(f'~/.password-store/{PASS_DIRECTORY}/.gpg-id').expanduser(), remove: bool =False) -> None:
    """
    Ensure the gpg ID exists (leftover from 'pass init' in the entrypoint, or a git clone) and its contents match PASS_GPG_KEY_ID.

    Args:
        path (Path): Path-like object to the .gpg-id file.
        remove (bool): indicate whether or not to remove this file, should it exist.
    """
    if path.exists():
        with open(path, mode='r') as gpg_id_f:
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

    if not PASS_GIT_URL:
        log.error(f'Must provide a valid git URL (PASS_GIT_URL)')
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