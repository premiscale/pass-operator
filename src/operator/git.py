"""
Methods to interact minimally with a Git repository.
"""


from typing import Union, List
from pathlib import Path
from src.operator.utils import cmd

import logging


log = logging.getLogger(__name__)


def pull(path: Union[Path, str], branch: str ='main') -> List[str]:
    """
    Run git pull at some location.

    Args:
        path (Union[Path, str]): path to the git repository.
        branch (str): branch to pull.

    Returns:
        List[str]: stdout of the command.
    """
    with cmd(f'cd {str(path)} && git pull origin {branch}', shell=True) as s:
        return s