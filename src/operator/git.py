"""
Methods to interact minimally with a Git repository.
"""


from git import Repo
from time import sleep
from src.operator import env

import logging
# import sys


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
        repo.git.checkout(env['PASS_GIT_BRANCH'])

    log.info(f'Successfully cloned repo {env["PASS_GIT_URL"]} to password store {env["PASS_DIRECTORY"]}')


def pull() -> None:
    """
    Blocking function that runs 'git pull' in the cloned repository, repeatedly.
    """
    while True:
        log.info(f'Updating local password store at "{env["PASS_DIRECTORY"]}"')
        repo = Repo(env['PASS_DIRECTORY'])
        repo.remotes.origin.pull()
        sleep(float(env['OPERATOR_INTERVAL']))