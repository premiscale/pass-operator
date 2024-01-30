"""
Methods to interact minimally with a Git repository.
"""


from pathlib import Path
from src.operator.utils import cmd

import logging


log = logging.getLogger(__name__)


def clone(url: str, branch: str ='main', path: Path | str =Path('~/.password-store').expanduser()) -> None:
    """
    Run git clone into a location.

    Args:
        url (str): Git repo URL.
        path (Union[Path, str]): Local container repo path.
        branch (str, optional): Branch to clone into from the remote repository. Defaults to 'main'.
    """
    if not Path(path).exists():
        Path(path).mkdir(parents=True, exist_ok=True)

    with cmd(f'git clone --branch {branch} {url} {path}', shell=True) as (stdout, stderr):
        log.info(f'stdout: {stdout} | stderr: {stderr}')


def pull(path: Path | str =Path('~/.password-store').expanduser(), branch: str ='main', continuous: bool =False) -> None:
    """
    Run git pull at some location.

    Args:
        path (Union[Path, str]): path to the git repository.
        branch (str): branch to pull.
        continuous (bool):
    """
    from time import sleep
    if continuous:
        while True:
            with cmd(f'cd {path} && git gc --prune=now && git fetch && git merge origin/{branch}', shell=True) as (stdout, stderr):
                log.info(f'stdout: {stdout} | stderr: {stderr}')
            sleep(60)