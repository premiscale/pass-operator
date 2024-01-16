"""
Provide methods for interacting with GnuPG.
"""

import logging

from typing import Optional
from pathlib import Path
from gnupg import GPG


log = logging.getLogger(__name__)


def decrypt(path: Path, home: Path = Path('~/.gnupg').expanduser()) -> Optional[str]:
    """
    Decrypt a path in the store to a string.

    Args:
        path (Path): pass store path.
        home (Path): GnuPG home directory (default: ~/.gnupg)

    Returns:
        str: the decrypted string.
    """
    gpg = GPG(gnupghome=home)

    try:
        with open(f'{path}.gpg', 'rb') as gpg_f:
            # https://gnupg.readthedocs.io/en/latest/#decryption
            gpg_f_decrypted = gpg.decrypt_file(gpg_f)

        return str(gpg_f_decrypted)
    except (IOError, PermissionError) as e:
        log.error(e)
        return None


def decrypt_bytes(path: Path) -> str:
    """
    Decrypt a path in the store to a b64enc'ed string of bytes.

    Args:
        path (Path): pass store path.

    Returns:
        bytes: base64'ed string of bytes.
    """
    return ''