"""
Methods to interact minimally with a Git repository.
"""


from typing import Union, List
from pathlib import Path
from src.operator.utils import cmd

import logging


log = logging.getLogger(__name__)


def clone(url: str, branch: str ='main', path: Union[Path, str] =Path('~/.password-store').expanduser()) -> List[str]:
    """
    Run git clone into a location.

    Args:
        url (str): Git repo URL.
        path (Union[Path, str]): Local container repo path.
        branch (str, optional): Branch to clone into from the remote repository. Defaults to 'main'.

    Returns:
        List[s]: _description_
    """
    with cmd(f'git clone --branch {branch} {url} {path}', shell=False) as s:
        return s


def pull(path: Union[Path, str], branch: str ='main') -> List[str]:
    """
    Run git pull at some location.

    Args:
        path (Union[Path, str]): path to the git repository.
        branch (str): branch to pull.

    Returns:
        List[str]: stdout of the command.
    """
    with cmd(f'cd {path} && git pull origin {branch}', shell=True) as s:
        return s