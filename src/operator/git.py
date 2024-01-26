"""
Methods to interact minimally with a Git repository.
"""


from pathlib import Path
from typing import Union
from git import Repo

import logging
import os


log = logging.getLogger(__name__)


class GitRepo:
    """
    Abstract gitpython with some higher-level methods for cloning and pulling updates from a git project.

    Referencing this to clean this up eventually ~

       https://stackoverflow.com/questions/13166595/how-can-i-pull-a-remote-repository-with-gitpython
    """

    def __init__(self, repo_url: str, branch: str, clone_location: Union[Path, str] ='repo') -> None:
        self.repo_url = repo_url
        self.branch = branch
        self.clone_location = (os.getenv('HOME') or '') + '/.password-store/' + str(clone_location)
        self.cloned = False
        self.repo: Repo

    def clone(self) -> None:
        """
        Clone a git repository. Should only be called once.

        Args:
            repo_url (str): Location of the git repository.
            branch (str): Git branch to checkout.
            loc (str): Local file path to clone to.
        """
        if self.cloned:
            log.warning(f'Repository at URL {self.repo_url} has already been cloned to location "{self.clone_location}". Skipping')
            return None

        self.repo = Repo.clone_from(
            url=self.repo_url,
            to_path=self.clone_location
        )

        # if self.branch not in self.repo.branches:
        #     log.error(f'Branch "{self.branch}" not found in project at URL "{self.repo_url}"')
        #     sys.exit(1)

        if str(self.repo.active_branch) != self.branch:
            self.repo.git.checkout(self.branch)

        self.cloned = True

        log.info(f'Successfully cloned repo {self.repo_url} to password store {self.clone_location}')

        return None

    def pull(self) -> None:
        """
        Run 'git pull' in the cloned repository. This method will be called repeatedly, on an interval.
        """
        if not self.cloned:
            self.clone()

        log.info(f'Updating local password store at "{self.clone_location}"')
        self.repo.remotes.origin.pull()