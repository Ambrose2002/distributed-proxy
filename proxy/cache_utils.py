"""Module providing a thread-safe TTLCache for caching data with expiration support in the proxy node.

The TTLCache is used to store key-value pairs with a time-to-live (TTL), ensuring that cached data
is automatically evicted after the TTL expires. This cache helps improve performance by reducing
redundant data retrievals within the proxy node.
"""

import threading
from datetime import datetime, timedelta
from collections import defaultdict

class TTLCache: 
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
        self.store = {}
        self.ttl = ttl
        self.lock = threading.RLock()
        
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
        
    def size(self):
        """Return the current number of entries in the cache.

        Returns:
            int: Number of key-value pairs stored.

        Concurrency:
            Not explicitly locked; may reflect approximate size if concurrent modifications occur.
        """
        return len(self.store)
    

class ListNode:
    def __init__(self, key, value, next=None, prev=None):
        self.key = key
        self.value = value
        self.next = next
        self.prev = prev
        
        
class LRUCache:
    
    def __init__(self, capacity):
        self.capacity = capacity
        
        self.head = ListNode("head", "")
        self.tail = ListNode("tail", "")
        self.head.next = self.tail
        self.tail.prev = self.head
        
        self.dict = {}
        self.lock = threading.RLock()
        
    
    def get(self, key):
        
        with self.lock:
            if key not in self.dict:
                return None
            
            node = self.dict[key]
            
            self._delete(node)
            self._add_to_end(node)
            self.dict[key] = node
            return node.value
        
    def set(self, key, value):
        with self.lock:
            if key in self.dict:
                node = self.dict[key]
                node.value = value
                self._delete(node)
            else:
                node = ListNode(key, value)
            
            self._add_to_end(node)
            self.dict[key] = node
            
            if self.size() > self.capacity:
                node_to_delete = self.head.next
                self._delete(node_to_delete)
        
    def _delete(self, node):
        node.prev.next = node.next
        node.next.prev = node.prev
        
        self.dict.pop(node.key)
        
        node.prev = None
        node.next = None
        
        
        
    def _add_to_end(self, node):
        previous = self.tail.prev
        if previous is None:
            raise RuntimeError("List structure corrupted: tail.prev is None")
        previous.next = node
        node.prev = previous
        node.next = self.tail
        self.tail.prev = node
        
        
    def size(self):
        return len(self.dict)