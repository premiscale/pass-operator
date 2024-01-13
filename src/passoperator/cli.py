"""
A kubernetes operator that syncs and decrypts secrets from Linux password store (https://www.passwordstore.org/) git repositories
"""

import logging
import sys

from pathlib import Path
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from importlib import metadata as meta
from enum import Enum

from src.passoperator.operator import PassOperator


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
            log.error(f'ERROR: Must specify an accepted log level, received {s}')
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
        '--log-file', default='/opt/pass-operator/runtime.log', type=str,
        help='Log file location (if log-stdout is not provided).'
    )

    parser.add_argument(
        '--pass-binary', type=str, default='/usr/bin/pass',
        help='Path to an alternate pass binary.'
    )

    parser.add_argument(
        '--pass-dir', type=str, default='/opt/pass-operator/repo',
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
        help='Git branch to pull secrets from in repository.'
    )

    parser.add_argument(
        '--interval', type=int, default=60,
        help='PassSecret reconciliation interval. Defines how often the operator ensures secrets are in alignment with desired state of the git repository.'
    )

    args = parser.parse_args()

    if args.version:
        print(f'pass-operator v{__version__}')
        sys.exit(0)

    # Configure logger
    if args.log_stdout:
        logging.basicConfig(
            stream=sys.stdout,
            format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
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
                filemode='a'
            )
        except (FileNotFoundError, PermissionError) as msg:
            log.error(f'Failed to configure logging, received: {msg}')
            sys.exit(1)

    if args.daemon:
        PassOperator(
            interval=args.interval,
            git_repo_url=args.git_ssh_url,
            git_repo_branch=args.git_branch,
            git_repo_clone_location=args.pass_dir
        ).daemon_start(
            dict()
        )