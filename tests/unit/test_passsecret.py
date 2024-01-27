"""
Verify that classmethods src.operator.secret.PassSecret.{from_dict,to_dict} are indeed inverses of each other.
"""


from deepdiff import DeepDiff
from importlib import resources
from unittest import TestCase
from src.operator.secret import PassSecret

import yaml


class PassSecretParseInverse(TestCase):
    """
    Test that from_dict and to_dict are inverse methods.
    """

    def setUp(self) -> None:
        """
        Create a PassSecret instance for use in testing.
        """
        with resources.open_text('tests.e2e.crd.data', 'test_singular_data.yaml') as f:
            self.passsecret_data = yaml.load(f, Loader=yaml.Loader)

        return super().setUp()

    def test_inverse(self) -> None:
        """
        Test that class creation and export are inverses of each other.

        PT(PT'(data)) == PT'(PT(data))
        """

        self.assertIsNotNone(
            PassSecret.from_dict(self.passsecret_data)
        )

        self.assertDictEqual(
            # DeepDiff the objects.
            DeepDiff(
                PassSecret.from_dict(self.passsecret_data).to_dict(),
                self.passsecret_data,
                exclude_paths=[
                    "root['metadata']['labels']",
                    "root['metadata']['annotations']"
                ]
            ),
            # DeepDiff should be empty.
            {}
        )

        self.assertEqual(
            PassSecret.from_dict(PassSecret.from_dict(self.passsecret_data).to_dict()),
            PassSecret.from_dict(self.passsecret_data)
        )