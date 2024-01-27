"""
Provide interfaces for interacting with PassSecret manifests and encrypted data in a clean, OO-way.
"""


from __future__ import annotations
from typing import Dict
from dataclasses import dataclass, field
from pathlib import Path
from src.operator.gpg import decrypt

import base64
import logging
import os


log = logging.getLogger(__name__)

PASS_DIRECTORY = os.getenv('PASS_DIRECTORY', 'repo')
PASS_GPG_PASSPHRASE = os.getenv('PASS_GPG_PASSPHRASE')


@dataclass
class ManagedSecret:
    """
    Logic for interacting with managed Secret objects.
    """
    name: str
    data: Dict[str, str] | None = None
    stringData: Dict[str, str] | None = None
    namespace: str ='default'
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
    """
    Manage PassSecret data in a clean, interoperable way.
    """

    name: str
    managedSecretName: str
    encryptedData: Dict[str, str]
    annotations: Dict[str, str] | None = None
    labels: Dict[str, str] | None = None
    namespace: str ='default'
    kind: str ='PassSecret'
    apiGroup: str ='secrets.premiscale.com'
    apiVersion: str ='v1alpha1'

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
                annotations = {}

            if 'labels' in manifest and len(manifest['labels']):
                labels = manifest['labels']
            else:
                labels = {}

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
        stringData = {}

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