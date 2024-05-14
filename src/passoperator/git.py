"""
Methods to interact minimally with a Git repository.
"""


from git import Repo
from git.exc import CommandError
from time import sleep
from passoperator import env

import logging
import sys


log = logging.getLogger(__name__)


def clone() -> None:
    """
    Run git clone with configuration from environment variables using gitpython.
    """
    repo = Repo.clone_from(
        url=env['PASS_GIT_URL'],
        to_path=env['PASS_DIRECTORY']
    )

    # if env['PASS_GIT_BRANCH'] not in repo.branches:
    #     log.error(f'Branch "{env["PASS_GIT_BRANCH"]}" not found in project at URL "{env["PASS_GIT_URL"]}"')
    #     sys.exit(1)

    if str(repo.active_branch) != env['PASS_GIT_BRANCH']:
        repo.git.checkout('origin/' + env['PASS_GIT_BRANCH'])

    log.info(f'Successfully cloned repo {env["PASS_GIT_URL"]} to password store {env["PASS_DIRECTORY"]}')


def pull(daemon: bool =False, retry: bool =False) -> None:
    """
    Blocking function that optionally runs 'git pull' in the cloned repository, repeatedly. This said, the
    default behavior is to retry indefinitely until a 'git pull' succeeds.

    Args:
        daemon (bool): whether or not to loop on the user-specified OPERATOR_INTERVAL. (default: False)
        retry (bool): whether or not to retry the git pull indefinitely until it succeeds. (default: False)
    """
    tries = 0

    while daemon or retry:
        # Try to pull from the repository. If successful and daemon is not set, break from the loop.
        # Otherwise, continue to try to pull from the repository on an interval.
        try:
            log.info(f'Updating local password store at "{env["PASS_DIRECTORY"]}"')
            repo = Repo(env['PASS_DIRECTORY'])
            repo.remotes.origin.pull()
            if daemon:
                tries = 0
                sleep(float(env['OPERATOR_INTERVAL']))
        except CommandError as e:
            log.error(f'Retry {tries} git pull: {e}')
            tries += 1

        if not daemon:
            break