"""
Provide interfaces for interacting with PassSecret manifests and encrypted data in a clean, OO-way.
"""


from __future__ import annotations
from typing import Dict
from dataclasses import dataclass, field
from pathlib import Path
from src.operator.gpg import decrypt
from src.operator.utils import b64Dec, b64Enc
from src.operator import env

import logging


log = logging.getLogger(__name__)


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

        # Propagate one field to the other, make sure they match despite b64 conversion.
        if self.stringData and self.data:
            # Ensure stringData and data contain the same keys & values by iterating over both if both are set independently.
            for key in self.stringData:
                if key not in self.data:
                    self.data[key] = b64Enc(self.stringData[key])
                else:
                    assert b64Dec(self.data[key]) == self.stringData[key]
            for key in self.data:
                if key not in self.stringData:
                    self.stringData[key] = b64Dec(self.data[key])
                else:
                    assert b64Enc(self.stringData[key]) == self.data[key]

        elif self.data and not self.stringData:
            self.stringData = {
                key: b64Dec(value) for key, value in self.data.items()
            }

        elif self.stringData and not self.data:
            self.data = {
                key: b64Enc(value) for key, value in self.stringData.items()
            }

    @classmethod
    def from_dict(cls, manifest: Dict) -> ManagedSecret:
        """
        Parse a k8s manifest into a ManagedSecret (Secret) dataclass.

        Args:
            manifest (Dict): a Secret manifest.

        Returns:
            ManagedSecret: a ManagedSecret created from parsing the contents of the manifest.

        Raises:
            KeyError, ValueError: if expected keys are not present during dictionary unpacking.
        """
        # TODO: manage managed secrets' labels and annotations.
        # if 'annotations' in manifest and len(manifest['annotations']):
        #     annotations = manifest['annotations']
        # else:
        #     annotations = {}

        # if 'labels' in manifest and len(manifest['labels']):
        #     labels = manifest['labels']
        # else:
        #     labels = {}

        return cls(
            name=manifest['metadata']['name'],
            namespace=manifest['metadata']['namespace'],
            data=manifest['data'],
            stringData=manifest['stringData'],
            immutable=manifest['immutable'],
            secretType=manifest['type']
        )

    def to_dict(self) -> Dict:
        """
        Output this object as a k8s manifest dictionary.

        Returns:
            Dict: this object as a dict.
        """
        return {
            'apiVersion': self.apiVersion, # f'{self.apiGroup}/{self.apiVersion}' if self.apiGroup else self.apiVersion,
            'kind': self.kind,
            'metadata': {
                'name': self.name,
                'namespace': self.namespace
                # TODO: labels and annotations, at a future date.
            },
            'data': self.data,
            'immutable': self.immutable,
            'type': self.secretType
        }

    @classmethod
    def from_client_dict(cls, manifest: Dict) -> ManagedSecret:
        """
        Parse a k8s manifest from the kubernetes Python client package into a ManagedSecret (Secret)
        dataclass. Primary difference is naming of the keys.

        Args:
            manifest (Dict): a Secret manifest.

        Returns:
            ManagedSecret: a ManagedSecret created from parsing the contents of the manifest.

        Raises:
            KeyError, ValueError: if expected keys are not present during dictionary unpacking.
        """
        # TODO: manage managed secrets' labels and annotations.
        # if 'annotations' in manifest and len(manifest['annotations']):
        #     annotations = manifest['annotations']
        # else:
        #     annotations = {}

        # if 'labels' in manifest and len(manifest['labels']):
        #     labels = manifest['labels']
        # else:
        #     labels = {}

        return cls(
            name=manifest['metadata']['name'],
            namespace=manifest['metadata']['namespace'],
            data=manifest['data'],
            stringData=manifest['string_data'],  # This is the only change from the method above, unfortunately.
            immutable=manifest['immutable'],
            secretType=manifest['type']
        )

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

    def __eq__(self, __value: object) -> bool:
        """
        Compare two ManagedSecrets.

        Returns:
            bool: whether or not the ManagedSecrets as dictionaries equal one another.
        """
        if isinstance(__value, ManagedSecret):
            return self.to_dict() == __value.to_dict()
        return False

    def data_equals(self, __value: ManagedSecret) -> bool:
        """
        True iff the .data-contents are exactly the same.

        Args:
            __value (ManagedSecret): another ManagedSecret object to compare against.

        Returns:
            bool: whether or not the ManagedSecrets' contained data are equal.
        """
        return self.data == __value.data


@dataclass
class PassSecret:
    """
    Manage PassSecret data in a clean, interoperable way.
    """

    # PassSecret objects require our set of environment variables because we need to decrypt the contents
    # in order to instantiate a ManagedSecret object.
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
        if (decryptedData := self._decrypt()) is None:
            raise ValueError(f'Could not decrypt data on PassSecret {self.name}. Do you need to set a passphrase?')

        self.managedSecret = ManagedSecret(
            name=self.managedSecretName,
            namespace=self.managedSecretNamespace,
            stringData=decryptedData,
            immutable=self.managedSecretImmutable,
            secretType=self.managedSecretType
        )

    def to_dict(self) -> Dict:
        """
        Output this object as a K8s manifest dictionary.

        Returns:
            Dict: this object as a dict.
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
    def from_dict(cls, manifest: Dict) -> PassSecret:
        """
        Parse a k8s manifest into a PassSecret dataclass.

        Args:
            manifest (Dict): the PassSecret manifest dictionary to parse into the dataclass.

        Raises:
            KeyError, ValueError: if expected keys are not present during dictionary unpacking.
        """
        if 'annotations' in manifest and len(manifest['annotations']):
            annotations = manifest['annotations']
        else:
            annotations = {}

        if 'labels' in manifest and len(manifest['labels']):
            labels = manifest['labels']
        else:
            labels = {}

        if 'immutable' not in manifest['spec']['managedSecret']:
            manifest['spec']['managedSecret']['immutable'] = False

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
            managedSecretImmutable=manifest['spec']['managedSecret']['immutable'],
        )

    def _decrypt(self) -> Dict[str, str] | None:
        """
        Decrypt the contents of this PassSecret's paths and store them on an attribute

        Returns:
            Optional[Dict[str, str]]: a dictionary of data keys and decrypted paths' values. If decryption was not possible, None.
        """
        stringData = {}

        for secretKey in self.encryptedData:
            secretPath = self.encryptedData[secretKey]

            decryptedSecret = decrypt(
                Path(f'{env["PASS_DIRECTORY"]}/{secretPath}'),
                passphrase=env['PASS_GPG_PASSPHRASE']
            )

            if decryptedSecret:
                stringData[secretKey] = decryptedSecret
            else:
                return None

        return stringData

    def __eq__(self, __value: object) -> bool:
        """
        Compare two PassSecrets.
        """
        if isinstance(__value, PassSecret):
            return self.to_dict() == __value.to_dict()
        return False