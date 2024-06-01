"""
Provide a locking mechanism for event handlers to block processing PassSecrets and any object
that is already in-progress.
"""


from __future__ import annotations
from typing import Dict, Tuple, List, Any, Callable, Iterator, TypeAlias
from time import sleep
from functools import wraps
from dataclasses import dataclass
from time import sleep, time

import kopf
import logging
import uuid


log = logging.getLogger(__name__)

__all__ = [
    'lock',
    'drain_event_queues'
]


Key: TypeAlias = Tuple[Any, Any, Any]


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
    __unblock_order_queue: Dict[Key, _Queue] = {}

    def __init__(self, maxsize: int = 0):
        self.maxsize = maxsize

    def __iter__(self) -> Iterator[Key]:
        return iter(self.__unblock_order_queue)

    def __getitem__(self, key: Key) -> List[str]:
        return self.__unblock_order_queue[key].event_ids

    # Instead of providing a setitem method, we'll provide an interface around the individual queues.

    def init(self, key: Key) -> None:
        """
        Initialize a queue for a particular object.

        Args:
            key (Key): A unique identifier for the queue of IDs (name, namespace).
        """
        if key not in self.__unblock_order_queue:
            self.__unblock_order_queue[key] = _Queue(event_ids=[])

    def put(self, key: Key, event_id: str) -> bool:
        """
        Place an event ID on the queue. If the queue is full, return False.

        Args:
            key (Key): A unique identifier for the queue of IDs (name, namespace).
            event_id (str): A unique identifier for the event.

        Returns:
            bool: False if the queue is full, else True.
        """
        if key not in self.__unblock_order_queue:
            self.init(key)

        if self.__unblock_order_queue[key].locked or len(self.__unblock_order_queue[key].event_ids) >= self.maxsize > 0:
            return False

        self.__unblock_order_queue[key].event_ids.append(event_id)
        return True

    def get(self, key: Key) -> str:
        """
        Retrieve the first event ID from the queue.

        Args:
            key (Key): A unique identifier for the queue of IDs (name, namespace).

        Returns:
            str: the first event ID in the queue.
        """
        return self.__unblock_order_queue[key].event_ids.pop(0)

    def qsize(self, key: Key) -> int:
        """
        Get the size of the queue.

        Args:
            key (Key): A unique identifier for the queue of IDs (name, namespace).

        Returns:
            int: the size of the queue.
        """
        if key not in self.__unblock_order_queue:
            self.init(key)

        return len(self.__unblock_order_queue[key].event_ids)

    def lock(self, key: Key) -> None:
        """
        Lock the queue to prevent further modifications.

        Args:
            key (Key): A unique identifier for the queue of IDs (name, namespace).
        """
        if key not in self.__unblock_order_queue:
            self.init(key)

        log.debug(f'Locking queue for {key[0]} "{key[1]}" in namespace "{key[2]}"')
        self.__unblock_order_queue[key].locked = True

    def unlock(self, key: Key) -> None:
        """
        Unlock the queue to allow modifications.

        Args:
            key (Key): A unique identifier for the queue of IDs (name, namespace).
        """
        if key not in self.__unblock_order_queue:
            self.init(key)

        log.debug(f'Unlocking queue for {key[0]} "{key[1]}" in namespace "{key[2]}"')
        self.__unblock_order_queue[key].locked = False

    def drain(self, key: Key) -> None:
        """
        Drain the queue of all event IDs.

        Args:
            key (Key): A unique identifier for the queue of IDs (name, namespace).
        """
        if key not in self.__unblock_order_queue:
            self.init(key)

        assert self.__unblock_order_queue[key].locked

        while True:
            if len(self.__unblock_order_queue[key].event_ids) == 0:
                log.debug(f'Successfully drained queue for {key[0]} "{key[1]}" in namespace "{key[2]}"')
                break
            else:
                sleep(0.25) # Wait for the queue to be empty.

    def fst(self, key: Key) -> str:
        """
        Get the first event ID in the queue.

        Args:
            key (Key): A unique identifier for the queue of IDs (name, namespace).

        Returns:
            str: the first event ID in the queue.
        """
        return self.__unblock_order_queue[key].event_ids[0]


eventqueues = EventQueues()


def drain_event_queues() -> None:
    """
    Drain the event queues for all objects that currently have a backlog of events.
    """
    for queue in eventqueues:
        eventqueues.lock(queue)
        eventqueues.drain(queue)  # blocks


def lock(wait: bool = True) -> Callable:
    """
    Decorator to halt handlers' progress or drop the handler altogether on an object's event until
    it's safe to modify. A common clash with an object is a timer and an event handler.

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

            if (not wait and eventqueues.qsize(key) > 1) or (eventqueues.maxsize > 0 and eventqueues.qsize(key) == eventqueues.maxsize):
                log.info(f'Exiting early for {key[0]} "{key[1]}" in namespace "{key[2]}" due to object queue backlog exceeding specified limit.')
                return None

            _lock_event(key, event_id=_id)
            _block_event(key, event_id=_id)

            try:
                return f(body=body, *args, **kwargs)
            finally:
                _unlock_event(key, event_id=_id)
        return wrapper
    return decorator


def _lock_event(key: Key, event_id: str) -> bool:
    """
    Block handlers' progress on an object until it's safe to modify the managed secret.
    Decryption takes time, so we want to be sure to queue up any changes.

    Args:
        key (Key): key of the object.
        event_id (str): unique identifier for the event.

    Returns:
        bool: True if the PassSecret is blocked, else False.
    """
    log.debug(f'Blocking event {event_id} for {key[0]} "{key[1]}" in namespace "{key[2]}"')

    # Queue up the handler's internal ID to be processed when the current actions on the queue are done.
    return eventqueues.put(key, event_id)


def _unlock_event(key: Key, event_id: str) -> None:
    """
    Unblock handlers' progress to modify the managed secret.

    Args:
        key (Key): key of the object.
        event_id (str): unique identifier for the event.
    """
    log.debug(f'Unlocking event {event_id} for {key[0]} "{key[1]}" in namespace "{key[2]}"')

    assert eventqueues.get(key) == event_id


def _is_event_locked(key: Key, event_id: str) -> bool:
    """
    Check if a particular object event is at the start of the queue. If it's not, block the handler. Otherwise, proceed.

    Args:
        key (Key): key of the object.
        event_id (str): unique identifier for the event.

    Returns:
        bool: True if the PassSecret is blocked, else False.
    """
    return eventqueues.qsize(key) > 0 and eventqueues.fst(key) != event_id


def _block_event(key: Key, event_id: str) -> None:
    """
    Block handlers' progress on a PassSecret until it's safe to modify the managed secret.
    This should only ever be called by event handlers, not by the reconciliation loop.

    Args:
        key (Key): key of the object.
        event_id (str): unique identifier for the event.
    """
    start_time = time()
    while _is_event_locked(key, event_id):
        sleep(0.25)
    else:
        log.debug(f'Unblocked event {event_id} for {key[0]} "{key[1]}" in namespace "{key[2]}" after {time() - start_time:.2f} seconds.')