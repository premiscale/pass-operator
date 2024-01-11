"""
Define some high-level methods for interacting with a git repository from pass.
"""


def pass_git_pull(key: str, repo_url: str, branch: str, ) -> None:
    """
    Run a pass git pull to pull latest contents from the repository.
    """
