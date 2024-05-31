"""
Provide a locking mechanism for event handlers to block processing PassSecrets that are already in-progress.
"""


from __future__ import annotations
from typing import List, Tuple, Any, Callable
from time import sleep
from functools import wraps

import kopf
import logging


log = logging.getLogger(__name__)

__in_progress_queue: List[Tuple[Any, Any]] = []

__all__ = [
    'lock_passsecret'
]


def lock_passsecret(exit_early: bool = False) -> Callable:
    """
    Decorator to halt handlers' progress on a PassSecret until it's safe to modify.

    Args:
        exit_early (bool): if True, the handler will exit early if the PassSecret is already blocked instead of waiting.

    Returns:
        Callable: the decorated function.
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(body: kopf.Body, *args: Any, **kwargs: Any):
            nonlocal exit_early
            if exit_early:
                if _is_passsecret_blocked(body):
                    log.info(f'PassSecret "{body["metadata"]["name"]}" is still in progress. Skipping.')
                    return None

            # If exit_early is not set, this method will block until the PassSecret is unlocked.
            _block_passsecret_block(body)

            try:
                return f(body=body, *args, **kwargs)
            finally:
                _lift_passsecret_block(body)
        return wrapper
    return decorator


def _passsecret_block(body: kopf.Body) -> None:
    """
    Block handlers' progress on a PassSecret until it's safe to modify the managed secret.
    Decryption takes time, so we want to be sure to queue up any changes.

    Args:
        body [kopf.Body]: raw body of the PassSecret.

    Raises:
        kopf.TemporaryError: if the PassSecret is already blocked.
    """
    log.debug(f'Blocking PassSecret "{body["metadata"]["name"]}" in namespace "{body["metadata"]["namespace"]}')

    if _is_passsecret_blocked(body):
        raise kopf.TemporaryError(f'PassSecret "{body["metadata"]["name"]}" in namespace "{body["metadata"]["namespace"]}" is already blocked.')

    __in_progress_queue.append(
        (
            body['metadata']['name'],
            body['metadata']['namespace']
        )
    )


def _is_passsecret_blocked(body: kopf.Body) -> bool:
    """
    Check if a PassSecret is blocked from modification.

    Args:
        body [kopf.Body]: raw body of the PassSecret.

    Returns:
        bool: True if the PassSecret is blocked, else False.
    """
    return (
        body['metadata']['name'],
        body['metadata']['namespace']
    ) in __in_progress_queue


def _block_passsecret_block(body: kopf.Body) -> None:
    """
    Block handlers' progress on a PassSecret until it's safe to modify the managed secret.
    This should only ever be called by event handlers, not by the reconciliation loop.

    Args:
        body (kopf.Body): raw body of the PassSecret.
    """
    while True:
        if not _is_passsecret_blocked(body):
            _passsecret_block(body)
            break
        else:
            log.debug(f'PassSecret "{body["metadata"]["name"]}" in namespace "{body["metadata"]["namespace"]}" is already blocked.')
            sleep(0.5)


def _lift_passsecret_block(body: kopf.Body) -> None:
    """
    Unblock handlers' progress to modify the managed secret.

    Args:
        body [kopf.Body]: raw body of the PassSecret.
    """
    log.debug(f'Lifting block on PassSecret "{body["metadata"]["name"]}" in namespace "{body["metadata"]["namespace"]}"')
    __in_progress_queue.remove(
        (
            body['metadata']['name'],
            body['metadata']['namespace']
        )
    )