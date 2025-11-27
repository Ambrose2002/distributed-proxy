"""Module providing thread-safe TTLCache and LRUCache implementations along with an abstract Cache base class for caching data with expiration support in the proxy node.

The TTLCache is used to store key-value pairs with a time-to-live (TTL), ensuring that cached data
is automatically evicted after the TTL expires. The LRUCache implements a Least Recently Used
eviction policy. Both caches help improve performance by reducing redundant data retrievals
within the proxy node.
"""

import threading
from datetime import datetime, timedelta
from collections import defaultdict
from abc import ABC, abstractmethod
from typing import Any, Tuple 

class Cache(ABC):
    """Abstract base class for cache implementations.

    Defines a thread-safe interface for cache operations including get, set, and size.
    Subclasses must implement the get and set methods.
    Thread safety is managed via a reentrant lock.
    """
    
    def __init__(self):
        self.store = {}
        self.lock = threading.RLock()
        
        
    @abstractmethod
    def get(self, key) -> Tuple[Any, bool]:
        pass
    
    @abstractmethod
    def set(self, key, value):
        pass
    
    def size(self):
        return len(self.store)
    

class TTLCache(Cache): 
    """Thread-safe cache storing key-value pairs with expiration timestamps.

    This cache maintains entries with a fixed time-to-live (TTL). Entries are evicted
    upon access if expired. Thread safety is ensured via a reentrant lock, allowing safe
    concurrent access. Intended for use cases where cached data should automatically expire
    after a certain duration to prevent stale data usage.
    """
    
    def __init__(self, ttl):
        """Initialize the TTLCache with a specified time-to-live for entries.

        Args:
            ttl (int): Time-to-live duration in seconds for each cache entry.

        Side Effects:
            Creates an internal store dictionary and a reentrant lock for concurrency control.
        """
        super().__init__()
        self.ttl = ttl
        
    def get(self, key):
        """Retrieve the value for a given key if it exists and has not expired.

        Args:
            key: The key to look up in the cache.

        Returns:
            tuple: (value, True) if key exists and is valid; (None, False) otherwise.

        Side Effects:
            If the key exists but is expired, it is removed from the cache.

        Concurrency:
            Thread-safe; acquires a lock during access.
        """
        with self.lock:
            if key not in self.store:
                return (None, False)

            value, exp = self.store[key]
            if datetime.now() > exp:
                self.delete(key)
                return (None, False)
            return (value, True)
    
    def set(self, key, value):
        """Set the value for a given key with the current TTL expiration.

        Args:
            key: The key to store.
            value: The value associated with the key.

        Side Effects:
            Updates or adds the key-value pair with a new expiration timestamp.

        Concurrency:
            Thread-safe; acquires a lock during modification.
        """
        with self.lock:
            self.store[key] = (value, datetime.now() + timedelta(seconds = self.ttl))
        
    def delete(self, key):
        """Remove a key and its associated value from the cache if present.

        Args:
            key: The key to remove.

        Side Effects:
            Deletes the key from the internal store if it exists.

        Concurrency:
            Thread-safe; acquires a lock during modification.
        """
        with self.lock:
            self.store.pop(key, None)
    

class ListNode:
    """Doubly-linked list node used internally by LRUCache to maintain usage order.

    Each node stores a key, a value, and pointers to the previous and next nodes in the list.
    """
    def __init__(self, key, value, next=None, prev=None):
        self.key = key
        self.value = value
        self.next = next
        self.prev = prev
        
        
class LRUCache(Cache):
    """Thread-safe Least Recently Used (LRU) cache implementation.

    Maintains a fixed capacity and evicts the least recently used entries when capacity is exceeded.
    Uses a doubly-linked list to track usage order, with most recently used items at the end.
    Thread safety is ensured via a reentrant lock.
    """
    
    def __init__(self, capacity):
        """Initialize the LRUCache with a fixed capacity.

        Args:
            capacity (int): Maximum number of entries the cache can hold.

        Side Effects:
            Initializes internal linked list with dummy head and tail nodes and sets up locking.
        """
        super().__init__()
        self.capacity = capacity
        
        self.head = ListNode("head", "")
        self.tail = ListNode("tail", "")
        self.head.next = self.tail
        self.tail.prev = self.head
        self.lock = threading.RLock()
        
    
    def get(self, key):
        """Retrieve the value for a given key and mark it as recently used.

        Args:
            key: The key to look up in the cache.

        Returns:
            tuple: (value, True) if key exists; (None, False) otherwise.

        Side Effects:
            Moves the accessed node to the end of the usage list to mark it as recently used.

        Concurrency:
            Thread-safe; acquires a lock during access and modification.
        """
        with self.lock:
            if key not in self.store:
                return (None, False)
            
            node = self.store[key]
            
            self._delete(node)
            self._add_to_end(node)
            self.store[key] = node
            return (node.value, True)
        
    def set(self, key, value):
        """Set the value for a given key, updating usage and evicting if necessary.

        Args:
            key: The key to store.
            value: The value associated with the key.

        Side Effects:
            Updates existing node or adds a new node to the end of the usage list.
            Evicts the least recently used node if capacity is exceeded.

        Concurrency:
            Thread-safe; acquires a lock during modification.
        """
        with self.lock:
            if key in self.store:
                node = self.store[key]
                node.value = value
                self._delete(node)
            else:
                node = ListNode(key, value)
            
            self._add_to_end(node)
            self.store[key] = node
            
            if self.size() > self.capacity:
                node_to_delete = self.head.next
                self._delete(node_to_delete)
        
    def _delete(self, node):
        """Remove a node from the linked list and from the store.

        Args:
            node (ListNode): The node to remove.

        Side Effects:
            Updates pointers of neighboring nodes and removes the node from the cache store.

        Concurrency:
            Assumes caller holds the lock.
        """
        node.prev.next = node.next
        node.next.prev = node.prev
        
        self.store.pop(node.key)
        
        node.prev = None
        node.next = None
        
        
        
    def _add_to_end(self, node):
        """Add a node to the end of the linked list, marking it as most recently used.

        Args:
            node (ListNode): The node to add.

        Side Effects:
            Updates pointers of the tail and previous last node to include the new node.

        Concurrency:
            Assumes caller holds the lock.
        """
        previous = self.tail.prev
        if previous is None:
            raise RuntimeError("List structure corrupted: tail.prev is None")
        previous.next = node
        node.prev = previous
        node.next = self.tail
        self.tail.prev = node
        