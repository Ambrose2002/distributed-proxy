"""Test suite for TTLCache to verify basic cache operations and TTL expiration."""

from proxy.cache_utils import TTLCache
import time

# Test that the cache size is initially zero.
def test_size():
    cache = TTLCache(3)
    assert cache.size() == 0
    
# Test that setting a key increases the cache size.
def test_set_basic():
    cache = TTLCache(3)
    cache.set("key1", "value1")
    assert cache.size() == 1
    
# Test that a set value can be retrieved correctly.
def test_get_basic():
    cache = TTLCache(3)
    cache.set("key1", "value1")
    assert cache.get("key1")[0] == "value1"
    
# Test that updating a key changes its stored value.
def test_get_modified():
    cache = TTLCache(3)
    cache.set("key1", "value1")
    cache.set("key1", "value01")
    assert cache.get("key1")[0] == "value01"
    
# Test that a key returns None after its TTL expires.
def test_get_after_ttl_expire():
    cache = TTLCache(1)
    cache.set("key1", "value1")
    time.sleep(2)
    assert cache.get("key1")[0] == None