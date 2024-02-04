"""
Utils for the operator.
"""


from typing import Generator, Tuple, List
from enum import Enum
from contextlib import contextmanager
from subprocess import Popen, PIPE, DEVNULL

import logging
import sys
import base64


log = logging.getLogger(__name__)


class LogLevel(Enum):
    """
    Log level enums.
    """
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


def b64Enc(value: str) -> str:
    """
    base64 encode a string.

    Args:
        value (str): the string to b64 encode.

    Returns:
        str: the value b64-encoded.
    """
    return base64.b64encode(bytes(value.rstrip().encode('utf-8'))).decode()


def b64Dec(value: str) -> str:
    """
    base64 -d a string.

    Args:
        value (str): the string to b64 decode.

    Returns:
        str: the value b64-decoded.
    """
    return base64.b64decode(value).rstrip().decode()


@contextmanager
def cmd(command: str, sep: str =' ', shell: bool =False, block: bool =True) -> Generator[Tuple[str, str] | Tuple[None, None], None, None]:
    """
    Get results from terminal commands as lists of lines of text.
    """
    if block:
        with Popen(command.split(sep), shell=shell, stdout=PIPE, stderr=PIPE) as proc:
            stdout, stderr = proc.communicate()
        yield stdout.decode().rstrip(), stderr.decode().rstrip()
    else:
        with Popen(command.split(sep), shell=shell, stdout=DEVNULL, stderr=DEVNULL) as proc:
            yield None, None