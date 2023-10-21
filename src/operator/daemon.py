"""
Start the kopf-based operator.
"""

from typing import Any

import kopf
import logging


log = logging.getLogger(__name__)


@kopf.on.create('PassSecret')
def start(version: str, **kwargs: Any) -> None:
    """
    Start the pass operator.

    Args:
        version (str): version of the agent.

    Returns:
        None.
    """
    log.info(f'Starting Pass operator v{version}')


@kopf.on.cleanup('PassSecret')
def stop(log) -> None:
    """
    Stop

    Args:
        log (_type_): _description_
    """
