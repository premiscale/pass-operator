"""
A kubernetes operator that syncs and decrypts secrets from pass git repositories
"""

import logging

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from importlib import metadata as meta


__version__ = meta.version('pass-operator')


def main() -> None:
    """

    """