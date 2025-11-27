"""Tests for the LRUCache class in proxy.cache_utils.

These tests verify the correct behavior of the LRUCache implementation,
including capacity handling, insertion, modification, eviction, and retrieval.
"""

from proxy.cache_utils import LRUCache

 # Tests that the capacity is set correctly during initialization.
def test_capacity():
    cache = LRUCache(3)
    assert cache.capacity == 3
    
 # Tests that a new cache has size zero.
def test_initial_size_is_zero():
    cache = LRUCache(3)
    assert cache.size() == 0
    

 # Tests basic set operations and size increment.
def test_set_basic():
    cache = LRUCache(3)
    cache.set("key1", "value1")
    assert cache.size() == 1
    
    cache.set("key2", "value2")
    assert cache.size() == 2
    
 # Tests that setting an existing key updates its value but not the size.
def test_set_modify_existing_key():
    cache = LRUCache(3)
    cache.set("key1", "value1")
    assert cache.size() == 1
    
    cache.set("key1", "value01")
    assert cache.size() == 1
    
 # Tests that exceeding capacity evicts the least recently used item.
def test_set_exceed_capacity():
    cache = LRUCache(2)
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")
    
    assert cache.size() == 2 
    
 # Tests basic get operation retrieves the correct value.
def test_get_basic():
    cache = LRUCache(3)
    cache.set("key1", "value1")
    
    assert cache.get("key1")[0] == "value1"
    
 # Tests that getting a modified key retrieves the updated value.
def test_get_modified_key():
    cache = LRUCache(3)
    cache.set("key1", "value1")
    cache.set("key1", "value01")
    
    assert cache.get("key1")[0] == "value01"
    
 # Tests that getting an evicted key returns None after capacity is exceeded.
def test_get_capacity_exceeded():
    cache = LRUCache(2)
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")
    
    assert cache.get("key1")[0] == None