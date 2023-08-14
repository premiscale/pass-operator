"""
High level methods for interacting with the Kubernetes API.
"""

from typing import List, Dict
from kubernetes import client, config


class Kubectl:
    """
    Encapsulate commands' state.
    """
    def __init__(self, namespace: str = 'default') -> None:
        self.namespace = namespace
        config.load_incluster_config()
        self._api = client.CoreV1Api()

    def get_pods(self) -> List[Dict]:
        """
        Get a list of Pods in a namespace.

        Returns:
            List[Dict]: a list of pod names.
        """
        pods = self._api.list_namespaced_pod(namespace=self.namespace).to_dict().get('items')

        return pods

    def get_deployments(self) -> List[Dict]:
        """
        Get a list of Deployments in a namespace.

        Returns:
            List[Dict]: a list of Deployment objects.
        """
        # deployments = self._api.list_namespaced_deployment
        return list()