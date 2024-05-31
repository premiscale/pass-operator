"""
Provide a locking mechanism for event handlers to block processing PassSecrets and any object
that is already in-progress.
"""


from __future__ import annotations
from typing import Dict, Tuple, List, Any, Callable, Iterator
from time import sleep
from functools import wraps
from dataclasses import dataclass
from time import sleep

import kopf
import logging
import uuid


log = logging.getLogger(__name__)

__all__ = [
    'lock',
    'drain_event_queues'
]


def _generate_lock_id() -> str:
    """
    Generate a unique identifier for a lock.

    Returns:
        str: a unique identifier.
    """
    return str(uuid.uuid4())


@dataclass
class _Queue:
    """
    A queue dataclass to store event IDs and other attributes about a particular object's event queue.
    """
    event_ids: List[str]
    locked: bool = False


class EventQueues:
    """
    A queue type to store event IDs. This ensures that events for a particular object are
    processed in the order they are received.

    Processing PassSecrets in particular takes a little time, so we
    want to be sure that we don't attempt to modify the same PassSecret between multiple threads.

    Returns:
        _type_: _description_
    """
    __unblock_order_queue: Dict[Tuple[Any, Any, Any], _Queue] = {}

    def __init__(self, maxsize: int = 0):
        self.maxsize = maxsize

    def __iter__(self) -> Iterator[Tuple[Any, Any, Any]]:
        return iter(self.__unblock_order_queue)

    def __getitem__(self, key: Tuple[Any, Any, Any]) -> List[str]:
        return self.__unblock_order_queue[key].event_ids

    # Instead of providing a setitem method, we'll provide an interface around the individual queues.

    def put(self, key: Tuple[Any, Any, Any], event_id: str) -> bool:
        """
        Place an event ID on the queue. If the queue is full, return False.

        Args:
            key (Tuple[Any, Any, Any]): A unique identifier for the queue of IDs (name, namespace).
            event_id (str): A unique identifier for the event.

        Returns:
            bool: False if the queue is full, else True.
        """
        if key not in self.__unblock_order_queue:
            self.__unblock_order_queue[key].event_ids = []

        if self.__unblock_order_queue[key].locked or len(self.__unblock_order_queue[key].event_ids) >= self.maxsize > 0:
            return False

        self.__unblock_order_queue[key].event_ids.append(event_id)
        return True

    def get(self, key: Tuple[Any, Any, Any]) -> str:
        """
        Retrieve the first event ID from the queue.

        Args:
            key (Tuple[Any, Any, Any]): A unique identifier for the queue of IDs (name, namespace).

        Returns:
            str: the first event ID in the queue.
        """
        return self.__unblock_order_queue[key].event_ids.pop(0)

    def qsize(self, key: Tuple[Any, Any, Any]) -> int:
        """
        Get the size of the queue.

        Args:
            key (Tuple[Any, Any, Any]): A unique identifier for the queue of IDs (name, namespace).

        Returns:
            int: the size of the queue.
        """
        return len(self.__unblock_order_queue[key].event_ids)

    def lock(self, key: Tuple[Any, Any, Any]) -> None:
        """
        Lock the queue to prevent further modifications.

        Args:
            key (Tuple[Any, Any, Any]): A unique identifier for the queue of IDs (name, namespace).
        """
        log.debug(f'Locking queue for {key[0]} "{key[1]}" in namespace "{key[2]}"')
        self.__unblock_order_queue[key].locked = True

    def unlock(self, key: Tuple[Any, Any, Any]) -> None:
        """
        Unlock the queue to allow modifications.

        Args:
            key (Tuple[Any, Any, Any]): A unique identifier for the queue of IDs (name, namespace).
        """
        self.__unblock_order_queue[key].locked = False

    def drain(self, key: Tuple[Any, Any, Any]) -> None:
        """
        Drain the queue of all event IDs.

        Args:
            key (Tuple[Any, Any, Any]): A unique identifier for the queue of IDs (name, namespace).
        """
        assert self.__unblock_order_queue[key].locked

        while True:
            if len(self.__unblock_order_queue[key].event_ids) == 0:
                log.debug(f'Successfully drained queue for {key[0]} "{key[1]}" in namespace "{key[2]}"')
                break
            else:
                sleep(0.25) # Wait for the queue to be empty.

    def fst(self, key: Tuple[Any, Any, Any]) -> str:
        """
        Get the first event ID in the queue.

        Args:
            key (Tuple[Any, Any, Any]): A unique identifier for the queue of IDs (name, namespace).

        Returns:
            str: the first event ID in the queue.
        """
        return self.__unblock_order_queue[key].event_ids[0]


eventqueue = EventQueues()


def drain_event_queues() -> None:
    """
    Drain the event queues for all objects that currently have a backlog of events.
    """
    for queue in eventqueue:
        eventqueue.lock(queue)
        eventqueue.drain(queue)  # blocks


def lock(wait: bool = True) -> Callable:
    """
    Decorator to halt handlers' progress on an object until it's safe to modify.

    Args:
        wait (bool): if False, the handler will exit early without executing the handler's body.
            Otherwise, get in line (if there is one).

    Returns:
        Callable: the decorated function.
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(body: kopf.Body, *args: Any, **kwargs: Any):
            nonlocal wait

            key = (
                body['kind'],
                body['metadata']['name'],
                body['metadata']['namespace'],
            )

            _id = _generate_lock_id()
            _lock_event(key, event_id=_id)

            # Exit doing nothing if the queue for this particular object is not empty.
            if not wait and eventqueue.qsize(key) > 1:
                _unlock_event(key, event_id=_id)
                return None

            _block_event(key, event_id=_id)

            try:
                return f(body=body, *args, **kwargs)
            finally:
                _unlock_event(key, event_id=_id)
        return wrapper
    return decorator


def _lock_event(key: Tuple[Any, Any, Any], event_id: str) -> None:
    """
    Block handlers' progress on an object until it's safe to modify the managed secret.
    Decryption takes time, so we want to be sure to queue up any changes.

    Args:
        key (Tuple[Any, Any, Any]): key of the object.
        event_id (str): unique identifier for the event.

    Raises:
        kopf.TemporaryError: if the object is already blocked.
    """
    log.debug(f'Blocking event ID "{event_id}" for {key[0]} "{key[1]}" in namespace "{key[2]}"')

    if _is_event_locked(key, event_id):
        raise kopf.TemporaryError(f'Event {event_id} for {key[0]} "{key[1]}" in namespace "{key[2]}" is already blocked.')

    # Queue up the handler's internal ID to be processed when the current actions on the queue are done.
    eventqueue.put(key, event_id)


def _is_event_locked(key: Tuple[Any, Any, Any], event_id: str) -> bool:
    """
    Check if a particular object event is at the start of the queue. If it's not, block the handler. Otherwise, proceed.

    Args:
        key (Tuple[Any, Any, Any]): key of the object.
        event_id (str): unique identifier for the event.

    Returns:
        bool: True if the PassSecret is blocked, else False.
    """
    return eventqueue.qsize(key) > 0 and \
    eventqueue.fst(key) != event_id


def _block_event(key: Tuple[Any, Any, Any], event_id: str) -> None:
    """
    Block handlers' progress on a PassSecret until it's safe to modify the managed secret.
    This should only ever be called by event handlers, not by the reconciliation loop.

    Args:
        key (Tuple[Any, Any, Any]): key of the object.
        event_id (str): unique identifier for the event.
    """
    while _is_event_locked(key, event_id):
        log.debug(f'{key[0]} "{key[1]}" in namespace "{key[2]}" is already blocked.')
        sleep(0.25)


def _unlock_event(key: Tuple[Any, Any, Any], event_id: str) -> None:
    """
    Unblock handlers' progress to modify the managed secret.

    Args:
        key (Tuple[Any, Any, Any]): key of the object.
        event_id (str): unique identifier for the event.
    """
    log.debug(f'Lifting block on {key[0]} "{key[1]}" in namespace "{key[2]}"')

    assert eventqueue.get(key) == event_id