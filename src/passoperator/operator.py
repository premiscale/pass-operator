"""
Define the kopf-based operator, define some high-level methods for interacting with a git repository from pass.
"""

import kopf
import logging
import kubernetes
import datetime
import yaml
import os
import sys

from typing import Any, Dict, Union
from functools import cache
from importlib import resources
from git import Repo
from pathlib import Path


log = logging.getLogger(__name__)


class GitRepo:
    """
    Abstract gitpython with some higher-level methods for cloning and pulling updates from a git project.
    """

    def __init__(self, repo_url: str, branch: str, clone_location: Union[Path, str] ='/opt/pass-operator/repo') -> None:
        self.repo_url = repo_url
        self.branch = branch
        self.clone_location = clone_location
        self.cloned = False
        self.repo: Repo

    def git_clone(self) -> None:
        """
        Clone a git repository. Should only be called once.

        Args:
            repo_url (str): Location of the git repository.
            branch (str): Git branch to checkout.
            loc (str): Local file path to clone to.
        """
        if self.cloned:
            log.warn(f'Repository at URL {self.repo_url} has already been cloned to location "{self.clone_location}". Skipping.')
            return None

        repo = Repo.clone_from(
            url=self.repo_url,
            to_path=self.clone_location
        )

        if self.branch not in repo.branches:
            log.error(f'Branch "{self.branch}" not found in project at URL "{self.repo_url}"')
            sys.exit(1)

        if str(repo.active_branch) != self.branch:
            repo.git.checkout(self.branch)

        self.cloned = True

    def pass_git_pull(self) -> None:
        """
        Run 'git pull' in the cloned repository. This method will be called repeatedly, on an interval.
        """
        if not self.cloned:
            self.git_clone()

        self.repo.pull()


class PassOperator:
    """
    Encapsulate operator state.
    """

    def __init__(self, interval: int, git_repo_url: str, git_repo_branch: str, git_repo_clone_location: str ='/opt/pass-operator/repo') -> None:
        self.interval = interval

        # Clone the pass git repository into the pod.
        self.pass_git_repo = GitRepo(
            repo_url=git_repo_url,
            branch=git_repo_branch,
            clone_location=git_repo_clone_location
        )

        self.managed_secrets: Dict[str, str] = dict()
        self._api = kubernetes.client.CoreV1Api()

    @property
    def interval(self) -> int:
        return self._interval

    @interval.setter
    def interval(self, value: int) -> None:
        if value < 0:
            raise ValueError(f'Expected reconciliation interval value >= 1s, received {value}')
        self._interval = value

    @staticmethod
    @cache
    def read_manifest(path: str) -> Dict[str, str]:
        """
        Read a secret template from file and cache the contents.

        Args:
            path (str): filename to read from data.

        Returns:
            str: contents of the file.
        """
        with resources.open_text('src.data', path) as obj:
            return yaml.safe_load(obj.read().rstrip())

    @staticmethod
    def get_current_namespace(namespace_path: str ='/var/run/secrets/kubernetes.io/serviceaccount/namespace') -> str:
        """
        Get the current namespace this operator is deployed in. Refactored from the following GitHub issue.

            https://github.com/kubernetes-client/python/issues/363

        Args:
            namespace_path (str): Namespace path in the local filesystem. Defaults to '/var/run/secrets/kubernetes.io/serviceaccount/namespace'.

        Returns:
            str: the namespace this process is running within on K8s.
        """
        if os.path.exists(namespace_path):
            with open(namespace_path) as f:
                return f.read().strip()
        try:
            _, active_context = kubernetes.config.list_kube_config_contexts()
            return active_context['context']['namespace']
        except KeyError:
            return 'default'

    def daemon_start(self, kopf_config: Dict) -> int:
        """
        Start the kopf daemon.

        Args:
            kopf_config (dict): kopf config dictionary.

        Returns:
            int: exit code.
        """
        return kopf.run(**kopf_config)

    @kopf.on.cleanup()
    def cleanup(self, **kwargs) -> None:
        pass

    @kopf.on.startup()
    def start(self, settings: kopf.OperatorSettings, version: str, priority: int =100) -> None:
        """
        Reconcile current state of PassSecret objects and remote git repository (desired state);
        bring current state of those objects into alignment.
        """
        log.info(f'Starting operator version {version}')

        log.info(f'Setting operator priority to {priority}')
        settings.peering.priority = priority

    @kopf.on.update('PassSecret')
    def update(self, **kwargs: Any) -> None:
        """
        An update was received on the PassSecret object, so attempt to update the corresponding Secret.
        """


    @kopf.on.create('PassSecret')
    def create(self, **kwargs: Any) -> None:
        """
        Create a new Secret from a PassSecret manifest.

        Args:
            version (str): version of the agent.

        Returns:
            None.
        """


    @kopf.on.delete('PassSecret')
    def delete(self, **kwargs: Any) -> None:
        """
        Remove the secret from memory.

        Args:
            spec (str): _description_
        """

    @kopf.timer('PassSecret', interval=interval, initial_delay=1)
    def reconciliation(self) -> Any:
        """
        Reconcile secrets across all namespaces and ensure they match the stored desired state.

        Args:
            spec (_type_): _description_
            log (_type_): _description_

        Returns:
            Any: _description_
        """

    @kopf.on.probe(id='now')
    def get_current_timestamp(self, **kwargs):
        return datetime.datetime.utcnow().isoformat()

    @kopf.on.probe(id='status')
    def get_current_status(self, **kwargs):
        return 'ok'