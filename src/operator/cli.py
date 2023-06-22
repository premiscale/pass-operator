"""
A kubernetes operator that syncs and decrypts secrets from pass git repositories
"""

import logging
import sys

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from importlib import metadata as meta
from enum import Enum


__version__ = meta.version('pass-operator')

log = logging.getLogger(__name__)


class LogLevel(Enum):
    info = logging.INFO
    error = logging.ERROR
    warn = logging.WARNING
    debug = logging.DEBUG

    def __str__(self):
        return self.name

    @classmethod
    def from_string(cls, s: str) -> 'LogLevel':
        """
        Convert a string to the enum value.

        Args:
            s (str): key to convert to the enum value.

        Returns:
            LogLevel: Log level object.
        """
        try:
            return cls[s.lower()]
        except KeyError:
            log.error('Must specify an accepted log level.')
            sys.exit(1)


def main() -> None:
    """
    Set up operator.
    """
    parser = ArgumentParser(description=__doc__, formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        '--version', action='store_true', default=False,
        help='Display the operator version.'
    )

    parser.add_argument(
        '--daemon', action='store_true', default=False,
        help='Start the operator as a background daemon process.'
    )

    parser.add_argument(
        '--log-stdout', action='store_true', default=False,
        help='Print logs to stdout.'
    )

    parser.add_argument(
        '--log-level', default='info', choices=list(LogLevel), type=LogLevel.from_string,
        help='Set the logging level. Valid choices are info, debug, error, and warn (in any case).'
    )

    parser.add_argument(
        '--log-file', default='/opt/pass-operator/runtime.log'
    )

    parser.add_argument(
        '--ssh-key', type=str,
        help='Specify the SSH key to use with git. Must be a valid path to key file or private SSH key contents.'
    )

    parser.add_argument(
        '--pass-binary', type=str, default='/usr/bin/pass',
        help='Path to an alternate pass binary.'
    )

    parser.add_argument(
        '--pass-dir', type=str, default='~/.password-store/',
        help='Pass directory to clone into.'
    )

    parser.add_argument(
        '--gpg-key-id', type=str,
        help='Private GPG key ID to use with pass to decrypt secrets.'
    )

    parser.add_argument(
        '--git-ssh-url', type=str,
        help='Repository\'s git domain to clone.'
    )

    parser.add_argument(
        '--git-branch', type=str, default='main',
        help='Git branch to clone from the repository.'
    )

    args = parser.parse_args()

    if args.version:
        print(f'pass-operator v{__version__}')
        sys.exit(0)

    # Configure logger
    if args.log_stdout:
        logging.basicConfig(
            stream=sys.stdout,
            format='%(asctime)s | %(levelname)s | %(message)s',
            level=args.log_level
        )
    else:
        logging.basicConfig(
            filename=args.log_file,
            format='%(asctime)s | %(levelname)s | %(message)s',
            level=args.log_level,
            filemode='a'
        )

