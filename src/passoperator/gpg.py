"""
Provide methods for interacting with GnuPG.
"""


from pathlib import Path
from gnupg import GPG

import logging


log = logging.getLogger(__name__)


def decrypt(path: Path, home: Path = Path('~/.gnupg').expanduser(), passphrase: str | None = None) -> str | None:
    """
    Decrypt a path in the store to a string.

    Args:
        path (Path): pass store path.
        home (Path): GnuPG home directory (default: ~/.gnupg)

    Returns:
        Optional[str]: the decrypted string if we could decrypt it; None, otherwise.
    """
    home.mkdir(parents=True, exist_ok=True)

    gpg = GPG(
        gnupghome=home
    )

    try:
        # https://gnupg.readthedocs.io/en/latest/#decryption
        decrypted_file = gpg.decrypt_file(
            f'{str(path)}.gpg',
            always_trust=True,
            passphrase=passphrase
        )

        return str(decrypted_file).rstrip()
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