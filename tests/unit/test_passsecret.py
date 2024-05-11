"""
Verify that classmethods passoperator.secret.PassSecret.{from_dict,to_dict} are indeed inverses of each other.
"""


from deepdiff import DeepDiff
from unittest import TestCase
from humps import camelize
from cattrs import structure as from_dict

from passoperator.secret import PassSecret, ManagedSecret, Metadata, PassSecretSpec

from tests.common import (
    load_data
)


class PassSecretParseInverse(TestCase):
    """
    Test that from_dict and asdict are inverse methods.
    """

    def setUp(self) -> None:
        """
        Create a PassSecret instance for use in testing.
        """
        self.passsecret_data = load_data('test_singular_data')

        return super().setUp()

    def test_passsecret_export_import_inverse(self) -> None:
        """
        Test that class import and export are inverses of each other.

        PT(PT'(data)) == PT'(PT(data))
        """

        self.assertIsNotNone(
            from_dict(
                self.passsecret_data,
                PassSecret
            )
        )

        # PT'(PT(data)) == data
        self.assertDictEqual(
            DeepDiff(
                from_dict(
                    self.passsecret_data,
                    PassSecret
                ).to_dict(),
                self.passsecret_data,
                exclude_paths=[
                    "root['metadata']['labels']",
                    "root['metadata']['annotations']",
                    "root['spec']['managedSecret']['metadata']['labels']",
                    "root['spec']['managedSecret']['metadata']['annotations']",
                    "root['spec']['managedSecret']['kind']",
                    "root['spec']['managedSecret']['data']",
                    "root['spec']['managedSecret']['immutable']",
                    "root['spec']['managedSecret']['apiVersion']"
                ]
            ),
            {}
        )

        # PT(PT'(data)) == data
        self.assertDictEqual(
            DeepDiff(
                PassSecret(
                    metadata=Metadata(
                        name='singular-data',
                        namespace='pass-operator'
                    ),
                    spec=PassSecretSpec(
                        encryptedData={
                            'singular_data': 'premiscale/operator/singular-data'
                        },
                        managedSecret=ManagedSecret(
                            metadata=Metadata(
                                name='singular-data',
                                namespace='pass-operator'
                            ),
                            type='Opaque'
                        )
                    )
                ).to_dict(),
                self.passsecret_data,
                exclude_paths=[
                    "root['metadata']['labels']",
                    "root['metadata']['annotations']",
                    "root['spec']['managedSecret']['metadata']['labels']",
                    "root['spec']['managedSecret']['metadata']['annotations']",
                    "root['spec']['managedSecret']['kind']",
                    "root['spec']['managedSecret']['data']",
                    "root['spec']['managedSecret']['immutable']",
                    "root['spec']['managedSecret']['apiVersion']"
                ]
            ),
            {}
        )