"""
Provide interfaces for interacting with PassSecret manifests and encrypted data in a clean, OO-way.
"""


from __future__ import annotations
from typing import Dict, Final, List
from pathlib import Path
from attrs import define, asdict as to_dict
from cattrs import structure as from_dict
from humps import camelize
from datetime import datetime

from passoperator.gpg import decrypt
from passoperator.utils import b64Dec, b64Enc
from passoperator import env

import kopf
import logging


log = logging.getLogger(__name__)


@define
class Metadata:
    """
    Metadata is the schema for the metadata field of a K8s object.
    """
    name: str
    namespace: str = 'default'
    annotations: Dict[str, str] | None = None
    labels: Dict[str, str] | None = None

    def to_dict(self) -> Dict:
        """
        Output this object as a K8s manifest dictionary.

        Returns:
            Dict: this object as a dict.
        """
        return to_dict(
            self,
            filter=lambda a, v: v is not None
        )


@define
class ManagedSecret:
    """
    Logic for interacting with managed Secret objects.
    """
    metadata: Metadata
    data: Dict[str, str] | None = None
    stringData: Dict[str, str] | None = None
    immutable: bool = False
    type: str = 'Opaque'
    kind: Final[str] = 'Secret'
    apiVersion: Final[str] = 'v1'
    finalizers: List[str] = []

    def __attrs_post_init__(self) -> None:
        if not self.data and not self.stringData:
            return None

        # Propagate one field to the other, make sure they match despite b64 conversion.
        if self.stringData and self.data:
            # Ensure stringData and data contain the same keys & values by iterating over both if both are set independently.
            for key in self.stringData:
                if key not in self.data:
                    self.data[key] = b64Enc(self.stringData[key])
                else:
                    assert self.data[key] == b64Enc(self.stringData[key])
            for key in self.data:
                if key not in self.stringData:
                    self.stringData[key] = b64Dec(self.data[key])
                else:
                    assert self.stringData[key] == b64Dec(self.data[key])

        elif self.data and not self.stringData:
            self.stringData = {
                key: b64Dec(value) for key, value in self.data.items()
            }

        elif self.stringData and not self.data:
            self.data = {
                key: b64Enc(value) for key, value in self.stringData.items()
            }

        # Ensure the managed secret is marked as managed and has a last-updated timestamp.
        if self.metadata.annotations is None:
            self.metadata.annotations = {}

        self.metadata.annotations['secrets.premiscale.com/managed'] = 'true'
        self.metadata.annotations['secrets.premiscale.com/last-updated'] = datetime.now().isoformat()

        return None

    def to_dict(self, export: bool = False) -> Dict:
        """
        Output this object as a k8s manifest dictionary.

        Args:
            export (bool): if True, export the object as a dict without the apiGroup and duplicate data keys.

        Returns:
            Dict: this object as a dict.
        """
        d = to_dict(self, filter=lambda a, v: v is not None and v is not False)

        if export:
            d.pop('stringData')

        return d

    def to_client_dict(self, finalizers: bool = False) -> Dict:
        """
        Output this secret to a dictionary with keys that match the arguments of kubernetes.client.V1Secret, for convenience.

        Args:
            finalizers (bool): if True, include the finalizers field in the output.
        """
        d = dict(self.to_dict(export=True))
        d.pop('data')
        d.pop('apiVersion')
        if not finalizers:
            d.pop('finalizers')
        d['string_data'] = self.stringData
        return d

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

    @classmethod
    def from_kopf(cls, body: kopf.Body | Dict) -> ManagedSecret:
        """
        Create a ManagedSecret object from a K8s body dict.

        Args:
            body (kopf.Body | Dict): the K8s manifest.

        Returns:
            ManagedSecret: the ManagedSecret object created from the manifest.
        """

        # Camelize the body to match the PassSecret object's fields, but keep the data fields as-is.
        camelized_body = dict(camelize(dict(body)))
        camelized_body['data'] = dict(body)['data']

        return from_dict(
            camelized_body,
            cls
        )


@define
class PassSecretSpec:
    """
    PassSecretSpec is the schema for the spec field of a PassSecret object. It also handles decrypting the encrypted data on
    the PassSecret object.
    """
    encryptedData: Dict[str, str]
    managedSecret: ManagedSecret

    def __attrs_post_init__(self) -> None:
        # Post-process the managedSecret field to decrypt the contents of the managedSecret.
        self.managedSecret = self.decrypt(self.managedSecret, self.encryptedData)

    @staticmethod
    def decrypt(ms: ManagedSecret, encryptedData: Dict[str, str]) -> ManagedSecret:
        """
        Decrypt the contents of this PassSecret's paths before returning the spec object.
        """
        stringData = {}

        for secretKey in encryptedData:
            secretPath = encryptedData[secretKey]

            decryptedSecret = decrypt(
                Path(f'{env["PASS_DIRECTORY"]}/{secretPath}'),
                passphrase=env['PASS_GPG_PASSPHRASE']
            )

            if decryptedSecret:
                stringData[secretKey] = decryptedSecret
            else:
                log.error(f'Failed to decrypt secret at path: {secretPath}')
                stringData[secretKey] = ''

        return ManagedSecret(
            metadata=ms.metadata,
            stringData=stringData,
            immutable=ms.immutable,
            type=ms.type
        )

    def to_dict(self) -> Dict:
        """
        Output this object as a K8s manifest dictionary.

        Returns:
            Dict: this object as a dict.
        """
        return {
            'encryptedData': self.encryptedData,
            'managedSecret': self.managedSecret.to_dict(export=True)
        }


@define
class PassSecret:
    """
    Manage PassSecret data in a clean, interoperable way.
    """
    metadata: Metadata
    spec: PassSecretSpec
    kind: Final[str] = 'PassSecret'
    apiVersion: Final[str] = 'secrets.premiscale.com/v1alpha1'

    def to_dict(self) -> Dict:
        """
        Output this object as a K8s manifest dictionary.

        Returns:
            Dict: this object as a dict.
        """
        return {
            'apiVersion': self.apiVersion,
            'kind': self.kind,
            'metadata': self.metadata.to_dict(),
            'spec': self.spec.to_dict()
        }

    def __eq__(self, __value: object) -> bool:
        """
        Compare two PassSecrets.
        """
        if isinstance(__value, PassSecret):
            return self.to_dict() == __value.to_dict()
        return False

    @classmethod
    def from_kopf(cls, body: kopf.Body | Dict) -> PassSecret:
        """
        Create a PassSecret object from a K8s body dict.

        Args:
            body (kopf.Body | Dict): the body of a K8s object.

        Returns:
            PassSecret: the PassSecret object created from the body.
        """
        # Camelize the body to match the PassSecret object's fields, but keep the encryptedData field as-is.
        camelized_body = dict(camelize(dict(body)))
        camelized_body['spec']['encryptedData'] = dict(body)['spec']['encryptedData']

        return from_dict(
            camelized_body,
            cls
        )